"""Observed AgentCore Policy decisions, from where the service actually reports them.

Pellier's policy gate is the managed AgentCore Policy engine attached to the
Gateway. This module answers one question about a governed call: what did that
engine decide, and how do we know? Five states, and only real events may claim
the first three:

    ALLOW / DENY            an enforced decision the engine reported
    WOULD_DENY              a real LOG_ONLY deny event: a policy in LOG_ONLY
                            matched and would have flipped the decision
    EVALUATION_INCOMPLETE   telemetry unreadable, absent in the window, or
                            missing the fields a decision needs
    POLICY_INFERRED         the Cedar text names the action. That is a fact
                            about policy text, not a decision about a call

Sources, in the order they are consulted:

    governed-receipt    the Gateway's own response to the call (supplied by the
                        caller as ``prior``): a deny marker, or a call that
                        returned under an enforcing gateway
    gateway-span        the gateway's policy-evaluation spans in the CloudWatch
                        Transaction Search log group (default ``aws/spans``),
                        read with Logs Insights
    cloudwatch-metric   ``LogOnlyMatches``, ``LogOnlyDecisionFlips`` and
                        ``LogOnlyEvalIncomplete`` in ``AWS/Bedrock-AgentCore``
    policy-text         the substring scan of each policy's Cedar statement

Span attribute names are not documented, so the span reader is schema-tolerant:
it looks for decision, flip, mode and policy fields by name fragments and always
persists the raw document beside its reading. LOG_ONLY outcomes never change the
enforced decision, which is why a WOULD_DENY row can coexist with an ALLOW row
for the same call, and why ``flip_of`` links the two.

Every observation is persisted to ``pellier.policy_decisions`` (migration 048),
which is append-only. The caller reads the terminal state for its receipt.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

POLICY_STATES = ("ALLOW", "DENY", "WOULD_DENY", "EVALUATION_INCOMPLETE", "POLICY_INFERRED")

STATE_ALLOW = "ALLOW"
STATE_DENY = "DENY"
STATE_WOULD_DENY = "WOULD_DENY"
STATE_EVALUATION_INCOMPLETE = "EVALUATION_INCOMPLETE"
STATE_POLICY_INFERRED = "POLICY_INFERRED"

# States that are decisions. Only these participate in flip detection.
TERMINAL_STATES = (STATE_ALLOW, STATE_DENY, STATE_WOULD_DENY)

SOURCE_SPAN = "gateway-span"
SOURCE_METRIC = "cloudwatch-metric"
SOURCE_RECEIPT = "governed-receipt"
SOURCE_TEXT = "policy-text"

METRIC_NAMESPACE = "AWS/Bedrock-AgentCore"
METRIC_MATCHES = "LogOnlyMatches"
METRIC_FLIPS = "LogOnlyDecisionFlips"
METRIC_INCOMPLETE = "LogOnlyEvalIncomplete"
LOG_ONLY_METRICS = (METRIC_MATCHES, METRIC_FLIPS, METRIC_INCOMPLETE)

DEFAULT_SPAN_LOG_GROUP = "aws/spans"
_SPAN_LOG_GROUP_SETTING = "AGENTCORE_POLICY_SPAN_LOG_GROUP"

# The strongest reading wins when one call produced several observations.
_STATE_RANK = {
    STATE_DENY: 4,
    STATE_WOULD_DENY: 3,
    STATE_ALLOW: 2,
    STATE_POLICY_INFERRED: 1,
    STATE_EVALUATION_INCOMPLETE: 0,
}

# CloudWatch metrics are aggregated per minute, and a turn's window is seconds
# wide, so the window is padded to cover the two minute-buckets a turn can fall
# across. The consequence is stated wherever a metric reading is reported: a
# WOULD_DENY read from a metric is minute-granular, and it can belong to another
# execution of the same action in the same minute.
_METRIC_WINDOW_PAD = timedelta(seconds=60)

# Bounds on the telemetry read. Every AWS call in this module runs on the
# operator's request path AFTER the write has already executed, so a slow
# CloudWatch must cost the reading and not the response: botocore's defaults
# (60-second reads, four retries) would hold an Execute request open for
# minutes. A missing reading is EVALUATION_INCOMPLETE, which is a worse receipt
# but an honest one.
_AWS_CONNECT_TIMEOUT_S = 3.0
_AWS_READ_TIMEOUT_S = 8.0
_AWS_MAX_ATTEMPTS = 2
_METRIC_DEADLINE_S = 20.0
_STOP_QUERY_TIMEOUT_S = 3.0
_DISCOVERY_PAGE_LIMIT = 5


@dataclass(frozen=True)
class PolicyObservation:
    """One reading of the policy engine's behaviour for one action."""

    state: str
    source: str
    action_id: str
    policy_id: Optional[str]
    policy_name: Optional[str]
    policy_mode: Optional[str]
    engine_mode: Optional[str]
    principal_id: Optional[str]
    resource: Optional[str]
    observed_at: datetime
    raw: Dict[str, Any]


def terminal_state(states: Iterable[str]) -> str:
    """The single state a receipt records when several observations exist.

    DENY outranks WOULD_DENY, which outranks ALLOW; both inferred and incomplete
    readings lose to any real decision. No observation at all is
    EVALUATION_INCOMPLETE, never ALLOW.
    """
    best = STATE_EVALUATION_INCOMPLETE
    for state in states:
        if _STATE_RANK.get(state, -1) > _STATE_RANK[best]:
            best = state
    return best


def span_log_group() -> str:
    """The Transaction Search log group, from settings, the environment, or the default."""
    try:
        from config import settings

        configured = str(getattr(settings, _SPAN_LOG_GROUP_SETTING, "") or "").strip()
        if configured:
            return configured
    except Exception:  # pragma: no cover - stripped-env import path
        pass
    return os.environ.get(_SPAN_LOG_GROUP_SETTING, "").strip() or DEFAULT_SPAN_LOG_GROUP


