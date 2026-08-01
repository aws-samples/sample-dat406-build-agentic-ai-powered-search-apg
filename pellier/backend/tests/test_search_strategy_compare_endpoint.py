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
    def extract(self, query: str) -> dict[str, Any]:
        return {
            "categories": ["Home"],
            "tags": ["gift"],
            "price_max_usd": 100,
            "in_stock_only": True,
            "soft_signal": "considered housewarming gift",
        }


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


def test_comparison_rejects_blank_query() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(app_module.compare_search_strategies(query="  "))
    assert exc_info.value.status_code == 400


def teardown_function() -> None:
    app_module.db_service = None
