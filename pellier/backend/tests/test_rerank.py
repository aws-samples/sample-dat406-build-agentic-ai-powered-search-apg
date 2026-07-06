"""Tests for ``RerankService.rerank`` — Cohere Rerank v3.5 via Bedrock.

We mock boto3 so the tests run offline; the real Bedrock invocation is
exercised in the live verification phase.

Runnable from the repo root:
    pellier/backend/.venv/bin/python -m pytest \
        pellier/backend/tests/test_rerank.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.rerank import RerankService, get_rerank_service
import services.rerank as rerank_module


@pytest.fixture
def mock_bedrock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Stub boto3.client('bedrock-agent-runtime') so .rerank is observable."""
    client = MagicMock()
    # Default: well-formed Bedrock Agent Runtime response.
    client.rerank.return_value = {
        "results": [
            {"index": 0, "relevanceScore": 0.95},
            {"index": 2, "relevanceScore": 0.71},
            {"index": 1, "relevanceScore": 0.34},
        ],
    }
    monkeypatch.setattr(rerank_module.boto3, "client", lambda *_, **__: client)
    return client


@pytest.fixture(autouse=True)
def reset_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force a fresh RerankService for each test."""
    monkeypatch.setattr(rerank_module, "_rerank_service", None)


class TestRerankRequestShape:
    """The Bedrock Agent Runtime request must match the rerank schema."""

    def test_request_body_includes_required_fields(
        self, mock_bedrock: MagicMock,
    ) -> None:
        svc = RerankService()
        docs = ["doc one", "doc two", "doc three"]
        svc.rerank(query="my query", documents=docs, top_n=2)

        assert mock_bedrock.rerank.call_count == 1
        kwargs = mock_bedrock.rerank.call_args.kwargs
        assert kwargs["queries"] == [{"type": "TEXT", "textQuery": {"text": "my query"}}]
        assert [s["inlineDocumentSource"]["textDocument"]["text"] for s in kwargs["sources"]] == docs
        assert kwargs["rerankingConfiguration"]["type"] == "BEDROCK_RERANKING_MODEL"
        config = kwargs["rerankingConfiguration"]["bedrockRerankingConfiguration"]
        assert config["numberOfResults"] == 2
        assert config["modelConfiguration"]["modelArn"].endswith("/cohere.rerank-v3-5:0")

    def test_top_n_clamped_to_document_count(
        self, mock_bedrock: MagicMock,
    ) -> None:
        svc = RerankService()
        docs = ["only doc"]
        svc.rerank(query="q", documents=docs, top_n=10)
        config = mock_bedrock.rerank.call_args.kwargs["rerankingConfiguration"]["bedrockRerankingConfiguration"]
        assert config["numberOfResults"] == 1

    def test_uses_configured_model_id(
        self, mock_bedrock: MagicMock,
    ) -> None:
        svc = RerankService()
        svc.rerank(query="q", documents=["doc"], top_n=1)
        config = mock_bedrock.rerank.call_args.kwargs["rerankingConfiguration"]["bedrockRerankingConfiguration"]
        assert config["modelConfiguration"]["modelArn"] == svc.model_arn
        # Verify it actually points to the rerank model, not something else.
        assert "rerank" in svc.model_id.lower()


class TestRerankResults:

    def test_returns_results_list_verbatim(
        self, mock_bedrock: MagicMock,
    ) -> None:
        svc = RerankService()
        results = svc.rerank("q", ["a", "b", "c"], top_n=3)
        # Mock returned 3 results — passed through unchanged.
        assert len(results) == 3
        assert results[0] == {"index": 0, "relevance_score": 0.95}
        assert results[2]["relevance_score"] == 0.34

    def test_empty_documents_returns_empty_without_calling_bedrock(
        self, mock_bedrock: MagicMock,
    ) -> None:
        svc = RerankService()
        results = svc.rerank(query="q", documents=[], top_n=5)
        assert results == []
        assert mock_bedrock.rerank.call_count == 0

    def test_zero_top_n_returns_empty_without_calling_bedrock(
        self, mock_bedrock: MagicMock,
    ) -> None:
        svc = RerankService()
        results = svc.rerank(query="q", documents=["doc"], top_n=0)
        assert results == []
        assert mock_bedrock.rerank.call_count == 0


class TestRerankFailureMode:

    def test_bedrock_exception_returns_empty_list(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client = MagicMock()
        client.rerank.side_effect = RuntimeError("Bedrock down")
        monkeypatch.setattr(rerank_module.boto3, "client", lambda *_, **__: client)
        svc = RerankService()
        # No exception — caller is responsible for falling back to RRF order.
        result = svc.rerank("q", ["a", "b"], top_n=2)
        assert result == []


class TestSingleton:

    def test_get_rerank_service_returns_same_instance(
        self, mock_bedrock: MagicMock,
    ) -> None:
        a = get_rerank_service()
        b = get_rerank_service()
        assert a is b
