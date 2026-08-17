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
AGENTCORE_RENDERER = REPO / "scripts" / "deploy" / "render_agentcore_project.py"
BOOTSTRAP = REPO / "scripts" / "bootstrap-labs.sh"
RESET_GOVERNED = REPO / "scripts" / "reset-governed-workshop.sh"
CATALOG_SEED = REPO / "scripts" / "seed_boutique_catalog.py"
WAREHOUSE_MIGRATION = REPO / "scripts" / "migrations" / "006_warehouse_inventory.sql"
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
    assert "CLAUDE_CODE_MODEL" not in values
    assert values["AGENT_MODEL_ID"] == "global.anthropic.claude-sonnet-4-6"
    assert values["BEDROCK_MODEL_ACCESS_READY"] == "true"


def test_claude_code_uses_latest_sonnet_alias() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "export CLAUDE_CODE_USE_BEDROCK=1" in source
    assert "export ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-sonnet}" in source
    assert "CLAUDE_CODE_MODEL" not in source


def test_facilitator_dry_run_covers_both_lab1_build_sites() -> None:
    source = FACILITATOR_DRY_RUN.read_text(encoding="utf-8")
    assert "agents/stock_keeper.py" in source
    assert "agents/stock_keeper_solution.py" in source
    assert "services/agent_tools.py" in source
    assert "agent_tools_floor_check_solution.py" in source
    assert '"Stock Keeper"[[:space:]]*:[[:space:]]*"shipped"' in source
    assert '"floor_check"[[:space:]]*:[[:space:]]*"shipped"' in source


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _valid_managed_receipt() -> dict[str, object]:
    canonical_names = [f"tool_{index}" for index in range(15)]
    return {
        "status": "ready",
        "cli": {"package": "@aws/agentcore@0.26.0"},
        "runtime": {"runtime_arn": "arn:aws:bedrock-agentcore:runtime/test"},
        "memory": {
            "memory_id": "memory-123",
            "seed": {"status": "ready"},
        },
        "gateway": {
            "gateway_id": "gateway-123",
            "gateway_arn": "arn:aws:bedrock-agentcore:gateway/test",
            "gateway_url": "https://gateway.example.test/mcp",
        },
        "policy": {
            "policy_engine_id": "policy-123",
            "mode": "ENFORCE",
        },
        "observability": {
            "transaction_search": {
                "destination": "CloudWatchLogs",
                "status": "ACTIVE",
                "resource_policy": "TransactionSearchXRayAccess",
                "resource_policy_document": (
                    '{"Version":"2012-10-17","Statement":'
                    '[{"Sid":"TransactionSearchXRayAccess"}]}'
                ),
                "cleanup": {
                    "destination_changed": True,
                    "previous_destination": "XRay",
                    "resource_policy_created": True,
                    "previous_resource_policy_document": None,
                },
            },
            "control_plane_audit": {
                "source": "CloudTrail Event History",
                "event_source": "bedrock-agentcore.amazonaws.com",
                "event_name": "CreateAgentRuntime",
                "event_time": "2026-08-13T12:00:00Z",
                "resource_type": "runtime",
            },
            "runtime_log_group": {
                "name": "/aws/bedrock-agentcore/runtimes/pellier_orchestrator-abc123-DEFAULT",
                "kms_key_arn": (
                    "arn:aws:kms:us-east-1:123456789012:"
                    "key/12345678-1234-1234-1234-1234567890ab"
                ),
                "retention_days": 30,
                "cleanup": {
                    "created_by_workshop": True,
                    "previous_kms_key_arn": None,
                    "previous_retention_days": None,
                },
            },
            "trace_log_groups": {
                "groups": [
                    {
                        "name": "aws/spans",
                        "kms_key_arn": (
                            "arn:aws:kms:us-east-1:123456789012:"
                            "key/12345678-1234-1234-1234-1234567890ab"
                        ),
                        "retention_days": 30,
                        "cleanup": {
                            "created_by_workshop": True,
                            "previous_kms_key_arn": None,
                            "previous_retention_days": None,
                        },
                    },
                    {
                        "name": "/aws/application-signals/data",
                        "kms_key_arn": (
                            "arn:aws:kms:us-east-1:123456789012:"
                            "key/12345678-1234-1234-1234-1234567890ab"
                        ),
                        "retention_days": 30,
                        "cleanup": {
                            "created_by_workshop": True,
                            "previous_kms_key_arn": None,
                            "previous_retention_days": None,
                        },
                    },
                ],
                "kms_key_arn": (
                    "arn:aws:kms:us-east-1:123456789012:"
                    "key/12345678-1234-1234-1234-1234567890ab"
                ),
                "retention_days": 30,
            },
            "unified_trace": {
                "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
                "session_id": "builders-smoke-session-0000000000000001",
                "runtime_arn": "arn:aws:bedrock-agentcore:runtime/test",
                "runtime_log_group": (
                    "/aws/bedrock-agentcore/runtimes/"
                    "pellier_orchestrator-abc123-DEFAULT"
                ),
                "span_count": 3,
                "span_names": [
                    "chat",
                    "execute_tool find_pieces_hybrid",
                    "invoke_agent pellier_orchestrator",
                ],
                "agent_span": True,
                "model_span": True,
                "tool_span": True,
                "agent_input_observed": True,
                "agent_output_observed": True,
                "tool_input_output_observed": True,
                "tool_input_output_structured": True,
                "tool_input_output_sanitized": True,
                "attribute_contract": {
                    "agent_input": "gen_ai.input.messages",
                    "agent_output": "gen_ai.output.messages",
                    "tool_input": "gen_ai.tool.call.arguments",
                    "tool_output": "gen_ai.tool.call.result",
                },
                "step_latency_observed": True,
                "step_latency_ms": {"agent": 125, "model": 80, "tool": 30},
                "model_ids": ["global.anthropic.claude-sonnet-5"],
                "tool_names": ["find_pieces_hybrid"],
                "provenance": "agentcore-unified-telemetry",
            },
        },
        "verification": {
            "local_tool_schema": {
                "count": 15,
                "canonical_names": canonical_names,
            },
            "gateway_control_plane": {
                "target_count": 4,
                "target_names": [
                    "catalog-target",
                    "experience-target",
                    "inventory-target",
                    "returns-target",
                ],
                "policy_mode": "ENFORCE",
            },
            "targets_attached": True,
            "gateway_tools_discovered": True,
            "gateway_tool_count": 15,
            "gateway_tool_names": canonical_names,
            "gateway_prefixed_tool_names": [
                f"target__{name}" for name in canonical_names
            ],
            "memory_seeded": True,
            "live_policy_allow": True,
            "live_policy_deny": True,
            "live_policy_proof": {
                "allow": {
                    "outcome": "allow",
                    "tool_audit_row_after_call": {"audit_id": 1},
                },
                "deny": {
                    "outcome": "deny",
                    "cedar_denial": True,
                    "tool_audit_row_after_call": None,
                },
            },
            "authenticated_runtime_invoke_smoke": True,
            "transaction_search_ready": True,
            "trace_log_groups_encrypted": True,
            "trace_log_groups_retention_bounded": True,
            "control_plane_audit_verified": True,
            "runtime_log_group_encrypted": True,
            "runtime_log_group_retention_bounded": True,
            "unified_trace_delivered": True,
            "unified_trace_agent_span": True,
            "unified_trace_model_span": True,
            "unified_trace_tool_span": True,
            "unified_trace_agent_input": True,
            "unified_trace_agent_output": True,
            "unified_trace_tool_io_structured": True,
            "unified_trace_tool_io_sanitized": True,
            "unified_trace_step_latency": True,
            "runtime_invoke_smoke": {
                "rail": "gateway-mcp",
                "session_id": "builders-smoke-session-0000000000000001",
                "response_preview": "A live managed response.",
            },
        },
    }


