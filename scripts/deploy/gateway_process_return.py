#!/usr/bin/env python3
"""Invoke Pellier process_return through AgentCore Gateway.

This is a deterministic workshop helper for the Cedar exercise. It does not
ask a model to decide whether to call the tool: it calls the Gateway MCP tool
directly with a real Cognito bearer token. A Gateway/Cedar DENY raises before
the Lambda target executes, so no ``pellier.tool_audit`` row is written.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any

import anyio
import boto3
import psycopg
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


DEFAULT_TOOL_NAME = "pellier-concierge-experience-target___process_return"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_env() -> None:
    for env_path in (_repo_root() / ".env", _repo_root() / "pellier" / "backend" / ".env"):
        if not env_path.is_file():
            continue
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("'\"")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _secret_hash(username: str, client_id: str, client_secret: str) -> str:
    digest = hmac.new(
        client_secret.encode("utf-8"),
        msg=f"{username}{client_id}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _token_from_cognito() -> str:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    pool_id = os.environ.get("COGNITO_POOL_ID") or os.environ.get("COGNITO_POOL")
    client_id = os.environ.get("COGNITO_CLIENT_ID") or os.environ.get("COGNITO_CLIENT")
    creds_secret_arn = _require("COGNITO_TEST_CREDENTIALS_SECRET_ARN")
    if not pool_id or not client_id:
        raise SystemExit("Missing Cognito pool/client env vars.")

    sm = boto3.client("secretsmanager", region_name=region)
    creds_raw = sm.get_secret_value(SecretId=creds_secret_arn).get("SecretString", "")
    creds = json.loads(creds_raw or "{}")
    users = creds.get("users") or []
    if not users:
        raise SystemExit("Cognito test credential secret has no users array.")
    username = users[0].get("username", "")
    password = users[0].get("password", "")
    if not username or not password:
        raise SystemExit("Cognito test credential secret is missing username/password.")

    auth_params = {"USERNAME": username, "PASSWORD": password}
    client_secret_arn = os.environ.get("COGNITO_CLIENT_SECRET_ARN", "").strip()
    if client_secret_arn:
        secret_raw = sm.get_secret_value(SecretId=client_secret_arn).get("SecretString", "")
        secret_payload = json.loads(secret_raw) if secret_raw and secret_raw.startswith("{") else {}
        client_secret = secret_payload.get("client_secret") or secret_raw
        if client_secret:
            auth_params["SECRET_HASH"] = _secret_hash(username, client_id, client_secret)

    cognito = boto3.client("cognito-idp", region_name=region)
    auth = cognito.admin_initiate_auth(
        UserPoolId=pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters=auth_params,
    )
    token = auth.get("AuthenticationResult", {}).get("AccessToken", "")
    if not token:
        raise SystemExit("Cognito did not return an access token.")
    return token


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _db_connect():
    return psycopg.connect(
        host=_require("DB_HOST"),
        port=os.environ.get("DB_PORT", "5432"),
        user=_require("DB_USER"),
        password=_require("DB_PASSWORD"),
        dbname=_require("DB_NAME"),
    )


def _audit_high_water(args: argparse.Namespace) -> int:
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(max(audit_id), 0) "
                "FROM pellier.tool_audit "
                "WHERE tool = 'process_return' "
                "  AND caller = 'gateway' "
                "  AND args->>'customer_id' = %s "
                "  AND args->>'product_id' = %s "
                "  AND args->>'reason' = %s",
                (args.customer_id, str(args.product_id), args.reason),
            )
            return int(cur.fetchone()[0] or 0)


def _latest_matching_audit(args: argparse.Namespace, after_audit_id: int) -> int | None:
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT audit_id "
                "FROM pellier.tool_audit "
                "WHERE tool = 'process_return' "
                "  AND caller = 'gateway' "
                "  AND args->>'customer_id' = %s "
                "  AND args->>'product_id' = %s "
                "  AND args->>'reason' = %s "
                "  AND audit_id > %s "
                "ORDER BY audit_id DESC LIMIT 1",
                (args.customer_id, str(args.product_id), args.reason, after_audit_id),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None


def _record_receipt(args: argparse.Namespace, payload: dict[str, Any], before_audit_id: int) -> None:
    audit_id = _latest_matching_audit(args, before_audit_id)
    if payload["outcome"] == "allow" and audit_id is None:
        raise RuntimeError("Gateway call ALLOWed but no matching tool_audit row was found.")
    if payload["outcome"] == "deny" and audit_id is not None:
        raise RuntimeError(f"Gateway call DENYed but tool_audit row {audit_id} was written.")

    receipt_args = {
        "customer_id": args.customer_id,
        "product_id": int(args.product_id),
        "reason": args.reason,
        "tool_audit_high_water_before": before_audit_id,
        "tool_audit_row_after_call": audit_id,
        "absence_verified": payload["outcome"] == "deny" and audit_id is None,
    }
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pellier.governed_receipts
                    (audit_id, session_id, principal_id, principal_label,
                     tool, caller, decision, args, policy_engine_id,
                     policy_name, created_at)
                VALUES
                    (%s, %s, %s, %s, 'process_return', 'gateway',
                     %s, %s::jsonb, %s, %s, now())
                RETURNING receipt_id
                """,
                (
                    audit_id,
                    args.session_id,
                    args.principal_id,
                    args.principal_label,
                    payload["outcome"].upper(),
                    json.dumps(receipt_args, sort_keys=True),
                    os.environ.get("AGENTCORE_POLICY_ENGINE_ID", ""),
                    args.policy_name,
                ),
            )
            receipt_id = int(cur.fetchone()[0])
        conn.commit()
    payload["recorded_receipt_id"] = receipt_id
    payload["recorded_receipt_session_id"] = args.session_id
    payload["tool_audit_high_water_before"] = before_audit_id
    payload["tool_audit_row_after_call"] = audit_id


