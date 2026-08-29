"""Durable Operator Concierge conversations, on the tables Pellier already has.

Reuse, not a new store
----------------------

``pellier.conversations`` and ``pellier.messages`` exist from migration 007 and hold
140 real messages across 48 sessions from the shopper dispatcher path. Their writer
is gone, so the substrate is dormant rather than missing. This module restores a
writer for the Operator surface and leaves the historical rows exactly as they are.

The live schema supplies everything needed, so this module adds no migration:

    conversations.session_id  VARCHAR PRIMARY KEY   thread identity
    conversations.agent_name  VARCHAR               surface discriminator
    conversations.metadata    JSONB                 client + creation attribution
    messages.id               SERIAL PRIMARY KEY    deterministic replay order
    messages.role             VARCHAR               'user' | 'assistant'
    messages.metadata         JSONB                 turn_id + structured artifact

`messages.id` being a serial primary key matters: replay ordering comes from it
rather than from `created_at`, which is a timestamp without time zone and can tie.

Two identities, two jobs
------------------------

    session_id   one Operator Concierge thread, many turns
    turn_id      one operator request and its resulting assistant artifact

Both sides of an interaction carry the SAME ``turn_id``, minted by
``services/turn_identity.py``. That is what lets a later review point at the exact
turn that proposed it:

    session_id -> turn_id -> review_id -> execution_turn_id -> tool_audit / domain

No new correlation-id family is introduced, because the existing one already
reaches all the way to the write evidence.

What the browser may not do
---------------------------

The browser supplies an operator message and nothing else. It cannot set the role,
the turn id, the client binding, the operator identity, or any artifact. Those are
all server-derived, because every one of them is a claim about what happened rather
than a request to do something.

Aurora is the record
--------------------

For the Operator surface this is the durable transcript. AgentCore Memory may later
improve what the agent knows, but it must not become a second answer to what the
operator said, what evidence was shown, or which turn produced a review.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# The surface discriminator. Distinct from the legacy `dispatcher` (42 rows) and
# `agents_as_tools` (6 rows), so a Concierge query can never return a shopper thread.
SURFACE = "operator_concierge"

# Bumped when the persisted artifact shape changes in a way a reader must notice.
# v2 adds `workflow`, `primaryLabel`, `primaryNote` and `sections`. A v1 row is still
# readable — every added key is optional — but a v1 READER shown a v2 draft would omit
# the "not sent" label, which is exactly the kind of misread the version guards.
ARTIFACT_VERSION = 2

# Roles, matching what the table and the shopper path already use. Inventing
# `operator` as a role would break every existing reader for no gain; the surface
# and actor live in metadata instead.
ROLE_OPERATOR = "user"
ROLE_ASSISTANT = "assistant"

# A turn whose assistant side never arrived. The operator's request is never deleted:
# losing what someone asked is worse than showing that the answer failed.
TURN_INCOMPLETE = "incomplete"
TURN_COMPLETE = "complete"
TURN_FAILED = "failed"

_MAX_HISTORY = 100


class SessionError(Exception):
    """A session operation the caller should surface rather than retry blindly."""

    def __init__(self, code: str, status_code: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_id(customer_id: str, token: str) -> str:
    """Readable but not semantically load-bearing.

    The customer appears in the id for operator legibility in psql. It is NEVER the
    authority for the binding — `metadata.customer_id` is, and every read verifies
    against that. An id that carries meaning invites someone to parse it.
    """
    return f"opc-{customer_id.lower()}-{token}"


async def create_session(
    db: Any, *, customer_id: str, operator_sub: str
) -> Dict[str, Any]:
    """Open a team-visible Concierge thread bound to one canonical client.

    Not a consequential action: no Bedrock call, no AgentCore call, no review. It
    records who opened the thread for audit attribution. Authorized operators share
    the client thread; each appended turn records the operator who actually authored
    it, so ``created_by`` is not an ownership or read-authorization boundary.
    """
    import uuid

    if not customer_id:
        raise SessionError("customer_id_required", 422)
    if not operator_sub:
        raise SessionError("operator_identity_required", 401)

    session_id = _session_id(customer_id, uuid.uuid4().hex[:16])
    metadata = {
        "surface": SURFACE,
        "customer_id": customer_id,
        "created_by": operator_sub,
        "schema_version": ARTIFACT_VERSION,
    }
    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO pellier.conversations (session_id, agent_name, metadata)
                VALUES (%s, %s, %s::jsonb)
                """,
                (session_id, SURFACE, json.dumps(metadata)),
            )
    return {
        "sessionId": session_id,
        "customerId": customer_id,
        "surface": SURFACE,
        "createdBy": operator_sub,
        "createdAt": _now().isoformat(),
        "turns": [],
    }


