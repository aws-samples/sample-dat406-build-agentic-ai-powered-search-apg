"""The workshop scaffold must not spend a Bedrock call to explain it is unbuilt."""

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
    class ProfileDB:
        def __init__(self) -> None:
            self.calls = []

        async def fetch_one(self, query, *params):
            self.calls.append((query, params))
            return {
                "customer_exists": True,
                "facts_available": 3,
                "orders_available": 7,
            }

        async def fetch_all(self, *_args, **_kwargs):
            raise AssertionError("stub path loaded full persona context")

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("exercise-state dispatcher invoked Bedrock-backed work")

    profile_db = ProfileDB()
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

    service = EnhancedChatService(db_service=profile_db)
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
    assert len(profile_db.calls) == 1
    profile_event = next(
        event for event in events if event["type"] == "aurora_profile_context"
    )
    assert profile_event["profile"] == {
        "source": "Local PostgreSQL",
        "customer_id": "CUST-MARCO",
        "facts_available": 3,
        "orders_available": 7,
        "available": True,
    }
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
        "action": "Workshop build pending",
        "status": "completed",
        "source": "Pellier build state",
    }
    complete = next(event for event in events if event["type"] == "complete")
    assert complete["response"]["success"] is True
    assert complete["response"]["agent_execution"]["model"] is None
    assert events[-1]["type"] == "complete"
