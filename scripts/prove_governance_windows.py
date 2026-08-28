#!/usr/bin/env python3
"""Prove both governance windows against the live Gateway, end to end.

This is the composite proof: everything else verifies one layer at a time, and
the whole point of the design is what happens when two layers disagree.

    ENFORCE window
        Cedar DENY before the target runs. The tool never executes, so there is
        no execution row and no business change. The authoritative artifact is
        the policy decision, because the database was never reached.

    LOG_ONLY window
        Cedar reports a would-deny and the request continues. The tool DOES
        execute, and Aurora refuses it: Row-Level Security scopes the read the
        write depends on. Zero business change, one attempt receipt. Never call
        this an enforced Cedar denial — Cedar enforced nothing.

Both windows use the same request, so the only variable is enforcement mode.

Mode is switched through the AgentCore CLI project rather than the SDK, for the
reasons in `scripts/policy_mode.py`. The script restores the shipped mode on
exit, including after a failure, so a crashed run cannot leave the account in
monitor mode.

Usage::

    python3 scripts/prove_governance_windows.py
    python3 scripts/prove_governance_windows.py --keep-log-only   # inspect it
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

_REPO = pathlib.Path(__file__).resolve().parents[0].parent
_BACKEND = _REPO / "pellier" / "backend"
_DEPLOY = _REPO / "scripts" / "deploy"
_PROJECT = _REPO / ".agentcore-project" / "pellier"

# The forbid policy whose mode decides which window we are in. A permit policy
# in LOG_ONLY looks identical to one in ACTIVE from the caller's side.
GATING_POLICY = "initiate_return_damaged_only"

# A reason the gating policy forbids. `damaged` is the only permitted value, so
# this request is the one Cedar has an opinion about.
FORBIDDEN_REASON = "changed_mind"

# Anna's order, requested while holding Marco's token: refused by Cedar in the
# ENFORCE window, and by Row-Level Security in the LOG_ONLY window. Using a
# cross-customer request means the LOG_ONLY window has a database-side refusal
# to demonstrate rather than merely succeeding.
TARGET_CUSTOMER = "CUST-ANNA"
TARGET_PRODUCT = "21"

# `policy_mode.py` returns this when the CLI project cannot be deployed in
# the current account. That is an environment limitation, not a governance
# failure, so it exits as a skip.
_NOT_DEPLOYABLE = 3


def _load_env() -> Dict[str, str]:
    values: Dict[str, str] = {}
    env_path = _BACKEND / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip('"').strip("'")
    values.update(
        {
            k: v
            for k, v in os.environ.items()
            if k.startswith(("DB_", "AWS_", "COGNITO_", "AGENTCORE_"))
        }
    )
    return values


def _import_tools() -> Tuple[Any, Any]:
    """Load the existing Gateway helpers rather than reimplementing them."""
    sys.path.insert(0, str(_DEPLOY))
    import importlib.util

    def load(name: str, filename: str) -> Any:
        spec = importlib.util.spec_from_file_location(name, _DEPLOY / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load("gw_auth", "test_gateway_auth.py"), load("gw_tools", "test_gateway_tools.py")


def _policy_tool() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "policy_mode_tool", _REPO / "scripts" / "policy_mode.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _call_initiate_return(
    gateway_url: str, token: str, *, reason: str, idempotency_key: str
) -> Dict[str, Any]:
    """Invoke initiate_return through the Gateway's MCP endpoint.

    Returns a dict describing the outcome, including whether the call was
    refused before the target ran.
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(gateway_url, headers=headers) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            name = next(
                (t.name for t in tools.tools if t.name.endswith("initiate_return")),
                None,
            )
            if name is None:
                return {"outcome": "tool_absent"}
            try:
                response = await session.call_tool(
                    name,
                    {
                        "customer_id": TARGET_CUSTOMER,
                        "product_id": int(TARGET_PRODUCT),
                        "reason": reason,
                        "idempotency_key": idempotency_key,
                    },
                )
            except Exception as exc:  # a Cedar denial surfaces as a protocol error
                return {"outcome": "refused", "detail": str(exc)[:300]}

            text = "".join(
                getattr(block, "text", "") for block in (response.content or [])
            )
            return {
                "outcome": "returned",
                "is_error": bool(getattr(response, "isError", False)),
                "text": text[:600],
            }


