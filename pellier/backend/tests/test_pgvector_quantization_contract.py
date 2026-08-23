"""pgvector quantization contract for the Measure deep-dive surface.

These are the tripwires for four confirmed defects in
``services/index_performance.py`` that shipped without coverage. Each one
produced a *plausible* answer, which is why no test caught them:

1. The binary-quantization benchmark ordered by ``<#>`` on a ``bit``
   expression. pgvector defines only ``<~>`` (Hamming) and ``<%>``
   (Jaccard) for ``bit``; ``<#>`` is negative inner product and exists for
   ``vector``/``halfvec``/``sparsevec`` only. The query therefore raised
   ``operator does not exist`` on every run and the broad ``except``
   reported it as an unavailable feature rather than a bug.
2. The "scalar quantization" bucket claimed int8 at 1 byte/dimension and a
   4x reduction while its own SQL example cast to ``halfvec`` — fp16, 2
   bytes/dimension, 2x. The number and the SQL described different
   techniques.
3. The HNSW result substituted a fabricated index name
   (``product_catalog_embedding_hnsw_idx``) when the plan did not name one.
   The real index is ``product_catalog_embedding_hnsw``.
4. Feature-version comments attributed ``binary_quantize`` and
   ``hnsw.iterative_scan`` to pgvector 0.8.1. Upstream: ``binary_quantize``,
   ``halfvec`` and ``bit`` indexing landed in 0.7.0; iterative index scans
   landed in 0.8.0.

The database is mocked at the psycopg boundary — these assert the SQL the
service emits and the arithmetic it reports, neither of which needs a live
cluster.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

import services.index_performance as index_performance
from services.index_performance import IndexPerformanceService

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_SQL = _REPO_ROOT / "scripts" / "migrations" / "001_schema.sql"

# The real index, as created by migration 001. The service must never invent
# a name that differs from this one.
REAL_HNSW_INDEX = "product_catalog_embedding_hnsw"
FABRICATED_HNSW_INDEX = "product_catalog_embedding_hnsw_idx"

INDEX_BYTES = 4_096_000
ROW_COUNT = 40


# ---------------------------------------------------------------------------
# psycopg boundary fake
# ---------------------------------------------------------------------------


class _Row(dict):
    """Row that answers by column name or position.

    The service mixes ``dict_row`` cursors with plain ones (``result[0]``),
    so the fake has to satisfy both access styles.
    """

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _FakeCursor:
    """Records executed SQL and answers the shapes the service reads."""

    def __init__(self, log: List[str]) -> None:
        self._log = log
        self._last = ""

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        self._last = sql
        self._log.append(sql)

    def fetchone(self) -> Optional[_Row]:
        if "pg_relation_size" in self._last:
            return _Row(index_bytes=INDEX_BYTES, index_size="4000 kB")
        if "COUNT(*)" in self._last:
            return _Row(count=ROW_COUNT, cnt=ROW_COUNT)
        if "extversion" in self._last:
            return _Row(extversion="0.8.0")
        if "EXPLAIN" in self._last:
            return _Row(plan={})
        return None

    def fetchall(self) -> List[_Row]:
        if "productId" in self._last:
            return [_Row(productId=1, description="d", price=1.0, rating=5.0)]
        return []


class _FakeConnection:
    def __init__(self, log: List[str]) -> None:
        self._log = log

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def cursor(self, *args: Any, **kwargs: Any) -> _FakeCursor:
        return _FakeCursor(self._log)


@pytest.fixture
def sql_log(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """Every statement the service sends, in order."""
    log: List[str] = []
    monkeypatch.setattr(
        index_performance.psycopg, "connect", lambda *a, **k: _FakeConnection(log)
    )
    return log


@pytest.fixture
def service() -> IndexPerformanceService:
    return IndexPerformanceService("postgresql://stub/stub")


# ---------------------------------------------------------------------------
# 1. Binary quantization must use a bit operator that exists
# ---------------------------------------------------------------------------


def _binary_statements(sql_log: List[str]) -> List[str]:
    return [s for s in sql_log if "binary_quantize" in s]


def test_binary_quantization_orders_by_hamming_operator(
    service: IndexPerformanceService, sql_log: List[str]
) -> None:
    """``<~>`` is the Hamming operator for ``bit``; the benchmark must use it."""
    asyncio.run(
        service.compare_quantization_benchmark(
            query="linen shirt", embedding=[0.1] * 1024, limit=5, num_runs=1
        )
    )
    statements = _binary_statements(sql_log)
    assert statements, "the binary-quantization branch never ran"
    for statement in statements:
        assert "<~>" in statement, statement


def test_binary_quantization_never_uses_inner_product_on_bit(
    service: IndexPerformanceService, sql_log: List[str]
) -> None:
    """``<#>`` is undefined for ``bit`` — its return would be a hard SQL error."""
    asyncio.run(
        service.compare_quantization_benchmark(
            query="linen shirt", embedding=[0.1] * 1024, limit=5, num_runs=1
        )
    )
    for statement in _binary_statements(sql_log):
        assert "<#>" not in statement, statement


