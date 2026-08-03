"""
Pellier Experience MCP Server — Lambda-hosted MCP server for the Theo /
return-flow tools that the Experience Guide owns.

Exposes tools:
  - process_return:        Atomic ownership-check → INSERT into ``pellier.returns``
                           → (if damaged) decrement ``pellier.product_catalog.quantity``.
  - escalate_to_stylist:   Honest fallback that hands the conversation off
                           to a human stylist when no catalog tool fits.

Deployed as a Lambda function behind AgentCore Gateway. Mirrors the
in-process @tool functions in ``pellier/backend/services/agent_tools.py``
and ``pellier/backend/services/business_logic.py`` — same JSON envelopes,
same Cedar-allowed reason set, same ownership SQL — so the orchestrator's
prompt is identical whether tools execute in-process or behind Gateway.

References:
    RDS Data API transactions:
        https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html
"""
import json
import hashlib
import logging
import os
import time
from typing import Any

import boto3

from common.types import resolve_invocation

logger = logging.getLogger(__name__)

REGION = os.environ.get("REGION", "us-east-1")
DB_REGION = os.environ.get("DB_REGION", REGION)
DB_CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN = os.environ.get("SECRET_ARN", "")
DATABASE = os.environ.get("DATABASE", "postgres")
SCHEMA = "pellier"

# Cedar policy ``process-return-allowed-reasons`` enforces this set
# upstream; we re-check inside the Lambda as defense-in-depth so a
# misbehaving caller that bypasses Cedar can't write garbage.
ALLOWED_RETURN_REASONS = {
    "damaged",
    "wrong_size",
    "not_as_described",
    "changed_mind",
    "other",
}

rds_client = boto3.client("rds-data", region_name=DB_REGION)


def _row_to_dict(record: list, columns: list[str]) -> dict:
    out: dict = {}
    for i, field in enumerate(record):
        if "stringValue" in field:
            out[columns[i]] = field["stringValue"]
        elif "longValue" in field:
            out[columns[i]] = field["longValue"]
        elif "doubleValue" in field:
            out[columns[i]] = field["doubleValue"]
        elif "booleanValue" in field:
            out[columns[i]] = field["booleanValue"]
        elif "isNull" in field:
            out[columns[i]] = None
        else:
            out[columns[i]] = str(field)
    return out


def _execute_in_transaction(transaction_id: str, sql: str, parameters: list = None) -> list[dict]:
    params = {
        "resourceArn": DB_CLUSTER_ARN,
        "secretArn": SECRET_ARN,
        "database": DATABASE,
        "sql": sql,
        "transactionId": transaction_id,
        # Without this the Data API omits columnMetadata entirely, columns
        # is [] and the first returned row IndexErrors (box-verified
        # 2026-06-12). The ALLOW beat only passed before because the
        # ownership check returned ZERO rows — nothing reached the parser.
        "includeResultMetadata": True,
    }
    if parameters:
        params["parameters"] = parameters
    response = rds_client.execute_statement(**params)
    columns = [col["name"] for col in response.get("columnMetadata", [])]
    return [_row_to_dict(record, columns) for record in response.get("records", [])]


def _write_tool_audit(tool: str, args: dict, result: dict, latency_ms: int) -> None:
    """Reconstruct the pellier.tool_audit evidence row on the GATEWAY rail.

    On the in-process rail the FastAPI PolicyEnforcementHook writes this row;
    behind the Gateway the tool runs in THIS Lambda, so we write it here. This
    is what makes the governed ALLOW proof queryable: every
    tool call that REACHES this Lambda was already ALLOWed by managed AgentCore
    Policy at the Gateway (a DENY never executes the Lambda, so no row is
    written — that absence is the proof).

    Keying note: the Gateway → Lambda event is ``{name, arguments}`` only — it
    carries NO session_id. So we key by the real identity that IS present
    (``customer_id``, surfaced in ``args``) and use ``session_id =
    'gateway-<customer_id>'`` as a stable, queryable handle. The governed query
    therefore filters on ``args->>'customer_id'`` rather than session_id.

    Schema (scripts/migrations/002_workshop_telemetry.sql):
      tool_audit(session_id, tool, caller, args JSONB, result JSONB, latency_ms)

    Fire-and-forget: a telemetry write must NEVER fail the actual return, so
    every error here is swallowed (the tool result is already committed).
    """
    try:
        customer_id = str(args.get("customer_id", "")) or "unknown"
        rds_client.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DATABASE,
            sql=(
                f"INSERT INTO {SCHEMA}.tool_audit "
                "(session_id, tool, caller, args, result, latency_ms) "
                "VALUES (:sid, :tool, :caller, :args::jsonb, :result::jsonb, :ms)"
            ),
            parameters=[
                {"name": "sid", "value": {"stringValue": f"gateway-{customer_id}"}},
                {"name": "tool", "value": {"stringValue": tool}},
                {"name": "caller", "value": {"stringValue": "gateway"}},
                {"name": "args", "value": {"stringValue": json.dumps(args, default=str)}},
                {"name": "result", "value": {"stringValue": json.dumps(result, default=str)}},
                {"name": "ms", "value": {"longValue": int(latency_ms)}},
            ],
        )
    except Exception as exc:  # never let audit failure break the tool
        logger.warning("tool_audit write failed (non-fatal): %s", exc)


