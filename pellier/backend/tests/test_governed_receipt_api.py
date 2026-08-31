"""HTTP boundary tests for principal-scoped governed receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

import app as app_module


class _ReceiptDB:
    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any] | None:
        if "FROM pellier.governed_turn_receipts" not in query:
            return None
        if params != ("turn-1", "principal-1"):
            return None
        return {
            "turn_id": "turn-1",
            "session_id": "session-1",
            "principal_sub": "principal-1",
            "principal_verified": True,
            "rail": "gateway-mcp",
            "model_config": {},
            "retrieval_receipt_id": None,
            "citations": [],
            "tool_audit_ids": [],
            "policy_events": [{"decision": "NOT_EVALUATED"}],
            "trace": {},
            "terminal_outcome": {},
            "terminal_status": "complete",
            "latency_ms": 12,
            "created_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
        }


def test_governed_receipt_requires_verified_principal(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "db_service", _ReceiptDB())
    client = TestClient(app_module.app)

    response = client.get("/api/governed-receipts/turn-1")

    assert response.status_code == 401


def test_governed_receipt_is_scoped_to_the_verified_principal(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "db_service", _ReceiptDB())
    app_module.app.dependency_overrides[app_module.get_current_user] = lambda: {
        "sub": "principal-1",
        "access_token": "jwt",
    }
    try:
        client = TestClient(app_module.app)
        response = client.get("/api/governed-receipts/turn-1")
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_current_user, None)

    assert response.status_code == 200
    assert response.json()["turn_id"] == "turn-1"
    assert response.json()["principal_sub"] == "principal-1"
