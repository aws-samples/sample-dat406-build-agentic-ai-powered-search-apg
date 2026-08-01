"""Regression tests for workshop bootstrap readiness and model resolution."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[3]
MODEL_CHECK = REPO / "scripts" / "check_model_access.py"
HEALTH_GATE = REPO / "scripts" / "health-gate.sh"
PROVISIONER = REPO / "scripts" / "provision_agentcore_end_to_end.py"
SEED_PREFERENCES = REPO / "scripts" / "seed-sample-preferences.sh"


def _load_model_check():
    spec = importlib.util.spec_from_file_location("pellier_model_check", MODEL_CHECK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for model in module.MODELS:
        model.pop("_resolved_id", None)
    return module


def test_model_preflight_persists_sonnet_46_runtime_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_model_check()
    env_file = tmp_path / ".env"
    env_file.write_text("BEDROCK_OPUS_MODEL=stale\n", encoding="utf-8")

    def fake_check(_client, _rerank_client, model):
        if model.get("role") == "editorial":
            return False
        if model.get("role") == "sonnet":
            model["_resolved_id"] = "global.anthropic.claude-sonnet-4-6"
        return True

    monkeypatch.setattr(module, "check_model", fake_check)
    monkeypatch.setattr(module.boto3, "client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        sys, "argv", ["check_model_access.py", "--write-env", str(env_file)]
    )

    module.main()

    values = dict(
        line.split("=", 1)
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    assert values["BEDROCK_OPUS_MODEL"] == "global.anthropic.claude-sonnet-4-6"
    assert values["BEDROCK_ROUTER_MODEL"] == "global.anthropic.claude-sonnet-4-6"
    assert values["AGENT_MODEL_ID"] == "global.anthropic.claude-sonnet-4-6"
    assert values["BEDROCK_MODEL_ACCESS_READY"] == "true"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _run_health_gate(tmp_path: Path, model_ready: bool) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    fake_bin = tmp_path / "bin"
    repo.mkdir()
    fake_bin.mkdir()
    (repo / ".env").write_text(
        f"BEDROCK_MODEL_ACCESS_READY={'true' if model_ready else 'false'}\n",
        encoding="utf-8",
    )
    _write_executable(
        fake_bin / "curl",
        """#!/bin/bash
case "$*" in
  *api/health*) printf '{"status":"healthy"}' ;;
  *) printf '<!doctype html><div id="root"></div>' ;;
esac
""",
    )
    _write_executable(
        fake_bin / "psql",
        """#!/bin/bash
case "$*" in
  *product_catalog*) printf '1000\n' ;;
  *warehouse_inventory*) printf '120\n' ;;
  *governed_receipts*) printf '1\n' ;;
esac
""",
    )
    _write_executable(fake_bin / "node", "#!/bin/bash\nprintf 'v20.20.2\\n'\n")
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PELLIER_REPO"] = str(repo)
    return subprocess.run(
        ["bash", str(HEALTH_GATE)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_core_health_gate_allows_missing_optional_agentcore_pillars(
    tmp_path: Path,
) -> None:
    proc = _run_health_gate(tmp_path, model_ready=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "READY" in proc.stdout
    assert "AGENTCORE_MEMORY_ID empty" in proc.stdout
    assert "AGENTCORE_RUNTIME_ENDPOINT empty" in proc.stdout
    assert "AGENTCORE_GATEWAY_URL empty" in proc.stdout


def test_core_health_gate_requires_model_preflight(tmp_path: Path) -> None:
    proc = _run_health_gate(tmp_path, model_ready=False)
    assert proc.returncode == 1
    assert "model-access preflight did not pass" in proc.stdout


def test_runtime_arn_is_recorded_before_smoke() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")
    record = source.index('result["runtime"] = {')
    smoke = source.index("smoke = _authenticated_runtime_smoke(")
    assert record < smoke
    assert '"BEDROCK_ROUTER_MODEL": model_id' in source
    assert 'os.environ.get("AGENT_MODEL_ID", "global.' not in source


def test_preference_seed_uses_access_token() -> None:
    source = SEED_PREFERENCES.read_text(encoding="utf-8")
    assert "AuthenticationResult.AccessToken" in source
    assert "AuthenticationResult.IdToken" not in source
