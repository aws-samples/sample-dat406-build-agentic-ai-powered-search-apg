"""``/api/observatory/*`` — Pellier Observatory read-only API endpoints.

This router provides the backend data layer for the Pellier Observatory
frontend surfaces. Most endpoints are read-only reference payloads with
graceful degradation when a live dependency is unavailable; the memory
surface is live-only and never serves static memory data.

Endpoints are additive to the existing ``routes/workshop.py`` router
(which also mounts at ``/api/observatory/``). No path conflicts — workshop
owns ``/query``, ``/resume``, ``/tool-registry``; this router owns the
observatory surface endpoints listed below.

Endpoints:
    GET  /sessions             — session list for persona
    GET  /sessions/{id}        — full session detail or 404
    GET  /agents               — 5 agents with status, tools, model config
    GET  /tools/list           — tools with signatures, status, metadata
    POST /tools/discover       — pgvector semantic search
    GET  /routing              — 3 routing patterns with active indicator
    GET  /memory/{persona}     — four memory types plus operational history
    GET  /performance          — metrics and benchmarks
    GET  /evaluations          — agent scorecards
    GET  /architecture         - system architecture diagram payload
    GET  /operator-lineage/{customer_id}
                              - live shopper-to-operator graph and outcome
    GET  /build-state          - shipped vs exercise maps for agents and tools
    GET  /readiness            - workshop readiness checks for live pillars
    GET  /proof-board          - required-path evidence cards and fallbacks
    POST /skills/route         - Live skill router demo (Sonnet 4.6)
    GET  /policies             - Cedar policies for the Write-path surface
    GET  /tool-audit/recent    - Recent rows from pellier.tool_audit
"""

from __future__ import annotations

import json
import logging
import re
import runpy
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
# Aliased: `Path` in this module is `pathlib.Path`, used for filesystem
# reads. Importing FastAPI's under the same name shadowed it and every
# `Path(__file__)` became a path-parameter declaration.
from fastapi import Path as PathParam
from pydantic import BaseModel, Field
from services.auth import require_operator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/observatory", tags=["observatory"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ObservatorySessionSummary(BaseModel):
    """Summary of a single session for the sessions list."""
    id: str
    persona_id: str = Field(alias="personaId")
    opening_query: str = Field(alias="openingQuery")
    elapsed_ms: int = Field(alias="elapsedMs")
    agent_count: int = Field(alias="agentCount")
    routing_pattern: str = Field(alias="routingPattern")
    timestamp: str
    status: str

    model_config = {"populate_by_name": True}


class ObservatoryToolDiscoverRequest(BaseModel):
    """Request body for the tool discovery endpoint."""
    query: str = Field(
        default="show me something for long summer walks",
        min_length=1,
        description="Natural-language query for semantic tool discovery",
    )
    limit: int = Field(default=5, ge=1, le=9)


class ObservatoryToolDiscoverResult(BaseModel):
    """A single tool discovery result with similarity score."""
    rank: int
    tool_id: str
    name: str
    description: str
    similarity: float
    status: str


class ObservatoryToolDiscoverResponse(BaseModel):
    """Response from the tool discovery endpoint."""
    query: str
    results: list[ObservatoryToolDiscoverResult]
    duration_ms: int
    sql: str
    total_count: int


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "src"
    / "observatory"
    / "fixtures"
)

_fixture_cache: dict[str, Any] = {}


def _load_fixture(name: str) -> Any:
    """Load a fixture JSON file from the frontend fixtures directory.

    Results are cached in memory after first load. Returns None if the
    file doesn't exist or can't be parsed.
    """
    if not re.fullmatch(r"[a-z0-9-]{1,128}", name):
        logger.warning("Rejected invalid fixture name")
        return None
    if name in _fixture_cache:
        return _fixture_cache[name]
    path = (_FIXTURE_DIR / f"{name}.json").resolve()
    try:
        path.relative_to(_FIXTURE_DIR.resolve())
    except ValueError:
        logger.warning("Rejected fixture path outside fixture directory")
        return None
    try:
        data = json.loads(path.read_text())
        _fixture_cache[name] = data
        return data
    except FileNotFoundError:
        logger.warning("Fixture file not found: %s", path)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Fixture file malformed: %s — %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Tool / build state helpers (fixtures + workshop live overlay)
# ---------------------------------------------------------------------------


def _fixture_tool_status_map() -> dict[str, str]:
    """functionName → shipped | exercise from tools.json fixtures."""
    tools = _load_fixture("tools") or []
    out: dict[str, str] = {}
    for t in tools:
        fn = t.get("functionName")
        st = t.get("status")
        if isinstance(fn, str) and isinstance(st, str):
            out[fn] = st
    return out


def _tool_discovery_status(tool_name: str) -> str:
    """Status for discovery rows — matches Observatory Tools surface / fixtures."""
    return _fixture_tool_status_map().get(tool_name, "shipped")


def _check_inventory_is_workshop_stub() -> bool:
    """True when the live ``check_inventory`` body still returns the starter stub."""
    try:
        import inspect
        from services import agent_tools

        src = inspect.getsource(agent_tools.check_inventory)
    except Exception:
        return True
    if "check_inventory is in stub state" in src:
        return True
    if "received_product_query" in src:
        return True
    return False


def _inventory_agent_definition_is_workshop_stub() -> bool:
    """True when the Inventory Agent definition still carries the starter stub."""
    try:
        from agents import inventory_agent

        return bool(getattr(inventory_agent, "_INVENTORY_AGENT_STUBBED", False))
    except Exception:
        return True


def _configured(value: Any) -> bool:
    """True when an env/config value is present and non-empty."""
    return bool(str(value or "").strip())


def _gateway_identity_configured(settings: Any) -> bool:
    """True when the governed Gateway helper can mint a Cognito JWT."""
    return all([
        _configured(settings.cognito_pool_id_resolved),
        _configured(settings.COGNITO_CLIENT_ID),
        _configured(getattr(settings, "COGNITO_TEST_CREDENTIALS_SECRET_ARN", None)),
    ])


def _readiness_check(
    *,
    check_id: str,
    label: str,
    state: str,
    detail: str,
    required: bool = True,
    href: str | None = None,
) -> dict[str, Any]:
    """Small serializable readiness row used by Observatory and tests."""
    out: dict[str, Any] = {
        "id": check_id,
        "label": label,
        "state": state,
        "detail": detail,
        "required": required,
    }
    if href:
        out["href"] = href
    return out


async def _workshop_counts() -> dict[str, int] | None:
    """Return the live counts used by the readiness and proof panels.

    None means the database is unavailable. The caller decides whether
    that is a hard fail or a pending proof state.
    """
    try:
        from app import db_service
        if db_service is None:
            return None
        row = await db_service.fetch_one(
            """
            SELECT
              (SELECT count(*) FROM pellier.product_catalog)::int AS catalog_count,
              (SELECT count(*) FROM pellier.warehouse_inventory)::int AS warehouse_count,
              (SELECT count(*) FROM pellier.tool_audit)::int AS audit_count
            """
        )
        if not row:
            return None
        d = dict(row)
        return {
            "catalog_count": int(d.get("catalog_count") or 0),
            "warehouse_count": int(d.get("warehouse_count") or 0),
            "audit_count": int(d.get("audit_count") or 0),
        }
    except Exception as exc:
        logger.warning("Observatory readiness counts unavailable: %s", exc)
        return None


async def _latest_audit_row(
    *,
    principal_sub: str,
    tool: str | None = None,
    caller: str | None = None,
) -> dict[str, Any] | None:
    """Return the latest audit row visible to one verified principal."""
    clauses = ["(gr.principal_id = %s OR gtr.principal_sub = %s)"]
    params: list[Any] = [principal_sub, principal_sub]
    if tool:
        clauses.append("ta.tool = %s")
        params.append(tool)
    if caller:
        clauses.append("ta.caller = %s")
        params.append(caller)
    where = f"WHERE {' AND '.join(clauses)}"
    try:
        from app import db_service
        if db_service is None:
            return None
        row = await db_service.fetch_one(
            f"""
            SELECT ta.audit_id,
                   ta.session_id,
                   ta.tool,
                   ta.caller,
                   ta.args,
                   ta.result,
                   ta.latency_ms,
                   ta.created_at
              FROM pellier.tool_audit ta
              LEFT JOIN pellier.governed_receipts gr
                ON gr.audit_id = ta.audit_id
              LEFT JOIN pellier.governed_turn_receipts gtr
                ON gtr.tool_audit_ids @> jsonb_build_array(
                    jsonb_build_object('audit_id', ta.audit_id)
                )
              {where}
             ORDER BY ta.audit_id DESC
             LIMIT 1
            """,
            *params,
        )
        if not row:
            return None
        d = dict(row)
        if d.get("created_at") is not None:
            d["created_at"] = d["created_at"].isoformat()
        return d
    except Exception as exc:
        logger.warning("Observatory latest audit row unavailable: %s", exc)
        return None


