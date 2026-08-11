"""
Pellier Search MCP Server — Lambda-hosted MCP server for catalog discovery.

Exposes the six catalog and inventory tools from the canonical 15-tool
Pellier contract:
  - find_pieces
  - find_pieces_hybrid
  - explore_collection
  - floor_check
  - running_low
  - restock_shelf

Deployed as a Lambda function behind AgentCore Gateway. The Lambda
mirrors the in-process @tool functions in ``pellier/backend/services/``
— same JSON envelopes, same error shapes — so swapping the orchestrator
between the in-process path and the Gateway path is invisible to the
agent's prompt.

References:
    Cohere Rerank on Bedrock:
        https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-cohere-rerank.html
    RDS Data API:
        https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html
"""
import json
import hashlib
import logging
import os
import time
from typing import Any

import boto3

from common.types import resolve_invocation

logger = logging.getLogger(__name__)

# --- Database helpers (RDS Data API) ---

REGION = os.environ.get("REGION", "us-east-1")
DB_REGION = os.environ.get("DB_REGION", REGION)
DB_CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN = os.environ.get("SECRET_ARN", "")
DATABASE = os.environ.get("DATABASE", "postgres")
# Cohere Embed v4 — MUST match the catalog seed + in-process path so the
# managed Gateway vector search shares the same embedding space.
EMBED_MODEL_ID = os.environ.get("BEDROCK_EMBED_MODEL_ID", "us.cohere.embed-v4:0")
SCHEMA = "pellier"

# Module-level clients for Lambda warm start reuse
rds_client = boto3.client("rds-data", region_name=DB_REGION)
bedrock_client = boto3.client("bedrock-runtime", region_name=REGION)
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=REGION)


def _execute_sql(sql: str, parameters: list = None) -> list[dict]:
    """Execute SQL via RDS Data API and return rows as dicts."""
    params = {
        "resourceArn": DB_CLUSTER_ARN,
        "secretArn": SECRET_ARN,
        "database": DATABASE,
        "sql": sql,
        # Without this the Data API omits columnMetadata entirely, columns
        # is [] and the first returned row IndexErrors (box-verified
        # 2026-06-12 — "list index out of range" on every successful SELECT).
        "includeResultMetadata": True,
    }
    if parameters:
        params["parameters"] = parameters

    response = rds_client.execute_statement(**params)
    columns = [col["name"] for col in response.get("columnMetadata", [])]
    rows = []
    for record in response.get("records", []):
        row = {}
        for i, field in enumerate(record):
            if "stringValue" in field:
                row[columns[i]] = field["stringValue"]
            elif "longValue" in field:
                row[columns[i]] = field["longValue"]
            elif "doubleValue" in field:
                row[columns[i]] = field["doubleValue"]
            elif "booleanValue" in field:
                row[columns[i]] = field["booleanValue"]
            elif "isNull" in field:
                row[columns[i]] = None
            else:
                row[columns[i]] = str(field)
        rows.append(row)
    return rows


def _execute_in_transaction(
    transaction_id: str,
    sql: str,
    parameters: list | None = None,
) -> list[dict]:
    params = {
        "resourceArn": DB_CLUSTER_ARN,
        "secretArn": SECRET_ARN,
        "database": DATABASE,
        "sql": sql,
        "transactionId": transaction_id,
        "includeResultMetadata": True,
    }
    if parameters:
        params["parameters"] = parameters
    response = rds_client.execute_statement(**params)
    columns = [col["name"] for col in response.get("columnMetadata", [])]
    return [
        {
            columns[index]: (
                field.get("stringValue")
                if "stringValue" in field
                else field.get("longValue")
                if "longValue" in field
                else field.get("doubleValue")
                if "doubleValue" in field
                else None
            )
            for index, field in enumerate(record)
        }
        for record in response.get("records", [])
    ]


