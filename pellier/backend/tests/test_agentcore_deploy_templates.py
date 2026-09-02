"""Static tests for Pellier's AgentCore CLI 0.26 project contract."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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

import gateway_tool_schemas as schemas_module  # noqa: E402
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
        model_id="global.anthropic.claude-sonnet-4-6",
        fast_model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
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
    assert runtime["networkMode"] == "PUBLIC"
    assert runtime["tags"]["PellierDeploymentClass"] == "workshop"
    assert (
        runtime["tags"]["PellierRuntimeExposure"]
        == renderer.WORKSHOP_RUNTIME_EXPOSURE
    )
    assert "workshop-only public runtime" in runtime["description"]
    assert runtime["requestHeaderAllowlist"] == ["Authorization"]
    assert runtime["authorizerType"] == "CUSTOM_JWT"
    assert "executionRoleArn" not in runtime
    assert Path(runtime["codeLocation"]) == root / "runtime-src"

    env = {item["name"]: item["value"] for item in runtime["envVars"]}
    assert env == {
        "AGENT_MODEL_ID": "global.anthropic.claude-sonnet-4-6",
        "BEDROCK_OPUS_MODEL": "global.anthropic.claude-sonnet-4-6",
        "BEDROCK_REPORTING_MODEL": "global.anthropic.claude-sonnet-4-6",
        "BEDROCK_ROUTER_MODEL": "global.anthropic.claude-sonnet-4-6",
        "BEDROCK_SONNET_MODEL": "global.anthropic.claude-sonnet-4-6",
        "BEDROCK_FAST_MODEL": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
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
    assert Path("services/response_mode.py") in actual
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
    # 15, not the canonical 17: `issue_credit` and `get_ticket_history` are deferred for
    # this workshop iteration, so they are not published. Derived rather than written as
    # a literal, because the literal is what went stale.
    assert sum(len(json.loads(path.read_text())) for path in schemas) == len(
        schemas_module.workshop_published_tools()
    )

    engine = project["policyEngines"][0]
    assert engine["name"] == renderer.POLICY_ENGINE_NAME
    assert engine["policies"] == []


def test_second_phase_attaches_the_baseline_cedar_set(tmp_path: Path) -> None:
    """The rendered project carries the baseline policies, whatever they are.

    This test used to enumerate all eighteen policy names, which duplicated
    ``baseline_policies`` in a second place and is how the set drifted to a shape nobody
    had validated: an eighteen-policy model with username/customer ownership baked into
    the baseline, so a fresh stack shipped the Lab 4 answer. The policy-by-policy
    contract now lives in ``test_fresh_policy_set.py``. What belongs HERE is the
    project-level property: every policy the renderer produces reaches the project's
    single engine, enforced and validated, with no wildcard among them.
    """
    _, project = _render(tmp_path, include_policies=True)
    policies = project["policyEngines"][0]["policies"]
    expected = renderer.baseline_policies()

    assert [policy["name"] for policy in policies] == [p["name"] for p in expected]
    assert all(policy["enforcementMode"] == "ACTIVE" for policy in policies)
    assert all(
        policy["validationMode"] == "FAIL_ON_ANY_FINDINGS" for policy in policies
    )
    statements = "\n".join(policy["statement"] for policy in policies)
    assert renderer.INITIATE_RETURN_ACTION in statements
    assert "resource is AgentCore::Gateway" in statements
    # A wildcard permit authorizes any action published later, including one added after
    # this project was reviewed. Default-deny is the whole reason the allow-list is
    # written out action by action.
    assert "permit (principal, action, resource is AgentCore::Gateway)" not in statements
    assert "permit (\n  principal,\n  action,\n" not in statements


def test_restock_inventory_is_published_without_a_baseline_permit(tmp_path: Path) -> None:
    """Published and unauthorized is a DENY, and that is the intended shape.

    ``restock_inventory`` must exist on the Gateway so the operator desk can attempt it
    and the refusal is a real Cedar decision rather than a missing tool. Naming it in a
    baseline permit would authorize it for every principal.
    """
    _, project = _render(tmp_path, include_policies=True)
    policies = project["policyEngines"][0]["policies"]

    # The property is "no PERMIT reaches it", not "the name appears nowhere". It now
    # appears in `forbid_restock_without_operator_group`, which makes the refusal explicit
    # and attributable instead of an absence, and a forbid cannot grant anything.
    permits = [
        policy["statement"]
        for policy in policies
        if policy["statement"].lstrip().startswith("permit")
    ]
    assert permits, "the baseline emitted no permit at all"
    for statement in permits:
        assert renderer.RESTOCK_ACTION not in statement, (
            "a permit reaches restock_inventory; it must stay default-deny"
        )

    schemas = sorted((Path(tmp_path) / "pellier" / "tool-schemas").glob("*.json")) or \
        sorted(Path(tmp_path).rglob("tool-schemas/*.json"))
    published = {
        tool["name"]
        for path in schemas
        for tool in json.loads(path.read_text())
    }
    assert "restock_inventory" in published


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


def test_cloudtrail_audit_receipt_is_recent_correlated_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioner = _load_provisioner()
    deployment_started_at = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    requested: dict[str, Any] = {}

    class _Paginator:
        def paginate(self, **kwargs: Any) -> list[dict[str, list[dict[str, Any]]]]:
            requested.update(kwargs)
            return [
                {
                    "Events": [
                        {
                            "EventSource": "bedrock-agentcore.amazonaws.com",
                            "EventName": "CreateAgentRuntime",
                            "EventTime": deployment_started_at,
                            "CloudTrailEvent": json.dumps(
                                {
                                    "requestParameters": {
                                        "agentRuntimeName": renderer.RUNTIME_NAME
                                    },
                                    "responseElements": {
                                        "agentRuntimeArn": (
                                            "arn:aws:bedrock-agentcore:us-east-1:"
                                            "123456789012:runtime/pellier-runtime"
                                        )
                                    },
                                    "userIdentity": {
                                        "arn": "must-not-appear-in-receipt"
                                    },
                                }
                            ),
                        }
                    ]
                }
            ]

    class _CloudTrail:
        def get_paginator(self, name: str) -> _Paginator:
            assert name == "lookup_events"
            return _Paginator()

    monkeypatch.setattr(
        provisioner.boto3,
        "client",
        lambda service, **_: _CloudTrail() if service == "cloudtrail" else None,
    )

    proof = provisioner._verify_agentcore_control_plane_audit(
        region="us-east-1",
        deployment_started_at=deployment_started_at,
        runtime_arn=(
            "arn:aws:bedrock-agentcore:us-east-1:123456789012:"
            "runtime/pellier-runtime"
        ),
        gateway_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gateway",
        memory_id="memory-123",
        policy_engine_id="policy-123",
    )

    assert requested["LookupAttributes"] == [
        {
            "AttributeKey": "EventSource",
            "AttributeValue": "bedrock-agentcore.amazonaws.com",
        }
    ]
    assert proof == {
        "source": "CloudTrail Event History",
        "event_source": "bedrock-agentcore.amazonaws.com",
        "event_name": "CreateAgentRuntime",
        "event_time": "2026-08-13T12:00:00Z",
        "resource_type": "runtime",
    }
    assert "userIdentity" not in proof
    assert "must-not-appear-in-receipt" not in json.dumps(proof)


def test_transaction_search_setup_is_scoped_and_requires_active_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioner = _load_provisioner()

    class _Logs:
        policy_name = ""
        policy_document = ""

        def describe_resource_policies(self, **_: Any) -> dict[str, Any]:
            return {"resourcePolicies": []}

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
        "resource_policy_document": logs.policy_document,
        "span_log_group": "aws/spans",
        "cleanup": {
            "destination_changed": True,
            "previous_destination": "XRay",
            "resource_policy_created": True,
            "previous_resource_policy_document": None,
        },
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


def test_runtime_log_group_is_customer_encrypted_and_retention_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioner = _load_provisioner()
    runtime_arn = (
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:"
        "runtime/pellier_orchestrator-abc123"
    )
    kms_key_arn = (
        "arn:aws:kms:us-east-1:123456789012:"
        "key/12345678-1234-1234-1234-1234567890ab"
    )

    class _Paginator:
        def __init__(self, logs: Any) -> None:
            self.logs = logs

        def paginate(self, **_: Any) -> list[dict[str, list[dict[str, Any]]]]:
            return [{"logGroups": [self.logs.group]}]

    class _Logs:
        class exceptions:
            class ResourceAlreadyExistsException(Exception):
                pass

        def __init__(self) -> None:
            self.group = {
                "logGroupName": provisioner._runtime_log_group_name(runtime_arn),
                "kmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/old",
                "retentionInDays": 7,
            }
            self.associated_kms_key = ""
            self.retention_days = 0

        def create_log_group(self, **_: Any) -> None:
            raise self.exceptions.ResourceAlreadyExistsException()

        def get_paginator(self, name: str) -> _Paginator:
            assert name == "describe_log_groups"
            return _Paginator(self)

        def associate_kms_key(self, *, logGroupName: str, kmsKeyId: str) -> None:
            assert logGroupName == self.group["logGroupName"]
            self.associated_kms_key = kmsKeyId
            self.group["kmsKeyId"] = kmsKeyId

        def put_retention_policy(
            self, *, logGroupName: str, retentionInDays: int
        ) -> None:
            assert logGroupName == self.group["logGroupName"]
            self.retention_days = retentionInDays
            self.group["retentionInDays"] = retentionInDays

    logs = _Logs()
    monkeypatch.setattr(
        provisioner.boto3,
        "client",
        lambda service, **_: logs if service == "logs" else None,
    )

    proof = provisioner._ensure_runtime_log_group(
        region="us-east-1",
        runtime_arn=runtime_arn,
        kms_key_arn=kms_key_arn,
        retention_days=30,
    )

    assert proof == {
        "name": "/aws/bedrock-agentcore/runtimes/pellier_orchestrator-abc123-DEFAULT",
        "kms_key_arn": kms_key_arn,
        "retention_days": 30,
        "cleanup": {
            "created_by_workshop": False,
            "creation_pending": False,
            "previous_kms_key_arn": (
                "arn:aws:kms:us-east-1:123456789012:key/old"
            ),
            "previous_retention_days": 7,
        },
    }
    assert logs.associated_kms_key == kms_key_arn
    assert logs.retention_days == 30


def test_runtime_log_group_rejects_alias_and_unbounded_retention() -> None:
    provisioner = _load_provisioner()

    with pytest.raises(RuntimeError, match="customer-managed KMS key ARN"):
        provisioner._ensure_runtime_log_group(
            region="us-east-1",
            runtime_arn="arn:aws:bedrock-agentcore:us-east-1:123:runtime/test",
            kms_key_arn="arn:aws:kms:us-east-1:123456789012:alias/pellier",
            retention_days=30,
        )
    with pytest.raises(RuntimeError, match="must be one of"):
        provisioner._runtime_log_retention_days("0")


def test_trace_log_groups_are_created_encrypted_and_retention_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioner = _load_provisioner()
    kms_key_arn = (
        "arn:aws:kms:us-east-1:123456789012:"
        "key/12345678-1234-1234-1234-1234567890ab"
    )

    class _Paginator:
        def __init__(self, logs: Any) -> None:
            self.logs = logs

        def paginate(self, **kwargs: Any) -> list[dict[str, Any]]:
            name = kwargs["logGroupNamePrefix"]
            group = self.logs.groups.get(name)
            return [{"logGroups": [group] if group else []}]

    class _Logs:
        class exceptions:
            class ResourceAlreadyExistsException(Exception):
                pass

        def __init__(self) -> None:
            self.groups: dict[str, dict[str, Any]] = {}

        def create_log_group(
            self, *, logGroupName: str, kmsKeyId: str
        ) -> None:
            self.groups[logGroupName] = {
                "logGroupName": logGroupName,
                "kmsKeyId": kmsKeyId,
            }

        def get_paginator(self, name: str) -> _Paginator:
            assert name == "describe_log_groups"
            return _Paginator(self)

        def associate_kms_key(
            self, *, logGroupName: str, kmsKeyId: str
        ) -> None:
            self.groups[logGroupName]["kmsKeyId"] = kmsKeyId

        def put_retention_policy(
            self, *, logGroupName: str, retentionInDays: int
        ) -> None:
            self.groups[logGroupName]["retentionInDays"] = retentionInDays

    logs = _Logs()
    monkeypatch.setattr(provisioner.boto3, "client", lambda *_args, **_kwargs: logs)

    proof = provisioner._ensure_trace_log_groups(
        region="us-east-1",
        kms_key_arn=kms_key_arn,
        retention_days=30,
    )

    assert [group["name"] for group in proof["groups"]] == [
        "aws/spans",
        "/aws/application-signals/data",
    ]
    assert all(group["kms_key_arn"] == kms_key_arn for group in proof["groups"])
    assert all(group["retention_days"] == 30 for group in proof["groups"])
    assert all(
        group["cleanup"]
        == {
            "created_by_workshop": True,
            "creation_pending": False,
            "previous_kms_key_arn": None,
            "previous_retention_days": None,
        }
        for group in proof["groups"]
    )
    assert {
        name: (group["kmsKeyId"], group["retentionInDays"])
        for name, group in logs.groups.items()
    } == {
        "aws/spans": (kms_key_arn, 30),
        "/aws/application-signals/data": (kms_key_arn, 30),
    }


def test_log_group_create_race_checkpoints_existing_ownership_before_repair() -> None:
    provisioner = _load_provisioner()
    kms_key_arn = (
        "arn:aws:kms:us-east-1:123456789012:"
        "key/12345678-1234-1234-1234-1234567890ab"
    )
    log_group_name = "aws/spans"
    events: list[str] = []
    checkpoints: list[dict[str, Any]] = []

    class _Paginator:
        def __init__(self, logs: Any) -> None:
            self.logs = logs

        def paginate(self, **_: Any) -> list[dict[str, Any]]:
            return [{"logGroups": [self.logs.group] if self.logs.group else []}]

    class _Logs:
        class exceptions:
            class ResourceAlreadyExistsException(Exception):
                pass

        def __init__(self) -> None:
            self.group: dict[str, Any] | None = None

        def get_paginator(self, _: str) -> _Paginator:
            return _Paginator(self)

        def create_log_group(self, **_: Any) -> None:
            events.append("create")
            self.group = {
                "logGroupName": log_group_name,
                "kmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/external",
                "retentionInDays": 7,
            }
            raise self.exceptions.ResourceAlreadyExistsException()

        def associate_kms_key(self, **_: Any) -> None:
            events.append("associate")
            assert self.group is not None
            self.group["kmsKeyId"] = kms_key_arn

        def put_retention_policy(self, **_: Any) -> None:
            events.append("retention")
            assert self.group is not None
            self.group["retentionInDays"] = 30

    def checkpoint(group: dict[str, Any]) -> None:
        checkpoints.append(json.loads(json.dumps(group)))
        if group["cleanup"]["creation_pending"]:
            ownership = "pending"
        elif group["cleanup"]["created_by_workshop"]:
            ownership = "created"
        else:
            ownership = "preexisting"
        events.append(f"checkpoint:{ownership}")

    proof = provisioner._ensure_protected_log_group(
        logs=_Logs(),
        log_group_name=log_group_name,
        kms_key_arn=kms_key_arn,
        retention_days=30,
        on_cleanup_state=checkpoint,
    )

    assert events == [
        "checkpoint:pending",
        "create",
        "checkpoint:preexisting",
        "associate",
        "retention",
    ]
    assert checkpoints[-1]["cleanup"] == {
        "created_by_workshop": False,
        "creation_pending": False,
        "previous_kms_key_arn": (
            "arn:aws:kms:us-east-1:123456789012:key/external"
        ),
        "previous_retention_days": 7,
    }
    assert proof["cleanup"] == checkpoints[-1]["cleanup"]


def test_trace_log_group_failure_keeps_partial_cleanup_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioner = _load_provisioner()
    kms_key_arn = (
        "arn:aws:kms:us-east-1:123456789012:"
        "key/12345678-1234-1234-1234-1234567890ab"
    )
    checkpoints: list[dict[str, Any]] = []

    class _Paginator:
        def __init__(self, logs: Any) -> None:
            self.logs = logs

        def paginate(self, **kwargs: Any) -> list[dict[str, Any]]:
            group = self.logs.groups.get(kwargs["logGroupNamePrefix"])
            return [{"logGroups": [group] if group else []}]

    class _Logs:
        class exceptions:
            class ResourceAlreadyExistsException(Exception):
                pass

        def __init__(self) -> None:
            self.groups: dict[str, dict[str, Any]] = {}

        def get_paginator(self, _: str) -> _Paginator:
            return _Paginator(self)

        def create_log_group(
            self,
            *,
            logGroupName: str,
            kmsKeyId: str,
        ) -> None:
            if logGroupName == "/aws/application-signals/data":
                raise RuntimeError("injected create failure")
            self.groups[logGroupName] = {
                "logGroupName": logGroupName,
                "kmsKeyId": kmsKeyId,
            }

        def associate_kms_key(self, **_: Any) -> None:
            raise AssertionError("new groups already use the required key")

        def put_retention_policy(
            self,
            *,
            logGroupName: str,
            retentionInDays: int,
        ) -> None:
            self.groups[logGroupName]["retentionInDays"] = retentionInDays

    logs = _Logs()
    monkeypatch.setattr(provisioner.boto3, "client", lambda *_args, **_kwargs: logs)

    with pytest.raises(RuntimeError, match="injected create failure"):
        provisioner._ensure_trace_log_groups(
            region="us-east-1",
            kms_key_arn=kms_key_arn,
            retention_days=30,
            on_cleanup_state=lambda group: checkpoints.append(
                json.loads(json.dumps(group))
            ),
        )

    assert [group["name"] for group in checkpoints] == [
        "aws/spans",
        "aws/spans",
        "/aws/application-signals/data",
    ]
    assert checkpoints[0]["cleanup"] == {
        "created_by_workshop": False,
        "creation_pending": True,
        "previous_kms_key_arn": None,
        "previous_retention_days": None,
    }
    assert checkpoints[1]["cleanup"] == {
        "created_by_workshop": True,
        "creation_pending": False,
        "previous_kms_key_arn": None,
        "previous_retention_days": None,
    }
    assert checkpoints[2]["cleanup"] == {
        "created_by_workshop": False,
        "creation_pending": True,
        "previous_kms_key_arn": None,
        "previous_retention_days": None,
    }
    assert logs.groups["aws/spans"]["retentionInDays"] == 30


def test_transaction_search_checkpoints_prior_state_before_policy_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioner = _load_provisioner()
    events: list[str] = []
    checkpoints: list[dict[str, Any]] = []

    class _Logs:
        def describe_resource_policies(self, **_: Any) -> dict[str, Any]:
            return {"resourcePolicies": []}

        def put_resource_policy(self, **_: Any) -> None:
            events.append("put-policy")
            raise RuntimeError("injected policy failure")

    class _XRay:
        def get_trace_segment_destination(self) -> dict[str, str]:
            return {"Destination": "XRay", "Status": "ACTIVE"}

    logs = _Logs()
    xray = _XRay()
    monkeypatch.setattr(
        provisioner.boto3,
        "client",
        lambda service, **_: logs if service == "logs" else xray,
    )

    def checkpoint(receipt: dict[str, Any]) -> None:
        events.append("checkpoint")
        checkpoints.append(json.loads(json.dumps(receipt)))

    with pytest.raises(RuntimeError, match="injected policy failure"):
        provisioner._configure_transaction_search(
            region="us-east-1",
            account_id="123456789012",
            partition="aws",
            on_cleanup_state=checkpoint,
        )

    assert events == ["checkpoint", "put-policy"]
    policy_document = checkpoints[0].pop("resource_policy_document")
    assert json.loads(policy_document)["Statement"][0]["Sid"] == (
        "TransactionSearchXRayAccess"
    )
    assert checkpoints == [
        {
            "destination": "CloudWatchLogs",
            "status": "CONFIGURING",
            "resource_policy": "TransactionSearchXRayAccess",
            "span_log_group": "aws/spans",
            "cleanup": {
                "destination_changed": True,
                "previous_destination": "XRay",
                "resource_policy_created": True,
                "previous_resource_policy_document": None,
            },
        }
    ]


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
                "startTimeUnixNano": "1000000000",
                "endTimeUnixNano": "1900000000",
                "attributes": {
                    "session.id": session_id,
                    "gen_ai.input.messages": {"stringValue": "find linen"},
                    "gen_ai.output.messages": {"stringValue": "linen dress"},
                },
                "resource": resource(),
            }
        },
        {
            "@message": json.dumps(
                {
                    "traceId": trace_id,
                    "name": "chat",
                    "durationNanos": "320000000",
                    "attributes": {
                        "gen_ai.request.model": "global.anthropic.claude-sonnet-4-6"
                    },
                    "resource": resource(),
                }
            )
        },
        {
            "@message": {
                "traceId": trace_id,
                "name": "execute_tool search_products_hybrid",
                "durationMs": 45,
                "attributes": {
                    "gen_ai.tool.name": "search_products_hybrid",
                    "gen_ai.tool.call.arguments": {"query": "linen"},
                    "gen_ai.tool.call.result": {"product_ids": ["P-101"]},
                },
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
    assert proof["agent_input_observed"] is True
    assert proof["agent_output_observed"] is True
    assert proof["tool_input_output_structured"] is True
    assert proof["tool_input_output_sanitized"] is True
    assert proof["attribute_contract"] == {
        "agent_input": "gen_ai.input.messages",
        "agent_output": "gen_ai.output.messages",
        "tool_input": "gen_ai.tool.call.arguments",
        "tool_output": "gen_ai.tool.call.result",
    }
    assert proof["step_latency_ms"] == {"agent": 900, "model": 320, "tool": 45}
    assert proof["model_ids"] == ["global.anthropic.claude-sonnet-4-6"]
    assert proof["tool_names"] == ["search_products_hybrid"]
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


def test_unified_trace_summary_rejects_secret_bearing_tool_io() -> None:
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
    records[2]["@message"]["attributes"]["gen_ai.tool.call.arguments"] = {
        "authorization": "Bearer token"
    }

    with pytest.raises(RuntimeError, match="secret or credential marker"):
        provisioner._summarize_trace_records(
            records,
            trace_id=trace_id,
            session_id=session_id,
            runtime_arn=runtime_arn,
        )


def test_unified_trace_summary_rejects_unstructured_tool_io() -> None:
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
    records[2]["@message"]["attributes"]["gen_ai.tool.call.result"] = (
        "free-form result"
    )

    with pytest.raises(RuntimeError, match="structured JSON"):
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
        fast_model_id="fast-model",
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


def _ownership():
    """Load the checked-in ownership manifest."""
    import sys

    deploy = REPO_ROOT / "scripts" / "deploy"
    if str(deploy) not in sys.path:
        sys.path.insert(0, str(deploy))
    import ownership

    return ownership


def _scannable_sources():
    excluded_parts = {
        ".agentcore-project", ".git", ".venv", "__pycache__", "node_modules", "tests",
    }
    # The manifest defines the forbidden and allowed operation names, so it has to
    # spell them. Scanning it would make the guard fail on its own vocabulary.
    excluded_files = {"scripts/deploy/ownership.py"}
    for path in (*REPO_ROOT.rglob("*.py"), *REPO_ROOT.rglob("*.sh")):
        relative = path.relative_to(REPO_ROOT)
        if excluded_parts.intersection(relative.parts):
            continue
        if relative.as_posix() in excluded_files:
            continue
        try:
            yield relative, path.read_text()
        except (UnicodeDecodeError, OSError):
            continue


def test_cfn_owned_resources_are_never_mutated_directly() -> None:
    """Runtime, Memory and their IAM live in a CloudFormation stack.

    A direct control-plane update would drift the stack from reality, and the next
    CLI deploy would silently revert it. These operations are forbidden everywhere
    in the repository, with no exception module.
    """
    ownership = _ownership()
    for relative, source in _scannable_sources():
        for operation in ownership.FORBIDDEN_CONTROL_PLANE_WRITES:
            assert operation not in source, (
                f"{relative} mutates a CloudFormation-owned AgentCore resource with "
                f"{operation}. Runtime, Memory and their IAM belong to stack "
                f"{ownership.CFN_STACK}; change them through the CLI project."
            )


def test_control_plane_updates_live_only_in_the_migration_module() -> None:
    """The Gateway, its targets and the policies are NOT stack-owned.

    They were created by direct API and the CLI cannot represent them: `import
    gateway` maps zero targets because their tool schemas are inline. So updating
    them in place is the supported path, but it is confined to one module rather
    than available to application code.
    """
    ownership = _ownership()
    allowed = ownership.MIGRATION_MODULE
    for relative, source in _scannable_sources():
        rel = relative.as_posix()
        for operation in ownership.ALLOWED_IN_MIGRATION_MODULE:
            if operation in source:
                assert rel == allowed, (
                    f"{rel} calls {operation}. In-place control-plane updates are "
                    f"permitted only in {allowed}, which asserts the account, "
                    "region and resource ids before it writes."
                )


def test_the_migration_module_pins_the_environment_before_writing() -> None:
    """An allow-list of ids is what makes the exception safe rather than a hole."""
    ownership = _ownership()
    source = (REPO_ROOT / ownership.MIGRATION_MODULE).read_text()
    for token in (
        "EXPECTED_ACCOUNT",
        "EXPECTED_REGION",
        "EXPECTED_GATEWAY_ID",
        "EXPECTED_POLICY_ENGINE_ID",
        "EXPECTED_TARGET_NAMES",
        "EXPECTED_POLICY_NAMES",
    ):
        assert token in source, (
            f"{ownership.MIGRATION_MODULE} does not assert {token} before mutating"
        )


def test_the_ownership_manifest_matches_the_audited_deployment() -> None:
    """Ownership is ARN plus CloudFormation membership, never a workshop tag."""
    ownership = _ownership()
    assert ownership.may_update_directly("runtime") is False
    assert ownership.may_update_directly("memory") is False
    assert ownership.may_update_directly("iam") is False
    assert ownership.may_update_directly("gateway") is True
    assert ownership.may_update_directly("gateway_targets") is True
    assert ownership.may_update_directly("policy_engine") is True
    assert ownership.may_update_directly("policies") is True
    for key in ("runtime", "memory", "iam"):
        assert ownership.MANIFEST[key].stack == ownership.CFN_STACK
    for key in ("gateway", "gateway_targets", "policy_engine", "policies"):
        assert ownership.MANIFEST[key].stack == "", (
            f"{key} is recorded as stack-owned; the audit found it in no stack"
        )
    # PellierWorkshopId carries three different values in this account and is
    # forensic provenance only. It must not appear as ownership evidence.
    source = (REPO_ROOT / "scripts" / "deploy" / "ownership.py").read_text()
    assert "PellierWorkshopId" in source, "the manifest should explain why not to use it"
    assert "forensic provenance only" in source


def test_the_cli_project_path_is_still_the_only_creator() -> None:
    """Nothing may create AgentCore resources outside the CLI project."""
    for relative, source in _scannable_sources():
        assert "bedrock-agentcore-control create-" not in source, relative
        assert "bedrock-agentcore-control delete-" not in source, relative


def test_deploy_all_is_only_a_canonical_provisioner_wrapper() -> None:
    source = DEPLOY_SCRIPT.read_text()
    assert "provision_agentcore_end_to_end.py" in source
    assert "deploy_gateway.py" not in source
    assert "deploy_policy.py" not in source
    assert "bedrock-agentcore-control create" not in source