async def _load_session_row(db: Any, session_id: str) -> Optional[Dict[str, Any]]:
    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT session_id, agent_name, metadata, created_at, updated_at
                  FROM pellier.conversations
                 WHERE session_id = %s
                """,
                (session_id,),
            )
            row = await cur.fetchone()
    if not row:
        return None
    # Rows are mappings, not tuples: the pool configures a dict row factory, which
    # a tuple-based test fake hid until the first live round-trip.
    r = dict(row)
    raw = r.get("metadata")
    metadata = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    return {
        "session_id": r.get("session_id"),
        "agent_name": r.get("agent_name"),
        "metadata": metadata,
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
    }


async def require_session(db: Any, *, session_id: str, customer_id: str) -> Dict[str, Any]:
    """Load a session and prove it belongs to this surface AND this client.

    The session id alone is never sufficient. A request routed under one client that
    names another client's session is rejected rather than silently switching
    context, which is the difference between a scoping bug and a data leak.
    """
    row = await _load_session_row(db, session_id)
    if row is None:
        raise SessionError("session_not_found", 404)
    if row["agent_name"] != SURFACE or row["metadata"].get("surface") != SURFACE:
        # A shopper dispatcher thread is not a Concierge session, even though both
        # live in this table.
        raise SessionError("not_a_concierge_session", 404)
    if row["metadata"].get("customer_id") != customer_id:
        raise SessionError("session_client_mismatch", 403)
    return row


async def latest_session(db: Any, *, customer_id: str) -> Optional[str]:
    """The most recent Concierge session for this client, for resume."""
    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT session_id
                  FROM pellier.conversations
                 WHERE agent_name = %s
                   AND metadata->>'customer_id' = %s
                 ORDER BY created_at DESC
                 LIMIT 1
                """,
                (SURFACE, customer_id),
            )
            row = await cur.fetchone()
    return dict(row).get("session_id") if row else None


_GRAPH_ARTIFACT_FOR_REVIEW_SQL = """
SELECT c.session_id, m.id, m.metadata
  FROM pellier.conversations c
  JOIN pellier.messages m ON m.session_id = c.session_id
 WHERE c.agent_name = %(surface)s
   AND c.metadata->>'surface' = %(surface)s
   AND c.metadata->>'customer_id' = %(customer_id)s
   AND m.role = %(role)s
   AND m.metadata->>'surface' = %(surface)s
   AND m.metadata->'artifact'->'orchestration'->'checkpoint'->>'reviewId'
       = %(review_id)s
   AND m.metadata->'artifact'->'orchestration'->'checkpoint'->>'actionHash'
       = %(action_hash)s
 ORDER BY m.id DESC
 LIMIT 1
"""


async def load_graph_artifact_for_review(
    db: Any,
    *,
    customer_id: str,
    review_id: int,
    action_hash: str,
) -> Optional[Dict[str, Any]]:
    """Load the graph artifact that proves the exact durable review lineage.

    A client's latest Concierge answer is not necessarily the turn that produced the
    review currently being inspected. Joining on both the server-created review id
    and its action hash prevents a later summary, or an older proposal for the same
    client, from being presented as that review's orchestration evidence.
    """
    if not customer_id or review_id <= 0 or not action_hash:
        return None

    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _GRAPH_ARTIFACT_FOR_REVIEW_SQL,
                {
                    "surface": SURFACE,
                    "customer_id": customer_id,
                    "role": ROLE_ASSISTANT,
                    "review_id": str(review_id),
                    "action_hash": action_hash,
                },
            )
            row = await cur.fetchone()

    if not row:
        return None

    result = dict(row)
    raw = result.get("metadata")
    metadata = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    artifact = metadata.get("artifact") or {}
    orchestration = artifact.get("orchestration")
    if not isinstance(orchestration, dict):
        return None

    return {
        "sessionId": result.get("session_id"),
        "turnId": metadata.get("turn_id", ""),
        "orchestration": orchestration,
    }


