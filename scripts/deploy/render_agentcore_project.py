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

from gateway_tool_schemas import (
    TOOL_SCHEMAS,
    WORKSHOP_DEFERRED_TOOLS,
    schema_for,
    workshop_published_tools,
    workshop_target_tools,
)


AGENTCORE_CLI = "@aws/agentcore@0.26.0"
PROJECT_NAME = "pellier"
RUNTIME_NAME = "pellier_orchestrator"
MEMORY_NAME = "PellierMemory"
GATEWAY_NAME = "pellier-gateway"
POLICY_ENGINE_NAME = "pellier_policy_engine"
EXPERIENCE_TARGET = "pellier-concierge-experience-target"
INITIATE_RETURN_ACTION = f"{EXPERIENCE_TARGET}___initiate_return"
RESTOCK_ACTION = "pellier-discovery-search-target___restock_inventory"
ISSUE_CREDIT_ACTION = "pellier-concierge-experience-target___issue_credit"
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


def baseline_policies(action_token: str = INITIATE_RETURN_ACTION) -> list[dict[str, Any]]:
    """The fail-closed Cedar baseline a fresh workshop provision installs.

    THREE POLICIES, and each one exists for a reason the migration proved the hard way.

    1. `baseline_permit_workshop_tools` — an EXACT allow-list of action ids, never
       `permit(principal, action, resource == gw)`. A wildcard hands every future
       published tool a matching permit the moment it appears, which is exactly what made
       the `initiate_return` publication window unsafe. With an explicit list,
       publication and authorization stay separate decisions.

    2. `initiate_return_damaged_only` — a dedicated permit conditioned on
       `reason == damaged`.

    3. `initiate_return_deny_other_reasons` — the matching forbid.

    WHAT THIS BASELINE DELIBERATELY OMITS
    -------------------------------------

    The actor/customer OWNERSHIP condition — binding `principal.getTag("username")` to
    `context.input.customer_id` — is **absent on purpose**. It is the Lab 4 challenge: a
    participant observes that Marco's token can act on Theo's return, writes the rule,
    and proves the behaviour changed because of their Policy work.

    An earlier version of this renderer installed `initiate_return_owned_damaged` and
    `initiate_return_deny_unowned_or_unsupported`, both carrying that ownership
    condition, plus four ownership-gated read permits. On a freshly provisioned stack the
    participant's exercise would already be solved: step 3's DENY would fire before they
    wrote anything, and the lab would teach that Cedar does something it was already
    doing. That is why this is a teaching baseline and not a claim about the complete
    recommended production posture — the Lab 4 solution adds the ownership dimension, and
    a production deployment would keep it.

    Nothing downstream may re-add the challenge condition. `tests/test_fresh_policy_set.py`
    evaluates the generated Cedar and fails if it reappears.

    EXCLUDED FROM THE ALLOW-LIST
    ----------------------------

        initiate_return     governed by its own permit/forbid pair above
        restock_inventory   mutates warehouse stock. Published as part of the workshop
                            tool contract, and DEFAULT DENY: no matching permit. Cedar is
                            default-deny, so omission is the control. A redundant
                            permit-plus-forbid pair would only add a second thing to keep
                            in sync.

    Deferred tools are not published at all, so they need no forbid: `issue_credit` and
    `get_ticket_history` have no action id on a fresh Gateway.

    WHY THERE IS NO OPERATOR-AUTHORIZATION POLICY HERE
    --------------------------------------------------

    Operator authorization is enforced at the API boundary only
    (`services/auth.py::require_operator`, on every `/api/operator` route). There is no
    Gateway-side defence-in-depth for it, and that is a structural limit rather than an
    omission. The desk invokes exactly two capabilities:

      `initiate_return`  published and permitted, but SHARED with the shopper rail. It is
                         Lab 4's whole subject, so it cannot carry an operator-only
                         condition without destroying the exercise.
      `issue_credit`     the only genuinely operator-only capability, and deferred, so a
                         fresh Gateway has no action id for it. A policy naming it is
                         rejected as `unrecognized action`.

    A previous version of this function gated `restock_inventory` on a Cognito group and
    called that operator enforcement. It was not. `restock_inventory` is an Inventory
    Agent tool with no operator route, and it already has no matching permit, so both an
    operator and a shopper are denied either way. The policy changed the recorded reason
    and no outcome, while risking the entire provision: an unproven
    `getTag(...).contains(...)` under FAIL_ON_ANY_FINDINGS fails `agentcore deploy`, and
    a failed deploy means no Gateway, no Runtime and no Memory.

    WHEN AN OPERATOR-ONLY TOOL IS INTENTIONALLY PUBLISHED, add a separate
    single-action policy for it, using the group name from
    `services/auth.py::OPERATOR_GROUP`, and live-validate it before release.
    `tests/test_fresh_policy_set.py` fails if a baseline policy claims operator
    enforcement without one, so this cannot be re-added decoratively.
    """
    gateway_type = "resource is AgentCore::Gateway"

    # Derived from the one publication contract, so a tool added to the catalogue cannot
    # silently acquire a permit and a deferred tool cannot acquire one at all.
    published = workshop_target_tools()
    NO_BASELINE_PERMIT = {"initiate_return", "restock_inventory"}
    allowed: list[str] = [
        f"{target}___{tool}"
        for target, tools in published.items()
        for tool in tools
        if tool not in NO_BASELINE_PERMIT
    ]
    if not allowed:
        raise SystemExit(
            "refusing to render a baseline permit that permits nothing; "
            "check WORKSHOP_DEFERRED_TOOLS"
        )

    action_list = ",\n".join(
        f'    AgentCore::Action::"{action}"' for action in sorted(allowed)
    )
    policies: list[dict[str, Any]] = [
        {
            "name": "baseline_permit_workshop_tools",
            "description": (
                f"Permit exactly the {len(allowed)} safe workshop actions. "
                "No wildcard, so a newly published tool is denied by default."
            ),
            "statement": (
                "permit (\n"
                "  principal,\n"
                "  action in [\n"
                f"{action_list}\n"
                "  ],\n"
                f"  {gateway_type}\n"
                ");"
            ),
            "validationMode": "FAIL_ON_ANY_FINDINGS",
            "enforcementMode": "ACTIVE",
        },
        {
            "name": "initiate_return_damaged_only",
            "description": "Permit returns only when the stated reason is damaged",
            "statement": (
                f"permit (principal, action == AgentCore::Action::\"{action_token}\", "
                f"{gateway_type})\n"
                "when {\n"
                '  context.input has reason && context.input.reason == "damaged"\n'
                "};"
            ),
            "validationMode": "FAIL_ON_ANY_FINDINGS",
            "enforcementMode": "ACTIVE",
        },
        {
            "name": "initiate_return_deny_other_reasons",
            "description": (
                "Forbid returns with a missing reason or any reason other than damaged"
            ),
            "statement": (
                f"forbid (principal, action == AgentCore::Action::\"{action_token}\", "
                f"{gateway_type})\n"
                "when {\n"
                '  !(context.input has reason) || context.input.reason != "damaged"\n'
                "};"
            ),
            "validationMode": "FAIL_ON_ANY_FINDINGS",
            "enforcementMode": "ACTIVE",
        },
    ]
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
    action_token: str = INITIATE_RETURN_ACTION,
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
        _write_json(schema_path, schema_for(surface, workshop=True))
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
    parser.add_argument("--action-token", default=INITIATE_RETURN_ACTION)
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
