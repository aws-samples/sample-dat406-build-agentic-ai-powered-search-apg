"""Security contract for the ``/api/performance/*`` request bodies.

``hnsw.ef_search`` is applied with a Postgres ``SET``, which cannot take a bound
parameter, so the value is interpolated into statement text. psycopg permits
multiple statements in one ``execute()`` when no parameters are bound, so an
unvalidated body turns that interpolation into arbitrary SQL execution:

    {"query": "x", "ef_search": "40; DROP TABLE pellier.tool_audit"}

Two independent gates must hold, and this module tests both:

1. The route rejects the payload (Pydantic bounds on ``ef_search``).
2. ``index_performance`` clamps at the sink, because the service is reachable
   from more than one caller.

Runnable from the repo root per ``pytest.ini``:

    pellier/backend/.venv/bin/python -m pytest \
        pellier/backend/tests/test_performance_endpoint_validation.py -v
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app as app_module
from models.search import (
    PerfCompareRequest,
    PerfIterativeScanRequest,
    PerfQuantizationRequest,
)
from services.index_performance import (
    EF_SEARCH_DEFAULT,
    EF_SEARCH_MAX,
    EF_SEARCH_MIN,
    _clamp_ef_search,
)

# The exact payload from the audit write-up. If any gate regresses, this string
# reaches a `SET` statement and the trailing DROP executes.
INJECTION_PAYLOAD = "40; DROP TABLE pellier.tool_audit"


# ---------------------------------------------------------------------------
# Gate 1 — the request models reject the payload before it reaches SQL
# ---------------------------------------------------------------------------


def test_compare_request_rejects_injection_string() -> None:
    """A non-numeric ``ef_search`` must not validate."""
    with pytest.raises(ValidationError):
        PerfCompareRequest(query="x", ef_search=INJECTION_PAYLOAD)


def test_iterative_scan_request_rejects_injection_string() -> None:
    with pytest.raises(ValidationError):
        PerfIterativeScanRequest(
            query="x", category="Shirts", ef_search=INJECTION_PAYLOAD
        )


@pytest.mark.parametrize("bad", [0, -1, 1001, 10**9])
def test_compare_request_enforces_ef_search_bounds(bad: int) -> None:
    """Out-of-range integers are refused, not silently clamped, at the API."""
    with pytest.raises(ValidationError):
        PerfCompareRequest(query="x", ef_search=bad)


@pytest.mark.parametrize("good", [EF_SEARCH_MIN, EF_SEARCH_DEFAULT, EF_SEARCH_MAX])
def test_compare_request_accepts_in_range_values(good: int) -> None:
    assert PerfCompareRequest(query="x", ef_search=good).ef_search == good


def test_compare_request_requires_non_empty_query() -> None:
    with pytest.raises(ValidationError):
        PerfCompareRequest(query="", ef_search=40)


def test_quantization_request_has_no_ef_search_field() -> None:
    """The quantization route never applies ef_search; it must not accept one.

    Guards against a future copy-paste reintroducing the sink here.
    """
    assert "ef_search" not in PerfQuantizationRequest.model_fields


# ---------------------------------------------------------------------------
# Gate 2 — the sink clamps independently of the API layer
# ---------------------------------------------------------------------------


def test_clamp_rejects_injection_string() -> None:
    """A string payload must never survive to interpolation."""
    assert _clamp_ef_search(INJECTION_PAYLOAD) == EF_SEARCH_DEFAULT


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, EF_SEARCH_MIN),
        (-5, EF_SEARCH_MIN),
        (10**9, EF_SEARCH_MAX),
        (1001, EF_SEARCH_MAX),
        (40, 40),
        ("64", 64),
        (None, EF_SEARCH_DEFAULT),
        ({"a": 1}, EF_SEARCH_DEFAULT),
    ],
)
def test_clamp_produces_int_in_range(raw: Any, expected: int) -> None:
    result = _clamp_ef_search(raw)
    assert isinstance(result, int)
    assert EF_SEARCH_MIN <= result <= EF_SEARCH_MAX
    assert result == expected


def test_clamped_value_is_never_multi_statement() -> None:
    """The property that actually matters: the interpolated text is one int.

    Renders the clamped value exactly as the sink does and asserts no statement
    separator can appear.
    """
    for raw in [INJECTION_PAYLOAD, "40; SELECT 1", "1' OR '1'='1", 10**9, None]:
        statement = f"SET hnsw.ef_search = {_clamp_ef_search(raw)}"
        assert ";" not in statement
        assert statement.rsplit("=", 1)[1].strip().isdigit()


# ---------------------------------------------------------------------------
# Gate 1, end to end — through the real FastAPI route
# ---------------------------------------------------------------------------


class _StubEmbeddings:
    """Deterministic stand-in so no Bedrock call is made."""

    def generate_embedding(self, query: str) -> List[float]:
        return [0.1] * 1024


class _RecordingPerformanceService:
    """Captures what the route forwards, and fails loudly if SQL is reached."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def compare_index_performance(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "hnsw": {"execution_time_ms": 1},
            "sequential": {"execution_time_ms": 2},
        }

    async def compare_filtered_search(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        return {"ok": True}

    async def compare_quantization_benchmark(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        return {"ok": True}


@pytest.fixture
def perf_service(monkeypatch: pytest.MonkeyPatch) -> _RecordingPerformanceService:
    service = _RecordingPerformanceService()
    monkeypatch.setattr(app_module, "index_performance_service", service)
    monkeypatch.setattr(app_module, "embedding_service", _StubEmbeddings())
    return service


@pytest.fixture
def client(perf_service: _RecordingPerformanceService) -> TestClient:
    """Mount only the three performance routes, bypassing app lifespan."""
    api = FastAPI()
    for route in app_module.app.routes:
        if getattr(route, "path", "").startswith("/api/performance/"):
            api.routes.append(route)
    api.dependency_overrides[app_module.get_embedding_service] = _StubEmbeddings
    return TestClient(api)


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/performance/compare", {"query": "linen shirt"}),
        (
            "/api/performance/iterative-scan",
            {"query": "linen shirt", "category": "Shirts"},
        ),
    ],
)
def test_endpoint_rejects_injection_payload(
    client: TestClient,
    perf_service: _RecordingPerformanceService,
    path: str,
    body: Dict[str, Any],
) -> None:
    """422 from validation, and the service is never invoked."""
    resp = client.post(path, json={**body, "ef_search": INJECTION_PAYLOAD})
    assert resp.status_code == 422, resp.text
    assert perf_service.calls == []


def test_compare_forwards_validated_ef_search(
    client: TestClient, perf_service: _RecordingPerformanceService
) -> None:
    resp = client.post(
        "/api/performance/compare",
        json={"query": "linen shirt", "ef_search": 64, "limit": 5},
    )
    assert resp.status_code == 200, resp.text
    assert perf_service.calls[0]["ef_search"] == 64
    assert perf_service.calls[0]["limit"] == 5


def test_compare_rejects_missing_query(client: TestClient) -> None:
    """Absent query is a validation error, not a hand-rolled 400."""
    resp = client.post("/api/performance/compare", json={"ef_search": 40})
    assert resp.status_code == 422, resp.text
