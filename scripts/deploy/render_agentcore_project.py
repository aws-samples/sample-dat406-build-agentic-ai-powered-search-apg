#!/usr/bin/env python3
"""Render Pellier's declarative AgentCore CLI project.

The AgentCore CLI owns Runtime, Memory, Gateway, Gateway target registrations,
AgentCore-managed service roles, and Policy. ``deploy_lambda.py`` separately
owns the external Lambda functions and their Lambda execution roles. This
renderer only writes CLI project inputs; it does not call AgentCore
control-plane APIs.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from gateway_tool_schemas import TOOL_SCHEMAS, schema_for


AGENTCORE_CLI = "@aws/agentcore@0.26.0"
PROJECT_NAME = "pellier"
RUNTIME_NAME = "pellier_orchestrator"
MEMORY_NAME = "PellierMemory"
GATEWAY_NAME = "pellier-gateway"
POLICY_ENGINE_NAME = "pellier_policy_engine"
EXPERIENCE_TARGET = "pellier-concierge-experience-target"
PROCESS_RETURN_ACTION = f"{EXPERIENCE_TARGET}___process_return"
RESTOCK_ACTION = "pellier-discovery-search-target___restock_shelf"
WORKSHOP_RUNTIME_EXPOSURE = "public-workshop-only"
RUNTIME_SOURCE_FILES = (
    Path("agentcore_runtime.py"),
    Path("services/__init__.py"),
    Path("services/agentcore_gateway.py"),
    Path("services/conversation_context.py"),
    Path("services/intent_router.py"),
    Path("services/product_envelope.py"),
    Path("services/response_mode.py"),
)


def project_root(repo: Path) -> Path:
    return repo / ".agentcore-project" / PROJECT_NAME


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _render_runtime_source(root: Path, backend_dir: Path) -> Path:
    """Stage only the source files reachable from the managed entrypoint."""
    runtime_dir = root / "runtime-src"
    shutil.rmtree(runtime_dir, ignore_errors=True)
    runtime_dir.mkdir(parents=True)

    for dependency_file in ("pyproject.toml", "uv.lock"):
        shutil.copy2(backend_dir / dependency_file, runtime_dir / dependency_file)
    for relative in RUNTIME_SOURCE_FILES:
        source = backend_dir / relative
        destination = runtime_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return runtime_dir


def baseline_policies(action_token: str = PROCESS_RETURN_ACTION) -> list[dict[str, Any]]:
    """Return the fail-closed Cedar baseline added after initial deployment."""
    gateway_type = "resource is AgentCore::Gateway"
    policies: list[dict[str, Any]] = []
    customer_scoped_actions: dict[str, str] = {}
    for schema in TOOL_SCHEMAS.values():
        target = schema["target_name"]
        for tool in schema["tools"]:
            tool_name = tool["name"]
            token = f"{target}___{tool_name}"
            if tool_name in {
                "preference_snapshot",
                "trace_receipt",
                "escalate_to_stylist",
            }:
                customer_scoped_actions[tool_name] = token
                continue
            if tool_name in {"process_return", "restock_shelf"}:
                continue
            policies.append(
                {
                    "name": f"permit_{tool_name}",
                    "description": f"Permit the authenticated {tool_name} action",
                    "statement": (
                        "permit (\n"
                        "  principal,\n"
                        f'  action == AgentCore::Action::"{token}",\n'
                        f"  {gateway_type}\n"
                        ");"
                    ),
                    "validationMode": "FAIL_ON_ANY_FINDINGS",
                    "enforcementMode": "ACTIVE",
                }
            )

    ownership = (
        'principal.hasTag("username") &&\n'
        "  context.input has customer_id &&\n"
        "  (\n"
        '    (principal.getTag("username") == "marco" && '
        'context.input.customer_id == "CUST-MARCO") ||\n'
        '    (principal.getTag("username") == "anna" && '
        'context.input.customer_id == "CUST-ANNA") ||\n'
        '    (principal.getTag("username") == "theo" && '
        'context.input.customer_id == "CUST-THEO")\n'
        "  )"
    )
    process_action = f'action == AgentCore::Action::"{action_token}"'
    for tool_name, token in customer_scoped_actions.items():
        policies.append(
            {
                "name": f"permit_{tool_name}_owned",
                "description": (
                    f"Permit {tool_name} only for the verified Aurora customer"
                ),
                "statement": (
                    "permit (\n"
                    "  principal,\n"
                    f'  action == AgentCore::Action::"{token}",\n'
                    f"  {gateway_type}\n"
                    ")\n"
                    "when {\n"
                    f"  {ownership}\n"
                    "};"
                ),
                "validationMode": "FAIL_ON_ANY_FINDINGS",
                "enforcementMode": "ACTIVE",
            }
        )
    policies.extend(
        [
        {
            "name": "process_return_owned_damaged",
            "description": "Permit damaged-item returns only for the verified owner",
            "statement": (
                f"permit (principal, {process_action}, {gateway_type})\n"
                "when {\n"
                f"  {ownership} &&\n"
                '  context.input has reason && context.input.reason == "damaged"\n'
                "};"
            ),
            "validationMode": "FAIL_ON_ANY_FINDINGS",
            "enforcementMode": "ACTIVE",
        },
        {
            "name": "process_return_deny_unowned_or_unsupported",
            "description": "Explicitly deny unowned or unsupported returns",
            "statement": (
                f"forbid (principal, {process_action}, {gateway_type})\n"
                "unless {\n"
                f"  {ownership} &&\n"
                '  context.input has reason && context.input.reason == "damaged"\n'
                "};"
            ),
            "validationMode": "FAIL_ON_ANY_FINDINGS",
            "enforcementMode": "ACTIVE",
        },
        {
            "name": "deny_restock_shelf",
            "description": "Shopper principals may never mutate warehouse stock",
            "statement": (
                "forbid (\n"
                "  principal,\n"
                f'  action == AgentCore::Action::"{RESTOCK_ACTION}",\n'
                f"  {gateway_type}\n"
                ");"
            ),
            "validationMode": "FAIL_ON_ANY_FINDINGS",
            "enforcementMode": "ACTIVE",
        },
        ]
    )
    return policies


def render_project(
    *,
    repo: Path,
    account_id: str,
    region: str,
    cognito_pool: str,
    cognito_client: str,
    lambda_arns: dict[str, str],
    model_id: str,
    workshop_id: str,
    include_policies: bool,
    opus_model_id: str | None = None,
    sonnet_model_id: str | None = None,
    action_token: str = PROCESS_RETURN_ACTION,
) -> Path:
    """Write agentcore.json, aws-targets.json, and four tool-schema files."""
    root = project_root(repo)
    config_dir = root / "agentcore"
    schemas_dir = root / "tool-schemas"
    backend_dir = repo / "pellier" / "backend"
    runtime_dir = _render_runtime_source(root, backend_dir)
    runtime_opus_model = opus_model_id or model_id
    runtime_sonnet_model = sonnet_model_id or model_id
    discovery_url = (
        f"https://cognito-idp.{region}.amazonaws.com/"
        f"{cognito_pool}/.well-known/openid-configuration"
    )
    tags = {
        "Project": "pellier",
        "PellierWorkshopId": workshop_id,
        "PellierDeploymentClass": "workshop",
        "PellierRuntimeExposure": WORKSHOP_RUNTIME_EXPOSURE,
    }

    targets: list[dict[str, Any]] = []
    for surface, schema in TOOL_SCHEMAS.items():
        schema_path = schemas_dir / f"{surface}.json"
        _write_json(schema_path, schema_for(surface))
        targets.append(
            {
                "name": schema["target_name"],
                "targetType": "lambdaFunctionArn",
                "lambdaFunctionArn": {
                    "lambdaArn": lambda_arns[surface],
                    "toolSchemaFile": str(schema_path.relative_to(root)),
                },
            }
        )

    project = {
        "$schema": "https://raw.githubusercontent.com/aws/agentcore-cli/main/schemas/agentcore.schema.v1.json",
        "name": PROJECT_NAME,
        "version": 1,
        "managedBy": "CDK",
        "tags": tags,
        "runtimes": [
            {
                "name": RUNTIME_NAME,
                "description": (
                    "Pellier governed dispatcher "
                    "(workshop-only public runtime; not production-ready)"
                ),
                "build": "CodeZip",
                "entrypoint": "agentcore_runtime.py",
                "codeLocation": str(runtime_dir),
                "runtimeVersion": "PYTHON_3_12",
                "envVars": [
                    {"name": "AGENT_MODEL_ID", "value": model_id},
                    {"name": "BEDROCK_ROUTER_MODEL", "value": model_id},
                    {
                        "name": "BEDROCK_OPUS_MODEL",
                        "value": runtime_opus_model,
                    },
                    {
                        "name": "BEDROCK_SONNET_MODEL",
                        "value": runtime_sonnet_model,
                    },
                    {
                        "name": "BEDROCK_REPORTING_MODEL",
                        "value": runtime_sonnet_model,
                    },
                    {
                        "name": "UNIFIED_TRACES_DESTINATION_ENABLED",
                        "value": "true",
                    },
                ],
                "networkMode": "PUBLIC",
                "instrumentation": {"enableOtel": True},
                "protocol": "HTTP",
                "requestHeaderAllowlist": ["Authorization"],
                "authorizerType": "CUSTOM_JWT",
                "authorizerConfiguration": {
                    "customJwtAuthorizer": {
                        "discoveryUrl": discovery_url,
                        "allowedClients": [cognito_client],
                    }
                },
                "tags": tags,
            }
        ],
        "memories": [
            {
                "name": MEMORY_NAME,
                "eventExpiryDuration": 30,
                "strategies": [
                    {
                        "type": "USER_PREFERENCE",
                        "name": "PellierUserPreferences",
                        "description": "Extract durable shopper preferences",
                        "namespaceTemplates": ["/pellier/preferences/{actorId}/"],
                    }
                ],
                "tags": tags,
            }
        ],
        "credentials": [],
        "payments": [],
        "evaluators": [],
        "onlineEvalConfigs": [],
        "agentCoreGateways": [
            {
                "name": GATEWAY_NAME,
                "description": "Pellier MCP tools for search, pricing, curation, and experience",
                "protocolType": "MCP",
                "targets": targets,
                "authorizerType": "CUSTOM_JWT",
                "authorizerConfiguration": {
                    "customJwtAuthorizer": {
                        "discoveryUrl": discovery_url,
                        "allowedClients": [cognito_client],
                    }
                },
                "enableSemanticSearch": True,
                "exceptionLevel": "NONE",
                "policyEngineConfiguration": {
                    "policyEngineName": POLICY_ENGINE_NAME,
                    "mode": "ENFORCE",
                },
                "tags": tags,
            }
        ],
        "policyEngines": [
            {
                "name": POLICY_ENGINE_NAME,
                "description": "Cedar authorization for Pellier Gateway tools",
                "tags": tags,
                "policies": baseline_policies(action_token) if include_policies else [],
            }
        ],
    }

    _write_json(config_dir / "agentcore.json", project)
    _write_json(
        config_dir / "aws-targets.json",
        [{"name": "default", "account": account_id, "region": region}],
    )
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--cognito-pool", required=True)
    parser.add_argument("--cognito-client", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--opus-model-id")
    parser.add_argument("--sonnet-model-id")
    parser.add_argument("--workshop-id", required=True)
    parser.add_argument("--lambda-arns", type=Path, required=True)
    parser.add_argument("--include-policies", action="store_true")
    parser.add_argument("--action-token", default=PROCESS_RETURN_ACTION)
    args = parser.parse_args()

    lambda_arns = json.loads(args.lambda_arns.read_text())
    root = render_project(
        repo=args.repo.resolve(),
        account_id=args.account_id,
        region=args.region,
        cognito_pool=args.cognito_pool,
        cognito_client=args.cognito_client,
        lambda_arns=lambda_arns,
        model_id=args.model_id,
        workshop_id=args.workshop_id,
        include_policies=args.include_policies,
        opus_model_id=args.opus_model_id,
        sonnet_model_id=args.sonnet_model_id,
        action_token=args.action_token,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
