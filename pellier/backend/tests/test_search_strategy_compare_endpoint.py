"""Contract tests for the live four-strategy retrieval comparison."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import HTTPException

import app as app_module
import services.embeddings as embeddings_module
import services.hybrid_search as hybrid_module
import services.rerank as rerank_module
import services.structured_extract as extract_module
import services.vector_search as vector_module


class _Embedding:
    def embed_query(self, query: str) -> list[float]:
        return [0.1] * 1024


class _VectorSearch:
    def __init__(self, db: Any) -> None:
        self.db = db

    async def vector_search(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [
            {"name": "Vector first", "product_id": 1},
            {"name": "Vector second", "product_id": 2},
        ]

    async def vector_search_filtered(
        self, *args: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": f"Filtered {index}",
                "product_id": index,
                "description": "A filtered result",
                "category": "Home",
            }
            for index in range(1, 7)
        ]

    async def vector_search_planned(
        self, *args: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        # Record the compiled predicates so a test can assert the agentic
        # strategy really ran a plan rather than ad-hoc kwargs.
        self.last_predicates = list(kwargs.get("predicates") or [])
        self.last_predicate_params = list(kwargs.get("predicate_params") or [])
        return [
            {
                "name": f"Planned {index}",
                "product_id": index,
                "description": "A planned result",
                "category": "Home",
            }
            for index in range(1, 7)
        ]


class _HybridSearch:
    def __init__(self, db: Any) -> None:
        self.db = db

    async def search(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [
            {
                "name": f"Hybrid {index}",
                "product_id": index,
                "description": "A hybrid result",
                "category": "Home",
            }
            for index in range(1, 7)
        ]


class _Reranker:
    def rerank(
        self, *, query: str, documents: list[str], top_n: int
    ) -> list[dict[str, int]]:
        return [{"index": index} for index in reversed(range(min(top_n, len(documents))))]


class _Extractor:
    """Stands in for Sonnet. Facets must be real catalog values — the
    planner drops anything outside ``KNOWN_CATEGORIES`` / ``KNOWN_TAGS``,
    so a fixture using invented facets would silently test nothing."""

    def extract(self, query: str) -> dict[str, Any]:
        return {
            "categories": ["Home Decor"],
            "tags": ["gift"],
            "price_max_usd": 100,
            "in_stock_only": True,
            "exclusions": ["candle"],
            "soft_signal": "considered housewarming gift",
        }


class _EmptyPoolVectorSearch(_VectorSearch):
    """Every planned attempt comes back empty, forcing the full ladder."""

    def __init__(self, db: Any) -> None:
        super().__init__(db)
        self.attempts: list[list[str]] = []

    async def vector_search_planned(
        self, *args: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        self.attempts.append(list(kwargs.get("predicates") or []))
        return []


@pytest.fixture(autouse=True)
def _stub_services(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "db_service", object())
    monkeypatch.setattr(embeddings_module, "EmbeddingService", _Embedding)
    monkeypatch.setattr(vector_module, "VectorSearch", _VectorSearch)
    monkeypatch.setattr(hybrid_module, "HybridSearch", _HybridSearch)
    monkeypatch.setattr(rerank_module, "get_rerank_service", lambda: _Reranker())
    monkeypatch.setattr(
        extract_module, "get_structured_extractor", lambda: _Extractor()
    )


def test_comparison_labels_single_run_latency_and_modeled_cost_honestly() -> None:
    body = asyncio.run(
        app_module.compare_search_strategies(
            query="A milestone gift for a new homeowner"
        )
    )

    assert body["query"] == "A milestone gift for a new homeowner"
    assert body["sharedQueryEmbeddingObservedMs"] >= 0
    assert "not a percentile" in body["measurementAssumptions"]["latency"]
    assert "not a billing measurement" in body["measurementAssumptions"]["cost"]
    assert "not calculated" in body["measurementAssumptions"]["quality"]

    assert len(body["strategies"]) == 4
    for strategy in body["strategies"]:
        assert strategy["observedMs"] >= 0
        assert strategy["modeledCostPerThousandUsd"] >= 0
        assert "p50Ms" not in strategy
        assert "costPerThousandUsd" not in strategy
        assert strategy["products"]

    agentic = body["strategies"][-1]
    assert agentic["extractedFilters"]["priceMaxUsd"] == 100
    assert agentic["extractedFilters"]["filterUsed"] == "strict"
    # The typed plan that ran is reported alongside the raw extraction.
    plan = agentic["searchPlan"]
    assert plan["hard_constraints"]["price_max_usd"] == 100.0
    assert plan["hard_constraints"]["in_stock_only"] is True
    assert plan["exclusions"] == ["candle"]
    assert agentic["relaxations"] == []


def test_exhausted_ladder_never_drops_a_hard_constraint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even when every attempt returns nothing, price/stock/exclusions hold.

    Regression guard for the audit's A2 finding: the previous ladder's
    final ``drop_all`` rung removed price and in-stock entirely, so this
    query could answer with an out-of-stock $250 candle.
    """
    empty = _EmptyPoolVectorSearch(object())
    monkeypatch.setattr(vector_module, "VectorSearch", lambda db: empty)

    body = asyncio.run(
        app_module.compare_search_strategies(
            query="in-stock housewarming gift under $100, no candles"
        )
    )

    assert empty.attempts, "the agentic strategy should have attempted retrieval"
    for predicates in empty.attempts:
        assert "price <= %s" in predicates
        assert "quantity > 0" in predicates
        assert "NOT (tags ?| %s)" in predicates

    agentic = body["strategies"][-1]
    assert agentic["searchPlan"]["hard_constraints"]["price_max_usd"] == 100.0
    assert agentic["searchPlan"]["hard_constraints"]["in_stock_only"] is True
    assert agentic["hardConstraintsEnforced"] == [
        "price <= $100",
        "in stock",
        "category in Home Decor",
    ]
    # Widening happened, and it is disclosed rather than silent.
    assert [r["step"] for r in agentic["relaxations"]] == ["drop_tags"]
    assert agentic["relaxations"][0]["dropped"] == ["gift"]


def test_comparison_rejects_blank_query() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(app_module.compare_search_strategies(query="  "))
    assert exc_info.value.status_code == 400


def teardown_function() -> None:
    app_module.db_service = None
