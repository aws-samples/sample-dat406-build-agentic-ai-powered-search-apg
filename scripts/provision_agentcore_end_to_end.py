#!/usr/bin/env python3
"""
Provision the full AgentCore managed path for the Pellier workshop.

This script is strict by design:
  - Deploy 4 MCP Lambda servers.
  - Create/update AgentCore Gateway with Cognito JWT auth.
  - Verify exactly 4 targets and 15 live MCP tools.
  - Render AgentCore runtime templates.
  - Deploy Runtime via @aws/agentcore CLI.
  - Emit one JSON payload with managed endpoints + status.

Any failure exits non-zero so bootstrap can fail readiness gates.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import boto3


EXPECTED_TARGETS = {
    "search": {
        "target_name": "pellier-discovery-search-target",
        "handler": "pellier_search_server.lambda_handler",
        "server_name": "pellier-search-server",
        "entrypoint": "scripts/deploy/pellier_search_server.py",
    },
    "pricing": {
        "target_name": "pellier-value-pricing-target",
        "handler": "pellier_pricing_server.lambda_handler",
        "server_name": "pellier-pricing-server",
        "entrypoint": "scripts/deploy/pellier_pricing_server.py",
    },
    "recommendation": {
        "target_name": "pellier-curation-recommendation-target",
        "handler": "pellier_recommend_server.lambda_handler",
        "server_name": "pellier-recommend-server",
        "entrypoint": "scripts/deploy/pellier_recommend_server.py",
    },
    "experience": {
        "target_name": "pellier-concierge-experience-target",
        "handler": "pellier_experience_server.lambda_handler",
        "server_name": "pellier-experience-server",
        "entrypoint": "scripts/deploy/pellier_experience_server.py",
    },
}

EXPECTED_TOOL_NAMES = {
    "search": [
        "find_pieces",
        "find_pieces_hybrid",
        "explore_collection",
        "floor_check",
        "running_low",
        "restock_shelf",
    ],
    "pricing": [
        "price_intelligence",
        "side_by_side",
    ],
    "recommendation": [
        "preference_snapshot",
        "trace_receipt",
        "whats_trending",
        "returns_and_care",
        "style_match",
    ],
    "experience": [
        "process_return",
        "escalate_to_stylist",
    ],
}

RUNTIME_ROLE_NAME = "pellier-agentcore-runtime-execution"
RUNTIME_ROLE_MANAGED_POLICIES = (
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
)


def _region_from_arn(arn: str, fallback: str) -> str:
    match = re.match(r"^arn:[^:]+:[^:]+:([^:]+):", arn or "")
    return match.group(1) if match else fallback


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def _parse_runtime_arn(stdout: str, stderr: str) -> str:
    for blob in (stdout, stderr):
        for line in blob.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            for key in ("runtimeArn", "agentRuntimeArn", "arn"):
                if isinstance(payload.get(key), str):
                    return payload[key]
            runtimes = payload.get("runtimes")
            if isinstance(runtimes, list):
                for runtime in runtimes:
                    if not isinstance(runtime, dict):
                        continue
                    for key in ("arn", "runtimeArn", "agentRuntimeArn"):
                        if isinstance(runtime.get(key), str):
                            return runtime[key]
    combined = f"{stdout}\n{stderr}"
    match = re.search(
        r"(arn:aws[a-z-]*:bedrock-agentcore:[^:\s]+:\d+:runtime/[a-zA-Z0-9_-]+)",
        combined,
    )
    if match:
        return match.group(1)
    raise RuntimeError("Runtime deploy succeeded but runtime ARN was not found in output")


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _ensure_execution_role_arn(region: str) -> str:
    """Return the Runtime execution role ARN, creating the standalone role if needed.

    Workshop Studio can pass AGENTCORE_ROLE_ARN from infrastructure outputs. For
    local/event dry runs, the participant role's iam_policy.json allows creating
    and passing ``pellier-agentcore-runtime-*`` roles, so the provisioner should
    recover instead of failing on an empty env var.
    """
    existing = (
        os.environ.get("AGENTCORE_ROLE_ARN", "").strip()
        or os.environ.get("AGENTCORE_EXECUTION_ROLE_ARN", "").strip()
    )
    if existing:
        return existing

    from botocore.exceptions import ClientError

    iam = boto3.client("iam", region_name=region)
    try:
        role_arn = iam.get_role(RoleName=RUNTIME_ROLE_NAME)["Role"]["Arn"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise
        trust = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        role_arn = iam.create_role(
            RoleName=RUNTIME_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description="Pellier AgentCore Runtime execution role (workshop)",
        )["Role"]["Arn"]

    for policy_arn in RUNTIME_ROLE_MANAGED_POLICIES:
        iam.attach_role_policy(RoleName=RUNTIME_ROLE_NAME, PolicyArn=policy_arn)
    return role_arn


def _compute_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    digest = hmac.new(
        client_secret.encode("utf-8"),
        msg=f"{username}{client_id}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _ensure_data_api_enabled(region: str, db_cluster_arn: str) -> None:
    """Pre-flight: the four MCP Lambdas reach Aurora EXCLUSIVELY through
    rds-data, so a cluster without the Data API deploys everything green and
    then dies at the FIRST tool SQL with HttpEndpointNotEnabledException —
    surfaced to participants only as the agent's vague "temporary database
    issue" (box-verified 2026-06-12). The WS template now sets
    EnableHttpEndpoint: true on the DBCluster; this guard heals older stacks
    and fails LOUDLY instead of letting the gap hide behind polite prose.

    The enable flip is ASYNC: enable-http-endpoint returns success while
    describe keeps reporting false for ~15s — so poll, never fire-and-check.
    """
    import time

    rds = boto3.client("rds", region_name=region)
    cluster_id = db_cluster_arn.rsplit(":", 1)[-1]

    def _enabled() -> bool:
        out = rds.describe_db_clusters(DBClusterIdentifier=cluster_id)
        return bool(out["DBClusters"][0].get("HttpEndpointEnabled"))

    if _enabled():
        return

    print(f"Data API disabled on {cluster_id} — enabling (template drift heal)...")
    rds.enable_http_endpoint(ResourceArn=db_cluster_arn)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        time.sleep(5)
        if _enabled():
            # Settle margin: the describe flip precedes full data-plane
            # readiness by a few seconds on a cold cluster.
            time.sleep(10)
            return
    raise RuntimeError(
        f"Aurora Data API still disabled on {cluster_id} 120s after "
        "enable-http-endpoint. Every Gateway tool call would fail with "
        "HttpEndpointNotEnabledException. Check EnableHttpEndpoint: true on "
        "the DBCluster in pellier-database.yml and the instance role's "
        "rds:EnableHttpEndpoint/rds:DescribeDBClusters grant."
    )


def _cognito_access_token(
    region: str,
    user_pool_id: str,
    client_id: str,
    creds_secret_arn: str,
    client_secret_arn: str | None,
) -> tuple[str, str]:
    sm = boto3.client("secretsmanager", region_name=region)
    cognito = boto3.client("cognito-idp", region_name=region)

    creds_raw = sm.get_secret_value(SecretId=creds_secret_arn).get("SecretString", "")
    creds = json.loads(creds_raw) if creds_raw else {}
    users = creds.get("users", [])
    if not users:
        raise RuntimeError("Cognito test credentials secret has no users array")

    user0 = users[0]
    username = user0.get("username", "")
    password = user0.get("password", "")
    if not username or not password:
        raise RuntimeError("Cognito test credentials secret is missing username/password")

    auth_params: dict[str, str] = {"USERNAME": username, "PASSWORD": password}
    if client_secret_arn:
        client_secret_raw = sm.get_secret_value(SecretId=client_secret_arn).get("SecretString", "")
        client_secret_payload = json.loads(client_secret_raw) if client_secret_raw else {}
        client_secret = client_secret_payload.get("client_secret", "")
        if client_secret:
            auth_params["SECRET_HASH"] = _compute_secret_hash(username, client_id, client_secret)

    auth = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters=auth_params,
    )
    access_token = auth.get("AuthenticationResult", {}).get("AccessToken")
    if not access_token:
        raise RuntimeError("Failed to obtain Cognito access token for managed proof")
    return access_token, username


def _discover_live_gateway_tools(
    *,
    deploy_dir: Path,
    gateway_url: str,
    access_token: str,
) -> dict[str, Any]:
    """Require the authenticated MCP discovery surface to match all 15 tools."""
    deploy_path = str(deploy_dir)
    if deploy_path not in sys.path:
        sys.path.insert(0, deploy_path)
    from test_gateway_tools import discover_gateway_tools

    tools = discover_gateway_tools(gateway_url, access_token)
    full_names = sorted(str(tool.name) for tool in tools)
    canonical_names = {name.rsplit("__", 1)[-1] for name in full_names}
    expected_names = {
        name
        for names in EXPECTED_TOOL_NAMES.values()
        for name in names
    }
    missing = sorted(expected_names - canonical_names)
    unexpected = sorted(canonical_names - expected_names)
    if len(tools) != 15 or missing or unexpected:
        details = [f"observed {len(tools)} tools, expected 15"]
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected: " + ", ".join(unexpected))
        raise RuntimeError(
            "Live Gateway MCP discovery does not match the canonical contract ("
            + "; ".join(details)
            + ")"
        )
    return {
        "count": len(tools),
        "canonical_names": sorted(canonical_names),
        "prefixed_names": full_names,
    }


def _authenticated_runtime_smoke(
    *,
    region: str,
    runtime_arn: str,
    access_token: str,
    username: str,
) -> dict[str, Any]:

    # CUSTOM_JWT runtimes are invoked over the raw HTTPS data plane with the
    # Cognito token as a Bearer header (the transport behind dat403's
    # `agentcore invoke --bearer-token`). boto3 is the WRONG door here:
    # there is no "bedrock-agentcore-runtime" service name (box-verified
    # 2026-06-12 — provisioning died on it AFTER everything deployed), and the
    # real client's invoke_agent_runtime has no authToken param at all (it
    # SigV4-signs, which a JWT-gated runtime rejects).
    runtime_id = runtime_arn.rsplit("/", 1)[-1]
    payload = json.dumps(
        {
            "prompt": "Smoke test: find one linen item under 150.",
            "session_id": "builders-smoke-session",
        }
    )
    escaped_arn = urllib.parse.quote(runtime_arn, safe="")
    url = (
        f"https://bedrock-agentcore.{region}.amazonaws.com"
        f"/runtimes/{escaped_arn}/invocations?qualifier=DEFAULT"
    )
    request = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            # The runtime keys its session off this header; reuse one id so
            # re-runs don't fan out sessions. Must be >= 33 chars.
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": "builders-smoke-session-0000000000000001",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"Runtime smoke invoke HTTP {err.code}: {detail}"
        ) from err
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = {"response": raw}
    response_text = str(decoded.get("response", "")).strip()
    if not response_text:
        raise RuntimeError("Runtime smoke invoke returned empty response payload")
    rail = str(decoded.get("rail", "")).strip()
    if rail != "gateway-mcp":
        raise RuntimeError(
            "Runtime smoke did not execute through AgentCore Gateway "
            f"(expected rail=gateway-mcp, got {rail or 'missing'})"
        )

    return {
        "runtime_id": runtime_id,
        "username": username,
        "rail": rail,
        "response_preview": response_text[:200],
    }


def _live_policy_proof(
    *,
    repo: Path,
    deploy_dir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    """Execute one real Gateway ALLOW and one real Cedar DENY."""
    helper = deploy_dir / "gateway_process_return.py"
    proofs: dict[str, Any] = {}
    cases = (
        ("allow", "damaged", "provision-policy-allow"),
        ("deny", "changed_mind", "provision-policy-deny"),
    )
    for expected, reason, session_id in cases:
        proc = _run(
            [
                sys.executable,
                str(helper),
                "--product-id",
                "31",
                "--reason",
                reason,
                "--expect",
                expected,
                "--record-receipt",
                "--session-id",
                session_id,
            ],
            cwd=repo,
            env=env,
        )
        payload = json.loads(proc.stdout)
        if payload.get("outcome") != expected:
            raise RuntimeError(
                f"Live Policy {expected.upper()} proof returned "
                f"{payload.get('outcome') or 'no outcome'}"
            )
        if expected == "allow" and payload.get("tool_audit_row_after_call") is None:
            raise RuntimeError("Live Policy ALLOW produced no execution audit row")
        if expected == "deny" and (
            payload.get("tool_audit_row_after_call") is not None
            or payload.get("cedar_denial") is not True
        ):
            raise RuntimeError("Live Policy DENY did not prove pre-execution blocking")
        proofs[expected] = payload
    return proofs


# The @aws/agentcore CLI is pinned. @latest drifted from a flat-config
# `deploy` (which read agentcore.json + aws-targets.json directly) to a
# stateful, CDK-based project model (create -> add -> deploy). Pinning a
# known-good version keeps every fresh participant account on identical,
# tested CLI behavior instead of whatever @latest resolves to mid-event.
AGENTCORE_CLI = "@aws/agentcore@0.18.0"

# Allowed JSON-Schema-ish runtimeVersion values the CLI accepts. The CLI
# defaults to PYTHON_3_14, which the CodeZip build / Lambda runtime may not
# support yet — pin to a known-supported line.
RUNTIME_PYTHON_VERSION = "PYTHON_3_12"


def _agentcore_project_paths(backend_dir: Path) -> tuple[Path, Path]:
    """Return (project_root, agentcore_config_path) for the scaffolded 0.18
    project, rooted at REPO level — NEVER inside backend_dir. The CodeZip
    packager copies the whole code-location (backend_dir) into
    <project>/agentcore/.cache/<agent>/staging at synth time; a project rooted
    inside the code-location therefore copies ITSELF recursively until mkdir
    dies with ENAMETOOLONG (box-verified 2026-06-12). The packager's exclusion
    list is hard-coded (.git/.venv/__pycache__/.pytest_cache/.DS_Store/
    node_modules — @aws/agentcore-cdk packaging/helpers.js), so the only fix is
    rooting the project outside the tree being packaged."""
    repo_root = backend_dir.parent.parent  # <repo>/pellier/backend -> <repo>
    project_root = repo_root / ".agentcore-project" / "pellier"
    config_path = project_root / "agentcore" / "agentcore.json"
    return project_root, config_path


def _patch_agentcore_config(
    config_path: Path,
    *,
    runtime_name: str,
    execution_role_arn: str,
    env_vars: dict[str, str],
    account_id: str,
    region: str,
    discovery_url: str = "",
    allowed_client: str = "",
) -> None:
    """Inject the fields the 0.18 CLI has NO flags for — the execution role,
    envVars, a pinned runtimeVersion, networkMode, and the JWT header
    allowlist — into runtimes[<our agent>], and write aws-targets.json in the
    new ARRAY shape. `agentcore add agent` sets name/entrypoint/protocol via
    flags; everything here is the gap.

    Field spellings are taken from the WORKING dat403 reference
    (`modules/05/strands/deploy/setup_deploy.sh:90-113`), which hand-writes the
    full runtime object that `agentcore deploy` consumes:
      * ``roleArn`` — NOT ``executionRoleArn``. This is the single most
        important key: ``add agent`` has no role flag, so this patch is the
        ONLY thing that sets the runtime's execution role. dat403's working
        config uses ``roleArn``; a wrong key deploys a runtime with no role and
        every Bedrock call fails at invoke.
      * ``networkMode: "PUBLIC"`` — dat403 sets it explicitly; don't rely on a
        CLI default.
      * ``requestHeaderAllowlist: ["Authorization"]`` — required for the runtime
        to forward the Cognito JWT inward.

    Defensive by design: match the runtime object by name with a single-runtime
    fallback, and only SET our fields (never strip what the CLI added). We also
    re-assert the CUSTOM_JWT authorizer block in dat403's proven shape if the
    add-agent flags didn't populate it."""
    if not config_path.is_file():
        raise RuntimeError(
            f"agentcore.json not found at {config_path} — `agentcore create`/`add agent` did not scaffold it"
        )
    config = json.loads(config_path.read_text())
    runtimes = config.get("runtimes")
    if not isinstance(runtimes, list) or not runtimes:
        raise RuntimeError(
            f"agentcore.json has no runtimes[] to patch (found: {type(runtimes).__name__}); "
            "`agentcore add agent` likely failed"
        )

    target = None
    for rt in runtimes:
        if isinstance(rt, dict) and rt.get("name") == runtime_name:
            target = rt
            break
    if target is None:
        if len(runtimes) == 1 and isinstance(runtimes[0], dict):
            target = runtimes[0]  # single-runtime project: unambiguous
        else:
            names = [rt.get("name") for rt in runtimes if isinstance(rt, dict)]
            raise RuntimeError(
                f"Could not find runtime '{runtime_name}' to patch in {names}"
            )

    # roleArn (NOT executionRoleArn) — matches dat403's working config.
    target["roleArn"] = execution_role_arn
    target["runtimeVersion"] = RUNTIME_PYTHON_VERSION
    target["networkMode"] = "PUBLIC"
    target["requestHeaderAllowlist"] = ["Authorization"]
    target["envVars"] = [{"name": k, "value": v} for k, v in env_vars.items()]

    # Re-assert the CUSTOM_JWT authorizer in dat403's proven shape if add-agent
    # didn't populate it (the flag→JSON translation is the one thing dat403
    # can't confirm). Note the runtime SDK uses lowercase-j `customJwtAuthorizer`
    # (the Gateway API uses caps `customJWTAuthorizer` — different surfaces).
    if discovery_url and allowed_client and not target.get("authorizerConfiguration"):
        target["authorizerType"] = "CUSTOM_JWT"
        target["authorizerConfiguration"] = {
            "customJwtAuthorizer": {
                "discoveryUrl": discovery_url,
                "allowedClients": [allowed_client],
            }
        }

    config_path.write_text(json.dumps(config, indent=2))

    # aws-targets.json is an ARRAY in 0.18 ([{name,account,region}]) and no
    # longer carries the execution role (that conflation is gone).
    targets_path = config_path.parent / "aws-targets.json"
    targets_path.write_text(
        json.dumps(
            [{"name": "default", "account": account_id, "region": region}],
            indent=2,
        )
    )


