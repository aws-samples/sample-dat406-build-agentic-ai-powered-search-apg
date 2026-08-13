"""Tests for durable retrieval receipts.

``pellier.tool_audit`` proves a tool ran. A retrieval receipt proves *why*
a particular product won: which constraints were hard, which preferences
were widened, how each branch ranked the pool, and which merchandising
rule reordered the final list.

Two properties matter most here:

  * The receipt records what actually happened, and stays silent about
    what did not. An empty ``rerank_scores`` means rerank did not run —
    that absence is evidence, so it must not be back-filled.
  * Writing a receipt can never break the turn it describes.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from services.retrieval_receipt import (
    build_receipt,
    current_turn_context,
    persist_receipt,
    query_hash,
    reset_turn_context,
    receipt_params,
    set_turn_context,
)
from services.search_plan import build_plan


def _plan() -> Any:
    return build_plan(
        "in-stock housewarming gift under $100, no candles",
        {
            "categories": ["Home Decor"],
            "tags": ["home"],
            "price_max_usd": 100,
            "in_stock_only": True,
            "exclusions": ["candle"],
            "soft_signal": "thoughtful housewarming gift",
        },
    )


def _candidates() -> List[Dict[str, Any]]:
    return [
        {"product_id": 1, "vec_rank": 1, "fts_rank": 3, "rrf_score": 0.032},
        {"product_id": 2, "vec_rank": 2, "rrf_score": 0.016},
        {"product_id": 3, "fts_rank": 1, "rrf_score": 0.016},
    ]


def _ordered() -> List[Dict[str, Any]]:
    return [
        {"product_id": 3, "rerank_score": 0.91},
        {"product_id": 1, "rerank_score": 0.62},
    ]


# ---------------------------------------------------------------------------
# Query hashing
# ---------------------------------------------------------------------------
def test_query_hash_is_stable_across_casing_and_whitespace() -> None:
    assert query_hash("Under $100 Gift") == query_hash("under $100  gift")


def test_query_hash_differs_for_different_queries() -> None:
    assert query_hash("linen shirt") != query_hash("wool coat")


def test_receipt_stores_a_hash_and_only_a_short_preview() -> None:
    """The raw query is not retained in full."""
    long_query = "gift " * 100
    receipt = build_receipt(query=long_query, plan=_plan())

    row = receipt.to_row()

    assert len(row["query_hash"]) == 64
    assert len(row["query_preview"]) <= 120


# ---------------------------------------------------------------------------
# Plan capture
# ---------------------------------------------------------------------------
def test_receipt_captures_hard_constraints_and_exclusions() -> None:
    receipt = build_receipt(query="gift", plan=_plan())

    row = receipt.to_row()

    assert row["hard_constraints"]["price_max_usd"] == 100.0
    assert row["hard_constraints"]["in_stock_only"] is True
    assert row["exclusions"] == ["candle"]
    assert row["soft_preferences"]["tags"] == ["home"]


def test_receipt_records_applied_relaxations() -> None:
    """A widened plan must say what it widened."""
    _, widened = _plan().relaxation_ladder()
    receipt = build_receipt(query="gift", plan=widened)

    row = receipt.to_row()

    assert [r["step"] for r in row["relaxations"]] == ["drop_tags"]
    # And the hard constraints survived the widening.
    assert row["hard_constraints"]["price_max_usd"] == 100.0


# ---------------------------------------------------------------------------
# Per-stage rank capture
# ---------------------------------------------------------------------------
def test_receipt_captures_per_branch_ranks_and_scores() -> None:
    receipt = build_receipt(
        query="gift", plan=_plan(), candidates=_candidates(), ordered=_ordered()
    )

    row = receipt.to_row()

    assert row["candidate_product_ids"] == ["1", "2", "3"]
    assert row["vector_ranks"] == {"1": 1, "2": 2}
    assert row["lexical_ranks"] == {"1": 3, "3": 1}
    assert row["rrf_scores"]["1"] == pytest.approx(0.032)
    assert row["rerank_scores"] == {"3": 0.91, "1": 0.62}
    assert row["citation_ids"] == ["3", "1"]


def test_absent_rerank_stays_absent() -> None:
    """No rerank scores means rerank did not run — do not fabricate them."""
    receipt = build_receipt(
        query="gift",
        plan=_plan(),
        candidates=_candidates(),
        ordered=[{"product_id": 1, "rerank_score": None}],
    )

    row = receipt.to_row()

    assert row["rerank_scores"] == {}
    assert row["citation_ids"] == ["1"]


def test_rows_without_a_product_id_are_skipped() -> None:
    receipt = build_receipt(
        query="gift",
        plan=_plan(),
        candidates=[{"vec_rank": 1}, {"product_id": 7, "vec_rank": 2}],
    )

    assert receipt.to_row()["candidate_product_ids"] == ["7"]


def test_camel_case_product_id_is_accepted() -> None:
    """Normalized tool output uses productId; raw SQL rows use product_id."""
    receipt = build_receipt(
        query="gift", plan=_plan(), ordered=[{"productId": 9, "rerank_score": 0.5}]
    )

    assert receipt.to_row()["citation_ids"] == ["9"]


# ---------------------------------------------------------------------------
# Merchandising disclosure
# ---------------------------------------------------------------------------
def test_receipt_records_merchandising_rules() -> None:
    """A non-relevance ranking signal must be subtractable from evaluation."""
    receipt = build_receipt(
        query="milestone gift",
        plan=_plan(),
        merchandising_rules=[
            {"ruleId": "merch.milestone-home-gift.v1", "fromRank": 4, "toRank": 1}
        ],
    )

    rules = receipt.to_row()["merchandising_rules"]

    assert rules[0]["ruleId"] == "merch.milestone-home-gift.v1"


def test_no_merchandising_rules_is_an_empty_list() -> None:
    receipt = build_receipt(query="gift", plan=_plan())

    assert receipt.to_row()["merchandising_rules"] == []


# ---------------------------------------------------------------------------
# Provenance and correlation
# ---------------------------------------------------------------------------
def test_receipt_carries_model_and_config_provenance() -> None:
    receipt = build_receipt(
        query="gift",
        plan=_plan(),
        embedding_model="us.cohere.embed-v4:0",
        rerank_model="cohere.rerank-v3-5:0",
        retrieval_config={"k_vector": 20, "rrf_k": 60},
        trace_id="trace-abc",
        rail="gateway-mcp",
        session_id="sess-1",
        principal_sub="sub-1",
    )

    row = receipt.to_row()

    assert row["embedding_model"] == "us.cohere.embed-v4:0"
    assert row["rerank_model"] == "cohere.rerank-v3-5:0"
    assert row["retrieval_config"]["rrf_k"] == 60
    assert row["trace_id"] == "trace-abc"
    assert row["rail"] == "gateway-mcp"
    assert row["session_id"] == "sess-1"
    assert row["principal_sub"] == "sub-1"


def test_anonymous_turn_has_no_principal() -> None:
    """A demo persona is never promoted into the principal column."""
    assert build_receipt(query="gift", plan=_plan()).to_row()["principal_sub"] is None


def test_route_turn_context_carries_only_trusted_correlation_fields() -> None:
    token = set_turn_context(
        turn_id="turn-1",
        session_id="session-1",
        principal_sub="principal-1",
        rail="in-process",
    )
    try:
        assert current_turn_context() == {
            "turn_id": "turn-1",
            "session_id": "session-1",
            "principal_sub": "principal-1",
            "rail": "in-process",
        }
    finally:
        reset_turn_context(token)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def test_params_align_with_the_insert_placeholders() -> None:
    from services.retrieval_receipt import _INSERT_SQL

    params = receipt_params(build_receipt(query="gift", plan=_plan()))

    assert _INSERT_SQL.count("%s") == len(params)


def test_json_columns_are_serialized_strings() -> None:
    params = receipt_params(
        build_receipt(query="gift", plan=_plan(), candidates=_candidates())
    )

    # ``turn_id`` is the first column, so search_plan binds in position 6.
    # Every JSON column binds as text.
    plan_param = params[5]
    assert isinstance(plan_param, str)
    assert json.loads(plan_param)["hard_constraints"]["price_max_usd"] == 100.0


def test_persist_receipt_writes_one_row() -> None:
    calls: List[tuple[Any, ...]] = []

    class _DB:
        async def execute_query(self, *args: Any) -> None:
            calls.append(args)

    import asyncio

    ok = asyncio.run(persist_receipt(_DB(), build_receipt(query="gift", plan=_plan())))

    assert ok is True
    assert len(calls) == 1
    assert "INSERT INTO pellier.retrieval_receipts" in calls[0][0]


def test_persist_receipt_never_raises_on_db_failure() -> None:
    """Evidence collection must not break the turn it describes."""

    class _DB:
        async def execute_query(self, *args: Any) -> None:
            raise RuntimeError("connection reset")

    import asyncio

    assert (
        asyncio.run(persist_receipt(_DB(), build_receipt(query="gift", plan=_plan())))
        is False
    )


def test_persist_receipt_is_a_noop_without_a_db() -> None:
    import asyncio

    assert asyncio.run(persist_receipt(None, build_receipt(query="g", plan=_plan()))) is False


# ---------------------------------------------------------------------------
# Planner extraction flag on the shipped path
# ---------------------------------------------------------------------------
def test_extractor_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second Sonnet call per search is opt-in, not the default."""
    import services.agent_tools as agent_tools
    from config import settings

    monkeypatch.setattr(
        settings, "SEARCH_PLANNER_EXTRACT_ENABLED", False, raising=False
    )

    def _boom() -> Any:  # pragma: no cover - must never be reached
        raise AssertionError("extractor should not be constructed when disabled")

    import services.structured_extract as extract_module

    monkeypatch.setattr(extract_module, "get_structured_extractor", _boom)

    assert agent_tools._extract_query_structure("gift under $100") is None


