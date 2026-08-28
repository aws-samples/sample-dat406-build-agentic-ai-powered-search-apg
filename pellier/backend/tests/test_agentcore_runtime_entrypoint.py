"""Executable contract tests for the managed AgentCore Runtime entrypoint."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

import services.agentcore_gateway as gateway_module
from services.conversation_context import build_conversation_prompt


ENTRYPOINT = Path(__file__).resolve().parents[1] / "agentcore_runtime.py"


class _RuntimeApp:
    def __init__(self) -> None:
        self.handler = None

    def entrypoint(self, handler):
        self.handler = handler
        return handler


class _Context:
    request_headers = {"Authorization": "Bearer verified-jwt"}


class _Response:
    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.text = text
        self.stop_reason = stop_reason

    def __str__(self) -> str:
        return self.text


class _Dispatcher:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[str] = []
        self.trace_attributes: dict[str, str] = {}
        self.last_products = [
            {
                "productId": 7,
                "name": "Italian Linen Camp Shirt",
                "price": 228,
            }
        ]
        self.last_tool_events = [
            {
                "id": "tool-1",
                "tool": "search_products_hybrid",
                "status": "success",
            }
        ]
        self.last_intent = "recommendation"
        self.last_specialist = "recommendation"
        self.response_mode = "balanced"
        self.last_model_id = "global.anthropic.claude-opus-4-6-v1"
        self.last_tool_names = ["search_products_hybrid"]

    def __call__(self, prompt: str) -> _Response:
        self.calls.append(prompt)
        return self.response


def _load_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: _Response,
) -> tuple[Any, _Dispatcher, list[dict[str, Any]]]:
    runtime_sdk = types.ModuleType("bedrock_agentcore.runtime")
    runtime_sdk.BedrockAgentCoreApp = _RuntimeApp
    runtime_sdk.BedrockAgentCoreContext = type(
        "_BedrockAgentCoreContext",
        (),
        {"get_request_headers": staticmethod(lambda: {})},
    )
    package = types.ModuleType("bedrock_agentcore")
    package.runtime = runtime_sdk
    monkeypatch.setitem(sys.modules, "bedrock_agentcore", package)
    monkeypatch.setitem(sys.modules, "bedrock_agentcore.runtime", runtime_sdk)
    monkeypatch.setenv(
        "AGENTCORE_GATEWAY_URL",
        "https://gateway.example.test/mcp",
    )

    dispatcher = _Dispatcher(response)
    factory_calls: list[dict[str, Any]] = []

    def _factory(**kwargs: Any) -> _Dispatcher:
        factory_calls.append(kwargs)
        return dispatcher

    monkeypatch.setattr(gateway_module, "create_gateway_dispatcher", _factory)

    spec = importlib.util.spec_from_file_location(
        "test_managed_agentcore_entrypoint",
        ENTRYPOINT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.app is not None
    assert module.app.handler is not None
    return module.app.handler, dispatcher, factory_calls


def test_entrypoint_runs_fixed_dispatcher_and_returns_observed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler, dispatcher, factory_calls = _load_entrypoint(
        monkeypatch,
        response=_Response("A grounded resort edit."),
    )

    result = handler(
        {
            "prompt": "Build a resort edit",
            "session_id": "session-123",
            "turn_id": "turn-123",
            "user_id": "cognito-sub-123",
            "customer_id": "CUST-MARCO",
            "response_mode": "balanced",
            "history": [{"role": "user", "content": "I prefer linen."}],
        },
        _Context(),
    )

    assert factory_calls == [
        {
            "access_token": "verified-jwt",
            "response_mode": "balanced",
            "customer_id": "CUST-MARCO",
            "routing_query": "Build a resort edit",
        }
    ]
    assert dispatcher.calls == [
        build_conversation_prompt(
            "Build a resort edit",
            [{"role": "user", "content": "I prefer linen."}],
        )
    ]
    assert dispatcher.trace_attributes == {
        "session.id": "session-123",
        "turn.id": "turn-123",
        "user.id": "cognito-sub-123",
        "runtime": "agentcore-managed",
        "workshop": "pellier",
    }
    assert result == {
        "response": "A grounded resort edit.",
        "products": dispatcher.last_products,
        "rail": "gateway-mcp",
        "intent": "recommendation",
        "specialist": "recommendation",
        "response_mode": "balanced",
        "model": "global.anthropic.claude-opus-4-6-v1",
        "gateway_tools": ["search_products_hybrid"],
        "tool_calls": dispatcher.last_tool_events,
        "orchestration": "dispatcher",
    }


def test_entrypoint_rejects_truncated_model_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler, dispatcher, _ = _load_entrypoint(
        monkeypatch,
        response=_Response("Partial answer", stop_reason="max_tokens"),
    )

    result = handler(
        {
            "prompt": "Build a resort edit",
            "session_id": "session-123",
            "user_id": "cognito-sub-123",
            "customer_id": "CUST-MARCO",
        },
        _Context(),
    )

    assert result == {
        "error": "runtime_output_truncated",
        "products": dispatcher.last_products,
        "rail": "gateway-mcp",
        "tool_calls": dispatcher.last_tool_events,
    }