async def _audit_row_by_id(
    audit_id: int | None, *, principal_sub: str
) -> dict[str, Any] | None:
    """Return one audit row only when its receipt belongs to the principal."""
    if not audit_id or not principal_sub:
        return None
    try:
        from app import db_service
        if db_service is None:
            return None
        row = await db_service.fetch_one(
            """
            SELECT ta.audit_id,
                   ta.session_id,
                   ta.tool,
                   ta.caller,
                   ta.args,
                   ta.result,
                   ta.latency_ms,
                   ta.created_at
              FROM pellier.tool_audit ta
              LEFT JOIN pellier.governed_receipts gr
                ON gr.audit_id = ta.audit_id
              LEFT JOIN pellier.governed_turn_receipts gtr
                ON gtr.tool_audit_ids @> jsonb_build_array(
                    jsonb_build_object('audit_id', ta.audit_id)
                )
             WHERE ta.audit_id = %s
               AND (gr.principal_id = %s OR gtr.principal_sub = %s)
             LIMIT 1
            """,
            int(audit_id),
            principal_sub,
            principal_sub,
        )
        if not row:
            return None
        d = dict(row)
        if d.get("created_at") is not None:
            d["created_at"] = d["created_at"].isoformat()
        return d
    except Exception as exc:
        logger.warning("Observatory audit row lookup unavailable: %s", exc)
        return None


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


async def _write_operation_for_execution(
    audit_row: dict[str, Any] | None,
    governed_args: Any,
) -> dict[str, Any] | None:
    """Resolve the idempotency ledger from principal-scoped execution data.

    ``write_operations`` has no principal column of its own. The lookup key is
    therefore accepted only from the already principal-scoped governed receipt
    or its linked audit row; this helper never searches the ledger broadly.
    """
    audit_args = _json_object((audit_row or {}).get("args"))
    receipt_args = _json_object(governed_args)
    idempotency_key = (
        audit_args.get("idempotency_key")
        or audit_args.get("idempotencyKey")
        or receipt_args.get("idempotency_key")
        or receipt_args.get("idempotencyKey")
    )
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        return None
    try:
        from app import db_service
        if db_service is None:
            return None
        row = await db_service.fetch_one(
            """
            SELECT idempotency_key,
                   operation,
                   request_hash,
                   created_at,
                   completed_at,
                   result
              FROM pellier.write_operations
             WHERE idempotency_key = %s
             LIMIT 1
            """,
            idempotency_key.strip(),
        )
        if not row:
            return None
        result = dict(row)
        for field in ("created_at", "completed_at"):
            value = result.get(field)
            if value is not None and hasattr(value, "isoformat"):
                result[field] = value.isoformat()
        return result
    except Exception as exc:
        logger.debug("Observatory write-operation lookup unavailable: %s", exc)
        return None


