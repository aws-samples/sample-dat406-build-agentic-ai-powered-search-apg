"""Regression checks for intentionally absent public routes."""

import asyncio
from typing import Any

import app as app_module


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
        assert params == ("session-123", 16)
        return [
            {"role": "user", "content": "The bowl arrived chipped."},
            {"role": "assistant", "content": "I recorded the return."},
        ]


def test_boutique_session_route_reads_aurora_working_memory() -> None:
    payload = asyncio.run(
        app_module.get_boutique_chat_session("session-123", db=_HistoryDB())
    )

    assert payload == {
        "session_id": "session-123",
        "source": "aurora",
        "turns": [
            {"role": "user", "content": "The bowl arrived chipped."},
            {"role": "assistant", "content": "I recorded the return."},
        ],
    }
