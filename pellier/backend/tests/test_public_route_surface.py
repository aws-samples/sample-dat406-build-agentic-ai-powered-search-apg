"""Regression checks for intentionally absent public routes."""

import asyncio
from typing import Any

import app as app_module
import pytest
from services.aurora_session_memory import session_actor_id


def test_unauthenticated_dev_chaos_routes_are_not_registered() -> None:
    paths = {
        path
        for route in app_module.app.routes
        if (path := getattr(route, "path", None)) is not None
    }

    assert "/api/dev/chaos" not in paths


class _HistoryDB:
    async def fetch_all(self, query: str, *params: Any) -> list[dict[str, str]]:
        assert "FROM pellier.messages" in query
        assert params == (
            "session-123",
            session_actor_id(None, "token-" * 8),
            16,
        )
        return [
            {"role": "user", "content": "The bowl arrived chipped."},
            {"role": "assistant", "content": "I recorded the return."},
        ]


def test_boutique_session_route_reads_aurora_working_memory() -> None:
    payload = asyncio.run(
        app_module.get_boutique_chat_session(
            "session-123",
            db=_HistoryDB(),
            user=None,
            session_token="token-" * 8,
        )
    )

    assert payload == {
        "session_id": "session-123",
        "source": "aurora",
        "turns": [
            {"role": "user", "content": "The bowl arrived chipped."},
            {"role": "assistant", "content": "I recorded the return."},
        ],
    }


def test_boutique_session_route_requires_anonymous_ownership_token() -> None:
    with pytest.raises(app_module.HTTPException) as exc_info:
        asyncio.run(
            app_module.get_boutique_chat_session(
                "session-123",
                db=_HistoryDB(),
                user=None,
                session_token=None,
            )
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "session_ownership_required"
