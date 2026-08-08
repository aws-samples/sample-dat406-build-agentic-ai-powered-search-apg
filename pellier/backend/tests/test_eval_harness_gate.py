"""Tests for the retrieval harness's CI gate and scoring layers.

The harness itself needs Aurora and Bedrock, so these tests exercise the
pure functions: threshold evaluation, planner scoring, and hard-constraint
compliance. Those are the parts that decide whether CI passes, and before
this suite existed the harness returned exit code 0 unconditionally — a
relevance regression was invisible to CI by construction.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_HARNESS_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "eval_retrieval_harness.py"
)


def _load_harness() -> Any:
    """Import the standalone harness script as a module.

    The module must be registered in ``sys.modules`` before execution:
    its dataclasses are defined under ``from __future__ import
    annotations``, and ``dataclasses`` resolves a class's module by name
    at decoration time.
    """
    import sys

    spec = importlib.util.spec_from_file_location(
        "eval_retrieval_harness", _HARNESS_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def harness() -> Any:
    return _load_harness()


def _healthy_totals() -> dict[str, dict[str, float]]:
    return {
        "vector": {"recall_at_5": 0.60, "mrr_at_5": 0.50},
        "hybrid": {"recall_at_5": 0.75, "mrr_at_5": 0.60},
        "rerank": {"recall_at_5": 0.85, "mrr_at_5": 0.70},
        "agentic": {"recall_at_5": 0.80, "mrr_at_5": 0.68},
    }


def _clean_planner() -> dict[str, float]:
    return {
        "constraints_expected": 10,
        "constraints_recovered": 8,
        "constraint_recall": 0.80,
        "hallucinated_constraints": 0,
        "hallucinated_constraint_rate": 0.0,
    }


def _clean_compliance() -> dict[str, float]:
    return {
        "rows_scored": 75,
        "hard_violations": 0,
        "hard_constraint_violation_rate": 0.0,
        "exclusion_violations": 0,
        "exclusion_violation_rate": 0.0,
    }


def _gate(harness: Any, **overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "totals": _healthy_totals(),
        "coverage": 0.90,
        "planner": _clean_planner(),
        "compliance": _clean_compliance(),
        "strict_planner": False,
    }
    kwargs.update(overrides)
    return harness._evaluate_gate(**kwargs)


# ---------------------------------------------------------------------------
# Gate: healthy run
# ---------------------------------------------------------------------------
def test_healthy_run_passes(harness: Any) -> None:
    verdict = _gate(harness)

    assert verdict["passed"] is True
    assert verdict["failures"] == []


# ---------------------------------------------------------------------------
# Gate: quality regressions
# ---------------------------------------------------------------------------
def test_recall_regression_fails_the_gate(harness: Any) -> None:
    totals = _healthy_totals()
    totals["rerank"]["recall_at_5"] = 0.40

    verdict = _gate(harness, totals=totals)

    assert verdict["passed"] is False
    assert any("recall@5" in failure for failure in verdict["failures"])


def test_mrr_regression_fails_the_gate(harness: Any) -> None:
    totals = _healthy_totals()
    totals["rerank"]["mrr_at_5"] = 0.10

    verdict = _gate(harness, totals=totals)

    assert verdict["passed"] is False
    assert any("mrr@5" in failure for failure in verdict["failures"])


def test_candidate_coverage_regression_fails_the_gate(harness: Any) -> None:
    verdict = _gate(harness, coverage=0.10)

    assert verdict["passed"] is False
    assert any("coverage" in failure for failure in verdict["failures"])


# ---------------------------------------------------------------------------
# Gate: correctness budgets are zero-tolerance
# ---------------------------------------------------------------------------
def test_a_single_hard_constraint_violation_fails_the_gate(harness: Any) -> None:
    """One violated hard constraint is a bug, not an averageable metric."""
    compliance = _clean_compliance()
    compliance["hard_violations"] = 1
    compliance["hard_constraint_violation_rate"] = 0.013

    verdict = _gate(harness, compliance=compliance)

    assert verdict["passed"] is False
    assert any("hard-constraint" in failure for failure in verdict["failures"])


def test_a_single_exclusion_violation_fails_the_gate(harness: Any) -> None:
    compliance = _clean_compliance()
    compliance["exclusion_violations"] = 1
    compliance["exclusion_violation_rate"] = 0.013

    verdict = _gate(harness, compliance=compliance)

    assert verdict["passed"] is False
    assert any("exclusion" in failure for failure in verdict["failures"])


def test_hallucinated_constraint_fails_the_gate(harness: Any) -> None:
    """An invented hard constraint silently removes valid results."""
    planner = _clean_planner()
    planner["hallucinated_constraints"] = 1
    planner["hallucinated_constraint_rate"] = 0.067

    verdict = _gate(harness, planner=planner)

    assert verdict["passed"] is False
    assert any("hallucinated" in failure for failure in verdict["failures"])


# ---------------------------------------------------------------------------
# Gate: planner recall is opt-in
# ---------------------------------------------------------------------------
def test_low_planner_recall_passes_unless_strict(harness: Any) -> None:
    planner = _clean_planner()
    planner["constraint_recall"] = 0.20

    assert _gate(harness, planner=planner)["passed"] is True
    strict = _gate(harness, planner=planner, strict_planner=True)
    assert strict["passed"] is False
    assert any("constraint recall" in f for f in strict["failures"])


def test_gate_reports_its_thresholds(harness: Any) -> None:
    verdict = _gate(harness)

    assert verdict["thresholds"]["hard_constraint_violation_rate_max"] == 0.0
    assert verdict["thresholds"]["rerank_recall_at_5_min"] > 0


# ---------------------------------------------------------------------------
# Planner scoring
# ---------------------------------------------------------------------------
def test_planner_score_credits_a_recovered_constraint(harness: Any) -> None:
    from services.search_plan import build_plan

    plan = build_plan(
        "linen under $200",
        {"categories": ["Apparel"], "price_max_usd": 200},
    )
    expected = harness.Filters(categories=("Apparel",), price_max=200.0)

    score = harness._score_plan(plan, expected)

    assert score["constraints_recovered"] == 2
    assert score["constraints_expected"] == 2
    assert score["hallucinated_constraints"] == 0


def test_planner_score_flags_a_missed_constraint(harness: Any) -> None:
    from services.search_plan import build_plan

    plan = build_plan("linen shirts", {})
    expected = harness.Filters(categories=("Apparel",), price_max=200.0)

    score = harness._score_plan(plan, expected)

    assert score["constraints_recovered"] == 0
    assert score["constraints_expected"] == 2


def test_planner_score_flags_an_invented_price_ceiling(harness: Any) -> None:
    from services.search_plan import build_plan

    plan = build_plan("linen shirts", {"price_max_usd": 50})
    expected = harness.Filters()

    score = harness._score_plan(plan, expected)

    assert score["hallucinated_constraints"] == 1


# ---------------------------------------------------------------------------
# Compliance scoring
# ---------------------------------------------------------------------------
def test_compliance_counts_an_over_budget_row(harness: Any) -> None:
    from services.search_plan import build_plan

    plan = build_plan("gift under $100", {"price_max_usd": 100})
    rows = [
        {"price": 90.0, "category": "Gifts", "tags": []},
        {"price": 250.0, "category": "Gifts", "tags": []},
    ]

    score = harness._score_compliance(rows, plan)

    assert score["rows"] == 2
    assert score["hard_violations"] == 1


def test_compliance_counts_an_excluded_tag(harness: Any) -> None:
    from services.search_plan import build_plan

    plan = build_plan("gift, no candles", {"exclusions": ["candle"]})
    rows = [
        {"price": 20.0, "category": "Gifts", "tags": ["candle"]},
        {"price": 20.0, "category": "Gifts", "tags": ["home"]},
    ]

    score = harness._score_compliance(rows, plan)

    assert score["exclusion_violations"] == 1


def test_compliance_is_clean_when_every_row_is_valid(harness: Any) -> None:
    from services.search_plan import build_plan

    plan = build_plan(
        "in-stock gift under $100, no candles",
        {"price_max_usd": 100, "in_stock_only": True, "exclusions": ["candle"]},
    )
    rows = [{"price": 40.0, "category": "Gifts", "tags": ["home"]}]

    score = harness._score_compliance(rows, plan)

    assert score["hard_violations"] == 0
    assert score["exclusion_violations"] == 0


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def test_planner_totals_aggregate_rates(harness: Any) -> None:
    totals = harness._planner_totals(
        [
            {
                "constraints_expected": 2,
                "constraints_recovered": 2,
                "hallucinated_constraints": 0,
            },
            {
                "constraints_expected": 2,
                "constraints_recovered": 1,
                "hallucinated_constraints": 1,
            },
        ]
    )

    assert totals["constraint_recall"] == 0.75
    assert totals["hallucinated_constraint_rate"] == 0.5


def test_compliance_totals_aggregate_rates(harness: Any) -> None:
    totals = harness._compliance_totals(
        [
            {"rows": 5, "hard_violations": 1, "exclusion_violations": 0},
            {"rows": 5, "hard_violations": 0, "exclusion_violations": 1},
        ]
    )

    assert totals["rows_scored"] == 10
    assert totals["hard_constraint_violation_rate"] == 0.1
    assert totals["exclusion_violation_rate"] == 0.1


def test_plan_filters_drop_soft_tags(harness: Any) -> None:
    """Only hard constraints reach the SQL filter for the agentic row."""
    from services.search_plan import build_plan

    plan = build_plan(
        "gift under $100",
        {"categories": ["Gifts"], "tags": ["home"], "price_max_usd": 100},
    )

    filters = harness._plan_filters(plan)

    assert filters.categories == ("Gifts",)
    assert filters.price_max == 100.0
    assert filters.tags == ()
