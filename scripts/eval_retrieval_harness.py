#!/usr/bin/env python3
"""Golden-query retrieval harness for the governed Pellier workshop.

Runs the same Aurora catalog through four retrieval strategies:

* vector
* hybrid
* hybrid+rerank
* agentic, planned by the *real* ``services.search_plan`` planner

The agentic row deliberately does **not** use the pinned filters in each
golden query's definition. Pinned filters make that row an oracle-filter
experiment: it measures how good retrieval could be if a perfect planner
existed, which is exactly the number that hides planner bugs. Instead the
harness runs the shipped extractor plus the shipped planner, then scores
the plan itself against the pinned filters as ground truth. A planning
mistake now shows up as a planner-precision miss rather than disappearing
into a healthy-looking recall figure.

Three evaluation layers, per the governed-workshop audit:

1. **Planner correctness** — did the plan recover the expected hard
   constraints, and did it invent any that were not asked for?
2. **Retriever/ranker quality** — Recall@5, Hit@1, MRR@5, candidate
   coverage, short-result rate, and hard-constraint compliance.
3. **Exit status** — the harness fails with a non-zero exit code when a
   threshold regresses, so CI can gate on relevance instead of merely
   printing it.

The harness is intentionally standalone. It does not need the FastAPI server
running, but it uses the same Bedrock models and PostgreSQL tables as the app.

Run ``--json`` for machine-readable output, ``--no-gate`` to report without
enforcing thresholds (useful when exploring), and ``--strict-planner`` to
also gate on planner precision.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
import psycopg
from psycopg.rows import dict_row


EMBED_MODEL_DEFAULT = "us.cohere.embed-v4:0"
RERANK_MODEL_DEFAULT = "cohere.rerank-v3-5:0"


# CI thresholds. A regression below any of these fails the run with a
# non-zero exit status. They are floors observed on the seeded catalog,
# set just below current measured performance so ordinary noise does not
# flap the gate but a real relevance regression trips it.
#
# The three ``*_max`` violation budgets are zero on purpose: a hard
# constraint that is violated even once is a correctness bug, not a
# quality metric to average away.
THRESHOLDS: dict[str, float] = {
    "rerank_recall_at_5_min": 0.70,
    "rerank_mrr_at_5_min": 0.55,
    "agentic_recall_at_5_min": 0.60,
    "hybrid_candidate_coverage_min": 0.75,
    "hard_constraint_violation_rate_max": 0.0,
    "exclusion_violation_rate_max": 0.0,
    "planner_hallucinated_constraint_rate_max": 0.0,
}

# Planner precision is gated only under --strict-planner: the extractor is
# a live model call, so this number moves with model behaviour rather than
# with the code under test.
PLANNER_RECALL_MIN = 0.60


@dataclass(frozen=True)
class Filters:
    categories: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    price_max: float | None = None


@dataclass(frozen=True)
class GoldenQuery:
    label: str
    query: str
    expected: tuple[str, ...]
    filters: Filters = field(default_factory=Filters)


GOLDEN_QUERIES: tuple[GoldenQuery, ...] = (
    GoldenQuery(
        "goa_linen",
        "linen shirts and layers for ten days in Goa",
        ("11", "14", "16", "18"),
        Filters(categories=("Apparel",), tags=("linen", "travel", "resort")),
    ),
    GoldenQuery(
        "drawstring_trousers",
        "drawstring linen trousers for resort packing",
        ("14",),
        Filters(categories=("Apparel",), tags=("linen", "resort")),
    ),
    GoldenQuery(
        "panama_hat",
        "packable panama hat for coastal sun",
        ("19",),
        Filters(categories=("Accessories",), tags=("travel", "resort")),
    ),
    GoldenQuery(
        "dopp_kit",
        "canvas dopp kit for carry-on toiletries",
        ("12",),
        Filters(categories=("Accessories",), tags=("canvas", "travel")),
    ),
    GoldenQuery(
        "weekend_bag",
        "leather weekend bag for a 48 hour trip",
        ("3", "17"),
        Filters(categories=("Accessories",), tags=("leather", "travel")),
    ),
    GoldenQuery(
        "beeswax_under_50",
        "beeswax candle under fifty dollars",
        ("21", "38"),
        Filters(categories=("Home Decor",), tags=("candle", "artisanal"), price_max=50),
    ),
    GoldenQuery(
        "ring_dish",
        "small ceramic ring dish gift",
        ("23",),
        Filters(categories=("Home Decor",), tags=("ceramic", "gift"), price_max=50),
    ),
    GoldenQuery(
        "soap_gift",
        "handmade soap gift set",
        ("26",),
        Filters(categories=("Beauty",), tags=("beauty", "gift", "artisanal")),
    ),
    GoldenQuery(
        "pour_over",
        "stoneware pour over coffee ritual",
        ("31",),
        Filters(categories=("Home Decor",), tags=("ceramic", "slow")),
    ),
    GoldenQuery(
        "ceramic_tumblers",
        "charcoal ceramic tumblers set",
        ("36",),
        Filters(categories=("Home Decor",), tags=("ceramic",)),
    ),
    GoldenQuery(
        "table_runner",
        "linen table runner for dinner",
        ("39",),
        Filters(categories=("Home Decor",), tags=("linen", "home")),
    ),
    GoldenQuery(
        "linen_throw",
        "raw linen throw for sofa",
        ("32",),
        Filters(categories=("Home Decor",), tags=("linen", "slow")),
    ),
    GoldenQuery(
        "card_wallet",
        "minimal leather card wallet",
        ("13",),
        Filters(categories=("Accessories",), tags=("leather", "minimal")),
    ),
    GoldenQuery(
        "terracotta_planter",
        "terracotta planter for a patio",
        ("34",),
        Filters(categories=("Home Decor",), tags=("ceramic", "earth")),
    ),
    GoldenQuery(
        "merino_socks",
        "merino travel socks temperature regulating",
        ("20",),
        Filters(categories=("Apparel",), tags=("merino", "travel")),
    ),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_env() -> None:
    for env_path in (_repo_root() / ".env", _repo_root() / "pellier" / "backend" / ".env"):
        if not env_path.is_file():
            continue
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("'\"")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _connect() -> psycopg.Connection[Any]:
    return psycopg.connect(
        host=_require("DB_HOST"),
        port=os.environ.get("DB_PORT", "5432"),
        user=_require("DB_USER"),
        password=_require("DB_PASSWORD"),
        dbname=_require("DB_NAME"),
        row_factory=dict_row,
    )


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _embed_queries(queries: list[str], *, region: str, model_id: str) -> list[list[float]]:
    body = {
        "texts": queries,
        "input_type": "search_query",
        "embedding_types": ["float"],
        "output_dimension": 1024,
    }
    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(response["body"].read())
    embeddings = payload.get("embeddings", {})
    vectors = embeddings.get("float", []) if isinstance(embeddings, dict) else embeddings
    if len(vectors) != len(queries):
        raise RuntimeError(f"Expected {len(queries)} embeddings, got {len(vectors)}")
    for vector in vectors:
        if len(vector) != 1024:
            raise RuntimeError(f"Expected 1024-dim embedding, got {len(vector)}")
    return [[float(v) for v in vector] for vector in vectors]


def _import_backend_planner() -> Any:
    """Import the shipped planner so the agentic row runs real code.

    The harness is standalone, so the backend package is not on the path
    by default. Importing it here (rather than reimplementing planning)
    is the whole point: an evaluation that scores its own private copy of
    the planner cannot detect a planner regression.
    """
    import sys

    backend = Path(__file__).resolve().parents[1] / "pellier" / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from services.search_plan import build_plan  # noqa: PLC0415

    return build_plan


def _plan_for(build_plan: Any, golden: "GoldenQuery", extractor: Any, top_k: int) -> Any:
    """Run the shipped extractor + planner for one golden query.

    Falls back to an empty extraction when the model call fails, which
    scores as a planner miss rather than silently substituting the pinned
    oracle filters.
    """
    try:
        extracted = extractor.extract(golden.query)
    except Exception as exc:  # pragma: no cover - live Bedrock failure path
        print(f"  ! extractor failed for {golden.label}: {exc}")
        extracted = {}
    return build_plan(golden.query, extracted, top_k=top_k)


def _score_plan(plan: Any, expected: Filters) -> dict[str, Any]:
    """Compare a produced plan against the golden query's pinned filters.

    Returns per-query planner metrics: how much of the expected
    constraint set the planner recovered, and whether it invented a
    constraint nobody asked for (the more dangerous error, since an
    invented hard constraint silently removes valid results).
    """
    expected_categories = {c.lower() for c in expected.categories}
    got_categories = {c.lower() for c in plan.hard.categories}
    expected_price = expected.price_max
    got_price = plan.hard.price_max_usd

    recovered = 0
    total = 0
    hallucinated = 0

    if expected_categories:
        total += 1
        if expected_categories & got_categories:
            recovered += 1
    if got_categories - expected_categories and expected_categories:
        hallucinated += 1
    elif got_categories and not expected_categories:
        hallucinated += 1

    if expected_price is not None:
        total += 1
        # A tighter ceiling than asked for is still a miss: it removes
        # valid candidates.
        if got_price is not None and abs(got_price - expected_price) < 0.01:
            recovered += 1
    elif got_price is not None:
        hallucinated += 1

    return {
        "expected_categories": sorted(expected_categories),
        "planned_categories": sorted(got_categories),
        "expected_price_max": expected_price,
        "planned_price_max": got_price,
        "planned_in_stock_only": plan.hard.in_stock_only,
        "planned_exclusions": list(plan.exclusions),
        "planned_soft_tags": list(plan.soft.tags),
        "constraints_recovered": recovered,
        "constraints_expected": total,
        "hallucinated_constraints": hallucinated,
        "relaxations": [r.step for r in plan.relaxations],
    }


def _score_compliance(rows: list[dict[str, Any]], plan: Any) -> dict[str, int]:
    """Count returned rows that violate the plan's own hard constraints.

    This is the metric the audit's A3 finding is really about: if filters
    are applied after reranking (or not at all), invalid rows reach the
    result list. Scoring compliance on the *returned* rows catches that
    regardless of where filtering was supposed to happen.
    """
    price_max = plan.hard.price_max_usd
    categories = {c.lower() for c in plan.hard.categories}
    exclusions = {t.lower() for t in plan.exclusions}

    hard_violations = 0
    exclusion_violations = 0
    for row in rows:
        price = row.get("price")
        if price_max is not None and price is not None and float(price) > price_max + 0.001:
            hard_violations += 1
        category = str(row.get("category") or "").lower()
        if categories and category and category not in categories:
            hard_violations += 1
        row_tags = {str(t).lower() for t in (row.get("tags") or [])}
        if exclusions and (row_tags & exclusions):
            exclusion_violations += 1
    return {
        "rows": len(rows),
        "hard_violations": hard_violations,
        "exclusion_violations": exclusion_violations,
    }


def _plan_filters(plan: Any) -> "Filters":
    """Project a ``SearchPlan``'s hard constraints onto harness Filters.

    Soft tag preferences are deliberately excluded: they are preferences,
    and the harness measures what the *hard* constraints did to recall.
    """
    return Filters(
        categories=tuple(plan.hard.categories),
        tags=(),
        price_max=plan.hard.price_max_usd,
    )


def _where_for_filters(filters: Filters, params: list[Any]) -> str:
    clauses = ['"imgUrl" IS NOT NULL', "embedding IS NOT NULL", "quantity > 0"]
    if filters.categories:
        clauses.append("category = ANY(%s)")
        params.append(list(filters.categories))
    if filters.tags:
        clauses.append("tags ?| %s")
        params.append(list(filters.tags))
    if filters.price_max is not None:
        clauses.append("price <= %s")
        params.append(float(filters.price_max))
    return " AND ".join(clauses)


def _vector_search(conn: psycopg.Connection[Any], vector: list[float], *, limit: int, filters: Filters | None = None) -> list[dict[str, Any]]:
    params: list[Any] = [_vector_literal(vector)]
    where = _where_for_filters(filters or Filters(), params)
    sql = f"""
        SELECT product_id, name, category, price, tags, description,
               1 - (embedding <=> %s::vector) AS score
        FROM pellier.product_catalog
        WHERE {where}
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    params.extend([_vector_literal(vector), int(limit)])
    with conn.cursor() as cur:
        cur.execute("SET LOCAL hnsw.iterative_scan = 'relaxed_order'")
        cur.execute(sql, params)
        return [_jsonable(dict(row)) for row in cur.fetchall()]


