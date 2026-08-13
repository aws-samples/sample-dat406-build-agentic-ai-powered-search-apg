#!/usr/bin/env python3
"""Provision and prove Pellier's managed AgentCore path.

AgentCore CLI is the only control-plane deployment path for Runtime, Memory,
Gateway, Gateway target registrations, AgentCore-managed service roles, Policy
engine, and Cedar policies. ``deploy_lambda.py`` owns the external Lambda
functions and their Lambda execution roles. The remaining Python/AWS SDK code
is limited to Aurora preflight, Memory data seeding, authentication, and
post-deploy proof.
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
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


DEPLOY_DIR = Path(__file__).resolve().parent / "deploy"
if str(DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(DEPLOY_DIR))

from gateway_tool_schemas import TOOL_SCHEMAS, schema_for  # noqa: E402
from render_agentcore_project import (  # noqa: E402
    AGENTCORE_CLI,
    GATEWAY_NAME,
    MEMORY_NAME,
    POLICY_ENGINE_NAME,
    PROCESS_RETURN_ACTION,
    PROJECT_NAME,
    RUNTIME_NAME,
    project_root,
    render_project,
)


EXPECTED_TARGETS = {
    "search": {
        "handler": "pellier_search_server.lambda_handler",
        "server_name": "pellier-search-server",
        "entrypoint": "scripts/deploy/pellier_search_server.py",
    },
    "pricing": {
        "handler": "pellier_pricing_server.lambda_handler",
        "server_name": "pellier-pricing-server",
        "entrypoint": "scripts/deploy/pellier_pricing_server.py",
    },
    "recommendation": {
        "handler": "pellier_recommend_server.lambda_handler",
        "server_name": "pellier-recommend-server",
        "entrypoint": "scripts/deploy/pellier_recommend_server.py",
    },
    "experience": {
        "handler": "pellier_experience_server.lambda_handler",
        "server_name": "pellier-experience-server",
        "entrypoint": "scripts/deploy/pellier_experience_server.py",
    },
}

AWS_CONFIG = Config(
    retries={"total_max_attempts": 5, "mode": "adaptive"},
    connect_timeout=10,
    read_timeout=60,
)
TRANSACTION_SEARCH_POLICY = "TransactionSearchXRayAccess"
RUNTIME_SMOKE_SESSION = "builders-smoke-session-0000000000000001"
TRACE_DELIVERY_TIMEOUT_SECONDS = 240
_RUNTIME_LOG_RETENTION_DAYS = frozenset(
    {
        1,
        3,
        5,
        7,
        14,
        30,
        60,
        90,
        120,
        150,
        180,
        365,
        400,
        545,
        731,
        1827,
        2192,
        2557,
        2922,
        3288,
        3653,
    }
)
_AGENT_INPUT_ATTRIBUTE_KEYS = (
    "gen_ai.input.messages",
    "gen_ai.request.input",
    "gen_ai.prompt",
)
_AGENT_OUTPUT_ATTRIBUTE_KEYS = (
    "gen_ai.output.messages",
    "gen_ai.response.output",
    "gen_ai.completion",
)
_TOOL_INPUT_ATTRIBUTE_KEYS = (
    "gen_ai.tool.call.arguments",
    "gen_ai.tool.input",
    "gen_ai.tool.parameters",
)
_TOOL_OUTPUT_ATTRIBUTE_KEYS = (
    "gen_ai.tool.call.result",
    "gen_ai.tool.output",
    "gen_ai.tool.result",
)
_SENSITIVE_TRACE_VALUE = re.compile(
    r"(authorization|bearer\s|access[_-]?token|id[_-]?token|refresh[_-]?token|"
    r"api[_-]?key|client[_-]?secret|password|secret[_-]?key)",
    re.IGNORECASE,
)


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        redacted = list(cmd)
        for index, value in enumerate(redacted[:-1]):
            if value in {"--bearer-token", "--token", "--password", "--client-secret"}:
                redacted[index + 1] = "<redacted>"
        raise RuntimeError(
            f"Command failed: {' '.join(redacted)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    return proc


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _region_from_arn(arn: str, fallback: str) -> str:
    match = re.match(r"^arn:[^:]+:[^:]+:([^:]+):", arn or "")
    return match.group(1) if match else fallback


def _runtime_log_group_name(runtime_arn: str) -> str:
    """Return the one AgentCore Runtime log group this provisioner owns."""
    runtime_id = runtime_arn.rsplit("/", 1)[-1].strip()
    if not runtime_id:
        raise RuntimeError("AgentCore Runtime ARN did not include a runtime id")
    return f"/aws/bedrock-agentcore/runtimes/{runtime_id}-DEFAULT"


def _runtime_log_retention_days(value: str) -> int:
    """Validate the finite CloudWatch retention contract before deployment."""
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "AGENTCORE_RUNTIME_LOG_RETENTION_DAYS must be a supported "
            "CloudWatch Logs retention value"
        ) from exc
    if days not in _RUNTIME_LOG_RETENTION_DAYS:
        supported = ", ".join(str(item) for item in sorted(_RUNTIME_LOG_RETENTION_DAYS))
        raise RuntimeError(
            "AGENTCORE_RUNTIME_LOG_RETENTION_DAYS must be one of: "
            f"{supported}"
        )
    return days


def _find_runtime_log_group(logs: Any, log_group_name: str) -> dict[str, Any] | None:
    """Find one exact log group without relying on a truncated list response."""
    paginator = logs.get_paginator("describe_log_groups")
    for page in paginator.paginate(logGroupNamePrefix=log_group_name):
        for group in page.get("logGroups", []):
            if group.get("logGroupName") == log_group_name:
                return group
    return None


def _ensure_runtime_log_group(
    *,
    region: str,
    runtime_arn: str,
    kms_key_arn: str,
    retention_days: int,
) -> dict[str, Any]:
    """Create or repair the Runtime log group before it receives a smoke turn.

    AgentCore emits Runtime payloads to this group. A deployment receipt is
    useful only when the payload-bearing destination has a customer key and
    bounded retention, so this check happens before Runtime invocation.
    """
    if not re.match(
        r"^arn:[^:]+:kms:[^:]+:\d{12}:key/(?:mrk-)?[0-9a-f-]{36}$",
        kms_key_arn,
    ):
        raise RuntimeError(
            "AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN must be a customer-managed KMS key ARN"
        )

    logs = boto3.client("logs", region_name=region, config=AWS_CONFIG)
    log_group_name = _runtime_log_group_name(runtime_arn)
    try:
        logs.create_log_group(logGroupName=log_group_name, kmsKeyId=kms_key_arn)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass

    observed = _find_runtime_log_group(logs, log_group_name)
    if observed is None:
        raise RuntimeError(f"Runtime log group was not created: {log_group_name}")

    if observed.get("kmsKeyId") != kms_key_arn:
        logs.associate_kms_key(logGroupName=log_group_name, kmsKeyId=kms_key_arn)
    if observed.get("retentionInDays") != retention_days:
        logs.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_days,
        )

    verified = _find_runtime_log_group(logs, log_group_name)
    if verified is None:
        raise RuntimeError(f"Runtime log group disappeared: {log_group_name}")
    if verified.get("kmsKeyId") != kms_key_arn:
        raise RuntimeError("Runtime log group KMS key does not match the required key")
    if verified.get("retentionInDays") != retention_days:
        raise RuntimeError("Runtime log group retention does not match the required days")

    return {
        "name": log_group_name,
        "kms_key_arn": kms_key_arn,
        "retention_days": retention_days,
    }


def _configure_transaction_search(
    *,
    region: str,
    account_id: str,
    partition: str,
) -> dict[str, Any]:
    """Install the scoped X-Ray delivery policy and require an active destination."""
    logs = boto3.client("logs", region_name=region, config=AWS_CONFIG)
    xray = boto3.client("xray", region_name=region, config=AWS_CONFIG)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "TransactionSearchXRayAccess",
                "Effect": "Allow",
                "Principal": {"Service": "xray.amazonaws.com"},
                "Action": "logs:PutLogEvents",
                "Resource": [
                    (
                        f"arn:{partition}:logs:{region}:{account_id}:"
                        "log-group:aws/spans:*"
                    ),
                    (
                        f"arn:{partition}:logs:{region}:{account_id}:"
                        "log-group:/aws/application-signals/data:*"
                    ),
                ],
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {
                        "aws:SourceArn": (
                            f"arn:{partition}:xray:{region}:{account_id}:*"
                        )
                    },
                },
            }
        ],
    }
    logs.put_resource_policy(
        policyName=TRANSACTION_SEARCH_POLICY,
        policyDocument=json.dumps(policy, separators=(",", ":")),
    )

    destination = xray.get_trace_segment_destination()
    if destination.get("Destination") != "CloudWatchLogs":
        xray.update_trace_segment_destination(Destination="CloudWatchLogs")

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        destination = xray.get_trace_segment_destination()
        if (
            destination.get("Destination") == "CloudWatchLogs"
            and destination.get("Status") == "ACTIVE"
        ):
            return {
                "destination": "CloudWatchLogs",
                "status": "ACTIVE",
                "resource_policy": TRANSACTION_SEARCH_POLICY,
                "span_log_group": "aws/spans",
            }
        time.sleep(5)
    raise RuntimeError(
        "Transaction Search trace destination did not become CloudWatchLogs/ACTIVE"
    )


def _ensure_data_api_enabled(region: str, db_cluster_arn: str) -> None:
    rds = boto3.client("rds", region_name=region, config=AWS_CONFIG)
    cluster_id = db_cluster_arn.rsplit(":", 1)[-1]

    def enabled() -> bool:
        response = rds.describe_db_clusters(DBClusterIdentifier=cluster_id)
        return bool(response["DBClusters"][0].get("HttpEndpointEnabled"))

    if enabled():
        return

    print(f"Enabling Aurora Data API on {cluster_id}...")
    rds.enable_http_endpoint(ResourceArn=db_cluster_arn)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        time.sleep(5)
        if enabled():
            time.sleep(10)
            return
    raise RuntimeError(f"Aurora Data API did not become ready on {cluster_id}")


def _compute_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    digest = hmac.new(
        client_secret.encode("utf-8"),
        msg=f"{username}{client_id}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _cognito_access_token(
    *,
    region: str,
    user_pool_id: str,
    client_id: str,
    credentials_secret_arn: str,
    client_secret_arn: str | None,
) -> tuple[str, str]:
    secrets = boto3.client("secretsmanager", region_name=region, config=AWS_CONFIG)
    cognito = boto3.client("cognito-idp", region_name=region, config=AWS_CONFIG)
    credentials_raw = secrets.get_secret_value(
        SecretId=credentials_secret_arn
    ).get("SecretString", "")
    credentials = json.loads(credentials_raw) if credentials_raw else {}
    users = credentials.get("users", [])
    if not users:
        raise RuntimeError("Cognito test credentials secret has no users")

    username = str(users[0].get("username", ""))
    password = str(users[0].get("password", ""))
    if not username or not password:
        raise RuntimeError("Cognito test credentials are missing username/password")

    auth_parameters = {"USERNAME": username, "PASSWORD": password}
    if client_secret_arn:
        client_secret_raw = secrets.get_secret_value(
            SecretId=client_secret_arn
        ).get("SecretString", "")
        client_secret_payload = json.loads(client_secret_raw) if client_secret_raw else {}
        client_secret = str(client_secret_payload.get("client_secret", ""))
        if client_secret:
            auth_parameters["SECRET_HASH"] = _compute_secret_hash(
                username, client_id, client_secret
            )

    response = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters=auth_parameters,
    )
    access_token = response.get("AuthenticationResult", {}).get("AccessToken")
    if not access_token:
        raise RuntimeError("Cognito did not return an access token")
    verified_user = cognito.get_user(AccessToken=str(access_token))
    verified_username = str(verified_user.get("Username", "")).strip()
    if not verified_username:
        raise RuntimeError("Cognito GetUser did not return a username")
    if verified_username.casefold() != username.casefold():
        raise RuntimeError(
            "Cognito authenticated username did not match the seeded user"
        )
    if verified_username != verified_username.casefold():
        raise RuntimeError(
            "Cognito username is not lowercase; identity-bound workshop policy "
            "would not match lowercase customer_id arguments"
        )
    return str(access_token), verified_username


def _scaffold_cli_project(
    *,
    repo: Path,
    env: dict[str, str],
) -> Path:
    root = project_root(repo)
    config_path = root / "agentcore" / "agentcore.json"
    output_dir = root.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    legacy_root = repo / "pellier" / "backend" / ".agentcore-project"
    if legacy_root.exists():
        shutil.rmtree(legacy_root, ignore_errors=True)

    if not config_path.is_file():
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        _run(
            [
                "npx",
                "-y",
                AGENTCORE_CLI,
                "create",
                "--project-name",
                PROJECT_NAME,
                "--no-agent",
                "--skip-git",
                "--skip-python-setup",
                "--output-dir",
                str(output_dir),
                "--json",
            ],
            cwd=output_dir,
            env=env,
        )
    return root


def _agentcore(
    root: Path,
    *args: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return _run(
        ["npx", "-y", AGENTCORE_CLI, *args],
        cwd=root,
        env=env,
    )


def _deploy_cli_project(
    *,
    repo: Path,
    account_id: str,
    region: str,
    cognito_pool: str,
    cognito_client: str,
    lambda_arns: dict[str, str],
    model_id: str,
    workshop_id: str,
    env: dict[str, str],
) -> tuple[Path, dict[str, Any]]:
    """Deploy infrastructure first, then add Gateway-scoped Cedar policies."""
    root = _scaffold_cli_project(repo=repo, env=env)
    common = {
        "repo": repo,
        "account_id": account_id,
        "region": region,
        "cognito_pool": cognito_pool,
        "cognito_client": cognito_client,
        "lambda_arns": lambda_arns,
        "model_id": model_id,
        "workshop_id": workshop_id,
    }

    render_project(**common, include_policies=False)
    _agentcore(root, "validate", env=env)
    _agentcore(root, "deploy", "--yes", "--json", env=env)

    state = _read_deployed_state(root)
    _require_gateway_state(state, GATEWAY_NAME)
    _require_state_resource(state, "policyEngines", POLICY_ENGINE_NAME)

    render_project(
        **common,
        include_policies=True,
        action_token=PROCESS_RETURN_ACTION,
    )
    _agentcore(root, "validate", env=env)
    _agentcore(root, "deploy", "--yes", "--json", env=env)
    return root, _read_deployed_state(root)


def _read_deployed_state(root: Path) -> dict[str, Any]:
    path = root / "agentcore" / ".cli" / "deployed-state.json"
    if not path.is_file():
        raise RuntimeError(f"AgentCore CLI deployed state not found: {path}")
    try:
        state = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AgentCore CLI deployed state is invalid JSON: {path}") from exc
    if not isinstance(state.get("targets"), dict):
        raise RuntimeError("AgentCore CLI deployed state has no targets map")
    return state


def _state_resources(state: dict[str, Any]) -> dict[str, Any]:
    target = state.get("targets", {}).get("default")
    if not isinstance(target, dict):
        target = next(iter(state.get("targets", {}).values()), {})
    resources = target.get("resources", {}) if isinstance(target, dict) else {}
    if not isinstance(resources, dict):
        raise RuntimeError("AgentCore CLI deployed state has no resources")
    return resources


def _require_state_resource(
    state: dict[str, Any],
    category: str,
    name: str,
) -> dict[str, Any]:
    value = _state_resources(state).get(category, {}).get(name)
    if not isinstance(value, dict):
        raise RuntimeError(
            f"AgentCore CLI deployed state is missing {category}.{name}"
        )
    return value


def _require_gateway_state(
    state: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    mcp = _state_resources(state).get("mcp", {})
    value = mcp.get("gateways", {}).get(name) if isinstance(mcp, dict) else None
    if not isinstance(value, dict):
        raise RuntimeError(
            f"AgentCore CLI deployed state is missing mcp.gateways.{name}"
        )
    return value


def _deploy_lambdas(
    *,
    repo: Path,
    deploy_dir: Path,
    region: str,
    db_region: str,
    db_cluster_arn: str,
    db_secret_arn: str,
    db_name: str,
) -> dict[str, str]:
    lambda_client = boto3.client("lambda", region_name=region, config=AWS_CONFIG)
    arns: dict[str, str] = {}
    for surface, config in EXPECTED_TARGETS.items():
        _run(
            [
                sys.executable,
                str(deploy_dir / "deploy_lambda.py"),
                "--region",
                region,
                "--server-name",
                config["server_name"],
                "--db-cluster-arn",
                db_cluster_arn,
                "--db-region",
                db_region,
                "--secret-arn",
                db_secret_arn,
                "--database",
                db_name,
                "--mcp-server-path",
                str(repo / config["entrypoint"]),
                "--handler",
                config["handler"],
            ],
            cwd=repo,
        )
        function_name = f"{config['server_name']}-function"
        response = lambda_client.get_function(FunctionName=function_name)
        arns[surface] = response["Configuration"]["FunctionArn"]
    return arns


def _verify_local_schema() -> dict[str, Any]:
    names = [
        tool["name"]
        for surface in TOOL_SCHEMAS
        for tool in schema_for(surface)
    ]
    if len(names) != 15 or len(set(names)) != 15:
        raise RuntimeError(
            f"Canonical Gateway schema must contain 15 unique tools, found {len(names)}"
        )
    return {"count": len(names), "canonical_names": sorted(names)}


def _verify_gateway_control_plane(
    *,
    region: str,
    gateway_id: str,
) -> dict[str, Any]:
    control = boto3.client(
        "bedrock-agentcore-control",
        region_name=region,
        config=AWS_CONFIG,
    )
    expected = {schema["target_name"] for schema in TOOL_SCHEMAS.values()}
    observed: set[str] = set()
    paginator = control.get_paginator("list_gateway_targets")
    for page in paginator.paginate(gatewayIdentifier=gateway_id):
        observed.update(
            str(item["name"])
            for item in page.get("items", [])
            if item.get("name")
        )
    if observed != expected:
        raise RuntimeError(
            "Gateway target mismatch: "
            f"expected {sorted(expected)}, observed {sorted(observed)}"
        )
    gateway = control.get_gateway(gatewayIdentifier=gateway_id)
    policy_config = gateway.get("policyEngineConfiguration", {})
    if policy_config.get("mode") != "ENFORCE":
        raise RuntimeError("Gateway Policy mode is not ENFORCE")
    return {
        "target_count": len(observed),
        "target_names": sorted(observed),
        "status": gateway.get("status", "UNKNOWN"),
        "policy_mode": policy_config.get("mode"),
    }


def _discover_live_gateway_tools(
    *,
    deploy_dir: Path,
    gateway_url: str,
    access_token: str,
) -> dict[str, Any]:
    deploy_path = str(deploy_dir)
    if deploy_path not in sys.path:
        sys.path.insert(0, deploy_path)
    from test_gateway_tools import discover_gateway_tools

    tools = discover_gateway_tools(gateway_url, access_token)
    full_names = sorted(str(tool.name) for tool in tools)
    canonical_names = {name.rsplit("__", 1)[-1] for name in full_names}
    expected = {
        tool["name"]
        for surface in TOOL_SCHEMAS
        for tool in schema_for(surface)
    }
    if len(tools) != 15 or canonical_names != expected:
        raise RuntimeError(
            "Live Gateway discovery mismatch: "
            f"expected {sorted(expected)}, observed {sorted(canonical_names)}"
        )
    return {
        "count": len(tools),
        "canonical_names": sorted(canonical_names),
        "prefixed_names": full_names,
    }


def _seed_memory(
    *,
    repo: Path,
    memory_id: str,
    region: str,
    env: dict[str, str],
) -> dict[str, Any]:
    proc = _run(
        [
            sys.executable,
            str(repo / "scripts" / "deploy" / "seed_agentcore_memory.py"),
            "--memory-id",
            memory_id,
            "--region",
            region,
        ],
        cwd=repo,
        env=env,
    )
    return json.loads(proc.stdout)


def _authenticated_runtime_smoke(
    *,
    root: Path,
    access_token: str,
    username: str,
    env: dict[str, str],
) -> dict[str, Any]:
    runtime_session_id = RUNTIME_SMOKE_SESSION
    proc = _agentcore(
        root,
        "invoke",
        "--runtime",
        RUNTIME_NAME,
        "--session-id",
        runtime_session_id,
        "--bearer-token",
        access_token,
        "--prompt",
        "Smoke test: find one linen item under 150. Do not mutate data.",
        "--json",
        env=env,
    )
    try:
        cli_payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("AgentCore CLI invoke did not return JSON") from exc
    if cli_payload.get("success") is not True:
        raise RuntimeError("AgentCore CLI invoke did not report success")

    raw_response = cli_payload.get("response")
    if isinstance(raw_response, str):
        try:
            decoded = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "AgentCore CLI Runtime response was not a JSON object"
            ) from exc
    elif isinstance(raw_response, dict):
        decoded = raw_response
    else:
        raise RuntimeError("AgentCore CLI Runtime response was missing")

    if not str(decoded.get("response", "")).strip():
        raise RuntimeError("Runtime smoke returned an empty response")
    if decoded.get("rail") != "gateway-mcp":
        raise RuntimeError(
            "Runtime smoke did not use Gateway MCP "
            f"(rail={decoded.get('rail') or 'missing'})"
        )
    return {
        "username": username,
        "session_id": runtime_session_id,
        "rail": decoded["rail"],
        "intent": decoded.get("intent"),
        "specialist": decoded.get("specialist"),
        "gateway_tools": decoded.get("gateway_tools", []),
        "response_preview": str(decoded["response"])[:200],
    }


def _summarize_trace_records(
    records: Any,
    *,
    trace_id: str,
    session_id: str,
    runtime_arn: str,
) -> dict[str, Any]:
    """Validate the downloaded unified trace and return bounded proof metadata."""
    if not isinstance(records, list):
        raise RuntimeError("AgentCore trace download must be a JSON array")

    spans: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        message = record.get("@message")
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                continue
        if isinstance(message, dict) and message.get("traceId") == trace_id:
            spans.append(message)

    if not spans:
        raise RuntimeError(f"Unified trace {trace_id} contained no span records")

    def attribute_value(value: Any) -> Any:
        """Unwrap both JSON-log and OTLP typed attribute value shapes."""
        if not isinstance(value, dict):
            return value
        for key in (
            "stringValue",
            "boolValue",
            "intValue",
            "doubleValue",
            "arrayValue",
            "kvlistValue",
        ):
            if key in value:
                return value[key]
        if "value" in value:
            return attribute_value(value["value"])
        return value

    def attribute_map(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return {str(key): attribute_value(item) for key, item in value.items()}
        if not isinstance(value, list):
            return {}
        mapped: dict[str, Any] = {}
        for item in value:
            if not isinstance(item, dict) or not item.get("key"):
                continue
            mapped[str(item["key"])] = attribute_value(item.get("value"))
        return mapped

    def attributes(span: dict[str, Any]) -> dict[str, Any]:
        return attribute_map(span.get("attributes"))

    def resource_attributes(span: dict[str, Any]) -> dict[str, Any]:
        resource = span.get("resource")
        value = resource.get("attributes") if isinstance(resource, dict) else None
        return attribute_map(value)

    def first_attribute(
        span_list: list[dict[str, Any]], keys: tuple[str, ...]
    ) -> Any:
        for span in span_list:
            span_attributes = attributes(span)
            for key in keys:
                value = span_attributes.get(key)
                if value not in (None, "", [], {}):
                    return value
        return None

    def numeric_value(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)) and value >= 0:
            return int(value)
        if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+)?", value):
            return int(float(value))
        return None

    def duration_ms(span: dict[str, Any]) -> int | None:
        for key in ("durationMs", "duration_ms"):
            value = numeric_value(span.get(key))
            if value is not None:
                return value
        for key in ("durationNanos", "duration_nanos"):
            value = numeric_value(span.get(key))
            if value is not None:
                return int(value / 1_000_000)
        for start_key, end_key in (
            ("startTimeUnixNano", "endTimeUnixNano"),
            ("start_time_unix_nano", "end_time_unix_nano"),
        ):
            start = numeric_value(span.get(start_key))
            end = numeric_value(span.get(end_key))
            if start is not None and end is not None:
                if end >= start:
                    return int((end - start) / 1_000_000)
        return None

    def contains_sensitive_value(value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                _SENSITIVE_TRACE_VALUE.search(str(key))
                or contains_sensitive_value(item)
                for key, item in value.items()
            )
        if isinstance(value, list):
            return any(contains_sensitive_value(item) for item in value)
        return bool(_SENSITIVE_TRACE_VALUE.search(str(value or "")))

    if not all(
        runtime_arn in str(resource_attributes(span).get("cloud.resource_id", ""))
        for span in spans
    ):
        raise RuntimeError("Unified trace includes a span from another Runtime")

    observed_sessions = {
        str(attributes(span).get("session.id"))
        for span in spans
        if attributes(span).get("session.id")
    }
    if session_id not in observed_sessions:
        raise RuntimeError(
            "Unified trace did not preserve the authenticated Runtime session id"
        )

    agent_spans = [
        span for span in spans if str(span.get("name", "")).startswith("invoke_agent")
    ]
    model_spans = [
        span
        for span in spans
        if span.get("name") == "chat"
        and attributes(span).get("gen_ai.request.model")
    ]
    tool_spans = [
        span
        for span in spans
        if str(span.get("name", "")).startswith("execute_tool")
        and attributes(span).get("gen_ai.tool.name")
    ]
    missing = [
        label
        for label, values in (
            ("agent", agent_spans),
            ("model", model_spans),
            ("tool", tool_spans),
        )
        if not values
    ]
    if missing:
        raise RuntimeError(
            "Unified trace is missing required span classes: " + ", ".join(missing)
        )

    agent_input = first_attribute(spans, _AGENT_INPUT_ATTRIBUTE_KEYS)
    agent_output = first_attribute(spans, _AGENT_OUTPUT_ATTRIBUTE_KEYS)
    tool_input = first_attribute(tool_spans, _TOOL_INPUT_ATTRIBUTE_KEYS)
    tool_output = first_attribute(tool_spans, _TOOL_OUTPUT_ATTRIBUTE_KEYS)
    if agent_input is None or agent_output is None:
        raise RuntimeError(
            "Unified trace is missing required Agent input/output attributes"
        )
    if tool_input is None or tool_output is None:
        raise RuntimeError(
            "Unified trace is missing required sanitized tool input/output attributes"
        )
    if contains_sensitive_value(tool_input) or contains_sensitive_value(tool_output):
        raise RuntimeError(
            "Unified trace tool input/output contains a secret or credential marker"
        )

    step_latencies = {
        "agent": duration_ms(agent_spans[0]),
        "model": duration_ms(model_spans[0]),
        "tool": duration_ms(tool_spans[0]),
    }
    if any(value is None for value in step_latencies.values()):
        raise RuntimeError(
            "Unified trace is missing per-step latency for agent, model, or tool"
        )

    return {
        "trace_id": trace_id,
        "session_id": session_id,
        "runtime_arn": runtime_arn,
        "span_count": len(spans),
        "span_names": sorted({str(span.get("name", "")) for span in spans}),
        "agent_span": True,
        "model_span": True,
        "tool_span": True,
        "agent_input_observed": True,
        "agent_output_observed": True,
        "tool_input_output_observed": True,
        "tool_input_output_sanitized": True,
        "step_latency_observed": True,
        "step_latency_ms": step_latencies,
        "model_ids": sorted(
            {
                str(attributes(span)["gen_ai.request.model"])
                for span in model_spans
            }
        ),
        "tool_names": sorted(
            {
                str(attributes(span)["gen_ai.tool.name"])
                for span in tool_spans
            }
        ),
        "provenance": "agentcore-unified-telemetry",
    }


def _wait_for_unified_trace(
    *,
    root: Path,
    session_id: str,
    runtime_arn: str,
    env: dict[str, str],
) -> dict[str, Any]:
    """Poll the pinned CLI until the smoke invocation has a complete trace."""
    deadline = time.monotonic() + TRACE_DELIVERY_TIMEOUT_SECONDS
    last_error = "trace not listed yet"
    trace_path = Path("/tmp") / f"pellier-agentcore-trace-{session_id}.json"

    while time.monotonic() < deadline:
        try:
            listed = _agentcore(
                root,
                "traces",
                "list",
                "--runtime",
                RUNTIME_NAME,
                "--since",
                "15m",
                "--limit",
                "20",
                "--json",
                env=env,
            )
            payload = json.loads(listed.stdout)
            if payload.get("success") is not True:
                raise RuntimeError("AgentCore CLI trace listing did not report success")
            traces = payload.get("traces")
            if not isinstance(traces, list):
                raise RuntimeError("AgentCore CLI trace listing has no traces array")
            match = next(
                (
                    trace
                    for trace in traces
                    if isinstance(trace, dict)
                    and trace.get("sessionId") == session_id
                    and trace.get("traceId")
                ),
                None,
            )
            if match is None:
                last_error = f"no trace listed for session {session_id}"
                time.sleep(10)
                continue

            trace_id = str(match["traceId"])
            trace_path.unlink(missing_ok=True)
            downloaded = _agentcore(
                root,
                "traces",
                "get",
                trace_id,
                "--runtime",
                RUNTIME_NAME,
                "--since",
                "15m",
                "--output",
                str(trace_path),
                "--json",
                env=env,
            )
            try:
                download_payload = json.loads(downloaded.stdout)
                if download_payload.get("success") is not True:
                    raise RuntimeError(
                        "AgentCore CLI trace download did not report success"
                    )
                records = json.loads(trace_path.read_text(encoding="utf-8"))
            finally:
                trace_path.unlink(missing_ok=True)
            proof = _summarize_trace_records(
                records,
                trace_id=trace_id,
                session_id=session_id,
                runtime_arn=runtime_arn,
            )
            proof["listed_span_count"] = int(match.get("spanCount") or 0)
            proof["runtime_log_group"] = _runtime_log_group_name(runtime_arn)
            return proof
        except (OSError, ValueError, RuntimeError) as exc:
            last_error = str(exc)
            time.sleep(10)

    raise RuntimeError(
        "Unified AgentCore trace did not become complete within "
        f"{TRACE_DELIVERY_TIMEOUT_SECONDS}s: {last_error}"
    )


def _live_policy_proof(
    *,
    repo: Path,
    deploy_dir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    helper = deploy_dir / "gateway_process_return.py"
    proofs: dict[str, Any] = {}
    for expected, reason, session_id in (
        ("allow", "damaged", "provision-policy-allow"),
        ("deny", "changed_mind", "provision-policy-deny"),
    ):
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
                f"Policy {expected.upper()} proof returned {payload.get('outcome')}"
            )
        if expected == "allow" and payload.get("tool_audit_row_after_call") is None:
            raise RuntimeError("Policy ALLOW produced no execution audit row")
        if expected == "deny" and (
            payload.get("tool_audit_row_after_call") is not None
            or payload.get("cedar_denial") is not True
        ):
            raise RuntimeError("Policy DENY did not prove pre-execution blocking")
        proofs[expected] = payload
    return proofs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", default=os.environ.get("REPO_PATH", "."))
    parser.add_argument("--output-json", default="/tmp/pellier-agentcore-managed.json")
    args = parser.parse_args()

    repo = Path(args.repo_path).resolve()
    deploy_dir = repo / "scripts" / "deploy"
    output_path = Path(args.output_json)
    region = _require_env("AWS_REGION")
    required = {
        "db_cluster_arn": _require_env("DB_CLUSTER_ARN"),
        "db_secret_arn": _require_env("DB_SECRET_ARN"),
        "cognito_pool": _require_env("COGNITO_POOL"),
        "cognito_client": _require_env("COGNITO_CLIENT"),
        "credentials_secret": _require_env(
            "COGNITO_TEST_CREDENTIALS_SECRET_ARN"
        ),
        "workshop_id": _require_env("WORKSHOP_ID"),
        "model_id": _require_env("AGENT_MODEL_ID"),
        "runtime_log_kms_key_arn": _require_env(
            "AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN"
        ),
    }
    runtime_log_retention_days = _runtime_log_retention_days(
        _require_env("AGENTCORE_RUNTIME_LOG_RETENTION_DAYS")
    )
    client_secret_arn = (
        os.environ.get("COGNITO_CLIENT_SECRET_ARN", "").strip() or None
    )
    db_region = os.environ.get("DB_REGION", "").strip() or _region_from_arn(
        required["db_cluster_arn"], region
    )
    db_name = os.environ.get("DB_NAME", "pellier")
    deploy_env = os.environ.copy()
    deploy_env.update({"AWS_REGION": region, "AWS_DEFAULT_REGION": region})

    result: dict[str, Any] = {
        "status": "failed",
        "region": region,
        "cli": {"package": AGENTCORE_CLI},
        "lambdas": {},
        "gateway": {},
        "memory": {},
        "observability": {},
        "policy": {},
        "runtime": {},
        "verification": {},
    }

    try:
        _ensure_data_api_enabled(db_region, required["db_cluster_arn"])
        local_schema = _verify_local_schema()
        result["verification"]["local_tool_schema"] = local_schema

        lambda_arns = _deploy_lambdas(
            repo=repo,
            deploy_dir=deploy_dir,
            region=region,
            db_region=db_region,
            db_cluster_arn=required["db_cluster_arn"],
            db_secret_arn=required["db_secret_arn"],
            db_name=db_name,
        )
        result["lambdas"] = {
            surface: {"function_arn": arn}
            for surface, arn in lambda_arns.items()
        }

        sts = boto3.client("sts", region_name=region, config=AWS_CONFIG)
        caller = sts.get_caller_identity()
        account_id = caller["Account"]
        partition = str(caller.get("Arn", "arn:aws:")).split(":", 2)[1]
        transaction_search = _configure_transaction_search(
            region=region,
            account_id=account_id,
            partition=partition,
        )
        result["observability"]["transaction_search"] = transaction_search
        result["verification"]["transaction_search_ready"] = True
        root, state = _deploy_cli_project(
            repo=repo,
            account_id=account_id,
            region=region,
            cognito_pool=required["cognito_pool"],
            cognito_client=required["cognito_client"],
            lambda_arns=lambda_arns,
            model_id=required["model_id"],
            workshop_id=required["workshop_id"],
            env=deploy_env,
        )
        result["cli"]["project_root"] = str(root)

        runtime_state = _require_state_resource(state, "runtimes", RUNTIME_NAME)
        memory_state = _require_state_resource(state, "memories", MEMORY_NAME)
        gateway_state = _require_gateway_state(state, GATEWAY_NAME)
        policy_state = _require_state_resource(
            state, "policyEngines", POLICY_ENGINE_NAME
        )
        runtime_arn = str(runtime_state["runtimeArn"])
        memory_id = str(memory_state["memoryId"])
        gateway_id = str(gateway_state["gatewayId"])
        gateway_arn = str(gateway_state["gatewayArn"])
        gateway_url = str(gateway_state.get("gatewayUrl", ""))
        policy_engine_id = str(policy_state["policyEngineId"])
        if not gateway_url:
            raise RuntimeError("AgentCore CLI state did not include Gateway URL")

        result["runtime"] = {
            "runtime_arn": runtime_arn,
            "agent_model_id": required["model_id"],
        }
        runtime_log_group = _ensure_runtime_log_group(
            region=region,
            runtime_arn=runtime_arn,
            kms_key_arn=required["runtime_log_kms_key_arn"],
            retention_days=runtime_log_retention_days,
        )
        result["observability"]["runtime_log_group"] = runtime_log_group
        result["verification"]["runtime_log_group_encrypted"] = True
        result["verification"]["runtime_log_group_retention_bounded"] = True
        result["memory"] = {
            "memory_id": memory_id,
            "memory_arn": memory_state.get("memoryArn"),
        }
        result["gateway"] = {
            "gateway_id": gateway_id,
            "gateway_arn": gateway_arn,
            "gateway_url": gateway_url,
        }
        result["policy"] = {
            "policy_engine_id": policy_engine_id,
            "policy_engine_arn": policy_state.get("policyEngineArn"),
            "mode": "ENFORCE",
            "gated_tool": "process_return",
        }

        control_proof = _verify_gateway_control_plane(
            region=region,
            gateway_id=gateway_id,
        )
        result["verification"]["gateway_control_plane"] = control_proof
        result["verification"]["targets_attached"] = (
            control_proof["target_count"] == 4
        )

        access_token, smoke_username = _cognito_access_token(
            region=region,
            user_pool_id=required["cognito_pool"],
            client_id=required["cognito_client"],
            credentials_secret_arn=required["credentials_secret"],
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

        memory_seed = _seed_memory(
            repo=repo,
            memory_id=memory_id,
            region=region,
            env=deploy_env,
        )
        result["memory"]["seed"] = memory_seed
        result["verification"]["memory_seeded"] = (
            memory_seed.get("status") == "ready"
        )

        proof_env = deploy_env.copy()
        proof_env.update(
            {
                "AGENTCORE_GATEWAY_URL": gateway_url,
                "AGENTCORE_GATEWAY_ARN": gateway_arn,
                "AGENTCORE_POLICY_ENGINE_ID": policy_engine_id,
                "PELLIER_TOKEN": access_token,
            }
        )
        policy_proof = _live_policy_proof(
            repo=repo,
            deploy_dir=deploy_dir,
            env=proof_env,
        )
        result["verification"]["live_policy_allow"] = True
        result["verification"]["live_policy_deny"] = True
        result["verification"]["live_policy_proof"] = policy_proof

        runtime_smoke = _authenticated_runtime_smoke(
            root=root,
            access_token=access_token,
            username=smoke_username,
            env=deploy_env,
        )
        result["verification"]["authenticated_runtime_invoke_smoke"] = True
        result["verification"]["runtime_invoke_smoke"] = runtime_smoke
        trace_proof = _wait_for_unified_trace(
            root=root,
            session_id=runtime_smoke["session_id"],
            runtime_arn=runtime_arn,
            env=deploy_env,
        )
        result["observability"]["unified_trace"] = trace_proof
        result["verification"]["unified_trace_delivered"] = True
        result["verification"]["unified_trace_agent_span"] = trace_proof["agent_span"]
        result["verification"]["unified_trace_model_span"] = trace_proof["model_span"]
        result["verification"]["unified_trace_tool_span"] = trace_proof["tool_span"]
        result["verification"]["unified_trace_agent_input"] = trace_proof[
            "agent_input_observed"
        ]
        result["verification"]["unified_trace_agent_output"] = trace_proof[
            "agent_output_observed"
        ]
        result["verification"]["unified_trace_tool_io_sanitized"] = trace_proof[
            "tool_input_output_sanitized"
        ]
        result["verification"]["unified_trace_step_latency"] = trace_proof[
            "step_latency_observed"
        ]

        required_checks = (
            "targets_attached",
            "gateway_tools_discovered",
            "memory_seeded",
            "live_policy_allow",
            "live_policy_deny",
            "authenticated_runtime_invoke_smoke",
            "transaction_search_ready",
            "runtime_log_group_encrypted",
            "runtime_log_group_retention_bounded",
            "unified_trace_delivered",
            "unified_trace_agent_span",
            "unified_trace_model_span",
            "unified_trace_tool_span",
            "unified_trace_agent_input",
            "unified_trace_agent_output",
            "unified_trace_tool_io_sanitized",
            "unified_trace_step_latency",
        )
        missing = [
            check
            for check in required_checks
            if result["verification"].get(check) is not True
        ]
        if missing:
            raise RuntimeError(
                "Managed readiness checks did not pass: " + ", ".join(missing)
            )
        result["status"] = "ready"
        output_path.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return 0
    except (ClientError, RuntimeError, OSError, ValueError) as exc:
        result["error"] = str(exc)
        output_path.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