# ---------------------------------------------------------------------------
# Source 1: gateway policy-evaluation spans
# ---------------------------------------------------------------------------


def _epoch(moment: datetime) -> int:
    return int(moment.timestamp())


def _insights_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _span_query(action_id: str, engine_id: str, trace_id: Optional[str]) -> str:
    clauses = [f'@message like "{_insights_literal(action_id)}"']
    if engine_id:
        clauses.append(f'@message like "{_insights_literal(engine_id)}"')
    if trace_id:
        clauses.append(f'@message like "{_insights_literal(trace_id)}"')
    return (
        "fields @timestamp, @message | filter "
        + " and ".join(clauses)
        + " | sort @timestamp desc | limit 100"
    )


async def _stop_query(logs_client: Any, query_id: str) -> None:
    """Best effort cancel. An abandoned query holds an account concurrency slot."""
    stop = getattr(logs_client, "stop_query", None)
    if stop is None:
        return
    try:
        await asyncio.wait_for(
            asyncio.to_thread(stop, queryId=query_id), timeout=_STOP_QUERY_TIMEOUT_S
        )
    except Exception:  # noqa: BLE001 - cancelling a query is never worth an error
        logger.debug("could not stop Logs Insights query %s", query_id, exc_info=True)


async def _await_query(
    logs_client: Any, query_id: str, poll_interval_s: float, timeout_s: float
) -> List[Dict[str, str]]:
    """Poll one Logs Insights query to completion within a bounded window.

    The deadline bounds each individual poll, not only the gap between polls: a
    ``get_query_results`` that never answers is exactly the failure this
    function exists to survive. A query still running at the deadline is
    stopped before the timeout is raised.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            await _stop_query(logs_client, query_id)
            raise TimeoutError("Logs Insights query did not complete in the polling window")
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(logs_client.get_query_results, queryId=query_id),
                timeout=remaining,
            )
        except TimeoutError:
            await _stop_query(logs_client, query_id)
            raise TimeoutError(
                "Logs Insights query did not complete in the polling window"
            ) from None
        status = str(response.get("status") or "")
        if status == "Complete":
            return [
                {f["field"]: f["value"] for f in row if f.get("field") != "@ptr"}
                for row in response.get("results", [])
            ]
        if status in {"Failed", "Cancelled", "Timeout", "Unknown"}:
            raise RuntimeError(f"Logs Insights query {status.lower()}")
        await asyncio.sleep(poll_interval_s)


def _unwrap_otlp(value: Any) -> Any:
    """OTLP JSON wraps scalars as {"stringValue": ...}; return the scalar."""
    if isinstance(value, Mapping) and len(value) == 1:
        key = next(iter(value))
        if str(key).endswith("Value"):
            inner = value[key]
            if isinstance(inner, Mapping) and "values" in inner:
                return [_unwrap_otlp(v) for v in inner.get("values", [])]
            return inner
    return value


def _flatten_attribute_block(block: Any) -> Dict[str, Any]:
    """One attribute block as a flat mapping, in either JSON shape."""
    if isinstance(block, Mapping):
        return {str(k): _unwrap_otlp(v) for k, v in block.items()}
    if isinstance(block, list):
        return {
            str(item["key"]): _unwrap_otlp(item.get("value"))
            for item in block
            if isinstance(item, Mapping) and "key" in item
        }
    return {}


def _span_attributes(doc: Mapping[str, Any]) -> Dict[str, Any]:
    """Flatten a span document's attributes, tolerating both JSON shapes.

    Accepts a plain mapping and the OTLP list form (``[{"key", "value"}]``), and
    folds resource attributes in beneath the span's own so a span-level field
    always wins.
    """
    resource = doc.get("resource")
    resource_block = resource.get("attributes") if isinstance(resource, Mapping) else None
    merged = _flatten_attribute_block(resource_block)
    merged.update(_flatten_attribute_block(doc.get("attributes")))
    return merged


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    text = str(value).strip().lower()
    if text in {"true", "yes"}:
        return True
    try:
        return float(text) > 0
    except ValueError:
        return False


def _as_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    text = str(value).strip()
    if text.startswith("["):
        try:
            return [str(v) for v in json.loads(text)]
        except ValueError:
            pass
    return [text] if text else []


def _decision_from_text(text: str) -> Optional[str]:
    """A decision-shaped attribute value as a state, or None when it says neither."""
    if "deny" in text or "forbid" in text:
        return STATE_DENY
    if "allow" in text or "permit" in text:
        return STATE_ALLOW
    if "incomplete" in text or "partial" in text:
        return STATE_EVALUATION_INCOMPLETE
    return None


def _is_engine_scoped(key: str) -> bool:
    """Whether an attribute name is about the engine rather than one policy."""
    return "engine" in key or "gateway" in key or "enforcement" in key


_DECISION_WORDS = ("decision", "effect", "outcome", "verdict")
_POLICY_ID_WORDS = ("policy_id", "policyid")
_POLICY_MODES = frozenset({"ACTIVE", "LOG_ONLY"})
_ENGINE_MODES = frozenset({"ENFORCE", "LOG_ONLY"})


def _names_a_decision(key: str) -> bool:
    """Whether an attribute name looks like it carries the evaluation's outcome."""
    return any(word in key for word in _DECISION_WORDS)


def _apply_decision(info: Dict[str, Any], text: str) -> None:
    """Record what a decision-shaped value said, including saying nothing."""
    decided = _decision_from_text(text)
    if decided == STATE_EVALUATION_INCOMPLETE:
        info["incomplete"] = True
    elif decided is not None:
        info["decision"] = decided