async def _call_gateway(args: argparse.Namespace, token: str) -> dict[str, Any]:
    gateway_url = args.gateway_url or _require("AGENTCORE_GATEWAY_URL")
    tool_args = {
        "customer_id": args.customer_id,
        "product_id": int(args.product_id),
        "reason": args.reason,
    }
    async with streamablehttp_client(
        gateway_url,
        headers={"Authorization": f"Bearer {token}"},
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(args.tool_name, tool_args)
            return {
                "outcome": "allow",
                "tool": args.tool_name,
                "arguments": tool_args,
                "result": _jsonable(result),
            }


def _exception_summary(exc: BaseException) -> str:
    children = getattr(exc, "exceptions", None)
    if children:
        return "; ".join(_exception_summary(child) for child in children)[:700]
    return str(exc)[:700]


def main() -> int:
    parser = argparse.ArgumentParser(description="Invoke process_return through AgentCore Gateway.")
    parser.add_argument("--customer-id", default="theo")
    parser.add_argument("--product-id", type=int, required=True)
    parser.add_argument("--reason", default="damaged")
    parser.add_argument("--expect", choices=("allow", "deny"), default="allow")
    parser.add_argument("--gateway-url", default="")
    parser.add_argument("--tool-name", default=DEFAULT_TOOL_NAME)
    parser.add_argument(
        "--record-receipt",
        action="store_true",
        help="Record a governed_receipts row for the Gateway decision and absence check.",
    )
    parser.add_argument("--session-id", default="gateway-final-sale-proof")
    parser.add_argument("--principal-id", default="CUST-MARCO")
    parser.add_argument("--principal-label", default="Marco (Cognito JWT)")
    parser.add_argument("--policy-name", default="workshop_final_sale_forbid")
    args = parser.parse_args()

    _load_env()
    token = os.environ.get("PELLIER_TOKEN", "").strip() or _token_from_cognito()
    before_audit_id = _audit_high_water(args) if args.record_receipt else 0

    try:
        payload = anyio.run(_call_gateway, args, token)
    except Exception as exc:
        payload = {
            "outcome": "deny",
            "tool": args.tool_name,
            "arguments": {
                "customer_id": args.customer_id,
                "product_id": int(args.product_id),
                "reason": args.reason,
            },
            "error_type": exc.__class__.__name__,
            "error": _exception_summary(exc),
            "gateway_rail": True,
            "tool_executed": False,
        }

    if args.record_receipt:
        _record_receipt(args, payload, before_audit_id)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["outcome"] == args.expect else 2


if __name__ == "__main__":
    raise SystemExit(main())
