"""Tests for the immutable, participant-facing governed turn receipt."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from services.governed_turn_receipt import (
    get_turn_receipt,
    get_visible_tool_audit,
    persist_turn_receipt,
)
from services.managed_policy import recent_decisions


class _ReceiptDB:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any] | None:
        self.calls.append((query, *params))
        if "FROM pellier.retrieval_receipts" in query:
            return {
                "receipt_id": 42,
                "embedding_model": "us.cohere.embed-v4:0",
                "rerank_model": "cohere.rerank-v3-5:0",
                "retrieval_config": {"rrf_k": 60},
                "citation_ids": ["P-2", "P-1"],
            }
        if "FROM pellier.governed_turn_receipts" in query:
            assert params == ("turn-persisted", "principal-1")
            return {
                "turn_id": "turn-persisted",
                "session_id": "session-1",
                "principal_sub": "principal-1",
                "principal_verified": True,
                "rail": "gateway-mcp",
                "model_config": '{"agent_model":"model-1"}',
                "retrieval_receipt_id": 42,
                "citations": '[{"entity_id":"P-1"}]',
                "tool_audit_ids": "[]",
                "policy_events": '[{"decision":"NOT_EVALUATED"}]',
                "trace": "{}",
                "terminal_outcome": "{}",
                "terminal_status": "complete",
                "latency_ms": 32,
                "created_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
            }
        return None

    async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
        self.calls.append((query, *params))
        if "FROM pellier.tool_audit" in query:
            assert params == ("turn-persisted",)
            return [
                {
                    "audit_id": 9,
                    "tool": "find_pieces_hybrid",
                    "caller": "gateway",
                    "latency_ms": 18,
                    "created_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                }
            ]
        if "FROM pellier.governed_receipts" in query:
            assert params == ("turn-persisted",)
            return []
        if "FROM pellier.product_catalog" in query:
            assert params == (["P-2", "P-1"],)
            return [
                {
                    "product_id": "P-1",
                    "name": "Linen Trouser",
                    "description": "Lightweight travel layer",
                    "updated_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
                },
                {
                    "product_id": "P-2",
                    "name": "Linen Camp Shirt",
                    "description": "Breathable resort shirt",
                    "updated_at": datetime(2026, 8, 2, tzinfo=timezone.utc),
                },
            ]
        return []

    async def execute_query(self, *args: Any) -> None:
        self.calls.append(args)


def test_persisted_receipt_uses_catalog_evidence_not_product_card_count() -> None:
    db = _ReceiptDB()

    receipt = asyncio.run(
        persist_turn_receipt(
            db,
            turn_id="turn-persisted",
            session_id="session-1",
            principal_sub="principal-1",
            rail="gateway-mcp",
            terminal_status="complete",
            latency_ms=32,
            trace={
                "traceKind": "managed-runtime-receipt",
                "traceId": "trace-1",
                "spans": [{"invented": "must not persist"}],
            },
        )
    )

    assert receipt == {
        "turn_id": "turn-persisted",
        "rail": "gateway-mcp",
        "terminal_status": "complete",
        "citation_count": 2,
        "tool_count": 1,
        "policy_decision": "NOT_EVALUATED",
        "latency_ms": 32,
    }
    insert = db.calls[-1]
    assert "INSERT INTO pellier.governed_turn_receipts" in insert[0]
    citations = json.loads(insert[8])
    assert [citation["entity_id"] for citation in citations] == ["P-2", "P-1"]
    assert citations[0] == {
        "evidence_id": "retrieval-42-catalog-P-2",
        "source_uri": "aurora://pellier/product_catalog/P-2",
        "revision": "2026-08-02T00:00:00+00:00",
        "quote": "Linen Camp Shirt: Breathable resort shirt",
        "entity_id": "P-2",
    }
    policy_events = json.loads(insert[10])
    assert policy_events[0]["decision"] == "NOT_EVALUATED"
    trace = json.loads(insert[11])
    assert trace["traceId"] == "trace-1"
    assert "spans" not in trace


def test_explicit_governed_policy_event_wins_over_absence() -> None:
    db = _ReceiptDB()

    async def policy_rows(query: str, *params: Any) -> list[dict[str, Any]]:
        if "FROM pellier.tool_audit" in query:
            return []
        if "FROM pellier.governed_receipts" in query:
            return [
                {
                    "receipt_id": 7,
                    "audit_id": None,
                    "tool": "process_return",
                    "caller": "gateway",
                    "decision": "DENY",
                    "policy_engine_id": "policy-1",
                    "policy_name": "deny-return",
                    "created_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                }
            ]
        if "FROM pellier.product_catalog" in query:
            return []
        return []

    db.fetch_all = policy_rows  # type: ignore[method-assign]
    receipt = asyncio.run(
        persist_turn_receipt(
            db,
            turn_id="turn-persisted",
            session_id="session-1",
            principal_sub="principal-1",
            rail="gateway-mcp",
            terminal_status="denied-before-execution",
            latency_ms=5,
            terminal_error_code="policy_denied",
        )
    )

    assert receipt is not None
    assert receipt["policy_decision"] == "DENY"


def test_receipt_read_is_scoped_to_the_verified_principal() -> None:
    receipt = asyncio.run(
        get_turn_receipt(
            _ReceiptDB(), turn_id="turn-persisted", principal_sub="principal-1"
        )
    )

    assert receipt is not None
    assert receipt["principal_sub"] == "principal-1"
    assert receipt["citations"] == [{"entity_id": "P-1"}]
    assert receipt["created_at"] == "2026-08-12T00:00:00+00:00"


def test_receipt_persistence_failure_returns_no_ui_receipt() -> None:
    class _BrokenDB:
        async def fetch_one(self, *_: Any) -> None:
            raise RuntimeError("database unavailable")

    result = asyncio.run(
        persist_turn_receipt(
            _BrokenDB(),
            turn_id="turn-broken",
            session_id="session-1",
            principal_sub="principal-1",
            rail="in-process",
            terminal_status="failed",
            latency_ms=1,
        )
    )

    assert result is None


def test_visible_tool_audit_uses_receipt_principal_scope() -> None:
    class _AuditDB:
        seen: tuple[Any, ...] | None = None

        async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
            self.seen = (query, *params)
            return [
                {
                    "audit_id": 11,
                    "session_id": "session-1",
                    "tool": "process_return",
                    "caller": "gateway",
                    "args": {"turn_id": "turn-persisted"},
                    "result": {"status": "success"},
                    "latency_ms": 12,
                    "created_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                }
            ]

    db = _AuditDB()
    rows = asyncio.run(
        get_visible_tool_audit(db, principal_sub="principal-1", limit=10)
    )

    assert rows[0]["audit_id"] == 11
    assert rows[0]["created_at"] == "2026-08-12T00:00:00+00:00"
    assert db.seen is not None
    assert db.seen[1:] == ("principal-1", "principal-1", 10)
    assert "governed_turn_receipts" in db.seen[0]
    assert "jsonb_build_object('audit_id', ta.audit_id)" in db.seen[0]


def test_recent_policy_decisions_include_explicit_allow_and_deny() -> None:
    class _PolicyDB:
        seen: tuple[Any, ...] | None = None

        async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
            self.seen = (query, *params)
            return [
                {
                    "receipt_id": 1,
                    "audit_id": 2,
                    "session_id": "session-1",
                    "tool": "process_return",
                    "caller": "gateway",
                    "decision": "ALLOW",
                    "args": {"turn_id": "turn-1"},
                    "policy_engine_id": "engine-1",
                    "policy_name": "allow-return",
                    "created_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                },
                {
                    "receipt_id": 3,
                    "audit_id": None,
                    "session_id": "session-1",
                    "tool": "process_return",
                    "caller": "gateway",
                    "decision": "DENY",
                    "args": {"turn_id": "turn-2"},
                    "policy_engine_id": "engine-1",
                    "policy_name": "deny-return",
                    "created_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                },
            ]

    db = _PolicyDB()
    result = asyncio.run(
        recent_decisions(
            db, principal_sub="principal-1", session_id="session-1", limit=10
        )
    )

    assert result["source"] == "governed-receipts"
    assert [decision["decision"] for decision in result["decisions"]] == [
        "ALLOW",
        "DENY",
    ]
    assert db.seen is not None
    assert db.seen[1:] == ("principal-1", "session-1", 10)
    assert "principal_id = %s" in db.seen[0]
