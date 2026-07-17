"""Regression coverage for the locally runnable editorial chat stream."""

from __future__ import annotations

import asyncio
import json
import os

# app.py validates these settings at import time; this test never opens a DB.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "pellier_test")
os.environ.setdefault("DB_USER", "pellier_test")
os.environ.setdefault("DB_PASSWORD", "pellier_test")

import app as app_module
from models.search import ChatRequest


def _event_from_chunk(chunk: str) -> dict:
    assert chunk.startswith("data: ")
    return json.loads(chunk.removeprefix("data: ").strip())


def test_smoke_chat_stream_emits_multiple_exact_content_deltas(monkeypatch) -> None:
    monkeypatch.setattr(app_module.settings, "PELLIER_SMOKE_MODE", True)
    monkeypatch.setattr(app_module, "SMOKE_THINKING_DELAY_SECONDS", 0)
    monkeypatch.setattr(app_module, "SMOKE_CHUNK_DELAY_SECONDS", 0)

    async def collect_events() -> list[dict]:
        response = await app_module.chat_stream(
            ChatRequest(
                message="Pack Marco for ten days in Goa",
                conversation_history=[],
                session_id="smoke-stream-test",
                customer_id="CUST-MARCO",
            ),
            user={},
        )
        return [
            _event_from_chunk(chunk)
            async for chunk in response.body_iterator
        ]

    events = asyncio.run(collect_events())
    deltas = [event["delta"] for event in events if event["type"] == "content_delta"]
    complete = next(event for event in events if event["type"] == "complete")

    assert events[0]["type"] == "skill_routing"
    assert len(deltas) > 3
    assert "".join(deltas) == complete["response"]["response"]
    assert events[-1]["type"] == "complete"
