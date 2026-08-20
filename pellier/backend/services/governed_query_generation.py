"""
Turn a business question into one candidate SQL statement.

Separate module from `services/governed_query.py` on purpose. That module is
the boundary and must be reviewable without reading a prompt; this one is the
part a model influences, and nothing here is trusted. Generation is a
convenience: if it produces a `DROP TABLE`, the boundary refuses it, and the
receipt records the refusal.

The schema context below is an allowlist, not documentation. A table absent
from it is a table the model has not been told about — which is not a
security control either, since `pellier_query`'s grants and the schema
allowlist in the boundary are what actually decide.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Tables the capability answers questions about, with the columns worth
# naming. Deliberately excludes every evidence table: a question about the
# business is not a question about the audit trail, and `pellier_query` cannot
# read those anyway.
SCHEMA_CONTEXT = """
Schema `pellier` (PostgreSQL). Only these relations exist for you:

product_catalog("productId" text, name text, brand text, color text,
                price numeric, description text, category text, tags jsonb,
                rating numeric, reviews integer, quantity integer, tier integer)
warehouses(id text, display_name text, city text,
           ship_window_min integer, ship_window_max integer)
warehouse_inventory(warehouse_id text, product_id text, quantity smallint)
customers(id text, name text, preferences_summary text)
orders(id bigint, customer_id text, product_id text, quantity integer,
       placed_at timestamptz)
returns(id bigint, customer_id text, product_id text, reason text,
        status text, quantity integer, order_id bigint, requested_at timestamptz)
return_policies(category text, window_days integer, restockable boolean)

Notes:
- "productId" is quoted camelCase text, not an integer. product_id columns in
  other tables are text and join to it.
- orders and returns are row-level-security protected; a query may return no
  rows for reasons unrelated to the data.
""".strip()

_INSTRUCTIONS = """
Write exactly one PostgreSQL SELECT statement that answers the question.

Rules:
- One statement. No semicolon.
- SELECT only. No INSERT, UPDATE, DELETE, DDL, or transaction control.
- Only the relations listed in the schema. Never system catalogs.
- Qualify nothing outside schema `pellier`.
- Aggregate or order as the question requires; a row limit is applied for you.
- Output only SQL. No prose, no markdown fence, no explanation.
""".strip()

# Strips a ```sql fence when a model adds one anyway.
_FENCE = re.compile(r"^\s*```(?:sql)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def strip_fence(text: str) -> str:
    """Return the SQL inside a markdown fence, or the text unchanged."""
    match = _FENCE.match(text or "")
    return match.group(1).strip() if match else (text or "").strip()


def build_prompt(question: str) -> str:
    """Compose the generation prompt for one question."""
    return (
        f"{SCHEMA_CONTEXT}\n\n{_INSTRUCTIONS}\n\n"
        f"Question: {question.strip()}\n\nSQL:"
    )


def generate_sql(question: str) -> Optional[str]:
    """Return one candidate SQL statement, or ``None`` if generation failed.

    Temperature 0 so the same question yields the same statement, which is
    what makes a workshop exercise reproducible. Returns ``None`` rather than
    raising: a generation failure is an outcome the receipt should record, not
    an exception the tool has to translate.
    """
    if not question or not question.strip():
        return None
    try:
        import boto3

        from config import settings
        from services.response_mode import resolve_specialist_model

        model_id, _max_tokens, _tier = resolve_specialist_model("sonnet")
        client = boto3.client(
            "bedrock-runtime", region_name=settings.aws_region_resolved
        )
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": build_prompt(question)}]}],
            inferenceConfig={"maxTokens": 600, "temperature": 0},
        )
        blocks = response["output"]["message"]["content"]
        text = "".join(block.get("text", "") for block in blocks)
        return strip_fence(text) or None
    except Exception as exc:
        logger.warning("governed query generation failed: %s", exc)
        return None
