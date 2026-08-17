"""Regression checks for intentionally absent public routes."""

import asyncio

import app as app_module
import pytest
from services.agentcore_memory import AgentCoreMemory


def test_unauthenticated_dev_chaos_routes_are_not_registered() -> None:
    paths = {
        path
        for route in app_module.app.routes
        if (path := getattr(route, "path", None)) is not None
    }

    assert "/api/dev/chaos" not in paths


def test_pellier_session_route_reads_agentcore_working_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_history(_self, namespace: str):
        assert namespace == "anon-session-123"
        return [
            {"role": "user", "content": "The bowl arrived chipped."},
            {"role": "assistant", "content": "I recorded the return."},
        ]

    monkeypatch.setattr(AgentCoreMemory, "get_session_history", fake_history)
    payload = asyncio.run(
        app_module.get_pellier_chat_session(
            "session-123",
            user=None,
            session_token="token-" * 8,
        )
    )

    assert payload == {
        "session_id": "session-123",
        "source": "agentcore-memory",
        "turns": [
            {"role": "user", "content": "The bowl arrived chipped."},
            {"role": "assistant", "content": "I recorded the return."},
        ],
    }


def test_pellier_session_route_requires_anonymous_ownership_token() -> None:
    with pytest.raises(app_module.HTTPException) as exc_info:
        asyncio.run(
            app_module.get_pellier_chat_session(
                "session-123",
                user=None,
                session_token=None,
            )
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "session_ownership_required"
