"""Two rails for one write, and one denial that must not lie.

`BusinessLogic.initiate_return` chooses its rail from `principal_sub`:

* **None** — the ordinary connection, owned by the table owner, which
  bypasses Row-Level Security. This is the anonymous and simulated-persona
  path the storefront uses today, and it is exactly why an agent on this rail
  can process another customer's return: the only gate is the `customer_id`
  argument, which the caller supplies.
* **A verified subject** — `principal_session`, a non-owner role with the
  principal bound transaction-locally, so RLS decides which customer's rows
  may change.

The subtle part is the message. `process_return_idempotent` establishes
ownership by selecting from `pellier.orders`; under RLS that select is scoped,
so a request for an out-of-scope customer finds nothing and the function
reports "Customer X did not order product Y". That sentence is **false** — the
order may well exist — and it disguises an authorization boundary as a fact
about the data. So the governed rail re-asks the database whether the customer
is in scope, and reports an authorization denial when it is not.

The discrimination matters in both directions, and both are pinned here: an
in-scope customer who genuinely never ordered the product must still get the
truthful "did not order" answer.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

import pytest

from services.business_logic import BusinessLogic


class _Cursor:
    """Replays scripted results and records the SQL it was given."""

    def __init__(self, script: List[Any], calls: List[Tuple[str, Any]]) -> None:
        self._script = script
        self._calls = calls
        self._last: Any = None

    async def __aenter__(self) -> "_Cursor":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None

    async def execute(self, sql: str, params: Any = None) -> None:
        self._calls.append((sql, params))
        self._last = self._script.pop(0) if self._script else None

    async def fetchone(self) -> Any:
        return self._last


class _Transaction:
    async def __aenter__(self) -> "_Transaction":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None


class _Connection:
    def __init__(self, script: List[Any], calls: List[Tuple[str, Any]]) -> None:
        self._script = script
        self._calls = calls

    def cursor(self) -> _Cursor:
        return _Cursor(self._script, self._calls)

    def transaction(self) -> _Transaction:
        return _Transaction()


class _Db:
    """Minimal DatabaseService stand-in that records which rail was used."""

    def __init__(self, *, governed_script: Optional[List[Any]] = None,
                 owner_result: Any = None) -> None:
        self.governed_script = governed_script or []
        self.owner_result = owner_result
        self.calls: List[Tuple[str, Any]] = []
        self.principal_sessions: List[Optional[str]] = []
        self.owner_queries: List[str] = []

    async def fetch_one(self, query: str, *params: Any) -> Any:
        self.owner_queries.append(query)
        return self.owner_result

    @asynccontextmanager
    async def principal_session(self, principal_sub: Optional[str], **_kw: Any):
        self.principal_sessions.append(principal_sub)
        yield _Connection(self.governed_script, self.calls)


def _return_row(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"result": payload}


_SUCCESS = {"status": "success", "return_id": 7, "product_id": 11}
_NOT_ORDERED = {
    "status": "error",
    "message": "Customer CUST-ANNA did not order product 21; cannot process return.",
}


# ---------------------------------------------------------------------------
# Rail selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_principal_uses_the_owner_rail():
    """Anonymous turns must keep working; they are the storefront default."""
    db = _Db(owner_result=_return_row(_SUCCESS))
    logic = BusinessLogic(db)

    result = await logic.initiate_return("CUST-MARCO", 11, "damaged", "key-1")

    assert result["status"] == "success"
    assert db.principal_sessions == [], "must not open a governed session"
    assert db.owner_queries, "must go through the ordinary connection"


@pytest.mark.asyncio
async def test_verified_principal_uses_the_governed_rail():
    db = _Db(governed_script=[_return_row(_SUCCESS)])
    logic = BusinessLogic(db)

    result = await logic.initiate_return(
        "CUST-MARCO", 11, "damaged", "key-2", principal_sub="sub-marco"
    )

    assert result["status"] == "success"
    assert db.principal_sessions == ["sub-marco"]
    assert db.owner_queries == [], "must not fall back to the owner connection"


@pytest.mark.asyncio
async def test_governed_rail_binds_the_subject_not_the_persona():
    """A UI selection must never choose which rows are writable."""
    db = _Db(governed_script=[_return_row(_SUCCESS)])
    logic = BusinessLogic(db)

    await logic.initiate_return(
        "CUST-ANNA", 21, "damaged", "key-3", principal_sub="sub-marco"
    )

    # The bound principal is the subject; the customer argument is just an
    # argument, and RLS is what reconciles them.
    assert db.principal_sessions == ["sub-marco"]


# ---------------------------------------------------------------------------
# The denial must not lie
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_out_of_scope_customer_is_reported_as_an_authorization_denial():
    """"Did not order" would be a false claim about Aurora's contents."""
    db = _Db(
        governed_script=[
            _return_row(_NOT_ORDERED),
            {"in_scope": 0},  # CUST-ANNA is not in this principal's scope
        ]
    )
    logic = BusinessLogic(db)

    result = await logic.initiate_return(
        "CUST-ANNA", 21, "damaged", "key-4", principal_sub="sub-marco"
    )

    assert result["status"] == "policy_blocked"
    assert result["denied_by"] == "database_row_level_security"
    assert "not authorized" in result["message"]
    assert "did not order" not in result["message"]
    # And it says nothing changed, because nothing did.
    assert "nothing was changed" in result["message"]


