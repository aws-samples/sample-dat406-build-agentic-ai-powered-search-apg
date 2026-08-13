"""
Managed AgentCore Policy — read surface for the Gateway-enforced Cedar engine.

The boutique's policy gate is a **managed AgentCore Policy Engine** attached to
the AgentCore Gateway in ENFORCE mode by the declarative AgentCore CLI project.
The Gateway intercepts every tool call and evaluates it against Cedar BEFORE
the Lambda runs — argument-aware, default-deny, forbid-wins. This replaced the
old local ``BeforeToolCall`` hook + hand-rolled fake-Cedar engine (both removed).

This module is the **read side** of that managed gate. It does NOT enforce
anything (the Gateway does) — it just lets the Agent Trace Policy surface show, live,
which Cedar policies are attached to the engine and what evidence the managed
rail produced.

Two reads:

  1. ``list_managed_policies()`` — boto3 ``bedrock-agentcore-control``
     ``list_policies(policyEngineId=...)`` + ``get_policy`` per id to pull the
     full Cedar ``definition``. Keyed on ``AGENTCORE_POLICY_ENGINE_ID`` (written
     to ``.env`` by the deploy script). Returns the policy statements so the
     surface can render "this is the Cedar the Gateway enforces".

  2. ``recent_decisions()`` — reads the explicit, immutable
     ``pellier.governed_receipts`` decision records. Tool audit rows prove only
     execution, so treating every one as an inferred ALLOW hid DENY evidence and
     exposed broad audit history. The receipt table preserves both outcomes and
     associates each one with its verified principal.

Both reads are best-effort: a missing engine id, missing boto3, or an
unreachable control-plane returns an empty list with a ``source`` marker rather
than raising, so the Agent Trace surface degrades to "(no policies)" instead of a
500.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Env var the deploy script writes (``POLICY_ENGINE_ID=<id>`` → ``.env`` as
# ``AGENTCORE_POLICY_ENGINE_ID``). Read at call time (not import time) so a
# late-arriving .env still takes effect.
_ENGINE_ID_ENV = "AGENTCORE_POLICY_ENGINE_ID"


def _engine_id() -> str:
    return os.environ.get(_ENGINE_ID_ENV, "").strip()


def _region() -> str:
    """Region for the control-plane client. Mirror the backend's settings
    resolution but tolerate config import failure (this module is imported
    from routes that may run in a stripped env)."""
    try:
        from config import settings
        return settings.aws_region_resolved
    except Exception:
        return os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "us-east-1"


def list_managed_policies() -> Dict[str, Any]:
    """Return the Cedar policies attached to the managed policy engine.

    Shape (compatible with the Agent Trace Policy surface):
        {
            "source": "managed-engine" | "no-engine-id" | "error",
            "policy_engine_id": "<id or ''>",
            "policies": [
                {"id", "name", "description", "cedar"},
                ...
            ],
            "error": "<str>"   # only when source == "error"
        }

    ``cedar`` holds the Cedar statement pulled from the policy's
    ``definition.cedar.statement`` (the direct-Cedar shape the deploy script
    writes). ``applies_to`` is intentionally absent — managed Cedar encodes the
    gated action inside the statement itself (``action == AgentCore::Action::...``)
    rather than in a sidecar field.
    """
    engine_id = _engine_id()
    if not engine_id:
        return {
            "source": "no-engine-id",
            "policy_engine_id": "",
            "policies": [],
        }

    try:
        import boto3
    except Exception as exc:  # pragma: no cover — boto3 always present in deploy env
        logger.warning("boto3 unavailable for managed policy read: %s", exc)
        return {"source": "error", "policy_engine_id": engine_id, "policies": [], "error": str(exc)}

    try:
        client = boto3.client("bedrock-agentcore-control", region_name=_region())
        summaries = client.list_policies(policyEngineId=engine_id).get("policies", [])
        policies: List[Dict[str, Any]] = []
        for summary in summaries:
            policy_id = summary.get("policyId", "")
            name = summary.get("name", policy_id)
            description = summary.get("description", "")
            cedar = ""
            # The list summary may omit the full definition; fetch it per id.
            try:
                detail = client.get_policy(policyEngineId=engine_id, policyId=policy_id)
                description = detail.get("description", description)
                definition = detail.get("definition", {}) or {}
                cedar = (definition.get("cedar", {}) or {}).get("statement", "")
            except Exception as exc:
                logger.debug("get_policy(%s) failed: %s", policy_id, exc)
            policies.append({
                "id": policy_id,
                "name": name,
                "description": description,
                "cedar": cedar,
            })
        return {
            "source": "managed-engine",
            "policy_engine_id": engine_id,
            "policies": policies,
        }
    except Exception as exc:
        logger.warning("Managed policy list failed: %s", exc)
        return {"source": "error", "policy_engine_id": engine_id, "policies": [], "error": str(exc)}


async def recent_decisions(
    db_service: Any,
    *,
    principal_sub: str,
    session_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Return explicit managed-policy receipts for one verified principal.

    Shape:
        {
            "source": "governed-receipts",
            "session_id": "<session or null>",
            "decisions": [
                {"receipt_id", "audit_id", "tool", "caller", "args",
                 "policy_engine_id", "policy_name", "created_at",
                 "decision": "ALLOW" | "DENY"},
                ...
            ],
            "count": <int>,
        }

    ``principal_sub`` is mandatory. The API caller has already verified the
    Cognito subject before it reaches this service, and the SQL scope keeps one
    attendee from inspecting another attendee's policy history.
    """
    sid = session_id or None
    if db_service is None or not principal_sub:
        return {
            "source": "governed-receipts",
            "session_id": sid,
            "decisions": [],
            "count": 0,
        }

    limit = max(1, min(500, int(limit)))
    if session_id:
        sql = (
            "SELECT receipt_id, audit_id, session_id, tool, caller, decision, "
            "args, policy_engine_id, policy_name, created_at "
            "FROM pellier.governed_receipts "
            "WHERE principal_id = %s AND session_id = %s "
            "ORDER BY created_at DESC LIMIT %s"
        )
        params = (principal_sub, session_id, limit)
    else:
        sql = (
            "SELECT receipt_id, audit_id, session_id, tool, caller, decision, "
            "args, policy_engine_id, policy_name, created_at "
            "FROM pellier.governed_receipts "
            "WHERE principal_id = %s ORDER BY created_at DESC LIMIT %s"
        )
        params = (principal_sub, limit)

    try:
        rows = await db_service.fetch_all(sql, *params)
    except Exception as exc:
        logger.warning("Managed decisions (governed_receipts) read failed: %s", exc)
        return {
            "source": "governed-receipts",
            "session_id": sid,
            "decisions": [],
            "count": 0,
            "error": str(exc),
        }

    decisions: List[Dict[str, Any]] = []
    for r in rows or []:
        created = r.get("created_at")
        decisions.append({
            "receipt_id": r.get("receipt_id"),
            "audit_id": r.get("audit_id"),
            "session_id": r.get("session_id"),
            "tool": r.get("tool"),
            "caller": r.get("caller"),
            "args": r.get("args"),
            "policy_engine_id": r.get("policy_engine_id"),
            "policy_name": r.get("policy_name"),
            "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
            "decision": r.get("decision"),
        })
    return {
        "source": "governed-receipts",
        "session_id": sid,
        "decisions": decisions,
        "count": len(decisions),
    }
