"""The release blocker: a governed deployment must not silently lose its write rail.

Found live on 2026-08-27. `WORKSHOP_FORMAT` was absent from a backend `.env`, `Settings`
defaulted it to `builders`, `requires_managed_rail()` returned False, and a real shopper
turn executed `initiate_return` in process — no human review, no AgentCore Policy
verdict, no `tool_audit` receipt. Readiness said nothing, because it read the flag to
GRADE the other governed checks and never checked the flag itself.

The deployment shape is detectable without the flag: a governed box has a Gateway and a
policy engine configured. Those two facts together are what make an unset format a
misconfiguration rather than a supported local mode.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict

import pytest


async def _managed_rail_check() -> Dict[str, Any]:
    from routes import observatory

    out = await observatory._collect_readiness()
    return next(c for c in out["checks"] if c["id"] == "managed_rail")


def _configure(monkeypatch: pytest.MonkeyPatch, *, fmt: str,
               gateway: str, engine: str) -> None:
    from config import settings
    from services import execution_rail

    monkeypatch.setattr(settings, "WORKSHOP_FORMAT", fmt, raising=False)
    monkeypatch.setattr(settings, "AGENTCORE_GATEWAY_ARN", gateway, raising=False)
    monkeypatch.setattr(settings, "AGENTCORE_POLICY_ENGINE_ID", engine, raising=False)
    importlib.reload(execution_rail)


@pytest.fixture(autouse=True)
def _restore_rail():
    yield
    from services import execution_rail

    importlib.reload(execution_rail)


@pytest.mark.asyncio
async def test_a_governed_deployment_with_the_rail_on_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch, fmt="governed", gateway="arn:gw", engine="engine-1")
    check = await _managed_rail_check()
    assert check["state"] == "pass"
    assert check["required"] is True
    assert "managed-rail only" in check["detail"]


@pytest.mark.asyncio
async def test_a_governed_shaped_deployment_without_the_flag_FAILS(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact live misconfiguration. Readiness must refuse, not warn."""
    _configure(monkeypatch, fmt="builders", gateway="arn:gw", engine="engine-1")
    check = await _managed_rail_check()
    assert check["state"] == "fail", (
        "a Gateway-and-policy-engine deployment running in-process writes reported "
        "anything other than fail"
    )
    assert check["required"] is True
    assert "no human review" in check["detail"]
    assert "no tool_audit receipt" in check["detail"]
    assert "Set WORKSHOP_FORMAT=governed" in check["detail"]


@pytest.mark.asyncio
async def test_an_unset_format_on_a_governed_box_also_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch, fmt="", gateway="arn:gw", engine="engine-1")
    check = await _managed_rail_check()
    assert check["state"] == "fail"


@pytest.mark.asyncio
async def test_a_genuine_local_lineage_only_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In-process writes ARE the supported behaviour without a governed rail."""
    _configure(monkeypatch, fmt="builders", gateway="", engine="")
    check = await _managed_rail_check()
    assert check["state"] == "warn"
    assert check["required"] is False
    assert "supported behaviour for this lineage" in check["detail"]


@pytest.mark.asyncio
async def test_the_check_reports_the_effective_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An operator must be able to read the mode off the surface, not infer it."""
    _configure(monkeypatch, fmt="governed", gateway="arn:gw", engine="engine-1")
    check = await _managed_rail_check()
    assert "WORKSHOP_FORMAT=governed" in check["detail"]


def test_the_governed_rail_covers_every_mutation_tool() -> None:
    from services.execution_rail import mutation_tools, requires_managed_rail
    from config import settings

    original = settings.WORKSHOP_FORMAT
    try:
        settings.WORKSHOP_FORMAT = "governed"
        import importlib

        from services import execution_rail

        importlib.reload(execution_rail)
        for tool in execution_rail.mutation_tools():
            assert execution_rail.requires_managed_rail(tool) is True, tool
    finally:
        settings.WORKSHOP_FORMAT = original
        import importlib

        from services import execution_rail

        importlib.reload(execution_rail)


def test_readiness_grades_governed_checks_off_the_same_flag() -> None:
    """The flag decides fail-vs-warn elsewhere, which is why it must be checked."""
    import pathlib

    source = pathlib.Path("routes/observatory.py").read_text()
    assert 'return "fail" if governed_format else "warn"' in source
    assert 'check_id="managed_rail"' in source
    # And the new check is appended before the other governed checks consume the flag.
    assert source.index('check_id="managed_rail"') < source.index('check_id="gateway"')
