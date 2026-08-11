"""Static tests for Pellier's AgentCore CLI 0.26 project contract."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "pellier" / "backend"
DEPLOY_DIR = REPO_ROOT / "scripts" / "deploy"
DEPLOY_SCRIPT = DEPLOY_DIR / "deploy_all.sh"
PROVISIONER_PATH = REPO_ROOT / "scripts" / "provision_agentcore_end_to_end.py"
RENDERER_PATH = DEPLOY_DIR / "render_agentcore_project.py"
ENTRYPOINT = BACKEND_DIR / "agentcore_runtime.py"
RUNTIME_SERVICE = BACKEND_DIR / "services" / "agentcore_runtime.py"
RUNTIME_SOLUTION = (
    REPO_ROOT / "solutions" / "the-ledger" / "services" / "agentcore_runtime.py"
)
PYPROJECT = BACKEND_DIR / "pyproject.toml"

if str(DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(DEPLOY_DIR))

import render_agentcore_project as renderer  # noqa: E402


def _load_provisioner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pellier_agentcore_provisioner", PROVISIONER_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lambda_arns() -> dict[str, str]:
    return {
        surface: f"arn:aws:lambda:us-east-1:123456789012:function:pellier-{surface}"
        for surface in renderer.TOOL_SCHEMAS
    }


def _render(tmp_path: Path, *, include_policies: bool) -> tuple[Path, dict[str, Any]]:
    repo = tmp_path / "repo"
    (repo / "pellier" / "backend").mkdir(parents=True)
    root = renderer.render_project(
        repo=repo,
        account_id="123456789012",
        region="us-east-1",
        cognito_pool="us-east-1_example",
        cognito_client="client-id",
        lambda_arns=_lambda_arns(),
        model_id="global.anthropic.claude-sonnet-5",
        workshop_id="p12345678",
        include_policies=include_policies,
    )
    config = json.loads((root / "agentcore" / "agentcore.json").read_text())
    return root, config


def test_agentcore_cli_is_pinned_once() -> None:
    assert renderer.AGENTCORE_CLI == "@aws/agentcore@0.26.0"
    source = PROVISIONER_PATH.read_text()
    assert "AGENTCORE_CLI" in source
    assert "@aws/agentcore@latest" not in source


def test_renderer_emits_valid_cdk_managed_project_shape(tmp_path: Path) -> None:
    root, project = _render(tmp_path, include_policies=False)

    assert project["managedBy"] == "CDK"
    assert project["name"] == "pellier"
    assert project["version"] == 1
    assert project["credentials"] == []
    assert project["payments"] == []
    assert json.loads((root / "agentcore" / "aws-targets.json").read_text()) == [
        {
            "name": "default",
            "account": "123456789012",
            "region": "us-east-1",
        }
    ]


def test_runtime_uses_cli_managed_role_and_resource_discovery(tmp_path: Path) -> None:
    _, project = _render(tmp_path, include_policies=False)
    runtime = project["runtimes"][0]

    assert runtime["name"] == renderer.RUNTIME_NAME
    assert runtime["build"] == "CodeZip"
    assert runtime["entrypoint"] == "agentcore_runtime.py"
    assert runtime["runtimeVersion"] == "PYTHON_3_12"
    assert runtime["protocol"] == "HTTP"
    assert runtime["requestHeaderAllowlist"] == ["Authorization"]
    assert runtime["authorizerType"] == "CUSTOM_JWT"
    assert "executionRoleArn" not in runtime

    env = {item["name"]: item["value"] for item in runtime["envVars"]}
    assert env == {
        "AGENT_MODEL_ID": "global.anthropic.claude-sonnet-5",
        "BEDROCK_ROUTER_MODEL": "global.anthropic.claude-sonnet-5",
    }
    assert "AGENTCORE_GATEWAY_URL" not in env
    assert "AGENTCORE_MEMORY_ID" not in env


def test_runtime_bridges_cli_injected_discovery_names() -> None:
    source = ENTRYPOINT.read_text()
    assert "AGENTCORE_GATEWAY_PELLIER_GATEWAY_URL" in source
    assert "MEMORY_PELLIERMEMORY_ID" in source
    assert 'os.environ["AGENTCORE_GATEWAY_URL"]' in source
    assert 'os.environ["AGENTCORE_MEMORY_ID"]' in source
    assert "MCP_GATEWAY_URL" in source  # compatibility fallback only


def test_memory_gateway_targets_and_policy_engine_share_one_project(
    tmp_path: Path,
) -> None:
    root, project = _render(tmp_path, include_policies=False)

    memory = project["memories"][0]
    assert memory["name"] == renderer.MEMORY_NAME
    assert memory["strategies"][0]["type"] == "USER_PREFERENCE"

    gateway = project["agentCoreGateways"][0]
    assert gateway["name"] == renderer.GATEWAY_NAME
    assert gateway["protocolType"] == "MCP"
    assert gateway["policyEngineConfiguration"] == {
        "policyEngineName": renderer.POLICY_ENGINE_NAME,
        "mode": "ENFORCE",
    }
    assert len(gateway["targets"]) == 4
    assert {target["targetType"] for target in gateway["targets"]} == {
        "lambdaFunctionArn"
    }
    assert {
        target["lambdaFunctionArn"]["lambdaArn"] for target in gateway["targets"]
    } == set(_lambda_arns().values())

    schemas = sorted((root / "tool-schemas").glob("*.json"))
    assert len(schemas) == 4
    assert sum(len(json.loads(path.read_text())) for path in schemas) == 15

    engine = project["policyEngines"][0]
    assert engine["name"] == renderer.POLICY_ENGINE_NAME
    assert engine["policies"] == []


def test_second_phase_adds_only_the_baseline_cedar_set(tmp_path: Path) -> None:
    _, project = _render(tmp_path, include_policies=True)
    policies = project["policyEngines"][0]["policies"]

    assert {policy["name"] for policy in policies} == {
        "baseline_permit_gateway_tools",
        "process_return_damaged_only",
        "process_return_allow_damaged",
    }
    assert all(policy["enforcementMode"] == "ACTIVE" for policy in policies)
    assert all(
        policy["validationMode"] == "IGNORE_ALL_FINDINGS" for policy in policies
    )
    statements = "\n".join(policy["statement"] for policy in policies)
    assert renderer.PROCESS_RETURN_ACTION in statements
    assert "resource is AgentCore::Gateway" in statements


def test_deployed_state_reads_mcp_gateway_shape() -> None:
    provisioner = _load_provisioner()
    state = {
        "targets": {
            "default": {
                "resources": {
                    "mcp": {
                        "gateways": {
                            renderer.GATEWAY_NAME: {
                                "gatewayId": "gateway-1",
                                "gatewayArn": "arn:aws:bedrock-agentcore:us-east-1:123:gateway/gateway-1",
                                "gatewayUrl": "https://gateway.example/mcp",
                            }
                        }
                    }
                }
            }
        }
    }

    gateway = provisioner._require_gateway_state(state, renderer.GATEWAY_NAME)
    assert gateway["gatewayId"] == "gateway-1"


def test_deployed_state_rejects_obsolete_flat_gateway_shape() -> None:
    provisioner = _load_provisioner()
    state = {
        "targets": {
            "default": {
                "resources": {
                    "gateways": {renderer.GATEWAY_NAME: {"gatewayId": "wrong"}}
                }
            }
        }
    }

    with pytest.raises(RuntimeError, match=r"mcp\.gateways\.pellier-gateway"):
        provisioner._require_gateway_state(state, renderer.GATEWAY_NAME)


def test_deploy_sequence_validates_both_cli_phases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provisioner = _load_provisioner()
    root = tmp_path / "project"
    calls: list[tuple[str, ...]] = []
    render_phases: list[bool] = []
    state = {
        "targets": {
            "default": {
                "resources": {
                    "mcp": {
                        "gateways": {
                            renderer.GATEWAY_NAME: {
                                "gatewayId": "gateway-1",
                                "gatewayArn": "arn:gateway",
                            }
                        }
                    },
                    "policyEngines": {
                        renderer.POLICY_ENGINE_NAME: {
                            "policyEngineId": "engine-1",
                            "policyEngineArn": "arn:engine",
                        }
                    },
                }
            }
        }
    }

    monkeypatch.setattr(
        provisioner, "_scaffold_cli_project", lambda **_: root
    )
    monkeypatch.setattr(
        provisioner,
        "render_project",
        lambda **kwargs: render_phases.append(kwargs["include_policies"]),
    )
    monkeypatch.setattr(
        provisioner,
        "_agentcore",
        lambda _root, *args, **_: calls.append(args),
    )
    monkeypatch.setattr(provisioner, "_read_deployed_state", lambda _root: state)

    returned_root, returned_state = provisioner._deploy_cli_project(
        repo=tmp_path,
        account_id="123456789012",
        region="us-east-1",
        cognito_pool="pool",
        cognito_client="client",
        lambda_arns=_lambda_arns(),
        model_id="model",
        workshop_id="workshop",
        env={},
    )

    assert returned_root == root
    assert returned_state is state
    assert render_phases == [False, True]
    assert calls == [
        ("validate",),
        ("deploy", "--yes", "--json"),
        ("validate",),
        ("deploy", "--yes", "--json"),
    ]


def test_pyproject_carries_runtime_imports() -> None:
    deps = PYPROJECT.read_text()
    for package in ("strands-agents", "bedrock-agentcore", "pydantic-settings", "boto3"):
        assert package in deps


def test_entrypoint_is_fail_closed_byo_app() -> None:
    text = ENTRYPOINT.read_text()
    assert "BedrockAgentCoreApp" in text
    assert "@app.entrypoint" in text
    assert '"error": "authentication_required"' in text
    assert '"error": "managed_gateway_unavailable"' in text
    assert "create_gateway_dispatcher" in text
    assert "from agents.orchestrator import create_orchestrator" not in text
    for field in ('"intent"', '"specialist"', '"gateway_tools"'):
        assert field in text


def test_runtime_smoke_uses_pinned_agentcore_cli() -> None:
    provisioner = PROVISIONER_PATH.read_text()
    assert '"invoke"' in provisioner
    assert '"--runtime"' in provisioner
    assert '"--bearer-token"' in provisioner
    assert '"--session-id"' in provisioner
    assert "urllib.request" not in provisioner


def test_bootstrap_runtime_solution_matches_fail_closed_service() -> None:
    assert RUNTIME_SOLUTION.read_text() == RUNTIME_SERVICE.read_text()


def test_obsolete_flat_templates_and_runtime_provisioner_are_removed() -> None:
    for stale in (
        BACKEND_DIR / "agentcore.json.template",
        BACKEND_DIR / "aws-targets.json.template",
        REPO_ROOT / "scripts" / "provision_agentcore_runtime.py",
    ):
        assert not stale.exists()


def test_deploy_all_is_only_a_canonical_provisioner_wrapper() -> None:
    source = DEPLOY_SCRIPT.read_text()
    assert "provision_agentcore_end_to_end.py" in source
    assert "deploy_gateway.py" not in source
    assert "deploy_policy.py" not in source
    assert "bedrock-agentcore-control create" not in source
