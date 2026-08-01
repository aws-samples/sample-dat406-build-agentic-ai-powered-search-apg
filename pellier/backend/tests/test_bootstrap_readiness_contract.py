"""Regression tests for workshop bootstrap readiness and model resolution."""

from __future__ import annotations

import importlib.util
import json
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
FACILITATOR_DRY_RUN = REPO / "scripts" / "dry-run-builders.sh"


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


def _run_health_gate(
    tmp_path: Path,
    model_ready: bool,
    *,
    workshop_format: str = "builders",
    managed_ready: bool = False,
    customer_count: int = 5,
    order_count: int = 20,
    audit_count: int = 1,
) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    fake_bin = tmp_path / "bin"
    repo.mkdir()
    fake_bin.mkdir()
    env_lines = [
        f"BEDROCK_MODEL_ACCESS_READY={'true' if model_ready else 'false'}",
        f"WORKSHOP_FORMAT={workshop_format}",
    ]
    if managed_ready:
        env_lines.extend(
            [
                "AGENTCORE_MEMORY_ID=memory-123",
                "AGENTCORE_RUNTIME_ENDPOINT=arn:aws:bedrock-agentcore:us-east-1:123:runtime/test",
                "USE_AGENTCORE_RUNTIME=true",
                "AGENTCORE_GATEWAY_URL=https://gateway.example.test/mcp",
                "AGENTCORE_GATEWAY_ARN=arn:aws:bedrock-agentcore:us-east-1:123:gateway/test",
                "AGENTCORE_POLICY_ENGINE_ID=policy-123",
            ]
        )
        (tmp_path / "managed.json").write_text(
            json.dumps({"status": "ready"}),
            encoding="utf-8",
        )
    (repo / ".env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    _write_executable(
        fake_bin / "curl",
        """#!/bin/bash
case "$*" in
  *api/health*) printf '{"status":"healthy"}' ;;
  *memory/status*) printf '{"live":true,"source":"agentcore-sdk","resource_status":"ACTIVE"}' ;;
  *) printf '<!doctype html><div id="root"></div>' ;;
esac
""",
    )
    _write_executable(
        fake_bin / "psql",
        f"""#!/bin/bash
case "$*" in
  *product_catalog*) printf '1000\n' ;;
  *warehouse_inventory*) printf '120\n' ;;
  *governed_receipts*) printf '1\n' ;;
  *customers*) printf '{customer_count}\n' ;;
  *orders*) printf '{order_count}\n' ;;
  *tool_audit*) printf '{audit_count}\n' ;;
esac
""",
    )
    _write_executable(fake_bin / "node", "#!/bin/bash\nprintf 'v20.20.2\\n'\n")
    _write_executable(fake_bin / "jq", "#!/bin/bash\nexit 0\n")
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PELLIER_REPO"] = str(repo)
    if managed_ready:
        env["AGENTCORE_MANAGED_OUTPUT_JSON"] = str(tmp_path / "managed.json")
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


def test_governed_health_gate_rejects_missing_agentcore_pillars(
    tmp_path: Path,
) -> None:
    proc = _run_health_gate(
        tmp_path,
        model_ready=True,
        workshop_format="governed",
    )
    assert proc.returncode == 1
    assert "AGENTCORE_MEMORY_ID empty" in proc.stdout
    assert "AGENTCORE_RUNTIME_ENDPOINT empty" in proc.stdout
    assert "AGENTCORE_GATEWAY_URL empty" in proc.stdout
    assert "AGENTCORE_POLICY_ENGINE_ID empty" in proc.stdout
    assert "NOT READY" in proc.stdout


