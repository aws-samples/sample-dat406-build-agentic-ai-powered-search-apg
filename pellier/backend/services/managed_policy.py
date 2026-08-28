"""
Managed AgentCore Policy — read surface for the Gateway-enforced Cedar engine.

Pellier's policy gate is a **managed AgentCore Policy Engine** attached to
the AgentCore Gateway in ENFORCE mode by the declarative AgentCore CLI project.
The Gateway intercepts every tool call and evaluates it against Cedar BEFORE
the Lambda runs — argument-aware, default-deny, forbid-wins. This replaced the
old local ``BeforeToolCall`` hook + hand-rolled fake-Cedar engine (both removed).

This module is the **read side** of that managed gate. It does NOT enforce
anything (the Gateway does) — it just lets the Observatory Policy surface show, live,
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
than raising, so the Observatory surface degrades to "(no policies)" instead of a
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
    """The policy engine id, from settings first and the environment second.

    `Settings` loads `.env` into the settings OBJECT, not into `os.environ`. Reading
    only the environment therefore returned "" on every normally-configured backend,
    `engine_state_for_action` returned None, and `resolve_permissive_policy_state`
    downgraded every Gateway ALLOW to NOT_EVALUATED. The workshop's single most
    important positive claim — AgentCore Policy ALLOW — was unreachable, and it failed
    in the honest direction, which is why nothing looked broken.

    Same try-settings-then-environment shape as `_region()` below, so this module
    tolerates being imported from a stripped env without silently losing config in a
    complete one.
    """
    try:
        from config import settings

        from_settings = str(
            getattr(settings, _ENGINE_ID_ENV, "") or ""
        ).strip()
        if from_settings:
            return from_settings
    except Exception:  # pragma: no cover - stripped-env import path
        pass
    return os.environ.get(_ENGINE_ID_ENV, "").strip()


def policy_engine_id() -> str:
    """The configured policy engine id, or "" when this deployment has none.

    Public because an execution receipt has to name which engine produced its verdict:
    the same word ALLOW means different things from different engines, and an
    unattributed verdict is not evidence.
    """
    return _engine_id()


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

    Shape (compatible with the Observatory Policy surface):
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


async def engine_state_for_action(action_id: str):
    """The policy engine's declared state, filtered to one Gateway action.

    Reads the control plane rather than a local table: the enforcement mode and
    the policy statements are the engine's own facts, and they are what decides
    whether a Gateway call that returned was an authorization or an unenforced
    observation.

    Enforcement is the conjunction of two scopes with different vocabularies,
    verified against the live service: a policy is ``ACTIVE`` or ``LOG_ONLY``; a
    gateway attachment is ``ENFORCE`` or ``LOG_ONLY``. Both are reported so the
    caller can classify without assuming one vocabulary covers both.

    Args:
        action_id: The target-qualified Cedar action, e.g.
            ``pellier-concierge-experience-target___initiate_return``.

    Returns:
        A ``services.governed_execution.PolicyEngineState``, or ``None`` when the
        engine cannot be read. ``None`` is a legitimate answer and the caller
        must not treat it as permission.
    """
    from services.governed_execution import PolicyEngineState

    engine_id = _engine_id()
    if not engine_id:
        return None

    import boto3

    client = boto3.client("bedrock-agentcore-control", region_name=_region())

    # `settings` is imported here, not at module scope: this module tolerates being
    # imported from a stripped env. The reference below was previously bare, which was
    # a NameError waiting behind the `not engine_id` guard — with the engine id never
    # resolving, this line was unreachable and the gateway-mode read was dead code.
    gateway_mode = ""
    try:
        from config import settings as _settings

        gateway_arn = str(
            getattr(_settings, "AGENTCORE_GATEWAY_ARN", "") or ""
        ).strip()
    except Exception:  # pragma: no cover - stripped-env import path
        gateway_arn = os.environ.get("AGENTCORE_GATEWAY_ARN", "").strip()
    if gateway_arn:
        gateway_id = gateway_arn.rsplit("/", 1)[-1]
        gateway = client.get_gateway(gatewayIdentifier=gateway_id)
        gateway_mode = str(
            (gateway.get("policyEngineConfiguration") or {}).get("mode") or ""
        )

    policies: Dict[str, tuple] = {}
    matching: list[str] = []
    for summary in client.list_policies(policyEngineId=engine_id).get("policies", []):
        detail = client.get_policy(
            policyEngineId=engine_id, policyId=summary["policyId"]
        )
        name = str(detail.get("name") or summary.get("policyId"))
        statement = str(
            (detail.get("definition") or {}).get("cedar", {}).get("statement") or ""
        )
        # The effect is read from the statement rather than a response field: the
        # control plane does not return `effect` on this shape, and inferring
        # "forbid" from a name would break the moment a policy is renamed.
        effect = "forbid" if statement.lstrip().startswith("forbid") else "permit"
        policies[name] = (effect, str(detail.get("enforcementMode") or ""))
        if effect == "forbid" and action_id in statement:
            matching.append(name)

    return PolicyEngineState(
        gateway_mode=gateway_mode,
        policies=policies,
        matching_forbids=tuple(matching),
    )