def _run_health_gate(
    tmp_path: Path,
    model_ready: bool,
    *,
    workshop_format: str = "builders",
    managed_ready: bool = False,
    customer_count: int = 5,
    order_count: int = 20,
    audit_count: int = 1,
    retrieval_receipts_exists: bool = True,
    governed_turn_receipts_exists: bool = True,
    managed_receipt: dict[str, object] | None = None,
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
            json.dumps(managed_receipt or _valid_managed_receipt()),
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
  *inventory_consistency_check*) printf '0\n' ;;
  *product_catalog*) printf '1000\n' ;;
  *warehouse_inventory*) printf '120\n' ;;
  *governed_receipts*) printf '1\n' ;;
  *customers*) printf '{customer_count}\n' ;;
  *orders*) printf '{order_count}\n' ;;
  *tool_audit*) printf '{audit_count}\n' ;;
  *"to_regclass('pellier.retrieval_receipts')"*) printf '{"pellier.retrieval_receipts" if retrieval_receipts_exists else ""}\n' ;;
  *"to_regclass('pellier.governed_turn_receipts')"*) printf '{"pellier.governed_turn_receipts" if governed_turn_receipts_exists else ""}\n' ;;
esac
""",
    )
    _write_executable(fake_bin / "node", "#!/bin/bash\nprintf 'v20.20.2\\n'\n")
    _write_executable(fake_bin / "aws", "#!/bin/bash\nprintf 'ENFORCE\\n'\n")
    env = os.environ.copy()
    for managed_key in (
        "AGENTCORE_MEMORY_ID",
        "AGENTCORE_RUNTIME_ENDPOINT",
        "USE_AGENTCORE_RUNTIME",
        "AGENTCORE_GATEWAY_URL",
        "AGENTCORE_GATEWAY_ARN",
        "AGENTCORE_POLICY_ENGINE_ID",
        "AGENTCORE_MANAGED_OUTPUT_JSON",
    ):
        env.pop(managed_key, None)
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


def test_governed_health_gate_rejects_incomplete_managed_receipt(
    tmp_path: Path,
) -> None:
    proc = _run_health_gate(
        tmp_path,
        model_ready=True,
        workshop_format="governed",
        managed_ready=True,
        managed_receipt={"status": "ready"},
    )
    assert proc.returncode == 1
    assert "cli.package" in proc.stdout
    assert "Managed provisioning receipt is incomplete or degraded" in proc.stdout
    assert "NOT READY" in proc.stdout


@pytest.mark.parametrize(
    ("missing_data", "message"),
    [
        ({"customer_count": 0}, "Customer records empty or missing"),
        ({"order_count": 19}, "Orders incomplete or missing"),
        (
            {"audit_count": 0},
            "JSONB tool execution ledger has no completed agent or Gateway actions",
        ),
        (
            {"retrieval_receipts_exists": False},
            "Retrieval receipt schema missing",
        ),
        (
            {"governed_turn_receipts_exists": False},
            "Governed turn receipt schema missing",
        ),
    ],
)
def test_governed_health_gate_rejects_missing_operational_data(
    tmp_path: Path,
    missing_data: dict[str, int | bool],
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
    renderer = AGENTCORE_RENDERER.read_text(encoding="utf-8")
    record = source.index('result["runtime"] = {')
    smoke = source.index("runtime_smoke = _authenticated_runtime_smoke(")
    assert record < smoke
    assert '{"name": "BEDROCK_ROUTER_MODEL", "value": model_id}' in renderer
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
    tmp_path: Path,
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

        def get_user(self, **_kwargs):
            return {"Username": "marco"}

    def fake_client(service, **_kwargs):
        return Secrets() if service == "secretsmanager" else Cognito()

    monkeypatch.setattr(module.boto3, "client", fake_client)

    access_token, username = module._cognito_access_token(
        region="us-east-1",
        user_pool_id="us-east-1_pool",
        client_id="client-id",
        credentials_secret_arn="test-users",
        client_secret_arn="client-secret",
    )
    assert access_token == "jwt-token"
    assert username == "marco"

    runtime_payload = {
        "response": "runtime response",
        "rail": rail,
    }
    monkeypatch.setattr(
        module,
        "_agentcore",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["agentcore", "invoke"],
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "response": json.dumps(runtime_payload),
                }
            ),
            stderr="",
        ),
    )

    invoke = lambda: module._authenticated_runtime_smoke(
        root=tmp_path,
        access_token=access_token,
        username=username,
        env={},
    )
    if should_pass:
        assert invoke()["rail"] == "gateway-mcp"
    else:
        with pytest.raises(RuntimeError, match="Gateway MCP"):
            invoke()


def test_agentcore_command_errors_redact_bearer_tokens(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_provisioner()
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="denied",
        ),
    )

    with pytest.raises(RuntimeError) as exc_info:
        module._run(
            ["agentcore", "invoke", "--bearer-token", "secret-token"],
            cwd=tmp_path,
        )

    assert "secret-token" not in str(exc_info.value)
    assert "--bearer-token <redacted>" in str(exc_info.value)


def test_policy_attachment_is_a_provisioning_hard_gate() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")
    renderer = AGENTCORE_RENDERER.read_text(encoding="utf-8")

    assert '"policyEngineConfiguration"' in renderer
    assert '"mode": "ENFORCE"' in renderer
    assert "policy_state = _require_state_resource(" in source
    assert '"policyEngines", POLICY_ENGINE_NAME' in source
    assert 'result["status"] = "ready"' in source
    assert source.index(
        "policy_state = _require_state_resource("
    ) < source.index('result["status"] = "ready"')
    assert "_live_policy_proof(" in source
    assert '"live_policy_allow"' in source
    assert '"live_policy_deny"' in source
    assert "Gateway Policy mode is" in source
    assert "_discover_live_gateway_tools(" in source
    assert '"gateway_tools_discovered"' in source
    assert '"gateway_tool_count"' in source
    assert "len(tools) != 15" in source
    assert "Gateway target mismatch" in source


def test_bootstrap_normalizes_cognito_aliases_before_managed_provisioning() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    pool_alias = (
        'export COGNITO_POOL="${COGNITO_POOL:-'
        '${COGNITO_POOL_ID:-${COGNITO_USER_POOL_ID:-}}}"'
    )
    client_alias = (
        'export COGNITO_CLIENT="${COGNITO_CLIENT:-'
        '${COGNITO_CLIENT_ID:-}}"'
    )
    provision = "python3 '$REPO_PATH/scripts/provision_agentcore_end_to_end.py'"

    assert source.index(pool_alias) < source.index(provision)
    assert source.index(client_alias) < source.index(provision)
    assert "export COGNITO_POOL='${COGNITO_POOL:-}'" in source
    assert "export COGNITO_CLIENT='${COGNITO_CLIENT:-}'" in source
    assert "export AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN=" in source
    assert "export AGENTCORE_RUNTIME_LOG_RETENTION_DAYS=" in source


def test_deploy_wrapper_requires_runtime_log_protection_inputs() -> None:
    source = (REPO / "scripts" / "deploy" / "deploy_all.sh").read_text(
        encoding="utf-8"
    )

    assert "AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN" in source
    assert "AGENTCORE_RUNTIME_LOG_RETENTION_DAYS" in source


def test_governed_reset_restores_catalog_before_exact_warehouse_matrix() -> None:
    reset = RESET_GOVERNED.read_text(encoding="utf-8")
    seeder = CATALOG_SEED.read_text(encoding="utf-8")
    warehouse = WAREHOUSE_MIGRATION.read_text(encoding="utf-8")

    catalog_reset = '"$REPO/scripts/seed_boutique_catalog.py"'
    warehouse_reset = "006_warehouse_inventory.sql"
    assert reset.index(catalog_reset) < reset.index(warehouse_reset)
    assert "quantity = EXCLUDED.quantity" in seeder
    assert "DELETE FROM pellier.warehouse_inventory;" in warehouse
    assert "IF nrows <> 120 OR invalid_products <> 0 THEN" in warehouse


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
    assert "Skipping local process_return; governed mutations require gateway-mcp" in source
    assert "JOIN pellier.tool_audit ta ON ta.audit_id = gr.audit_id" in source
    assert "gr.identity_source='cognito'" in source


def test_preference_seed_uses_access_token() -> None:
    source = SEED_PREFERENCES.read_text(encoding="utf-8")
    assert "AuthenticationResult.AccessToken" in source
    assert "AuthenticationResult.IdToken" not in source


def test_hash_locked_test_requirements_include_async_pytest_plugin() -> None:
    lock = (REPO / "pellier" / "backend" / "requirements.lock").read_text(
        encoding="utf-8"
    )
    assert "pytest-asyncio==1.4.0" in lock
