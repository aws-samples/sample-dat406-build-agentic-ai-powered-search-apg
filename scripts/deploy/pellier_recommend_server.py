"""
Pellier Curation MCP Server - Lambda-hosted read and recommendation tools.

Exposes the five curation and evidence tools from the canonical 15-tool
Pellier contract:
  - preference_snapshot
  - trace_receipt
  - whats_trending
  - returns_and_care
  - style_match

Deployed as a Lambda function behind AgentCore Gateway.
"""
import json
import logging
import os
from typing import Any

import boto3

from common.types import resolve_invocation

logger = logging.getLogger(__name__)

REGION = os.environ.get("REGION", "us-east-1")
DB_REGION = os.environ.get("DB_REGION", REGION)
DB_CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
SECRET_ARN = os.environ.get("SECRET_ARN", "")
DATABASE = os.environ.get("DATABASE", "postgres")
SCHEMA = "pellier"

# Module-level clients for Lambda warm start reuse
rds_client = boto3.client("rds-data", region_name=DB_REGION)
bedrock_client = boto3.client("bedrock-runtime", region_name=REGION)

_PERSONA_CUSTOMER_IDS = {
    "marco": "CUST-MARCO",
    "anna": "CUST-ANNA",
    "theo": "CUST-THEO",
    "fresh": "CUST-FRESH",
}


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


def _decode_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _resolve_customer_id(customer_id: str = "", persona: str = "") -> str:
    explicit = (customer_id or "").strip()
    if explicit:
        return _PERSONA_CUSTOMER_IDS.get(explicit.lower(), explicit.upper())
    return _PERSONA_CUSTOMER_IDS.get((persona or "").strip().lower(), "")


# --- Tool implementations ---

def preference_snapshot(
    customer_id: str = "",
    persona: str = "",
    limit: int = 5,
) -> dict:
    """Return a read-only customer, order, and episodic-memory snapshot."""
    resolved = _resolve_customer_id(customer_id, persona)
    if not resolved:
        return {
            "status": "no_customer_context",
            "message": "No customer_id or persona context was supplied.",
            "read_only": True,
        }

    safe_limit = max(1, min(int(limit or 5), 10))
    customer = _execute_sql(
        f"""
        SELECT id, name, preferences_summary
          FROM {SCHEMA}.customers
         WHERE id = :customer_id;
        """,
        [{"name": "customer_id", "value": {"stringValue": resolved}}],
    )
    if not customer:
        return {"status": "not_found", "customer_id": resolved, "read_only": True}

    parameters = [
        {"name": "customer_id", "value": {"stringValue": resolved}},
        {"name": "limit", "value": {"longValue": safe_limit}},
    ]
    orders = _execute_sql(
        f"""
        SELECT o.product_id, pc.name, pc.brand, pc.category, pc.color,
               pc.price, o.quantity, o.placed_at
          FROM {SCHEMA}.orders o
          JOIN {SCHEMA}.product_catalog pc
            ON pc."productId" = o.product_id
         WHERE o.customer_id = :customer_id
         ORDER BY o.placed_at DESC
         LIMIT :limit;
        """,
        parameters,
    )
    facts = _execute_sql(
        f"""
        SELECT summary_text, ts_offset_days
          FROM {SCHEMA}.customer_episodic_seed
         WHERE customer_id = :customer_id
         ORDER BY ts_offset_days DESC
         LIMIT :limit;
        """,
        parameters,
    )
    return {
        "status": "success",
        "read_only": True,
        "customer": customer[0],
        "recent_orders": orders,
        "memory_facts": [
            {
                "summary": fact.get("summary_text"),
                "ts_offset_days": fact.get("ts_offset_days"),
            }
            for fact in facts
        ],
        "sources": [
            "pellier.customers",
            "pellier.orders",
            "pellier.customer_episodic_seed",
        ],
    }


def trace_receipt(
    session_id: str = "",
    tool_name: str = "",
    caller: str = "",
    limit: int = 3,
) -> dict:
    """Return recent read-only audit receipts for the requested rail."""
    filters = []
    parameters = []
    for field, value in (
        ("session_id", session_id),
        ("tool", tool_name),
        ("caller", caller.lower() if caller else ""),
    ):
        clean = (value or "").strip()
        if clean:
            filters.append(f"{field} = :{field}")
            parameters.append(
                {"name": field, "value": {"stringValue": clean}}
            )
    safe_limit = max(1, min(int(limit or 3), 10))
    parameters.append({"name": "limit", "value": {"longValue": safe_limit}})
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = _execute_sql(
        f"""
        SELECT audit_id, session_id, tool, caller, args, result,
               latency_ms, created_at
          FROM {SCHEMA}.tool_audit
          {where}
         ORDER BY audit_id DESC
         LIMIT :limit;
        """,
        parameters,
    )
    if not rows:
        return {
            "status": "no_allow_receipt",
            "read_only": True,
            "filters": {
                "session_id": (session_id or "").strip() or None,
                "tool_name": (tool_name or "").strip() or None,
                "caller": (caller or "").strip().lower() or None,
            },
            "interpretation": (
                "No pellier.tool_audit ALLOW row matched these filters."
            ),
        }

    receipts = []
    for row in rows:
        result = _decode_json(row.get("result"))
        if isinstance(result, dict):
            status = result.get("status") or result.get("type")
            if status is None and "error" in result:
                status = "error"
            result_summary = {
                "status": status or "recorded",
                "keys": sorted(str(key) for key in result)[:10],
            }
        elif isinstance(result, list):
            result_summary = {"status": "recorded", "items": len(result)}
        else:
            result_summary = {
                "status": "pending" if result is None else "recorded"
            }
        receipts.append(
            {
                "audit_id": row.get("audit_id"),
                "session_id": row.get("session_id"),
                "tool": row.get("tool"),
                "caller": row.get("caller"),
                "decision": "ALLOW",
                "args": _decode_json(row.get("args")),
                "result_summary": result_summary,
                "latency_ms": row.get("latency_ms"),
                "created_at": row.get("created_at"),
            }
        )
    return {
        "status": "success",
        "read_only": True,
        "count": len(receipts),
        "receipts": receipts,
        "source": "pellier.tool_audit",
    }