def _write_tool_audit(tool: str, args: dict, result: dict, latency_ms: int) -> None:
    """Record a Gateway mutation after the target actually executes."""
    try:
        rds_client.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DATABASE,
            sql=(
                f"INSERT INTO {SCHEMA}.tool_audit "
                "(session_id, tool, caller, args, result, latency_ms) "
                "VALUES (:sid, :tool, 'gateway', :args::jsonb, "
                ":result::jsonb, :latency_ms)"
            ),
            parameters=[
                {
                    "name": "sid",
                    "value": {"stringValue": "gateway-stock-keeper"},
                },
                {"name": "tool", "value": {"stringValue": tool}},
                {
                    "name": "args",
                    "value": {"stringValue": json.dumps(args, default=str)},
                },
                {
                    "name": "result",
                    "value": {"stringValue": json.dumps(result, default=str)},
                },
                {"name": "latency_ms", "value": {"longValue": int(latency_ms)}},
            ],
        )
    except Exception as exc:
        logger.warning("tool_audit write failed (non-fatal): %s", exc)


def _get_embedding(text: str) -> list[float]:
    """Generate a query embedding via Cohere Embed v4.

    Must match the in-process path (pellier/backend/services/embeddings.py):
    the catalog was seeded with Cohere Embed v4 at output_dimension=1024, so the
    managed Gateway path has to embed in the SAME vector space — Titan v2 vectors
    are a different space and would make pgvector cosine search return wrong
    rankings even though the dimension (1024) happens to match. input_type is
    "search_query" because these are live shopper queries, not catalog docs.
    """
    response = bedrock_client.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps(
            {"texts": [text], "input_type": "search_query", "output_dimension": 1024}
        ),
    )
    result = json.loads(response["body"].read())
    return result["embeddings"]["float"][0]


# --- MCP Tool implementations ---


def semantic_search(query: str, limit: int = 5, max_price: float = None, min_rating: float = None) -> dict:
    """Search products by semantic similarity using pgvector."""
    embedding = _get_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    where_clauses = ["quantity > 0"]
    parameters = [
        {"name": "embedding", "value": {"stringValue": embedding_str}},
        {"name": "lim", "value": {"longValue": int(limit)}},
    ]
    if max_price:
        where_clauses.append("price <= :max_price")
        parameters.append({"name": "max_price", "value": {"doubleValue": float(max_price)}})
    if min_rating:
        where_clauses.append("rating >= :min_rating")
        parameters.append({"name": "min_rating", "value": {"doubleValue": float(min_rating)}})
    where_sql = " AND ".join(where_clauses)

    # NO session GUCs here: Data API execute_statement is single-statement
    # ("Multistatements aren't supported", box-verified 2026-06-12 — a
    # prepended SET killed EVERY read tool on the Gateway path). The
    # hnsw.iterative_scan tuning stays on the in-process rail (psycopg);
    # at this catalog's scale it doesn't change recall anyway.
    #
    # Column names: the seeded schema (001_schema.sql) is description/
    # category/rating/badge — NOT the Amazon-dataset names these servers
    # were first written against (box-verified 2026-06-12: 42703). Aliases
    # keep the response keys the downstream Python already expects.
    sql = f"""
        SELECT "productId", description AS product_description, price,
               rating AS stars, reviews,
               category AS category_name, quantity, "imgUrl",
               1 - (embedding <=> :embedding::vector) AS similarity
        FROM {SCHEMA}.product_catalog
        WHERE {where_sql}
        ORDER BY embedding <=> :embedding::vector
        LIMIT :lim;
    """
    rows = _execute_sql(sql, parameters)
    return {"products": rows, "query": query, "count": len(rows)}


def get_inventory_health() -> dict:
    """Get inventory health summary across categories."""
    sql = f"""
        SELECT category AS category_name,
               COUNT(*) AS total_products,
               SUM(CASE WHEN quantity < 10 THEN 1 ELSE 0 END) AS low_stock,
               AVG(quantity)::int AS avg_quantity
        FROM {SCHEMA}.product_catalog
        GROUP BY category
        ORDER BY low_stock DESC
        LIMIT 10;
    """
    rows = _execute_sql(sql)
    return {"categories": rows}


def get_low_stock_products(limit: int = 5) -> dict:
    """Get products with lowest stock levels."""
    sql = f"""
        SELECT "productId", description AS product_description, price,
               rating AS stars, quantity, category AS category_name
        FROM {SCHEMA}.product_catalog
        WHERE quantity > 0 AND quantity < 10
        ORDER BY quantity ASC
        LIMIT :lim;
    """
    parameters = [{"name": "lim", "value": {"longValue": int(limit)}}]
    rows = _execute_sql(sql, parameters)
    return {"products": rows, "count": len(rows)}