# One statement that validates the session, honours transport idempotency, inserts
# the message and stamps the conversation. Written as CTEs because each `execute`
# is a separate network round trip to a remote Aurora cluster, and the naive
# four-trip version measured 2145ms before any orchestration had begun. Premium UX
# is most sensitive to dead time BEFORE the visible work starts.
#
# Validation is not weakened: `target` is the gate, and nothing inserts unless the
# session matches this surface AND this customer. The returned row carries enough
# state to raise the same precise errors as before.
_APPEND_TURN_SQL = """
WITH target AS (
    SELECT session_id,
           agent_name,
           metadata->>'customer_id' AS bound_customer,
           metadata->>'surface'     AS bound_surface
      FROM pellier.conversations
     WHERE session_id = %(session_id)s
),
eligible AS (
    SELECT session_id FROM target
     WHERE agent_name = %(surface)s
       AND bound_surface = %(surface)s
       AND bound_customer = %(customer_id)s
),
existing AS (
    SELECT m.id, m.metadata
      FROM pellier.messages m
      JOIN eligible e ON e.session_id = m.session_id
     WHERE %(transport_key)s <> ''
       AND m.metadata->>'transport_idempotency_key' = %(transport_key)s
     ORDER BY m.id ASC
     LIMIT 1
),
inserted AS (
    INSERT INTO pellier.messages (session_id, role, content, metadata)
    SELECT e.session_id, %(role)s, %(content)s, %(metadata)s::jsonb
      FROM eligible e
     WHERE NOT EXISTS (SELECT 1 FROM existing)
    RETURNING id, metadata
),
touched AS (
    UPDATE pellier.conversations c
       SET updated_at = now()
      FROM inserted i
     WHERE c.session_id = %(session_id)s
    RETURNING c.session_id
)
SELECT (SELECT COUNT(*) FROM target)                       AS session_exists,
       (SELECT bound_customer FROM target)                 AS bound_customer,
       (SELECT bound_surface FROM target)                   AS bound_surface,
       (SELECT agent_name FROM target)                      AS agent_name,
       (SELECT COUNT(*) FROM eligible)                      AS eligible,
       (SELECT id FROM existing)                            AS existing_id,
       (SELECT metadata FROM existing)                      AS existing_metadata,
       (SELECT id FROM inserted)                            AS inserted_id,
       (SELECT COUNT(*) FROM touched)                       AS touched
"""


