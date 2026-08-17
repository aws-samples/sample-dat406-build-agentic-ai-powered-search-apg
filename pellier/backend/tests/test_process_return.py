"""Tests for ``BusinessLogic.process_return`` and the ``process_return`` @tool.

The atomic transaction is the central correctness claim: ownership check
→ INSERT into returns → conditional UPDATE of product_catalog.quantity,
all in one go. We mock psycopg so these run offline; the real Aurora
write is exercised in the live verification phase.

Runnable from the repo root:
    pellier/backend/.venv/bin/python -m pytest \
        pellier/backend/tests/test_process_return.py -v
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pytest

from services.business_logic import BusinessLogic


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Scripted FakeCursor — feeds different fetchone() responses to each
# step of the process_return transaction so we can exercise success
# and rejection paths without a live DB.
# ---------------------------------------------------------------------------


class FakeCursor:
    """Records every execute(); fetchone() returns scripted responses."""

    def __init__(self, fetchone_returns: List[Optional[Dict[str, Any]]]):
        self._returns = list(fetchone_returns)
        self._next = 0
        self.executes: List[tuple[str, Optional[Sequence[Any]]]] = []

    async def __aenter__(self) -> "FakeCursor":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def execute(self, sql: str, params: Any = None) -> None:
        self.executes.append((sql, params))

    async def fetchone(self) -> Optional[Dict[str, Any]]:
        if self._next >= len(self._returns):
            return None
        out = self._returns[self._next]
        self._next += 1
        return out


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor

    def cursor(self) -> FakeCursor:
        return self._cursor


class FakeDB:
    def __init__(self, fetchone_returns: List[Optional[Dict[str, Any]]]):
        self.cursor = FakeCursor(fetchone_returns)
        self.conn = FakeConnection(self.cursor)
        self.fetch_one_calls: List[tuple[str, tuple[Any, ...]]] = []

    @asynccontextmanager
    async def get_connection(self):
        yield self.conn

    async def fetch_one(self, query: str, *params: Any) -> Optional[Dict[str, Any]]:
        self.fetch_one_calls.append((query, params))
        return await self.cursor.fetchone()


# ---------------------------------------------------------------------------
# Defense-in-depth: bad reasons rejected before SQL runs
# ---------------------------------------------------------------------------


class TestReasonValidation:

    def test_unknown_reason_returns_policy_blocked(self) -> None:
        db = FakeDB([])  # SQL never runs
        logic = BusinessLogic(db)  # type: ignore[arg-type]
        result = _run(logic.process_return("c-1", 21, "evil", "return-evil"))
        assert result["status"] == "policy_blocked"
        assert "evil" in result["message"]
        # No SQL executed because the guard runs before get_connection().
        assert db.cursor.executes == []

    def test_empty_reason_returns_policy_blocked(self) -> None:
        db = FakeDB([])
        logic = BusinessLogic(db)  # type: ignore[arg-type]
        result = _run(logic.process_return("c-1", 21, "", "return-empty"))
        assert result["status"] == "policy_blocked"

    @pytest.mark.parametrize("reason", [
        "damaged", "wrong_size", "not_as_described", "changed_mind", "other",
    ])
    def test_canonical_reasons_pass_validation(self, reason: str) -> None:
        # Ownership check returns no rows so the call rejects on
        # ownership, but only AFTER reason validation passed (proving
        # the reason was canonical).
        db = FakeDB([{"result": {"status": "error", "message": "did not order"}}])
        logic = BusinessLogic(db)  # type: ignore[arg-type]
        result = _run(logic.process_return("c-1", 21, reason, f"return-{reason}"))
        # If reason had been blocked, status would be "policy_blocked";
        # we expect "error" because ownership failed.
        assert result["status"] == "error"
        assert "did not order" in result["message"]


# ---------------------------------------------------------------------------
# Shared Aurora function contract
# ---------------------------------------------------------------------------


class TestIdempotentStoredFunctions:

    def test_process_return_calls_idempotent_function(self) -> None:
        expected = {
            "status": "success",
            "return_id": 42,
            "product_id": 21,
            "name": "Wabi-Sabi Bowl",
            "reason": "damaged",
            "new_quantity": 7,
            "warehouse_id": "BK-01",
            "idempotent_replay": False,
        }
        db = FakeDB([{"result": expected}])
        logic = BusinessLogic(db)  # type: ignore[arg-type]
        result = _run(logic.process_return(
            "c-theo",
            21,
            "damaged",
            "return-c-theo-21-1",
        ))

        assert result == expected
        query, params = db.fetch_one_calls[0]
        assert "pellier.process_return_idempotent" in query
        assert params[0] == "return-c-theo-21-1"
        assert len(params[1]) == 64

    def test_replay_result_is_returned_without_new_local_mutation(self) -> None:
        replay = {
            "status": "success",
            "return_id": 42,
            "idempotent_replay": True,
        }
        db = FakeDB([{"result": json.dumps(replay)}])
        logic = BusinessLogic(db)  # type: ignore[arg-type]

        result = _run(logic.process_return(
            "c-theo",
            21,
            "damaged",
            "return-c-theo-21-1",
        ))

        assert result == replay

    def test_restock_targets_warehouse_and_uses_idempotency(self) -> None:
        expected = {
            "status": "success",
            "product_id": "21",
            "new_quantity": 18,
            "warehouse_id": "ATX-02",
            "idempotent_replay": False,
        }
        db = FakeDB([{"result": expected}])
        logic = BusinessLogic(db)  # type: ignore[arg-type]

        result = _run(logic.restock_shelf(
            21,
            5,
            "restock-21-atx-1",
            "ATX-02",
        ))

        assert result == expected
        query, params = db.fetch_one_calls[0]
        assert "pellier.restock_shelf_idempotent" in query
        assert params[0] == "restock-21-atx-1"
        assert params[-1] == "ATX-02"


# ---------------------------------------------------------------------------
# Tool wrapper — the @tool that agents actually call
# ---------------------------------------------------------------------------


class TestToolWrapper:

    def test_returns_json_envelope_when_db_uninitialized(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import services.agent_tools as agent_tools
        monkeypatch.setattr(agent_tools, "_db_service", None)
        result = json.loads(agent_tools.process_return(
            "c-1",
            21,
            "damaged",
            "return-c-1-21",
        ))
        assert "Database service not initialized" in result["error"]

    @pytest.mark.parametrize(
        ("tool_name", "args"),
        [
            ("process_return", ("c-1", 21, "damaged", "return-c-1-21")),
            ("restock_shelf", (21, 10, "restock-21-1")),
        ],
    )
    def test_governed_mutations_require_managed_gateway(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tool_name: str,
        args: tuple[Any, ...],
    ) -> None:
        import services.agent_tools as agent_tools
        from config import settings

        monkeypatch.setattr(settings, "WORKSHOP_FORMAT", "governed")
        result = json.loads(getattr(agent_tools, tool_name)(*args))

        assert result == {
            "error": "managed_rail_required",
            "tool": tool_name,
            "required_rail": "gateway-mcp",
        }


def test_gateway_restock_writes_execution_audit() -> None:
    repo = Path(__file__).resolve().parents[3]
    source = (
        repo / "scripts" / "deploy" / "pellier_search_server.py"
    ).read_text()

    assert '"product_id": product.get("product_id")' in source
    assert 'if tool_name == "restock_shelf"' in source
    assert "_write_tool_audit_in_transaction(" in source
    assert "transactionId=transaction_id" in source
    assert '"gateway-stock-keeper"' in source
