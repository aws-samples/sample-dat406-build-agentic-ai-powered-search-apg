"""Regression tests for the optional Pellier AgentCore Memory mirror."""

from __future__ import annotations

import asyncio

from services import agentcore_memory
from services.agentcore_memory import AgentCoreMemory
from services.chat import _append_boutique_stm_turn


def test_boutique_turn_does_not_claim_local_fallback_as_managed(
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentcore_memory, "_SESSION_STORE", {})
    monkeypatch.setattr(agentcore_memory.settings, "AGENTCORE_MEMORY_ID", None)

    asyncio.run(
        _append_boutique_stm_turn(
            "persona-marco-fallback",
            "Show me linen for Goa.",
            "Here are two breathable options.",
        )
    )

    history = asyncio.run(
        AgentCoreMemory().get_session_history(
            "anon-persona-marco-fallback"
        )
    )
    assert history == []
