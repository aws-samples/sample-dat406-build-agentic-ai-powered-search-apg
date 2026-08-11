"""Tests for the Agent Trace Proof Board and readiness API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import agent_trace
from routes.agent_trace import router as agent_trace_router


class _ProofDB:
    async def fetch_one(self, query: str, *params: Any) -> dict | None:
        if "catalog_count" in query:
            return {
                "catalog_count": 40,
                "warehouse_count": 120,
                "audit_count": 7,
            }
        if "FROM pellier.governed_receipts" in query:
            return {
                "receipt_id": 505,
                "audit_id": 303,
                "session_id": "gateway-marco-for-theo-incident",
                "principal_id": "CUST-MARCO",
                "principal_label": "Marco (Cognito JWT)",
                "tool": "process_return",
                "caller": "gateway",
                "decision": "ALLOW",
                "args": {"customer_id": "theo", "product_id": "37", "reason": "damaged"},
                "policy_engine_id": "policy-1",
                "policy_name": "process_return_damaged_only",
                "created_at": None,
            }
        if params == (303,):
            return {
                "audit_id": 303,
                "session_id": "managed-proof",
                "tool": "process_return",
                "caller": "gateway",
                "args": {"customer_id": "theo", "product_id": "37", "reason": "damaged"},
                "result": {"status": "success"},
                "latency_ms": 55,
                "created_at": None,
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


class _DenyProofDB(_ProofDB):
    async def fetch_one(self, query: str, *params: Any) -> dict | None:
        if "FROM pellier.governed_receipts" in query and params[:1] == ("gateway-identity-mismatch-proof",):
            return {
                "receipt_id": 606,
                "audit_id": None,
                "session_id": "gateway-identity-mismatch-proof",
                "principal_id": "CUST-MARCO",
                "principal_label": "Marco (Cognito JWT)",
                "tool": "process_return",
                "caller": "gateway",
                "decision": "DENY",
                "args": {
                    "customer_id": "theo",
                    "product_id": 37,
                    "reason": "damaged",
                    "absence_verified": True,
                },
                "policy_engine_id": "policy-1",
                "policy_name": "workshop_identity_match_forbid",
                "created_at": None,
            }
        return await super().fetch_one(query, *params)


def _client(stub_db: _ProofDB) -> TestClient:
    import app as app_module

    app_module.db_service = stub_db  # type: ignore[attr-defined]
    fast = FastAPI()
    fast.include_router(agent_trace_router)
    return TestClient(fast)


def _configure_managed(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "WORKSHOP_FORMAT", "governed", raising=False)
    monkeypatch.setattr(settings, "COGNITO_POOL_ID", "pool-1", raising=False)
    monkeypatch.setattr(settings, "COGNITO_CLIENT_ID", "client-1", raising=False)
    monkeypatch.setattr(settings, "COGNITO_DOMAIN", "auth.example.com", raising=False)
    monkeypatch.setattr(settings, "COGNITO_TEST_CREDENTIALS_SECRET_ARN", "secret-1", raising=False)
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


def test_governed_readiness_fails_without_managed_policy(monkeypatch) -> None:
    _configure_managed(monkeypatch)
    from config import settings

    monkeypatch.setattr(settings, "AGENTCORE_POLICY_ENGINE_ID", "", raising=False)
    client = _client(_ProofDB())

    body = client.get("/api/agent-trace/readiness").json()

    assert body["status"] == "not_ready"
    checks = {c["id"]: c for c in body["checks"]}
    assert checks["policy"]["required"] is True
    assert checks["policy"]["state"] == "fail"


def test_governed_readiness_requires_exact_warehouse_seed(monkeypatch) -> None:
    class _WrongWarehouseCountDB(_ProofDB):
        async def fetch_one(self, query: str, *params: Any) -> dict | None:
            if "catalog_count" in query:
                return {
                    "catalog_count": 40,
                    "warehouse_count": 119,
                    "audit_count": 7,
                }
            return await super().fetch_one(query, *params)

    _configure_managed(monkeypatch)
    client = _client(_WrongWarehouseCountDB())

    body = client.get("/api/agent-trace/readiness").json()

    assert body["status"] == "not_ready"
    checks = {c["id"]: c for c in body["checks"]}
    assert checks["aurora"]["state"] == "fail"
    assert "expected exactly 120" in checks["aurora"]["detail"]


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
    assert body["managedReceipt"]["governedPrincipalId"] == "CUST-MARCO"
    assert body["managedReceipt"]["governedDecision"] == "ALLOW"
    cards = {c["id"]: c for c in body["cards"]}
    assert cards["marco-floor-check"]["status"] == "complete"
    assert cards["marco-floor-check"]["group"] == "Agent and tool evidence"
    assert "act" not in cards["marco-floor-check"]
    assert cards["audit-ledger"]["status"] == "complete"
    assert cards["managed-rail"]["status"] == "complete"
    assert cards["marco-floor-check"]["lab"] == "Lab 1: Ground Answers in Live Data"
    assert cards["retrieval-comparison"]["lab"] == "Lab 2: Choose a Search Strategy You Can Defend"
    assert cards["retrieval-comparison"]["status"] == "available"
    assert cards["managed-rail"]["lab"] == "Lab 3: Run the Agent as a Managed Service"
    assert cards["managed-rail"]["required"] is True
    assert cards["audit-ledger"]["lab"] == "Lab 3: Run the Agent as a Managed Service"
    assert cards["runtime-gateway-policy"]["lab"] == "Lab 4: Stop the Wrong Action Before It Runs"
    assert cards["runtime-gateway-policy"]["required"] is True
    assert all("act" not in card for card in cards.values())
    assert "curl" in cards["managed-rail"]["fallback"]["command"]
    assert "search-strategies/compare" in cards["retrieval-comparison"]["fallback"]["command"]
    assert "process_return" in cards["audit-ledger"]["fallback"]["command"]


def test_proof_board_scopes_gateway_deny_absence(monkeypatch) -> None:
    _configure_managed(monkeypatch)
    client = _client(_DenyProofDB())

    r = client.get("/api/agent-trace/proof-board?session_id=gateway-identity-mismatch-proof")
    assert r.status_code == 200
    receipt = r.json()["managedReceipt"]

    assert receipt["governedDecision"] == "DENY"
    assert receipt["governedAuditId"] is None
    assert receipt["gatewayAuditPresent"] is False
    assert receipt["gatewayAuditAbsenceVerified"] is True
    assert "Gateway/Cedar DENY" in receipt["absenceCheckDetail"]


def test_build_state_reports_stock_keeper_midpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_trace,
        "_stock_keeper_definition_is_workshop_stub",
        lambda: False,
    )
    monkeypatch.setattr(
        agent_trace,
        "_floor_check_is_workshop_stub",
        lambda: True,
    )
    client = _client(_ProofDB())

    r = client.get("/api/agent-trace/build-state")
    assert r.status_code == 200
    body = r.json()

    assert body["agents"]["Stock Keeper"] == "shipped"
    assert body["tools"]["floor_check"] == "exercise"


def test_build_state_does_not_promote_scaffolded_stock_keeper_from_tool(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agent_trace,
        "_stock_keeper_definition_is_workshop_stub",
        lambda: True,
    )
    monkeypatch.setattr(
        agent_trace,
        "_floor_check_is_workshop_stub",
        lambda: False,
    )
    client = _client(_ProofDB())

    r = client.get("/api/agent-trace/build-state")
    assert r.status_code == 200
    body = r.json()

    assert body["agents"]["Stock Keeper"] == "exercise"
    assert body["tools"]["floor_check"] == "shipped"


def test_memory_semantic_empty_is_marked_settling(monkeypatch) -> None:
    async def _empty(_persona: str) -> list:
        return []

    async def _episodic(_persona: str) -> list:
        return [{"id": "ep-1", "content": "order", "substrate": "episodic"}]

    async def _procedural() -> list:
        return [{"id": "pr-1", "content": "floor_check", "substrate": "procedural"}]

    monkeypatch.setattr(
        agent_trace,
        "_load_live_working",
        _empty,
    )
    monkeypatch.setattr(
        agent_trace,
        "_load_live_semantic",
        _empty,
    )
    monkeypatch.setattr(
        agent_trace,
        "_load_live_episodic",
        _episodic,
    )
    monkeypatch.setattr(
        agent_trace,
        "_load_live_procedural",
        _procedural,
    )
    client = _client(_ProofDB())

    r = client.get("/api/agent-trace/memory/marco")
    assert r.status_code == 200
    body = r.json()

    assert body["semantic"]["source"] == "settling"
    assert body["semantic"]["items"] == []
    assert "asynchronous" in body["semantic"]["caveat"]
    assert body["episodic"]["source"] == "live"


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