async def append_operator_turn(
    db: Any,
    *,
    session_id: str,
    customer_id: str,
    operator_sub: str,
    message: str,
    transport_key: str = "",
) -> Dict[str, Any]:
    """Persist the operator's request and mint the turn id for the interaction.

    ``transport_key`` is TRANSPORT IDEMPOTENCY, not domain lineage: it stops a
    network retry from duplicating the same request. ``turn_id`` remains the only
    lineage identity, and it is generated here rather than accepted from the caller.

    Executed as ONE round trip. The previous four-trip version cost 2145ms against
    the remote cluster; the semantics are unchanged, including append-only writes and
    the surface/customer gate.
    """
    text = (message or "").strip()
    if not text:
        raise SessionError("message_required", 422)

    from services.turn_identity import new_turn_id

    turn_id = new_turn_id()
    metadata: Dict[str, Any] = {
        "surface": SURFACE,
        "turn_id": turn_id,
        "actor_type": "operator",
        "actor_sub": operator_sub,
        "turn_state": TURN_INCOMPLETE,
        "artifact_version": ARTIFACT_VERSION,
    }
    if transport_key:
        metadata["transport_idempotency_key"] = transport_key

    params = {
        "session_id": session_id,
        "surface": SURFACE,
        "customer_id": customer_id,
        "transport_key": transport_key or "",
        "role": ROLE_OPERATOR,
        "content": text,
        "metadata": json.dumps(metadata),
    }
    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_APPEND_TURN_SQL, params)
            row = dict(await cur.fetchone() or {})

    # Same error precision as the previous multi-trip version.
    if not int(row.get("session_exists") or 0):
        raise SessionError("session_not_found", 404)
    if row.get("agent_name") != SURFACE or row.get("bound_surface") != SURFACE:
        raise SessionError("not_a_concierge_session", 404)
    if row.get("bound_customer") != customer_id:
        raise SessionError("session_client_mismatch", 403)

    if row.get("existing_id") is not None:
        raw = row.get("existing_metadata")
        meta = raw if isinstance(raw, dict) else json.loads(raw or "{}")
        return {
            "messageId": int(row["existing_id"]),
            "sessionId": session_id,
            "turnId": meta.get("turn_id", ""),
            "role": ROLE_OPERATOR,
            "content": text,
            "turnState": meta.get("turn_state", TURN_INCOMPLETE),
            "replayed": True,
        }

    if row.get("inserted_id") is None:
        raise SessionError("turn_not_persisted", 500)

    return {
        "messageId": int(row["inserted_id"]),
        "sessionId": session_id,
        "turnId": turn_id,
        "role": ROLE_OPERATOR,
        "content": text,
        "turnState": TURN_INCOMPLETE,
        "replayed": False,
    }


async def _find_by_transport_key(
    db: Any, session_id: str, transport_key: str
) -> Optional[Dict[str, Any]]:
    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, content, metadata
                  FROM pellier.messages
                 WHERE session_id = %s
                   AND metadata->>'transport_idempotency_key' = %s
                 ORDER BY id ASC
                 LIMIT 1
                """,
                (session_id, transport_key),
            )
            row = await cur.fetchone()
    if not row:
        return None
    r = dict(row)
    raw = r.get("metadata")
    meta = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    return {
        "messageId": int(r["id"]),
        "sessionId": session_id,
        "turnId": meta.get("turn_id", ""),
        "role": ROLE_OPERATOR,
        "content": r.get("content"),
        "turnState": meta.get("turn_state", TURN_INCOMPLETE),
    }


_APPEND_ARTIFACT_SQL = """
WITH target AS (
    SELECT session_id,
           agent_name,
           metadata->>'customer_id' AS bound_customer,
           metadata->>'surface'     AS bound_surface
      FROM pellier.conversations
     WHERE session_id = %(session_id)s
),
eligible AS (
    SELECT session_id FROM target
     WHERE agent_name = %(surface)s
       AND bound_surface = %(surface)s
       AND bound_customer = %(customer_id)s
),
inserted AS (
    INSERT INTO pellier.messages (session_id, role, content, metadata)
    SELECT e.session_id, %(role)s, %(content)s, %(metadata)s::jsonb FROM eligible e
    RETURNING id
),
touched AS (
    UPDATE pellier.conversations c SET updated_at = now()
      FROM inserted i WHERE c.session_id = %(session_id)s
    RETURNING c.session_id
)
SELECT (SELECT COUNT(*) FROM target)       AS session_exists,
       (SELECT bound_customer FROM target) AS bound_customer,
       (SELECT bound_surface FROM target)  AS bound_surface,
       (SELECT agent_name FROM target)     AS agent_name,
       (SELECT id FROM inserted)           AS inserted_id
