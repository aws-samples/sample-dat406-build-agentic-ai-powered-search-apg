"""Policy decision observations: real events, never inferred text.

Five states, from three sources plus the Gateway's own response:

    ALLOW / DENY            an enforced decision the engine reported
    WOULD_DENY              a real LOG_ONLY deny event (span or metric)
    EVALUATION_INCOMPLETE   telemetry unreadable, absent, or partial
    POLICY_INFERRED         the Cedar text names the action; not a decision

The substring scan that used to yield WOULD_DENY can only ever yield
POLICY_INFERRED now. Every assertion here is about that boundary.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

REPO = BACKEND.parents[1]
MIGRATIONS = REPO / "scripts" / "migrations"


def _sql_without_comments(path: Path) -> str:
    return "\n".join(line.split("--", 1)[0] for line in path.read_text().splitlines())


# ---------------------------------------------------------------------------
# Migration 048
# ---------------------------------------------------------------------------


def test_migration_048_creates_an_append_only_decision_table() -> None:
    sql = _sql_without_comments(MIGRATIONS / "048_policy_decisions.sql")
    assert "CREATE TABLE IF NOT EXISTS pellier.policy_decisions" in sql
    for state in ("ALLOW", "DENY", "WOULD_DENY", "EVALUATION_INCOMPLETE", "POLICY_INFERRED"):
        assert f"'{state}'" in sql, state
    for source in ("gateway-span", "cloudwatch-metric", "governed-receipt", "policy-text"):
        assert f"'{source}'" in sql, source
    assert "flip_of" in sql
    assert (
        "CREATE TRIGGER policy_decisions_append_only BEFORE UPDATE OR DELETE"
        " ON pellier.policy_decisions" in sql
    )
    assert "EXECUTE FUNCTION pellier.reject_evidence_mutation()" in sql
    assert "GRANT SELECT, INSERT ON pellier.policy_decisions TO pellier_agent" in sql


def test_migration_048_widens_the_receipt_domains_to_the_five_states() -> None:
    sql = _sql_without_comments(MIGRATIONS / "048_policy_decisions.sql")
    assert "governed_receipts_decision_check" in sql
    assert "execution_receipts_policy_outcome_check" in sql
    # The in-process rail still records NOT_EVALUATED, so widening must keep it.
    widened = sql[sql.index("execution_receipts_policy_outcome_check"):]
    assert "'NOT_EVALUATED'" in widened
    assert "'EVALUATION_INCOMPLETE'" in widened
    assert "'POLICY_INFERRED'" in widened


def test_migration_048_admits_the_refused_rail() -> None:
    sql = _sql_without_comments(MIGRATIONS / "048_policy_decisions.sql")
    assert "execution_receipts_rail_check" in sql
    rail = sql[sql.index("execution_receipts_rail_check"):]
    assert "'refused'" in rail
    assert "'gateway-mcp'" in rail and "'in-process'" in rail


def test_migration_048_drops_only_the_two_checks_it_replaces() -> None:
    """The drop loop is a catalog scan, so it has to be narrow and deduplicated.

    Without DISTINCT a CHECK spanning both columns is returned twice and its
    second DROP fails the migration; without the name and single-column filters
    any other CHECK on those columns is dropped and never put back.
    """
    sql = _sql_without_comments(MIGRATIONS / "048_policy_decisions.sql")
    loop = sql[sql.index("FOR v_name IN"):sql.index("END LOOP")]
    assert "SELECT DISTINCT c.conname" in loop
    assert "cardinality(c.conkey) = 1" in loop
    assert "'^execution_receipts_' || a.attname || '_check[0-9]*$'" in loop


def test_migration_048_does_not_add_run_id() -> None:
    """WP4's migration 049 owns run_id; adding it here would collide."""
    sql = _sql_without_comments(MIGRATIONS / "048_policy_decisions.sql")
    assert "run_id" not in sql


def test_migration_048_rolls_its_probe_back() -> None:
    text = (MIGRATIONS / "048_policy_decisions.sql").read_text()
    assert "SQLSTATE 'P0048'" in text
    assert "ERRCODE = 'P0048'" in text


# ---------------------------------------------------------------------------
# The service: fakes
# ---------------------------------------------------------------------------

import json  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
import asyncio  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402

from services import policy_decisions as pd  # noqa: E402

ENGINE = "engine-abc123"
ACTION = "pellier-concierge-experience-target___initiate_return"
START = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
END = START + timedelta(seconds=30)


def _span(attributes: Dict[str, Any], **top: Any) -> str:
    doc = {
        "name": "policy.evaluate",
        "traceId": "trace-1",
        "startTimeUnixNano": str(int(START.timestamp() * 1e9)),
        "attributes": attributes,
    }
    doc.update(top)
    return json.dumps(doc)


class FakeLogs:
    """A Logs Insights client that completes on the first poll."""

    def __init__(self, messages: List[str], *, fail: Optional[Exception] = None) -> None:
        self.messages = messages
        self.fail = fail
        self.started: List[Dict[str, Any]] = []

    def start_query(self, **kwargs: Any) -> Dict[str, Any]:
        if self.fail is not None:
            raise self.fail
        self.started.append(kwargs)
        return {"queryId": "q-1"}

    def get_query_results(self, queryId: str) -> Dict[str, Any]:  # noqa: N803 - boto3 casing
        return {
            "status": "Complete",
            "results": [
                [{"field": "@timestamp", "value": "2026-09-04 12:00:01.000"},
                 {"field": "@message", "value": message},
                 {"field": "@ptr", "value": "x"}]
                for message in self.messages
            ],
        }


