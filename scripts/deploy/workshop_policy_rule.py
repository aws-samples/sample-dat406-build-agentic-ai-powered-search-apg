#!/usr/bin/env python3
"""Apply or reset the governed-workshop participant Cedar rule.

The shipped policy set is created by deploy_policy.py. This helper never edits
those baseline policies. It adds one separately named participant policy and
can delete that policy again in one reset command.

Usage:
    python3 scripts/deploy/workshop_policy_rule.py show
    python3 scripts/deploy/workshop_policy_rule.py apply \
      --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
      --gateway-arn "$AGENTCORE_GATEWAY_ARN"
    python3 scripts/deploy/workshop_policy_rule.py reset \
      --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import boto3

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import deploy_policy  # noqa: E402


PARTICIPANT_POLICY_NAME = "workshop_final_sale_forbid"
PARTICIPANT_POLICY_DESCRIPTION = (
    "Workshop participant rule: forbid process_return for final-sale product 37"
)
EXPERIENCE_TARGET = deploy_policy.EXPERIENCE_TARGET
FINAL_SALE_PRODUCT_ID = 37


def _region(default: str = "us-east-1") -> str:
    return (
        os.environ.get("AWS_DEFAULT_REGION")
        or os.environ.get("AWS_REGION")
        or default
    )


def _client(region: str):
    return boto3.client("bedrock-agentcore-control", region_name=region)


def _policy_engine_id(value: str | None) -> str:
    resolved = (
        value
        or os.environ.get("AGENTCORE_POLICY_ENGINE_ID")
        or os.environ.get("POLICY_ENGINE_ID")
        or ""
    ).strip()
    if not resolved:
        raise SystemExit(
            "Missing policy engine id. Pass --policy-engine-id or set "
            "AGENTCORE_POLICY_ENGINE_ID."
        )
    return resolved


def _gateway_arn(value: str | None) -> str:
    resolved = (
        value
        or os.environ.get("AGENTCORE_GATEWAY_ARN")
        or os.environ.get("GATEWAY_ARN")
        or ""
    ).strip()
    if not resolved:
        raise SystemExit(
            "Missing gateway ARN. Pass --gateway-arn or set AGENTCORE_GATEWAY_ARN."
        )
    return resolved


def _candidate_actions(experience_target: str = EXPERIENCE_TARGET) -> list[str]:
    return [
        f"{experience_target}___process_return",
        f"{experience_target}__process_return",
    ]


def build_final_sale_forbid(
    *,
    gateway_arn: str,
    action_token: str,
    product_id: int = FINAL_SALE_PRODUCT_ID,
) -> str:
    """Return the participant Cedar rule for one final-sale product."""
    return (
        f'forbid(principal, action == AgentCore::Action::"{action_token}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}")\n'
        "when {\n"
        "  context.input has product_id &&\n"
        f"  context.input.product_id == {int(product_id)}\n"
        "};"
    )


def _list_policies(client: Any, engine_id: str) -> list[dict[str, Any]]:
    token = None
    policies: list[dict[str, Any]] = []
    while True:
        kwargs: dict[str, Any] = {"policyEngineId": engine_id}
        if token:
            kwargs["nextToken"] = token
        page = client.list_policies(**kwargs)
        policies.extend(page.get("policies", []))
        token = page.get("nextToken")
        if not token:
            return policies


def _participant_policies(client: Any, engine_id: str) -> list[dict[str, Any]]:
    return [
        policy
        for policy in _list_policies(client, engine_id)
        if policy.get("name") == PARTICIPANT_POLICY_NAME
    ]


def apply_rule(args: argparse.Namespace) -> int:
    region = args.region
    engine_id = _policy_engine_id(args.policy_engine_id)
    gateway_arn = _gateway_arn(args.gateway_arn)
    client = _client(region)

    existing = [
        policy for policy in _participant_policies(client, engine_id)
        if policy.get("status") not in ("CREATE_FAILED", "FAILED")
    ]
    if existing:
        policy_id = existing[0]["policyId"]
        print(f"Participant policy already present: {policy_id}")
        print(f"POLICY_ID={policy_id}")
        return 0

    def cedar_builder(action_token: str) -> str:
        return build_final_sale_forbid(
            gateway_arn=gateway_arn,
            action_token=action_token,
            product_id=args.product_id,
        )

    policy_id, accepted_action = deploy_policy.create_action_policy_with_fallback(
        client,
        engine_id,
        PARTICIPANT_POLICY_NAME,
        PARTICIPANT_POLICY_DESCRIPTION,
        cedar_builder,
        _candidate_actions(args.experience_target),
    )

    print("Participant final-sale forbid applied.")
    if accepted_action:
        print(f"ACTION_TOKEN={accepted_action}")
    print(f"POLICY_ID={policy_id}")
    return 0


def reset_rule(args: argparse.Namespace) -> int:
    region = args.region
    engine_id = _policy_engine_id(args.policy_engine_id)
    client = _client(region)
    policies = _participant_policies(client, engine_id)
    if not policies:
        print("No participant final-sale policy found; shipped state already restored.")
        return 0

    deleted = 0
    for policy in policies:
        policy_id = policy.get("policyId")
        if not policy_id:
            continue
        client.delete_policy(policyEngineId=engine_id, policyId=policy_id)
        deleted += 1
        print(f"Deleted participant policy {policy_id}")

    print(f"Reset complete. Removed {deleted} participant policy/policies.")
    return 0


def show_rule(args: argparse.Namespace) -> int:
    gateway_arn = args.gateway_arn or os.environ.get("AGENTCORE_GATEWAY_ARN") or "GATEWAY_ARN"
    action_token = _candidate_actions(args.experience_target)[0]
    print(build_final_sale_forbid(
        gateway_arn=gateway_arn,
        action_token=action_token,
        product_id=args.product_id,
    ))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply/reset the Pellier governed workshop Cedar rule."
    )
    parser.add_argument(
        "--region",
        default=_region(),
        help="AWS region for bedrock-agentcore-control (default: env or us-east-1)",
    )
    parser.add_argument(
        "--policy-engine-id",
        default=None,
        help="AgentCore Policy Engine id (default: AGENTCORE_POLICY_ENGINE_ID)",
    )
    parser.add_argument(
        "--gateway-arn",
        default=None,
        help="AgentCore Gateway ARN (required for apply; default: AGENTCORE_GATEWAY_ARN)",
    )
    parser.add_argument(
        "--experience-target",
        default=EXPERIENCE_TARGET,
        help="Gateway target name that owns process_return.",
    )
    parser.add_argument(
        "--product-id",
        type=int,
        default=FINAL_SALE_PRODUCT_ID,
        help="Final-sale productId to forbid through process_return.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show", help="Print the Cedar rule shape.")
    sub.add_parser("apply", help="Create/reuse the participant forbid policy.")
    sub.add_parser("reset", help="Delete the participant forbid policy.")

    args = parser.parse_args()
    if args.command == "show":
        return show_rule(args)
    if args.command == "apply":
        return apply_rule(args)
    if args.command == "reset":
        return reset_rule(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