def test_extractor_runs_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.agent_tools as agent_tools
    import services.structured_extract as extract_module
    from config import settings

    monkeypatch.setattr(
        settings, "SEARCH_PLANNER_EXTRACT_ENABLED", True, raising=False
    )

    class _Extractor:
        def extract(self, query: str) -> Dict[str, Any]:
            return {"price_max_usd": 100, "soft_signal": query}

    monkeypatch.setattr(
        extract_module, "get_structured_extractor", lambda: _Extractor()
    )

    result = agent_tools._extract_query_structure("gift under $100")

    assert result is not None
    assert result["price_max_usd"] == 100


def test_extractor_failure_degrades_to_no_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Bedrock failure must not fail the shopper's search."""
    import services.agent_tools as agent_tools
    import services.structured_extract as extract_module
    from config import settings

    monkeypatch.setattr(
        settings, "SEARCH_PLANNER_EXTRACT_ENABLED", True, raising=False
    )

    class _Extractor:
        def extract(self, query: str) -> Dict[str, Any]:
            raise RuntimeError("ThrottlingException")

    monkeypatch.setattr(
        extract_module, "get_structured_extractor", lambda: _Extractor()
    )

    assert agent_tools._extract_query_structure("gift") is None


# ---------------------------------------------------------------------------
# Migration registration
# ---------------------------------------------------------------------------
def test_every_migration_is_applied_by_bootstrap() -> None:
    """Every migration file must appear in bootstrap's apply list.

    A migration that exists on disk but is not enumerated in
    ``scripts/bootstrap-labs.sh`` never runs on a fresh box, so the table
    is missing in production while every local test passes. This guard
    fails the moment the two drift.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    migrations_dir = repo_root / "scripts" / "migrations"
    bootstrap = (repo_root / "scripts" / "bootstrap-labs.sh").read_text()

    on_disk = sorted(p.name for p in migrations_dir.glob("0*.sql"))
    assert on_disk, "no migrations found — check the path"

    # 001_schema.sql is applied separately, ahead of the loop.
    missing = [
        name
        for name in on_disk
        if name != "001_schema.sql" and name not in bootstrap
    ]
    assert not missing, (
        "migrations exist but bootstrap-labs.sh never applies them: "
        f"{missing}. A fresh box would boot without these tables."
    )