class FakeCloudWatch:
    """Answers GetMetricData from a {(metric, policy_id): [values]} table."""

    def __init__(self, table: Dict[tuple, List[float]]) -> None:
        self.table = table
        self.queries: List[Dict[str, Any]] = []

    def list_metrics(self, **kwargs: Any) -> Dict[str, Any]:
        name = kwargs.get("MetricName")
        metrics = []
        for (metric, policy_id), _values in self.table.items():
            if metric != name or policy_id is None:
                continue
            metrics.append({
                "Namespace": pd.METRIC_NAMESPACE,
                "MetricName": metric,
                "Dimensions": [
                    {"Name": "PolicyEngine", "Value": ENGINE},
                    {"Name": "OperationName", "Value": ACTION},
                    {"Name": "Policy", "Value": policy_id},
                ],
            })
        return {"Metrics": metrics}

    def get_metric_data(self, **kwargs: Any) -> Dict[str, Any]:
        self.queries = kwargs["MetricDataQueries"]
        results = []
        for query in self.queries:
            metric = query["MetricStat"]["Metric"]
            dims = {d["Name"]: d["Value"] for d in metric["Dimensions"]}
            values = self.table.get((metric["MetricName"], dims.get("Policy")), [])
            results.append({
                "Id": query["Id"],
                "Label": metric["MetricName"],
                "Values": values,
                "Timestamps": [END] * len(values),
            })
        return {"MetricDataResults": results}


class FakeCur:
    def __init__(self, db: "FakeDb") -> None:
        self.db = db
        self._row: Optional[Dict[str, Any]] = None

    async def execute(self, sql: str, params: Any = None) -> None:
        self.db.statements.append((sql, params))
        if sql.lstrip().upper().startswith("SELECT"):
            self._row = self.db.prior
        elif sql.lstrip().upper().startswith("INSERT"):
            self.db.inserted.append(dict(params))
            self.db.next_id += 1
            self._row = {"decision_id": self.db.next_id}
        else:
            self._row = None

    async def fetchone(self) -> Optional[Dict[str, Any]]:
        return self._row

    async def __aenter__(self) -> "FakeCur":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class FakeConn:
    def __init__(self, db: "FakeDb") -> None:
        self.db = db

    def cursor(self) -> FakeCur:
        return FakeCur(self.db)

    async def __aenter__(self) -> "FakeConn":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class FakeDb:
    def __init__(self, prior: Optional[Dict[str, Any]] = None) -> None:
        self.prior = prior
        self.inserted: List[Dict[str, Any]] = []
        self.statements: List[tuple] = []
        self.next_id = 100

    def get_connection(self) -> FakeConn:
        return FakeConn(self)

    async def fetch_all(self, sql: str, *params: Any) -> List[Dict[str, Any]]:
        self.statements.append((sql, params))
        return []


def _obs(state: str, source: str = "gateway-span", **over: Any) -> pd.PolicyObservation:
    base = dict(
        state=state, source=source, action_id=ACTION, policy_id=None, policy_name=None,
        policy_mode=None, engine_mode=None, principal_id="sub-operator", resource="gw-1",
        observed_at=START, raw={},
    )
    base.update(over)
    return pd.PolicyObservation(**base)


@pytest.fixture(autouse=True)
def _engine_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "AGENTCORE_POLICY_ENGINE_ID", ENGINE, raising=False)
    monkeypatch.setattr(settings, "AGENTCORE_POLICY_SPAN_LOG_GROUP", None, raising=False)


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


def test_the_five_states_are_the_only_states() -> None:
    assert pd.POLICY_STATES == (
        "ALLOW", "DENY", "WOULD_DENY", "EVALUATION_INCOMPLETE", "POLICY_INFERRED",
    )


def test_terminal_state_prefers_the_strongest_real_decision() -> None:
    assert pd.terminal_state([]) == "EVALUATION_INCOMPLETE"
    assert pd.terminal_state(["EVALUATION_INCOMPLETE"]) == "EVALUATION_INCOMPLETE"
    assert pd.terminal_state(["POLICY_INFERRED", "EVALUATION_INCOMPLETE"]) == "POLICY_INFERRED"
    assert pd.terminal_state(["ALLOW", "POLICY_INFERRED"]) == "ALLOW"
    assert pd.terminal_state(["ALLOW", "WOULD_DENY"]) == "WOULD_DENY"
    assert pd.terminal_state(["WOULD_DENY", "DENY", "ALLOW"]) == "DENY"