def _write_request_hash(operation: str, arguments: dict) -> str:
    payload = json.dumps(
        {"operation": operation, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def process_return(
    customer_id: str,
    product_id: int,
    reason: str,
    idempotency_key: str,
) -> dict:
    """Execute the shared idempotent return transaction in Aurora."""
    if reason not in ALLOWED_RETURN_REASONS:
        return {
            "status": "policy_blocked",
            "message": (
                f"Reason '{reason}' is not an allowed return reason. "
                f"Allowed: {sorted(ALLOWED_RETURN_REASONS)}."
            ),
        }

    clean_key = str(idempotency_key or "").strip()
    if not clean_key:
        return {"status": "error", "message": "idempotency_key is required."}
    product_id_text = str(product_id)
    request_hash = _write_request_hash(
        "process_return",
        {
            "customer_id": str(customer_id),
            "product_id": int(product_id),
            "reason": str(reason),
        },
    )

    begin = rds_client.begin_transaction(
        resourceArn=DB_CLUSTER_ARN,
        secretArn=SECRET_ARN,
        database=DATABASE,
    )
    transaction_id = begin["transactionId"]

    try:
        rows = _execute_in_transaction(
            transaction_id,
            f"SELECT {SCHEMA}.process_return_idempotent("
            ":idempotency_key, :request_hash, :cid, :pid, :reason"
            ") AS result;",
            [
                {"name": "idempotency_key", "value": {"stringValue": clean_key}},
                {"name": "request_hash", "value": {"stringValue": request_hash}},
                {"name": "cid", "value": {"stringValue": str(customer_id)}},
                {"name": "pid", "value": {"stringValue": product_id_text}},
                {"name": "reason", "value": {"stringValue": str(reason)}},
            ],
        )
        rds_client.commit_transaction(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=SECRET_ARN,
            transactionId=transaction_id,
        )
        raw_result = rows[0].get("result") if rows else None
        return json.loads(raw_result) if isinstance(raw_result, str) else (
            raw_result or {"status": "error", "message": "Return produced no result."}
        )
    except Exception as exc:
        try:
            rds_client.rollback_transaction(
                resourceArn=DB_CLUSTER_ARN,
                secretArn=SECRET_ARN,
                transactionId=transaction_id,
            )
        except Exception:
            logger.warning("rollback failed for transaction %s", transaction_id)
        logger.error("process_return failed: %s", exc)
        return {"status": "error", "message": str(exc)}


def escalate_to_stylist(reason: str = "", customer_id: str = "") -> dict:
    """Honest fallback that hands the conversation off to a human stylist.

    No DB write, no products — pure UI handoff. The chat surface renders
    a `StylistHandoffCard` from this payload (Type ``escalation``). The
    ``stylist`` channel is a placeholder for whatever live-chat / email /
    CX-ticket system a production deployment would wire in.
    """
    cleaned_reason = (reason or "").strip() or (
        "The agent thought a human stylist was the right next step."
    )
    cleaned_customer = (customer_id or "").strip() or None
    return {
        "type": "escalation",
        "channel": "stylist",
        "status": "handed_off",
        "reason": cleaned_reason,
        "customer_id": cleaned_customer,
        "contact": {
            "label": "Talk to a stylist",
            "mailto": "stylist@pellier.example",
            "response_window": "Within 1 business day",
        },
        "next_steps": [
            "A Pellier stylist receives your note with full context.",
            "They reply within one business day.",
            "You can keep browsing — we'll pick up where you left off.",
        ],
    }


# --- Lambda MCP handler ---

TOOLS = {
    "process_return": {
        "fn": process_return,
        "description": (
            "Process a customer return atomically. Verifies ownership "
            "(customer must have ordered the product), inserts a row "
            "into pellier.returns, and (if reason='damaged') decrements "
            "product_catalog.quantity. Reason must be one of: damaged, "
            "wrong_size, not_as_described, changed_mind, other."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Salesforce-style customer ID"},
                "product_id": {"type": "integer", "description": "productId in pellier.product_catalog"},
                "reason": {
                    "type": "string",
                    "description": "One of damaged, wrong_size, not_as_described, changed_mind, other",
                    "enum": sorted(ALLOWED_RETURN_REASONS),
                },
                "idempotency_key": {
                    "type": "string",
                    "description": "Stable unique key for this intended return",
                },
            },
            "required": ["customer_id", "product_id", "reason", "idempotency_key"],
        },
    },
    "escalate_to_stylist": {
        "fn": escalate_to_stylist,
        "description": (
            "Hand the conversation off to a human stylist. Honest fallback "
            "for asks the catalog cannot answer (cultural dressing norms, "
            "body-image fit, out-of-policy returns, catalog misses). Do "
            "not call this when another tool can answer."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "One short sentence describing why the handoff is happening"},
                "customer_id": {"type": "string", "description": "Optional customer id so the stylist queue can pre-load order history"},
            },
            "required": [],
        },
    },
}


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for MCP tool invocation via AgentCore Gateway."""
    # Resolve BOTH invocation shapes (Gateway client_context-prefixed vs direct
    # {name,arguments}); shared helper in common/types.py, packaged into the zip.
    tool_name, arguments = resolve_invocation(event, context)

    if tool_name == "list_tools":
        return {
            "tools": [
                {"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
                for name, spec in TOOLS.items()
            ]
        }

    if tool_name not in TOOLS:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        started = time.monotonic()
        result = TOOLS[tool_name]["fn"](**arguments)
        latency_ms = int((time.monotonic() - started) * 1000)
        # Evidence ledger for the audited write tool. Reaching this point means
        # managed AgentCore Policy ALLOWed the call at the Gateway; a DENY would
        # have blocked it before the Lambda ran, leaving no row. Mirrors the
        # in-process hook's record_allow.
        if tool_name == "process_return":
            _write_tool_audit(tool_name, arguments, result, latency_ms)
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
    except Exception as e:
        logger.error("Tool %s failed: %s", tool_name, e)
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}