def _extract_runtime_arn_from_state(project_root: Path) -> str | None:
    """Prefer the authoritative deployed-state file over scraping stdout.
    The 0.18 CLI records the deployed runtime ARN in agentcore/.cli/
    deployed-state.json. Returns None if absent/unparseable so the caller can
    fall back to _parse_runtime_arn."""
    state_path = project_root / "agentcore" / ".cli" / "deployed-state.json"
    if not state_path.is_file():
        return None
    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    # Field name is agentRuntimeArn per the probed schema; search defensively
    # for any runtime ARN-shaped value in case the key differs across minors.
    def _find_arn(node: Any) -> str | None:
        if isinstance(node, str):
            if re.fullmatch(
                r"arn:aws[a-z-]*:bedrock-agentcore:[^:\s]+:\d+:runtime/[A-Za-z0-9_-]+",
                node,
            ):
                return node
            return None
        if isinstance(node, dict):
            # Prefer the documented key first.
            for key in ("agentRuntimeArn", "runtimeArn", "arn"):
                val = node.get(key)
                if isinstance(val, str) and val.startswith("arn:"):
                    return val
            for val in node.values():
                found = _find_arn(val)
                if found:
                    return found
        if isinstance(node, list):
            for item in node:
                found = _find_arn(item)
                if found:
                    return found
        return None

    return _find_arn(state)


