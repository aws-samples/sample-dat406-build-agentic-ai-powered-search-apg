"""Shared planned hybrid retrieval primitives for the Observatory.

The hybrid+rerank and agentic comparison variants need the same contract:
compile a typed ``SearchPlan`` into hard predicates, apply those predicates in
*both* hybrid branches before RRF, then rerank only the valid candidate pool.
Keeping those mechanics here prevents the teaching surface from drifting into
two hidden implementations of its own comparison path.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from config import settings


def catalog_document(row: Dict[str, Any]) -> str:
    """Return the bounded catalog representation supplied to the reranker."""
    name = " ".join(str(row.get("name") or "").split())
    description = " ".join(str(row.get("description") or "").split())
    category = " ".join(str(row.get("category") or "").split())
    if len(description) > 240:
        description = description[:237] + "…"
    return f"{name} — {description} ({category})"


async def retrieve_planned_hybrid(
    db: Any,
    *,
    query: str,
    query_embedding: Sequence[float],
    plan: Any,
    k_vector: int | None = None,
    k_fts: int | None = None,
    top_n: int | None = None,
) -> List[Dict[str, Any]]:
    """Retrieve one valid hybrid candidate pool for an already-built plan.

    ``SearchPlan`` owns the legal constraints and their bound parameters;
    ``HybridSearch`` owns the branch execution and RRF merge. This boundary is
    deliberately narrow so callers can choose a different *declared* rerank
    query (for example a planner's soft signal) without changing hard-filter
    enforcement or candidate generation.
    """
    from services.hybrid_search import HybridSearch

    hard_clauses, hard_params = plan.compile_predicates()
    return await HybridSearch(db).search(
        query=query,
        query_embedding=list(query_embedding),
        k_vector=k_vector or settings.HYBRID_VECTOR_K,
        k_fts=k_fts or settings.HYBRID_FTS_K,
        top_n=top_n or settings.HYBRID_TOP_N,
        hard_clauses=hard_clauses,
        hard_params=hard_params,
    )


def rerank_hybrid_candidates(
    candidates: Sequence[Dict[str, Any]],
    *,
    query: str,
    top_n: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Rerank a known candidate pool, degrading honestly to RRF order.

    An invalid reranker index is ignored rather than projecting an unknown row
    into the result. If every returned index is invalid, the function returns
    RRF order with ``rerank_score=None`` — no fabricated rerank evidence.
    """
    from services.rerank import get_rerank_service

    pool = [dict(candidate) for candidate in candidates]
    documents = [catalog_document(candidate) for candidate in pool]
    rerank_results = get_rerank_service().rerank(
        query=query,
        documents=documents,
        top_n=min(max(1, int(top_n)), settings.RERANK_MAX_DOCUMENTS),
    )
    if not rerank_results:
        return [{**candidate, "rerank_score": None} for candidate in pool], []

    ordered: List[Dict[str, Any]] = []
    applied: List[Dict[str, Any]] = []
    for result in rerank_results:
        try:
            index = int(result["index"])
        except (KeyError, TypeError, ValueError):
            continue
        if index < 0 or index >= len(pool):
            continue
        try:
            score = float(result.get("relevance_score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        ordered.append({**pool[index], "rerank_score": score})
        applied.append(dict(result))

    if not ordered:
        return [{**candidate, "rerank_score": None} for candidate in pool], []
    return ordered, applied