def _read_decision_field(info: Dict[str, Any], key: str, value: Any, text: str) -> None:
    """Fold one decision, flip or incompleteness signal into the reading."""
    if "incomplete" in key:
        info["incomplete"] = info["incomplete"] or _truthy(value)
    elif "flip" in key:
        info["flip"] = info["flip"] or _truthy(value)
    elif _names_a_decision(key):
        _apply_decision(info, text)


def _read_log_only_matches(info: Dict[str, Any], key: str, value: Any) -> None:
    """Collect the policies a LOG_ONLY evaluation reported as matching."""
    is_log_only = "log_only" in key or "logonly" in key
    if is_log_only and ("match" in key or "polic" in key):
        info["log_only_policies"] = info["log_only_policies"] + _as_list(value)


def _policy_field_slot(key: str, text: str) -> Optional[str]:
    """Which reading slot a policy-scoped attribute name fills, if any."""
    if key.endswith("id") or any(word in key for word in _POLICY_ID_WORDS):
        return "policy_id"
    if "name" in key:
        return "policy_name"
    if "mode" in key and text.upper() in _POLICY_MODES:
        return "policy_mode"
    return None


def _read_policy_identity(info: Dict[str, Any], key: str, value: Any, text: str) -> None:
    """Fold one policy-scoped identity or mode signal into the reading."""
    if "polic" not in key or _is_engine_scoped(key):
        return
    slot = _policy_field_slot(key, text)
    if slot == "policy_mode":
        info["policy_mode"] = text.upper()
    elif slot is not None:
        info[slot] = info[slot] or str(value)


def _read_policy_field(info: Dict[str, Any], key: str, value: Any, text: str) -> None:
    """Fold one policy or engine mode signal into the reading."""
    _read_log_only_matches(info, key, value)
    _read_policy_identity(info, key, value, text)
    if _is_engine_scoped(key) and "mode" in key and text.upper() in _ENGINE_MODES:
        info["engine_mode"] = text.upper()


def _read_subject_field(info: Dict[str, Any], key: str, value: Any) -> None:
    """Fold the principal and resource names into the reading."""
    if "principal" in key and info["principal"] is None:
        info["principal"] = str(value)
    if "resource" in key and info["resource"] is None:
        info["resource"] = str(value)


def _classify_span_attributes(attrs: Mapping[str, Any]) -> Dict[str, Any]:
    """Read decision-shaped fields out of undocumented attribute names.

    Every reader is name-fragment based and additive, because the attribute
    vocabulary is not published: an unrecognized key simply contributes nothing,
    and the raw document is persisted regardless.
    """
    info: Dict[str, Any] = {
        "decision": None, "flip": False, "incomplete": False, "policy_id": None,
        "policy_name": None, "policy_mode": None, "engine_mode": None,
        "principal": None, "resource": None, "log_only_policies": [],
    }
    for raw_key, value in attrs.items():
        key = str(raw_key).lower()
        text = str(value).strip().lower()
        _read_decision_field(info, key, value, text)
        _read_policy_field(info, key, value, text)
        _read_subject_field(info, key, value)
    return info