def _deploy_runtime_via_cli(
    *,
    backend_dir: Path,
    runtime_name: str,
    region: str,
    account_id: str,
    cognito_pool: str,
    cognito_client: str,
    execution_role_arn: str,
    gateway_url: str,
    model_id: str,
    deploy_env: dict[str, str],
) -> str:
    """Scaffold a 0.18 AgentCore project, register our in-repo orchestrator as
    a BYO agent (HTTP + CUSTOM_JWT), patch in the role/envVars the CLI can't set
    via flags, and `agentcore deploy` (CDK). Returns the deployed runtime ARN.

    Idempotent: skips `create` if the project exists, and re-adds the agent
    cleanly so a re-run (facilitator recovery) doesn't error on a duplicate."""
    project_root, config_path = _agentcore_project_paths(backend_dir)
    output_dir = project_root.parent  # `create` writes <output_dir>/<project>/
    # Only ensure the PARENT (.agentcore-project) exists – do NOT pre-create
    # project_root (.agentcore-project/pellier). `agentcore create` scaffolds
    # that folder itself and ABORTS if it already exists ("A folder named
    # 'pellier' already exists in this directory"). Pre-creating it here (the
    # old `project_root.mkdir`) defeated the `config_path.is_file()` skip-guard
    # below: the empty dir had no agentcore.json, so the guard said "create"
    # while the CLI refused the existing folder → Runtime never deployed.
    output_dir.mkdir(parents=True, exist_ok=True)

    # Purge any LEGACY project an older script version rooted INSIDE the
    # code-location (backend_dir/.agentcore-project). The CodeZip packager
    # copies backend_dir wholesale, so a stale tree there — possibly holding
    # a deep recursive .cache from the self-copy bug — would be packaged into
    # every zip or re-trigger ENAMETOOLONG at staging. Re-runs on a box
    # provisioned by the old version must recover in place.
    legacy_root = backend_dir / ".agentcore-project"
    if legacy_root.exists():
        shutil.rmtree(legacy_root, ignore_errors=True)

    discovery_url = (
        f"https://cognito-idp.{region}.amazonaws.com/{cognito_pool}/.well-known/openid-configuration"
    )

    # 1. Scaffold an EMPTY project (no agent) so we can BYO ours. Skip if the
    #    project already exists AND is complete (re-run safety). If project_root
    #    exists but has no agentcore.json, a prior `create` died partway (or
    #    something pre-created the dir): the CLI would abort with "folder already
    #    exists", so clear the incomplete dir first and let create scaffold clean.
    if not config_path.is_file():
        if project_root.exists():
            shutil.rmtree(project_root, ignore_errors=True)
        _run(
            [
                "npx", "-y", AGENTCORE_CLI, "create",
                "--project-name", "pellier",
                "--no-agent",
                "--defaults",
                "--build", "CodeZip",
                "--language", "Python",
                "--framework", "Strands",
                "--model-provider", "Bedrock",
                "--protocol", "HTTP",
                "--skip-git",
                "--skip-python-setup",
                # NOTE: do NOT pass --skip-install. The 0.18 CLI scaffolds a
                # TypeScript CDK app (agentcore-cdk-app) and `deploy` compiles
                # it with `tsc`, which needs that app's node_modules
                # (aws-cdk-lib, constructs, @aws/agentcore-cdk, @types/node).
                # --skip-install skips the npm install for it → deploy fails
                # with TS2307 "Cannot find module 'aws-cdk-lib'" etc. We keep
                # --skip-python-setup because the agent is BYO Python (our own
                # backend venv); only the CDK app's Node deps must install.
                "--output-dir", str(output_dir),
                "--json",
            ],
            cwd=output_dir,
            env=deploy_env,
        )

    # 2. Register our existing orchestrator entrypoint as a BYO agent with the
    #    real CUSTOM_JWT authorizer. Remove first so a re-run is clean (the CLI
    #    errors on a duplicate agent name); ignore remove failure when absent.
    try:
        _run(
            ["npx", "-y", AGENTCORE_CLI, "remove", "agent", "--name", runtime_name, "--yes"],
            cwd=project_root,
            env=deploy_env,
        )
    except RuntimeError:
        pass  # agent not present yet — expected on first run

    _run(
        [
            "npx", "-y", AGENTCORE_CLI, "add", "agent",
            "--name", runtime_name,
            "--type", "byo",
            "--build", "CodeZip",
            "--language", "Python",
            "--framework", "Strands",
            "--model-provider", "Bedrock",
            "--protocol", "HTTP",
            "--code-location", str(backend_dir),
            "--entrypoint", "agentcore_runtime.py",
            "--authorizer-type", "CUSTOM_JWT",
            "--discovery-url", discovery_url,
            "--allowed-clients", cognito_client,
            "--json",
        ],
        cwd=project_root,
        env=deploy_env,
    )

    # 3. Patch in roleArn + envVars + runtimeVersion + networkMode +
    #    requestHeaderAllowlist (no CLI flags for these), re-assert the JWT
    #    authorizer if needed, and write aws-targets.json (array shape).
    _patch_agentcore_config(
        config_path,
        runtime_name=runtime_name,
        execution_role_arn=execution_role_arn,
        # Both names on purpose: config.py reads AGENTCORE_GATEWAY_URL (the
        # name the backend/tests standardize on); MCP_GATEWAY_URL is the
        # legacy/deploy-script name the entrypoint also bridges. Without the
        # config-visible name the governed Runtime fails closed because its
        # managed Gateway rail is unavailable.
        env_vars={
            "MCP_GATEWAY_URL": gateway_url,
            "AGENTCORE_GATEWAY_URL": gateway_url,
            "AGENT_MODEL_ID": model_id,
            # The deployed entrypoint imports services.agentcore_gateway,
            # which reads this Settings field rather than AGENT_MODEL_ID.
            "BEDROCK_ROUTER_MODEL": model_id,
        },
        account_id=account_id,
        region=region,
        discovery_url=discovery_url,
        allowed_client=cognito_client,
    )

    # 3.5 Self-heal the CDK app's node_modules. `deploy` compiles agentcore/cdk
    #     with `npm run build` (tsc) but NEVER installs its deps — only `create`
    #     does. A project scaffolded by an older script version (which passed
    #     --skip-install) is skipped by the create-guard above and would fail
    #     tsc forever with TS2307 "Cannot find module 'aws-cdk-lib'". Detect the
    #     missing install and run it ourselves so re-runs recover in place.
    cdk_dir = project_root / "agentcore" / "cdk"
    if cdk_dir.is_dir() and not (cdk_dir / "node_modules" / "aws-cdk-lib").is_dir():
        _run(["npm", "install"], cwd=cdk_dir, env=deploy_env)

    # 4. Deploy (CDK) from the PROJECT ROOT (the dir containing agentcore/).
    runtime_deploy = _run(
        ["npx", "-y", AGENTCORE_CLI, "deploy", "-y", "--json"],
        cwd=project_root,
        env=deploy_env,
    )

    # 5. Prefer the authoritative deployed-state file; fall back to scraping.
    return _extract_runtime_arn_from_state(project_root) or _parse_runtime_arn(
        runtime_deploy.stdout, runtime_deploy.stderr
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision full AgentCore managed path for builders")
    parser.add_argument("--repo-path", default=os.environ.get("REPO_PATH", "."))
    parser.add_argument("--gateway-name", default="pellier-gateway")
    parser.add_argument("--runtime-name", default="pellier_orchestrator")
    parser.add_argument("--output-json", default="/tmp/pellier-agentcore-managed.json")
    args = parser.parse_args()

    repo = Path(args.repo_path).resolve()
    backend_dir = repo / "pellier" / "backend"
    deploy_dir = repo / "scripts" / "deploy"
    output_path = Path(args.output_json)

    region = _require_env("AWS_REGION")
    required = {
        "AWS_REGION": region,
        "DB_CLUSTER_ARN": _require_env("DB_CLUSTER_ARN"),
        "DB_SECRET_ARN": _require_env("DB_SECRET_ARN"),
        "COGNITO_POOL": _require_env("COGNITO_POOL"),
        "COGNITO_CLIENT": _require_env("COGNITO_CLIENT"),
        "AGENTCORE_ROLE_ARN": _ensure_execution_role_arn(region),
        "COGNITO_TEST_CREDENTIALS_SECRET_ARN": _require_env("COGNITO_TEST_CREDENTIALS_SECRET_ARN"),
        "WORKSHOP_ID": _require_env("WORKSHOP_ID"),
        "AGENT_MODEL_ID": _require_env("AGENT_MODEL_ID"),
    }
    db_region = os.environ.get("DB_REGION", "").strip() or _region_from_arn(
        required["DB_CLUSTER_ARN"],
        required["AWS_REGION"],
    )
    client_secret_arn = os.environ.get("COGNITO_CLIENT_SECRET_ARN", "").strip() or None
    db_name = os.environ.get("DB_NAME", "pellier")
    model_id = required["AGENT_MODEL_ID"]

    result: dict[str, Any] = {
        "status": "failed",
        "region": required["AWS_REGION"],
        "gateway_name": args.gateway_name,
        "runtime_name": args.runtime_name,
        "lambdas": {},
        "gateway": {},
        "runtime": {},
        "verification": {"targets_attached": False},
    }

    try:
        _ensure_data_api_enabled(db_region, required["DB_CLUSTER_ARN"])

        lambda_arns: dict[str, str] = {}
        for surface, cfg in EXPECTED_TARGETS.items():
            cmd = [
                "python3",
                str(deploy_dir / "deploy_lambda.py"),
                "--region",
                required["AWS_REGION"],
                "--server-name",
                cfg["server_name"],
                "--db-cluster-arn",
                required["DB_CLUSTER_ARN"],
                "--db-region",
                db_region,
                "--secret-arn",
                required["DB_SECRET_ARN"],
                "--database",
                db_name,
                "--mcp-server-path",
                str(repo / cfg["entrypoint"]),
                "--handler",
                cfg["handler"],
            ]
            _run(cmd, cwd=repo)

            # deploy_lambda.py creates the function as f"{server_name}-function"
            # (e.g. pellier-search-server-function), NOT target_name (which is
            # the Gateway *target* alias, e.g. pellier-discovery-search-target).
            # Look it up by its real function name or get-function 404s and the
            # whole provision marks failed.
            function_name = f"{cfg['server_name']}-function"
            get_fn = _run(
                [
                    "aws",
                    "lambda",
                    "get-function",
                    "--function-name",
                    function_name,
                    "--region",
                    required["AWS_REGION"],
                    "--query",
                    "Configuration.FunctionArn",
                    "--output",
                    "text",
                ],
                cwd=repo,
            )
            arn = get_fn.stdout.strip()
            lambda_arns[surface] = arn
            result["lambdas"][surface] = {"function_arn": arn, "function_name": cfg["target_name"]}

        gateway_cmd = [
            "python3",
            str(deploy_dir / "deploy_gateway.py"),
            "--region",
            required["AWS_REGION"],
            "--gateway-name",
            args.gateway_name,
            "--search-lambda-arn",
            lambda_arns["search"],
            "--pricing-lambda-arn",
            lambda_arns["pricing"],
            "--recommendation-lambda-arn",
            lambda_arns["recommendation"],
            "--experience-lambda-arn",
            lambda_arns["experience"],
            "--cognito-user-pool-id",
            required["COGNITO_POOL"],
            "--cognito-client-id",
            required["COGNITO_CLIENT"],
        ]
        _run(gateway_cmd, cwd=repo)

        gateway_id_proc = _run(
            [
                "aws",
                "bedrock-agentcore-control",
                "list-gateways",
                "--region",
                required["AWS_REGION"],
                "--query",
                f"items[?name=='{args.gateway_name}'].gatewayId | [0]",
                "--output",
                "text",
            ],
            cwd=repo,
        )
        gateway_id = gateway_id_proc.stdout.strip()
        if not gateway_id or gateway_id == "None":
            raise RuntimeError(f"Gateway id not found for name {args.gateway_name}")

        gateway_url_proc = _run(
            [
                "aws",
                "bedrock-agentcore-control",
                "get-gateway",
                "--gateway-identifier",
                gateway_id,
                "--region",
                required["AWS_REGION"],
                "--query",
                "gatewayUrl",
                "--output",
                "text",
            ],
            cwd=repo,
        )
        gateway_url = gateway_url_proc.stdout.strip()
        result["gateway"] = {
            "gateway_id": gateway_id,
            "gateway_url": gateway_url,
        }

        targets_proc = _run(
            [
                "aws",
                "bedrock-agentcore-control",
                "list-gateway-targets",
                "--gateway-identifier",
                gateway_id,
                "--region",
                required["AWS_REGION"],
                "--output",
                "json",
            ],
            cwd=repo,
        )
        target_payload = json.loads(targets_proc.stdout)
        attached = {item.get("name") for item in target_payload.get("items", [])}
        expected = {cfg["target_name"] for cfg in EXPECTED_TARGETS.values()}
        missing_targets = sorted(expected - attached)
        unexpected_targets = sorted(attached - expected)
        if len(attached) != 4 or missing_targets or unexpected_targets:
            details = [f"observed {len(attached)} targets, expected 4"]
            if missing_targets:
                details.append("missing: " + ", ".join(missing_targets))
            if unexpected_targets:
                details.append("unexpected: " + ", ".join(unexpected_targets))
            raise RuntimeError(
                "Gateway target set does not match the canonical contract ("
                + "; ".join(details)
                + ")"
            )
        result["verification"]["targets_attached"] = True
        result["verification"]["target_count"] = len(attached)
        result["verification"]["target_names"] = sorted(attached)

        prefixed_expected: list[str] = []
        prefixed_observed: set[str] = set()
        for surface, cfg in EXPECTED_TARGETS.items():
            for name in EXPECTED_TOOL_NAMES[surface]:
                prefixed_expected.append(f"{cfg['target_name']}__{name}")

        for item in target_payload.get("items", []):
            target_name = item.get("name")
            target_id = item.get("targetId")
            if not target_name or not target_id:
                continue
            target_detail_proc = _run(
                [
                    "aws",
                    "bedrock-agentcore-control",
                    "get-gateway-target",
                    "--gateway-identifier",
                    gateway_id,
                    # NOTE: get-gateway-target uses the SHORT form --target-id
                    # (not --target-identifier like the gateway arg). The AWS
                    # CLI is inconsistent here; --target-identifier raises
                    # "ParamValidation: the following arguments are required:
                    # --target-id" and aborts after targets are already attached.
                    "--target-id",
                    target_id,
                    "--region",
                    required["AWS_REGION"],
                    "--output",
                    "json",
                ],
                cwd=repo,
            )
            target_detail = json.loads(target_detail_proc.stdout)
            inline_tools = (
                target_detail.get("targetConfiguration", {})
                .get("mcp", {})
                .get("lambda", {})
                .get("toolSchema", {})
                .get("inlinePayload", [])
            )
            for tool in inline_tools:
                tool_name = tool.get("name")
                if isinstance(tool_name, str) and tool_name:
                    prefixed_observed.add(f"{target_name}__{tool_name}")

        expected_prefixed = set(prefixed_expected)
        missing_prefixed = sorted(expected_prefixed - prefixed_observed)
        unexpected_prefixed = sorted(prefixed_observed - expected_prefixed)
        if (
            len(prefixed_observed) != 15
            or missing_prefixed
            or unexpected_prefixed
        ):
            details = [
                f"observed {len(prefixed_observed)} schema tools, expected 15"
            ]
            if missing_prefixed:
                details.append("missing: " + ", ".join(missing_prefixed))
            if unexpected_prefixed:
                details.append("unexpected: " + ", ".join(unexpected_prefixed))
            raise RuntimeError(
                "Gateway tool schema does not match the canonical contract ("
                + "; ".join(details)
                + ")"
            )
        result["verification"]["prefixed_tools_verified"] = True
        result["verification"]["prefixed_tool_count"] = len(prefixed_observed)
        result["verification"]["prefixed_tools"] = sorted(prefixed_observed)

        access_token, smoke_username = _cognito_access_token(
            region=required["AWS_REGION"],
            user_pool_id=required["COGNITO_POOL"],
            client_id=required["COGNITO_CLIENT"],
            creds_secret_arn=required["COGNITO_TEST_CREDENTIALS_SECRET_ARN"],
            client_secret_arn=client_secret_arn,
        )
        live_gateway = _discover_live_gateway_tools(
            deploy_dir=deploy_dir,
            gateway_url=gateway_url,
            access_token=access_token,
        )
        result["verification"]["gateway_tools_discovered"] = True
        result["verification"]["gateway_tool_count"] = live_gateway["count"]
        result["verification"]["gateway_tool_names"] = live_gateway[
            "canonical_names"
        ]
        result["verification"]["gateway_prefixed_tool_names"] = live_gateway[
            "prefixed_names"
        ]

        account_proc = _run(
            ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
            cwd=repo,
        )
        account_id = account_proc.stdout.strip()

        deploy_env = os.environ.copy()
        deploy_env["AWS_REGION"] = required["AWS_REGION"]
        deploy_env["AWS_DEFAULT_REGION"] = required["AWS_REGION"]

        # Managed AgentCore Policy (the 4th pillar): create a Cedar policy
        # engine, gate process_return to damaged-only, and attach to THIS
        # gateway in ENFORCE mode. Policy enforces at the Gateway boundary, so
        # it gates the agents_as_tools rail (process_return runs in the
        # experience Lambda). This is a hard readiness requirement for the
        # governed workshop: Lab 5 cannot run without it.
        try:
            gateway_arn_proc = _run(
                [
                    "aws", "bedrock-agentcore-control", "get-gateway",
                    "--gateway-identifier", gateway_id,
                    "--region", required["AWS_REGION"],
                    "--query", "gatewayArn", "--output", "text",
                ],
                cwd=repo,
            )
            gateway_arn = gateway_arn_proc.stdout.strip()
            result["gateway"]["gateway_arn"] = gateway_arn
            policy_proc = _run(
                [
                    "python3", str(deploy_dir / "deploy_policy.py"),
                    "--gateway-id", gateway_id,
                    "--gateway-arn", gateway_arn,
                    "--region", required["AWS_REGION"],
                    "--mode", "ENFORCE",
                ],
                cwd=repo,
                env=deploy_env,
            )
            policy_engine_id = ""
            for line in policy_proc.stdout.splitlines():
                if line.startswith("POLICY_ENGINE_ID="):
                    policy_engine_id = line.split("=", 1)[1].strip()
            if not policy_engine_id:
                raise RuntimeError(
                    "Managed Policy deploy completed without a policy engine id"
                )
            result["policy"] = {
                "policy_engine_id": policy_engine_id,
                "mode": "ENFORCE",
                "gated_tool": "process_return",
            }
            result["verification"]["managed_policy_attached"] = bool(policy_engine_id)

            policy_state_proc = _run(
                [
                    "aws",
                    "bedrock-agentcore-control",
                    "get-gateway",
                    "--gateway-identifier",
                    gateway_id,
                    "--region",
                    required["AWS_REGION"],
                    "--output",
                    "json",
                ],
                cwd=repo,
            )
            policy_state = json.loads(policy_state_proc.stdout)
            current_mode = (
                policy_state.get("policyEngineConfiguration", {}).get("mode")
            )
            if current_mode != "ENFORCE":
                raise RuntimeError(
                    f"Gateway Policy mode is {current_mode or 'missing'}, expected ENFORCE"
                )

            proof_env = deploy_env.copy()
            proof_env["AGENTCORE_GATEWAY_URL"] = gateway_url
            proof_env["AGENTCORE_GATEWAY_ARN"] = gateway_arn
            proof_env["AGENTCORE_POLICY_ENGINE_ID"] = policy_engine_id
            proof_env["PELLIER_TOKEN"] = access_token
            live_policy = _live_policy_proof(
                repo=repo,
                deploy_dir=deploy_dir,
                env=proof_env,
            )
            result["verification"]["live_policy_allow"] = True
            result["verification"]["live_policy_deny"] = True
            result["verification"]["live_policy_proof"] = live_policy
        except RuntimeError as exc:
            result["policy"] = {"error": str(exc)}
            result["verification"]["managed_policy_attached"] = False
            raise RuntimeError(
                "Managed AgentCore Policy is required but failed to attach"
            ) from exc

        # Scaffold the 0.18 project, register our in-repo orchestrator as a BYO
        # agent (HTTP + CUSTOM_JWT), patch in the role/envVars the CLI has no
        # flags for, and CDK-deploy. Returns the deployed runtime ARN.
        runtime_arn = _deploy_runtime_via_cli(
            backend_dir=backend_dir,
            runtime_name=args.runtime_name,
            region=required["AWS_REGION"],
            account_id=account_id,
            cognito_pool=required["COGNITO_POOL"],
            cognito_client=required["COGNITO_CLIENT"],
            execution_role_arn=required["AGENTCORE_ROLE_ARN"],
            gateway_url=gateway_url,
            model_id=model_id,
            deploy_env=deploy_env,
        )
        # Record the deployed resource immediately. Later control-plane checks
        # or smoke invocation may fail, but operators still need the ARN to
        # inspect and recover the READY Runtime.
        result["runtime"] = {
            "runtime_arn": runtime_arn,
            "agent_model_id": model_id,
            "mcp_gateway_url": gateway_url,
        }

        runtime_lookup_proc = _run(
            [
                "aws",
                "bedrock-agentcore-control",
                "list-agent-runtimes",
                "--region",
                required["AWS_REGION"],
                "--output",
                "json",
            ],
            cwd=repo,
        )
        runtime_lookup = json.loads(runtime_lookup_proc.stdout)
        runtime_items = runtime_lookup.get("agentRuntimes", [])
        # The Node CLI prefixes the deployed runtime name with the project name
        # (dat403 changelog: e.g. "pellier_pellier_orchestrator-…"), so an exact
        # match can miss a successful deploy. Match exact first, then fall back
        # to substring. (The authoritative ARN already came from
        # deployed-state.json; this lookup is only a control-plane visibility
        # gate, so a too-strict match would hard-fail an otherwise-good deploy.)
        matched = [i for i in runtime_items if i.get("agentRuntimeName") == args.runtime_name]
        if not matched:
            matched = [
                i for i in runtime_items
                if args.runtime_name in (i.get("agentRuntimeName") or "")
            ]
        if not matched:
            raise RuntimeError(f"Runtime {args.runtime_name} not found in list-agent-runtimes")
        control = boto3.client(
            "bedrock-agentcore-control",
            region_name=required["AWS_REGION"],
        )
        control.tag_resource(
            resourceArn=runtime_arn,
            tags={
                "Project": "pellier",
                "PellierWorkshopId": required["WORKSHOP_ID"],
            },
        )
        runtime_status = matched[0].get("status") or matched[0].get("agentRuntimeStatus") or "UNKNOWN"
        result["verification"]["runtime_control_plane_visible"] = True
        result["verification"]["runtime_status"] = runtime_status

        try:
            smoke = _authenticated_runtime_smoke(
                region=required["AWS_REGION"],
                runtime_arn=runtime_arn,
                access_token=access_token,
                username=smoke_username,
            )
        except Exception as exc:
            result["status"] = "degraded"
            result["verification"]["authenticated_runtime_invoke_smoke"] = False
            result["verification"]["runtime_invoke_smoke_error"] = str(exc)
            output_path.write_text(json.dumps(result, indent=2))
            print(json.dumps(result), file=sys.stderr)
            return 1
        result["verification"]["authenticated_runtime_invoke_smoke"] = True
        result["verification"]["runtime_invoke_smoke"] = smoke

        required_verifications = (
            "targets_attached",
            "prefixed_tools_verified",
            "gateway_tools_discovered",
            "managed_policy_attached",
            "live_policy_allow",
            "live_policy_deny",
            "runtime_control_plane_visible",
            "authenticated_runtime_invoke_smoke",
        )
        missing = [
            name for name in required_verifications
            if result["verification"].get(name) is not True
        ]
        if missing:
            raise RuntimeError(
                "Managed readiness checks did not pass: " + ", ".join(missing)
            )
        result["status"] = "ready"

        output_path.write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
        return 0
    except Exception as exc:
        result["error"] = str(exc)
        output_path.write_text(json.dumps(result, indent=2))
        print(json.dumps(result), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
