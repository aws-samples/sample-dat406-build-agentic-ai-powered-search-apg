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
from services.rerank import RerankOutcome
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
    """Fake reranker mirroring ``RerankService``'s real contract.

    ``fail`` makes every call behave like a Bedrock outage so the tests can
    assert the endpoint reports degradation instead of silently publishing
    fusion order under a reranked label.
    """

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.model_id = "cohere.rerank-v3-5:0"

    def rerank(
        self, *, query: str, documents: list[str], top_n: int
    ) -> list[dict[str, int]]:
        return self.rerank_with_status(
            query=query, documents=documents, top_n=top_n,
        ).results

    def rerank_with_status(
        self, *, query: str, documents: list[str], top_n: int
    ) -> RerankOutcome:
        if self.fail:
            return RerankOutcome(
                results=[],
                executed=False,
                model_id=self.model_id,
                request_id="req-degraded",
                degraded_reason="ThrottlingException: rate exceeded",
            )
        return RerankOutcome(
            results=[
                {"index": index}
                for index in reversed(range(min(top_n, len(documents))))
            ],
            executed=True,
            model_id=self.model_id,
            request_id="req-ok",
        )


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
            query="A housewarming gift under $100 that is in stock"
        )
    )

    assert body["query"] == "A housewarming gift under $100 that is in stock"
    assert body["sharedQueryEmbeddingObservedMs"] >= 0
    assert "not a percentile" in body["measurementAssumptions"]["latency"]
    assert "not a billing measurement" in body["measurementAssumptions"]["cost"]
    assert "not calculated" in body["measurementAssumptions"]["quality"]
    assert body["costModel"]["pricingReviewedOn"] == "2026-08-16"
    assert body["costModel"]["pricingSource"].endswith("/bedrock/pricing/")
    assert (
        body["costModel"]["components"]["rerank"]["modelId"]
        == app_module.settings.BEDROCK_RERANK_MODEL
    )
    assert (
        body["costModel"]["components"]["filterExtraction"][
            "inputTokensPerRequest"
        ]
        == 600
    )

    assert len(body["strategies"]) == 4
    for strategy in body["strategies"]:
        assert strategy["observedMs"] >= 0
        assert strategy["modeledCostPerThousandUsd"] >= 0
        assert strategy["costComponents"]
        assert "p50Ms" not in strategy
        assert "costPerThousandUsd" not in strategy
        assert strategy["products"]

    agentic = body["strategies"][-1]
    assert agentic["extractedFilters"]["priceMaxUsd"] == 100
    assert agentic["extractedFilters"]["filterUsed"] == "strict"
    assert "filterExtraction" in agentic["costComponents"]
    assert "additionalSoftSignalEmbedding" in agentic["costComponents"]

    for strategy in body["strategies"][2:]:
        assert strategy["rerankExecuted"] is True
        assert strategy["productOrderSource"] == "rerank"
        assert strategy["degradedReason"] is None
        assert "rerank" in strategy["costComponents"]


def test_degraded_rerank_is_labelled_and_not_charged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed rerank must never be published — or priced — as a rerank.

    Before this guard the endpoint substituted fusion rows, kept the
    "hybrid + rerank" label, and still charged the rerank component, so a
    Bedrock outage looked like a successful reranked comparison.
    """
    monkeypatch.setattr(
        rerank_module, "get_rerank_service", lambda: _Reranker(fail=True)
    )

    body = asyncio.run(
        app_module.compare_search_strategies(
            query="A housewarming gift under $100 that is in stock"
        )
    )

    hybrid_rerank, agentic = body["strategies"][2], body["strategies"][3]

    for strategy in (hybrid_rerank, agentic):
        assert strategy["rerankExecuted"] is False
        assert "rerank" not in strategy["costComponents"]
        assert "degraded" in strategy["productOrderSource"]
        assert "ThrottlingException" in strategy["degradedReason"]
        assert strategy["rerankRequestId"] == "req-degraded"

    # The rerank surcharge must be absent from both modeled costs.
    components = body["costModel"]["components"]
    surcharge = components["rerank"]["modeledCostPerThousandUsd"]
    embedding = components["queryEmbedding"]["modeledCostPerThousandUsd"]
    extraction = components["filterExtraction"]["modeledCostPerThousandUsd"]

    assert surcharge > 0
    assert hybrid_rerank["modeledCostPerThousandUsd"] == embedding
    # queryEmbedding + softSignal re-embed + filterExtraction, no rerank.
    assert agentic["modeledCostPerThousandUsd"] == round(
        embedding * 2 + extraction, 4
    )


def test_hard_predicates_are_never_relaxed_to_widen_the_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Price and availability must survive every relaxation rung.

    The old ladder ended in a ``drop_all`` rung that discarded
    ``price_max_usd`` and ``in_stock_only``, so "under $100, in stock"
    could return over-budget, out-of-stock rows while extractedFilters
    still advertised the constraints.
    """

    class _EmptyVectorSearch(_VectorSearch):
        async def vector_search_filtered(
            self, *args: Any, **kwargs: Any
        ) -> list[dict[str, Any]]:
            # Never enough rows, so every relaxation rung is attempted.
            _EmptyVectorSearch.seen.append(kwargs)
            return []

    _EmptyVectorSearch.seen = []
    monkeypatch.setattr(vector_module, "VectorSearch", _EmptyVectorSearch)

    body = asyncio.run(
        app_module.compare_search_strategies(
            query="A housewarming gift under $100 that is in stock"
        )
    )

    assert _EmptyVectorSearch.seen, "expected the filter ladder to run"
    for attempt in _EmptyVectorSearch.seen:
        assert attempt["price_max_usd"] == 100
        assert attempt["in_stock_only"] is True

    filters = body["strategies"][-1]["extractedFilters"]
    assert filters["hardConstraintsEnforced"] is True
    assert filters["filterUsed"] == "drop_cats"
    assert filters["relaxedFilters"] == ["tags", "categories"]
    assert filters["poolBelowTarget"] is True
    assert filters["poolSize"] == 0
    assert "never relaxed" in body["measurementAssumptions"]["constraints"]


def test_comparison_rejects_blank_query() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(app_module.compare_search_strategies(query="  "))
    assert exc_info.value.status_code == 400


def teardown_function() -> None:
    app_module.db_service = None