def test_governed_health_gate_requires_complete_managed_receipt(
    tmp_path: Path,
) -> None:
    proc = _run_health_gate(
        tmp_path,
        model_ready=True,
        workshop_format="governed",
        managed_ready=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "gateway-mcp Runtime smoke" in proc.stdout
    assert "READY" in proc.stdout


@pytest.mark.parametrize(
    ("missing_data", "message"),
    [
        ({"customer_count": 0}, "Customer records empty or missing"),
        ({"order_count": 0}, "Orders empty or missing"),
        (
            {"audit_count": 0},
            "JSONB tool execution ledger has no completed agent or Gateway actions",
        ),
    ],
)
def test_governed_health_gate_rejects_missing_operational_data(
    tmp_path: Path,
    missing_data: dict[str, int],
    message: str,
) -> None:
    proc = _run_health_gate(
        tmp_path,
        model_ready=True,
        workshop_format="governed",
        managed_ready=True,
        **missing_data,
    )
    assert proc.returncode == 1
    assert message in proc.stdout
    assert "NOT READY" in proc.stdout


def test_runtime_arn_is_recorded_before_smoke() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")
    record = source.index('result["runtime"] = {')
    smoke = source.index("smoke = _authenticated_runtime_smoke(")
    assert record < smoke
    assert '"BEDROCK_ROUTER_MODEL": model_id' in source
    assert 'os.environ.get("AGENT_MODEL_ID", "global.' not in source


def _load_provisioner():
    spec = importlib.util.spec_from_file_location("pellier_provisioner", PROVISIONER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("rail", "should_pass"),
    [
        ("gateway-mcp", True),
        ("in-process", False),
        ("", False),
    ],
)
def test_runtime_smoke_requires_gateway_mcp_rail(
    monkeypatch: pytest.MonkeyPatch,
    rail: str,
    should_pass: bool,
) -> None:
    module = _load_provisioner()

    class Secrets:
        def get_secret_value(self, *, SecretId):
            if "client" in SecretId:
                return {"SecretString": json.dumps({"client_secret": "secret"})}
            return {
                "SecretString": json.dumps(
                    {"users": [{"username": "Marco", "password": "Password1"}]}
                )
            }

    class Cognito:
        def admin_initiate_auth(self, **_kwargs):
            return {"AuthenticationResult": {"AccessToken": "jwt-token"}}

    def fake_client(service, **_kwargs):
        return Secrets() if service == "secretsmanager" else Cognito()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {"response": "runtime response", "rail": rail}
            ).encode()

    monkeypatch.setattr(module.boto3, "client", fake_client)
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *_a, **_k: Response())

    invoke = lambda: module._authenticated_runtime_smoke(
        region="us-east-1",
        runtime_arn=(
            "arn:aws:bedrock-agentcore:us-east-1:123456789012:"
            "runtime/pellier"
        ),
        user_pool_id="us-east-1_pool",
        client_id="client-id",
        creds_secret_arn="test-users",
        client_secret_arn="client-secret",
    )
    if should_pass:
        assert invoke()["rail"] == "gateway-mcp"
    else:
        with pytest.raises(RuntimeError, match="gateway-mcp"):
            invoke()


def test_policy_attachment_is_a_provisioning_hard_gate() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")
    assert "Managed AgentCore Policy is required but failed to attach" in source
    assert 'result["verification"]["managed_policy_attached"] = False' in source
    assert 'result["status"] = "ready"' in source
    assert source.index(
        "Managed AgentCore Policy is required but failed to attach"
    ) < source.index('result["status"] = "ready"')


def test_facilitator_dry_run_requires_managed_rail_and_current_policy_receipts() -> None:
    source = FACILITATOR_DRY_RUN.read_text(encoding="utf-8")
    assert '-H "Authorization: Bearer ${POLICY_TOKEN}"' in source
    assert 'runtime_rail" == "gateway-mcp"' in source
    assert "gateway_process_return.py" in source
    assert "--expect allow --record-receipt" in source
    assert "--expect deny --record-receipt" in source
    assert "POLICY_ALLOW_SESSION" in source
    assert "POLICY_DENY_SESSION" in source
    assert "absence_verified" in source


def test_preference_seed_uses_access_token() -> None:
    source = SEED_PREFERENCES.read_text(encoding="utf-8")
    assert "AuthenticationResult.AccessToken" in source
    assert "AuthenticationResult.IdToken" not in source
