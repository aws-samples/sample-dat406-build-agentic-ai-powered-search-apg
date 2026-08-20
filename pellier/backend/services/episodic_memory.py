"""episodic_memory — Aurora-backed episodic recall for memory panels.

Teaching frame: AgentCore Memory owns session history in production.
The Observatory demo needs deterministic, pre-seeded episodes so a
workshop attendee picking "Marco" sees continuity from a real database
read. The table it reads from is ``pellier.customer_episodic_seed``,
seeded by migration 003, and later code can blend in orders / returns.

Two callers:

- ``routes/workshop.py`` — invokes ``emit_memory_episodic_panel`` when
  the turn's customer_id is not anonymous so the right-rail telemetry
  tab shows a real MEMORY · EPISODIC card on the resume turn.
- ``routes/observatory_observatory.py`` — the Memory page uses direct Aurora
  reads for episodic state and keeps AgentCore for working / semantic memory.

Failure semantics: on any DB or schema error we emit a skipped panel
with the error in ``meta`` (same pattern as the Gateway panel) rather
than raising. Episodic is a teaching overlay; it must never break the
user-facing turn.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from services.agent_context import AgentContext

logger = logging.getLogger(__name__)


_SELECT_SEED_SQL = (
    "SELECT summary_text, ts_offset_days "
    "FROM pellier.customer_episodic_seed "
    "WHERE customer_id = %s "
    "ORDER BY ts_offset_days DESC "
    "LIMIT %s"
)


async def fetch_episodic_seed(
    db_service: Any,
    customer_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return episodic seed rows for ``customer_id``, newest first.

    Each row is ``{"summary_text": str, "ts_offset_days": int}``.
    Returns ``[]`` for anonymous callers, unknown customers, or any
    query error (logged as a warning — see module docstring).
    """
    if not customer_id or customer_id == "anonymous":
        return []

    try:
        rows = await db_service.fetch_all(_SELECT_SEED_SQL, customer_id, limit)
    except Exception as exc:  # pragma: no cover - defensive DB path
        logger.warning(
            "fetch_episodic_seed failed for customer=%s: %s", customer_id, exc
        )
        return []

    return [
        {
            "summary_text": r["summary_text"],
            "ts_offset_days": int(r["ts_offset_days"]),
        }
        for r in rows
    ]


def _format_relative(days: int) -> str:
    """Turn a negative day-offset into a human-readable relative string.

    -1 → "1 day ago", -14 → "2 weeks ago", -30 → "1 month ago".
    Kept rough because the workshop doesn't want calendar precision;
    the row is there to set the stage, not be audited.
    """
    days = abs(days)
    if days < 1:
        return "today"
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"
    if days < 30:
        weeks = max(1, round(days / 7))
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    months = max(1, round(days / 30))
    return f"{months} month{'s' if months != 1 else ''} ago"


