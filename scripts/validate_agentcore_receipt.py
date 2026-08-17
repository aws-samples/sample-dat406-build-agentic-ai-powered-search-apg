#!/usr/bin/env python3
"""Validate the managed AgentCore readiness receipt emitted by the provisioner."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_CLI = "@aws/agentcore@0.26.0"
TRACE_ATTRIBUTE_ALLOWLISTS = {
    "agent_input": {
        "gen_ai.input.messages",
        "gen_ai.request.input",
        "gen_ai.prompt",
    },
    "agent_output": {
        "gen_ai.output.messages",
        "gen_ai.response.output",
        "gen_ai.completion",
    },
    "tool_input": {
        "gen_ai.tool.call.arguments",
        "gen_ai.tool.input",
        "gen_ai.tool.parameters",
    },
    "tool_output": {
        "gen_ai.tool.call.result",
        "gen_ai.tool.output",
        "gen_ai.tool.result",
    },
}


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
        "observability.transaction_search.destination": "CloudWatchLogs",
        "observability.transaction_search.status": "ACTIVE",
        "observability.control_plane_audit.source": "CloudTrail Event History",
        "observability.control_plane_audit.event_source": (
            "bedrock-agentcore.amazonaws.com"
        ),
        "observability.unified_trace.provenance": "agentcore-unified-telemetry",
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
        "observability.transaction_search.resource_policy",
        "observability.transaction_search.resource_policy_document",
        "observability.control_plane_audit.event_name",
        "observability.control_plane_audit.event_time",
        "observability.control_plane_audit.resource_type",
        "observability.runtime_log_group.name",
        "observability.runtime_log_group.kms_key_arn",
        "observability.trace_log_groups.kms_key_arn",
        "observability.unified_trace.trace_id",
        "observability.unified_trace.session_id",
        "observability.unified_trace.runtime_arn",
        "observability.unified_trace.runtime_log_group",
        "verification.runtime_invoke_smoke.session_id",
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
        "verification.transaction_search_ready",
        "verification.trace_log_groups_encrypted",
        "verification.trace_log_groups_retention_bounded",
        "verification.control_plane_audit_verified",
        "verification.runtime_log_group_encrypted",
        "verification.runtime_log_group_retention_bounded",
        "verification.unified_trace_delivered",
        "verification.unified_trace_agent_span",
        "verification.unified_trace_model_span",
        "verification.unified_trace_tool_span",
        "verification.unified_trace_agent_input",
        "verification.unified_trace_agent_output",
        "verification.unified_trace_tool_io_structured",
        "verification.unified_trace_tool_io_sanitized",
        "verification.unified_trace_step_latency",
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

    span_count = _value(payload, "observability.unified_trace.span_count")
    if type(span_count) is not int or span_count < 3:
        errors.append(
            "observability.unified_trace.span_count must include agent, model, and tool spans"
        )
    for path in (
        "observability.unified_trace.agent_span",
        "observability.unified_trace.model_span",
        "observability.unified_trace.tool_span",
        "observability.unified_trace.agent_input_observed",
        "observability.unified_trace.agent_output_observed",
        "observability.unified_trace.tool_input_output_observed",
        "observability.unified_trace.tool_input_output_structured",
        "observability.unified_trace.tool_input_output_sanitized",
        "observability.unified_trace.step_latency_observed",
    ):
        if _value(payload, path) is not True:
            errors.append(f"{path} must be true")

    attribute_contract = _value(
        payload, "observability.unified_trace.attribute_contract"
    )
    if not isinstance(attribute_contract, dict):
        errors.append(
            "observability.unified_trace.attribute_contract must be an object"
        )
    else:
        for role, allowed in TRACE_ATTRIBUTE_ALLOWLISTS.items():
            observed = attribute_contract.get(role)
            if observed not in allowed:
                errors.append(
                    "observability.unified_trace.attribute_contract."
                    f"{role}={observed!r} is not allowlisted"
                )

    retention_days = _value(payload, "observability.runtime_log_group.retention_days")
    if type(retention_days) is not int or retention_days <= 0:
        errors.append(
            "observability.runtime_log_group.retention_days must be a positive integer"
        )
    runtime_cleanup = _value(
        payload, "observability.runtime_log_group.cleanup"
    )
    if (
        not isinstance(runtime_cleanup, dict)
        or type(runtime_cleanup.get("created_by_workshop")) is not bool
        or runtime_cleanup.get("creation_pending") is True
    ):
        errors.append(
            "observability.runtime_log_group.cleanup must capture ownership"
        )

    trace_groups = _value(payload, "observability.trace_log_groups.groups")
    expected_trace_groups = {"aws/spans", "/aws/application-signals/data"}
    if not isinstance(trace_groups, list) or len(trace_groups) != 2:
        errors.append(
            "observability.trace_log_groups.groups must contain both trace destinations"
        )
    else:
        names = {
            group.get("name")
            for group in trace_groups
            if isinstance(group, dict)
        }
        if names != expected_trace_groups:
            errors.append(
                "observability.trace_log_groups.groups must contain "
                "aws/spans and /aws/application-signals/data"
            )
        expected_kms = _value(
            payload, "observability.trace_log_groups.kms_key_arn"
        )
        expected_retention = _value(
            payload, "observability.trace_log_groups.retention_days"
        )
        for group in trace_groups:
            if not isinstance(group, dict):
                continue
            if group.get("kms_key_arn") != expected_kms:
                errors.append(
                    f"trace log group {group.get('name')!r} must use the receipt KMS key"
                )
            if (
                type(group.get("retention_days")) is not int
                or group.get("retention_days") != expected_retention
                or group["retention_days"] <= 0
            ):
                errors.append(
                    f"trace log group {group.get('name')!r} must use bounded retention"
                )
            cleanup = group.get("cleanup")
            if (
                not isinstance(cleanup, dict)
                or type(cleanup.get("created_by_workshop")) is not bool
                or cleanup.get("creation_pending") is True
            ):
                errors.append(
                    f"trace log group {group.get('name')!r} must capture cleanup ownership"
                )

    transaction_cleanup = _value(
        payload, "observability.transaction_search.cleanup"
    )
    transaction_policy_document = _value(
        payload, "observability.transaction_search.resource_policy_document"
    )
    if isinstance(transaction_policy_document, str):
        try:
            parsed_policy = json.loads(transaction_policy_document)
        except json.JSONDecodeError:
            parsed_policy = None
        if not isinstance(parsed_policy, dict):
            errors.append(
                "observability.transaction_search.resource_policy_document "
                "must be a JSON object"
            )
    if not isinstance(transaction_cleanup, dict):
        errors.append(
            "observability.transaction_search.cleanup must capture prior state"
        )
    else:
        if type(transaction_cleanup.get("destination_changed")) is not bool:
            errors.append(
                "observability.transaction_search.cleanup.destination_changed "
                "must be boolean"
            )
        if transaction_cleanup.get("previous_destination") not in {
            "XRay",
            "CloudWatchLogs",
        }:
            errors.append(
                "observability.transaction_search.cleanup.previous_destination "
                "must be XRay or CloudWatchLogs"
            )
        if type(transaction_cleanup.get("resource_policy_created")) is not bool:
            errors.append(
                "observability.transaction_search.cleanup.resource_policy_created "
                "must be boolean"
            )

    step_latencies = _value(payload, "observability.unified_trace.step_latency_ms")
    if not isinstance(step_latencies, dict):
        errors.append(
            "observability.unified_trace.step_latency_ms must contain agent, model, and tool"
        )
    else:
        for kind in ("agent", "model", "tool"):
            latency = step_latencies.get(kind)
            if type(latency) is not int or latency < 0:
                errors.append(
                    "observability.unified_trace.step_latency_ms."
                    f"{kind} must be a non-negative integer"
                )

    for path in (
        "observability.unified_trace.span_names",
        "observability.unified_trace.model_ids",
        "observability.unified_trace.tool_names",
    ):
        values = _value(payload, path)
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(value, str) and value for value in values)
        ):
            errors.append(f"{path} must contain observed non-empty strings")

    trace_session = _value(payload, "observability.unified_trace.session_id")
    smoke_session = _value(payload, "verification.runtime_invoke_smoke.session_id")
    if trace_session != smoke_session:
        errors.append(
            "observability.unified_trace.session_id must match "
            "verification.runtime_invoke_smoke.session_id"
        )
    trace_runtime = _value(payload, "observability.unified_trace.runtime_arn")
    runtime_arn = _value(payload, "runtime.runtime_arn")
    if trace_runtime != runtime_arn:
        errors.append(
            "observability.unified_trace.runtime_arn must match runtime.runtime_arn"
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
