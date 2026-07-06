#!/usr/bin/env python3
"""Presenter demo: image search over the existing Pellier vector substrate.

Cohere Embed v4 maps text and image inputs into the same 1024-dimensional
space. Pellier's required path stores text embeddings in
``pellier.product_catalog.embedding``; this demo embeds one local product image
and runs the same pgvector cosine operator against that column. Different
modality, same table, same index, same operator.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import boto3
import psycopg


DEFAULT_IMAGE = "pellier/frontend/public/products/theo-stoneware-pour-over.png"


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


def _image_data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _embed_image(path: Path, *, model_id: str, region: str) -> tuple[list[float], float]:
    body = {
        "input_type": "search_query",
        "embedding_types": ["float"],
        "images": [_image_data_uri(path)],
        "output_dimension": 1024,
    }
    started = time.perf_counter()
    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    payload = json.loads(response["body"].read())
    embeddings = payload.get("embeddings")
    if isinstance(embeddings, dict):
        vector = embeddings.get("float", [[]])[0]
    else:
        vector = (embeddings or [[]])[0]
    if len(vector) != 1024:
        raise RuntimeError(f"Expected a 1024-dim image embedding, got {len(vector)}")
    return [float(v) for v in vector], elapsed_ms


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def _query_neighbors(vector: list[float], *, top_k: int) -> list[dict[str, Any]]:
    sql = """
        SELECT
            product_id,
            name,
            category,
            price,
            ROUND((1 - (embedding <=> %s::vector))::numeric, 4) AS cosine_similarity
        FROM pellier.product_catalog
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    literal = _vector_literal(vector)
    with psycopg.connect(
        host=_require("DB_HOST"),
        port=os.environ.get("DB_PORT", "5432"),
        user=_require("DB_USER"),
        password=_require("DB_PASSWORD"),
        dbname=_require("DB_NAME"),
    ) as conn:
        with conn.cursor() as cur:
            started = time.perf_counter()
            cur.execute(sql, (literal, literal, int(top_k)))
            rows = cur.fetchall()
            elapsed_ms = (time.perf_counter() - started) * 1000
    return [
        {
            "rank": i + 1,
            "product_id": row[0],
            "name": row[1],
            "category": row[2],
            "price": float(row[3]),
            "cosine_similarity": float(row[4]),
            "query_ms": round(elapsed_ms, 1),
        }
        for i, row in enumerate(rows)
    ]


def _print_table(rows: list[dict[str, Any]]) -> None:
    print("rank | product_id | cosine | name | category | price")
    print("-----|------------|--------|------|----------|------")
    for row in rows:
        print(
            f"{row['rank']:>4} | {row['product_id']:<10} | "
            f"{row['cosine_similarity']:.4f} | {row['name']} | "
            f"{row['category']} | ${row['price']:.0f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Cohere Embed v4 image search over Pellier catalog embeddings.")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Local image path, relative to repo root by default.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")
    args = parser.parse_args()

    _load_env()
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    model_id = os.environ.get("BEDROCK_EMBEDDING_MODEL") or os.environ.get("BEDROCK_EMBED_MODEL_ID") or "us.cohere.embed-v4:0"
    image_path = Path(args.image)
    if not image_path.is_absolute():
        image_path = _repo_root() / image_path
    if not image_path.is_file():
        raise SystemExit(f"Image not found: {image_path}")

    vector, embed_ms = _embed_image(image_path, model_id=model_id, region=region)
    rows = _query_neighbors(vector, top_k=args.top_k)
    payload = {
        "image": str(image_path.relative_to(_repo_root())),
        "model_id": model_id,
        "embedding_dimension": len(vector),
        "bedrock_embedding_ms": round(embed_ms, 1),
        "query_ms": rows[0]["query_ms"] if rows else 0,
        "statement": "different modality, same table, same index, same operator",
        "neighbors": rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Image: {payload['image']}")
        print(f"Model: {model_id} ({payload['embedding_dimension']} dimensions)")
        print(f"Embed: {payload['bedrock_embedding_ms']} ms | pgvector query: {payload['query_ms']} ms")
        print("Different modality, same table, same index, same operator.")
        print()
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
