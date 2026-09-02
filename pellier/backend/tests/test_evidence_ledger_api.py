"""HTTP boundary tests for the principal-scoped Evidence Ledger."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

import app as app_module


class _LedgerDB:
    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable

    async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
        if self.unavailable:
            raise RuntimeError("database unavailable")
        if "evidence_ledger_event_refs" in query:
            if params != ("turn-1", "principal-1"):
                return []
            return [
                {
                    "turn_id": "turn-1",
                    "session_id": "session-1",
                    "event_kind": "response",
                    "phase": "terminal",
                    "status": "succeeded",
                    "provenance": "aurora-receipt",
                    "source_kind": "governed_turn_receipt",
                    "source_id": "turn-1",
                    "occurred_at": datetime(2026, 9, 2, tzinfo=timezone.utc),
                    "duration_ms": 12,
                    "summary": {
                        "terminal_status": "complete",
                        "citation_count": 0,
                        "tool_count": 0,
                    },
                }
            ]
        if "governed_query_receipts" in query or "retrieval_receipts" in query:
            return []
        raise AssertionError(f"unexpected query: {query}")


def _authenticated_client(monkeypatch, db: _LedgerDB) -> TestClient:
    monkeypatch.setattr(app_module, "db_service", db)
    app_module.app.dependency_overrides[app_module.get_current_user] = lambda: {
        "sub": "principal-1",
        "access_token": "jwt",
    }
    return TestClient(app_module.app)


def test_ledger_endpoint_requires_a_verified_principal(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "db_service", _LedgerDB())
    client = TestClient(app_module.app)

    response = client.get("/api/observatory/turns/turn-1/ledger")

    assert response.status_code == 401


def test_ledger_endpoint_returns_only_the_callers_turn(monkeypatch) -> None:
    client = _authenticated_client(monkeypatch, _LedgerDB())
    try:
        response = client.get("/api/observatory/turns/turn-1/ledger")
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_current_user, None)

    assert response.status_code == 200
    assert response.json()["turnId"] == "turn-1"
    assert response.json()["principalScoped"] is True


def test_ledger_endpoint_reports_projection_outage_as_unavailable(monkeypatch) -> None:
    client = _authenticated_client(monkeypatch, _LedgerDB(unavailable=True))
    try:
        response = client.get("/api/observatory/turns/turn-1/ledger")
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_current_user, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "evidence_ledger_unavailable"
