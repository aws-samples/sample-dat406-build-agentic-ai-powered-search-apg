"""Static tests for Pellier's AgentCore CLI 0.26 project contract."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
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


def _seed_runtime_sources(repo: Path) -> None:
    backend = repo / "pellier" / "backend"
    for relative in (
        Path("pyproject.toml"),
        Path("uv.lock"),
        *renderer.RUNTIME_SOURCE_FILES,
    ):
        source = BACKEND_DIR / relative
        destination = backend / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _render(tmp_path: Path, *, include_policies: bool) -> tuple[Path, dict[str, Any]]:
    repo = tmp_path / "repo"
    _seed_runtime_sources(repo)
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
    root, project = _render(tmp_path, include_policies=False)
    runtime = project["runtimes"][0]

    assert runtime["name"] == renderer.RUNTIME_NAME
    assert runtime["build"] == "CodeZip"
    assert runtime["entrypoint"] == "agentcore_runtime.py"
    assert runtime["runtimeVersion"] == "PYTHON_3_12"
    assert runtime["protocol"] == "HTTP"
    assert runtime["requestHeaderAllowlist"] == ["Authorization"]
    assert runtime["authorizerType"] == "CUSTOM_JWT"
    assert "executionRoleArn" not in runtime
    assert Path(runtime["codeLocation"]) == root / "runtime-src"

    env = {item["name"]: item["value"] for item in runtime["envVars"]}
    assert env == {
        "AGENT_MODEL_ID": "global.anthropic.claude-sonnet-5",
        "BEDROCK_ROUTER_MODEL": "global.anthropic.claude-sonnet-5",
        "UNIFIED_TRACES_DESTINATION_ENABLED": "true",
    }
    assert runtime["instrumentation"] == {"enableOtel": True}
    assert "AGENTCORE_GATEWAY_URL" not in env
    assert "AGENTCORE_MEMORY_ID" not in env


def test_runtime_bundle_contains_only_managed_import_graph(tmp_path: Path) -> None:
    root, _ = _render(tmp_path, include_policies=False)
    runtime_dir = root / "runtime-src"
    actual = {
        path.relative_to(runtime_dir)
        for path in runtime_dir.rglob("*")
        if path.is_file()
    }
    assert actual == {
        Path("pyproject.toml"),
        Path("uv.lock"),
        *renderer.RUNTIME_SOURCE_FILES,
    }
    assert Path("config.py") not in actual
    assert not any("tests" in path.parts for path in actual)


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


def test_transaction_search_setup_is_scoped_and_requires_active_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioner = _load_provisioner()

    class _Logs:
        policy_name = ""
        policy_document = ""

        def put_resource_policy(
            self, *, policyName: str, policyDocument: str
        ) -> None:
            self.policy_name = policyName
            self.policy_document = policyDocument

    class _XRay:
        updated_to = ""
        responses = iter(
            (
                {"Destination": "XRay", "Status": "ACTIVE"},
                {"Destination": "CloudWatchLogs", "Status": "ACTIVE"},
            )
        )

        def get_trace_segment_destination(self) -> dict[str, str]:
            return next(self.responses)

        def update_trace_segment_destination(self, *, Destination: str) -> None:
            self.updated_to = Destination

    logs = _Logs()
    xray = _XRay()

    def _client(service: str, **_: Any) -> Any:
        return {"logs": logs, "xray": xray}[service]

    monkeypatch.setattr(provisioner.boto3, "client", _client)
    monkeypatch.setattr(provisioner.time, "sleep", lambda _: None)

    proof = provisioner._configure_transaction_search(
        region="us-east-1",
        account_id="123456789012",
        partition="aws",
    )

    assert xray.updated_to == "CloudWatchLogs"
    assert proof == {
        "destination": "CloudWatchLogs",
        "status": "ACTIVE",
        "resource_policy": "TransactionSearchXRayAccess",
        "span_log_group": "aws/spans",
    }
    assert logs.policy_name == "TransactionSearchXRayAccess"
    policy = json.loads(logs.policy_document)
    statement = policy["Statement"][0]
    assert statement["Principal"] == {"Service": "xray.amazonaws.com"}
    assert statement["Action"] == "logs:PutLogEvents"
    assert statement["Resource"] == [
        "arn:aws:logs:us-east-1:123456789012:log-group:aws/spans:*",
        (
            "arn:aws:logs:us-east-1:123456789012:"
            "log-group:/aws/application-signals/data:*"
        ),
    ]
    assert statement["Condition"] == {
        "StringEquals": {"aws:SourceAccount": "123456789012"},
        "ArnLike": {
            "aws:SourceArn": "arn:aws:xray:us-east-1:123456789012:*"
        },
    }


def _unified_trace_records(
    *, trace_id: str, session_id: str, runtime_arn: str
) -> list[dict[str, Any]]:
    def resource() -> dict[str, dict[str, str]]:
        return {"attributes": {"cloud.resource_id": runtime_arn}}

    return [
        {
            "@message": {
                "traceId": trace_id,
                "name": "invoke_agent pellier_orchestrator",
                "attributes": {"session.id": session_id},
                "resource": resource(),
            }
        },
        {
            "@message": json.dumps(
                {
                    "traceId": trace_id,
                    "name": "chat",
                    "attributes": {
                        "gen_ai.request.model": "global.anthropic.claude-sonnet-5"
                    },
                    "resource": resource(),
                }
            )
        },
        {
            "@message": {
                "traceId": trace_id,
                "name": "execute_tool find_pieces_hybrid",
                "attributes": {"gen_ai.tool.name": "find_pieces_hybrid"},
                "resource": resource(),
            }
        },
        {
            "@message": {
                "traceId": "another-trace",
                "name": "execute_tool ignored",
                "attributes": {"gen_ai.tool.name": "ignored"},
                "resource": resource(),
            }
        },
    ]


def test_unified_trace_summary_requires_correlated_agent_model_and_tool_spans() -> None:
    provisioner = _load_provisioner()
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    session_id = "runtime-proof-000000000000000000001"
    runtime_arn = (
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:"
        "runtime/pellier_orchestrator-abc123"
    )

    proof = provisioner._summarize_trace_records(
        _unified_trace_records(
            trace_id=trace_id,
            session_id=session_id,
            runtime_arn=runtime_arn,
        ),
        trace_id=trace_id,
        session_id=session_id,
        runtime_arn=runtime_arn,
    )

    assert proof["span_count"] == 3
    assert proof["runtime_arn"] == runtime_arn
    assert proof["agent_span"] is True
    assert proof["model_span"] is True
    assert proof["tool_span"] is True
    assert proof["model_ids"] == ["global.anthropic.claude-sonnet-5"]
    assert proof["tool_names"] == ["find_pieces_hybrid"]
    assert proof["provenance"] == "agentcore-unified-telemetry"


def test_unified_trace_summary_rejects_spans_from_another_runtime() -> None:
    provisioner = _load_provisioner()
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    session_id = "runtime-proof-000000000000000000001"
    runtime_arn = (
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:"
        "runtime/pellier_orchestrator-abc123"
    )
    records = _unified_trace_records(
        trace_id=trace_id,
        session_id=session_id,
        runtime_arn=runtime_arn,
    )
    records[2]["@message"]["resource"]["attributes"]["cloud.resource_id"] = (
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/other"
    )

    with pytest.raises(RuntimeError, match="another Runtime"):
        provisioner._summarize_trace_records(
            records,
            trace_id=trace_id,
            session_id=session_id,
            runtime_arn=runtime_arn,
        )


def test_trace_poll_uses_pinned_cli_and_downloads_the_matching_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provisioner = _load_provisioner()
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    session_id = f"runtime-proof-{tmp_path.name}-0000000000000001"
    runtime_arn = (
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:"
        "runtime/pellier_orchestrator-abc123"
    )
    calls: list[tuple[str, ...]] = []

    def _agentcore(
        _root: Path, *args: str, env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        del env
        calls.append(args)
        if args[:2] == ("traces", "list"):
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "traces": [
                            {
                                "traceId": trace_id,
                                "sessionId": session_id,
                                "spanCount": 3,
                            }
                        ],
                    }
                ),
                stderr="",
            )
        output = Path(args[args.index("--output") + 1])
        output.write_text(
            json.dumps(
                _unified_trace_records(
                    trace_id=trace_id,
                    session_id=session_id,
                    runtime_arn=runtime_arn,
                )
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args, 0, stdout='{"success":true}', stderr=""
        )

    monkeypatch.setattr(provisioner, "_agentcore", _agentcore)

    proof = provisioner._wait_for_unified_trace(
        root=tmp_path,
        session_id=session_id,
        runtime_arn=runtime_arn,
        env={},
    )

    assert proof["trace_id"] == trace_id
    assert proof["listed_span_count"] == 3
    assert proof["runtime_log_group"].endswith(
        "/pellier_orchestrator-abc123-DEFAULT"
    )
    assert not Path(
        f"/tmp/pellier-agentcore-trace-{session_id}.json"
    ).exists()
    assert calls == [
        (
            "traces",
            "list",
            "--runtime",
            "pellier_orchestrator",
            "--since",
            "15m",
            "--limit",
            "20",
            "--json",
        ),
        (
            "traces",
            "get",
            trace_id,
            "--runtime",
            "pellier_orchestrator",
            "--since",
            "15m",
            "--output",
            f"/tmp/pellier-agentcore-trace-{session_id}.json",
            "--json",
        ),
    ]


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


def test_pyproject_contains_only_runtime_import_roots() -> None:
    deps = PYPROJECT.read_text()
    for package in (
        "strands-agents",
        "aws-opentelemetry-distro",
        "bedrock-agentcore",
        "mcp",
    ):
        assert package in deps
    for app_only_package in ("pydantic-settings", "psycopg", "pgvector", "fastapi"):
        assert app_only_package not in deps


def test_managed_runtime_imports_without_database_configuration(
    tmp_path: Path,
) -> None:
    root, _ = _render(tmp_path, include_policies=False)
    runtime_dir = root / "runtime-src"
    env = os.environ.copy()
    for key in (
        "DB_HOST",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DATABASE_URL",
    ):
        env.pop(key, None)
    env.update(
        {
            "PELLIER_DISABLE_DOTENV": "1",
            "AGENTCORE_GATEWAY_URL": "https://gateway.example.test/mcp",
            "BEDROCK_ROUTER_MODEL": "test-model",
            "PYTHONPATH": str(runtime_dir),
        }
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from services.agentcore_gateway import "
                "_managed_specialist_spec, create_gateway_dispatcher; "
                "from services.conversation_context import "
                "build_conversation_prompt; "
                "assert create_gateway_dispatcher('jwt') is not None; "
                "assert _managed_specialist_spec('inventory')[0] == 'inventory'; "
                "assert build_conversation_prompt('hello') == 'hello'"
            ),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


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
        BACKEND_DIR / ".bedrock_agentcore.yaml",
        BACKEND_DIR / "agentcore.json.template",
        BACKEND_DIR / "aws-targets.json.template",
        BACKEND_DIR / "scripts" / "create_local_memory.py",
        REPO_ROOT / "scripts" / "provision_agentcore_runtime.py",
    ):
        assert not stale.exists()


def test_no_direct_agentcore_control_plane_mutation_helpers() -> None:
    """AgentCore CLI/CDK owns resource mutations; SDK helpers may only inspect."""
    forbidden_sdk_calls = (
        ".create_agent_runtime(",
        ".update_agent_runtime(",
        ".delete_agent_runtime(",
        ".create_gateway(",
        ".update_gateway(",
        ".delete_gateway(",
        ".create_gateway_target(",
        ".update_gateway_target(",
        ".delete_gateway_target(",
        ".create_memory(",
        ".update_memory(",
        ".delete_memory(",
        ".create_policy_engine(",
        ".update_policy_engine(",
        ".delete_policy_engine(",
        ".create_policy(",
        ".update_policy(",
        ".delete_policy(",
    )
    excluded_parts = {
        ".agentcore-project",
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "tests",
    }
    source_paths = (
        *REPO_ROOT.rglob("*.py"),
        *REPO_ROOT.rglob("*.sh"),
    )

    for path in source_paths:
        relative = path.relative_to(REPO_ROOT)
        if excluded_parts.intersection(relative.parts):
            continue
        source = path.read_text()
        for operation in forbidden_sdk_calls:
            assert operation not in source, (
                f"{relative} mutates AgentCore with {operation}; render the "
                "resource in the CLI project instead"
            )
        assert "bedrock-agentcore-control create-" not in source
        assert "bedrock-agentcore-control update-" not in source
        assert "bedrock-agentcore-control delete-" not in source


def test_deploy_all_is_only_a_canonical_provisioner_wrapper() -> None:
    source = DEPLOY_SCRIPT.read_text()
    assert "provision_agentcore_end_to_end.py" in source
    assert "deploy_gateway.py" not in source
    assert "deploy_policy.py" not in source
    assert "bedrock-agentcore-control create" not in source