async def _latest_governed_receipt(
    *,
    principal_sub: str,
    tool: str | None = None,
    caller: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the latest managed policy receipt owned by one principal."""
    clauses = ["gr.principal_id = %s"]
    params: list[Any] = [principal_sub]
    if session_id:
        clauses.append("gr.session_id = %s")
        params.append(session_id)
    if tool:
        clauses.append("gr.tool = %s")
        params.append(tool)
    if caller:
        clauses.append("gr.caller = %s")
        params.append(caller)
    where = f"WHERE {' AND '.join(clauses)}"
    try:
        from app import db_service
        if db_service is None:
            return None
        row = await db_service.fetch_one(
            f"""
            SELECT receipt_id,
                   audit_id,
                   session_id,
                   principal_id,
                   principal_label,
                   tool,
                   caller,
                   decision,
                   args,
                   policy_engine_id,
                   policy_name,
                   token_fingerprint_sha256,
                   verified_subject,
                   verified_username,
                   issuer,
                   client_id,
                   identity_source,
                   created_at
              FROM pellier.governed_receipts gr
              {where}
             ORDER BY gr.receipt_id DESC
             LIMIT 1
            """,
            *params,
        )
        if not row:
            return None
        d = dict(row)
        if d.get("created_at") is not None:
            d["created_at"] = d["created_at"].isoformat()
        return d
    except Exception as exc:
        logger.debug("Observatory governed receipt unavailable: %s", exc)
        return None


def _empty_managed_receipt(session_id: str | None = None) -> dict[str, Any]:
    return {
        "present": False,
        "traceKind": "",
        "runtime": "",
        "rail": "",
        "jwtPassthrough": False,
        "gatewayPassthrough": False,
        "traceId": None,
        "runtimeRequestId": None,
        "sessionId": session_id,
        "managedTrace": {},
        "evidenceProvenance": "",
    }


def _latest_managed_receipt(
    session_id: str | None = None,
    *,
    principal_sub: str,
) -> dict[str, Any]:
    """Return a managed Runtime receipt only from the caller's cache scope."""
    if not session_id or not principal_sub:
        return _empty_managed_receipt(session_id)
    try:
        from services.agentcore_runtime import get_latest_trace

        trace = get_latest_trace(session_id, principal_sub=principal_sub)
    except Exception as exc:
        logger.debug("Managed receipt unavailable: %s", exc)
        return _empty_managed_receipt(session_id)
    return {
        "present": trace.get("traceKind") == "managed-runtime-receipt",
        "traceKind": trace.get("traceKind", ""),
        "runtime": trace.get("runtime", ""),
        "rail": trace.get("rail", ""),
        "jwtPassthrough": bool(trace.get("jwtPassthrough")),
        "gatewayPassthrough": bool(trace.get("gatewayPassthrough")),
        "traceId": trace.get("traceId"),
        "runtimeRequestId": trace.get("runtimeRequestId"),
        "sessionId": trace.get("sessionId") or session_id,
        "managedTrace": (
            trace.get("managedTrace")
            if isinstance(trace.get("managedTrace"), dict)
            else {}
        ),
        "evidenceProvenance": trace.get("evidenceProvenance", ""),
    }


async def _collect_readiness() -> dict[str, Any]:
    """Collect cheap workshop readiness checks without calling Bedrock."""
    from config import settings

    counts = await _workshop_counts()
    checks: list[dict[str, Any]] = []
    governed_format = str(settings.WORKSHOP_FORMAT).lower() == "governed"

    def managed_state(configured: bool) -> str:
        if configured:
            return "pass"
        return "fail" if governed_format else "warn"

    # The flag that GRADES every other governed check has to be checked itself.
    #
    # Found live on 2026-08-27: `WORKSHOP_FORMAT` absent from a backend `.env` made
    # `Settings` default to `builders`, `requires_managed_rail()` returned False, and a
    # real shopper turn executed `initiate_return` in process — no human review, no
    # Cedar verdict, no `tool_audit` receipt. Readiness reported nothing, because it
    # trusted the flag and merely downgraded the other checks from `fail` to `warn`.
    #
    # The deployment SHAPE is detectable independently of the flag: a governed box has
    # a Gateway and a policy engine configured. When those are present and the format
    # is not governed, that is a misconfiguration, not a supported local mode.
    from services.execution_rail import requires_managed_rail

    managed_required = requires_managed_rail("initiate_return")
    governed_shaped = bool(
        str(getattr(settings, "AGENTCORE_GATEWAY_ARN", "") or "").strip()
        and str(getattr(settings, "AGENTCORE_POLICY_ENGINE_ID", "") or "").strip()
    )
    effective_format = str(settings.WORKSHOP_FORMAT or "<unset>")
    if governed_format and managed_required:
        rail_state = "pass"
        rail_detail = (
            f"WORKSHOP_FORMAT={effective_format}. Governed writes are managed-rail "
            "only: initiate_return, issue_credit and restock_inventory cannot run in "
            "process."
        )
    elif governed_format and not managed_required:
        rail_state = "fail"
        rail_detail = (
            f"WORKSHOP_FORMAT={effective_format} but requires_managed_rail() is False. "
            "Configuration and code disagree; governed writes would run unguarded."
        )
    elif governed_shaped:
        rail_state = "fail"
        rail_detail = (
            f"WORKSHOP_FORMAT={effective_format}, but this deployment has a Gateway "
            "and a policy engine configured. Governed writes would execute in process "
            "with no human review, no AgentCore Policy verdict and no tool_audit "
            "receipt. Set WORKSHOP_FORMAT=governed."
        )
    else:
        rail_state = "warn"
        rail_detail = (
            f"WORKSHOP_FORMAT={effective_format}. In-process writes are the supported "
            "behaviour for this lineage; the managed rail is not required."
        )
    checks.append(_readiness_check(
        check_id="managed_rail",
        label="Managed write rail",
        state=rail_state,
        detail=rail_detail,
        required=governed_format or governed_shaped,
    ))

    if counts is None:
        checks.append(_readiness_check(
            check_id="aurora",
            label="Aurora PostgreSQL",
            state="fail",
            detail="Database unavailable to the backend.",  # copy-allow: observatory-readiness-detail
            href="/observatory/search",
        ))
    else:
        catalog_count = counts["catalog_count"]
        warehouse_count = counts["warehouse_count"]
        audit_count = counts["audit_count"]
        warehouse_ready = (
            warehouse_count == 120 if governed_format else warehouse_count > 0
        )
        checks.append(_readiness_check(
            check_id="aurora",
            label="Aurora PostgreSQL",
            state="pass" if catalog_count >= 40 and warehouse_ready else "fail",
            detail=(
                f"Catalog {catalog_count} products, warehouse "
                f"{warehouse_count} rows"
                f"{' (expected exactly 120)' if governed_format else ''}, "
                f"audit ledger {audit_count} rows."
            ),
            href="/observatory/search",
        ))

    cognito_ready = _gateway_identity_configured(settings)
    checks.append(_readiness_check(
        check_id="identity",
        label="Cognito identity",
        state=managed_state(cognito_ready),
        detail=(
            "User pool, app client, and test credential secret configured for JWT passthrough."  # copy-allow: observatory-readiness-detail
            if cognito_ready
            else "Missing Cognito pool/client/test credential secret; Gateway JWT proof cannot run."
        ),
        required=governed_format,
        href="/observatory/production-patterns",
    ))

    memory_configured = _configured(settings.AGENTCORE_MEMORY_ID)
    checks.append(_readiness_check(
        check_id="memory",
        label="AgentCore Memory",
        state=managed_state(memory_configured),
        detail=(
            "AGENTCORE_MEMORY_ID set for working and semantic memory."
            if memory_configured
            else "AGENTCORE_MEMORY_ID empty; working and semantic memory cannot show managed records."
        ),
        required=governed_format,
        href="/observatory/memory",
    ))

    runtime_configured = _configured(settings.AGENTCORE_RUNTIME_ENDPOINT)
    checks.append(_readiness_check(
        check_id="runtime",
        label="AgentCore Runtime",
        state=managed_state(runtime_configured),
        detail=(
            "Runtime endpoint configured; chat can use the managed rail when USE_AGENTCORE_RUNTIME=true."
            if runtime_configured
            else "AGENTCORE_RUNTIME_ENDPOINT empty; managed runtime invoke cannot be demonstrated."
        ),
        required=governed_format,
        href="/observatory/proof-board#managed-rail",
    ))

    gateway_configured = _configured(settings.AGENTCORE_GATEWAY_URL)
    checks.append(_readiness_check(
        check_id="gateway",
        label="AgentCore Gateway",
        state=managed_state(gateway_configured),
        detail=(
            "Gateway URL configured; MCP tool calls can receive the caller JWT."
            if gateway_configured
            else "AGENTCORE_GATEWAY_URL empty; Gateway/JWT tool calls cannot run."
        ),
        required=governed_format,
        href="/observatory/proof-board#managed-rail",
    ))

    policy_engine_id = getattr(settings, "AGENTCORE_POLICY_ENGINE_ID", None)
    policy_configured = _configured(policy_engine_id)
    checks.append(_readiness_check(
        check_id="policy",
        label="AgentCore Policy",
        state=managed_state(policy_configured),
        detail=(
            "Managed Cedar policy engine configured for Gateway enforcement."  # copy-allow: observatory-readiness-detail
            if policy_configured
            else "Policy engine id empty; live Gateway ALLOW/DENY enforcement cannot run."
        ),
        required=governed_format,
        href="/observatory/write-path",
    ))

    model_ids = {
        "opus": settings.BEDROCK_OPUS_MODEL,
        "sonnet": settings.BEDROCK_SONNET_MODEL,
        "router": settings.BEDROCK_ROUTER_MODEL,
        "reporting": settings.BEDROCK_REPORTING_MODEL,
        "embedding": settings.BEDROCK_EMBEDDING_MODEL,
        "rerank": settings.BEDROCK_RERANK_MODEL,
    }
    model_ready = all(_configured(v) for v in model_ids.values())
    checks.append(_readiness_check(
        check_id="models",
        label="Bedrock models",
        state="pass" if model_ready else "fail",
        detail=(
            "Opus, Sonnet, Cohere Embed, and Cohere Rerank model ids are configured."  # copy-allow: observatory-readiness-detail
            if model_ready
            else "One or more model ids are empty; run the model-access preflight."
        ),
        href="/observatory/settings",
    ))

    # The evidence substrate. Added after a live run found the Observatory unable to
    # reconstruct a single operator-rail execution, and the cluster still carrying a
    # database object under a name the contract retired. Both were invisible to
    # readiness, so both shipped.
    substrate = await _evidence_substrate_state()
    checks.append(_readiness_check(
        check_id="evidence_substrate",
        label="Evidence substrate",
        state=substrate["state"],
        detail=substrate["detail"],
        href="/observatory/proof-board",
    ))

    blocking = [c for c in checks if c["required"] and c["state"] == "fail"]
    warnings = [c for c in checks if c["state"] == "warn"]
    status = "ready" if not blocking and not warnings else "attention"
    if blocking:
        status = "not_ready"

    return {
        "status": status,
        "checks": checks,
        "counts": counts or {},
        "models": model_ids,
    }


async def _evidence_substrate_state() -> dict[str, str]:
    """Whether the tables an evidence reconstruction depends on are present and canonical.

    Four conditions, and each one shipped broken at least once:

      * `pellier.execution_receipts` — without it a Cedar DENY is provable only from an
        HTTP response body, and the ReviewRecord reports `policy: PENDING` for an action
        that was refused.
      * `pellier.operator_episodes` with its outcome index — without migration 026's
        index the writer raises a duplicate-key error on 024's index and the best-effort
        handler swallows it, so executions succeed and remember nothing.
      * `pellier.observatory_spans` present — the canonical span table.
      * `pellier.agent_trace_spans` ABSENT — the repository contract retires that name
        for every database object, and this cluster carried it for weeks.

    An unreadable database is `warn`, not `fail`: a local clone with no cluster is a
    legitimate state, and reporting it as a release blocker trains people to ignore the
    panel.
    """
    try:
        from app import db_service
        if db_service is None:
            return {"state": "warn",
                    "detail": "No database connection, so the evidence tables could not be checked."}  # copy-allow: observatory-readiness-detail
        rows = await db_service.fetch_all(
            """
            SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'pellier'
               AND table_name IN ('execution_receipts', 'operator_episodes',
                                  'observatory_spans', 'agent_trace_spans')
            """
        )
        present = {str(r["table_name"]) for r in (rows or [])}
        index_rows = await db_service.fetch_all(
            """
            SELECT indexname FROM pg_indexes
             WHERE schemaname = 'pellier'
               AND indexname = 'operator_episodes_outcome_idx'
            """
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("evidence substrate check unavailable: %s", exc)
        return {"state": "warn",
                "detail": "The evidence tables could not be read."}  # copy-allow: observatory-readiness-detail

    problems: list[str] = []
    for table in ("execution_receipts", "operator_episodes", "observatory_spans"):
        if table not in present:
            problems.append(f"pellier.{table} is missing")
    if "agent_trace_spans" in present:
        problems.append(
            "pellier.agent_trace_spans still exists; run migration 027"
        )
    if "operator_episodes" in present and not index_rows:
        problems.append(
            "operator_episodes_outcome_idx is missing; run migration 026, or every "
            "governed execution will fail to record its episode"
        )
    if problems:
        return {"state": "fail", "detail": ". ".join(problems) + "."}
    return {
        "state": "pass",
        "detail": (
            "Execution receipts, episodic memory and the canonical span table are "  # copy-allow: observatory-readiness-detail
            "present, and the retired trace object is gone."
        ),
    }


def _card_status(condition: bool, fallback: str = "pending") -> str:
    return "complete" if condition else fallback


async def _collect_proof_board(
    session_id: str | None = None, *, principal_sub: str
) -> dict[str, Any]:
    """Build the Observatory proof-card payload.

    The Proof Board is deliberately a read model. It reports evidence
    from source files, env/config, recent traces, and ``tool_audit``.
    It never calls Bedrock, Gateway, or the Runtime.
    """
    from config import settings

    readiness = await _collect_readiness()
    counts = readiness.get("counts") or {}
    governed_format = str(settings.WORKSHOP_FORMAT).lower() == "governed"
    check_inventory_wired = not _check_inventory_is_workshop_stub()
    latest_check_inventory = await _latest_audit_row(
        principal_sub=principal_sub, tool="check_inventory"
    )
    latest_initiate_return = await _latest_audit_row(
        principal_sub=principal_sub, tool="initiate_return"
    )
    latest_audit = await _latest_audit_row(principal_sub=principal_sub)
    latest_gateway = await _latest_audit_row(
        principal_sub=principal_sub, caller="gateway"
    )
    latest_governed = (
        await _latest_governed_receipt(
            principal_sub=principal_sub,
            caller="gateway",
            session_id=session_id,
        )
        if session_id
        else None
    )
    if not latest_governed:
        latest_governed = await _latest_governed_receipt(
            principal_sub=principal_sub, caller="gateway"
        )
    governed_audit = await _audit_row_by_id(
        latest_governed.get("audit_id") if latest_governed else None,
        principal_sub=principal_sub,
    )
    write_operation = await _write_operation_for_execution(
        governed_audit,
        latest_governed.get("args") if latest_governed else {},
    )
    managed_receipt = _latest_managed_receipt(
        session_id, principal_sub=principal_sub
    )
    policy_engine_id = getattr(settings, "AGENTCORE_POLICY_ENGINE_ID", None)

    runtime_configured = _configured(settings.AGENTCORE_RUNTIME_ENDPOINT)
    gateway_configured = _configured(settings.AGENTCORE_GATEWAY_URL)
    policy_configured = _configured(policy_engine_id)
    identity_configured = _gateway_identity_configured(settings)
    managed_rail_proven = all([
        managed_receipt.get("present"),
        managed_receipt.get("runtime") == "agentcore-managed",
        managed_receipt.get("rail") == "gateway-mcp",
        managed_receipt.get("jwtPassthrough"),
        managed_receipt.get("gatewayPassthrough"),
    ])
    governed_decision = latest_governed.get("decision") if latest_governed else ""
    governed_audit_present = bool(governed_audit)
    governed_absence_verified = bool(
        latest_governed
        and governed_decision == "DENY"
        and latest_governed.get("audit_id") is None
    )
    managed_receipt.update({
        "policyConfigured": policy_configured,
        "gatewayAuditPresent": governed_audit_present if latest_governed else bool(latest_gateway),
        "gatewayAuditAbsenceVerified": governed_absence_verified,
        "latestGatewayAuditId": (
            governed_audit.get("audit_id")
            if governed_audit
            else latest_gateway.get("audit_id") if latest_gateway and not latest_governed else None
        ),
        "latestGatewayAuditAt": (
            governed_audit.get("created_at")
            if governed_audit
            else latest_gateway.get("created_at") if latest_gateway and not latest_governed else ""
        ),
        "governedReceiptPresent": bool(latest_governed),
        "latestGovernedReceiptId": latest_governed.get("receipt_id") if latest_governed else None,
        "latestGovernedReceiptAt": latest_governed.get("created_at") if latest_governed else "",
        "governedAuditId": latest_governed.get("audit_id") if latest_governed else None,
        "governedPrincipalId": latest_governed.get("principal_id") if latest_governed else "",
        "governedPrincipalLabel": latest_governed.get("principal_label") if latest_governed else "",
        "governedVerifiedSubject": latest_governed.get("verified_subject") if latest_governed else "",
        "governedVerifiedUsername": latest_governed.get("verified_username") if latest_governed else "",
        "governedIdentitySource": latest_governed.get("identity_source") if latest_governed else "",
        "governedTokenFingerprint": latest_governed.get("token_fingerprint_sha256") if latest_governed else "",
        "governedDecision": governed_decision,
        "governedTool": latest_governed.get("tool") if latest_governed else "",
        "governedPolicyName": latest_governed.get("policy_name") if latest_governed else "",
        "governedArgs": latest_governed.get("args") if latest_governed else {},
        "writeOperationPresent": bool(write_operation),
        "writeOperationKey": (
            write_operation.get("idempotency_key") if write_operation else ""
        ),
        "writeOperationName": (
            write_operation.get("operation") if write_operation else ""
        ),
        "writeOperationCompletedAt": (
            write_operation.get("completed_at") if write_operation else None
        ),
        "absenceCheckDetail": (
            "Gateway/Cedar DENY: governed receipt has no audit_id and no tool_audit row was written."
            if governed_absence_verified
            else ""
        ),
    })

    cards = [
        {
            "id": "marco-floor-check",
            "lab": "Lab 1: Ground Answers in Live Data",
            "group": "Agent and tool evidence",
            "title": "Wire Marco to check_inventory",
            "status": _card_status(check_inventory_wired and bool(latest_check_inventory), "needs_run" if check_inventory_wired else "needs_build"),
            "required": True,
            "surface": "Code Editor + Pellier",
            "summary": "The Inventory Agent tool is wired and Marco's warehouse turn leaves a check_inventory audit row.",
            "evidenceSource": "services.agent_tools.check_inventory + pellier.tool_audit",
            "lastUpdated": latest_check_inventory.get("created_at") if latest_check_inventory else None,
            "evidence": [
                "check_inventory source no longer returns the workshop stub" if check_inventory_wired else "check_inventory still looks like the workshop stub",
                (
                    f"Latest check_inventory row: audit_id {latest_check_inventory.get('audit_id')}"
                    if latest_check_inventory
                    else "No check_inventory row found yet"
                ),
            ],
            "fallback": {
                "label": "Terminal fallback",
                "command": (
                    "curl -s http://localhost:8000/api/agent/chat "
                    "-H 'Content-Type: application/json' "
                    "-d '{\"message\":\"Marco needs the floor count for the Kyoto Linen Overshirt in cedar, size M\",\"session_id\":\"marco-proof\"}'"
                ),
            },
            "links": [
                {"label": "Tools", "to": "/observatory/tools"},
                {"label": "Sessions", "to": "/observatory/sessions"},
            ],
        },
        {
            "id": "retrieval-comparison",
            "lab": "Lab 2: Measure Hybrid Retrieval Trade-offs",
            "group": "Retrieval evidence",
            "title": "Compare Anna's four retrieval strategies",
            "status": (
                "available"
                if int(counts.get("catalog_count") or 0) >= 40
                else "needs_data"
            ),
            "required": True,
            "surface": "Pellier + Code Editor",
            "summary": "Vector, hybrid RRF, hybrid plus rerank, and Anna's agentic path are ready for one quality, latency, and cost comparison.",
            "evidenceSource": "search-strategies/compare + pellier.product_catalog",
            "evidence": [
                f"Catalog rows: {counts.get('catalog_count', 0)}",
                f"Embedding model: {settings.BEDROCK_EMBEDDING_MODEL}",
                f"Rerank model: {settings.BEDROCK_RERANK_MODEL}",
            ],
            "fallback": {
                "label": "Terminal fallback",
                "command": (
                    "curl -s 'http://localhost:8000/api/observatory/search-strategies/compare"
                    "?query=A%20milestone%20gift%20for%20a%20new%20homeowner'"
                ),
            },
            "links": [
                {"label": "Retrieval comparison", "to": "/observatory/performance"},
                {"label": "Search pipeline", "to": "/observatory/search"},
            ],
        },
        {
            "id": "audit-ledger",
            "lab": "Lab 3: Operate the Managed Agent Path",
            "group": "Operational evidence",
            "title": "Prove the tool_audit ledger",
            "status": (
                "complete"
                if latest_initiate_return and latest_governed
                else "needs_run" if not latest_initiate_return
                else "needs_data"
            ),
            "required": True,
            "surface": "Aurora SQL",
            "summary": "Theo's executed return and the seeded principal-versus-customer mismatch are reconstructible without depending on a UI panel.",
            "evidenceSource": "pellier.tool_audit + pellier.governed_receipts",
            "lastUpdated": (
                latest_initiate_return.get("created_at")
                if latest_initiate_return
                else latest_audit.get("created_at") if latest_audit else None
            ),
            "evidence": [
                (
                    f"Latest initiate_return row: audit_id {latest_initiate_return.get('audit_id')}"
                    if latest_initiate_return
                    else "No initiate_return row found yet"
                ),
                (
                    f"Latest audit row: {latest_audit.get('tool')} by {latest_audit.get('caller')}"
                    if latest_audit
                    else "No audit rows found yet"
                ),
                (
                    f"Latest governed receipt: {latest_governed.get('principal_label')} -> {latest_governed.get('decision')}"
                    if latest_governed
                    else "No governed identity receipt found yet"
                ),
            ],
            "fallback": {
                "label": "SQL fallback",
                "command": (
                    "psql \"$DATABASE_URL\" -c \"SELECT audit_id, session_id, tool, caller, args, result "
                    "FROM pellier.tool_audit WHERE tool = 'initiate_return' ORDER BY audit_id DESC LIMIT 3;\""
                ),
            },
            "links": [
                {"label": "Write-path", "to": "/observatory/write-path"},
            ],
        },
        {
            "id": "runtime-gateway-policy",
            "lab": "Lab 4: Govern Actions and Prove Outcomes",
            "group": "Managed boundaries",
            "title": "Inspect the Gateway and Cedar boundary",
            "status": (
                "available"
                if (
                    runtime_configured
                    and gateway_configured
                    and identity_configured
                    and policy_configured
                )
                else "needs_config"
            ),
            "required": governed_format,
            "surface": "Managed governance",
            "summary": "Runtime receives the caller JWT, Gateway discovers tools, and Policy defines the Cedar boundary.",
            "evidenceSource": "pellier/backend/.env + managed policy config",
            "evidence": [
                "Runtime endpoint configured" if runtime_configured else "Runtime endpoint missing",
                "Gateway URL configured" if gateway_configured else "Gateway URL missing",
                "Cognito configured" if identity_configured else "Cognito config incomplete",
                "Policy engine configured" if policy_configured else "Policy engine not configured",
            ],
            "fallback": {
                "label": "Config check",
                "command": "grep -E 'COGNITO|AGENTCORE_(RUNTIME|GATEWAY|POLICY)' pellier/backend/.env",
            },
            "links": [
                {"label": "Write-path", "to": "/observatory/write-path"},
            ],
        },
        {
            "id": "managed-rail",
            "lab": "Lab 3: Operate the Managed Agent Path",
            "group": "Managed boundaries",
            "title": "Prove the managed Runtime and Gateway rail",
            "status": _card_status(
                managed_rail_proven,
                (
                    "needs_run"
                    if runtime_configured and gateway_configured and identity_configured
                    else "needs_config"
                ),
            ),
            "required": governed_format,
            "surface": "Runtime receipt",
            "summary": "After the cross-turn Memory exercise, a managed Runtime turn must preserve the caller JWT and execute through Gateway/MCP.",
            "evidenceSource": "AgentCore Memory timeline + Runtime trace + pellier.tool_audit caller=gateway",
            "lastUpdated": latest_gateway.get("created_at") if latest_gateway else None,
            "evidence": [
                (
                    "AgentCore Memory configured for authenticated session history"
                    if _configured(settings.AGENTCORE_MEMORY_ID)
                    else "AgentCore Memory configuration missing"
                ),
                (
                    f"Managed receipt rail: {managed_receipt.get('rail')}"
                    if managed_receipt.get("present")
                    else "No managed Runtime receipt yet"
                ),
                f"JWT passthrough: {managed_receipt.get('jwtPassthrough')}",
                f"Gateway passthrough: {managed_receipt.get('gatewayPassthrough')}",
                (
                    f"Managed trace id: {managed_receipt.get('traceId')}"
                    if managed_receipt.get("traceId")
                    else "Managed trace id was not reported on the Runtime response"
                ),
                (
                    f"Latest gateway audit row: audit_id {latest_gateway.get('audit_id')}"
                    if latest_gateway
                    else "No caller='gateway' audit row found yet"
                ),
                (
                    f"Latest governed receipt: {latest_governed.get('principal_label')} -> {latest_governed.get('decision')}"
                    if latest_governed
                    else "No governed identity/policy receipt found yet"
                ),
            ],
            "fallback": {
                "label": "Terminal fallback",
                "command": (
                    "curl -N http://localhost:8000/api/agent/chat "
                    "-H 'Content-Type: application/json' "
                    "-H \"Authorization: Bearer $ACCESS_TOKEN\" "
                    "-d '{\"message\":\"Check floor inventory for BK-01\",\"session_id\":\"managed-proof\"}'"
                ),
            },
            "links": [
                {"label": "Memory", "to": "/observatory/memory"},
                {"label": "Proof Board", "to": "/observatory/proof-board#managed-rail"},
                {"label": "Sessions", "to": "/observatory/sessions"},
            ],
        },
    ]

    card_order = {
        "marco-floor-check": 1,
        "retrieval-comparison": 2,
        "managed-rail": 3,
        "audit-ledger": 4,
        "runtime-gateway-policy": 5,
    }
    cards.sort(key=lambda card: card_order.get(card["id"], 99))

    return {
        "status": readiness["status"],
        "readiness": readiness,
        "managedReceipt": managed_receipt,
        "cards": cards,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/sessions")
async def list_sessions(
    persona: Optional[str] = Query(default=None, description="Filter by persona ID"),
):
    """Return session list for the active persona.

    Returns fixture data. When a persona filter is provided, only
    sessions matching that persona are returned.
    """
    try:
        data = _load_fixture("sessions")
        if data is None:
            return []
        if persona:
            data = [s for s in data if s.get("personaId") == persona]
        return data
    except Exception as exc:
        logger.error("Failed to load sessions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load sessions")  # copy-allow: observatory-error-detail


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Return full session detail for a given session ID, or 404.

    Checks for a dedicated fixture file first (e.g., session-7f5a.json),
    then falls back to the sessions list for summary-only data.
    """
    try:
        # Try dedicated session detail fixture
        detail = _load_fixture(f"session-{session_id.lower()}")
        if detail is not None:
            return detail

        # Fall back to sessions list for summary data
        sessions = _load_fixture("sessions")
        if sessions:
            for s in sessions:
                if s.get("id", "").upper() == session_id.upper():
                    return s

        raise HTTPException(status_code=404, detail="Session not found")  # copy-allow: observatory-error-detail
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to load session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load session")  # copy-allow: observatory-error-detail


@router.get("/agents")
async def list_agents():
    """Return 5 agents with status, tools, and model configuration.

    Returns fixture data matching the frontend agents.json shape.
    """
    try:
        data = _load_fixture("agents")
        if data is None:
            return []
        return data
    except Exception as exc:
        logger.error("Failed to load agents: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load agents")  # copy-allow: observatory-error-detail


@router.get("/tools/list")
async def list_tools():
    """Return tools with signatures, status, and metadata (fixture-backed).

    Path is ``/tools/list`` to avoid conflict with the existing
    ``/api/tools`` endpoint on the main app. Returns fixture data
    matching the frontend tools.json shape.
    """
    try:
        data = _load_fixture("tools")
        if data is None:
            return []
        return data
    except Exception as exc:
        logger.error("Failed to load tools: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load tools")  # copy-allow: observatory-error-detail


@router.post("/tools/discover", response_model=ObservatoryToolDiscoverResponse)
async def discover_tools_endpoint(payload: ObservatoryToolDiscoverRequest):
    """Semantic tool discovery via pgvector.

    Attempts to use the real database for live pgvector similarity
    search. Falls back to fixture data when the database is unavailable.
    """
    start = time.time()

    # Try real pgvector discovery
    try:
        from app import db_service
        if db_service is not None:
            from services.embeddings import EmbeddingService
            from services.tool_registry import discover_tools

            emb_service = EmbeddingService()
            query_embedding = emb_service.embed_query(payload.query)
            result = await discover_tools(
                db_service, query_embedding, limit=payload.limit
            )

            if result.get("rows"):
                duration_ms = result.get("duration_ms", 0)
                results = []
                for i, row in enumerate(result["rows"], start=1):
                    results.append(ObservatoryToolDiscoverResult(
                        rank=i,
                        tool_id=row.get("tool_id", row.get("name", "")),
                        name=row.get("name", ""),
                        description=row.get("description", ""),
                        similarity=round(row.get("similarity", 0.0), 4),
                        status=_tool_discovery_status(row.get("name", "")),
                    ))
                return ObservatoryToolDiscoverResponse(
                    query=payload.query,
                    results=results,
                    duration_ms=duration_ms,
                    sql=result.get("sql", ""),
                    total_count=result.get("total_count", len(results)),
                )
    except Exception as exc:
        logger.warning("Live tool discovery failed, falling back to fixture: %s", exc)

    # Fallback: return fixture-based results
    duration_ms = int((time.time() - start) * 1000)
    tools_fixture = _load_fixture("tools")
    if tools_fixture is None:
        return ObservatoryToolDiscoverResponse(
            query=payload.query,
            results=[],
            duration_ms=duration_ms,
            sql="-- fixture fallback (no tools fixture found)",
            total_count=0,
        )

    # Simulate discovery by returning tools sorted by relevance to query
    # (simple keyword overlap heuristic for fixture mode)
    query_lower = payload.query.lower()
    scored: list[tuple[float, dict]] = []
    for tool in tools_fixture:
        name = tool.get("functionName", "")
        desc = tool.get("description", "")
        # Simple keyword overlap score
        words = set(query_lower.split())
        tool_words = set((name + " " + desc).lower().split())
        overlap = len(words & tool_words)
        score = 0.95 - (0.08 * (len(scored))) + (0.02 * overlap)
        scored.append((min(score, 0.99), tool))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for i, (score, tool) in enumerate(scored[: payload.limit], start=1):
        results.append(ObservatoryToolDiscoverResult(
            rank=i,
            tool_id=tool.get("functionName", ""),
            name=tool.get("functionName", ""),
            description=tool.get("description", ""),
            similarity=round(score, 4),
            status=tool.get("status", "shipped"),
        ))

    fixture_sql = (
        "-- fixture fallback\n"
        "WITH q AS (SELECT $1::vector AS emb)\n"
        "SELECT tool_id, name, description,\n"
        "       1 - (description_emb <=> (SELECT emb FROM q)) AS similarity\n"
        "FROM pellier.tools WHERE enabled = true\n"
        "ORDER BY description_emb <=> (SELECT emb FROM q)\n"
        f"LIMIT {payload.limit}"
    )

    return ObservatoryToolDiscoverResponse(
        query=payload.query,
        results=results,
        duration_ms=duration_ms,
        sql=fixture_sql,
        total_count=len(tools_fixture),
    )


@router.get("/routing")
async def list_routing():
    """Return 3 routing patterns with active indicator.

    Returns fixture data matching the frontend routing.json shape.
    """
    try:
        data = _load_fixture("routing")
        if data is None:
            return []
        return data
    except Exception as exc:
        logger.error("Failed to load routing patterns: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load routing patterns")  # copy-allow: observatory-error-detail


_PERSONA_TO_CUSTOMER_ID = {
    "marco": "CUST-MARCO",
    "anna": "CUST-ANNA",
    "theo": "CUST-THEO",
    "fresh": "CUST-FRESH",
}


async def _load_live_episodic(persona: str) -> list:
    """Read persona events, orders, and returns from Aurora."""
    customer_id = _PERSONA_TO_CUSTOMER_ID.get(persona.lower())
    if not customer_id:
        return []
    try:
        from app import db_service
        if db_service is None:
            return []
        rows = await db_service.fetch_all(
            """
            WITH events AS (
                SELECT
                    'seed-' || id::text AS id,
                    summary_text AS content,
                    ts_offset_days,
                    NULL::timestamptz AS happened_at
                  FROM pellier.customer_episodic_seed
                 WHERE customer_id = %s
                UNION ALL
                SELECT
                    'order-' || o.id::text AS id,
                    'Ordered ' || pc.name || ' (' || pc.color || ')' AS content,
                    NULL::int AS ts_offset_days,
                    o.placed_at AS happened_at
                  FROM pellier.orders o
                  JOIN pellier.product_catalog pc
                    ON pc."productId" = o.product_id
                 WHERE o.customer_id = %s
                UNION ALL
                SELECT
                    'return-' || r.id::text AS id,
                    'Return ' || r.status || ' for ' || pc.name || ' - reason: ' || r.reason AS content,
                    NULL::int AS ts_offset_days,
                    r.requested_at AS happened_at
                  FROM pellier.returns r
                  JOIN pellier.product_catalog pc
                    ON pc."productId" = r.product_id
                 WHERE r.customer_id = %s
            )
            SELECT id, content, ts_offset_days, happened_at
              FROM events
             ORDER BY happened_at DESC NULLS LAST,
                      ts_offset_days DESC NULLS LAST,
                      id DESC
             LIMIT 20
            """,
            customer_id,
            customer_id,
            customer_id,
        )
        if not rows:
            return []
        items = []
        for r in rows:
            d = dict(r)
            items.append({
                "id": f"ep-live-{d.get('id')}",
                "content": d.get("content", ""),
                "substrate": "episodic",
                "tsOffsetDays": d.get("ts_offset_days"),
                "timestamp": d.get("happened_at").isoformat()
                if d.get("happened_at") is not None
                else None,
            })
        return items
    except Exception as exc:
        logger.warning("Live episodic read failed for %s: %s", persona, exc)
        return []


async def _load_live_procedural() -> list:
    """Read procedural knowledge from runtime skills and MCP schemas.

    Procedural memory is the checked-in know-how that tells the agent how
    work should be performed. Runtime skills provide conditional instructions;
    the canonical Gateway schemas provide the tool contracts. This helper reads
    both real source surfaces and never derives know-how from execution logs.
    """
    items = []
    try:
        from skills import get_registry

        for skill in get_registry().get_all():
            items.append({
                "id": f"proc-skill-{skill.name}",
                "content": (
                    f"Runtime skill {skill.name} v{skill.version}: "
                    f"{skill.description}"
                ),
                "substrate": "procedural",
            })
    except Exception as exc:
        logger.warning("Runtime skill registry read failed: %s", exc)

    schema_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "deploy"
        / "gateway_tool_schemas.py"
    )
    try:
        tool_surfaces = runpy.run_path(str(schema_path)).get("TOOL_SCHEMAS", {})
        for surface, config in sorted(tool_surfaces.items()):
            tool_names = [
                str(tool.get("name", ""))
                for tool in config.get("tools", [])
                if tool.get("name")
            ]
            items.append({
                "id": f"proc-mcp-{surface}",
                "content": (
                    f"MCP {surface} contract: {', '.join(tool_names)}"
                ),
                "substrate": "procedural",
            })
    except Exception as exc:
        logger.warning("Canonical MCP schema read failed from %s: %s", schema_path, exc)

    return items


async def _load_live_operational_history() -> list:
    """Aggregate live tool_audit rows into operational evidence.

    Every ALLOWed tool call writes to pellier.tool_audit (reads and
    writes alike), so this aggregate covers the full per-tool signal.
    What we can honestly surface today is per-tool call counts and
    average latency — the same shape an intent-aware aggregate will
    take once intent / persona_id / success columns land on the table.
    """
    try:
        from app import db_service
        if db_service is None:
            return []
        rows = await db_service.fetch_all(
            """
            SELECT tool,
                   count(*)::int AS calls,
                   round(avg(latency_ms)::numeric, 0)::int AS avg_ms
              FROM pellier.tool_audit
             GROUP BY tool
             ORDER BY calls DESC, tool ASC
             LIMIT 6
            """,
        )
        if not rows:
            return []
        items = []
        for i, r in enumerate(rows):
            d = dict(r)
            items.append({
                "id": f"operational-live-{i}",
                "content": (
                    f"{d.get('tool')} - fired {d.get('calls')}x, "
                    f"avg {d.get('avg_ms')}ms"
                ),
                "substrate": "operational",
            })
        return items
    except Exception as exc:
        logger.warning("Live operational-history read failed: %s", exc)
        return []


async def _load_live_working(persona: str) -> list:
    """Read the persona's most recent storefront working-memory turns.

    This panel is persona-scoped and carries no session id, so we
    resolve the persona's latest Pellier session the same way the
    lab's section-3 readback does: every allowed tool call stamps its
    ``session_id`` in ``pellier.tool_audit`` (shaped
    ``persona-{persona}-{uuid}``), so we take the most recent one for
    this persona, rebuild the anonymous namespace the storefront wrote
    under (``anon-{session_id}``), and read it back through
    ``AgentCoreMemory.get_session_history`` — which transparently serves
    the live AgentCore SDK on a provisioned box or the process-local
    live session buffer used for offline local development. This is the
    SAME data ``GET
    /api/agent/session/{id}`` returns, so the panel and that API agree.

    Returns ``[]`` when the persona has no storefront session yet or the
    read comes back empty. No fixture data is used.
    """
    if persona.lower() not in _PERSONA_TO_CUSTOMER_ID:
        return []
    try:
        from app import db_service
        if db_service is None:
            return []
        # Scope to this persona so a different persona's later tool call
        # (e.g. Anna carrying over) can't shadow Marco's session — the
        # same guard the section-3 psql query uses.
        row = await db_service.fetch_one(
            """
            SELECT session_id
              FROM pellier.tool_audit
             WHERE session_id LIKE %s
             ORDER BY audit_id DESC
             LIMIT 1
            """,
            f"persona-{persona.lower()}-%",
        )
        if not row:
            return []
        session_id = dict(row).get("session_id")
        if not session_id:
            return []

        from services.agentcore_identity import AgentCoreIdentityService
        from services.agentcore_memory import AgentCoreMemory

        # Storefront turns are anonymous, so they live under
        # anon-{session_id} — the exact namespace an unauthenticated
        # GET /api/agent/session/{id} reads.
        namespace = AgentCoreIdentityService.build_namespace(None, session_id)
        memory = AgentCoreMemory()
        turns = await memory.get_session_history(namespace)
    except Exception as exc:
        logger.warning("Live working read failed for %s: %s", persona, exc)
        return []
    if not turns:
        return []
    items = []
    for i, t in enumerate(turns[-6:]):
        items.append({
            "id": f"wk-live-{i}",
            "content": str(t.get("content", ""))[:160],
            "substrate": "working",
            "timestamp": t.get("timestamp"),
        })
    return items


async def _load_live_semantic(persona: str) -> list:
    """Read durable, *extracted* preferences from AgentCore Memory.

    These are the semantic records a ``USER_PREFERENCE`` extraction
    strategy learns from conversation and writes under
    ``/pellier/preferences/{customer_id}/`` — learned prose, not the
    typed onboarding ``Preferences`` blob. We read them with the
    dedicated ``get_semantic_memories`` method (NOT
    ``get_user_preferences``, which serves storefront personalization).

    Returns one item per extracted preference string, or [] when the
    strategy has not produced records yet (SDK absent, extraction still
    settling, or memory unprovisioned). No fixture data is used.
    """
    customer_id = _PERSONA_TO_CUSTOMER_ID.get(persona.lower())
    if not customer_id:
        return []
    try:
        from services.agentcore_memory import AgentCoreMemory
        memory = AgentCoreMemory()
        preferences = await memory.get_semantic_memories(customer_id)
    except Exception as exc:
        logger.warning("Live semantic read failed for %s: %s", persona, exc)
        return []
    if not preferences:
        return []
    items = []
    for idx, pref in enumerate(preferences):
        text = str(pref).strip()
        if not text:
            continue
        items.append({
            "id": f"sem-live-{idx}",
            "content": text[:200],
            "substrate": "semantic",
        })
    return items


def _live_substrate(
    label: str,
    store: str,
    caveat: str = "",
    source: str = "live",
) -> dict:
    panel = {
        "label": label,
        "store": store,
        "source": source,
        "items": [],
    }
    if caveat:
        panel["caveat"] = caveat
    return panel


@router.get("/memory/{persona}")
async def get_memory(persona: str):
    """Return four memory types plus operational history for a persona.

    Each source is explicit:
      working    — AgentCore Memory session turns for the persona's
                   latest storefront session (resolved from
                   pellier.tool_audit, read back under anon-{sid} via
                   the same path as GET /api/agent/session/{id}); live
                   when that session has turns.
      semantic   — AgentCore Memory long-term records under
                   /pellier/preferences/{customer_id}/, extracted by a
                   USER_PREFERENCE strategy; live when the strategy has
                   produced records.
      episodic   — pellier.customer_episodic_seed rows; live when the
                   DB is reachable and the persona has rows.
      procedural — checked-in runtime skills plus canonical MCP tool
                   schemas; these are instructions and contracts.
      operational— pellier.tool_audit aggregate (calls + average
                   latency per tool). This is evidence of execution,
                   not memory.

    Read-only.
    """
    try:
        # Real semantic namespace = the USER_PREFERENCE strategy's
        # custom template resolved for this persona's customer_id
        # (e.g. /pellier/preferences/CUST-MARCO/). Falls back to the
        # raw persona for unknown personas so the store string is never
        # blank.
        _sem_customer_id = _PERSONA_TO_CUSTOMER_ID.get(persona.lower(), persona)
        _sem_store = f"/pellier/preferences/{_sem_customer_id}/"

        data = {
            "persona": persona,
            "working": _live_substrate(
                "Working - AgentCore Memory",
                f"anon-persona-{persona}-{{sid}}",
                "No live session turns found yet. Create a Pellier turn for this persona, then reload.",
            ),
            "semantic": _live_substrate(
                "Semantic - AgentCore Memory",
                _sem_store,
                (
                    "No USER_PREFERENCE records found yet. Extraction is "
                    "asynchronous after conversation; this panel stays empty "
                    "until AgentCore Memory has durable preference records."
                ),
                "settling",
            ),
            "episodic": _live_substrate(
                "Episodic - Aurora",
                "pellier.customer_episodic_seed + orders + returns",
                "No live Aurora events found for this persona yet.",
            ),
            "procedural": _live_substrate(
                "Procedural - source controlled",
                "skills/*/SKILL.md + scripts/deploy/gateway_tool_schemas.py",
                "No runtime skills or canonical MCP schemas were readable.",
            ),
            "operational": _live_substrate(
                "Operational History - Aurora",
                "pellier.tool_audit (aggregate)",
                "No live tool_audit rows found yet. Run a turn that calls a tool, then reload.",
            ),
        }

        data["working"]["items"] = await _load_live_working(persona)
        if data["working"]["items"]:
            data["working"].pop("caveat", None)

        data["semantic"]["items"] = await _load_live_semantic(persona)
        if data["semantic"]["items"]:
            data["semantic"]["source"] = "live"
            data["semantic"].pop("caveat", None)

        data["episodic"]["items"] = await _load_live_episodic(persona)
        if data["episodic"]["items"]:
            data["episodic"].pop("caveat", None)

        data["procedural"]["items"] = await _load_live_procedural()
        if data["procedural"]["items"]:
            data["procedural"].pop("caveat", None)

        data["operational"]["items"] = await _load_live_operational_history()
        if data["operational"]["items"]:
            data["operational"].pop("caveat", None)

        return data
    except Exception as exc:
        logger.error("Failed to load memory for %s: %s", persona, exc)
        raise HTTPException(status_code=500, detail="Failed to load memory state")  # copy-allow: observatory-error-detail


@router.get("/performance")
async def get_performance():
    """Return performance metrics and benchmarks.

    Returns fixture data matching the frontend performance.json shape.
    """
    try:
        data = _load_fixture("performance")
        if data is None:
            return {
                "coldStartP50": 0,
                "warmReuseP50": 0,
                "sampleCount": 0,
                "histogram": [],
                "latencyBudget": [],
                "pgvectorComparison": [],
                "storageUsage": [],
            }
        return data
    except Exception as exc:
        logger.error("Failed to load performance data: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load performance data")  # copy-allow: observatory-error-detail


@router.get("/evaluations")
async def get_evaluations():
    """Return agent evaluation scorecards with explicit provenance.

    Three states are distinguishable, and they are never interchangeable:

    ``fixture``
        Illustrative scorecards shipped with the repo. They describe no
        run at all — they exist so the surface has shape before anything
        has been evaluated.
    ``local-gate``
        The deterministic golden-set gate
        (``tests/test_golden_journeys.py`` plus
        ``scripts/eval_retrieval_harness.py``). Real current commit, real
        thresholds, fixture/golden input.
    ``managed``
        A real AgentCore batch evaluation over recorded sessions, scored
        by the deployed Runtime and correlated to CloudWatch traces.

    A scorecard styled the same way in all three states invites an
    attendee to read fixture illustrations as measured results, which is
    the confusion this envelope prevents.
    """
    try:
        from services import agentcore_evals

        data = _load_fixture("evaluations")
        managed = agentcore_evals.describe_configuration()
        return {
            "provenance": "managed" if managed["configured"] else "fixture",
            "states": {
                "fixture": {
                    "label": "Fixture / reference",
                    "available": data is not None,
                    "describes": "illustrative only — no run",
                },
                "localGate": {
                    "label": "Local deterministic gate",
                    "available": True,
                    "describes": "real current commit, golden input",
                    "sources": [
                        "tests/test_golden_journeys.py",
                        "scripts/eval_retrieval_harness.py",
                    ],
                },
                "managed": {
                    "label": "Managed AgentCore evaluation",
                    "available": managed["configured"],
                    "describes": (
                        "real deployed Runtime, trace-backed"
                        if managed["configured"]
                        else "not provisioned — read the local gate instead"
                    ),
                    "operation": managed["operation"],
                    "configuration": managed,
                },
            },
            "scorecards": data if data is not None else [],
        }
    except Exception as exc:
        logger.error("Failed to load evaluations: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load evaluations")  # copy-allow: observatory-error-detail


@router.get("/architecture")
async def get_architecture():
    """Return the architecture diagram payload for the Observatory Understand surface."""
    try:
        data = _load_fixture("architecture")
        if data is None:
            return {}
        return data
    except Exception as exc:
        logger.error("Failed to load architecture: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load architecture")  # copy-allow: observatory-error-detail


@router.get("/build-state")
async def get_build_state():
    """Shipped vs exercise for agents and tools (fixtures + live lab overlay).

    Loads ``agents.json`` / ``tools.json`` then overlays live workshop
    state from source files. Inventory Agent is shipped once its definition
    scaffold is completed; ``check_inventory`` is shipped once the tool body
    no longer returns the starter stub.

    Shape matches ``BuildStateApiResponse`` in the frontend ``useBuildState`` hook.
    """
    try:
        agents = _load_fixture("agents") or []
        tools = _load_fixture("tools") or []
        agent_map: dict[str, str] = {}
        tool_map: dict[str, str] = {}
        for agent in agents:
            name = agent.get("name")
            status = agent.get("status")
            if isinstance(name, str) and isinstance(status, str):
                agent_map[name] = status
        for tool in tools:
            fn = tool.get("functionName")
            status = tool.get("status")
            if isinstance(fn, str) and isinstance(status, str):
                tool_map[fn] = status

        if not _inventory_agent_definition_is_workshop_stub():
            agent_map["Inventory Agent"] = "shipped"

        if not _check_inventory_is_workshop_stub():
            tool_map["check_inventory"] = "shipped"

        return {"agents": agent_map, "tools": tool_map}
    except Exception as exc:
        logger.error("Failed to build build-state: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load build state")  # copy-allow: observatory-error-detail


@router.get("/readiness")
async def get_workshop_readiness():
    """Return cheap readiness checks for the live workshop pillars.

    This is the API version of ``scripts/health-gate.sh`` for the
    Observatory. It does not call Bedrock, Runtime, Gateway, or Policy; it
    only reads config and small Aurora counts so participants can open
    the panel without triggering managed services.
    """
    try:
        return await _collect_readiness()
    except Exception as exc:
        logger.error("Failed to build readiness payload: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load readiness")  # copy-allow: observatory-error-detail


@router.get("/proof-board")
async def get_proof_board(
    session_id: Optional[str] = Query(
        default=None,
        description="Session id for the latest managed Runtime receipt",
    ),
    operator: dict[str, Any] = Depends(require_operator),
):
    """Return required-path proof cards plus terminal fallbacks.

    The payload is intentionally operational: each card has a stable
    ``id`` for URL anchors, a status, short evidence lines, and a
    curl/SQL fallback. The frontend renders it at
    ``/observatory/proof-board`` and Pellier trace chips deep-link to
    individual anchors.
    """
    try:
        return await _collect_proof_board(
            session_id=session_id, principal_sub=operator["sub"]
        )
    except Exception as exc:
        logger.error("Failed to build proof-board payload: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load proof board")  # copy-allow: observatory-error-detail


class ObservatorySkillRouteRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


@router.post("/skills/route")
async def route_skills_endpoint(payload: ObservatorySkillRouteRequest):
    """Live skill-router demo for the Observatory Skills surface.

    Calls services/skills.SkillRouter.route() against the user query
    and returns the same RouterDecision shape the chat pipeline emits
    as an SSE skill_routing event:
        {loaded_skills, considered, elapsed_ms, user_message}

    Read-only; never raises. Returns an empty decision on any failure
    (matches the chat pipeline's behavior — skills stay dormant if the
    router can't decide).
    """
    try:
        from skills import SkillRouter, get_registry
        skill_router = SkillRouter(get_registry())
        decision = skill_router.route(payload.query)
        return {
            "loaded_skills": list(decision.loaded_skills or []),
            "considered": list(decision.considered or []),
            "elapsed_ms": int(decision.elapsed_ms or 0),
            "user_message": payload.query[:500],
        }
    except Exception as exc:
        logger.warning("Observatory skill route failed: %s", exc)
        return {
            "loaded_skills": [],
            "considered": [],
            "elapsed_ms": 0,
            "user_message": payload.query[:500],
            "error": "skill_routing_unavailable",
        }


@router.get("/policies")
async def get_cedar_policies(operator: dict[str, Any] = Depends(require_operator)):
    """Return the Cedar policies attached to the managed AgentCore Policy
    engine (Gateway-enforced, ENFORCE mode). Used by the Observatory's
    Write-path surface to show "policy is code, code is enforcement".

    Reads the managed engine via boto3 ``bedrock-agentcore-control``
    keyed on ``AGENTCORE_POLICY_ENGINE_ID``. The old local fake-Cedar
    ``PolicyService`` was removed — the Gateway is the one gate now.
    ``cedar`` carries the managed policy's Cedar statement; managed
    policies have no ``applies_to`` sidecar (the gated action is encoded
    inside the Cedar statement itself), so it is reported as null.
    """
    try:
        from services.managed_policy import list_managed_policies
        result = list_managed_policies()
        policies = result.get("policies", [])
        return {
            "count": len(policies),
            "source": result.get("source"),
            "policy_engine_id": result.get("policy_engine_id", ""),
            "policies": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "description": p.get("description"),
                    "applies_to": None,
                    "cedar": p.get("cedar"),
                }
                for p in policies
            ],
        }
    except Exception as exc:
        logger.error("Failed to load policies: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load policies")  # copy-allow: observatory-error-detail


@router.get("/executions")
async def list_governed_executions(
    limit: int = Query(default=20, ge=1, le=50),
    operator: dict[str, Any] = Depends(require_operator),
):
    """Governed operator executions this principal performed, newest first.

    Read-only and principal-scoped. The visibility authority is
    ``execution_receipts.actor_principal`` — the operator AgentCore Policy authorized —
    which is the operator-rail counterpart of ``governed_receipts.principal_id``. No
    existing filter was weakened to make these rows appear.
    """
    try:
        from app import db_service
        if db_service is None:
            return {"count": 0, "executions": []}

        from services.governed_execution import list_executions

        rows = await list_executions(
            db_service, principal_sub=operator["sub"], limit=limit
        )
        return {"count": len(rows), "executions": rows}
    except Exception as exc:
        logger.error("Failed to list governed executions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list executions")  # copy-allow: observatory-error-detail


@router.get("/operator-lineage/{customer_id}")
async def get_operator_lineage(
    customer_id: str = PathParam(..., min_length=1, max_length=64),
    review_id: int | None = Query(default=None, ge=1),
    operator: dict[str, Any] = Depends(require_operator),
):
    """Reconstruct the live storefront-to-operator loop for one client.

    No fixture fallback. The handoff is untrusted context from the append-only
    shopper receipt; the review is the durable human checkpoint; graph metadata
    comes from an actually persisted Operator Concierge artifact; execution
    evidence is principal-scoped to the operator who performed it.
    """
    from app import db_service

    if db_service is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    from services import governed_execution
    from services import operator_concierge_sessions as sessions
    from services import operator_review
    from services import shopper_handoff
    from services.data_source import database_source_label

    try:
        if review_id is None:
            handoff = await shopper_handoff.resolve_latest_for_customer(
                db_service, customer_id=customer_id
            )
        else:
            handoff = await shopper_handoff.resolve_for_review(
                db_service,
                review_id=review_id,
                expected_customer_id=customer_id,
            )
    except shopper_handoff.HandoffIntegrityError as exc:
        logger.error("Operator lineage mismatch for %s", customer_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Operator lineage handoff read failed for %s: %s", customer_id, exc)
        raise HTTPException(status_code=503, detail="operator_lineage_unavailable") from exc

    if not handoff:
        return {
            "customerId": customer_id,
            "dataSource": database_source_label(),
            "handoff": None,
            "review": None,
            "orchestration": None,
            "execution": None,
        }

    review_id = int((handoff.get("proposal") or {}).get("reviewId") or 0)
    review_row = await operator_review.get_review(db_service, review_id)
    if not review_row or str(review_row.get("customer_id") or "") != customer_id:
        raise HTTPException(status_code=409, detail="shopper_handoff_lineage_mismatch")

    receipt = await governed_execution.latest_receipt(db_service, review_id)
    review = {
        "reviewId": review_id,
        "customerId": customer_id,
        "customerName": review_row.get("customer_name") or customer_id,
        "action": review_row.get("action"),
        "status": review_row.get("status"),
        "sourceTurnId": review_row.get("source_turn_id"),
        "executionTurnId": review_row.get("execution_turn_id"),
        "actionHash": review_row.get("action_hash"),
        "requestedAt": (
            review_row["requested_at"].isoformat()
            if hasattr(review_row.get("requested_at"), "isoformat")
            else review_row.get("requested_at")
        ),
        "decidedAt": (
            review_row["decided_at"].isoformat()
            if hasattr(review_row.get("decided_at"), "isoformat")
            else review_row.get("decided_at")
        ),
    }

    orchestration = None
    try:
        graph_artifact = await sessions.load_graph_artifact_for_review(
            db_service,
            customer_id=customer_id,
            review_id=review_id,
            action_hash=str(review.get("actionHash") or ""),
        )
        if graph_artifact:
            orchestration = {
                **graph_artifact["orchestration"],
                "sessionId": graph_artifact.get("sessionId"),
                "turnId": graph_artifact.get("turnId"),
            }
    except Exception as exc:  # noqa: BLE001 - review lineage remains useful
        logger.warning(
            "Operator graph artifact unavailable for review %s: %s",
            review_id,
            exc,
        )

    execution = None
    if receipt:
        execution = await governed_execution.reconstruct_execution(
            db_service,
            review_id=review_id,
            principal_sub=str(operator["sub"]),
        )

    return {
        "customerId": customer_id,
        "customerName": review["customerName"],
        "dataSource": database_source_label(),
        "handoff": handoff,
        "review": review,
        "orchestration": orchestration,
        "execution": execution,
    }


@router.get("/executions/{review_id}")
async def reconstruct_governed_execution(
    review_id: int = PathParam(..., ge=1),
    operator: dict[str, Any] = Depends(require_operator),
):
    """One governed execution, reconstructed layer by layer from durable artifacts.

    The spine is the execution receipt, not ``tool_audit``. For a governed system,
    execution evidence begins at the authorization attempt: a Cedar DENY correctly
    writes no audit row and claims no idempotency key, and a reconstruction rooted at
    the tool cannot render it at all. Each layer reports whether it is present and why,
    so an absent layer reads as the evidence it is rather than as missing data.
    """
    try:
        from app import db_service
        if db_service is None:
            raise HTTPException(status_code=503, detail="database_unavailable")

        from services.governed_execution import reconstruct_execution

        story = await reconstruct_execution(
            db_service, review_id=review_id, principal_sub=operator["sub"]
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Reconstruction failed for review %s: %s", review_id, exc)
        raise HTTPException(status_code=500, detail="Failed to reconstruct execution")  # copy-allow: observatory-error-detail

    if story is None:
        # Either nothing was executed, or it was executed by a different principal.
        # One status for both on purpose: distinguishing them would tell a caller that
        # an execution they may not read exists.
        raise HTTPException(status_code=404, detail="no_execution_for_principal")
    return story


@router.get("/tool-audit/recent")
async def get_recent_tool_audit(
    limit: int = Query(default=10, ge=1, le=50),
    operator: dict[str, Any] = Depends(require_operator),
):
    """Return the most recent rows from pellier.tool_audit, in reverse
    chronological order. Used by the Write-path surface to demonstrate
    that every ALLOWed tool call (read or write) is reconstructible
    from a single row (args + result + latency_ms).

    Read-only and principal-scoped. An audit row must be joined to either an
    explicit policy receipt or a durable governed turn receipt for the
    verified caller; raw ledger history is never a browser-wide feed.
    """
    try:
        from app import db_service
        if db_service is None:
            return {"count": 0, "rows": []}

        from services.governed_turn_receipt import get_visible_tool_audit

        normalized = await get_visible_tool_audit(
            db_service, principal_sub=operator["sub"], limit=limit
        )
        return {"count": len(normalized), "rows": normalized}
    except Exception as exc:
        logger.error("Failed to load tool_audit: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load tool audit")  # copy-allow: observatory-error-detail
