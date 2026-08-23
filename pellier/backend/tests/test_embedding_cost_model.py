"""Embedding spend estimate must be token-based, not per-call.

Bedrock bills embeddings per input token and reports the billed count on
every ``invoke_model`` response (``x-amzn-bedrock-input-token-count``). The
dashboard previously accumulated a flat constant per call, which is the wrong
pricing dimension: a one-word query and an 8,000-character document produced
the same number. It fed a participant-facing cost comparison, so the number
looked authoritative while modelling something Bedrock does not charge for.

These tests pin the dimension (tokens) and the provenance (a reviewed rate
with a review date), not a particular price.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

import services.embeddings as embeddings_module
from services.embeddings import EmbeddingService, get_cache_stats


@pytest.fixture(autouse=True)
def reset_totals(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts from zero accumulated spend."""
    monkeypatch.setattr(embeddings_module, "_TOTAL_EMBEDDING_COST", 0.0)
    monkeypatch.setattr(embeddings_module, "_TOTAL_EMBEDDING_INPUT_TOKENS", 0)


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> EmbeddingService:
    """An EmbeddingService with no boto3 client and no cache."""
    monkeypatch.setattr(
        embeddings_module.boto3, "client", lambda *a, **k: object()
    )
    monkeypatch.setattr(embeddings_module, "get_cache_stats", get_cache_stats)
    import services.cache as cache_module

    monkeypatch.setattr(cache_module, "get_cache", lambda: None)
    return EmbeddingService()


def _stub_bedrock(
    monkeypatch: pytest.MonkeyPatch, tokens: int
) -> List[Dict[str, Any]]:
    """Replace the Bedrock call with a canned response of ``tokens`` tokens."""
    calls: List[Dict[str, Any]] = []

    def fake_call(self: EmbeddingService, request_body: dict) -> Tuple[dict, int]:
        calls.append(request_body)
        return ({"embeddings": {"float": [[0.01] * 1024]}}, tokens)

    monkeypatch.setattr(EmbeddingService, "_call_bedrock_embedding", fake_call)
    return calls


def test_cost_scales_with_billed_input_tokens(
    service: EmbeddingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ten times the tokens must cost ten times as much."""
    _stub_bedrock(monkeypatch, tokens=8)
    service.generate_embedding("short query")
    cheap = get_cache_stats()["total_embedding_cost_usd"]

    monkeypatch.setattr(embeddings_module, "_TOTAL_EMBEDDING_COST", 0.0)
    monkeypatch.setattr(embeddings_module, "_TOTAL_EMBEDDING_INPUT_TOKENS", 0)
    _stub_bedrock(monkeypatch, tokens=80)
    service.generate_embedding("a much longer query about linen and ceramics")
    dear = get_cache_stats()["total_embedding_cost_usd"]

    assert dear == pytest.approx(cheap * 10, rel=1e-6)


def test_billed_tokens_are_reported_alongside_cost(
    service: EmbeddingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The token count is auditable, so the estimate can be re-derived."""
    _stub_bedrock(monkeypatch, tokens=12)
    service.generate_embedding("linen shirt")
    stats = get_cache_stats()
    assert stats["total_embedding_input_tokens"] == 12


def test_cost_follows_the_reviewed_rate(
    service: EmbeddingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Estimate = billed tokens x reviewed USD-per-million / 1e6."""
    _stub_bedrock(monkeypatch, tokens=1_000)
    service.generate_embedding("linen shirt")
    expected = (
        1_000 * embeddings_module._EMBEDDING_USD_PER_MILLION_INPUT_TOKENS / 1_000_000
    )
    assert get_cache_stats()["total_embedding_cost_usd"] == pytest.approx(
        expected, rel=1e-9
    )


def test_zero_reported_tokens_adds_no_cost(
    service: EmbeddingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing header must not silently invent spend."""
    _stub_bedrock(monkeypatch, tokens=0)
    service.generate_embedding("linen shirt")
    assert get_cache_stats()["total_embedding_cost_usd"] == 0.0


def test_pricing_provenance_is_exposed() -> None:
    """A rate without a review date is not auditable."""
    stats = get_cache_stats()
    assert stats["embedding_pricing_reviewed_on"] == (
        embeddings_module._EMBEDDING_PRICING_REVIEWED_ON
    )
    assert embeddings_module._EMBEDDING_PRICING_REVIEWED_ON


def test_no_flat_per_call_cost_constant_remains() -> None:
    """The per-call constant was the bug; it must not come back."""
    assert not hasattr(embeddings_module, "_EMBEDDING_COST_PER_CALL")
