"""Redacted, append-only model invocation receipts.

OpenTelemetry remains the model-call telemetry source. This module projects
only bounded metadata into Aurora so a governed turn can be replayed after the
in-memory exporter and CloudWatch query window are gone.

Prompt text, completion text, tool arguments, tool results, arbitrary span
attributes, and shopper phrasing are never accepted by the writer.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

_INSERT_SQL = """
    INSERT INTO pellier.model_invocation_receipts (
        invocation_key, turn_id, session_id, principal_sub,
        model_id, inference_profile_id, purpose,
        input_tokens, output_tokens, total_tokens, stop_reason,
        latency_ms, outcome, trace_id, span_id, source
    ) VALUES (
        %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    )
    ON CONFLICT (invocation_key) DO NOTHING
"""


def _text(attrs: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = attrs.get(key)
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized[:512]
    return None


def _non_negative_int(attrs: Dict[str, Any], *keys: str) -> Optional[int]:
    for key in keys:
        value = attrs.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            return parsed
    return None


def _model_id(attrs: Dict[str, Any], fallback: Optional[str]) -> Optional[str]:
    return _text(
        attrs,
        "gen_ai.response.model",
        "gen_ai.request.model",
        "llm.response.model",
        "llm.request.model",
        "aws.bedrock.model.id",
    ) or (str(fallback).strip()[:512] if fallback else None)


def _inference_profile_id(attrs: Dict[str, Any]) -> Optional[str]:
    value = _text(
        attrs,
        "aws.bedrock.inference_profile.id",
        "gen_ai.request.inference_profile",
    )
    model = _model_id(attrs, None)
    if value:
        return value
    if model and (
        model.startswith("global.")
        or model.startswith("us.")
        or ":inference-profile/" in model
    ):
        return model
    return None


def _purpose(span: Dict[str, Any]) -> str:
    attrs = span.get("attributes") if isinstance(span.get("attributes"), dict) else {}
    agent = _text(attrs, "gen_ai.agent.name")
    if agent:
        return f"agent:{agent}"[:160]
    name = str(span.get("name") or "").strip().lower()
    if "invoke_agent" in name:
        return "agent invocation"
    return "model invocation"


def _usage(span: Dict[str, Any]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    attrs = span.get("attributes") if isinstance(span.get("attributes"), dict) else {}
    input_tokens = _non_negative_int(
        attrs,
        "gen_ai.usage.prompt_tokens",
        "gen_ai.usage.input_tokens",
        "llm.usage.prompt_tokens",
        "llm.usage.input_tokens",
        "input_tokens",
    )
    output_tokens = _non_negative_int(
        attrs,
        "gen_ai.usage.completion_tokens",
        "gen_ai.usage.output_tokens",
        "llm.usage.completion_tokens",
        "llm.usage.output_tokens",
        "output_tokens",
    )
    total_tokens = _non_negative_int(
        attrs,
        "gen_ai.usage.total_tokens",
        "llm.usage.total_tokens",
        "total_tokens",
    )
    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    return input_tokens, output_tokens, total_tokens


def _is_model_span(span: Dict[str, Any]) -> bool:
    attrs = span.get("attributes") if isinstance(span.get("attributes"), dict) else {}
    input_tokens, output_tokens, total_tokens = _usage(span)
    has_usage = any(value is not None for value in (input_tokens, output_tokens, total_tokens))
    has_model = _model_id(attrs, None) is not None
    name = str(span.get("name") or "").lower()
    model_name = any(
        marker in name
        for marker in ("invoke_agent", "invoke_model", "converse", "chat")
    )
    return has_usage and (has_model or model_name)


def _outcome(span: Dict[str, Any]) -> str:
    attrs = span.get("attributes") if isinstance(span.get("attributes"), dict) else {}
    status_code = str(span.get("statusCode") or "").strip().lower()
    if status_code == "error" or any(
        attrs.get(key)
        for key in (
            "error.type",
            "exception.type",
            "gen_ai.response.error",
        )
    ):
        return "failed"
    return "succeeded"


def invocation_rows(
    *,
    turn_id: str,
    session_id: Optional[str],
    principal_sub: Optional[str],
    agent_execution: Optional[Dict[str, Any]],
    default_model_id: Optional[str],
    source: str,
) -> List[Dict[str, Any]]:
    """Return metadata-only invocation rows from a terminal execution payload."""
    execution = agent_execution if isinstance(agent_execution, dict) else {}
    spans = execution.get("spans")
    candidates = [
        dict(span)
        for span in (spans if isinstance(spans, list) else [])
        if isinstance(span, dict) and _is_model_span(span)
    ]
    rows: List[Dict[str, Any]] = []
    for index, span in enumerate(candidates):
        attrs = (
            span.get("attributes")
            if isinstance(span.get("attributes"), dict)
            else {}
        )
        input_tokens, output_tokens, total_tokens = _usage(span)
        trace_id = str(span.get("traceId") or execution.get("trace_id") or "").strip()
        span_id = str(span.get("spanId") or "").strip()
        key_material = {
            "turn_id": turn_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "name": str(span.get("name") or ""),
            "start_ms": span.get("startMs"),
            "index": index,
        }
        invocation_key = hashlib.sha256(
            json.dumps(key_material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        rows.append(
            {
                "invocation_key": invocation_key,
                "turn_id": turn_id,
                "session_id": session_id,
                "principal_sub": principal_sub,
                "model_id": _model_id(attrs, default_model_id),
                "inference_profile_id": _inference_profile_id(attrs),
                "purpose": _purpose(span),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "stop_reason": _text(
                    attrs,
                    "gen_ai.response.finish_reasons",
                    "gen_ai.response.stop_reason",
                    "llm.response.stop_reason",
                ),
                "latency_ms": _non_negative_int(
                    {"latency_ms": span.get("durationMs")},
                    "latency_ms",
                ),
                "outcome": _outcome(span),
                "trace_id": trace_id or None,
                "span_id": span_id or None,
                "source": "otel" if source == "otel" else source,
            }
        )

    if rows or not default_model_id:
        return rows

    trace = execution.get("managed_trace")
    if not isinstance(trace, dict):
        trace = {}
    trace_id = str(
        trace.get("traceId")
        or execution.get("trace_id")
        or ""
    ).strip()
    usage = execution.get("usage") if isinstance(execution.get("usage"), dict) else {}
    input_tokens = _non_negative_int(
        usage,
        "prompt_tokens",
        "input_tokens",
    )
    output_tokens = _non_negative_int(
        usage,
        "completion_tokens",
        "output_tokens",
    )
    total_tokens = _non_negative_int(usage, "total_tokens")
    invocation_key = hashlib.sha256(
        f"{turn_id}|summary|{trace_id}|{default_model_id}".encode()
    ).hexdigest()
    return [
        {
            "invocation_key": invocation_key,
            "turn_id": turn_id,
            "session_id": session_id,
            "principal_sub": principal_sub,
            "model_id": default_model_id,
            "inference_profile_id": (
                default_model_id
                if default_model_id.startswith(("global.", "us."))
                else None
            ),
            "purpose": "terminal agent response",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "stop_reason": None,
            "latency_ms": _non_negative_int(
                {"latency_ms": execution.get("total_duration_ms")},
                "latency_ms",
            ),
            "outcome": "succeeded",
            "trace_id": trace_id or None,
            "span_id": None,
            "source": "runtime-summary" if source == "otel" else source,
        }
    ]


async def persist_model_invocation_receipts(
    db: Any,
    *,
    turn_id: str,
    session_id: Optional[str],
    principal_sub: Optional[str],
    agent_execution: Optional[Dict[str, Any]],
    default_model_id: Optional[str] = None,
    source: str = "otel",
) -> List[Dict[str, Any]]:
    """Persist redacted invocation metadata and return the attempted rows."""
    if db is None:
        return []
    safe_source = (
        source
        if source in {"otel", "agentcore-service-telemetry", "runtime-summary"}
        else "runtime-summary"
    )
    rows = invocation_rows(
        turn_id=turn_id,
        session_id=session_id,
        principal_sub=principal_sub,
        agent_execution=agent_execution,
        default_model_id=default_model_id,
        source=safe_source,
    )
    for row in rows:
        try:
            await db.execute_query(
                _INSERT_SQL,
                row["invocation_key"],
                row["turn_id"],
                row["session_id"],
                row["principal_sub"],
                row["model_id"],
                row["inference_profile_id"],
                row["purpose"],
                row["input_tokens"],
                row["output_tokens"],
                row["total_tokens"],
                row["stop_reason"],
                row["latency_ms"],
                row["outcome"],
                row["trace_id"],
                row["span_id"],
                row["source"],
            )
        except Exception as exc:
            logger.warning("model invocation receipt insert failed: %s", exc)
    return rows