def _fts_search(conn: psycopg.Connection[Any], query: str, *, limit: int, filters: Filters | None = None) -> list[dict[str, Any]]:
    params: list[Any] = [query]
    where = _where_for_filters(filters or Filters(), params)
    sql = f"""
        WITH q AS (
            SELECT websearch_to_tsquery('english', %s) AS ts_q
        )
        SELECT product_id, name, category, price, tags, description,
               ts_rank_cd(description_tsv, q.ts_q) AS score
        FROM pellier.product_catalog
        CROSS JOIN q
        WHERE {where}
          AND description_tsv @@ q.ts_q
        ORDER BY score DESC
        LIMIT %s;
    """
    params.append(int(limit))
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [_jsonable(dict(row)) for row in cur.fetchall()]


def _rrf_merge(vector_rows: list[dict[str, Any]], fts_rows: list[dict[str, Any]], *, rrf_k: int, limit: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for rows, rank_key in ((vector_rows, "vector_rank"), (fts_rows, "fts_rank")):
        for idx, row in enumerate(rows, start=1):
            pid = str(row["product_id"])
            item = merged.setdefault(pid, {**row, "rrf_score": 0.0, "vector_rank": None, "fts_rank": None})
            item["rrf_score"] += 1.0 / (rrf_k + idx)
            item[rank_key] = idx
    return sorted(merged.values(), key=lambda row: (-row["rrf_score"], str(row["product_id"])))[:limit]


def _hybrid_search(
    conn: psycopg.Connection[Any],
    query: str,
    vector: list[float],
    *,
    rrf_k: int,
    pool_k: int,
    limit: int,
    filters: Filters | None = None,
) -> list[dict[str, Any]]:
    vector_rows = _vector_search(conn, vector, limit=pool_k, filters=filters)
    fts_rows = _fts_search(conn, query, limit=pool_k, filters=filters)
    return _rrf_merge(vector_rows, fts_rows, rrf_k=rrf_k, limit=limit)


def _document(row: dict[str, Any]) -> str:
    tags = ", ".join(row.get("tags") or [])
    return (
        f"Name: {row['name']}. Category: {row['category']}. "
        f"Price: ${float(row['price']):.0f}. Tags: {tags}. "
        f"Description: {row.get('description') or ''}"
    )


def _rerank(query: str, candidates: list[dict[str, Any]], *, region: str, model_id: str, limit: int) -> list[dict[str, Any]]:
    if not candidates:
        return []
    model_arn = model_id if model_id.startswith("arn:") else f"arn:aws:bedrock:{region}::foundation-model/{model_id}"
    sources = [
        {
            "type": "INLINE",
            "inlineDocumentSource": {
                "type": "TEXT",
                "textDocument": {"text": _document(row)},
            },
        }
        for row in candidates
    ]
    client = boto3.client("bedrock-agent-runtime", region_name=region)
    response = client.rerank(
        queries=[{"type": "TEXT", "textQuery": {"text": query}}],
        sources=sources,
        rerankingConfiguration={
            "type": "BEDROCK_RERANKING_MODEL",
            "bedrockRerankingConfiguration": {
                "modelConfiguration": {"modelArn": model_arn},
                "numberOfResults": min(limit, len(sources)),
            },
        },
    )
    out = []
    for item in response.get("results", []):
        row = dict(candidates[int(item["index"])])
        row["rerank_score"] = float(item.get("relevanceScore", 0.0))
        out.append(row)
    return out[:limit]


def _recall_at_5(product_ids: list[str], expected: tuple[str, ...]) -> tuple[int, int, float]:
    hits = len(set(product_ids[:5]) & set(expected))
    total = len(expected)
    return hits, total, hits / total if total else 0.0


def _recall(product_ids: list[str], expected: tuple[str, ...]) -> tuple[int, int, float]:
    hits = len(set(product_ids) & set(expected))
    total = len(expected)
    return hits, total, hits / total if total else 0.0


def _mrr_at_5(product_ids: list[str], expected: tuple[str, ...]) -> float:
    expected_set = set(expected)
    for idx, product_id in enumerate(product_ids[:5], start=1):
        if product_id in expected_set:
            return 1.0 / idx
    return 0.0


def _hit_at_1(product_ids: list[str], expected: tuple[str, ...]) -> int:
    return int(bool(product_ids) and product_ids[0] in set(expected))


def _print_summary(results: dict[str, list[tuple[int, int, float, int, int]]]) -> None:
    print("strategy | hits | expected | recall@5 | hit@1 | mrr@5 | short@5")
    print("---------|------|----------|----------|-------|-------|--------")
    for strategy, pairs in results.items():
        hits = sum(pair[0] for pair in pairs)
        expected = sum(pair[1] for pair in pairs)
        recall = hits / expected if expected else 0.0
        mrr = sum(pair[2] for pair in pairs) / len(pairs) if pairs else 0.0
        hit_at_1 = sum(pair[3] for pair in pairs) / len(pairs) if pairs else 0.0
        short_rate = sum(pair[4] for pair in pairs) / len(pairs) if pairs else 0.0
        print(
            f"{strategy:<8} | {hits:>4} | {expected:>8} | {recall:.3f}    | "
            f"{hit_at_1:.3f} | {mrr:.3f} | {short_rate:.3f}"
        )


def _metric_totals(results: dict[str, list[tuple[int, int, float, int, int]]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for strategy, pairs in results.items():
        hits = sum(pair[0] for pair in pairs)
        expected = sum(pair[1] for pair in pairs)
        out[strategy] = {
            "hits": hits,
            "expected": expected,
            "recall_at_5": round(hits / expected if expected else 0.0, 3),
            "hit_at_1": round(sum(pair[3] for pair in pairs) / len(pairs), 3) if pairs else 0.0,
            "mrr_at_5": round(sum(pair[2] for pair in pairs) / len(pairs), 3) if pairs else 0.0,
            "short_result_rate_at_5": round(sum(pair[4] for pair in pairs) / len(pairs), 3) if pairs else 0.0,
        }
    return out


def _timing_totals(timings: dict[str, list[float]]) -> dict[str, float]:
    return {
        strategy: round((sum(values) / len(values)) * 1000, 1) if values else 0.0
        for strategy, values in timings.items()
    }


def _planner_totals(scores: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate per-query planner scores into rates."""
    expected = sum(int(s["constraints_expected"]) for s in scores)
    recovered = sum(int(s["constraints_recovered"]) for s in scores)
    hallucinated = sum(int(s["hallucinated_constraints"]) for s in scores)
    queries = len(scores) or 1
    return {
        "constraints_expected": expected,
        "constraints_recovered": recovered,
        "constraint_recall": round(recovered / expected, 3) if expected else 1.0,
        "hallucinated_constraints": hallucinated,
        "hallucinated_constraint_rate": round(hallucinated / queries, 3),
    }


def _compliance_totals(scores: list[dict[str, int]]) -> dict[str, float]:
    """Aggregate hard-constraint compliance over all returned rows."""
    rows = sum(int(s["rows"]) for s in scores)
    hard = sum(int(s["hard_violations"]) for s in scores)
    exclusion = sum(int(s["exclusion_violations"]) for s in scores)
    denominator = rows or 1
    return {
        "rows_scored": rows,
        "hard_violations": hard,
        "hard_constraint_violation_rate": round(hard / denominator, 3),
        "exclusion_violations": exclusion,
        "exclusion_violation_rate": round(exclusion / denominator, 3),
    }


def _evaluate_gate(
    *,
    totals: dict[str, dict[str, float]],
    coverage: float,
    planner: dict[str, float],
    compliance: dict[str, float],
    strict_planner: bool,
) -> dict[str, Any]:
    """Check every threshold and return the pass/fail verdict.

    Returns a dict with ``passed`` and a ``failures`` list of
    human-readable strings, so both the JSON and the text output can
    report exactly which threshold moved.
    """
    checks: list[tuple[str, float, float, bool]] = [
        (
            "rerank recall@5",
            totals["rerank"]["recall_at_5"],
            THRESHOLDS["rerank_recall_at_5_min"],
            True,
        ),
        (
            "rerank mrr@5",
            totals["rerank"]["mrr_at_5"],
            THRESHOLDS["rerank_mrr_at_5_min"],
            True,
        ),
        (
            "agentic recall@5",
            totals["agentic"]["recall_at_5"],
            THRESHOLDS["agentic_recall_at_5_min"],
            True,
        ),
        (
            "hybrid candidate coverage",
            coverage,
            THRESHOLDS["hybrid_candidate_coverage_min"],
            True,
        ),
        (
            "hard-constraint violation rate",
            compliance["hard_constraint_violation_rate"],
            THRESHOLDS["hard_constraint_violation_rate_max"],
            False,
        ),
        (
            "exclusion violation rate",
            compliance["exclusion_violation_rate"],
            THRESHOLDS["exclusion_violation_rate_max"],
            False,
        ),
        (
            "planner hallucinated-constraint rate",
            planner["hallucinated_constraint_rate"],
            THRESHOLDS["planner_hallucinated_constraint_rate_max"],
            False,
        ),
    ]
    if strict_planner:
        checks.append(
            ("planner constraint recall", planner["constraint_recall"], PLANNER_RECALL_MIN, True)
        )

    failures: list[str] = []
    for label, observed, threshold, is_floor in checks:
        if is_floor and observed < threshold:
            failures.append(f"{label} {observed:.3f} below floor {threshold:.3f}")
        elif not is_floor and observed > threshold:
            failures.append(f"{label} {observed:.3f} above ceiling {threshold:.3f}")

    return {
        "passed": not failures,
        "failures": failures,
        "thresholds": dict(THRESHOLDS),
        "strictPlanner": strict_planner,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Pellier golden-query retrieval evaluation.")
    parser.add_argument("--rrf-k", type=int, default=60, help="RRF damping constant for hybrid strategies.")
    parser.add_argument("--pool-k", type=int, default=20, help="Candidate count per vector/FTS branch before RRF.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--no-gate",
        action="store_true",
        help="Report metrics without failing the run on a threshold regression.",
    )
    parser.add_argument(
        "--strict-planner",
        action="store_true",
        help="Also gate on planner constraint recall (moves with model behaviour).",
    )
    args = parser.parse_args()

    build_plan = _import_backend_planner()
    from services.structured_extract import get_structured_extractor  # noqa: PLC0415

    extractor = get_structured_extractor()
    planner_scores: list[dict[str, Any]] = []
    compliance_scores: list[dict[str, int]] = []

    _load_env()
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    embed_model = os.environ.get("BEDROCK_EMBEDDING_MODEL") or os.environ.get("BEDROCK_EMBED_MODEL_ID") or EMBED_MODEL_DEFAULT
    rerank_model = os.environ.get("BEDROCK_RERANK_MODEL") or RERANK_MODEL_DEFAULT

    started = time.perf_counter()
    embed_started = time.perf_counter()
    vectors = _embed_queries([q.query for q in GOLDEN_QUERIES], region=region, model_id=embed_model)
    embed_elapsed_s = time.perf_counter() - embed_started
    detailed: list[dict[str, Any]] = []
    summary: dict[str, list[tuple[int, int, float, int, int]]] = {
        "vector": [],
        "hybrid": [],
        "rerank": [],
        "agentic": [],
    }
    strategy_timings: dict[str, list[float]] = {
        "vector": [],
        "hybrid": [],
        "rerank": [],
        "agentic": [],
    }
    pool_coverage: list[tuple[int, int]] = []

    with _connect() as conn:
        for golden, vector in zip(GOLDEN_QUERIES, vectors):
            strategy_started = time.perf_counter()
            vector_rows = _vector_search(conn, vector, limit=args.top_k)
            vector_elapsed_s = time.perf_counter() - strategy_started

            pool_k = max(1, int(args.pool_k))
            strategy_started = time.perf_counter()
            hybrid_rows = _hybrid_search(
                conn,
                golden.query,
                vector,
                rrf_k=args.rrf_k,
                pool_k=pool_k,
                limit=max(pool_k, args.top_k),
            )
            hybrid_elapsed_s = time.perf_counter() - strategy_started

            strategy_started = time.perf_counter()
            rerank_rows = _rerank(
                golden.query,
                hybrid_rows,
                region=region,
                model_id=rerank_model,
                limit=args.top_k,
            )
            rerank_elapsed_s = hybrid_elapsed_s + (time.perf_counter() - strategy_started)

            # Agentic row: the SHIPPED extractor + planner decide the
            # filters. Using golden.filters here instead would make this
            # an oracle experiment that cannot fail on a planner bug.
            strategy_started = time.perf_counter()
            plan = _plan_for(build_plan, golden, extractor, args.top_k)
            agentic_candidates = _hybrid_search(
                conn,
                golden.query,
                vector,
                rrf_k=args.rrf_k,
                pool_k=pool_k,
                limit=max(pool_k, args.top_k),
                filters=_plan_filters(plan),
            )
            agentic_rows = _rerank(
                golden.query,
                agentic_candidates,
                region=region,
                model_id=rerank_model,
                limit=args.top_k,
            )
            agentic_elapsed_s = time.perf_counter() - strategy_started
            plan_score = _score_plan(plan, golden.filters)
            planner_scores.append(plan_score)
            compliance = _score_compliance(agentic_rows, plan)
            compliance_scores.append(compliance)

            rows_by_strategy = {
                "vector": vector_rows,
                "hybrid": hybrid_rows[: args.top_k],
                "rerank": rerank_rows,
                "agentic": agentic_rows,
            }
            strategy_timings["vector"].append(vector_elapsed_s)
            strategy_timings["hybrid"].append(hybrid_elapsed_s)
            strategy_timings["rerank"].append(rerank_elapsed_s)
            strategy_timings["agentic"].append(agentic_elapsed_s)
            detail = {
                "label": golden.label,
                "query": golden.query,
                "expected": list(golden.expected),
                "latency_ms": {
                    "vector": round(vector_elapsed_s * 1000, 1),
                    "hybrid": round(hybrid_elapsed_s * 1000, 1),
                    "rerank": round(rerank_elapsed_s * 1000, 1),
                    "agentic": round(agentic_elapsed_s * 1000, 1),
                },
            }
            candidate_ids = [str(row["product_id"]) for row in hybrid_rows]
            coverage_hits, coverage_total, coverage = _recall(candidate_ids, golden.expected)
            pool_coverage.append((coverage_hits, coverage_total))
            detail["hybrid_candidate_coverage"] = {
                "pool_k": pool_k,
                "hits": coverage_hits,
                "expected": coverage_total,
                "coverage": round(coverage, 3),
            }
            detail["planner"] = plan_score
            detail["agentic_hard_constraint_compliance"] = compliance
            detail["search_plan"] = plan.to_dict()
            for strategy, rows in rows_by_strategy.items():
                product_ids = [str(row["product_id"]) for row in rows]
                hits, total, recall = _recall_at_5(product_ids, golden.expected)
                mrr = _mrr_at_5(product_ids, golden.expected)
                hit_at_1 = _hit_at_1(product_ids, golden.expected)
                short_result = int(len(product_ids) < args.top_k)
                summary[strategy].append((hits, total, mrr, hit_at_1, short_result))
                detail[strategy] = {
                    "top5": product_ids[:5],
                    "hits": hits,
                    "expected": total,
                    "recall_at_5": round(recall, 3),
                    "hit_at_1": hit_at_1,
                    "mrr_at_5": round(mrr, 3),
                    "short_result_at_5": bool(short_result),
                }
            detailed.append(detail)

    elapsed_s = time.perf_counter() - started
    totals = _metric_totals(summary)
    timing_totals = _timing_totals(strategy_timings)
    coverage_hits = sum(pair[0] for pair in pool_coverage)
    coverage_expected = sum(pair[1] for pair in pool_coverage)
    coverage_total = round(coverage_hits / coverage_expected if coverage_expected else 0.0, 3)
    rerank_lift = round(totals["rerank"]["mrr_at_5"] - totals["hybrid"]["mrr_at_5"], 3)
    agentic_lift = round(totals["agentic"]["mrr_at_5"] - totals["hybrid"]["mrr_at_5"], 3)
    planner_totals = _planner_totals(planner_scores)
    compliance_totals = _compliance_totals(compliance_scores)
    gate = _evaluate_gate(
        totals=totals,
        coverage=coverage_total,
        planner=planner_totals,
        compliance=compliance_totals,
        strict_planner=args.strict_planner,
    )
    if args.json:
        print(json.dumps({
            "query_count": len(GOLDEN_QUERIES),
            "rrf_k": args.rrf_k,
            "pool_k": args.pool_k,
            "top_k": args.top_k,
            "embed_model": embed_model,
            "rerank_model": rerank_model,
            "elapsed_s": round(elapsed_s, 2),
            "embedding_batch_ms": round(embed_elapsed_s * 1000, 1),
            "avg_strategy_latency_ms": timing_totals,
            "summary": totals,
            "hybrid_candidate_coverage_at_pool": coverage_total,
            "rerank_lift_mrr_vs_hybrid": rerank_lift,
            "agentic_lift_mrr_vs_hybrid": agentic_lift,
            "planner": planner_totals,
            "hard_constraint_compliance": compliance_totals,
            "gate": gate,
            "queries": detailed,
        }, indent=2))
        return 0 if (gate["passed"] or args.no_gate) else 1

    print(f"Pellier retrieval eval | queries={len(GOLDEN_QUERIES)} | rrf_k={args.rrf_k} | pool_k={args.pool_k} | top_k={args.top_k}")
    print(f"Models: {embed_model} + {rerank_model}")
    print()
    _print_summary(summary)
    print()
    print(f"embedding batch latency: {embed_elapsed_s * 1000:.1f} ms")
    print("avg strategy latency (ms): " + " | ".join(
        f"{strategy} {latency:.1f}" for strategy, latency in timing_totals.items()
    ))
    print(f"hybrid candidate coverage@pool_k: {coverage_total:.3f}")
    print(f"mrr@5 lift vs hybrid: rerank {rerank_lift:+.3f} | agentic {agentic_lift:+.3f}")
    print()
    print("query | expected | vector@5 | hybrid@5 | rerank@5 | agentic@5")
    print("------|----------|----------|----------|----------|----------")
    for item in detailed:
        print(
            f"{item['label']} | {','.join(item['expected'])} | "
            f"{','.join(item['vector']['top5']) or '-'} | "
            f"{','.join(item['hybrid']['top5']) or '-'} | "
            f"{','.join(item['rerank']['top5']) or '-'} | "
            f"{','.join(item['agentic']['top5']) or '-'}"
        )
    print()
    print(
        "planner: constraint recall "
        f"{planner_totals['constraint_recall']:.3f} "
        f"({planner_totals['constraints_recovered']}/"
        f"{planner_totals['constraints_expected']}) | "
        f"hallucinated-constraint rate "
        f"{planner_totals['hallucinated_constraint_rate']:.3f}"
    )
    print(
        "hard-constraint compliance: "
        f"violations {compliance_totals['hard_violations']}"
        f"/{compliance_totals['rows_scored']} rows "
        f"(rate {compliance_totals['hard_constraint_violation_rate']:.3f}) | "
        f"exclusion violations {compliance_totals['exclusion_violations']} "
        f"(rate {compliance_totals['exclusion_violation_rate']:.3f})"
    )
    print()
    if gate["passed"]:
        print("GATE: PASS — every threshold met.")
    else:
        print("GATE: FAIL")
        for failure in gate["failures"]:
            print(f"  - {failure}")
        if args.no_gate:
            print("  (--no-gate set: reporting only, exit status forced to 0)")
    print()
    print(f"Elapsed: {elapsed_s:.1f}s")
    return 0 if (gate["passed"] or args.no_gate) else 1


if __name__ == "__main__":
    raise SystemExit(main())
