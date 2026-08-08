"""The per-turn identifier contract on ``POST /api/chat/stream``.

A receipt deep link is only worth shipping if it resolves to the same turn
after a reload. That needs a server-minted id, emitted before any content
and repeated on the terminal event, so the client can capture it even if
the stream fails mid-answer.

The properties pinned here:

  1. ``turn_start`` is the first event and carries ``turn_id``.
  2. The terminal ``complete`` event repeats the same id.
  3. Ids are unique per turn and never positional.
  4. Smoke mode emits identity too — it is the mode that runs on stage.
"""

from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator, Dict, List

import pytest
from fastapi.testclient import TestClient

import app as app_module

_TURN_ID_RE = re.compile(r"^turn-[0-9a-f]{32}$")


def _events(body: str) -> List[Dict[str, Any]]:
    return [json.loads(m) for m in re.findall(r"^data: (.*)$", body, re.M)]


def _first(events: List[Dict[str, Any]], kind: str) -> Dict[str, Any] | None:
    return next((e for e in events if e.get("type") == kind), None)


@pytest.fixture
def live_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client on the non-smoke path with a stubbed chat service."""

    async def _stream(**kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        yield {"type": "content", "content": "hello"}
        yield {
            "type": "complete",
            "response": {"response": "hello", "products": [], "suggestions": []},
        }

    class _Svc:
        chat_stream = staticmethod(_stream)

    monkeypatch.setattr(app_module, "chat_service", _Svc())
    monkeypatch.setattr(app_module.settings, "PELLIER_SMOKE_MODE", False, raising=False)
    return TestClient(app_module.app)


@pytest.fixture
def smoke_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(app_module.settings, "PELLIER_SMOKE_MODE", True, raising=False)
    return TestClient(app_module.app)


def _post(client: TestClient, session_id: str = "sess-1") -> List[Dict[str, Any]]:
    response = client.post(
        "/api/chat/stream",
        json={"message": "linen", "conversation_history": [], "session_id": session_id},
    )
    assert response.status_code == 200
    return _events(response.text)


# ---------------------------------------------------------------------------
# Minting
# ---------------------------------------------------------------------------
def test_new_turn_id_is_prefixed_uuid4_hex() -> None:
    value = app_module.new_turn_id()

    assert _TURN_ID_RE.match(value), value


def test_turn_ids_are_unique() -> None:
    ids = {app_module.new_turn_id() for _ in range(200)}

    assert len(ids) == 200


def test_turn_id_is_not_positional() -> None:
    """A positional id would point at the wrong turn after any reordering."""
    value = app_module.new_turn_id()

    assert value not in {"turn-0", "turn-1", "0", "1"}


# ---------------------------------------------------------------------------
# Live stream
# ---------------------------------------------------------------------------
def test_turn_start_is_the_first_event(live_client: TestClient) -> None:
    events = _post(live_client)

    assert events[0]["type"] == "turn_start"
    assert _TURN_ID_RE.match(events[0]["turn_id"])
    assert events[0]["session_id"] == "sess-1"


def test_complete_repeats_the_same_turn_id(live_client: TestClient) -> None:
    events = _post(live_client)

    start = _first(events, "turn_start")
    complete = _first(events, "complete")

    assert start is not None and complete is not None
    assert complete["response"]["turn_id"] == start["turn_id"]
    assert complete["response"]["session_id"] == "sess-1"


def test_each_request_gets_a_distinct_turn_id(live_client: TestClient) -> None:
    first = _first(_post(live_client), "turn_start")
    second = _first(_post(live_client), "turn_start")

    assert first is not None and second is not None
    assert first["turn_id"] != second["turn_id"]


def test_complete_still_carries_the_rail(live_client: TestClient) -> None:
    """Turn identity must not displace the rail annotation."""
    complete = _first(_post(live_client), "complete")

    assert complete is not None
    assert complete["response"]["rail"] == "in-process"
    assert complete["response"]["railDecision"]["available"] is True


# ---------------------------------------------------------------------------
# Smoke mode — the mode that runs on stage
# ---------------------------------------------------------------------------
def test_smoke_mode_emits_turn_identity(smoke_client: TestClient) -> None:
    events = _post(smoke_client, session_id="sess-smoke")

    start = _first(events, "turn_start")
    complete = _first(events, "complete")

    assert start is not None, "smoke mode must mint a turn id too"
    assert _TURN_ID_RE.match(start["turn_id"])
    assert complete is not None
    assert complete["response"]["turn_id"] == start["turn_id"]


def test_smoke_mode_turn_start_precedes_content(smoke_client: TestClient) -> None:
    events = _post(smoke_client, session_id="sess-smoke")
    types = [e["type"] for e in events]

    assert types[0] == "turn_start"
    assert "content_delta" in types
    assert types.index("turn_start") < types.index("content_delta")
