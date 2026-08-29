"""Live Observatory lineage is reconstructed from durable operator artifacts."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app as app_module
from routes import observatory
from services import governed_execution
from services import operator_concierge_sessions as sessions
from services import operator_review
from services import shopper_handoff


def _client(monkeypatch: Any) -> TestClient:
    monkeypatch.setattr(app_module, "db_service", object())
    fast = FastAPI()
    fast.include_router(observatory.router)
    fast.dependency_overrides[observatory.require_operator] = lambda: {
        "sub": "operator-sub",
        "username": "operator",
    }
    return TestClient(fast)


def test_operator_lineage_route_has_the_operator_boundary() -> None:
    route = next(
        route
        for route in observatory.router.routes
        if isinstance(route, APIRoute)
        and route.path == "/api/observatory/operator-lineage/{customer_id}"
    )

    assert any(
        dependency.call is observatory.require_operator
        for dependency in route.dependant.dependencies
    )


def test_empty_lineage_has_no_fixture_fallback(
    monkeypatch: Any,
) -> None:
    async def no_handoff(_db: Any, *, customer_id: str) -> None:
        assert customer_id == "CUST-THEO"
        return None

    monkeypatch.setattr(
        shopper_handoff, "resolve_latest_for_customer", no_handoff
    )
    monkeypatch.setattr(
        "services.data_source.database_source_label",
        lambda: "Local PostgreSQL",
    )

    response = _client(monkeypatch).get(
        "/api/observatory/operator-lineage/CUST-THEO"
    )

    assert response.status_code == 200
    assert response.json() == {
        "customerId": "CUST-THEO",
        "dataSource": "Local PostgreSQL",
        "handoff": None,
        "review": None,
        "orchestration": None,
        "execution": None,
    }


def test_lineage_joins_handoff_review_graph_and_operator_scoped_execution(
    monkeypatch: Any,
) -> None:
    handoff = {
        "schemaVersion": "1",
        "trust": "UNTRUSTED_SHOPPER_CONTEXT",
        "checkpoint": "WAITING_FOR_HUMAN",
        "customerId": "CUST-THEO",
        "source": {"sessionId": "shopper-session", "turnId": "turn-shopper"},
        "shopperRequest": "My bowl arrived chipped.",
        "routing": {
            "specialist": "customer_service",
            "tools": ["get_return_policy", "initiate_return"],
        },
        "proposal": {
            "reviewId": 8,
            "action": "initiate_return",
            "actionHash": "a" * 64,
        },
    }

    async def latest_handoff(_db: Any, *, customer_id: str) -> dict[str, Any]:
        assert customer_id == "CUST-THEO"
        return handoff

    async def review(_db: Any, review_id: int) -> dict[str, Any]:
        assert review_id == 8
        return {
            "id": 8,
            "customer_id": "CUST-THEO",
            "customer_name": "Theo",
            "action": "initiate_return",
            "status": "pending",
            "source_turn_id": "turn-shopper",
            "execution_turn_id": None,
            "action_hash": "a" * 64,
            "requested_at": "2026-08-28T12:00:00Z",
            "decided_at": None,
        }

    async def latest_receipt(_db: Any, review_id: int) -> dict[str, Any]:
        assert review_id == 8
        return {"receipt_id": 91}

    async def reconstruct(
        _db: Any, *, review_id: int, principal_sub: str
    ) -> dict[str, Any]:
        assert (review_id, principal_sub) == (8, "operator-sub")
        return {
            "latestReceipt": {
                "policy_outcome": "ALLOW",
                "aurora_outcome": "APPLIED",
                "evidence_outcome": "COMPLETE",
                "rail": "gateway-mcp",
            }
        }

    async def latest_session(_db: Any, *, customer_id: str) -> str:
        assert customer_id == "CUST-THEO"
        return "opc-theo"

    async def history(
        _db: Any, *, session_id: str, customer_id: str, limit: int
    ) -> dict[str, Any]:
        assert (session_id, customer_id, limit) == (
            "opc-theo",
            "CUST-THEO",
            100,
        )
        return {
            "messages": [
                {
                    "role": sessions.ROLE_ASSISTANT,
                    "turnId": "turn-operator",
                    "artifact": {
                        "orchestration": {
                            "pattern": "strands-graph",
                            "deploymentTarget": "AgentCore Runtime",
                            "executedNodes": [
                                {
                                    "nodeId": "case-investigator",
                                    "status": "completed",
                                    "durationMs": 8,
                                },
                                {
                                    "nodeId": "resolution-planner",
                                    "status": "completed",
                                    "durationMs": 13,
                                },
                            ],
                            "checkpoint": {
                                "state": "WAITING_FOR_HUMAN",
                                "reviewId": 8,
                                "actionHash": "a" * 64,
                            },
                        }
                    },
                }
            ]
        }

    monkeypatch.setattr(
        shopper_handoff, "resolve_latest_for_customer", latest_handoff
    )
    monkeypatch.setattr(operator_review, "get_review", review)
    monkeypatch.setattr(governed_execution, "latest_receipt", latest_receipt)
    monkeypatch.setattr(governed_execution, "reconstruct_execution", reconstruct)
    monkeypatch.setattr(sessions, "latest_session", latest_session)
    monkeypatch.setattr(sessions, "load_history", history)
    monkeypatch.setattr(
        "services.data_source.database_source_label",
        lambda: "Local PostgreSQL",
    )

    response = _client(monkeypatch).get(
        "/api/observatory/operator-lineage/CUST-THEO"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handoff"]["trust"] == "UNTRUSTED_SHOPPER_CONTEXT"
    assert body["review"]["reviewId"] == 8
    assert body["orchestration"]["sessionId"] == "opc-theo"
    assert body["orchestration"]["turnId"] == "turn-operator"
    assert [
        node["nodeId"] for node in body["orchestration"]["executedNodes"]
    ] == ["case-investigator", "resolution-planner"]
    assert body["execution"]["latestReceipt"]["rail"] == "gateway-mcp"


def test_lineage_mismatch_fails_closed(monkeypatch: Any) -> None:
    async def mismatch(_db: Any, *, customer_id: str) -> None:
        raise shopper_handoff.HandoffIntegrityError(
            "shopper_handoff_lineage_mismatch"
        )

    monkeypatch.setattr(
        shopper_handoff, "resolve_latest_for_customer", mismatch
    )

    response = _client(monkeypatch).get(
        "/api/observatory/operator-lineage/CUST-THEO"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "shopper_handoff_lineage_mismatch"
