"""Runtime control-plane status must not be confused with a managed invocation."""

from __future__ import annotations

import asyncio


class _RuntimeClient:
    def __init__(self) -> None:
        self.runtime_ids: list[str] = []

    def get_agent_runtime(self, *, agentRuntimeId: str) -> dict[str, str]:
        self.runtime_ids.append(agentRuntimeId)
        return {
            "agentRuntimeId": agentRuntimeId,
            "agentRuntimeVersion": "2",
            "status": "READY",
        }


def test_runtime_status_reports_control_plane_state_without_claiming_execution(
    monkeypatch,
) -> None:
    import app as app_module
    import boto3

    client = _RuntimeClient()
    monkeypatch.setattr(
        app_module.settings,
        "AGENTCORE_RUNTIME_ENDPOINT",
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/pellier-test",
    )
    monkeypatch.setattr(app_module.settings, "USE_AGENTCORE_RUNTIME", False)
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: client)

    response = asyncio.run(app_module.agentcore_runtime_status())

    assert client.runtime_ids == ["pellier-test"]
    assert response == {
        "configured": True,
        "source": "agentcore-control-plane",
        "runtime_id": "pellier-test",
        "runtime_version": "2",
        "resource_status": "READY",
        "ready": True,
        "managed_rail_requested": False,
        "storefront_rail": "in-process",
        "fallback_reason": None,
    }
