#!/usr/bin/env python3
"""Apply or reset the governed-workshop participant Cedar rule.

The shipped policy set is created by deploy_policy.py. This helper never edits
those baseline policies. It adds separately named participant policies and can
delete them again in one reset command.

The required ``identity_match`` rule forbids process_return when the authenticated JWT
  principal is not the customer the return is for. Gates on IDENTITY:
  AgentCore Policy exposes JWT claims as principal tags, so the rule compares
  ``principal.getTag("username")`` against ``context.input.customer_id``.

Usage:
    python3 scripts/deploy/workshop_policy_rule.py show
    python3 scripts/deploy/workshop_policy_rule.py --rule identity_match \
      --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
      --gateway-arn "$AGENTCORE_GATEWAY_ARN" \
      --cedar-file policies/workshop_identity_match_forbid.cedar \
      apply
    python3 scripts/deploy/workshop_policy_rule.py \
      --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" reset
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import boto3

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import deploy_policy  # noqa: E402


PARTICIPANT_POLICY_NAME = "workshop_identity_match_forbid"
PARTICIPANT_POLICY_DESCRIPTION = (
    "Workshop participant rule: forbid process_return when the JWT principal "
    "is not the customer the return is for"
)
# Reset also removes the retired exercise policy if an older environment has it.
PARTICIPANT_POLICY_NAMES = (
    PARTICIPANT_POLICY_NAME,
    "workshop_final_sale_forbid",
)
EXPERIENCE_TARGET = deploy_policy.EXPERIENCE_TARGET
IDENTITY_CLAIM_TAG = "username"


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


def _gateway_id(value: str | None, gateway_arn: str | None = None) -> str:
    resolved = (
        value
        or os.environ.get("AGENTCORE_GATEWAY_ID")
        or os.environ.get("GATEWAY_ID")
        or ""
    ).strip()
    if not resolved:
        # The gateway id is the last path segment of the gateway ARN
        # (arn:aws:bedrock-agentcore:...:gateway/<id>), so the ARN most
        # environments already carry is enough.
        arn = (
            gateway_arn
            or os.environ.get("AGENTCORE_GATEWAY_ARN")
            or os.environ.get("GATEWAY_ARN")
            or ""
        ).strip()
        if "/" in arn:
            resolved = arn.rsplit("/", 1)[1]
    if not resolved:
        raise SystemExit(
            "Missing gateway id. Pass --gateway-id or --gateway-arn, or set "
            "AGENTCORE_GATEWAY_ID / AGENTCORE_GATEWAY_ARN."
        )
    return resolved


def _candidate_actions(experience_target: str = EXPERIENCE_TARGET) -> list[str]:
    return [
        f"{experience_target}___process_return",
        f"{experience_target}__process_return",
    ]


def build_identity_match_forbid(
    *,
    gateway_arn: str,
    action_token: str,
    claim_tag: str = IDENTITY_CLAIM_TAG,
) -> str:
    """Return the identity-mismatch Cedar rule.

    AgentCore Policy creates an ``AgentCore::OAuthUser`` principal from the
    validated JWT and exposes token claims as principal tags. The Cognito
    ACCESS token carries the ``username`` claim (lowercase persona name), so
    the rule can compare token identity to the tool's ``customer_id`` input.

    Deliberately fail-open (hasTag guard inside ``when``): if this engine
    revision does not surface the claim tag, the forbid simply never fires
    and the room's happy path stays green. The fail-closed production shape
    is the ``unless`` variant documented in the solution Cedar file.
    """
    return (
        f'forbid(principal, action == AgentCore::Action::"{action_token}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}")\n'
        "when {\n"
        "  context.input has customer_id &&\n"
        f'  principal.hasTag("{claim_tag}") &&\n'
        f'  principal.getTag("{claim_tag}") != context.input.customer_id\n'
        "};"
    )


def _strip_line_comments(statement: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in statement.splitlines())


def _load_cedar_file(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        raise SystemExit(f"Cedar file not found: {path}")
    return path.read_text()


def _render_cedar_template(
    statement: str,
    *,
    gateway_arn: str,
    action_token: str,
) -> str:
    return (
        statement
        .replace("GATEWAY_ARN", gateway_arn)
        .replace("ACTION_TOKEN", action_token)
    )


def _validate_identity_cedar(statement: str, *, claim_tag: str) -> list[str]:
    """Static workshop validation for the identity-mismatch rule."""
    uncommented = _strip_line_comments(statement)
    compact = re.sub(r"\s+", " ", uncommented)
    errors: list[str] = []
    if "forbid(" not in uncommented:
        errors.append("expected a forbid(...) rule")
    if "AgentCore::Action::" not in uncommented:
        errors.append("expected AgentCore::Action in the action clause")
    if "AgentCore::Gateway::" not in uncommented:
        errors.append("expected AgentCore::Gateway in the resource clause")
    if not re.search(r"context\.input\s+has\s+customer_id", compact):
        errors.append("expected guard: context.input has customer_id")
    if f'principal.hasTag("{claim_tag}")' not in compact:
        errors.append(
            f'expected claim guard: principal.hasTag("{claim_tag}") – '
            "guard the tag before reading it"
        )
    if not re.search(
        rf'principal\.getTag\("{re.escape(claim_tag)}"\)\s*!=\s*context\.input\.customer_id',
        compact,
    ):
        errors.append(
            f'expected condition: principal.getTag("{claim_tag}") '
            "!= context.input.customer_id"
        )
    when_match = re.search(r"when\s*\{(?P<body>.*?)\}\s*;", uncommented, re.S)
    if when_match and re.search(r"\bfalse\b", when_match.group("body")):
        errors.append("replace the starter false predicate in the when block")
    return errors


def _rule_spec(args: argparse.Namespace) -> dict[str, Any]:
    claim_tag = getattr(args, "claim_tag", IDENTITY_CLAIM_TAG)
    return {
        "policy_name": PARTICIPANT_POLICY_NAME,
        "policy_description": PARTICIPANT_POLICY_DESCRIPTION,
        "build": lambda gateway_arn, action_token: build_identity_match_forbid(
            gateway_arn=gateway_arn,
            action_token=action_token,
            claim_tag=claim_tag,
        ),
        "validate": lambda statement: _validate_identity_cedar(
            statement, claim_tag=claim_tag
        ),
    }


def _participant_cedar_builder(
    *,
    cedar_file: str | None,
    gateway_arn: str,
    spec: dict[str, Any],
):
    template = _load_cedar_file(cedar_file)

    def cedar_builder(action_token: str) -> str:
        statement = (
            _render_cedar_template(
                template,
                gateway_arn=gateway_arn,
                action_token=action_token,
            )
            if template is not None
            else spec["build"](gateway_arn, action_token)
        )
        errors = spec["validate"](statement)
        if errors:
            raise SystemExit(
                "Cedar validation failed:\n"
                + "\n".join(f"  - {error}" for error in errors)
            )
        return statement

    return cedar_builder


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


def _participant_policies(
    client: Any, engine_id: str, names: tuple[str, ...] = PARTICIPANT_POLICY_NAMES
) -> list[dict[str, Any]]:
    return [
        policy
        for policy in _list_policies(client, engine_id)
        if policy.get("name") in names
    ]


def apply_rule(args: argparse.Namespace) -> int:
    region = args.region
    engine_id = _policy_engine_id(args.policy_engine_id)
    gateway_arn = _gateway_arn(args.gateway_arn)
    client = _client(region)
    spec = _rule_spec(args)
    cedar_builder = _participant_cedar_builder(
        cedar_file=args.cedar_file,
        gateway_arn=gateway_arn,
        spec=spec,
    )
    # Validate the participant-authored file before checking idempotency so an
    # existing policy does not hide a broken local edit.
    cedar_builder(_candidate_actions(args.experience_target)[0])

    existing = [
        policy
        for policy in _participant_policies(
            client, engine_id, names=(spec["policy_name"],)
        )
        if policy.get("status") not in ("CREATE_FAILED", "FAILED")
    ]
    if existing:
        policy_id = existing[0]["policyId"]
        print(f"Participant policy already present: {policy_id}")
        print(f"POLICY_ID={policy_id}")
        return 0

    policy_id, accepted_action = deploy_policy.create_action_policy_with_fallback(
        client,
        engine_id,
        spec["policy_name"],
        spec["policy_description"],
        cedar_builder,
        _candidate_actions(args.experience_target),
    )

    print(f"Participant rule applied: {spec['policy_name']}")
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
        print("No participant policy found; shipped state already restored.")
        return 0

    deleted = 0
    for policy in policies:
        policy_id = policy.get("policyId")
        if not policy_id:
            continue
        client.delete_policy(policyEngineId=engine_id, policyId=policy_id)
        deleted += 1
        print(f"Deleted participant policy {policy.get('name')} ({policy_id})")

    print(f"Reset complete. Removed {deleted} participant policy/policies.")
    return 0


def show_rule(args: argparse.Namespace) -> int:
    gateway_arn = args.gateway_arn or os.environ.get("AGENTCORE_GATEWAY_ARN") or "GATEWAY_ARN"
    action_token = _candidate_actions(args.experience_target)[0]
    cedar_builder = _participant_cedar_builder(
        cedar_file=args.cedar_file,
        gateway_arn=gateway_arn,
        spec=_rule_spec(args),
    )
    print(cedar_builder(action_token))
    return 0


def set_mode(args: argparse.Namespace) -> int:
    """Re-attach the policy engine to the gateway in LOG_ONLY or ENFORCE mode.

    LOG_ONLY evaluates every Cedar policy and traces the would-be decision but
    never blocks the call – the standard staging step before flipping a new
    rule to ENFORCE in production. deploy_policy.attach_engine_to_gateway
    already carries the mode; this subcommand just makes the flip a
    one-liner for the workshop room.

    LOG_ONLY and ENFORCE are the only two values the GatewayPolicyEngineMode
    enum accepts; anything else fails client-side in botocore validation.
    """
    region = args.region
    engine_id = _policy_engine_id(args.policy_engine_id)
    gateway_id = _gateway_id(
        getattr(args, "gateway_id", None), gateway_arn=args.gateway_arn
    )
    mode = args.set.upper()
    client = _client(region)

    engine = client.get_policy_engine(policyEngineId=engine_id)
    engine_arn = engine["policyEngineArn"]

    # No-op when the gateway already reports the requested mode with this
    # engine: update_gateway is a full-replace call that briefly flips the
    # gateway to UPDATING, and the facilitator reset runs this on every pass.
    current = client.get_gateway(gatewayIdentifier=gateway_id)
    current_config = current.get("policyEngineConfiguration") or {}
    if (
        current_config.get("mode") == mode
        and current_config.get("arn") == engine_arn
        and current.get("status") not in ("UPDATING",)
    ):
        print(f"Gateway already in {mode} mode; nothing to do.")
        print(f"GATEWAY_POLICY_MODE={mode}")
        return 0

    deploy_policy.attach_engine_to_gateway(client, gateway_id, engine_arn, mode=mode)

    # update_gateway is asynchronous; read the mode back so the room gets a
    # confirmed state, not an optimistic print.
    for _ in range(18):
        gw = client.get_gateway(gatewayIdentifier=gateway_id)
        config = gw.get("policyEngineConfiguration") or {}
        status = gw.get("status", "UNKNOWN")
        if config.get("mode") == mode and status not in ("UPDATING",):
            print(f"GATEWAY_POLICY_MODE={config.get('mode')}")
            return 0
        time.sleep(10)
    print(f"Warning: gateway did not report mode {mode} yet; "
          "check get_gateway policyEngineConfiguration.")
    return 1


def validate_rule(args: argparse.Namespace) -> int:
    gateway_arn = args.gateway_arn or os.environ.get("AGENTCORE_GATEWAY_ARN") or "GATEWAY_ARN"
    action_token = _candidate_actions(args.experience_target)[0]
    cedar_builder = _participant_cedar_builder(
        cedar_file=args.cedar_file,
        gateway_arn=gateway_arn,
        spec=_rule_spec(args),
    )
    cedar = cedar_builder(action_token)
    print("Cedar file passed workshop validation.")
    print()
    print(cedar)
    return 0


def main() -> int:
    def add_common_flags(target: argparse.ArgumentParser, *, suppress_defaults: bool) -> None:
        default = argparse.SUPPRESS if suppress_defaults else None
        target.add_argument(
            "--region",
            default=argparse.SUPPRESS if suppress_defaults else _region(),
            help="AWS region for bedrock-agentcore-control (default: env or us-east-1)",
        )
        target.add_argument(
            "--policy-engine-id",
            default=default,
            help="AgentCore Policy Engine id (default: AGENTCORE_POLICY_ENGINE_ID)",
        )
        target.add_argument(
            "--gateway-arn",
            default=default,
            help="AgentCore Gateway ARN (required for apply; default: AGENTCORE_GATEWAY_ARN)",
        )
        target.add_argument(
            "--experience-target",
            default=argparse.SUPPRESS if suppress_defaults else EXPERIENCE_TARGET,
            help="Gateway target name that owns process_return.",
        )
        target.add_argument(
            "--rule",
            choices=("identity_match",),
            default=argparse.SUPPRESS if suppress_defaults else "identity_match",
            help="Identity-aware participant rule used by Lab 4.",
        )
        target.add_argument(
            "--claim-tag",
            default=argparse.SUPPRESS if suppress_defaults else IDENTITY_CLAIM_TAG,
            help=(
                "JWT claim tag the identity_match rule reads from the "
                "principal (Cognito access tokens carry 'username')."
            ),
        )
        target.add_argument(
            "--cedar-file",
            default=default,
            help=(
                "Participant-authored Cedar file. ACTION_TOKEN and GATEWAY_ARN "
                "placeholders are replaced before validation/apply."
            ),
        )

    parser = argparse.ArgumentParser(
        description="Apply/reset the Pellier governed workshop Cedar rule."
    )
    add_common_flags(parser, suppress_defaults=False)
    sub = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("show", "Print the Cedar rule shape."),
        ("validate", "Validate the participant Cedar file locally."),
        ("apply", "Create/reuse the participant forbid policy."),
        ("reset", "Delete the participant forbid policy."),
    ):
        child = sub.add_parser(command, help=help_text)
        add_common_flags(child, suppress_defaults=True)

    mode_parser = sub.add_parser(
        "mode",
        help="Flip the gateway's policy engine between LOG_ONLY and ENFORCE.",
    )
    add_common_flags(mode_parser, suppress_defaults=True)
    mode_parser.add_argument(
        "--set",
        required=True,
        choices=("LOG_ONLY", "ENFORCE", "log_only", "enforce"),
        help="LOG_ONLY traces would-be decisions without blocking; ENFORCE blocks.",
    )
    mode_parser.add_argument(
        "--gateway-id",
        default=argparse.SUPPRESS,
        help="AgentCore Gateway id (default: AGENTCORE_GATEWAY_ID, or "
             "derived from AGENTCORE_GATEWAY_ARN).",
    )

    args = parser.parse_args()
    if args.command == "show":
        return show_rule(args)
    if args.command == "validate":
        return validate_rule(args)
    if args.command == "apply":
        return apply_rule(args)
    if args.command == "reset":
        return reset_rule(args)
    if args.command == "mode":
        return set_mode(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