def find_pieces_hybrid(
    query: str,
    max_price: float = None,
    min_rating: float = 0.0,
    category: str = None,
    limit: int = 5,
) -> dict:
    """Hybrid retrieval: pgvector + Postgres FTS → RRF → Cohere Rerank v3.5.

    Mirrors `services.agent_tools.find_pieces_hybrid` but runs inside the
    Lambda microVM instead of the orchestrator's process. Three stages:

      1. Vector branch (pgvector cosine, k=20) and FTS branch
         (`ts_rank_cd`, k=20) execute in a single SQL statement against
         `pellier.product_catalog`. RDS Data API can't run multi-statement
         transactions, so we fold the two ranked lists into a CTE plus
         Reciprocal Rank Fusion (RRF) inside the same query.
      2. The merged ~30-candidate pool is sent to Cohere Rerank v3.5
         (`cohere.rerank-v3-5:0`) via Bedrock `invoke_model`.
      3. Top `limit` results are returned, with post-rerank filters for
         max_price and min_rating applied last so the rerank order is
         preserved.

    On a Bedrock failure (rate limit, invalid response), we fall back to
    RRF order — the Agent Trace surfaces this as a missing rerank stage in
    telemetry rather than crashing the request.
    """
    embedding = _get_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    # Hybrid retrieval in a single statement. RRF merges the two
    # ranked lists by `1/(60 + rank)` — the same constant the
    # in-process implementation uses, so participants get a one-to-one
    # comparison between paths.
    # Single statement only — Data API rejects a prepended SET (see
    # semantic_search). The CTE shape already folds everything into one query.
    sql = f"""
        WITH vector_results AS (
          SELECT "productId" AS pid,
                 row_number() OVER (ORDER BY embedding <=> :embedding::vector) AS vrank
          FROM {SCHEMA}.product_catalog
          WHERE quantity > 0
          LIMIT 20
        ),
        fts_results AS (
          SELECT "productId" AS pid,
                 row_number() OVER (ORDER BY ts_rank_cd(description_tsv, plainto_tsquery(:query)) DESC) AS frank
          FROM {SCHEMA}.product_catalog
          WHERE quantity > 0
            AND description_tsv @@ plainto_tsquery(:query)
          LIMIT 20
        ),
        rrf AS (
          SELECT COALESCE(v.pid, f.pid) AS pid,
                 COALESCE(1.0 / (60 + v.vrank), 0) +
                 COALESCE(1.0 / (60 + f.frank), 0) AS rrf_score
          FROM vector_results v
          FULL OUTER JOIN fts_results f USING (pid)
        )
        SELECT pc."productId", pc.description AS product_description, pc.price,
               pc.rating AS stars,
               pc.reviews, pc.category AS category_name, pc.quantity, pc."imgUrl",
               rrf.rrf_score
        FROM rrf
        JOIN {SCHEMA}.product_catalog pc ON pc."productId" = rrf.pid
        ORDER BY rrf.rrf_score DESC
        LIMIT 30;
    """
    parameters = [
        {"name": "embedding", "value": {"stringValue": embedding_str}},
        {"name": "query", "value": {"stringValue": query}},
    ]
    candidates = _execute_sql(sql, parameters)

    # Rerank stage. Cohere wants plain text per document; we mirror
    # the in-process `_doc_for_rerank` shape (name + description + cat).
    documents = []
    for p in candidates:
        desc = (p.get("product_description") or "").strip()
        cat = (p.get("category_name") or "").strip()
        if len(desc) > 240:
            desc = desc[:237] + "…"
        documents.append(f"{desc} ({cat})")

    rerank_results = _bedrock_rerank(query, documents, top_n=min(limit * 3, 30))
    if rerank_results:
        ordered = [
            {**candidates[r["index"]], "rerank_score": float(r["relevance_score"])}
            for r in rerank_results
        ]
        search_method = "hybrid+rerank"
    else:
        ordered = [{**c, "rerank_score": None} for c in candidates]
        search_method = "hybrid (rerank fallback to RRF order)"

    # Apply post-rerank filters last so the rerank ordering is honoured.
    filtered = []
    for p in ordered:
        if max_price is not None:
            try:
                if float(p.get("price") or 0) > float(max_price):
                    continue
            except (TypeError, ValueError):
                pass
        if min_rating:
            try:
                if float(p.get("stars") or 0) < float(min_rating):
                    continue
            except (TypeError, ValueError):
                pass
        if category and category.lower() not in (p.get("category_name") or "").lower():
            continue
        filtered.append(p)
        if len(filtered) >= limit:
            break

    return {
        "status": "success",
        "query": query,
        "count": len(filtered),
        "products": filtered,
        "search_method": search_method,
        "pool_size": len(candidates),
    }