@pytest.mark.asyncio
async def test_in_scope_customer_who_never_ordered_still_gets_the_truth():
    """The other direction: a real data answer must survive the translation."""
    db = _Db(
        governed_script=[
            _return_row(
                {
                    "status": "error",
                    "message": "Customer CUST-MARCO did not order product 39; "
                    "cannot process return.",
                }
            ),
            {"in_scope": 1},  # Marco IS in scope; the order genuinely is absent
        ]
    )
    logic = BusinessLogic(db)

    result = await logic.initiate_return(
        "CUST-MARCO", 39, "damaged", "key-5", principal_sub="sub-marco"
    )

    assert result["status"] == "error"
    assert "did not order product 39" in result["message"]
    assert "denied_by" not in result


@pytest.mark.asyncio
async def test_scope_is_only_consulted_when_ownership_lookup_failed():
    """A successful write must not pay for an extra round trip."""
    db = _Db(governed_script=[_return_row(_SUCCESS)])
    logic = BusinessLogic(db)

    await logic.initiate_return(
        "CUST-MARCO", 11, "damaged", "key-6", principal_sub="sub-marco"
    )

    scope_queries = [
        sql for sql, _p in db.calls if "current_principal_customers" in sql
    ]
    assert scope_queries == []


@pytest.mark.asyncio
async def test_scope_check_asks_about_the_requested_customer():
    db = _Db(governed_script=[_return_row(_NOT_ORDERED), {"in_scope": 0}])
    logic = BusinessLogic(db)

    await logic.initiate_return(
        "CUST-ANNA", 21, "damaged", "key-7", principal_sub="sub-marco"
    )

    scope_call = next(
        (sql, params) for sql, params in db.calls
        if "current_principal_customers" in sql
    )
    assert scope_call[1] == ("CUST-ANNA",)


@pytest.mark.asyncio
async def test_unrelated_errors_are_not_reclassified():
    """Only the not-ordered outcome is ambiguous under RLS."""
    db = _Db(
        governed_script=[
            _return_row({"status": "error", "message": "idempotency conflict"})
        ]
    )
    logic = BusinessLogic(db)

    result = await logic.initiate_return(
        "CUST-MARCO", 11, "damaged", "key-8", principal_sub="sub-marco"
    )

    assert result["status"] == "error"
    assert result["message"] == "idempotency conflict"
    assert not [sql for sql, _p in db.calls if "current_principal_customers" in sql]


@pytest.mark.asyncio
async def test_policy_blocked_reason_is_still_rejected_before_any_rail():
    """An invalid reason never reaches the database on either rail."""
    db = _Db()
    logic = BusinessLogic(db)

    result = await logic.initiate_return(
        "CUST-MARCO", 11, "because", "key-9", principal_sub="sub-marco"
    )

    assert result["status"] == "policy_blocked"
    assert db.principal_sessions == []
    assert db.owner_queries == []


# ---------------------------------------------------------------------------
# The tool passes the principal it was given, and nothing else
# ---------------------------------------------------------------------------


def _call_tool(tool: Any, **kwargs: Any) -> Any:
    """Invoke a Strands `@tool` body directly.

    The decorator returns a `DecoratedFunctionTool`; the plain function is
    reachable through the standard `__wrapped__` attribute, which is the
    convention the rest of this suite uses.
    """
    fn = getattr(tool, "__wrapped__", tool)
    return fn(**kwargs)


def test_tool_reads_the_principal_from_the_turn_context(monkeypatch):
    """The deterministic tool must bind the turn's verified subject.

    Tools run through `asyncio.to_thread` with the caller's context captured,
    so the principal arrives via ContextVar rather than through every
    signature. If the tool stopped reading it, every governed write would
    silently fall back to the ungoverned owner rail.
    """
    import services.agent_tools as agent_tools
    from services.turn_identity import principal_sub_var

    captured: Dict[str, Any] = {}

    class _Logic:
        def __init__(self, _db):
            pass

        async def initiate_return(self, *args, **kwargs):
            captured["kwargs"] = kwargs
            return {"status": "success"}

    monkeypatch.setattr(agent_tools, "_db_service", object())
    monkeypatch.setattr(
        "services.business_logic.BusinessLogic", _Logic, raising=True
    )
    monkeypatch.setattr(agent_tools, "_managed_rail_required", lambda _n: None)

    token = principal_sub_var.set("sub-theo")
    try:
        _call_tool(
            agent_tools.initiate_return,
            customer_id="CUST-THEO", product_id=31, reason="damaged",
            idempotency_key="key-10",
        )
    finally:
        principal_sub_var.reset(token)

    assert captured["kwargs"]["principal_sub"] == "sub-theo"


def test_anonymous_turn_passes_no_principal(monkeypatch):
    """Absent must reach the business layer as None, not as a persona."""
    import services.agent_tools as agent_tools
    from services.turn_identity import principal_sub_var

    captured: Dict[str, Any] = {}

    class _Logic:
        def __init__(self, _db):
            pass

        async def initiate_return(self, *args, **kwargs):
            captured["kwargs"] = kwargs
            return {"status": "success"}

    monkeypatch.setattr(agent_tools, "_db_service", object())
    monkeypatch.setattr(
        "services.business_logic.BusinessLogic", _Logic, raising=True
    )
    monkeypatch.setattr(agent_tools, "_managed_rail_required", lambda _n: None)

    token = principal_sub_var.set(None)
    try:
        _call_tool(
            agent_tools.initiate_return,
            customer_id="CUST-THEO", product_id=31, reason="damaged",
            idempotency_key="key-11",
        )
    finally:
        principal_sub_var.reset(token)

    assert captured["kwargs"]["principal_sub"] is None