def test_binary_quantization_branch_reports_available(
    service: IndexPerformanceService, sql_log: List[str]
) -> None:
    """A valid operator means the branch reports results, not an error dict.

    With the broken operator this key stayed False against a real cluster
    while the surface rendered it as "feature unavailable".
    """
    result = asyncio.run(
        service.compare_quantization_benchmark(
            query="linen shirt", embedding=[0.1] * 1024, limit=5, num_runs=1
        )
    )
    assert result["binary_available"] is True
    assert "error" not in result["binary"]


def test_halfvec_branch_uses_cosine_operator(
    service: IndexPerformanceService, sql_log: List[str]
) -> None:
    """``halfvec`` keeps ``<=>``; only the ``bit`` branch changes operator."""
    asyncio.run(
        service.compare_quantization_benchmark(
            query="linen shirt", embedding=[0.1] * 1024, limit=5, num_runs=1
        )
    )
    halfvec = [s for s in sql_log if "halfvec" in s]
    assert halfvec, "the halfvec branch never ran"
    for statement in halfvec:
        assert "<=>" in statement, statement


# ---------------------------------------------------------------------------
# 2. Quantization arithmetic must match the technique the SQL demonstrates
# ---------------------------------------------------------------------------


@pytest.fixture
def quantization(
    service: IndexPerformanceService, sql_log: List[str]
) -> Dict[str, Any]:
    return asyncio.run(service.get_quantization_comparison())


def test_halfvec_is_two_bytes_per_dimension(quantization: Dict[str, Any]) -> None:
    """fp16 over 1024 dimensions is 2048 bytes, not 1024."""
    assert quantization["scalar_quantization"]["bytes_per_vector"] == 2048


def test_halfvec_reduction_is_two_x_not_four_x(quantization: Dict[str, Any]) -> None:
    assert quantization["scalar_quantization"]["memory_reduction"] == "2x"


def test_halfvec_bucket_is_not_labelled_int8(quantization: Dict[str, Any]) -> None:
    """pgvector has no native int8 scalar quantization; do not imply it does."""
    label = quantization["scalar_quantization"]["type"].lower()
    assert "halfvec" in label
    assert "int8" not in label


def test_halfvec_estimate_is_half_the_float32_index(
    quantization: Dict[str, Any]
) -> None:
    """The reported estimate must follow from the reported bytes/vector."""
    assert quantization["scalar_quantization"]["estimated_index_bytes"] == (
        INDEX_BYTES // 2
    )


def test_binary_quantization_is_one_bit_per_dimension(
    quantization: Dict[str, Any]
) -> None:
    assert quantization["binary_quantization"]["bytes_per_vector"] == 128
    assert quantization["binary_quantization"]["memory_reduction"] == "32x"


def test_sql_examples_match_their_buckets(quantization: Dict[str, Any]) -> None:
    examples = quantization["sql_examples"]
    assert "halfvec" in examples["sq"]
    assert "binary_quantize" in examples["bq"]


def test_binary_quantization_example_cites_the_correct_version(
    quantization: Dict[str, Any]
) -> None:
    """``binary_quantize`` and ``bit`` indexing shipped in pgvector 0.7.0."""
    example = quantization["sql_examples"]["bq"]
    assert "0.7+" in example
    assert "0.8.1" not in example