async def emit_memory_episodic_panel(
    ctx: AgentContext,
    *,
    db_service: Any,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Emit a ``MEMORY · EPISODIC`` panel for the current turn.

    Skip-emits a panel with a friendly meta line when the turn's
    customer is anonymous — the emit is still a real panel event so
    the telemetry tab stays coherent (attendees see "no episodic
    recall for anonymous sessions" rather than a silent gap).
    """
    t0 = time.time()

    if not ctx.customer_id or ctx.customer_id == "anonymous":
        ctx.emit_panel(
            agent="memory",
            tag="MEMORY · EPISODIC",
            tag_class="cyan",
            title="Session history · AgentCore Memory (Aurora-seeded)",
            sql="",
            columns=["when", "summary"],
            rows=[],
            meta="anonymous session — no episodic recall",
            duration_ms=int((time.time() - t0) * 1000),
        )
        return []

    rows = await fetch_episodic_seed(db_service, ctx.customer_id, limit=limit)
    rendered = [[_format_relative(r["ts_offset_days"]), r["summary_text"]] for r in rows]

    meta = (
        f'{len(rows)} episode(s) for {ctx.customer_id} · '
        'Aurora seed (AgentCore interface in prod)'
    )
    if not rows:
        meta = (
            f'no seed rows for {ctx.customer_id} — '
            'run <code>psql -f scripts/migrations/003_persona_seed.sql</code>'
        )

    ctx.emit_panel(
        agent="memory",
        tag="MEMORY · EPISODIC",
        tag_class="cyan",
        title="Session history · AgentCore Memory (Aurora-seeded)",
        sql=_SELECT_SEED_SQL,
        columns=["when", "summary"],
        rows=rendered,
        meta=meta,
        duration_ms=int((time.time() - t0) * 1000),
    )
    return rows


# ---------------------------------------------------------------------------
# Working + Semantic emitters — the two AgentCore-owned memory types. The
# composite resume turn also emits episodic memory and operational history:
#
#   WORKING            → AgentCore session events
#   SEMANTIC           → AgentCore durable preference records
#   EPISODIC           → Aurora customer events
#   OPERATIONAL HISTORY→ Aurora tool_audit
#
# Procedural memory is checked-in runtime skills plus MCP tool schemas. It is
# inspectable source, not a per-persona read on the resume turn.
#
# Working + Semantic read the same path the standalone Observatory panels read
# (services.agentcore_memory) so the resume turn and GET /memory/{persona}
# agree. Both degrade honestly to an empty panel (never a fabricated row)
# when the session has no turns / the extraction strategy is unsettled.
# ---------------------------------------------------------------------------


# Resolve a persona's most-recent storefront session — the exact query the
# standalone Working panel (observatory._load_live_working) uses, so
# the resume turn surfaces the same "what we were just talking about" thread.
_SELECT_LATEST_PERSONA_SESSION_SQL = (
    "SELECT session_id "
    "FROM pellier.tool_audit "
    "WHERE session_id LIKE %s "
    "ORDER BY audit_id DESC "
    "LIMIT 1"
)


async def emit_memory_working_panel(
    ctx: AgentContext,
    *,
    db_service: Any,
    persona: str | None = None,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Emit a ``MEMORY · WORKING`` panel — recent session turns, in order.

    Working memory is AgentCore STM (short-term, session-scoped). The
    session we read depends on the caller:

    - With a ``persona`` (the resume "welcome back" turn), we resolve that
      persona's latest *storefront* session from ``pellier.tool_audit`` and
      read it back — the same path the standalone Observatory Working panel
      takes, so "what we were just talking about" matches the dashboard.
    - Without one, we fall back to this turn's own ``session_id``.

    Either way the namespace is the anonymous ``anon-{session_id}`` the
    storefront writes under, read through
    ``AgentCoreMemory.get_session_history`` (live SDK on a provisioned box,
    in-memory fallback otherwise).

    Honest degrade: no turns yet → empty panel with a "make a turn first"
    meta line, never a fabricated row.
    """
    t0 = time.time()
    title = "Session timeline · AgentCore STM"

    if not ctx.customer_id or ctx.customer_id == "anonymous":
        ctx.emit_panel(
            agent="memory",
            tag="MEMORY · WORKING",
            tag_class="cyan",
            title=title,
            sql="",
            columns=["turn", "content"],
            rows=[],
            meta="anonymous session — no working memory · AgentCore-owned (STM)",
            duration_ms=int((time.time() - t0) * 1000),
        )
        return []

    # Resolve which session's turns to show. Default to this turn's own
    # session; upgrade to the persona's latest storefront session when we
    # can find one (best-effort — a failed lookup just keeps the default).
    working_session_id = ctx.session_id
    resolved_from = "this session"
    if persona and db_service is not None:
        try:
            row = await db_service.fetch_one(
                _SELECT_LATEST_PERSONA_SESSION_SQL, f"persona-{persona.lower()}-%"
            )
            sid = dict(row).get("session_id") if row else None
            if sid:
                working_session_id = sid
                resolved_from = f"{persona}'s latest storefront session"
        except Exception as exc:  # pragma: no cover - defensive DB path
            logger.warning(
                "emit_memory_working_panel session resolve failed for persona=%s: %s",
                persona, exc,
            )

    turns: List[Dict[str, Any]] = []
    try:
        from services.agentcore_identity import AgentCoreIdentityService
        from services.agentcore_memory import AgentCoreMemory

        namespace = AgentCoreIdentityService.build_namespace(None, working_session_id)
        memory = AgentCoreMemory()
        turns = await memory.get_session_history(namespace)
    except Exception as exc:  # pragma: no cover - defensive SDK/store path
        logger.warning(
            "emit_memory_working_panel read failed for session=%s: %s",
            working_session_id, exc,
        )
        turns = []

    rendered = [
        [str(t.get("role", "")), str(t.get("content", ""))[:160]]
        for t in turns[-limit:]
    ]
    meta = (
        f'{len(rendered)} turn(s) from {resolved_from} · AgentCore-owned '
        f'(STM, namespace anon-{working_session_id})'
        if rendered
        else f'no turns yet for {resolved_from} — make a storefront turn first '
        '· AgentCore-owned (STM)'
    )

    ctx.emit_panel(
        agent="memory",
        tag="MEMORY · WORKING",
        tag_class="cyan",
        title=title,
        sql="",
        columns=["turn", "content"],
        rows=rendered,
        meta=meta,
        duration_ms=int((time.time() - t0) * 1000),
    )
    return turns


async def emit_memory_semantic_panel(
    ctx: AgentContext,
    *,
    db_service: Any,
) -> List[str]:
    """Emit a ``MEMORY · SEMANTIC`` panel — durable, extracted preferences.

    Semantic memory is AgentCore long-term: prose preferences a
    ``USER_PREFERENCE`` extraction strategy learns from conversation and
    stores under ``/pellier/preferences/{customer_id}/``. We read it with
    the dedicated ``get_semantic_memories`` method (NOT
    ``get_user_preferences``, which serves storefront personalization).

    Honest degrade: ``[]`` (SDK absent, extraction still settling, or
    memory unprovisioned) → empty panel, never a fabricated preference.
    """
    t0 = time.time()
    title = "Learned preferences · AgentCore (USER_PREFERENCE)"

    if not ctx.customer_id or ctx.customer_id == "anonymous":
        ctx.emit_panel(
            agent="memory",
            tag="MEMORY · SEMANTIC",
            tag_class="cyan",
            title=title,
            sql="",
            columns=["learned preference"],
            rows=[],
            meta="anonymous session — no semantic memory · AgentCore-owned (long-term)",
            duration_ms=int((time.time() - t0) * 1000),
        )
        return []

    preferences: List[str] = []
    try:
        from services.agentcore_memory import AgentCoreMemory

        memory = AgentCoreMemory()
        preferences = await memory.get_semantic_memories(ctx.customer_id)
    except Exception as exc:  # pragma: no cover - defensive SDK path
        logger.warning(
            "emit_memory_semantic_panel read failed for customer=%s: %s",
            ctx.customer_id, exc,
        )
        preferences = []

    cleaned = [str(p).strip() for p in (preferences or []) if str(p).strip()]
    rendered = [[p[:200]] for p in cleaned]
    meta = (
        f'{len(rendered)} extracted preference(s) for {ctx.customer_id} · '
        'AgentCore-owned (long-term, USER_PREFERENCE strategy)'
        if rendered
        else 'extraction not settled yet — no records · AgentCore-owned (long-term)'
    )

    ctx.emit_panel(
        agent="memory",
        tag="MEMORY · SEMANTIC",
        tag_class="cyan",
        title=title,
        sql="",
        columns=["learned preference"],
        rows=rendered,
        meta=meta,
        duration_ms=int((time.time() - t0) * 1000),
    )
    return cleaned


# ---------------------------------------------------------------------------
# Operational history — tool_audit aggregate, deliberately not memory.
# ---------------------------------------------------------------------------


_SELECT_TOOL_AUDIT_SQL = (
    "SELECT tool, "
    "count(*)::int AS calls, "
    "round(avg(latency_ms)::numeric, 0)::int AS avg_ms "
    "FROM pellier.tool_audit "
    "GROUP BY tool "
    "ORDER BY calls DESC, tool ASC "
    "LIMIT %s"
)


async def emit_operational_history_panel(
    ctx: AgentContext,
    *,
    db_service: Any,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Emit an operational-history panel from the tool_audit aggregate.

    Per-tool call counts + average latency across every ALLOWed tool call.
    This evidence says what ran and how long it took; it does not encode
    tool know-how. The aggregate is not customer-scoped and degrades to an
    empty panel on DB error or an empty table.
    """
    t0 = time.time()
    title = "Tool activity · Aurora (pellier.tool_audit aggregate)"

    rows: List[Dict[str, Any]] = []
    try:
        fetched = await db_service.fetch_all(_SELECT_TOOL_AUDIT_SQL, limit)
        rows = [dict(r) for r in fetched]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("emit_operational_history_panel DB error: %s", exc)
        rows = []

    rendered = [
        [str(r.get("tool", "")), str(r.get("calls", 0)), f"{r.get('avg_ms', 0)}ms"]
        for r in rows
    ]
    meta = (
        f'{len(rows)} tool(s) by call volume · Aurora-owned (every ALLOWed call, '
        'reads + writes)'
        if rows
        else 'no tool_audit rows yet — make a few storefront turns first · Aurora-owned'
    )

    ctx.emit_panel(
        agent="evidence",
        tag="OPERATIONAL · TOOL HISTORY",
        tag_class="cyan",
        title=title,
        sql=_SELECT_TOOL_AUDIT_SQL,
        columns=["tool", "calls", "avg_latency"],
        rows=rendered,
        meta=meta,
        duration_ms=int((time.time() - t0) * 1000),
    )
    return rows
