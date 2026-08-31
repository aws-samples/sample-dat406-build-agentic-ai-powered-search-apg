"""The workshop scaffold must not simulate an answer for an unbuilt specialist."""

from __future__ import annotations

import pytest

from services import agentcore_memory
from services import chat as chat_module
from services.chat import EnhancedChatService
from skills import SkillRouter
from config import settings


@pytest.mark.asyncio
async def test_inventory_stub_returns_before_skill_router_or_specialist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("exercise-state dispatcher invoked Bedrock-backed work")

    memory_setup_calls = []

    def record_memory_setup(*args, **kwargs):
        memory_setup_calls.append((args, kwargs))
        return None

    monkeypatch.setattr(SkillRouter, "route", unexpected_call)
    monkeypatch.setattr(
        chat_module,
        "_build_dispatcher_specialist",
        unexpected_call,
    )
    monkeypatch.setattr(settings, "AGENTCORE_MEMORY_ID", "memory-test")
    monkeypatch.setattr(
        agentcore_memory,
        "create_agentcore_session_manager",
        record_memory_setup,
    )

    service = EnhancedChatService(db_service=object())
    events = [
        event
        async for event in service.chat_stream(
            message=(
                "Is the Hadley shirt at the Brooklyn warehouse, "
                "and can it still ship in time?"
            ),
            pattern="dispatcher",
            turn_id="turn-00000000000000000000000000000000",
            session_id="session-00000000000000000000000000000000",
            user={"sub": "shopper-sub", "customer_id": "CUST-MARCO"},
        )
    ]

    assert memory_setup_calls == []
    assert not any(event["type"] == "skill_routing" for event in events)
    assert not any(
        event.get("source") == "Amazon Bedrock"
        for event in events
        if event["type"] == "agent_step"
    )
    step = next(event for event in events if event["type"] == "agent_step")
    assert step == {
        "type": "agent_step",
        "agent": "Inventory Agent",
        "action": "Workshop build required",
        "status": "blocked",
        "source": "Pellier build state",
    }
    error = next(event for event in events if event["type"] == "error")
    assert error["code"] == "workshop_build_required"
    assert "intentionally unbuilt" in error["error"]
    complete = next(event for event in events if event["type"] == "complete")
    assert complete["response"]["success"] is False
    assert complete["response"]["agent_execution"]["model"] is None
    assert complete["response"]["agent_execution"]["build_required"] is True
    assert events[-1]["type"] == "complete"