def _business_state(cfg: Dict[str, str]) -> Dict[str, int]:
    """Count the rows a successful return would have changed."""
    import subprocess

    child = os.environ.copy()
    child["PGPASSWORD"] = cfg["DB_PASSWORD"]
    sql = (
        "SELECT (SELECT count(*) FROM pellier.returns WHERE customer_id='"
        f"{TARGET_CUSTOMER}')::text || '|' || "
        "(SELECT count(*) FROM pellier.inventory_ledger)::text"
    )
    result = subprocess.run(
        [
            "psql", "-h", cfg["DB_HOST"], "-p", cfg.get("DB_PORT", "5432"),
            "-U", cfg["DB_USER"], "-d", cfg["DB_NAME"],
            "-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1", "-c", sql,
        ],
        env=child, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return {"returns": -1, "ledger": -1}
    returns, _, ledger = result.stdout.strip().partition("|")
    return {"returns": int(returns or 0), "ledger": int(ledger or 0)}


def _audit_rows(cfg: Dict[str, str], idempotency_key: str) -> int:
    """Count execution rows for one attempt."""
    import subprocess

    child = os.environ.copy()
    child["PGPASSWORD"] = cfg["DB_PASSWORD"]
    result = subprocess.run(
        [
            "psql", "-h", cfg["DB_HOST"], "-p", cfg.get("DB_PORT", "5432"),
            "-U", cfg["DB_USER"], "-d", cfg["DB_NAME"],
            "-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1",
            "-c",
            "SELECT count(*) FROM pellier.tool_audit WHERE tool='initiate_return'"
            f" AND args::text LIKE '%{idempotency_key}%'",
        ],
        env=child, capture_output=True, text=True,
    )
    return int((result.stdout or "0").strip() or 0)


def _run_window(
    label: str,
    cfg: Dict[str, str],
    gateway_url: str,
    token: str,
) -> Dict[str, Any]:
    """Issue the request and gather what changed."""
    import asyncio

    key = f"gov-window-{uuid.uuid4().hex[:8]}"
    before = _business_state(cfg)
    call = asyncio.run(
        _call_initiate_return(
            gateway_url, token, reason=FORBIDDEN_REASON, idempotency_key=key
        )
    )
    after = _business_state(cfg)
    return {
        "window": label,
        "idempotency_key": key,
        "call": call,
        "executions": _audit_rows(cfg, key),
        "business_change": {
            "returns": after["returns"] - before["returns"],
            "ledger": after["ledger"] - before["ledger"],
        },
    }


def _report(result: Dict[str, Any]) -> List[str]:
    """Return the assertions that failed for one window."""
    failures: List[str] = []
    window = result["window"]
    call = result["call"]

    if call["outcome"] == "tool_absent":
        return [f"{window}: initiate_return is not published on the Gateway"]

    if result["business_change"]["returns"] != 0:
        failures.append(f"{window}: a refused request committed a return row")
    if result["business_change"]["ledger"] != 0:
        failures.append(f"{window}: a refused request moved inventory")

    if window == "ENFORCE":
        # Cedar denies before the target runs, so nothing should have executed.
        if result["executions"] != 0:
            failures.append(
                f"{window}: expected no execution row, found {result['executions']}"
            )
    else:
        # The request continued past Cedar. Execution is expected; the database
        # is what refuses. Zero executions here would mean Cedar still blocked
        # it, so the mode change did not take effect.
        if result["executions"] == 0:
            failures.append(
                f"{window}: expected the tool to execute and be refused by the "
                "database, but nothing executed — Cedar may still be enforcing"
            )
    return failures


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--keep-log-only",
        action="store_true",
        help="Leave the gating policy in LOG_ONLY for manual inspection.",
    )
    args = parser.parse_args(argv)

    cfg = _load_env()
    missing = [
        key
        for key in (
            "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD",
            "AGENTCORE_GATEWAY_URL", "AGENTCORE_POLICY_ENGINE_ID",
            "COGNITO_POOL_ID", "COGNITO_CLIENT_ID",
        )
        if not cfg.get(key)
    ]
    if missing:
        print(
            "Not provisioned for this proof; missing "
            f"{', '.join(missing)}.\n"
            "Both windows need the managed Gateway, a Cedar engine, and Cognito.",
            file=sys.stderr,
        )
        return 2

    gw_auth, _gw_tools = _import_tools()
    policy = _policy_tool()

    import boto3

    control = boto3.client(
        "bedrock-agentcore-control", region_name=cfg.get("AWS_REGION", "us-east-1")
    )
    engine_id = cfg["AGENTCORE_POLICY_ENGINE_ID"]
    gateway_id = policy.gateway_id_from_arn(cfg.get("AGENTCORE_GATEWAY_ARN", ""))
    gateway_url = cfg["AGENTCORE_GATEWAY_URL"]

    token = gw_auth.get_cognito_token(
        pool_id=cfg["COGNITO_POOL_ID"],
        client_id=cfg["COGNITO_CLIENT_ID"],
        region=cfg.get("COGNITO_REGION") or cfg.get("AWS_REGION", "us-east-1"),
        credentials_secret_arn=cfg.get("COGNITO_TEST_CREDENTIALS_SECRET_ARN"),
    )

    failures: List[str] = []
    results: List[Dict[str, Any]] = []
    try:
        # ---- ENFORCE window ------------------------------------------------
        rc = policy._apply(
            _PROJECT, control, engine_id, gateway_id,
            policy_modes={GATING_POLICY: "ACTIVE"}, label="ENFORCE window",
        )
        if rc == _NOT_DEPLOYABLE:
            print(
                "\nSkipped: this box cannot switch enforcement mode, so the two\n"
                "windows cannot be compared here. The mode is a declared property\n"
                "of the AgentCore CLI project, and `agentcore deploy` is a\n"
                "whole-project CDK deploy — it needs a project rendered for this\n"
                "account. A provisioned Workshop Studio account has one.",
                file=sys.stderr,
            )
            return 2
        if rc != 0:
            return rc
        enforce = _run_window("ENFORCE", cfg, gateway_url, token)
        results.append(enforce)
        failures += _report(enforce)

        # ---- LOG_ONLY window ----------------------------------------------
        rc = policy._apply(
            _PROJECT, control, engine_id, gateway_id,
            policy_modes={GATING_POLICY: "LOG_ONLY"}, label="LOG_ONLY window",
        )
        if rc == _NOT_DEPLOYABLE:
            print("\nSkipped before the LOG_ONLY window.", file=sys.stderr)
            return 2
        if rc != 0:
            return rc
        log_only = _run_window("LOG_ONLY", cfg, gateway_url, token)
        results.append(log_only)
        failures += _report(log_only)
    finally:
        if not args.keep_log_only:
            # Restore even after a failure: a crashed run must not leave the
            # account in monitor mode.
            policy._restore_shipped(_PROJECT, control, engine_id, gateway_id)

    print()
    print("Governance windows")
    print("=" * 78)
    for result in results:
        call = result["call"]
        print(f"  {result['window']}")
        print(f"    gateway call      : {call['outcome']}"
              + (f" ({'error' if call.get('is_error') else 'ok'})"
                 if call["outcome"] == "returned" else ""))
        if call.get("text"):
            print(f"    tool said         : {call['text'][:120]}")
        if call.get("detail"):
            print(f"    refusal detail    : {call['detail'][:120]}")
        print(f"    execution rows    : {result['executions']}")
        print(f"    business change   : returns={result['business_change']['returns']}"
              f" ledger={result['business_change']['ledger']}")
        print()

    print("  Reading the pair:")
    print("    ENFORCE  — Cedar refused before the target ran, so the absence of")
    print("               an execution row IS the proof of non-execution.")
    print("    LOG_ONLY — Cedar would have denied but did not stop the request.")
    print("               The tool ran and Aurora refused it. Zero business")
    print("               change either way, for two entirely different reasons.")
    print()

    if failures:
        print("FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("✅ both windows behaved as designed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
