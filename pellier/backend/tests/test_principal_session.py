"""`DatabaseService.principal_session` — the same-transaction guarantee.

Row-Level Security on `pellier.orders` and `pellier.returns` binds the
*effective* role and reads `pellier.principal_sub`. Both must hold on one
physical connection inside one transaction, which the ordinary accessors
cannot provide: `fetch_all`, `fetch_one`, and `execute_query` each take their
own pooled connection and release it.

That failure mode is quiet and dangerous. A `SET LOCAL` issued through
`execute_query` is invisible to the next call, so the protected statement runs
with no principal — which fails closed and reads as "no such row" rather than
"not authorized". Nothing errors. So these tests assert the mechanics rather
than the outcome:

  1. Role and principal are set on the *same* connection as the caller's
     statements, and inside a transaction.
  2. The principal is bound with `set_config`, parameterized — never
     interpolated into SQL.
  3. The role is whitelisted, because `SET ROLE` cannot be parameterized.
  4. The owner role can never be assumed through this API, which would make
     a governed session silently ungoverned.

The live enforcement proof (owner bypasses, mapped principal sees one row,
unmapped sees none, cross-customer write is rejected) is an integration
concern against a real cluster and is not asserted here.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import pytest

from services.database import DatabaseService, _RUNTIME_ROLES


class _Cursor:
    def __init__(self, calls: List[Tuple[str, Any]]) -> None:
        self._calls = calls

    async def __aenter__(self) -> "_Cursor":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None

    async def execute(self, sql: str, params: Any = None) -> None:
        self._calls.append((sql, params))


class _Transaction:
    def __init__(self, events: List[str]) -> None:
        self._events = events

    async def __aenter__(self) -> "_Transaction":
        self._events.append("begin")
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        self._events.append("end")


class _Connection:
    """Records the statement order and transaction boundaries."""

    def __init__(self) -> None:
        self.calls: List[Tuple[str, Any]] = []
        self.events: List[str] = []

    def cursor(self) -> _Cursor:
        return _Cursor(self.calls)

    def transaction(self) -> _Transaction:
        return _Transaction(self.events)


@pytest.fixture
def service(monkeypatch) -> Tuple[DatabaseService, _Connection]:
    """A service whose `get_connection` yields one recording connection."""
    from contextlib import asynccontextmanager

    db = DatabaseService()
    conn = _Connection()

    @asynccontextmanager
    async def _get_connection():
        yield conn

    monkeypatch.setattr(db, "get_connection", _get_connection)
    return db, conn


# ---------------------------------------------------------------------------
# Same connection, same transaction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_role_and_principal_are_bound_before_caller_statements(service):
    db, conn = service

    async with db.principal_session("sub-marco") as session:
        async with session.cursor() as cur:
            await cur.execute("SELECT 1 FROM pellier.orders", None)

    statements = [sql for sql, _params in conn.calls]
    assert statements[0] == "SET LOCAL ROLE pellier_agent"
    assert "set_config('pellier.principal_sub', %s, true)" in statements[1]
    # The caller's statement runs last, on the same connection.
    assert statements[2] == "SELECT 1 FROM pellier.orders"


@pytest.mark.asyncio
async def test_binding_happens_inside_a_transaction(service):
    """Outside a transaction `SET LOCAL` is a no-op with a warning.

    An unbound principal fails closed, so the symptom would be missing rows
    rather than an error — which is why the transaction is asserted.
    """
    db, conn = service

    async with db.principal_session("sub-marco"):
        pass

    assert conn.events == ["begin", "end"]


@pytest.mark.asyncio
async def test_caller_statements_share_the_bound_connection(service):
    """One connection for the whole block, or RLS sees no principal."""
    db, conn = service

    async with db.principal_session("sub-marco") as session:
        assert session is conn


# ---------------------------------------------------------------------------
# The principal is data, not SQL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_principal_is_parameterized_not_interpolated(service):
    db, conn = service
    hostile = "x'; DROP TABLE pellier.orders; --"

    async with db.principal_session(hostile):
        pass

    set_config = next(
        (sql, params) for sql, params in conn.calls if "set_config" in sql
    )
    assert set_config[1] == (hostile,)
    assert "DROP TABLE" not in set_config[0]


@pytest.mark.asyncio
async def test_anonymous_binds_an_empty_principal_explicitly(service):
    """Absent must be bound, not skipped.

    Binding it makes the intent legible in the transaction, and the policies
    resolve an empty principal to no customer scope — denied, not widened.
    """
    db, conn = service

    async with db.principal_session(None):
        pass

    set_config = next(params for sql, params in conn.calls if "set_config" in sql)
    assert set_config == ("",)


@pytest.mark.asyncio
async def test_local_scope_is_used_so_pool_reuse_cannot_leak(service):
    """The third `set_config` argument is `is_local`.

    This is the release-blocking pool-leakage property in its unit form: a
    transaction-local setting cannot survive into the next borrower of the
    same pooled connection. Session-scoped state could, and would silently
    grant transaction B the principal of transaction A.
    """
    db, conn = service

    async with db.principal_session("sub-marco"):
        pass

    set_config_sql = next(sql for sql, _p in conn.calls if "set_config" in sql)
    assert ", true)" in set_config_sql, "must bind transaction-locally"
    assert "SET LOCAL ROLE" in " ".join(sql for sql, _p in conn.calls)


# ---------------------------------------------------------------------------
# Role whitelist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_role_is_refused(service):
    db, _conn = service

    with pytest.raises(ValueError, match="Unknown runtime role"):
        async with db.principal_session("sub-marco", role="postgres"):
            pass


@pytest.mark.asyncio
async def test_owner_cannot_be_assumed_through_this_api(service):
    """Assuming the owner would bypass RLS and ungovern the session."""
    db, _conn = service

    for owner_like in ("postgres", "rds_superuser", "pellier_owner"):
        with pytest.raises(ValueError):
            async with db.principal_session("sub-marco", role=owner_like):
                pass


@pytest.mark.asyncio
async def test_query_role_is_available_for_generated_sql(service):
    db, conn = service

    async with db.principal_session("sub-marco", role="pellier_query"):
        pass

    assert conn.calls[0][0] == "SET LOCAL ROLE pellier_query"


def test_runtime_roles_exclude_the_owner():
    assert _RUNTIME_ROLES == {"pellier_agent", "pellier_query"}
    assert "postgres" not in _RUNTIME_ROLES


@pytest.mark.asyncio
async def test_role_name_cannot_carry_injection(service):
    """`SET ROLE` takes no parameters, so the whitelist is the only defense."""
    db, _conn = service

    with pytest.raises(ValueError):
        async with db.principal_session(
            "sub-marco", role="pellier_agent; DROP TABLE pellier.orders"
        ):
            pass
