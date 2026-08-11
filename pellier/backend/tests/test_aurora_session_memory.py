"""Tests for Aurora-backed Boutique working memory."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.aurora_session_memory import AuroraSessionMemory


class _StubDB:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.fetch_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.execute_calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
        self.fetch_calls.append((query, params))
        return self.rows

    async def execute_query(self, query: str, *params: Any) -> None:
        self.execute_calls.append((query, params))


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_load_history_returns_bounded_chronological_messages() -> None:
    db = _StubDB(
        [
            {"role": "user", "content": "Theo reported a chipped bowl."},
            {"role": "assistant", "content": "I recorded the return."},
            {"role": "system", "content": "not exposed"},
        ]
    )

    history = _run(AuroraSessionMemory(db).load_history("session-1", limit=500))

    assert history == [
        {"role": "user", "content": "Theo reported a chipped bowl."},
        {"role": "assistant", "content": "I recorded the return."},
    ]
    query, params = db.fetch_calls[0]
    assert "ORDER BY id DESC" in query
    assert "ORDER BY id;" in query
    assert params == ("session-1", 100)


def test_append_turn_pair_uses_one_atomic_statement() -> None:
    db = _StubDB()
    memory = AuroraSessionMemory(db)

    _run(
        memory.append_turn_pair(
            "session-2",
            user_message="The bowl was chipped.",
            assistant_message="The damaged return is recorded.",
            actor_id="theo",
            agent_name="dispatcher",
        )
    )

    assert len(db.execute_calls) == 1
    query, params = db.execute_calls[0]
    assert "WITH session_row AS" in query
    assert "ON CONFLICT (session_id) DO UPDATE" in query
    assert "INSERT INTO pellier.messages" in query
    assert "jsonb_build_object('source', 'boutique', 'actor_id', %s::text)" in query
    assert params == (
        "session-2",
        "dispatcher",
        "theo",
        "The bowl was chipped.",
        "The damaged return is recorded.",
    )


@pytest.mark.parametrize(
    ("session_id", "assistant_message"),
    [
        ("", "answer"),
        ("session-3", "   "),
    ],
)
def test_append_turn_pair_rejects_incomplete_receipts(
    session_id: str,
    assistant_message: str,
) -> None:
    db = _StubDB()
    with pytest.raises(ValueError):
        _run(
            AuroraSessionMemory(db).append_turn_pair(
                session_id,
                user_message="question",
                assistant_message=assistant_message,
                actor_id="anonymous",
                agent_name="dispatcher",
            )
        )
    assert db.execute_calls == []