def _bedrock_rerank(query: str, documents: list, top_n: int) -> list:
    """Call Cohere Rerank v3.5 on Bedrock; return [] on any failure.

    Returning [] (instead of raising) matches the in-process service so
    the caller can fall back to RRF order. The Agent Trace surfaces a
    missing-rerank state from this signal — useful demo when the
    workshop wants to show graceful degradation under Bedrock pressure.
    """
    if not documents:
        return []
    model_id = "cohere.rerank-v3-5:0"
    model_arn = f"arn:aws:bedrock:{REGION}::foundation-model/{model_id}"
    sources = [
        {
            "type": "INLINE",
            "inlineDocumentSource": {
                "type": "TEXT",
                "textDocument": {"text": document},
            },
        }
        for document in documents
    ]
    try:
        response = bedrock_agent_runtime_client.rerank(
            queries=[{"type": "TEXT", "textQuery": {"text": query}}],
            sources=sources,
            rerankingConfiguration={
                "type": "BEDROCK_RERANKING_MODEL",
                "bedrockRerankingConfiguration": {
                    "modelConfiguration": {"modelArn": model_arn},
                    "numberOfResults": min(top_n, len(sources)),
                },
            },
        )
        return [
            {
                "index": item.get("index"),
                "relevance_score": item.get("relevanceScore", 0.0),
            }
            for item in response.get("results", [])
        ]
    except Exception as exc:
        logger.warning(f"Cohere rerank failed: {exc}")
        return []


