"""Behavioral tests for managed Gateway retrieval receipt persistence."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import boto3
import pytest


REPO = Path(__file__).resolve().parents[3]
DEPLOY = REPO / "scripts" / "deploy"
SERVER_PATH = DEPLOY / "pellier_search_server.py"


def _load_server(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Load the Lambda module with inert AWS clients."""
    if str(DEPLOY) not in sys.path:
        sys.path.insert(0, str(DEPLOY))

    class _Client:
        pass

    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: _Client())
    spec = importlib.util.spec_from_file_location(
        "pellier_gateway_retrieval_server", SERVER_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Rds:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def execute_statement(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"numberOfRecordsUpdated": 1}


def _candidate_rows() -> list[dict[str, Any]]:
    return [
        {
            "productId": "P-1",
            "product_description": "Linen Camp Shirt",
            "category_name": "Resort",
            "price": 128.0,
            "stars": 4.8,
            "vector_rank": 1,
            "lexical_rank": 2,
            "rrf_score": 0.0325,
        },
        {
            "productId": "P-2",
            "product_description": "Linen Trouser",
            "category_name": "Resort",
            "price": 148.0,
            "stars": 4.9,
            "vector_rank": 2,
            "lexical_rank": 1,
            "rrf_score": 0.0324,
        },
    ]


def _parameter_values(call: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for parameter in call["parameters"]:
        value = parameter["value"]
        values[parameter["name"]] = (
            value.get("stringValue") if "stringValue" in value else None
        )
    return values



def _shared_transport():
    """Return the module that owns the only Data API client.

    The surface servers share `common/dataapi.py` rather than each holding a
    client, so this is where a fake belongs. Reads are stubbed separately at
    `_execute_sql`; the receipt INSERT goes through `execute_write`, so a fake
    client here still captures it.
    """
    import common.dataapi as dataapi

    return dataapi


def test_gateway_hybrid_search_persists_actual_ranking_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _load_server(monkeypatch)
    rds = _Rds()
    monkeypatch.setattr(_shared_transport(), "rds_client", rds)
    monkeypatch.setattr(server, "_get_embedding", lambda _query: [0.1, 0.2])
    monkeypatch.setattr(server, "_execute_sql", lambda *_args, **_kwargs: _candidate_rows())
    monkeypatch.setattr(
        server,
        "_bedrock_rerank",
        lambda *_args, **_kwargs: [
            {"index": 1, "relevance_score": 0.92},
            {"index": 0, "relevance_score": 0.81},
        ],
    )

    response = server.lambda_handler(
        {
            "name": "search_products_hybrid",
            "arguments": {
                "query": "linen for a resort",
                "turn_id": "turn-0123456789abcdef0123456789abcdef",
                "limit": 2,
                "max_price": 175,
            },
        },
        SimpleNamespace(client_context=None),
    )

    payload = json.loads(response["content"][0]["text"])
    assert [product["productId"] for product in payload["products"]] == ["P-2", "P-1"]
    assert "_receipt_evidence" not in payload
    assert len(rds.calls) == 1

    call = rds.calls[0]
    assert "INSERT INTO pellier.retrieval_receipts" in call["sql"]
    values = _parameter_values(call)
    assert values["turn_id"] == "turn-0123456789abcdef0123456789abcdef"
    assert values["query_preview"] == "linen for a resort"
    assert values["rail"] == "gateway-mcp"
    assert json.loads(values["candidate_product_ids"]) == ["P-1", "P-2"]
    assert json.loads(values["citation_ids"]) == ["P-2", "P-1"]
    assert json.loads(values["vector_ranks"]) == {"P-1": 1, "P-2": 2}
    assert json.loads(values["lexical_ranks"]) == {"P-1": 2, "P-2": 1}
    assert json.loads(values["rrf_scores"]) == {"P-1": 0.0325, "P-2": 0.0324}
    assert json.loads(values["rerank_scores"]) == {"P-2": 0.92, "P-1": 0.81}
    plan = json.loads(values["search_plan"])
    assert plan["source"] == "agentcore-gateway-lambda"
    assert plan["hard_constraints"] == {"in_stock": True, "max_price": 175}


def test_gateway_hybrid_search_never_persists_an_untrusted_turn_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _load_server(monkeypatch)
    rds = _Rds()
    monkeypatch.setattr(_shared_transport(), "rds_client", rds)
    monkeypatch.setattr(server, "_get_embedding", lambda _query: [0.1, 0.2])
    monkeypatch.setattr(server, "_execute_sql", lambda *_args, **_kwargs: _candidate_rows())
    monkeypatch.setattr(server, "_bedrock_rerank", lambda *_args, **_kwargs: [])

    response = server.lambda_handler(
        {
            "name": "search_products_hybrid",
            "arguments": {
                "query": "linen",
                "turn_id": "not-a-server-minted-turn",
                "limit": 1,
            },
        },
        SimpleNamespace(client_context=None),
    )

    assert response.get("isError") is not True
    assert rds.calls == []


def test_gateway_semantic_search_persists_cosine_order_without_rerank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _load_server(monkeypatch)
    rds = _Rds()
    monkeypatch.setattr(_shared_transport(), "rds_client", rds)
    monkeypatch.setattr(server, "_get_embedding", lambda _query: [0.1, 0.2])
    monkeypatch.setattr(
        server,
        "_execute_sql",
        lambda *_args, **_kwargs: [
            {"productId": "P-3", "similarity": 0.91, "category_name": "Resort"},
            {"productId": "P-4", "similarity": 0.77, "category_name": "Resort"},
        ],
    )

    server.lambda_handler(
        {
            "name": "search_products",
            "arguments": {
                "query": "resort linen",
                "turn_id": "turn-abcdefabcdefabcdefabcdefabcdefab",
                "limit": 2,
            },
        },
        SimpleNamespace(client_context=None),
    )

    assert len(rds.calls) == 1
    values = _parameter_values(rds.calls[0])
    assert json.loads(values["vector_ranks"]) == {"P-3": 1, "P-4": 2}
    assert json.loads(values["rrf_scores"]) == {}
    assert json.loads(values["rerank_scores"]) == {}
    config = json.loads(values["retrieval_config"])
    assert config["strategy"] == "vector_similarity"
    assert config["similarity_scores"] == {"P-3": 0.91, "P-4": 0.77}
