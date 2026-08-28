"""Phase 2: the Operator Concierge conversation substrate.

Built on `pellier.conversations` / `pellier.messages` (migration 007), which hold
140 real dispatcher-path messages across 48 sessions and had no writer. These tests
protect two things: that the historical rows stay untouched, and that a browser
cannot forge any part of a transcript.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import pytest

from services import operator_concierge_sessions as SESSIONS


# ---------------------------------------------------------------------------
# A fake Aurora that behaves like the real table contract
# ---------------------------------------------------------------------------

class FakeDb:
    """Rows plus enough SQL routing to exercise ordering and scoping.

    Message ids increment like the SERIAL primary key, because replay ordering is
    asserted against that rather than against timestamps.
    """

    def __init__(self) -> None:
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.messages: List[Dict[str, Any]] = []
        self._next_id = 1
        self.updated: List[str] = []

    # Seed a legacy dispatcher session, as production has.
    def seed_legacy(self, session_id: str = "persona-theo-abc") -> None:
        self.conversations[session_id] = {
            "session_id": session_id,
            "agent_name": "dispatcher",
            "metadata": {"persona": "theo"},
            "created_at": None,
            "updated_at": None,
        }
        for role, content in (("user", "Browse linen"), ("assistant", "Here is the edit")):
            self.messages.append({
                "id": self._next_id, "session_id": session_id, "role": role,
                "content": content, "metadata": {"legacy": True}, "created_at": None,
            })
            self._next_id += 1

    def get_connection(self): return _Conn(self)


class _Cur:
    """A tiny interpreter for this module's four statements.

    Returns MAPPINGS, not tuples: the pool configures `dict_row`, and an earlier
    tuple-based fake let a `row[2]`-style access pass every test and then fail on the
    first live call. A fake looser than the real driver is worse than no fake.

    The three write/read paths are now single CTE statements, so this models the same
    surface/customer gate the SQL enforces — including that a mismatched session
    inserts NOTHING rather than raising after the fact.
    """

    def __init__(self, db: FakeDb) -> None:
        self.db = db
        self._result: Any = None
        self._rows: List[Dict[str, Any]] = []

    def _target(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.db.conversations.get(session_id)

    def _gate(self, p: Dict[str, Any]) -> Dict[str, Any]:
        """The CTE header columns, computed the way the SQL computes them."""
        row = self._target(p["session_id"])
        if row is None:
            return {"session_exists": 0, "bound_customer": None,
                    "bound_surface": None, "agent_name": None, "eligible": 0}
        meta = row["metadata"]
        eligible = (
            row["agent_name"] == p["surface"]
            and meta.get("surface") == p["surface"]
            and meta.get("customer_id") == p["customer_id"]
        )
        return {
            "session_exists": 1,
            "bound_customer": meta.get("customer_id"),
            "bound_surface": meta.get("surface"),
            "agent_name": row["agent_name"],
            "eligible": 1 if eligible else 0,
            "created_by": meta.get("created_by") if eligible else None,
        }

    async def execute(self, sql: str, params: Any = ()) -> None:
        s = " ".join(sql.split())
        if s.startswith("INSERT INTO pellier.conversations"):
            sid, agent, meta = params
            self.db.conversations[sid] = {
                "session_id": sid, "agent_name": agent,
                "metadata": json.loads(meta), "created_at": None, "updated_at": None,
            }
            self._result = None
        elif s.startswith("SELECT session_id, agent_name, metadata"):
            row = self._target(params[0])
            self._result = dict(row) if row else None
        elif s.startswith("SELECT session_id FROM pellier.conversations"):
            agent, customer = params
            hits = [
                c["session_id"] for c in self.db.conversations.values()
                if c["agent_name"] == agent and c["metadata"].get("customer_id") == customer
            ]
            self._result = {"session_id": hits[-1]} if hits else None
        elif "existing AS (" in s and "inserted AS (" in s:
            # _APPEND_TURN_SQL
            gate = self._gate(params)
            existing = None
            if gate["eligible"] and params["transport_key"]:
                for m in self.db.messages:
                    if (m["session_id"] == params["session_id"]
                            and m["metadata"].get("transport_idempotency_key")
                            == params["transport_key"]):
                        existing = m
                        break
            inserted_id = None
            if gate["eligible"] and existing is None:
                inserted_id = self.db._next_id
                self.db._next_id += 1
                self.db.messages.append({
                    "id": inserted_id, "session_id": params["session_id"],
                    "role": params["role"], "content": params["content"],
                    "metadata": json.loads(params["metadata"]), "created_at": None,
                })
                self.db.updated.append(params["session_id"])
            self._result = dict(
                gate,
                existing_id=existing["id"] if existing else None,
                existing_metadata=existing["metadata"] if existing else None,
                inserted_id=inserted_id,
                touched=1 if inserted_id else 0,
            )
        elif "inserted AS (" in s and "existing AS (" not in s and "LEFT JOIN" not in s:
            # _APPEND_ARTIFACT_SQL
            gate = self._gate(params)
            inserted_id = None
            if gate["eligible"]:
                inserted_id = self.db._next_id
                self.db._next_id += 1
                self.db.messages.append({
                    "id": inserted_id, "session_id": params["session_id"],
                    "role": params["role"], "content": params["content"],
                    "metadata": json.loads(params["metadata"]), "created_at": None,
                })
                self.db.updated.append(params["session_id"])
            self._result = dict(gate, inserted_id=inserted_id)
        elif "LEFT JOIN pellier.messages" in s:
            # _HISTORY_SQL
            gate = self._gate(params)
            if not gate["eligible"]:
                self._rows = []
                return
            rows = [m for m in self.db.messages if m["session_id"] == params["session_id"]]
            rows.sort(key=lambda m: m["id"], reverse=True)
            self._rows = [dict(gate, **dict(m)) for m in rows[: params["limit"]]]
            if not self._rows:
                self._rows = [dict(gate, id=None, role=None, content=None,
                                   metadata=None, created_at=None)]
        else:
            raise AssertionError(f"unexpected SQL: {s[:90]}")

    async def fetchone(self): return self._result
    async def fetchall(self): return self._rows
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False


class _Conn:
    def __init__(self, db: FakeDb) -> None: self.db = db
    def cursor(self): return _Cur(self.db)
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False


@pytest.fixture
def db() -> FakeDb:
    d = FakeDb()
    d.seed_legacy()
    return d


# ---------------------------------------------------------------------------
# Session identity and client binding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_session_is_bound_to_client_and_operator(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    stored = db.conversations[s["sessionId"]]
    assert stored["agent_name"] == SESSIONS.SURFACE
    assert stored["metadata"]["customer_id"] == "CUST-JESSICA"
    assert stored["metadata"]["created_by"] == "op-1"
    assert stored["metadata"]["surface"] == SESSIONS.SURFACE


@pytest.mark.asyncio
async def test_a_session_requires_an_operator_identity(db: FakeDb) -> None:
    with pytest.raises(SESSIONS.SessionError) as exc:
        await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="")
    assert exc.value.code == "operator_identity_required"


@pytest.mark.asyncio
async def test_one_client_cannot_read_another_clients_session(db: FakeDb) -> None:
    """The session id alone is never sufficient authority."""
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    with pytest.raises(SESSIONS.SessionError) as exc:
        await SESSIONS.require_session(
            db, session_id=s["sessionId"], customer_id="CUST-THEO"
        )
    assert exc.value.code == "session_client_mismatch"
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_one_client_cannot_append_to_another_clients_session(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    before = len(db.messages)
    with pytest.raises(SESSIONS.SessionError):
        await SESSIONS.append_operator_turn(
            db, session_id=s["sessionId"], customer_id="CUST-THEO",
            operator_sub="op-1", message="whose record is this",
        )
    assert len(db.messages) == before, "a cross-client append was persisted"


@pytest.mark.asyncio
async def test_a_legacy_dispatcher_thread_is_not_a_concierge_session(db: FakeDb) -> None:
    """Both surfaces share the table; a Concierge read must not return a shopper thread."""
    with pytest.raises(SESSIONS.SessionError) as exc:
        await SESSIONS.require_session(
            db, session_id="persona-theo-abc", customer_id="CUST-THEO"
        )
    assert exc.value.code == "not_a_concierge_session"


@pytest.mark.asyncio
async def test_latest_session_only_finds_concierge_sessions(db: FakeDb) -> None:
    assert await SESSIONS.latest_session(db, customer_id="CUST-THEO") is None
    s = await SESSIONS.create_session(db, customer_id="CUST-THEO", operator_sub="op-1")
    assert await SESSIONS.latest_session(db, customer_id="CUST-THEO") == s["sessionId"]


@pytest.mark.asyncio
async def test_the_session_id_is_not_the_authority_for_the_binding(db: FakeDb) -> None:
    """The id contains the customer for legibility; metadata decides."""
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    assert "jessica" in s["sessionId"]
    db.conversations[s["sessionId"]]["metadata"]["customer_id"] = "CUST-THEO"
    with pytest.raises(SESSIONS.SessionError):
        await SESSIONS.require_session(
            db, session_id=s["sessionId"], customer_id="CUST-JESSICA"
        )


# ---------------------------------------------------------------------------
# Turn identity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_turn_id_comes_from_turn_identity(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    turn = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="Summarize recent activity",
    )
    assert turn["turnId"].startswith("turn-")
    assert len(turn["turnId"]) == len("turn-") + 32


@pytest.mark.asyncio
async def test_both_sides_of_one_interaction_share_one_turn_id(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    turn = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="Summarize recent activity",
    )
    reply = await SESSIONS.append_assistant_artifact(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        turn_id=turn["turnId"], summary="Five orders, one open ticket.",
        artifact={"investigation": [], "evidence": []},
    )
    assert reply["turnId"] == turn["turnId"]
    ids = {m["metadata"]["turn_id"] for m in db.messages if "turn_id" in m["metadata"]}
    assert len(ids) == 1, "the assistant minted a second turn id"


@pytest.mark.asyncio
async def test_two_turns_get_different_ids_and_the_session_is_stable(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    a = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="first",
    )
    b = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="second",
    )
    assert a["turnId"] != b["turnId"]
    assert a["sessionId"] == b["sessionId"] == s["sessionId"]


def test_no_parallel_correlation_id_family_is_introduced() -> None:
    from pathlib import Path

    src = Path(SESSIONS.__file__).read_text()
    for invented in ("concierge_turn_id", "operator_trace_id", "correlation_id",
                     "conversation_turn_key"):
        assert invented not in src, f"a second identifier family appeared: {invented}"
    assert "from services.turn_identity import new_turn_id" in src


def test_transport_idempotency_is_labelled_as_transport_not_lineage() -> None:
    from pathlib import Path

    src = Path(SESSIONS.__file__).read_text()
    flat = " ".join(src.replace("#", " ").split())
    assert "TRANSPORT IDEMPOTENCY, not domain lineage" in flat
    assert "transport_idempotency_key" in src


@pytest.mark.asyncio
async def test_a_retry_with_the_same_transport_key_does_not_duplicate(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    first = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="Summarize", transport_key="tk-1",
    )
    again = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="Summarize", transport_key="tk-1",
    )
    assert again["messageId"] == first["messageId"]
    assert again["turnId"] == first["turnId"]
    assert again["replayed"] is True
    assert sum(1 for m in db.messages if m["role"] == "user"
               and m["session_id"] == s["sessionId"]) == 1


# ---------------------------------------------------------------------------
# Append-only history, ordering, and artifact safety
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_replay_is_ordered_by_the_serial_primary_key(db: FakeDb) -> None:
    """`created_at` is `timestamp without time zone` and can tie.

    Two inserts in the same tick would make timestamp ordering arbitrary exactly
    when a turn matters most, so ordering uses `messages.id`.
    """
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    for n in range(5):
        turn = await SESSIONS.append_operator_turn(
            db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
            operator_sub="op-1", message=f"request {n}",
        )
        await SESSIONS.append_assistant_artifact(
            db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
            turn_id=turn["turnId"], summary=f"answer {n}", artifact={},
        )
    history = await SESSIONS.load_history(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA", limit=40
    )
    ids = [m["messageId"] for m in history["messages"]]
    assert ids == sorted(ids), "replay is not in insertion order"
    contents = [m["content"] for m in history["messages"] if m["role"] == "user"]
    assert contents == [f"request {n}" for n in range(5)]
    from pathlib import Path

    # Scoped to the message replay query. `latest_session` legitimately orders
    # CONVERSATIONS by created_at — session_id is a random token, so there is no
    # better key there. What must not happen is ordering MESSAGES that way.
    src = Path(SESSIONS.__file__).read_text()
    replay = src[src.index("_HISTORY_SQL"):]
    replay = replay[: replay.index('"""', replay.index('"""') + 3)]
    assert "ORDER BY m.id DESC" in replay
    assert "created_at" not in replay.split("ORDER BY")[1]


@pytest.mark.asyncio
async def test_history_is_bounded_and_reports_truncation(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    for n in range(12):
        await SESSIONS.append_operator_turn(
            db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
            operator_sub="op-1", message=f"m{n}",
        )
    history = await SESSIONS.load_history(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA", limit=5
    )
    assert len(history["messages"]) == 5
    assert history["truncated"] is True
    # The most recent five, still in ascending order.
    assert [m["content"] for m in history["messages"]] == ["m7", "m8", "m9", "m10", "m11"]


@pytest.mark.asyncio
async def test_history_is_append_only(db: FakeDb) -> None:
    """A later review decision changes pellier.approvals, never the transcript."""
    from pathlib import Path

    src = Path(SESSIONS.__file__).read_text()
    assert "UPDATE pellier.messages" not in src
    assert "DELETE FROM pellier.messages" not in src
    # The only UPDATEs stamp the conversation, one per write path. Both live inside
    # a CTE now, so the statement reads `UPDATE pellier.conversations c SET ...`.
    assert src.count("UPDATE pellier.conversations c") == 2
    assert "UPDATE pellier.conversations" in src


@pytest.mark.asyncio
async def test_chain_of_thought_cannot_be_persisted(db: FakeDb) -> None:
    """The database must hold nothing the surface would be wrong to render."""
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    turn = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="investigate",
    )
    for key in ("reasoning", "chain_of_thought", "scratchpad", "system_prompt",
                "hidden_prompt", "thoughts", "raw_prompt", "reasoning_trace"):
        with pytest.raises(SESSIONS.SessionError) as exc:
            await SESSIONS.append_assistant_artifact(
                db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
                turn_id=turn["turnId"], summary="x", artifact={key: "let me think..."},
            )
        assert "forbidden_artifact_keys" in exc.value.code, key


@pytest.mark.asyncio
async def test_a_structured_artifact_round_trips_with_its_version(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    turn = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="Summarize Jessica's recent activity.",
    )
    artifact = {
        "investigation": [
            {"kind": "client", "label": "Client record loaded",
             "source": "aurora", "status": "complete", "durationMs": 41},
            {"kind": "order", "label": "Orders loaded",
             "source": "aurora", "status": "complete", "durationMs": 63},
        ],
        "evidence": [
            {"kind": "order", "status": "verified", "source": "aurora", "recordId": "315"},
            {"kind": "return", "status": "unverified", "source": "aurora",
             "note": "support ticket asserts a return; no return row exists"},
        ],
        "summary": "Five orders, one open ticket, no authoritative return.",
        "capabilityObservation": [
            {"capability": "initiate_return", "state": "temporarily_unavailable",
             "observedAt": "2026-08-26T23:48:44Z"},
        ],
    }
    await SESSIONS.append_assistant_artifact(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        turn_id=turn["turnId"], summary=artifact["summary"], artifact=artifact,
    )
    history = await SESSIONS.load_history(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA"
    )
    reply = next(m for m in history["messages"] if m["role"] == "assistant")
    assert reply["artifact"] == artifact, "the artifact did not round-trip exactly"
    assert reply["artifactVersion"] == SESSIONS.ARTIFACT_VERSION
    assert reply["turnId"] == turn["turnId"]
    assert reply["turnState"] == SESSIONS.TURN_COMPLETE


@pytest.mark.asyncio
async def test_an_interrupted_turn_keeps_the_operator_request(db: FakeDb) -> None:
    """Losing what someone asked is worse than showing that the answer failed."""
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    turn = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="investigate the return",
    )
    assert turn["turnState"] == SESSIONS.TURN_INCOMPLETE
    history = await SESSIONS.load_history(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA"
    )
    only = [m for m in history["messages"] if m["role"] == "user"]
    assert len(only) == 1
    assert only[0]["content"] == "investigate the return"
    assert only[0]["turnState"] == SESSIONS.TURN_INCOMPLETE


@pytest.mark.asyncio
async def test_a_failed_turn_can_be_recorded_without_deleting_the_request(db: FakeDb) -> None:
    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    turn = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="investigate",
    )
    await SESSIONS.append_assistant_artifact(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        turn_id=turn["turnId"], summary="Investigation could not be completed.",
        artifact={"investigation": [{"kind": "client", "status": "failed",
                                     "source": "aurora", "label": "Client record"}]},
        state=SESSIONS.TURN_FAILED,
    )
    history = await SESSIONS.load_history(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA"
    )
    assert [m["role"] for m in history["messages"]] == ["user", "assistant"]
    assert history["messages"][-1]["turnState"] == SESSIONS.TURN_FAILED


# ---------------------------------------------------------------------------
# Legacy row safety
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concierge_writes_never_touch_legacy_rows(db: FakeDb) -> None:
    legacy_before = json.dumps(
        [m for m in db.messages if m["session_id"] == "persona-theo-abc"], default=str
    )
    conv_before = json.dumps(db.conversations["persona-theo-abc"], default=str)

    s = await SESSIONS.create_session(db, customer_id="CUST-JESSICA", operator_sub="op-1")
    turn = await SESSIONS.append_operator_turn(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        operator_sub="op-1", message="hello",
    )
    await SESSIONS.append_assistant_artifact(
        db, session_id=s["sessionId"], customer_id="CUST-JESSICA",
        turn_id=turn["turnId"], summary="hi", artifact={},
    )

    legacy_after = json.dumps(
        [m for m in db.messages if m["session_id"] == "persona-theo-abc"], default=str
    )
    assert legacy_after == legacy_before, "legacy messages were modified"
    assert json.dumps(db.conversations["persona-theo-abc"], default=str) == conv_before


def test_no_destructive_migration_or_backfill_was_introduced() -> None:
    from pathlib import Path

    src = Path(SESSIONS.__file__).read_text()
    for destructive in ("DROP TABLE", "TRUNCATE", "DELETE FROM pellier.conversations",
                        "DELETE FROM pellier.messages", "ALTER TABLE"):
        assert destructive not in src, f"the writer performs {destructive}"
    migrations = Path(SESSIONS.__file__).resolve().parents[3] / "scripts" / "migrations"
    for path in migrations.glob("*.sql"):
        text = path.read_text()
        if "operator_concierge" in text:
            assert "UPDATE pellier.messages" not in text
            assert "DELETE FROM pellier.messages" not in text


def test_roles_stay_compatible_with_the_existing_table() -> None:
    """Inventing an `operator` role would break every existing reader for no gain."""
    assert SESSIONS.ROLE_OPERATOR == "user"
    assert SESSIONS.ROLE_ASSISTANT == "assistant"


# ---------------------------------------------------------------------------
# Review lineage
# ---------------------------------------------------------------------------

def test_propose_review_accepts_a_concierge_turn_id_unchanged() -> None:
    """The lineage hook: no translation layer between the two.

    session_id -> turn_id -> review_id -> execution_turn_id -> tool_audit.
    """
    import inspect

    from services import operator_review
    from services.turn_identity import new_turn_id

    signature = inspect.signature(operator_review.propose_review)
    assert "source_turn_id" in signature.parameters

    turn_id = new_turn_id()
    # The same format migration 021 constrains execution_turn_id to.
    import re

    assert re.fullmatch(r"turn-[0-9a-f]{32}", turn_id), turn_id
    migration = (
        __import__("pathlib").Path(operator_review.__file__).resolve().parents[3]
        / "scripts" / "migrations" / "021_governed_execution.sql"
    )
    assert "turn-[0-9a-f]{32}" in migration.read_text(), (
        "the execution turn format no longer matches what turn_identity mints"
    )
