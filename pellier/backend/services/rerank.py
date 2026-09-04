"""
Rerank Service — Cohere Rerank v3.5 via Bedrock.

Anna's hybrid pipeline (vector + Postgres FTS → RRF) produces a candidate
pool of ~30 products. The reranker reads the user's exact query
plus a short text rendering of each candidate and reorders by
relevance — usually with a markedly different ranking than what
either retrieval branch produced alone.

Why Cohere Rerank v3.5 specifically:

  - Trained on multilingual e-commerce-shaped data; product
    descriptions land in-distribution.
  - Returns a relevance score per document, so we can order by it
    and threshold ("don't show below 0.4") if we want. The score is
    a within-request ranking signal, not a calibrated probability.
  - Adds one extra Bedrock call per request; the Lab 2 compare
    endpoint reports the observed latency per strategy, so the
    workshop's "is the extra spend worth it?" question has a live
    answer instead of a hand-wave.
  - Already configured in config.py as
    ``BEDROCK_RERANK_MODEL = "cohere.rerank-v3-5:0"`` so wiring is a
    single import away.

This module deliberately keeps the rerank step decoupled from the
retrieval step: a Bedrock outage degrades Anna's path to plain
hybrid (still a meaningful upgrade over Marco's pure vector), it
doesn't take the chat down. The find_pieces_hybrid tool catches
the Bedrock exception and falls back to RRF order.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import boto3

from config import settings
from services.cache import get_cache

logger = logging.getLogger(__name__)


def _request_id(response: Any) -> Optional[str]:
    """Pull the AWS request id out of a boto3 response or ClientError body.

    Args:
        response: A boto3 response dict, a ``ClientError.response``, or
            anything else.

    Returns:
        The request id when present, else None. The id is what makes a
        degraded rerank traceable in CloudTrail, so it is reported
        alongside the failure rather than only logged.
    """
    if not isinstance(response, dict):
        return None
    metadata = response.get("ResponseMetadata")
    if not isinstance(metadata, dict):
        return None
    request_id = metadata.get("RequestId")
    return str(request_id) if request_id else None


@dataclass
class RerankOutcome:
    """What a rerank attempt actually did.

    ``rerank()`` returns only the ordered results, so a caller cannot tell
    an empty result set caused by a Bedrock failure from a legitimately
    empty candidate pool. Any surface that *labels* or *prices* its output
    as reranked must call :meth:`RerankService.rerank_with_status` and
    report ``executed`` — otherwise a degraded run is presented, and
    billed, as a reranked one.
    """

    results: List[Dict[str, Any]] = field(default_factory=list)
    executed: bool = False
    model_id: str = ""
    request_id: Optional[str] = None
    degraded_reason: Optional[str] = None


class RerankService:
    """Cohere Rerank v3.5 via Bedrock invoke_model.

    Bedrock exposes Cohere Rerank as a standard invoke_model target;
    the request body uses the Cohere Rerank API v2 schema. We send the
    candidate documents as plain strings — the agent_tools wrapper
    builds these from product fields (name/description/category) so
    the reranker has enough signal to make a meaningful judgment.

    Deliberate branch divergence: this branch (``main``) calls Rerank
    through ``bedrock-runtime`` ``invoke_model`` (IAM:
    ``bedrock:InvokeModel``); the ``governed`` branch uses the
    ``bedrock-agent-runtime`` Rerank API (IAM: ``bedrock:Rerank``).
    Both are valid Bedrock surfaces for ``cohere.rerank-v3-5:0``.
    """

    def __init__(self, region: Optional[str] = None):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region or settings.aws_region_resolved,
        )
        self.model_id = settings.BEDROCK_RERANK_MODEL

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rerank ``documents`` against ``query``; return top_n with scores.

        Args:
            query: User query string (what the agent is searching for).
            documents: Plain-text renderings of candidate products. Each
                document is a single string — name + description + tags
                concatenated by the caller. Length cap is implicit
                (Bedrock will return 4xx if any single document exceeds
                the model's per-doc limit, currently ~1024 tokens).
            top_n: Number of reranked results to return. Cohere returns
                top_n entries with their original-list indices and
                relevance_score in [0, 1].

        Returns:
            List of ``{"index": int, "relevance_score": float}`` dicts
            sorted by ``relevance_score`` descending. The ``index`` is
            into the *input* ``documents`` list so the caller can
            project candidate metadata back from their own pool.

            On any Bedrock error, returns an empty list — the caller
            is responsible for falling back to RRF order. We log at
            WARNING level so the failure is visible in Pellier Labs
            without crashing the request path. An empty list is
            therefore ambiguous; callers that label or price their
            output as reranked must use :meth:`rerank_with_status`.
        """
        return self.rerank_with_status(
            query=query, documents=documents, top_n=top_n,
        ).results

    def rerank_with_status(
        self,
        query: str,
        documents: List[str],
        top_n: int = 5,
    ) -> RerankOutcome:
        """Rerank ``documents`` and report whether the model actually ran.

        Same arguments as :meth:`rerank`. Use this whenever the caller
        labels, prices, or otherwise makes a claim about its output: the
        returned :class:`RerankOutcome` distinguishes "the reranker
        reordered these" from "Bedrock failed and this is the input order".

        Args:
            query: User query string.
            documents: Plain-text renderings of candidate products.
            top_n: Number of reranked results to return.

        Returns:
            A :class:`RerankOutcome`. ``executed`` is True only when
            Bedrock returned a result set for this pool; an empty
            candidate pool is reported as ``executed=False`` with an
            explicit reason rather than as a silent success.
        """
        outcome = RerankOutcome(model_id=self.model_id)
        if not documents:
            outcome.degraded_reason = "no candidate documents to rerank"
            return outcome
        if top_n <= 0:
            outcome.degraded_reason = "top_n must be positive"
            return outcome

        max_docs = max(1, int(settings.RERANK_MAX_DOCUMENTS))
        documents = documents[:max_docs]
        top_n = min(top_n, len(documents))

        cache = get_cache()
        cache_key = None
        if cache:
            cache_key = json.dumps(
                {
                    "query": query,
                    "documents": documents,
                    "top_n": top_n,
                    "model_id": self.model_id,
                },
                separators=(",", ":"),
                ensure_ascii=False,
            )
            cached = cache.get("rerank", cache_key)
            if cached is not None:
                outcome.results = cached
                outcome.executed = True
                outcome.request_id = "cache"
                return outcome

        # Cohere's v2 API expects a JSON body with these fields. The
        # api_version is part of the body (not a Bedrock-level header).
        body = {
            "query": query,
            "documents": documents,
            "top_n": top_n,
            "api_version": 2,
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
            results = payload.get("results", [])
            outcome.request_id = _request_id(response)
            if cache and cache_key:
                cache.set("rerank", cache_key, results, ttl=settings.RERANK_CACHE_TTL_SEC)
            outcome.results = results
            outcome.executed = bool(results)
            if not results:
                outcome.degraded_reason = (
                    "Bedrock returned no rerank results for this pool"
                )
            return outcome
        except Exception as exc:
            # Don't crash the pipeline — report the degradation so the
            # caller falls back to RRF order *and* says so. A caller that
            # silently substitutes RRF rows under a "reranked" label is
            # publishing evidence the run does not support.
            outcome.degraded_reason = f"{exc.__class__.__name__}: {exc}"
            outcome.request_id = _request_id(getattr(exc, "response", None))
            logger.warning(
                "Cohere Rerank failed: %s — caller should fall back to RRF "
                "order and label the result as degraded",
                exc,
            )
            return outcome

# -----------------------------------------------------------------
# Singleton accessor — mirrors the get_db_service pattern used
# elsewhere in services/.
# -----------------------------------------------------------------
_rerank_service: Optional[RerankService] = None


def get_rerank_service() -> RerankService:
    """Lazy singleton. The boto3 client is cheap to construct but the
    cached instance saves a few ms per turn and keeps Bedrock client
    config (region, retry policy) consistent."""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service
