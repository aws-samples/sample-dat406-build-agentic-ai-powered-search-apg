"""Who owns each deployed AgentCore resource, and therefore how it may change.

This module exists because the repository's previous rule — "the AgentCore CLI
owns every resource mutation" — was false for half of this deployment, and acting
on a false ownership model is how Runtime and Memory become collateral damage in
a Gateway rename.

The audit that produced this file
--------------------------------

CloudFormation stack ``AgentCore-pellier-default`` contains exactly six
resources: the Runtime, the Memory, ``AWS::CDK::Metadata``, and three IAM
resources. Cross-checked against the ``agentcore:created-by`` tag:

    Runtime         agentcore:created-by = agentcore-cli    in the stack
    Memory          agentcore:created-by = agentcore-cli    in the stack
    Gateway         tag absent                              in NO stack
    Gateway targets tag absent                              in NO stack
    Policy engine   tag absent                              in NO stack

So the Gateway, its four targets, and the policy engine were created by direct
control-plane calls and have never been CLI- or CDK-managed. Attempting to adopt
them proved it from the other side: ``agentcore import memory`` refused with
"already managed by CloudFormation stack AgentCore-pellier-default", while
``agentcore import gateway`` mapped the gateway with **zero** targets because it
cannot represent an inline tool schema.

Ownership is determined by ARN plus CloudFormation membership. It is NOT
determined by ``PellierWorkshopId``, which carries three different values across
this account from separate provisioning runs and is forensic provenance only.

The rule
--------

A resource in the stack is changed by the tool that owns the stack. A resource
outside it is changed in place through the supported ``bedrock-agentcore-control``
APIs, and only through the one narrowly scoped migration module that names it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Ownership models.
OWNER_CLI_CFN = "agentcore_cli_cfn"
OWNER_CONTROL_PLANE = "agentcore_control_plane"
OWNER_LAMBDA_SCRIPT = "lambda_deploy_script"

# The one CloudFormation stack that owns AgentCore resources in this deployment.
CFN_STACK = "AgentCore-pellier-default"

# The environment this migration is written for. A mismatch is a hard stop, not a
# warning: these are specific resources, and pointing them at another account would
# mutate something nobody audited.
#
# READ FROM THE ENVIRONMENT, not hardcoded. Every value here identifies one AWS
# account's deployment, and this repository is published. An account id, a gateway
# id, a policy engine id and a cluster name in a tracked file tell a reader exactly
# which resources to go looking for. So the operator supplies them and the migration
# refuses to run without them: `require_environment_pins()` below turns an unset pin
# into a hard stop rather than a comparison against an empty string, which would
# otherwise pass against any account at all.
EXPECTED_ACCOUNT = os.environ.get("PELLIER_EXPECTED_ACCOUNT", "")
EXPECTED_REGION = os.environ.get("PELLIER_EXPECTED_REGION", "us-east-1")
EXPECTED_GATEWAY_ID = os.environ.get("PELLIER_EXPECTED_GATEWAY_ID", "")
EXPECTED_POLICY_ENGINE_ID = os.environ.get("PELLIER_EXPECTED_POLICY_ENGINE_ID", "")
EXPECTED_DB_CLUSTER = os.environ.get("PELLIER_EXPECTED_DB_CLUSTER", "")

# The four Gateway targets, by name. Target ids are resolved live rather than
# pinned here: they are account-specific and would rot, while the names are the
# provisioning contract that `gateway_tool_schemas.py` also uses.
EXPECTED_TARGET_NAMES: Tuple[str, ...] = (
    "pellier-discovery-search-target",
    "pellier-value-pricing-target",
    "pellier-curation-recommendation-target",
    "pellier-concierge-experience-target",
)

# The three policies whose Cedar definitions this migration may rewrite. Any
# other policy id appearing live is unexpected drift and stops the run.
EXPECTED_POLICY_NAMES: Tuple[str, ...] = (
    "baseline_permit_gateway_tools",
    "process_return_allow_damaged",
    "process_return_damaged_only",
)

# The Lambda that Phase B1 already deployed. Its SHA is asserted so the migration
# cannot run against an unexpected build of the tool it is renaming.
EXPECTED_EXPERIENCE_LAMBDA = "pellier-experience-server-function"
EXPECTED_EXPERIENCE_SHA = os.environ.get("PELLIER_EXPECTED_EXPERIENCE_SHA", "")

# Every pin that has no safe default, paired with the value this module resolved at
# import. The region is absent because it has one: `us-east-1` is the workshop region
# everywhere else in this repository, and it is not an identifier.
#
# Checked against the RESOLVED values rather than `os.environ` at call time. The
# constants above are bound once, at import, so a process that set the variables
# afterwards would pass an `os.environ` check while every comparison in the preflight
# ran against an empty string.
def _resolved_pins() -> Tuple[Tuple[str, str], ...]:
    return (
        ("PELLIER_EXPECTED_ACCOUNT", EXPECTED_ACCOUNT),
        ("PELLIER_EXPECTED_GATEWAY_ID", EXPECTED_GATEWAY_ID),
        ("PELLIER_EXPECTED_POLICY_ENGINE_ID", EXPECTED_POLICY_ENGINE_ID),
        ("PELLIER_EXPECTED_DB_CLUSTER", EXPECTED_DB_CLUSTER),
        ("PELLIER_EXPECTED_EXPERIENCE_SHA", EXPECTED_EXPERIENCE_SHA),
    )


REQUIRED_PINS: Tuple[str, ...] = tuple(name for name, _ in _resolved_pins())


def missing_environment_pins() -> List[str]:
    """Required pins this module resolved to nothing."""
    return [name for name, value in _resolved_pins() if not str(value).strip()]


def require_environment_pins() -> None:
    """Refuse to proceed without every environment pin.

    Called from the migration's preflight. An unset pin is worse than a wrong one:
    ``result.record("account", ident["Account"], "")`` fails, but a preflight that
    compared two empty strings would pass against any account in the world, which is
    the exact opposite of what a hard stop is for.
    """
    missing = missing_environment_pins()
    if missing:
        raise SystemExit(
            "This migration is pinned to one audited deployment and refuses to run "
            "without knowing which one. Set these first:\n  "
            + "\n  ".join(missing)
            + "\n\nThey identify a specific account and its Gateway, policy engine, "
            "Aurora cluster, and the Lambda build the rename was written against. "
            "They are read from the environment rather than tracked in source because "
            "this repository is published."
        )


@dataclass(frozen=True)
class ResourceOwnership:
    """How one resource class may be changed."""

    resource: str
    owner: str
    direct_update: bool
    stack: str = ""
    note: str = ""


MANIFEST: Dict[str, ResourceOwnership] = {
    "runtime": ResourceOwnership(
        resource="AgentCore Runtime",
        owner=OWNER_CLI_CFN,
        direct_update=False,
        stack=CFN_STACK,
        note=(
            "In the stack. Changed only by the tool that owns the stack. A direct "
            "control-plane update would drift the stack from reality and the next "
            "CLI deploy would revert it."
        ),
    ),
    "memory": ResourceOwnership(
        resource="AgentCore Memory",
        owner=OWNER_CLI_CFN,
        direct_update=False,
        stack=CFN_STACK,
        note="In the stack, same reasoning as the Runtime.",
    ),
    "iam": ResourceOwnership(
        resource="IAM roles and policies for Runtime/Memory",
        owner=OWNER_CLI_CFN,
        direct_update=False,
        stack=CFN_STACK,
        note="Three IAM resources in the stack. Never touched by this migration.",
    ),
    "gateway": ResourceOwnership(
        resource="AgentCore Gateway",
        owner=OWNER_CONTROL_PLANE,
        direct_update=True,
        note=(
            "Created by direct API, in no stack. `update-gateway` is used ONLY to "
            "change the policy enforcement mode during explicit test phases, "
            "preserving every other field."
        ),
    ),
    "gateway_targets": ResourceOwnership(
        resource="AgentCore Gateway targets",
        owner=OWNER_CONTROL_PLANE,
        direct_update=True,
        note=(
            "Created by direct API, in no stack, with inline tool schemas that the "
            "CLI cannot import. `update-gateway-target` updates them in place; they "
            "are never deleted and recreated."
        ),
    ),
    "policy_engine": ResourceOwnership(
        resource="AgentCore Policy engine",
        owner=OWNER_CONTROL_PLANE,
        direct_update=True,
        note=(
            "Created by direct API, in no stack. Never replaced: `add policy-engine` "
            "creates rather than adopts, so a project-declared engine would be a "
            "second engine."
        ),
    ),
    "policies": ResourceOwnership(
        resource="AgentCore policies",
        owner=OWNER_CONTROL_PLANE,
        direct_update=True,
        note=(
            "`update-policy` rewrites the Cedar definition while the policy id "
            "stays stable, so history and attachments survive the rename."
        ),
    ),
    "experience_lambda": ResourceOwnership(
        resource="Experience MCP Lambda",
        owner=OWNER_LAMBDA_SCRIPT,
        direct_update=True,
        note="Deployed by scripts/deploy/deploy_lambda.py. Phase B1 is complete.",
    ),
}

# Control-plane write operations, split by what they touch. The allowed set is
# permitted ONLY inside the migration module named below; the forbidden set is
# permitted nowhere in this repository.
FORBIDDEN_CONTROL_PLANE_WRITES: Tuple[str, ...] = (
    ".create_agent_runtime(",
    ".update_agent_runtime(",
    ".delete_agent_runtime(",
    ".create_memory(",
    ".update_memory(",
    ".delete_memory(",
    ".create_gateway(",
    ".delete_gateway(",
    ".create_gateway_target(",
    ".delete_gateway_target(",
    ".create_policy_engine(",
    ".update_policy_engine(",
    ".delete_policy_engine(",
    ".create_policy(",
    ".delete_policy(",
)

ALLOWED_IN_MIGRATION_MODULE: Tuple[str, ...] = (
    ".update_gateway_target(",
    ".update_policy(",
    ".update_gateway(",
)

# The single module permitted to perform the allowed writes.
MIGRATION_MODULE = "scripts/migrate_gateway_vocabulary.py"


@dataclass
class PreflightResult:
    """Outcome of the environment assertions, with every checked value shown."""

    ok: bool
    checks: Dict[str, Dict[str, object]] = field(default_factory=dict)

    def record(self, name: str, observed: object, expected: object) -> None:
        passed = observed == expected
        self.checks[name] = {
            "observed": observed,
            "expected": expected,
            "ok": passed,
        }
        if not passed:
            self.ok = False


def may_update_directly(key: str) -> bool:
    """True when a resource class may be changed by a direct control-plane call."""
    entry = MANIFEST.get(key)
    if entry is None:
        raise KeyError(f"{key!r} is not in the ownership manifest")
    return entry.direct_update
