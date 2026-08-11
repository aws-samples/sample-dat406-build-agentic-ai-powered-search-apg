#!/usr/bin/env python3
"""Validate the managed AgentCore readiness receipt emitted by the provisioner."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_CLI = "@aws/agentcore@0.26.0"


def _value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def validate_receipt(payload: dict[str, Any]) -> list[str]:
    """Return human-readable contract violations; an empty list means ready."""
    errors: list[str] = []

    expected_values = {
        "status": "ready",
        "cli.package": EXPECTED_CLI,
        "policy.mode": "ENFORCE",
        "verification.gateway_control_plane.policy_mode": "ENFORCE",
        "memory.seed.status": "ready",
        "verification.runtime_invoke_smoke.rail": "gateway-mcp",
    }
    for path, expected in expected_values.items():
        actual = _value(payload, path)
        if actual != expected:
            errors.append(f"{path}={actual!r}, expected {expected!r}")

    for path in (
        "runtime.runtime_arn",
        "memory.memory_id",
        "gateway.gateway_id",
        "gateway.gateway_arn",
        "gateway.gateway_url",
        "policy.policy_engine_id",
        "verification.runtime_invoke_smoke.response_preview",
    ):
        actual = _value(payload, path)
        if not isinstance(actual, str) or not actual.strip():
            errors.append(f"{path} must be a non-empty string")

    for path in (
        "verification.targets_attached",
        "verification.gateway_tools_discovered",
        "verification.memory_seeded",
        "verification.live_policy_allow",
        "verification.live_policy_deny",
        "verification.authenticated_runtime_invoke_smoke",
    ):
        if _value(payload, path) is not True:
            errors.append(f"{path} must be true")

    expected_counts = {
        "verification.local_tool_schema.count": 15,
        "verification.gateway_control_plane.target_count": 4,
        "verification.gateway_tool_count": 15,
    }
    for path, expected in expected_counts.items():
        actual = _value(payload, path)
        if type(actual) is not int or actual != expected:
            errors.append(f"{path}={actual!r}, expected {expected}")

    expected_lists = {
        "verification.local_tool_schema.canonical_names": 15,
        "verification.gateway_control_plane.target_names": 4,
        "verification.gateway_tool_names": 15,
        "verification.gateway_prefixed_tool_names": 15,
    }
    for path, expected_length in expected_lists.items():
        actual = _value(payload, path)
        if (
            not isinstance(actual, list)
            or len(actual) != expected_length
            or len(set(actual)) != expected_length
        ):
            errors.append(
                f"{path} must contain {expected_length} unique entries"
            )

    prefixed_names = _value(payload, "verification.gateway_prefixed_tool_names")
    if isinstance(prefixed_names, list) and not all(
        isinstance(name, str) and "__" in name for name in prefixed_names
    ):
        errors.append(
            "verification.gateway_prefixed_tool_names must contain target-prefixed names"
        )

    allow = _value(payload, "verification.live_policy_proof.allow")
    if not isinstance(allow, dict) or allow.get("outcome") != "allow":
        errors.append("verification.live_policy_proof.allow must prove ALLOW")
    elif allow.get("tool_audit_row_after_call") is None:
        errors.append("Policy ALLOW must include an execution audit row")

    deny = _value(payload, "verification.live_policy_proof.deny")
    if not isinstance(deny, dict) or deny.get("outcome") != "deny":
        errors.append("verification.live_policy_proof.deny must prove DENY")
    elif (
        deny.get("cedar_denial") is not True
        or "tool_audit_row_after_call" not in deny
        or deny["tool_audit_row_after_call"] is not None
    ):
        errors.append("Policy DENY must be Cedar-specific and pre-execution")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} RECEIPT.json", file=sys.stderr)
        return 2

    receipt_path = Path(sys.argv[1])
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read receipt: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("receipt root must be a JSON object", file=sys.stderr)
        return 1

    errors = validate_receipt(payload)
    if errors:
        print("; ".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