# ---------------------------------------------------------------------------
# Spans
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_span_forbid_match_is_a_deny_with_its_raw_attributes_kept() -> None:
    attrs = {
        "aws.bedrock_agentcore.policy_engine.id": ENGINE,
        "aws.bedrock_agentcore.policy.action": ACTION,
        "aws.bedrock_agentcore.policy.decision": "DENY",
        "aws.bedrock_agentcore.policy.matched_policy_id": "pol-forbid-1",
        "aws.bedrock_agentcore.policy.principal": "sub-operator",
    }
    logs = FakeLogs([_span(attrs)])
    rows = await pd.observe_span_decisions(
        logs_client=logs, log_group="aws/spans", action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["DENY"]
    assert rows[0].source == "gateway-span"
    assert rows[0].policy_id == "pol-forbid-1"
    assert rows[0].principal_id == "sub-operator"
    assert rows[0].raw["attributes"] == attrs
    # The query is scoped to the engine and the action, not the whole log group.
    query = logs.started[0]["queryString"]
    assert ACTION in query and ENGINE in query
    assert logs.started[0]["logGroupNames"] == ["aws/spans"]


@pytest.mark.asyncio
async def test_a_span_permit_is_an_allow() -> None:
    attrs = {"policyEngineId": ENGINE, "action": ACTION, "effect": "permit"}
    rows = await pd.observe_span_decisions(
        logs_client=FakeLogs([_span(attrs)]), log_group="aws/spans",
        action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["ALLOW"]


@pytest.mark.asyncio
async def test_a_log_only_flip_in_a_span_is_would_deny() -> None:
    attrs = {
        "policy_engine_id": ENGINE,
        "action_id": ACTION,
        "decision": "ALLOW",
        "log_only_decision_flips": 1,
        "log_only_matched_policies": ["pol-log-only-7"],
    }
    rows = await pd.observe_span_decisions(
        logs_client=FakeLogs([_span(attrs)]), log_group="aws/spans",
        action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["WOULD_DENY"]
    assert rows[0].policy_id == "pol-log-only-7"
    assert rows[0].policy_mode == "LOG_ONLY"


@pytest.mark.asyncio
async def test_a_deny_evaluated_under_a_log_only_engine_is_would_deny() -> None:
    attrs = {
        "policy.engine.id": ENGINE, "policy.action": ACTION,
        "policy.decision": "deny", "policy.engine.mode": "LOG_ONLY",
    }
    rows = await pd.observe_span_decisions(
        logs_client=FakeLogs([_span(attrs)]), log_group="aws/spans",
        action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["WOULD_DENY"]
    assert rows[0].engine_mode == "LOG_ONLY"


@pytest.mark.asyncio
async def test_an_incomplete_evaluation_span_is_evaluation_incomplete() -> None:
    attrs = {
        "policy.engine.id": ENGINE, "policy.action": ACTION,
        "policy.decision": "ALLOW", "policy.log_only.eval_incomplete": True,
    }
    rows = await pd.observe_span_decisions(
        logs_client=FakeLogs([_span(attrs)]), log_group="aws/spans",
        action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["EVALUATION_INCOMPLETE"]


@pytest.mark.asyncio
async def test_a_span_with_no_decision_fields_is_incomplete_not_a_verdict() -> None:
    attrs = {"policy.engine.id": ENGINE, "policy.action": ACTION, "duration_ms": 3}
    rows = await pd.observe_span_decisions(
        logs_client=FakeLogs([_span(attrs)]), log_group="aws/spans",
        action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["EVALUATION_INCOMPLETE"]
    assert rows[0].raw["attributes"]["duration_ms"] == 3


@pytest.mark.asyncio
async def test_spans_for_other_actions_or_engines_are_ignored() -> None:
    other_action = _span({"policy.engine.id": ENGINE, "policy.action": "x___y",
                          "policy.decision": "DENY"})
    other_engine = _span({"policy.engine.id": "engine-zzz", "policy.action": ACTION,
                          "policy.decision": "DENY"})
    not_json = "plain text mentioning " + ACTION + " and " + ENGINE
    rows = await pd.observe_span_decisions(
        logs_client=FakeLogs([other_action, other_engine, not_json]), log_group="aws/spans",
        action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["EVALUATION_INCOMPLETE"]
    assert rows[0].raw["message"] == not_json


@pytest.mark.asyncio
async def test_a_trace_id_narrows_the_span_query() -> None:
    logs = FakeLogs([])
    await pd.observe_span_decisions(
        logs_client=logs, log_group="aws/spans", action_id=ACTION,
        start=START, end=END, trace_id="trace-77",
    )
    assert "trace-77" in logs.started[0]["queryString"]
    assert logs.started[0]["startTime"] == int(START.timestamp())
    assert logs.started[0]["endTime"] == int(END.timestamp())


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def test_metric_flips_are_would_deny_per_policy() -> None:
    cw = FakeCloudWatch({
        ("LogOnlyMatches", "pol-a"): [3.0],
        ("LogOnlyDecisionFlips", "pol-a"): [1.0, 1.0],
        ("LogOnlyDecisionFlips", None): [2.0],
        ("LogOnlyEvalIncomplete", None): [0.0],
    })
    rows = pd.observe_metric_window(
        cloudwatch_client=cw, policy_engine_id=ENGINE, action_id=ACTION, start=START, end=END,
    )
    assert [(r.state, r.policy_id) for r in rows] == [("WOULD_DENY", "pol-a")]
    assert rows[0].source == "cloudwatch-metric"
    assert rows[0].policy_mode == "LOG_ONLY"
    assert rows[0].raw["metric"] == "LogOnlyDecisionFlips"
    assert rows[0].raw["sum"] == 2.0
    dims = {d["Name"] for q in cw.queries for d in q["MetricStat"]["Metric"]["Dimensions"]}
    assert {"PolicyEngine", "OperationName", "Policy"} <= dims
    assert all(q["MetricStat"]["Metric"]["Namespace"] == "AWS/Bedrock-AgentCore"
               for q in cw.queries)


def test_engine_level_flips_count_when_no_policy_breakdown_exists() -> None:
    cw = FakeCloudWatch({("LogOnlyDecisionFlips", None): [1.0]})
    rows = pd.observe_metric_window(
        cloudwatch_client=cw, policy_engine_id=ENGINE, action_id=ACTION, start=START, end=END,
    )
    assert [(r.state, r.policy_id) for r in rows] == [("WOULD_DENY", None)]


def test_incomplete_evaluations_are_reported_and_matches_alone_are_not() -> None:
    cw = FakeCloudWatch({
        ("LogOnlyMatches", None): [5.0],
        ("LogOnlyEvalIncomplete", None): [1.0],
    })
    rows = pd.observe_metric_window(
        cloudwatch_client=cw, policy_engine_id=ENGINE, action_id=ACTION, start=START, end=END,
    )
    assert [r.state for r in rows] == ["EVALUATION_INCOMPLETE"]


def test_zero_valued_metrics_yield_no_rows() -> None:
    cw = FakeCloudWatch({
        ("LogOnlyMatches", None): [0.0],
        ("LogOnlyDecisionFlips", None): [0.0],
        ("LogOnlyEvalIncomplete", None): [],
    })
    assert pd.observe_metric_window(
        cloudwatch_client=cw, policy_engine_id=ENGINE, action_id=ACTION, start=START, end=END,
    ) == []


# ---------------------------------------------------------------------------
# The text scan can only infer
# ---------------------------------------------------------------------------


def test_the_text_scan_is_inferred_and_never_would_deny() -> None:
    engine_state = {
        "policy_engine_id": ENGINE,
        "gateway_mode": "LOG_ONLY",
        "policies": {"process_return_damaged_only": ("forbid", "ACTIVE"),
                     "baseline_permit": ("permit", "ACTIVE")},
        "policy_ids": {"process_return_damaged_only": "pol-1"},
        "matching": ["process_return_damaged_only"],
        "inferred": True,
    }
    rows = pd.inferred_from_policy_text(
        action_id=ACTION, matching_policies=["process_return_damaged_only"],
        engine_state=engine_state,
    )
    assert len(rows) == 1
    assert rows[0].state == "POLICY_INFERRED"
    assert rows[0].source == "policy-text"
    assert rows[0].policy_name == "process_return_damaged_only"
    assert rows[0].policy_id == "pol-1"
    assert rows[0].policy_mode == "ACTIVE"
    assert rows[0].engine_mode == "LOG_ONLY"
    assert "WOULD_DENY" not in {r.state for r in rows}


def test_no_matching_text_yields_no_inference() -> None:
    assert pd.inferred_from_policy_text(
        action_id=ACTION, matching_policies=[], engine_state={"policies": {}},
    ) == []


# ---------------------------------------------------------------------------
# Persistence and flips
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_links_a_reversal_to_the_prior_terminal_row() -> None:
    db = FakeDb(prior={"decision_id": 41, "state": "DENY"})
    ids = await pd.persist(
        db, [_obs("ALLOW", "governed-receipt")],
        session_id="operator-sub", turn_id="turn-" + "a" * 32, audit_id=9,
    )
    assert ids == [101]
    row = db.inserted[0]
    assert row["flip_of"] == 41
    assert row["state"] == "ALLOW"
    assert row["source"] == "governed-receipt"
    assert row["audit_id"] == 9
    assert row["turn_id"] == "turn-" + "a" * 32
    assert row["policy_engine_id"] == ENGINE
    assert json.loads(row["raw"]) == {}
    select_sql, select_params = next(
        (sql, params) for sql, params in db.statements
        if sql.lstrip().upper().startswith("SELECT") and "policy_decisions" in sql
    )
    assert "IN('ALLOW','DENY','WOULD_DENY')" in select_sql.replace(" ", "")
    assert select_params["principal_id"] == "sub-operator"
    assert select_params["resource"] == "gw-1"


@pytest.mark.asyncio
async def test_persist_does_not_flip_when_the_verdict_repeats_or_is_not_terminal() -> None:
    same = FakeDb(prior={"decision_id": 41, "state": "DENY"})
    await pd.persist(same, [_obs("WOULD_DENY")], session_id="s", turn_id="t", audit_id=None)
    assert same.inserted[0]["flip_of"] is None

    inferred = FakeDb(prior={"decision_id": 41, "state": "DENY"})
    await pd.persist(inferred, [_obs("POLICY_INFERRED", "policy-text")],
                     session_id="s", turn_id="t", audit_id=None)
    assert inferred.inserted[0]["flip_of"] is None
    # A non-terminal observation never even asks for a prior row.
    assert all(not sql.lstrip().upper().startswith("SELECT")
               for sql, _ in inferred.statements)


@pytest.mark.asyncio
async def test_persist_writes_nothing_for_no_observations() -> None:
    db = FakeDb()
    assert await pd.persist(db, [], session_id="s", turn_id="t", audit_id=None) == []
    assert db.statements == []


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_for_turn_combines_all_sources_and_reports_the_terminal_state() -> None:
    db = FakeDb()
    logs = FakeLogs([_span({"policy.engine.id": ENGINE, "policy.action": ACTION,
                            "policy.decision": "ALLOW"})])
    cw = FakeCloudWatch({("LogOnlyDecisionFlips", "pol-lo"): [1.0]})
    engine_state = {
        "policy_engine_id": ENGINE, "gateway_mode": "ENFORCE",
        "policies": {"process_return_damaged_only": ("forbid", "ACTIVE")},
        "policy_ids": {}, "matching": ["process_return_damaged_only"], "inferred": True,
    }
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="operator-sub", turn_id="turn-" + "b" * 32,
        audit_id=None, start=START, end=END,
        clients={"logs": logs, "cloudwatch": cw},
        prior=[_obs("ALLOW", "governed-receipt")], engine_state=engine_state,
        principal_id="sub-operator", resource="gw-1",
    )
    assert out["states"] == ["ALLOW", "ALLOW", "WOULD_DENY", "POLICY_INFERRED"]
    assert out["terminal"] == "WOULD_DENY"
    assert out["ids"] == [101, 102, 103, 104]
    sources = [row["source"] for row in db.inserted]
    assert sources == ["governed-receipt", "gateway-span", "cloudwatch-metric", "policy-text"]
    # Metrics are per-minute, so the metric window is widened around the turn.
    assert logs.started[0]["startTime"] == int(START.timestamp())


@pytest.mark.asyncio
async def test_collect_for_turn_records_one_incomplete_row_on_an_aws_error() -> None:
    db = FakeDb()
    logs = FakeLogs([], fail=RuntimeError("AccessDeniedException: logs:StartQuery"))
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END, clients={"logs": logs, "cloudwatch": FakeCloudWatch({})},
        engine_state={"policies": {}, "matching": [], "gateway_mode": "ENFORCE"},
    )
    assert out["states"] == ["EVALUATION_INCOMPLETE"]
    assert out["terminal"] == "EVALUATION_INCOMPLETE"
    raw = json.loads(db.inserted[0]["raw"])
    assert "AccessDeniedException" in raw["error"]
    assert db.inserted[0]["source"] == "gateway-span"


@pytest.mark.asyncio
async def test_collect_for_turn_uses_the_configured_span_log_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from config import settings

    monkeypatch.setattr(settings, "AGENTCORE_POLICY_SPAN_LOG_GROUP", "custom/spans",
                        raising=False)
    logs = FakeLogs([])
    await pd.collect_for_turn(
        FakeDb(), action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END, clients={"logs": logs, "cloudwatch": FakeCloudWatch({})},
        engine_state={"policies": {}, "matching": [], "gateway_mode": "ENFORCE"},
    )
    assert logs.started[0]["logGroupNames"] == ["custom/spans"]


@pytest.mark.asyncio
async def test_collect_for_turn_with_no_telemetry_records_incomplete_not_allow() -> None:
    db = FakeDb()
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END, clients={"logs": FakeLogs([]), "cloudwatch": FakeCloudWatch({})},
        engine_state={"policies": {}, "matching": [], "gateway_mode": "LOG_ONLY"},
    )
    assert out["states"] == ["EVALUATION_INCOMPLETE"]
    assert json.loads(db.inserted[0]["raw"])["reason"] == "no decision telemetry in window"


@pytest.mark.asyncio
async def test_collect_for_turn_without_an_engine_id_makes_no_aws_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from config import settings

    monkeypatch.setattr(settings, "AGENTCORE_POLICY_ENGINE_ID", "", raising=False)
    monkeypatch.delenv("AGENTCORE_POLICY_ENGINE_ID", raising=False)
    logs = FakeLogs([])
    db = FakeDb()
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END, clients={"logs": logs, "cloudwatch": FakeCloudWatch({})},
    )
    assert logs.started == []
    assert out["states"] == ["EVALUATION_INCOMPLETE"]
    assert "engine" in json.loads(db.inserted[0]["raw"])["reason"]


# ---------------------------------------------------------------------------
# Bounded telemetry: the operator's Execute request must not hang on CloudWatch
# ---------------------------------------------------------------------------
#
# Every reader here runs on the request path AFTER the write has executed. A
# slow or wedged CloudWatch must degrade the receipt to EVALUATION_INCOMPLETE,
# never hold the response open.


class _BlockingCloudWatch:
    """list_metrics blocks until the test releases it.

    An Event rather than a sleep: the abandoned worker thread has to be able to
    finish promptly, or every later test waits for it at interpreter exit.
    """

    def __init__(self) -> None:
        self.release = threading.Event()
        self.calls = 0

    def list_metrics(self, **_kwargs: Any) -> Dict[str, Any]:
        self.calls += 1
        self.release.wait(timeout=30.0)
        return {"Metrics": []}

    def get_metric_data(self, **_kwargs: Any) -> Dict[str, Any]:
        return {"MetricDataResults": []}


class _EndlessPaginator:
    """Every list_metrics page offers another NextToken, forever."""

    def __init__(self) -> None:
        self.calls = 0

    def list_metrics(self, **_kwargs: Any) -> Dict[str, Any]:
        self.calls += 1
        return {"Metrics": [], "NextToken": f"page-{self.calls}"}

    def get_metric_data(self, **_kwargs: Any) -> Dict[str, Any]:
        return {"MetricDataResults": []}


class _HangingLogs:
    """start_query answers; get_query_results does not, until released."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.stopped: List[str] = []

    def start_query(self, **_kwargs: Any) -> Dict[str, Any]:
        return {"queryId": "q-hung"}

    def get_query_results(self, queryId: str) -> Dict[str, Any]:  # noqa: N803
        self.release.wait(timeout=30.0)
        return {"status": "Running"}

    def stop_query(self, queryId: str) -> Dict[str, Any]:  # noqa: N803
        self.stopped.append(queryId)
        return {"success": True}


def test_the_aws_clients_are_built_with_short_timeouts_and_a_retry_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """botocore's defaults are 60s reads and four retries. Not on this path."""
    captured: List[Dict[str, Any]] = []

    class _FakeBoto3:
        @staticmethod
        def client(service: str, **kwargs: Any) -> str:
            captured.append({"service": service, **kwargs})
            return f"client-{service}"

    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3)
    logs, cloudwatch = pd._resolve_clients(None)
    assert (logs, cloudwatch) == ("client-logs", "client-cloudwatch")
    assert [c["service"] for c in captured] == ["logs", "cloudwatch"]
    for call in captured:
        config = call["config"]
        assert config.connect_timeout <= 5
        assert config.read_timeout <= 10
        assert config.retries["max_attempts"] <= 2


def test_the_metric_discovery_loop_is_bounded() -> None:
    """A NextToken that never runs out cannot become an unbounded page walk."""
    client = _EndlessPaginator()
    found = pd._discover_metrics(client, ENGINE, ACTION)
    assert found == []
    assert client.calls <= len(pd.LOG_ONLY_METRICS) * pd._DISCOVERY_PAGE_LIMIT


@pytest.mark.asyncio
async def test_a_slow_metric_read_is_abandoned_and_recorded_as_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The write already happened. A wedged CloudWatch costs the reading, not the turn."""
    monkeypatch.setattr(pd, "_METRIC_DEADLINE_S", 0.2)
    cloudwatch = _BlockingCloudWatch()
    db = FakeDb()
    began = time.monotonic()
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END, clients={"logs": FakeLogs([]), "cloudwatch": cloudwatch},
        engine_state={"policies": {}, "matching": [], "gateway_mode": "ENFORCE"},
    )
    cloudwatch.release.set()
    assert time.monotonic() - began < 5.0
    assert out["terminal"] == "EVALUATION_INCOMPLETE"
    raw = json.loads(db.inserted[0]["raw"])
    assert raw["stage"] == "cloudwatch-metric"
    assert "TimeoutError" in raw["error"]


@pytest.mark.asyncio
async def test_a_hung_results_poll_times_out_and_stops_the_query() -> None:
    """The poll deadline has to bound the call, not only the gap between calls."""
    logs = _HangingLogs()
    began = time.monotonic()
    with pytest.raises(TimeoutError):
        await pd.observe_span_decisions(
            logs_client=logs, log_group="aws/spans", action_id=ACTION,
            start=START, end=END, poll_interval_s=0.01, timeout_s=0.2,
        )
    logs.release.set()
    assert time.monotonic() - began < 5.0
    # An abandoned Insights query keeps burning the account's concurrency budget.
    assert logs.stopped == ["q-hung"]


class _HangingStartQuery:
    """start_query is the call that does not answer, until released.

    Its sibling deadline covers the result poll. Without one here, a Logs
    endpoint that accepts the connection and then stalls holds the operator's
    response open for whatever botocore's own budget happens to be.
    """

    def __init__(self) -> None:
        self.release = threading.Event()
        self.stopped: List[str] = []

    def start_query(self, **_kwargs: Any) -> Dict[str, Any]:
        self.release.wait(timeout=30.0)
        return {"queryId": "q-late"}

    def get_query_results(self, queryId: str) -> Dict[str, Any]:  # noqa: N803
        return {"status": "Complete", "results": []}

    def stop_query(self, queryId: str) -> Dict[str, Any]:  # noqa: N803
        self.stopped.append(queryId)
        return {"success": True}


@pytest.mark.asyncio
async def test_a_hung_start_query_times_out_within_the_span_budget() -> None:
    """timeout_s bounds the whole span read, not only the polling half of it."""
    logs = _HangingStartQuery()
    began = time.monotonic()
    with pytest.raises(TimeoutError):
        await pd.observe_span_decisions(
            logs_client=logs, log_group="aws/spans", action_id=ACTION,
            start=START, end=END, poll_interval_s=0.01, timeout_s=0.2,
        )
    logs.release.set()
    assert time.monotonic() - began < 5.0


# ---------------------------------------------------------------------------
# Bounded control plane: the Cedar text scan must not hold the turn open either
# ---------------------------------------------------------------------------
#
# When the caller supplies no engine_state, collect_for_turn reads the policy
# engine itself. That read is bedrock-agentcore-control, and it happens on the
# response path after the governed write has already executed.


class _BlockingControlPlane:
    """list_policies blocks until the test releases it.

    An Event rather than a sleep, for the same reason as _BlockingCloudWatch:
    the abandoned worker thread has to be able to finish promptly, or every
    later test waits for it at interpreter exit.
    """

    def __init__(self) -> None:
        self.release = threading.Event()
        self.calls = 0

    def get_gateway(self, **_kwargs: Any) -> Dict[str, Any]:
        return {}

    def list_policies(self, **_kwargs: Any) -> Dict[str, Any]:
        self.calls += 1
        self.release.wait(timeout=30.0)
        return {"policies": []}

    def get_policy(self, **_kwargs: Any) -> Dict[str, Any]:
        return {}


class _FailingControlPlane:
    """Every read raises, and the object counts how many were attempted."""

    def __init__(self) -> None:
        self.calls = 0

    def get_gateway(self, **_kwargs: Any) -> Dict[str, Any]:
        return {}

    def list_policies(self, **_kwargs: Any) -> Dict[str, Any]:
        self.calls += 1
        raise RuntimeError("control plane unreachable")

    def get_policy(self, **_kwargs: Any) -> Dict[str, Any]:
        return {}


def _control_plane_is(monkeypatch: pytest.MonkeyPatch, client: Any) -> None:
    import boto3

    monkeypatch.setattr(boto3, "client", lambda *_a, **_k: client)


def test_the_control_plane_client_is_built_with_short_timeouts_and_a_retry_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both telemetry clients were bounded and this one, on the same path, was not."""
    from services import managed_policy as mp

    captured: List[Dict[str, Any]] = []

    class _FakeBoto3:
        @staticmethod
        def client(service: str, **kwargs: Any) -> str:
            captured.append({"service": service, **kwargs})
            return f"client-{service}"

    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3)
    assert mp._control_client() == "client-bedrock-agentcore-control"
    assert captured[0]["service"] == "bedrock-agentcore-control"
    config = captured[0]["config"]
    assert config.connect_timeout <= 5
    assert config.read_timeout <= 10
    assert config.retries["max_attempts"] <= 2


@pytest.mark.asyncio
async def test_a_wedged_control_plane_read_is_abandoned_and_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The governed write already happened. A stalled control plane costs the scan."""
    from services import managed_policy as mp

    monkeypatch.setattr(mp, "_CONTROL_DEADLINE_S", 0.2)
    control = _BlockingControlPlane()
    _control_plane_is(monkeypatch, control)
    db = FakeDb()
    began = time.monotonic()
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END,
        clients={"logs": FakeLogs([]), "cloudwatch": FakeCloudWatch({})},
        engine_state=None,
    )
    control.release.set()
    assert time.monotonic() - began < 5.0
    assert out["terminal"] == "EVALUATION_INCOMPLETE"
    raw = json.loads(db.inserted[0]["raw"])
    assert raw["stage"] == pd.SOURCE_TEXT
    assert "TimeoutError" in raw["error"]


@pytest.mark.asyncio
async def test_the_control_plane_read_does_not_block_the_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A synchronous boto3 read inside an async function stalls every other request.

    The ticker is the assertion: it can only advance while the control-plane
    read is outstanding if that read left the loop free.
    """
    from services import managed_policy as mp

    monkeypatch.setattr(mp, "_CONTROL_DEADLINE_S", 0.5)
    control = _BlockingControlPlane()
    _control_plane_is(monkeypatch, control)
    ticks = 0

    async def _tick() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    ticker = asyncio.ensure_future(_tick())
    try:
        await pd.collect_for_turn(
            FakeDb(), action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
            start=START, end=END,
            clients={"logs": FakeLogs([]), "cloudwatch": FakeCloudWatch({})},
            engine_state=None,
        )
    finally:
        ticker.cancel()
        control.release.set()
    assert ticks >= 5, f"the event loop was blocked: only {ticks} ticks ran"


@pytest.mark.asyncio
async def test_the_cedar_scan_is_skipped_after_the_caller_already_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The operator route reads the engine first and swallows the failure.

    Re-running the read that just failed is wasted latency on exactly the
    deployment least able to afford it, so the second attempt is skipped and
    the receipt records that the evaluation was incomplete and why.
    """
    from services import managed_policy as mp

    control = _FailingControlPlane()
    _control_plane_is(monkeypatch, control)
    with pytest.raises(RuntimeError):
        await mp.engine_state_for_action(ACTION)
    assert control.calls == 1

    db = FakeDb()
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END,
        clients={"logs": FakeLogs([]), "cloudwatch": FakeCloudWatch({})},
        engine_state=None,
    )
    assert control.calls == 1, "the control plane was read a second time"
    assert out["terminal"] == "EVALUATION_INCOMPLETE"
    raw = json.loads(db.inserted[0]["raw"])
    assert raw["stage"] == pd.SOURCE_TEXT
    assert "skipped" in raw["error"]
    assert "control plane unreachable" in raw["error"]


def test_the_collection_entry_point_stays_within_the_length_limit() -> None:
    """100 lines per function is a hard limit, and this one grew past it.

    The sources it sequences are the contract, so the guard is on the entry
    point rather than on the file: the next source belongs in a named helper.
    """
    import inspect

    for name in ("collect_for_turn", "_observations_for_window"):
        length = len(inspect.getsource(getattr(pd, name)).splitlines())
        assert length <= 100, f"{name} is {length} lines"


@pytest.mark.asyncio
async def test_a_metric_reading_declares_its_minute_granularity() -> None:
    """The receipt wording depends on the source, so the source must be reported.

    A CloudWatch flip is a 60-second Sum over a window padded a further minute
    on each side. Persisted and returned as such, so nothing downstream can
    present it as a decision about one call.
    """
    db = FakeDb()
    cw = FakeCloudWatch({("LogOnlyDecisionFlips", "pol-lo"): [1.0]})
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END, clients={"logs": FakeLogs([]), "cloudwatch": cw},
        engine_state={"policies": {}, "matching": [], "gateway_mode": "LOG_ONLY"},
        principal_id="sub-operator", resource="gw-1",
    )
    assert out["terminal"] == "WOULD_DENY"
    assert out["terminal_source"] == pd.SOURCE_METRIC
    raw = json.loads(db.inserted[0]["raw"])
    assert raw["granularity"] == "minute"
    assert "another execution of this action" in raw["note"]


@pytest.mark.asyncio
async def test_the_terminal_source_names_the_span_when_a_span_decided() -> None:
    db = FakeDb()
    logs = FakeLogs([_span({"policy.engine.id": ENGINE, "policy.action": ACTION,
                            "policy.decision": "DENY"})])
    out = await pd.collect_for_turn(
        db, action_id=ACTION, session_id="s", turn_id="t", audit_id=None,
        start=START, end=END, clients={"logs": logs, "cloudwatch": FakeCloudWatch({})},
        engine_state={"policies": {}, "matching": [], "gateway_mode": "ENFORCE"},
    )
    assert out["terminal"] == "DENY"
    assert out["terminal_source"] == pd.SOURCE_SPAN


# ---------------------------------------------------------------------------
# The flip link is decided under a lock, not in a read-then-write window
# ---------------------------------------------------------------------------


class _ConcurrentDb:
    """A fake that models what a real transaction does: locks, and isolation.

    Rows a transaction inserted are invisible to the other transaction until it
    commits, and ``pg_advisory_xact_lock`` blocks the second holder of a key
    until the first commits. That pair is the whole point: without the lock the
    second reader looks at the table before the first insert is visible.
    """

    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []
        self.locks: Dict[str, asyncio.Lock] = {}
        self.next_id = 100

    def get_connection(self) -> "_ConcurrentConn":
        return _ConcurrentConn(self)


class _ConcurrentConn:
    def __init__(self, db: _ConcurrentDb) -> None:
        self.db = db
        self.pending: List[Dict[str, Any]] = []
        self.held: List[asyncio.Lock] = []

    def cursor(self) -> "_ConcurrentCur":
        return _ConcurrentCur(self)

    async def __aenter__(self) -> "_ConcurrentConn":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        self.db.rows.extend(self.pending)  # commit
        for lock in self.held:
            lock.release()


class _ConcurrentCur:
    def __init__(self, conn: _ConcurrentConn) -> None:
        self.conn = conn
        self._row: Optional[Dict[str, Any]] = None

    async def execute(self, sql: str, params: Any = None) -> None:
        await asyncio.sleep(0)  # a real await point, so the tasks interleave
        text = sql.strip()
        if "pg_advisory_xact_lock" in text:
            lock = self.conn.db.locks.setdefault(params["lock_key"], asyncio.Lock())
            await lock.acquire()
            self.conn.held.append(lock)
            self._row = None
        elif text.upper().startswith("SELECT"):
            matches = [
                row for row in self.conn.db.rows
                if (row["principal_id"], row["action_id"], row["resource"])
                == (params["principal_id"], params["action_id"], params["resource"])
                and row["state"] in pd.TERMINAL_STATES
            ]
            self._row = matches[-1] if matches else None
        else:
            self.conn.db.next_id += 1
            row = dict(params)
            row["decision_id"] = self.conn.db.next_id
            self.conn.pending.append(row)
            self._row = {"decision_id": row["decision_id"]}

    async def fetchone(self) -> Optional[Dict[str, Any]]:
        return self._row

    async def __aenter__(self) -> "_ConcurrentCur":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_two_concurrent_decisions_on_one_triple_still_link_one_flip() -> None:
    """The ALLOW must be committed and visible before the DENY reads for a flip."""
    db = _ConcurrentDb()
    allow = _obs("ALLOW", "gateway-span")
    deny = _obs("DENY", "gateway-span")
    first, second = await asyncio.gather(
        pd.persist(db, [allow], session_id="s", turn_id="t1", audit_id=None),
        pd.persist(db, [deny], session_id="s", turn_id="t2", audit_id=None),
    )
    assert len(db.rows) == 2
    by_id = {row["decision_id"]: row for row in db.rows}
    later = by_id[max(first[0], second[0])]
    earlier = by_id[min(first[0], second[0])]
    assert earlier["flip_of"] is None
    assert later["flip_of"] == earlier["decision_id"], (
        "the second decision read the table before the first was committed"
    )


@pytest.mark.asyncio
async def test_the_flip_lock_is_keyed_on_the_triple_not_the_whole_table() -> None:
    """Different actions must not serialize behind each other."""
    db = FakeDb()
    await pd.persist(
        db, [_obs("ALLOW", "gateway-span")], session_id="s", turn_id="t", audit_id=None,
    )
    lock_calls = [p for sql, p in db.statements if "pg_advisory_xact_lock" in sql]
    assert lock_calls, "the flip read must be serialized"
    assert lock_calls[0]["lock_key"] == f"sub-operator|{ACTION}|gw-1"