def restock_product(
    product_id: str,
    quantity: int,
    idempotency_key: str,
    warehouse_id: str = "BK-01",
) -> dict:
    """Execute the shared idempotent restock transaction in Aurora."""
    if quantity > 500:
        return {"error": "Restock quantity exceeds policy limit of 500", "denied": True}
    clean_key = str(idempotency_key or "").strip()
    if not clean_key:
        return {"error": "idempotency_key is required"}
    clean_warehouse = str(warehouse_id or "BK-01").strip() or "BK-01"
    request_payload = json.dumps(
        {
            "operation": "restock_shelf",
            "arguments": {
                "product_id": int(product_id),
                "quantity": int(quantity),
                "warehouse_id": clean_warehouse,
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    request_hash = hashlib.sha256(request_payload.encode("utf-8")).hexdigest()
    transaction = rds_client.begin_transaction(
        resourceArn=DB_CLUSTER_ARN,
        secretArn=SECRET_ARN,
        database=DATABASE,
    )
    transaction_id = transaction["transactionId"]
    try:
        rows = _execute_in_transaction(
            transaction_id,
            f"SELECT {SCHEMA}.restock_shelf_idempotent("
            ":idempotency_key, :request_hash, :pid, :qty, :warehouse_id"
            ") AS result;",
            [
                {"name": "idempotency_key", "value": {"stringValue": clean_key}},
                {"name": "request_hash", "value": {"stringValue": request_hash}},
                {"name": "pid", "value": {"stringValue": str(product_id)}},
                {"name": "qty", "value": {"longValue": int(quantity)}},
                {"name": "warehouse_id", "value": {"stringValue": clean_warehouse}},
            ],
        )
        rds_client.commit_transaction(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=SECRET_ARN,
            transactionId=transaction_id,
        )
        raw_result = rows[0].get("result") if rows else None
        result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
        if result and result.get("status") == "success":
            return {"success": True, "product": result}
        if result and result.get("status") == "policy_blocked":
            return {"error": result.get("message"), "denied": True}
        return {"error": (result or {}).get("message", "Restock failed"), "result": result}
    except Exception:
        rds_client.rollback_transaction(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=SECRET_ARN,
            transactionId=transaction_id,
        )
        raise


def find_pieces(
    query: str,
    max_price: float = None,
    min_rating: float = 0.0,
    category: str = None,
    limit: int = 5,
) -> dict:
    """Canonical semantic catalog search used by Style Advisor."""
    result = semantic_search(
        query=query,
        limit=limit,
        max_price=max_price,
        min_rating=min_rating,
    )
    if category:
        products = [
            product
            for product in result.get("products", [])
            if category.lower() in str(product.get("category_name", "")).lower()
        ]
        result["products"] = products
        result["count"] = len(products)
    result["status"] = "success"
    result["search_method"] = "semantic"
    return result


def explore_collection(
    category: str,
    min_rating: float = 0.0,
    max_price: float = None,
    limit: int = 5,
) -> dict:
    """Browse one category with deterministic rating and price filters."""
    conditions = ["lower(category) LIKE :category", "quantity > 0"]
    parameters = [
        {
            "name": "category",
            "value": {"stringValue": f"%{str(category).lower()}%"},
        },
        {"name": "limit", "value": {"longValue": max(1, min(int(limit), 20))}},
    ]
    if min_rating:
        conditions.append("rating >= :min_rating")
        parameters.append(
            {"name": "min_rating", "value": {"doubleValue": float(min_rating)}}
        )
    if max_price is not None:
        conditions.append("price <= :max_price")
        parameters.append(
            {"name": "max_price", "value": {"doubleValue": float(max_price)}}
        )
    rows = _execute_sql(
        f"""
        SELECT "productId", name, brand, color, description, price,
               rating, reviews, category, quantity, "imgUrl", badge
          FROM {SCHEMA}.product_catalog
         WHERE {' AND '.join(conditions)}
         ORDER BY rating DESC, reviews::int DESC
         LIMIT :limit;
        """,
        parameters,
    )
    return {
        "status": "success",
        "category": category,
        "count": len(rows),
        "products": rows,
    }


def floor_check(product_query: str = "") -> dict:
    """Return aggregate stock health or one product's warehouse breakdown."""
    tokens = [token for token in str(product_query).strip().split() if token]
    if not tokens:
        stats = _execute_sql(
            f"""
            SELECT COUNT(*) AS total_products,
                   SUM(quantity) AS total_units,
                   COUNT(*) FILTER (WHERE quantity <= 5) AS running_low_count,
                   COUNT(*) FILTER (WHERE quantity = 0) AS out_of_stock_count,
                   ROUND(AVG(quantity), 1) AS avg_quantity
              FROM {SCHEMA}.product_catalog;
            """
        )
        critical = get_low_stock_products(limit=5).get("products", [])
        return {
            "status": "success",
            "statistics": stats[0] if stats else {},
            "critical_items": critical,
        }

    clauses = []
    parameters = []
    for index, token in enumerate(tokens):
        name = f"token{index}"
        clauses.append(f"lower(name) LIKE :{name}")
        parameters.append(
            {"name": name, "value": {"stringValue": f"%{token.lower()}%"}}
        )
    candidates = _execute_sql(
        f"""
        SELECT "productId", name, brand, color, price
          FROM {SCHEMA}.product_catalog
         WHERE {' AND '.join(clauses)}
         ORDER BY rating DESC NULLS LAST
         LIMIT 5;
        """,
        parameters,
    )
    if not candidates:
        return {
            "status": "not_found",
            "query": product_query,
            "message": f"No product matched '{product_query}'.",
        }
    if len(candidates) > 1:
        return {
            "status": "ambiguous",
            "query": product_query,
            "candidates": candidates,
        }

    product = candidates[0]
    warehouses = _execute_sql(
        f"""
        SELECT w.id AS warehouse_id,
               w.display_name AS warehouse_name,
               w.city,
               w.ship_window_min,
               w.ship_window_max,
               wi.quantity
          FROM {SCHEMA}.warehouse_inventory wi
          JOIN {SCHEMA}.warehouses w ON w.id = wi.warehouse_id
         WHERE wi.product_id = :product_id
         ORDER BY wi.quantity DESC, w.id ASC;
        """,
        [
            {
                "name": "product_id",
                "value": {"stringValue": str(product["productId"])},
            }
        ],
    )
    return {
        "status": "success",
        "product": product,
        "total_units": sum(int(row.get("quantity") or 0) for row in warehouses),
        "warehouses": warehouses,
    }


def running_low(limit: int = 5) -> dict:
    """Canonical low-stock read used by Stock Keeper."""
    result = get_low_stock_products(limit=limit)
    for product in result.get("products", []):
        quantity = int(product.get("quantity") or 0)
        product["restock_urgency"] = (
            "critical" if quantity <= 2 else "low" if quantity <= 5 else "watch"
        )
    result["status"] = "success"
    return result


def restock_shelf(
    product_id: int,
    quantity: int,
    idempotency_key: str,
    warehouse_id: str = "BK-01",
) -> dict:
    """Canonical bounded inventory write used by Stock Keeper."""
    if int(quantity) <= 0:
        return {"status": "error", "message": "Quantity must be positive."}
    result = restock_product(
        str(product_id),
        int(quantity),
        idempotency_key,
        warehouse_id,
    )
    if result.get("success"):
        product = result["product"]
        return {
            "status": "success",
            "product_id": product.get("product_id"),
            "name": product.get("name"),
            "new_quantity": product.get("new_quantity"),
            "added": int(quantity),
            "warehouse_id": product.get("warehouse_id"),
            "idempotent_replay": product.get("idempotent_replay", False),
        }
    if result.get("denied"):
        return {"status": "policy_blocked", "message": result["error"]}
    return {"status": "error", "message": result.get("error", "Restock failed")}


# --- Lambda MCP handler ---

TOOLS = {
    "find_pieces": {
        "fn": find_pieces,
        "description": "Search products by natural language query using vector similarity. Returns ranked products with similarity scores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 5},
                "max_price": {"type": "number", "description": "Maximum price filter"},
                "min_rating": {"type": "number", "description": "Minimum star rating filter"},
                "category": {"type": "string", "description": "Optional category substring filter"},
            },
            "required": ["query"],
        },
    },
    "find_pieces_hybrid": {
        "fn": find_pieces_hybrid,
        "description": "Hybrid retrieval over the catalog: pgvector cosine + Postgres FTS merged via RRF, reranked by Cohere Rerank v3.5. Higher quality than semantic_search at the cost of one extra Bedrock call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "max_price": {"type": "number", "description": "Maximum price filter (post-rerank)"},
                "min_rating": {"type": "number", "description": "Minimum star rating filter (post-rerank)", "default": 0.0},
                "category": {"type": "string", "description": "Category substring filter (post-rerank). Leave unset to let the reranker pick across categories."},
                "limit": {"type": "integer", "description": "Max results to return", "default": 5},
            },
            "required": ["query"],
        },
    },
    "explore_collection": {
        "fn": explore_collection,
        "description": "Browse products in a category with optional rating and price filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Product category"},
                "min_rating": {"type": "number", "default": 0.0},
                "max_price": {"type": "number"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["category"],
        },
    },
    "floor_check": {
        "fn": floor_check,
        "description": "Check aggregate inventory or a named product across the Brooklyn, Austin, and Portland warehouses.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_query": {"type": "string", "description": "Optional product name or partial name"},
            },
            "required": [],
        },
    },
    "running_low": {
        "fn": running_low,
        "description": "Get products with critically low stock levels (below 10 units).",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max results", "default": 5}},
            "required": [],
        },
    },
    "restock_shelf": {
        "fn": restock_shelf,
        "description": "Restock a product by adding inventory. Quantity must be <= 500 per policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product ID to restock"},
                "quantity": {"type": "integer", "description": "Quantity to add (max 500)"},
                "idempotency_key": {"type": "string", "description": "Stable unique key for this intended write"},
                "warehouse_id": {"type": "string", "description": "Warehouse receiving stock; defaults to BK-01"},
            },
            "required": ["product_id", "quantity", "idempotency_key"],
        },
    },
}


def lambda_handler(event: dict, context: Any) -> dict:
    """Lambda handler for MCP tool invocation via AgentCore Gateway."""
    # Resolve BOTH invocation shapes (Gateway client_context-prefixed vs direct
    # {name,arguments}); shared helper in common/types.py, packaged into the zip.
    tool_name, arguments = resolve_invocation(event, context)

    if tool_name == "list_tools":
        return {
            "tools": [
                {"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
                for name, spec in TOOLS.items()
            ]
        }

    if tool_name not in TOOLS:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        started = time.monotonic()
        result = TOOLS[tool_name]["fn"](**arguments)
        if tool_name == "restock_shelf":
            _write_tool_audit(
                tool_name,
                arguments,
                result,
                int((time.monotonic() - started) * 1000),
            )
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}