def test_binary_quantization_example_uses_a_real_opclass(
    quantization: Dict[str, Any]
) -> None:
    """``bit_hamming_ops`` is the upstream HNSW opclass for ``bit``."""
    assert "bit_hamming_ops" in quantization["sql_examples"]["bq"]


# ---------------------------------------------------------------------------
# 3. The service must not invent an index name
# ---------------------------------------------------------------------------


def test_real_hnsw_index_name_exists_in_migration() -> None:
    """Anchors the expected name to the DDL that creates it."""
    assert REAL_HNSW_INDEX in _SCHEMA_SQL.read_text()


def test_service_never_hardcodes_a_fabricated_index_name() -> None:
    """The ``_idx`` variant does not exist in any migration."""
    source = inspect.getsource(index_performance)
    assert FABRICATED_HNSW_INDEX not in source
    assert FABRICATED_HNSW_INDEX not in _SCHEMA_SQL.read_text()


def test_hnsw_result_reports_whether_the_plan_used_an_index(
    service: IndexPerformanceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No index in the plan must surface as False, not as a guessed name."""
    log: List[str] = []
    monkeypatch.setattr(
        index_performance.psycopg, "connect", lambda *a, **k: _FakeConnection(log)
    )
    monkeypatch.setattr(
        IndexPerformanceService, "_extract_index_from_plan", lambda self, plan: None
    )
    monkeypatch.setattr(
        IndexPerformanceService,
        "_clear_cache",
        lambda self, conn: asyncio.sleep(0),
    )
    result = asyncio.run(
        service.compare_index_performance(
            query="linen shirt",
            embedding=[0.1] * 1024,
            limit=5,
            ef_search=40,
            num_runs=1,
        )
    )
    hnsw = result["hnsw"]
    assert hnsw["index_used"] is None
    assert hnsw["plan_used_index"] is False


# ---------------------------------------------------------------------------
# 4. The index-stats query has to be executable
# ---------------------------------------------------------------------------


def test_index_stats_sizes_the_index_by_oid_not_indexrelid(
    service: IndexPerformanceService, sql_log: List[str]
) -> None:
    """``pg_indexes`` exposes no ``indexrelid``.

    ``pg_relation_size(indexrelid)`` raised ``UndefinedColumn``, so
    ``/api/performance/stats`` returned 500 on every call and the surface that
    reports the live pgvector version had nothing to read. Live-verified after
    the fix against Aurora PostgreSQL 18.3 / pgvector 0.8.1.
    """
    asyncio.run(service.get_index_stats())
    index_queries = [s for s in sql_log if "pg_indexes" in s]
    assert index_queries, "get_index_stats never queried pg_indexes"
    for statement in index_queries:
        assert "pg_relation_size(indexrelid)" not in statement, statement
        assert "pg_relation_size(c.oid)" in statement, statement


def test_index_stats_binds_size_to_the_reported_schema(
    service: IndexPerformanceService, sql_log: List[str]
) -> None:
    """Joining on name alone can size a same-named index in another schema."""
    asyncio.run(service.get_index_stats())
    index_queries = [s for s in sql_log if "pg_indexes" in s]
    for statement in index_queries:
        assert "pg_namespace" in statement, statement
        assert "n.nspname = i.schemaname" in statement, statement


def test_index_stats_reports_the_installed_extension_version(
    service: IndexPerformanceService, sql_log: List[str]
) -> None:
    """The surface must source the version from the cluster, not a literal."""
    result = asyncio.run(service.get_index_stats())
    assert any("extversion" in s and "pg_extension" in s for s in sql_log)
    assert result["pgvector_version"] == "0.8.0"  # the fake cursor's value


# ---------------------------------------------------------------------------
# 5. Feature-version attributions
# ---------------------------------------------------------------------------


def test_no_iterative_scan_claim_points_at_0_8_1() -> None:
    """Iterative index scans shipped in pgvector 0.8.0."""
    source = inspect.getsource(index_performance)
    assert "0.8.1" not in source