def whats_trending(limit: int = 5, category: str = None) -> dict:
    """Return products ranked by rating times review volume."""
    conditions = ["rating >= 4.0", "reviews::int > 50", '"imgUrl" IS NOT NULL']
    parameters = [
        {
            "name": "limit",
            "value": {"longValue": max(1, min(int(limit or 5), 20))},
        }
    ]
    if category:
        conditions.append("lower(category) LIKE :category")
        parameters.append(
            {
                "name": "category",
                "value": {"stringValue": f"%{str(category).lower()}%"},
            }
        )
    rows = _execute_sql(
        f"""
        SELECT "productId", name, brand, color, "imgUrl", price, rating,
               reviews, category, badge, tags,
               (reviews::int * rating) AS trending_score
          FROM {SCHEMA}.product_catalog
         WHERE {' AND '.join(conditions)}
         ORDER BY trending_score DESC, rating DESC
         LIMIT :limit;
        """,
        parameters,
    )
    return {
        "status": "success",
        "count": len(rows),
        "products": rows,
        "metadata": {
            "criteria": "reviews * rating, min 4.0 rating, min 50 reviews",
            "limit": max(1, min(int(limit or 5), 20)),
            "category_filter": category,
        },
    }


def returns_and_care(category: str = "default") -> dict:
    """Return the exact category policy, falling back to the default row."""
    parameters = [
        {"name": "category", "value": {"stringValue": category or "default"}}
    ]
    rows = _execute_sql(
        f"""
        SELECT category_name, return_window_days, conditions, refund_method
          FROM {SCHEMA}.return_policies
         WHERE category_name = :category;
        """,
        parameters,
    )
    if not rows and category != "default":
        rows = _execute_sql(
            f"""
            SELECT category_name, return_window_days, conditions, refund_method
              FROM {SCHEMA}.return_policies
             WHERE category_name = 'default';
            """
        )
    if not rows:
        return {"error": f"No return policy found for category: {category}"}
    return rows[0]


def style_match(product_id: int, limit: int = 5) -> dict:
    """Find products nearest to a source product in the catalog vector space."""
    product_id_text = str(product_id).strip()
    source_rows = _execute_sql(
        f"""
        SELECT "productId", name, brand, price, embedding::text AS embedding
          FROM {SCHEMA}.product_catalog
         WHERE "productId" = :product_id;
        """,
        [{"name": "product_id", "value": {"stringValue": product_id_text}}],
    )
    if not source_rows:
        return {"error": f"Product {product_id} not found"}
    source = source_rows[0]
    embedding = source.pop("embedding", None)
    if not embedding:
        return {"error": f"Product {product_id} has no embedding"}

    matches = _execute_sql(
        f"""
        SELECT "productId", name, brand, color, price, rating, reviews,
               category, "imgUrl",
               1 - (embedding <=> CAST(:embedding AS vector)) AS similarity_score
          FROM {SCHEMA}.product_catalog
         WHERE "productId" <> :product_id
           AND embedding IS NOT NULL
         ORDER BY embedding <=> CAST(:embedding AS vector)
         LIMIT :limit;
        """,
        [
            {"name": "embedding", "value": {"stringValue": embedding}},
            {"name": "product_id", "value": {"stringValue": product_id_text}},
            {
                "name": "limit",
                "value": {"longValue": max(1, min(int(limit or 5), 20))},
            },
        ],
    )
    return {"source": source, "matches": matches, "count": len(matches)}


# --- Lambda MCP handler ---

TOOLS = {
    "preference_snapshot": {
        "fn": preference_snapshot,
        "description": "Read a safe customer preference, order, and memory snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "persona": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": [],
        },
    },
    "trace_receipt": {
        "fn": trace_receipt,
        "description": "Read recent ALLOW receipts from pellier.tool_audit.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "tool_name": {"type": "string"},
                "caller": {"type": "string"},
                "limit": {"type": "integer", "default": 3},
            },
            "required": [],
        },
    },
    "whats_trending": {
        "fn": whats_trending,
        "description": "Get products ranked by rating and review volume.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 5},
                "category": {"type": "string", "description": "Filter by category"},
            },
            "required": [],
        },
    },
    "returns_and_care": {
        "fn": returns_and_care,
        "description": "Look up the return and care policy for a category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "default": "default"},
            },
            "required": [],
        },
    },
    "style_match": {
        "fn": style_match,
        "description": "Find complementary products by vector similarity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["product_id"],
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
        result = TOOLS[tool_name]["fn"](**arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}