def _span_observed_at(doc: Mapping[str, Any], row: Mapping[str, str]) -> datetime:
    for key in ("startTimeUnixNano", "start_time_unix_nano", "endTimeUnixNano"):
        value = doc.get(key)
        if value:
            try:
                return datetime.fromtimestamp(int(value) / 1e9, tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
    stamp = row.get("@timestamp")
    if stamp:
        try:
            return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _mentions(blob: str, action_id: str, engine_id: str) -> bool:
    lowered = blob.lower()
    if action_id.lower() not in lowered:
        return False
    return not engine_id or engine_id.lower() in lowered


def _span_state(info: Mapping[str, Any]) -> Tuple[str, Optional[str], Optional[str]]:
    """The state a span reading resolves to, with the policy it implicates.

    Returns:
        ``(state, policy_id, policy_mode)``. An incomplete evaluation wins over
        everything: a partial result cannot be reported as a decision. A flip is
        the only span-side source of WOULD_DENY, and a deny under a LOG_ONLY
        scope is the other.
    """
    policy_id = info["policy_id"]
    policy_mode = info["policy_mode"]
    if info["incomplete"]:
        return STATE_EVALUATION_INCOMPLETE, policy_id, policy_mode
    if info["flip"]:
        return (
            STATE_WOULD_DENY,
            policy_id or (info["log_only_policies"] or [None])[0],
            "LOG_ONLY",
        )
    if info["decision"] == STATE_DENY and "LOG_ONLY" in (info["engine_mode"], policy_mode):
        return STATE_WOULD_DENY, policy_id, policy_mode
    if info["decision"] in (STATE_DENY, STATE_ALLOW):
        return info["decision"], policy_id, policy_mode
    return STATE_EVALUATION_INCOMPLETE, policy_id, policy_mode


def _unparsed_span(
    message: str, row: Mapping[str, str], action_id: str
) -> PolicyObservation:
    """A log line that mentions the action but is not a span document."""
    return PolicyObservation(
        state=STATE_EVALUATION_INCOMPLETE, source=SOURCE_SPAN, action_id=action_id,
        policy_id=None, policy_name=None, policy_mode=None, engine_mode=None,
        principal_id=None, resource=None, observed_at=_span_observed_at({}, row),
        raw={"message": message, "reason": "span was not a JSON document"},
    )


def _normalize_span(
    row: Mapping[str, str], *, action_id: str, engine_id: str
) -> Optional[PolicyObservation]:
    """One span row to one observation, or None when it is about something else."""
    message = str(row.get("@message") or "")
    try:
        doc = json.loads(message)
    except ValueError:
        doc = None
    if not isinstance(doc, Mapping):
        if not _mentions(message, action_id, engine_id):
            return None
        return _unparsed_span(message, row, action_id)
    if not _mentions(json.dumps(doc), action_id, engine_id):
        return None

    attrs = _span_attributes(doc)
    info = _classify_span_attributes(attrs)
    state, policy_id, policy_mode = _span_state(info)
    raw = {k: v for k, v in doc.items() if k != "attributes"}
    raw["attributes"] = attrs
    return PolicyObservation(
        state=state, source=SOURCE_SPAN, action_id=action_id, policy_id=policy_id,
        policy_name=info["policy_name"], policy_mode=policy_mode,
        engine_mode=info["engine_mode"], principal_id=info["principal"],
        resource=info["resource"], observed_at=_span_observed_at(doc, row), raw=raw,
    )


async def observe_span_decisions(
    *,
    logs_client: Any,
    log_group: str,
    action_id: str,
    start: datetime,
    end: datetime,
    trace_id: Optional[str] = None,
    poll_interval_s: float = 1.0,
    timeout_s: float = 10.0,
) -> List[PolicyObservation]:
    """Logs Insights over the Transaction Search span log group (default 'aws/spans').

    Schema-tolerant: any span whose attributes mention the policy engine and the
    action. Normalize: an ACTIVE forbid match -> DENY; a permit -> ALLOW; a
    LOG_ONLY policy in the decision-flipping set -> WOULD_DENY; attributes
    flagged incomplete -> EVALUATION_INCOMPLETE. Always keep the raw attributes.

    Args:
        logs_client: A ``boto3`` CloudWatch Logs client, or a fake with the same
            ``start_query`` / ``get_query_results`` surface.
        log_group: The span log group to query.
        action_id: The target-qualified Gateway action id.
        start: Window start (timezone-aware).
        end: Window end (timezone-aware).
        trace_id: Optional trace id to narrow the query.
        poll_interval_s: Seconds between result polls.
        timeout_s: Seconds before an unfinished query is reported as an error.

    Returns:
        One observation per matching span, newest first as the query returns them.

    Raises:
        RuntimeError: The query reached a failed terminal state.
        TimeoutError: The query did not complete inside ``timeout_s``.
    """
    from services.managed_policy import policy_engine_id

    engine_id = policy_engine_id()
    # One budget for the whole read. Bounding only the poll left the call that
    # opens the query answerable for as long as botocore would wait.
    deadline = time.monotonic() + timeout_s
    started = await asyncio.wait_for(
        asyncio.to_thread(
            logs_client.start_query,
            logGroupNames=[log_group],
            startTime=_epoch(start),
            endTime=_epoch(end),
            queryString=_span_query(action_id, engine_id, trace_id),
        ),
        timeout=timeout_s,
    )
    rows = await _await_query(
        logs_client, started["queryId"], poll_interval_s,
        max(0.0, deadline - time.monotonic()),
    )
    observations: List[PolicyObservation] = []
    for row in rows:
        observation = _normalize_span(row, action_id=action_id, engine_id=engine_id)
        if observation is not None:
            observations.append(observation)
    return observations


# ---------------------------------------------------------------------------
# Source 2: LOG_ONLY CloudWatch metrics
# ---------------------------------------------------------------------------


def _operation_matches(dims: Mapping[str, str], action_id: str) -> bool:
    operation = dims.get("OperationName")
    if not operation:
        return True
    return operation == action_id or operation in action_id or action_id.endswith(operation)


def _discover_metrics(
    cloudwatch_client: Any, policy_engine_id: str, action_id: str
) -> List[Tuple[str, Dict[str, str]]]:
    """Every published LOG_ONLY metric for this engine, with its exact dimensions.

    Explicit queries assume the dimension shape the documentation describes;
    discovery adds whatever the service actually published, so a differently
    keyed ``OperationName`` cannot hide a flip.
    """
    found: List[Tuple[str, Dict[str, str]]] = []
    for metric in LOG_ONLY_METRICS:
        token: Optional[str] = None
        for page in range(_DISCOVERY_PAGE_LIMIT):
            request: Dict[str, Any] = {
                "Namespace": METRIC_NAMESPACE,
                "MetricName": metric,
                "Dimensions": [{"Name": "PolicyEngine", "Value": policy_engine_id}],
            }
            if token:
                request["NextToken"] = token
            response = cloudwatch_client.list_metrics(**request)
            for item in response.get("Metrics", []):
                dims = {d["Name"]: d["Value"] for d in item.get("Dimensions", [])}
                if _operation_matches(dims, action_id):
                    found.append((metric, dims))
            token = response.get("NextToken")
            if not token:
                break
            if page == _DISCOVERY_PAGE_LIMIT - 1:
                # One engine publishes a handful of dimension shapes. More pages
                # than this is a paginator that will not end, and walking it
                # would hold the operator's request open.
                logger.warning(
                    "stopped %s discovery at %d pages; later pages were not read",
                    metric, _DISCOVERY_PAGE_LIMIT,
                )
    return found


def _metric_shapes(
    policy_engine_id: str,
    action_id: str,
    discovered: Sequence[Tuple[str, Dict[str, str]]],
) -> List[Tuple[str, Dict[str, str]]]:
    """Every (metric, dimensions) pair worth querying, without duplicates."""
    shapes: List[Tuple[str, Dict[str, str]]] = []
    seen = set()
    policy_ids = sorted({dims["Policy"] for _m, dims in discovered if dims.get("Policy")})
    base = {"PolicyEngine": policy_engine_id, "OperationName": action_id}
    for metric in LOG_ONLY_METRICS:
        candidates = [base] + [{**base, "Policy": pid} for pid in policy_ids]
        for dims in candidates + [d for m, d in discovered if m == metric]:
            key = (metric, tuple(sorted(dims.items())))
            if key not in seen:
                seen.add(key)
                shapes.append((metric, dict(dims)))
    return shapes


def _metric_queries(
    policy_engine_id: str,
    action_id: str,
    discovered: Sequence[Tuple[str, Dict[str, str]]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Tuple[str, Dict[str, str]]]]:
    """GetMetricData queries for the explicit shape plus every discovered shape."""
    shapes = _metric_shapes(policy_engine_id, action_id, discovered)
    queries: List[Dict[str, Any]] = []
    index: Dict[str, Tuple[str, Dict[str, str]]] = {}
    for n, (metric, dims) in enumerate(shapes):
        query_id = f"q{n}_{metric.lower()}"
        index[query_id] = (metric, dims)
        queries.append({
            "Id": query_id,
            "MetricStat": {
                "Metric": {
                    "Namespace": METRIC_NAMESPACE,
                    "MetricName": metric,
                    "Dimensions": [{"Name": k, "Value": v} for k, v in dims.items()],
                },
                "Period": 60,
                "Stat": "Sum",
            },
            "ReturnData": True,
        })
    return queries, index


def _metric_observation(
    state: str,
    *,
    metric: str,
    dims: Mapping[str, str],
    values: List[float],
    stamps: List[Any],
    action_id: str,
    end: datetime,
) -> PolicyObservation:
    observed = [s for s in stamps if isinstance(s, datetime)]
    return PolicyObservation(
        state=state, source=SOURCE_METRIC, action_id=action_id,
        policy_id=dims.get("Policy"), policy_name=None,
        policy_mode="LOG_ONLY" if dims.get("Policy") or state == STATE_WOULD_DENY else None,
        engine_mode=None, principal_id=None, resource=None,
        observed_at=max(observed) if observed else end,
        raw={
            "metric": metric, "namespace": METRIC_NAMESPACE, "sum": sum(values),
            "values": values, "timestamps": [str(s) for s in stamps], "dimensions": dict(dims),
            "granularity": "minute",
            "note": (
                "60-second Sum over a window padded by 60 seconds on each side; "
                "another execution of this action in the same minutes could have "
                "produced this datapoint"
            ),
        },
    )


def observe_metric_window(
    *,
    cloudwatch_client: Any,
    policy_engine_id: str,
    action_id: str,
    start: datetime,
    end: datetime,
) -> List[PolicyObservation]:
    """GetMetricData on AWS/Bedrock-AgentCore LogOnlyMatches, LogOnlyDecisionFlips,
    LogOnlyEvalIncomplete with dimensions PolicyEngine (+Policy per policy).

    Flips>0 -> WOULD_DENY (source cloudwatch-metric); Incomplete>0 ->
    EVALUATION_INCOMPLETE; otherwise no row. A per-policy flip row supersedes
    the engine-level aggregate for the same window, so one flip is not reported
    twice.

    This source is minute-granular, not per-call. The datapoints are 60-second
    Sums and the caller pads the window by a further 60 seconds on each side, so
    a flip reported here belongs to the action within a minute or two of this
    execution. If the same action ran twice in that span, the attribution to
    this call is an inference. A span reading is per-call; this one is not, and
    both the raw document and the receipt say so.

    Args:
        cloudwatch_client: A ``boto3`` CloudWatch client or a fake with
            ``list_metrics`` and ``get_metric_data``.
        policy_engine_id: The engine whose LOG_ONLY metrics to read.
        action_id: The Gateway action id, used as ``OperationName``.
        start: Window start.
        end: Window end.

    Returns:
        Observations for non-zero flip and incomplete datapoints only.
    """
    discovered = _discover_metrics(cloudwatch_client, policy_engine_id, action_id)
    queries, index = _metric_queries(policy_engine_id, action_id, discovered)
    response = cloudwatch_client.get_metric_data(
        MetricDataQueries=queries, StartTime=start, EndTime=end, ScanBy="TimestampDescending",
    )
    return _read_metric_results(response, index=index, action_id=action_id, end=end)


def _read_metric_results(
    response: Mapping[str, Any],
    *,
    index: Mapping[str, Tuple[str, Dict[str, str]]],
    action_id: str,
    end: datetime,
) -> List[PolicyObservation]:
    """Non-zero flip and incomplete datapoints as observations.

    A per-policy flip supersedes the engine-level aggregate for the same window,
    so the same flip is never reported twice with different attribution.
    """
    observations: List[PolicyObservation] = []
    engine_level_flips: List[PolicyObservation] = []
    per_policy_flips: List[PolicyObservation] = []
    for result in response.get("MetricDataResults", []):
        row = _reportable_metric_row(result, index=index, action_id=action_id, end=end)
        if row is None:
            continue
        metric, observation, dims = row
        if metric == METRIC_INCOMPLETE:
            observations.append(observation)
        elif dims.get("Policy"):
            per_policy_flips.append(observation)
        else:
            engine_level_flips.append(observation)
    observations.extend(per_policy_flips or engine_level_flips[:1])
    return observations


def _reportable_metric_row(
    result: Mapping[str, Any],
    *,
    index: Mapping[str, Tuple[str, Dict[str, str]]],
    action_id: str,
    end: datetime,
) -> Optional[Tuple[str, PolicyObservation, Dict[str, str]]]:
    """One GetMetricData result as an observation, or None when it reports nothing.

    A zero-valued datapoint is not evidence of anything, and neither is a metric
    this module did not ask for.
    """
    metric, dims = index.get(str(result.get("Id")), ("", {}))
    values = [float(v) for v in result.get("Values", [])]
    if not metric or metric == METRIC_MATCHES or sum(values) <= 0:
        return None
    observation = _metric_observation(
        STATE_WOULD_DENY if metric == METRIC_FLIPS else STATE_EVALUATION_INCOMPLETE,
        metric=metric, dims=dims, values=values,
        stamps=list(result.get("Timestamps", [])), action_id=action_id, end=end,
    )
    return metric, observation, dims


# ---------------------------------------------------------------------------
# Source 3: the Cedar text scan, which can only infer
# ---------------------------------------------------------------------------


def inferred_from_policy_text(
    *,
    action_id: str,
    matching_policies: List[str],
    engine_state: Dict[str, Any],
) -> List[PolicyObservation]:
    """The former substring scan. Always state POLICY_INFERRED, source policy-text.

    Args:
        action_id: The Gateway action id the scan matched against.
        matching_policies: Names of forbid policies whose Cedar text names the action.
        engine_state: The mapping ``managed_policy.engine_state_for_action`` returns.

    Returns:
        One POLICY_INFERRED observation per matching policy. Never WOULD_DENY.
    """
    policies = engine_state.get("policies") or {}
    policy_ids = engine_state.get("policy_ids") or {}
    gateway_mode = str(engine_state.get("gateway_mode") or "").upper() or None
    now = datetime.now(timezone.utc)
    observations: List[PolicyObservation] = []
    for name in matching_policies:
        effect, mode = policies.get(name, ("", ""))
        observations.append(PolicyObservation(
            state=STATE_POLICY_INFERRED, source=SOURCE_TEXT, action_id=action_id,
            policy_id=policy_ids.get(name), policy_name=name,
            policy_mode=str(mode).upper() or None, engine_mode=gateway_mode,
            principal_id=None, resource=None, observed_at=now,
            raw={
                "matched_by": "cedar-statement-substring",
                "effect": effect,
                "note": "policy text names the action; this is not a decision",
            },
        ))
    return observations


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

# The flip link is decided by reading the previous terminal row and inserting a
# reference to it, which is a read-then-write on shared state. Two executions of
# the same action by the same principal against the same resource would both read
# the same prior row and produce two links to it, or none, depending on commit
# order. The advisory lock is transaction-scoped and keyed on exactly that
# triple, so concurrent turns for OTHER actions never wait on each other.
_LOCK_TRIPLE = """
SELECT pg_advisory_xact_lock(hashtext(%(lock_key)s))
"""

_PRIOR_TERMINAL = """
SELECT decision_id, state
  FROM pellier.policy_decisions
 WHERE principal_id IS NOT DISTINCT FROM %(principal_id)s
   AND action_id = %(action_id)s
   AND resource IS NOT DISTINCT FROM %(resource)s
   AND state IN ('ALLOW', 'DENY', 'WOULD_DENY')
 ORDER BY observed_at DESC, decision_id DESC
 LIMIT 1
"""

_INSERT_DECISION = """
INSERT INTO pellier.policy_decisions
    (session_id, turn_id, audit_id, principal_id, action_id, resource,
     policy_engine_id, policy_id, policy_name, policy_mode, engine_mode,
     state, source, flip_of, observed_at, raw)
VALUES
    (%(session_id)s, %(turn_id)s, %(audit_id)s, %(principal_id)s, %(action_id)s,
     %(resource)s, %(policy_engine_id)s, %(policy_id)s, %(policy_name)s,
     %(policy_mode)s, %(engine_mode)s, %(state)s, %(source)s, %(flip_of)s,
     %(observed_at)s, %(raw)s::jsonb)
RETURNING decision_id
"""


def _flip_lock_key(observation: PolicyObservation) -> str:
    """The (principal, action, resource) triple the flip link is keyed on."""
    return "|".join((
        observation.principal_id or "",
        observation.action_id or "",
        observation.resource or "",
    ))


def _is_flip(prior_state: str, new_state: str) -> bool:
    if prior_state not in TERMINAL_STATES or new_state not in TERMINAL_STATES:
        return False
    return (prior_state == STATE_ALLOW) != (new_state == STATE_ALLOW)


async def persist(
    db_service: Any,
    observations: List[PolicyObservation],
    *,
    session_id: Optional[str],
    turn_id: Optional[str],
    audit_id: Optional[int],
) -> List[int]:
    """INSERT rows; detect a flip: if the newest prior row for the same (principal_id,
    action_id, resource) has a different terminal state (ALLOW vs DENY/WOULD_DENY),
    set flip_of to it.

    The read and the insert are serialized per triple with a transaction-scoped
    advisory lock. Without it two concurrent executions of the same action read
    the same prior row, and the flip link is duplicated or lost depending on
    which commits first.

    Args:
        db_service: The ``DatabaseService`` (or a fake exposing ``get_connection``).
        observations: What to record, in order. Order matters: a later terminal
            observation in the same batch can be a flip of an earlier one.
        session_id: Session the call belonged to.
        turn_id: Turn or execution turn the call belonged to.
        audit_id: The ``pellier.tool_audit`` row for the call, when known.

    Returns:
        The new ``decision_id`` values, in input order.
    """
    from services.managed_policy import policy_engine_id

    if not observations:
        return []
    engine_id = policy_engine_id() or None
    ids: List[int] = []
    async with db_service.get_connection() as conn:
        async with conn.cursor() as cur:
            for observation in observations:
                flip_of: Optional[int] = None
                if observation.state in TERMINAL_STATES:
                    await cur.execute(_LOCK_TRIPLE, {
                        "lock_key": _flip_lock_key(observation),
                    })
                    await cur.execute(_PRIOR_TERMINAL, {
                        "principal_id": observation.principal_id,
                        "action_id": observation.action_id,
                        "resource": observation.resource,
                    })
                    prior = await cur.fetchone()
                    if prior and _is_flip(str(prior["state"]), observation.state):
                        flip_of = int(prior["decision_id"])
                await cur.execute(_INSERT_DECISION, {
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "audit_id": audit_id,
                    "principal_id": observation.principal_id,
                    "action_id": observation.action_id,
                    "resource": observation.resource,
                    "policy_engine_id": engine_id,
                    "policy_id": observation.policy_id,
                    "policy_name": observation.policy_name,
                    "policy_mode": observation.policy_mode,
                    "engine_mode": observation.engine_mode,
                    "state": observation.state,
                    "source": observation.source,
                    "flip_of": flip_of,
                    "observed_at": observation.observed_at,
                    "raw": json.dumps(observation.raw, default=str),
                })
                row = await cur.fetchone()
                value = row["decision_id"] if isinstance(row, Mapping) else row[0]
                ids.append(int(value))
    return ids


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _incomplete(
    *, source: str, action_id: str, principal_id: Optional[str], resource: Optional[str],
    observed_at: datetime, raw: Dict[str, Any],
) -> PolicyObservation:
    return PolicyObservation(
        state=STATE_EVALUATION_INCOMPLETE, source=source, action_id=action_id,
        policy_id=None, policy_name=None, policy_mode=None, engine_mode=None,
        principal_id=principal_id, resource=resource, observed_at=observed_at, raw=raw,
    )


def _telemetry_client_config() -> Any:
    """Short timeouts and a small retry cap for both telemetry clients.

    botocore's defaults would let one unreachable endpoint hold the operator's
    Execute request for minutes.
    """
    from botocore.config import Config

    return Config(
        connect_timeout=_AWS_CONNECT_TIMEOUT_S,
        read_timeout=_AWS_READ_TIMEOUT_S,
        retries={"max_attempts": _AWS_MAX_ATTEMPTS, "mode": "standard"},
    )


def _resolve_clients(clients: Optional[Mapping[str, Any]]) -> Tuple[Any, Any]:
    logs = (clients or {}).get("logs")
    cloudwatch = (clients or {}).get("cloudwatch")
    if logs is not None and cloudwatch is not None:
        return logs, cloudwatch
    import boto3

    from services.managed_policy import resolved_region

    region = resolved_region()
    config = _telemetry_client_config()
    return (
        logs if logs is not None
        else boto3.client("logs", region_name=region, config=config),
        cloudwatch if cloudwatch is not None
        else boto3.client("cloudwatch", region_name=region, config=config),
    )


def _with_context(
    observations: Iterable[PolicyObservation],
    *, principal_id: Optional[str], resource: Optional[str],
) -> List[PolicyObservation]:
    """Fill in the caller's principal and resource where the source carried none.

    The flip detector keys on (principal, action, resource), so a metric row that
    knows only the engine must still land on the same triple as the receipt row.
    """
    filled = []
    for observation in observations:
        filled.append(replace(
            observation,
            principal_id=observation.principal_id or principal_id,
            resource=observation.resource or resource,
        ))
    return filled


async def _observe_from_aws(
    *, clients: Optional[Mapping[str, Any]], engine_id: str, action_id: str,
    start: datetime, end: datetime, trace_id: Optional[str],
) -> Tuple[List[PolicyObservation], List[Tuple[str, BaseException]]]:
    """Both telemetry sources, each attempted even if the other fails."""
    observed: List[PolicyObservation] = []
    errors: List[Tuple[str, BaseException]] = []
    logs, cloudwatch = _resolve_clients(clients)
    try:
        observed.extend(await observe_span_decisions(
            logs_client=logs, log_group=span_log_group(), action_id=action_id,
            start=start, end=end, trace_id=trace_id,
        ))
    except Exception as exc:  # noqa: BLE001 - recorded as evidence, not swallowed
        errors.append((SOURCE_SPAN, exc))
    try:
        observed.extend(await asyncio.wait_for(
            asyncio.to_thread(
                observe_metric_window,
                cloudwatch_client=cloudwatch, policy_engine_id=engine_id, action_id=action_id,
                start=start - _METRIC_WINDOW_PAD, end=end + _METRIC_WINDOW_PAD,
            ),
            timeout=_METRIC_DEADLINE_S,
        ))
    except Exception as exc:  # noqa: BLE001 - recorded as evidence, not swallowed
        errors.append((SOURCE_METRIC, exc))
    return observed, errors


async def _inferred_for(
    action_id: str, engine_state: Optional[Mapping[str, Any]],
) -> Tuple[List[PolicyObservation], Optional[BaseException]]:
    """The Cedar text scan, reading the control plane only when the caller did not.

    A caller that already read the engine passes what it read. A caller that
    tried and failed passes None, because ``routes/operator.py`` swallows the
    failure to keep the execution honest rather than to hide it. Those two look
    identical here, so the failure itself is the discriminator: when one is
    recorded for this request, the read is not repeated. Re-running a slow
    control-plane call is pure added latency on exactly the deployment least able
    to absorb it, and it would run on the post-write path.

    The skip is returned as an error, not dropped, so the receipt still records
    an incomplete evaluation and names the reason for it.

    Args:
        action_id: The Gateway action id to match against the Cedar text.
        engine_state: The caller's control-plane read, or None.

    Returns:
        ``(observations, error)``: the POLICY_INFERRED rows the text scan
        produced, and whatever prevented a reading, if anything did.
    """
    if engine_state is None:
        from services import managed_policy

        already_failed = managed_policy.control_plane_failure()
        if already_failed:
            return [], managed_policy.ControlPlaneUnavailable(
                "the Cedar text scan was skipped because the control-plane read "
                f"already failed in this request ({already_failed})"
            )
        try:
            engine_state = await managed_policy.engine_state_for_action(action_id)
        except Exception as exc:  # noqa: BLE001 - recorded as evidence, not swallowed
            return [], exc
    if not engine_state:
        return [], None
    matching = list(engine_state.get("matching") or [])
    return inferred_from_policy_text(
        action_id=action_id, matching_policies=matching, engine_state=dict(engine_state),
    ), None


async def _observations_for_window(
    *,
    clients: Optional[Mapping[str, Any]],
    engine_id: str,
    action_id: str,
    start: datetime,
    end: datetime,
    trace_id: Optional[str],
    engine_state: Optional[Mapping[str, Any]],
    principal_id: Optional[str],
    resource: Optional[str],
    already_held: bool,
) -> List[PolicyObservation]:
    """Everything the three sources observed about one call, plus what they could not.

    Telemetry first, then the Cedar text scan, then at most one incomplete row:
    naming the first failure when a source failed, or recording an empty window
    when every source answered and none of them saw the call. A failure is
    recorded rather than raised, because by the time this runs the governed call
    has already happened and a telemetry gap must not undo it.

    Args:
        clients: Optional ``{"logs": ..., "cloudwatch": ...}`` telemetry clients.
        engine_id: The policy engine whose decisions to read.
        action_id: The Gateway action id the call used.
        start: Window start, before the governed call was made.
        end: Window end, after it returned.
        trace_id: Optional trace id to narrow the span query.
        engine_state: The caller's control-plane read, when it holds one.
        principal_id: The actor the engine authorized, for the flip triple.
        resource: The resource the action targeted, for the flip triple.
        already_held: Whether the caller already holds an observation. An empty
            window is only worth recording when nothing else was observed at all.

    Returns:
        The observations to persist, in the order the sources produced them.
    """
    observed, errors = await _observe_from_aws(
        clients=clients, engine_id=engine_id, action_id=action_id,
        start=start, end=end, trace_id=trace_id,
    )
    rows = _with_context(observed, principal_id=principal_id, resource=resource)
    inferred, inference_error = await _inferred_for(action_id, engine_state)
    rows.extend(_with_context(inferred, principal_id=principal_id, resource=resource))
    if inference_error is not None:
        errors.append((SOURCE_TEXT, inference_error))
    if errors:
        source, first = errors[0]
        rows.append(_incomplete(
            source=source, action_id=action_id, principal_id=principal_id,
            resource=resource, observed_at=end,
            raw={
                "error": f"{type(first).__name__}: {first}",
                "stage": source,
                "errors": [f"{stage}: {type(exc).__name__}: {exc}" for stage, exc in errors],
            },
        ))
    elif not rows and not already_held:
        rows.append(_incomplete(
            source=SOURCE_SPAN, action_id=action_id, principal_id=principal_id,
            resource=resource, observed_at=end,
            raw={
                "reason": "no decision telemetry in window",
                "log_group": span_log_group(),
                "window": [start.isoformat(), end.isoformat()],
            },
        ))
    return rows


async def collect_for_turn(
    db_service: Any,
    *,
    action_id: str,
    session_id: Optional[str],
    turn_id: Optional[str],
    audit_id: Optional[int],
    start: datetime,
    end: datetime,
    trace_id: Optional[str] = None,
    clients: Optional[Mapping[str, Any]] = None,
    prior: Optional[List[PolicyObservation]] = None,
    engine_state: Optional[Mapping[str, Any]] = None,
    principal_id: Optional[str] = None,
    resource: Optional[str] = None,
) -> Dict[str, Any]:
    """Orchestrates the three sources with settings AGENTCORE_POLICY_SPAN_LOG_GROUP
    (default 'aws/spans'), AGENTCORE_POLICY_ENGINE_ID; on any AWS error records one
    EVALUATION_INCOMPLETE row with the error in raw. Returns {"states": [...], "ids": [...]}

    Args:
        db_service: Where to persist.
        action_id: The Gateway action id the call used.
        session_id: Session the call belonged to.
        turn_id: Execution turn the call belonged to.
        audit_id: The ``tool_audit`` row for the call, when known.
        start: Window start, before the governed call was made.
        end: Window end, after it returned.
        trace_id: Optional trace id to narrow the span query.
        clients: Optional ``{"logs": ..., "cloudwatch": ...}`` clients; built
            with ``boto3`` when absent.
        prior: Observations the caller already holds, typically the Gateway's own
            response as a ``governed-receipt`` row. Persisted first.
        engine_state: The mapping ``engine_state_for_action`` returns, when the
            caller already read it; read here otherwise.
        principal_id: The actor the engine authorized, for the flip triple.
        resource: The resource the action targeted, for the flip triple.

    Returns:
        ``{"states": [...], "ids": [...], "terminal": <state>,
        "terminal_source": <source>}`` where ``terminal`` is what a receipt
        records and ``terminal_source`` is the source that produced it. The
        source matters to the wording: a metric reading is minute-granular, so a
        receipt must not describe it as a decision about this one call.
    """
    from services.managed_policy import policy_engine_id

    engine_id = policy_engine_id()
    observations: List[PolicyObservation] = list(prior or [])
    if not engine_id:
        observations.append(_incomplete(
            source=SOURCE_SPAN, action_id=action_id, principal_id=principal_id,
            resource=resource, observed_at=end,
            raw={"reason": "no policy engine id configured, so no decision was observable"},
        ))
    else:
        observations.extend(await _observations_for_window(
            clients=clients, engine_id=engine_id, action_id=action_id,
            start=start, end=end, trace_id=trace_id, engine_state=engine_state,
            principal_id=principal_id, resource=resource,
            already_held=bool(observations),
        ))
    ids = await persist(
        db_service, observations, session_id=session_id, turn_id=turn_id, audit_id=audit_id
    )
    states = [observation.state for observation in observations]
    terminal = terminal_state(states)
    return {
        "states": states,
        "ids": ids,
        "terminal": terminal,
        "terminal_source": next(
            (o.source for o in observations if o.state == terminal), ""
        ),
    }