"""


async def append_assistant_artifact(
    db: Any,
    *,
    session_id: str,
    customer_id: str,
    turn_id: str,
    summary: str,
    artifact: Dict[str, Any],
    state: str = TURN_COMPLETE,
) -> Dict[str, Any]:
    """Persist the assistant side of an existing turn, sharing its turn id.

    Append-only. A later change of review state is recorded in
    ``pellier.approvals``, never by editing what was said at the time — the
    transcript is history, not current state.

    The artifact must contain only operator-safe, observable material. Nothing here
    stores hidden reasoning: the database should not hold anything the surface would
    be wrong to render.

    One round trip, same surface/customer gate as the operator side.
    """
    if not turn_id:
        raise SessionError("turn_id_required", 422)

    rejected = sorted(set(artifact) & _FORBIDDEN_ARTIFACT_KEYS)
    if rejected:
        raise SessionError(f"forbidden_artifact_keys:{','.join(rejected)}", 422)

    metadata = {
        "surface": SURFACE,
        "turn_id": turn_id,
        "actor_type": "assistant",
        "turn_state": state,
        "artifact_version": ARTIFACT_VERSION,
        "artifact": artifact,
    }
    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _APPEND_ARTIFACT_SQL,
                {
                    "session_id": session_id,
                    "surface": SURFACE,
                    "customer_id": customer_id,
                    "role": ROLE_ASSISTANT,
                    "content": summary or "",
                    "metadata": json.dumps(metadata),
                },
            )
            row = dict(await cur.fetchone() or {})

    if not int(row.get("session_exists") or 0):
        raise SessionError("session_not_found", 404)
    if row.get("agent_name") != SURFACE or row.get("bound_surface") != SURFACE:
        raise SessionError("not_a_concierge_session", 404)
    if row.get("bound_customer") != customer_id:
        raise SessionError("session_client_mismatch", 403)
    if row.get("inserted_id") is None:
        raise SessionError("artifact_not_persisted", 500)

    return {
        "messageId": int(row["inserted_id"]),
        "sessionId": session_id,
        "turnId": turn_id,
        "role": ROLE_ASSISTANT,
        "turnState": state,
    }


# Keys that must never be persisted, because they are model interiors rather than
# observable operator-safe evidence.
_FORBIDDEN_ARTIFACT_KEYS = {
    "reasoning",
    "reasoning_trace",
    "chain_of_thought",
    "thoughts",
    "scratchpad",
    "system_prompt",
    "hidden_prompt",
    "raw_prompt",
}


_HISTORY_SQL = """
WITH target AS (
    SELECT session_id,
           agent_name,
           metadata->>'customer_id' AS bound_customer,
           metadata->>'surface'     AS bound_surface,
           metadata->>'created_by'  AS created_by
      FROM pellier.conversations
     WHERE session_id = %(session_id)s
),
eligible AS (
    SELECT session_id, created_by FROM target
     WHERE agent_name = %(surface)s
       AND bound_surface = %(surface)s
       AND bound_customer = %(customer_id)s
)
SELECT (SELECT COUNT(*) FROM target)           AS session_exists,
       (SELECT bound_customer FROM target)     AS bound_customer,
       (SELECT bound_surface FROM target)      AS bound_surface,
       (SELECT agent_name FROM target)         AS agent_name,
       (SELECT created_by FROM eligible)       AS created_by,
       m.id, m.role, m.content, m.metadata, m.created_at
  FROM eligible e
  LEFT JOIN pellier.messages m ON m.session_id = e.session_id
 ORDER BY m.id DESC
 LIMIT %(limit)s
