"""Tests for read-only proof/memory tools in services.agent_tools."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from services import agent_tools


class FakeDB:
    def __init__(
        self,
        *,
        customer: dict[str, Any] | None = None,
        orders: list[dict[str, Any]] | None = None,
        facts: list[dict[str, Any]] | None = None,
        receipts: list[dict[str, Any]] | None = None,
    ) -> None:
        self.customer = customer
        self.orders = orders or []
        self.facts = facts or []
        self.receipts = receipts or []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any] | None:
        self.calls.append((query, params))
        if "FROM pellier.customers" in query:
            return self.customer
        return None

    async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
        self.calls.append((query, params))
        if "FROM pellier.orders" in query:
            return self.orders
        if "FROM pellier.customer_episodic_seed" in query:
            return self.facts
        if "FROM pellier.tool_audit" in query:
            return self.receipts
        return []


def _call(tool_obj, *args: Any, **kwargs: Any) -> dict[str, Any]:
    fn = getattr(tool_obj, "__wrapped__", tool_obj)
    return json.loads(fn(*args, **kwargs))


def test_get_customer_preferences_reads_safe_customer_memory() -> None:
    db = FakeDB(
        customer={
            "id": "CUST-MARCO",
            "name": "Marco",
            "preferences_summary": "Natural fibers and warm neutrals.",
        },
        orders=[
            {
                "product_id": "11",
                "name": "Italian Linen Camp Shirt",
                "brand": "Pellier Editions",
                "category": "Apparel",
                "color": "Indigo",
                "price": 228,
                "quantity": 1,
                "placed_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
            }
        ],
        facts=[
            {
                "summary_text": "Asked about wrinkle-resistance.",
                "ts_offset_days": -9,
            }
        ],
    )
    agent_tools.set_db_service(db)

    payload = _call(agent_tools.get_customer_preferences, customer_id="CUST-MARCO")

    assert payload["status"] == "success"
    assert payload["read_only"] is True
    assert payload["customer"]["id"] == "CUST-MARCO"
    assert payload["recent_orders"][0]["name"] == "Italian Linen Camp Shirt"
    assert payload["memory_facts"][0]["summary"] == "Asked about wrinkle-resistance."
    assert payload["sources"] == [
        "pellier.customers",
        "pellier.orders",
        "pellier.customer_episodic_seed",
    ]


def test_get_audit_trail_returns_allow_receipts_with_result_summary() -> None:
    db = FakeDB(
        receipts=[
            {
                "audit_id": 158,
                "session_id": "persona-theo-abc",
                "tool": "initiate_return",
                "caller": "gateway",
                "args": {"customer_id": "CUST-THEO", "reason": "damaged"},
                "result": {"status": "success", "return_id": 77},
                "latency_ms": 184,
                "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
            }
        ]
    )
    agent_tools.set_db_service(db)

    payload = _call(
        agent_tools.get_audit_trail,
        tool_name="initiate_return",
        caller="gateway",
    )

    assert payload["status"] == "success"
    assert payload["read_only"] is True
    receipt = payload["receipts"][0]
    assert receipt["decision"] == "ALLOW"
    assert receipt["tool"] == "initiate_return"
    assert receipt["caller"] == "gateway"
    assert receipt["result_summary"]["status"] == "success"
    assert receipt["created_at"] == "2026-07-01T00:00:00+00:00"

    sql, params = db.calls[-1]
    assert "tool = %s" in sql
    assert "caller = %s" in sql
    assert params == ("initiate_return", "gateway", 3)


def test_get_audit_trail_no_rows_reports_no_allow_boundary() -> None:
    db = FakeDB(receipts=[])
    agent_tools.set_db_service(db)

    payload = _call(
        agent_tools.get_audit_trail,
        session_id="persona-marco-none",
        tool_name="check_inventory",
    )

    assert payload["status"] == "no_allow_receipt"
    assert payload["read_only"] is True
    assert payload["filters"] == {
        "session_id": "persona-marco-none",
        "tool_name": "check_inventory",
        "caller": None,
    }
    assert "no-row" in payload["interpretation"]
