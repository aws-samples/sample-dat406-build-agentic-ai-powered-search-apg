"""Tests for Pellier Labs Proof Board and readiness API."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import agent_trace
from routes.agent_trace import router as agent_trace_router


def test_fixture_loader_rejects_path_traversal() -> None:
    assert agent_trace._load_fixture("../personas-config") is None
    assert agent_trace._load_fixture("tools/../../personas-config") is None


class _ProofDB:
    async def fetch_one(self, query: str, *params: Any) -> dict | None:
        if "catalog_count" in query:
            return {
                "catalog_count": 40,
                "warehouse_count": 120,
                "audit_count": 7,
            }
        if params == ("floor_check",):
            return {
                "audit_id": 101,
                "session_id": "marco-proof",
                "tool": "floor_check",
                "caller": "agent",
                "args": {"query": "Kyoto Linen Overshirt"},
                "result": {"quantity": 20},
                "latency_ms": 42,
                "created_at": None,
            }
        if params == ("process_return",):
            return {
                "audit_id": 202,
                "session_id": "theo-proof",
                "tool": "process_return",
                "caller": "agent",
                "args": {"reason": "damaged"},
                "result": {"status": "accepted"},
                "latency_ms": 81,
                "created_at": None,
            }
        if params == ("gateway",):
            return {
                "audit_id": 303,
                "session_id": "managed-proof",
                "tool": "floor_check",
                "caller": "gateway",
                "args": {},
                "result": {},
                "latency_ms": 55,
                "created_at": None,
            }
        return {
            "audit_id": 404,
            "session_id": "latest",
            "tool": "floor_check",
            "caller": "agent",
            "args": {},
            "result": {},
            "latency_ms": 11,
            "created_at": None,
        }


class _AuditDB(_ProofDB):
    def __init__(self) -> None:
        self.fetch_all_calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch_all(
        self,
        query: str,
        *params: Any,
    ) -> list[dict[str, Any]]:
        self.fetch_all_calls.append((query, params))
        return [
            {
                "audit_id": 101,
                "session_id": "marco-proof",
                "tool": "floor_check",
                "caller": "agent",
                "args": {"product_query": "Hadley shirt"},
                "result": {"status": "success"},
                "latency_ms": 42,
                "created_at": None,
            }
        ]


def _client(stub_db: _ProofDB) -> TestClient:
    import app as app_module

    app_module.db_service = stub_db  # type: ignore[attr-defined]
    fast = FastAPI()
    fast.include_router(agent_trace_router)
    return TestClient(fast)


def _configure_managed(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "COGNITO_POOL_ID", "pool-1", raising=False)
    monkeypatch.setattr(settings, "COGNITO_CLIENT_ID", "client-1", raising=False)
    monkeypatch.setattr(settings, "COGNITO_DOMAIN", "auth.example.com", raising=False)
    monkeypatch.setattr(settings, "AGENTCORE_MEMORY_ID", "mem-1", raising=False)
    monkeypatch.setattr(settings, "AGENTCORE_RUNTIME_ENDPOINT", "runtime-arn", raising=False)
    monkeypatch.setattr(settings, "AGENTCORE_GATEWAY_URL", "https://gateway.example/mcp", raising=False)
    monkeypatch.setattr(settings, "AGENTCORE_POLICY_ENGINE_ID", "policy-1", raising=False)


def test_readiness_reports_live_pillars(monkeypatch) -> None:
    _configure_managed(monkeypatch)
    client = _client(_ProofDB())

    r = client.get("/api/agent-trace/readiness")
    assert r.status_code == 200
    body = r.json()

    assert body["status"] == "ready"
    checks = {c["id"]: c for c in body["checks"]}
    assert checks["aurora"]["state"] == "pass"
    assert checks["identity"]["state"] == "pass"
    assert checks["runtime"]["state"] == "pass"
    assert checks["gateway"]["state"] == "pass"
    assert checks["policy"]["state"] == "pass"
    assert body["counts"]["catalog_count"] == 40


def test_build_state_tracks_tool_and_agent_completion_independently(
    monkeypatch,
) -> None:
    client = _client(_ProofDB())
    monkeypatch.setattr(
        agent_trace,
        "_floor_check_is_workshop_stub",
        lambda: True,
    )
    monkeypatch.setattr(
        agent_trace,
        "_stock_keeper_has_floor_check_grant",
        lambda: False,
    )

    starter = client.get("/api/agent-trace/build-state").json()
    assert starter["tools"]["floor_check"] == "exercise"
    assert starter["agents"]["Stock Keeper"] == "exercise"

    monkeypatch.setattr(
        agent_trace,
        "_floor_check_is_workshop_stub",
        lambda: False,
    )
    tool_wired = client.get("/api/agent-trace/build-state").json()
    assert tool_wired["tools"]["floor_check"] == "shipped"
    assert tool_wired["agents"]["Stock Keeper"] == "exercise"

    monkeypatch.setattr(
        agent_trace,
        "_stock_keeper_has_floor_check_grant",
        lambda: True,
    )
    complete = client.get("/api/agent-trace/build-state").json()
    assert complete["tools"]["floor_check"] == "shipped"
    assert complete["agents"]["Stock Keeper"] == "shipped"


def test_floor_check_runner_executes_participant_tool_before_agent_grant(
    monkeypatch,
) -> None:
    from services import agent_tools

    monkeypatch.setattr(
        agent_trace,
        "_floor_check_is_workshop_stub",
        lambda: False,
    )
    monkeypatch.setattr(
        agent_tools,
        "floor_check",
        lambda product_query="": json.dumps(
            {
                "status": "success",
                "product_query": product_query,
                "warehouses": [],
            }
        ),
    )
    client = _client(_ProofDB())

    response = client.get(
        "/api/agent-trace/tools/floor-check/run",
        params={"product_query": "Hadley shirt"},
    )

    assert response.status_code == 200
    assert response.json()["product_query"] == "Hadley shirt"


def test_recent_tool_audit_filters_by_tool_and_names_aurora_source() -> None:
    db = _AuditDB()
    client = _client(db)

    response = client.get(
        "/api/agent-trace/tool-audit/recent",
        params={"tool": "floor_check", "limit": 1},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "pellier.tool_audit"
    assert response.json()["filters"] == {"tool": "floor_check"}
    assert response.json()["rows"][0]["audit_id"] == 101
    query, params = db.fetch_all_calls[-1]
    assert "WHERE tool = %s" in query
    assert params == ("floor_check", 1)


def test_proof_board_returns_cards_receipt_and_fallbacks(monkeypatch) -> None:
    _configure_managed(monkeypatch)
    monkeypatch.setattr(
        agent_trace,
        "_floor_check_is_workshop_stub",
        lambda: False,
    )
    monkeypatch.setattr(
        agent_trace,
        "_latest_managed_receipt",
        lambda session_id=None: {
            "present": True,
            "traceKind": "managed-runtime-receipt",
            "runtime": "agentcore-managed",
            "rail": "gateway-mcp",
            "jwtPassthrough": True,
            "gatewayPassthrough": True,
        },
    )
    client = _client(_ProofDB())

    r = client.get("/api/agent-trace/proof-board?session_id=managed-proof")
    assert r.status_code == 200
    body = r.json()

    assert body["managedReceipt"]["jwtPassthrough"] is True
    cards = {c["id"]: c for c in body["cards"]}
    assert cards["marco-floor-check"]["status"] == "complete"
    assert cards["marco-floor-check"]["group"] == "Agent and tool evidence"
    assert "act" not in cards["marco-floor-check"]
    assert cards["audit-ledger"]["status"] == "complete"
    assert cards["managed-rail"]["status"] == "complete"
    assert "curl" in cards["managed-rail"]["fallback"]["command"]
    assert "process_return" in cards["audit-ledger"]["fallback"]["command"]


def test_readiness_missing_database_is_not_ready(monkeypatch) -> None:
    import app as app_module

    _configure_managed(monkeypatch)
    app_module.db_service = None  # type: ignore[attr-defined]
    fast = FastAPI()
    fast.include_router(agent_trace_router)
    client = TestClient(fast)

    r = client.get("/api/agent-trace/readiness")
    assert r.status_code == 200
    body = r.json()

    assert body["status"] == "not_ready"
    aurora = next(c for c in body["checks"] if c["id"] == "aurora")
    assert aurora["state"] == "fail"


def teardown_function() -> None:
    try:
        import app as app_module

        app_module.db_service = None  # type: ignore[attr-defined]
    except Exception:
        pass
