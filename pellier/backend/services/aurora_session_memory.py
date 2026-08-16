"""Aurora-backed working memory for the Pellier chat path."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


_LOAD_HISTORY_SQL = """
SELECT recent.role, recent.content
FROM (
    SELECT messages.id, messages.role, messages.content
    FROM pellier.messages AS messages
    INNER JOIN pellier.conversations AS conversations
        ON conversations.session_id = messages.session_id
    WHERE messages.session_id = %s
      AND conversations.metadata->>'actor_id' = %s
      AND messages.role IN ('user', 'assistant')
    ORDER BY messages.id DESC
    LIMIT %s
) AS recent
ORDER BY recent.id;
"""

_APPEND_TURN_SQL = """
WITH session_row AS (
    INSERT INTO pellier.conversations (
        session_id,
        agent_name,
        context,
        metadata,
        updated_at
    )
    VALUES (
        %s,
        %s,
        '{}'::jsonb,
        jsonb_build_object('source', 'boutique', 'actor_id', %s::text),
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (session_id) DO UPDATE
    SET agent_name = EXCLUDED.agent_name,
        metadata = pellier.conversations.metadata || EXCLUDED.metadata,
        updated_at = CURRENT_TIMESTAMP
    WHERE pellier.conversations.metadata->>'actor_id'
        = EXCLUDED.metadata->>'actor_id'
    RETURNING session_id
),
session_guard AS (
    SELECT (SELECT session_id FROM session_row) AS session_id
)
INSERT INTO pellier.messages (session_id, role, content, metadata)
SELECT
    session_guard.session_id,
    turn.role,
    turn.content,
    jsonb_build_object('source', 'boutique')
FROM session_guard
CROSS JOIN (
    VALUES
        ('user', %s::text, 1),
        ('assistant', %s::text, 2)
) AS turn(role, content, ordinal)
ORDER BY turn.ordinal;
"""


def session_actor_id(user: Dict[str, Any] | None, session_token: str | None) -> str:
    """Return the durable owner key for authenticated or anonymous sessions."""
    if user and user.get("sub"):
        return str(user["sub"])
    token = (session_token or "").strip()
    if len(token) < 32 or len(token) > 256:
        raise ValueError("A valid session ownership token is required")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"anonymous:{digest}"


class AuroraSessionMemory:
    """Persist and retrieve a bounded chat history in Aurora PostgreSQL."""

    def __init__(self, db_service: Any) -> None:
        self._db = db_service

    async def load_history(
        self,
        session_id: str,
        *,
        actor_id: str,
        limit: int = 16,
    ) -> List[Dict[str, str]]:
        """Return the most recent user and assistant messages chronologically."""
        if not session_id:
            return []
        bounded_limit = max(1, min(int(limit), 100))
        rows = await self._db.fetch_all(
            _LOAD_HISTORY_SQL,
            session_id,
            actor_id,
            bounded_limit,
        )
        return [
            {
                "role": str(row["role"]),
                "content": str(row["content"]),
            }
            for row in rows
            if row.get("role") in {"user", "assistant"}
            and row.get("content") is not None
        ]

    async def append_turn_pair(
        self,
        session_id: str,
        *,
        user_message: str,
        assistant_message: str,
        actor_id: str,
        agent_name: str,
    ) -> None:
        """Atomically upsert the session and append one completed turn pair."""
        if not session_id:
            raise ValueError("session_id is required")
        if not assistant_message.strip():
            raise ValueError("assistant_message is required")
        await self._db.execute_query(
            _APPEND_TURN_SQL,
            session_id,
            agent_name,
            actor_id,
            user_message,
            assistant_message,
        )