"""


async def load_history(
    db: Any, *, session_id: str, customer_id: str, limit: int = 40
) -> Dict[str, Any]:
    """Bounded, deterministically ordered replay of one Concierge session.

    Ordered by ``messages.id``, the serial primary key, not by ``created_at``: the
    timestamp column has no time zone and two inserts in the same tick would tie,
    which would make replay order arbitrary exactly when a turn matters most.

    One round trip. The validation is the same surface/customer gate, expressed as a
    CTE the message join depends on, so a mismatched session returns no rows rather
    than another client's transcript.
    """
    bounded = max(1, min(int(limit or 40), _MAX_HISTORY))
    async with db.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _HISTORY_SQL,
                {
                    "session_id": session_id,
                    "surface": SURFACE,
                    "customer_id": customer_id,
                    "limit": bounded,
                },
            )
            rows = [dict(r) for r in await cur.fetchall()]

    if not rows:
        # No rows at all means the gate rejected. Re-read only on this cold path to
        # produce the precise error; the happy path stays at one trip.
        probe = await _load_session_row(db, session_id)
        if probe is None:
            raise SessionError("session_not_found", 404)
        if probe["agent_name"] != SURFACE or probe["metadata"].get("surface") != SURFACE:
            raise SessionError("not_a_concierge_session", 404)
        if probe["metadata"].get("customer_id") != customer_id:
            raise SessionError("session_client_mismatch", 403)
        return {
            "sessionId": session_id,
            "customerId": customer_id,
            "surface": SURFACE,
            "createdBy": probe["metadata"].get("created_by", ""),
            "messages": [],
            "truncated": False,
        }

    head = rows[0]
    if not int(head.get("session_exists") or 0):
        raise SessionError("session_not_found", 404)
    if head.get("agent_name") != SURFACE or head.get("bound_surface") != SURFACE:
        raise SessionError("not_a_concierge_session", 404)
    if head.get("bound_customer") != customer_id:
        raise SessionError("session_client_mismatch", 403)

    messages: List[Dict[str, Any]] = []
    for r in reversed([x for x in rows if x.get("id") is not None]):
        raw = r.get("metadata")
        meta = raw if isinstance(raw, dict) else json.loads(raw or "{}")
        created = r.get("created_at")
        messages.append(
            {
                "messageId": int(r["id"]),
                "role": r.get("role"),
                "content": r.get("content"),
                "turnId": meta.get("turn_id", ""),
                "turnState": meta.get("turn_state", ""),
                "actorType": meta.get("actor_type", ""),
                "artifact": meta.get("artifact"),
                "artifactVersion": meta.get("artifact_version"),
                "createdAt": created.isoformat() if hasattr(created, "isoformat") else created,
            }
        )

    return {
        "sessionId": session_id,
        "customerId": head.get("bound_customer") or customer_id,
        "surface": SURFACE,
        "createdBy": head.get("created_by") or "",
        "messages": messages,
        "truncated": len(messages) >= bounded,
    }


# ---------------------------------------------------------------------------
# AgentCore Memory identity mapping for this surface
# ---------------------------------------------------------------------------
#
# AgentCore scopes short-term events by actor plus session, and they answer
# different questions:
#
#     actorId    the entity interacting with the agent -> the authenticated OPERATOR
#     sessionId  one conversation                      -> the Concierge session id
#
# The client is neither. Jessica is the business subject being investigated; she is
# not the person typing. Setting actorId to the open client would send the live
# USER_PREFERENCE strategy (namespace /pellier/preferences/{actorId}/) to learn
# "Jessica prefers concise drafts" from something the OPERATOR expressed — a subtle
# and ugly memory-contamination bug.
#
# So operator preference memory accrues to the operator, and client facts stay in
# Aurora where they are authoritative and current.


def memory_identity(*, operator_sub: str, session_id: str) -> Dict[str, str]:
    """The actor/session pair for this surface. No derived third identifier."""
    if not operator_sub:
        raise SessionError("operator_identity_required", 401)
    if not session_id:
        raise SessionError("session_required", 422)
    return {"actor_id": operator_sub, "session_id": session_id}


async def append_operator_memory(
    memory: Any,
    *,
    operator_sub: str,
    session_id: str,
    turns: List[Dict[str, Any]],
) -> str:
    """Mirror observable turns into AgentCore Memory for agent context.

    Returns which store took the write — ``"agentcore"``, ``"process_local"``, or
    ``""`` when it failed outright. A bool was not enough: a process-local dict
    accepts every write and dies with the worker, so "it landed" was true and
    "it persisted" was not.

    Never raises: Aurora is the authoritative transcript, so a memory failure must not
    delete or discredit a durable turn. The caller surfaces an honest limitation
    instead — "conversation memory unavailable" — rather than pretending the operator
    never spoke.

    The converse also holds and is the caller's responsibility: a successful memory
    write never substitutes for a failed Aurora write.
    """
    identity = memory_identity(operator_sub=operator_sub, session_id=session_id)
    try:
        return await memory.append_memory_event(
            actor_id=identity["actor_id"],
            session_id=identity["session_id"],
            turns=turns,
        )
    except Exception as exc:  # noqa: BLE001 - context is best-effort by design
        logger.warning(
            "AgentCore Memory unavailable for operator turn (%s/%s): %s",
            identity["actor_id"], identity["session_id"], exc,
        )
        return ""
