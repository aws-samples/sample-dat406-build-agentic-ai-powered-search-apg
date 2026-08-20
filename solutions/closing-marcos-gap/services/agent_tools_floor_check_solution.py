"""
Strands SDK Tools for Agents
Provides @tool decorated functions for agent use with live database access.

Two retrieval entry points:

  - ``find_pieces`` — Marco's foundation. Pure pgvector cosine
    similarity over the product catalog. It is the retrieval teaching surface.

  - ``find_pieces_hybrid`` — Anna's anchor capability. Hybrid
    pgvector + Postgres FTS (tsvector + ts_rank_cd) with RRF merge, then Cohere Rerank v3.5
    on the top 30. This is the hybrid retrieval teaching surface; granted only to
    the Curator agent (curator.py).
"""
from strands import tool
import contextvars
import json
import asyncio
import logging
import re

from config import settings

# Global service references
_db_service = None
_main_loop = None
logger = logging.getLogger(__name__)

def set_db_service(db_service):
    """Set the database service instance"""
    global _db_service
    _db_service = db_service

def set_main_loop(loop):
    """Store reference to the main uvicorn event loop for cross-thread dispatch"""
    global _main_loop
    _main_loop = loop

def _run_async(coro):
    """Run async coroutine from a sync context (e.g. Strands @tool in a background thread).

    Dispatches to the main uvicorn event loop via run_coroutine_threadsafe so that
    the AsyncConnectionPool (bound to the main loop) works correctly. Propagates
    the caller's ContextVars (e.g. ``db_query_log_var``) into the coroutine so
    per-turn telemetry buffers catch tool-initiated DB calls.
    """
    # Capture the current ContextVars (e.g. db_query_log_var) so the
    # coroutine runs with the same context even when dispatched to a
    # different event loop.
    ctx = contextvars.copy_context()

    async def _run_in_ctx():
        # Create a Task in the captured context; this ensures ContextVars
        # set by the caller (like db_query_log_var) are visible inside
        # the coroutine even though we crossed threads.
        return await asyncio.get_running_loop().create_task(coro, context=ctx)

    if _main_loop and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(_run_in_ctx(), _main_loop)
        return future.result(timeout=30)
    # Fallback for standalone / test contexts where no main loop is set.
    # Use get_running_loop() (not the deprecated get_event_loop()): it raises
    # RuntimeError exactly when there is no running loop, which is the case we
    # handle by spinning up a fresh one.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        # A loop is already running on this thread — hand the coroutine to it.
        future = asyncio.run_coroutine_threadsafe(_run_in_ctx(), loop)
        return future.result(timeout=30)
    # No running loop: create a private one, run to completion, and tear down.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


_MILESTONE_HOME_GIFT_PATTERN = re.compile(
    r"\b(milestone|housewarming|new homeowner|homeowner|new home|first home)\b",
    re.IGNORECASE,
)


def _extract_query_structure(query: str) -> dict | None:
    """Ask the structured extractor for a proposed plan, or return None.

    Gated behind ``SEARCH_PLANNER_EXTRACT_ENABLED`` (default off) because
    it is a second live Bedrock call on the shopper's critical path: it
    adds roughly 1-3 s and a Sonnet invocation to *every* search. The
    Observatory comparison surface runs the extractor unconditionally, which
    is where the workshop teaches what typed planning buys you; paying
    that cost on each storefront turn is a product decision, not a
    correctness one.

    Turning the flag off does not weaken any hard constraint. The tool
    still builds a plan from the caller's explicit arguments and still
    compiles those predicates into both retrieval branches before RRF —
    what the extractor adds is model-inferred constraints (an implied
    price ceiling, an implied exclusion) on top of the explicit ones.

    Args:
        query: The shopper's raw query.

    Returns:
        The extractor's dict, or ``None`` when the flag is off or
        extraction fails.
    """
    if not getattr(settings, "SEARCH_PLANNER_EXTRACT_ENABLED", False):
        return None
    try:
        from services.structured_extract import get_structured_extractor

        return get_structured_extractor().extract(query)
    except Exception as exc:
        logger.debug("structured extraction unavailable: %s", exc)
        return None


def _write_retrieval_receipt(**kwargs) -> None:
    """Persist a retrieval receipt, swallowing any failure.

    Evidence about a turn must never break the turn, so this is
    fire-and-forget. A lost receipt is a gap in evidence; a raised
    exception here would be a gap in the product.
    """
    if _db_service is None:
        return
    try:
        from services.retrieval_receipt import (
            build_receipt,
            current_turn_context,
            persist_receipt,
        )

        context = current_turn_context()
        for field in ("turn_id", "session_id", "principal_sub", "rail"):
            if field not in kwargs and context.get(field) is not None:
                kwargs[field] = context[field]
        receipt = build_receipt(**kwargs)
        _run_async(persist_receipt(_db_service, receipt))
    except Exception as exc:
        logger.debug("retrieval receipt write skipped: %s", exc)


# Merchandising rules are versioned and disclosed, never hidden. Relevance
# is rarely the only ranking signal in production commerce search — a
# buyer-curated hero, a margin boost, or a seasonal push all reorder
# results legitimately. What makes such a rule safe is that it is a
# declared ranking feature that shows up in the response (and so in
# relevance evaluation), not an invisible reorder that quietly contaminates
# every comparison. This one is Anna's housewarming hero.
MERCHANDISING_RULE_ID = "merch.milestone-home-gift.v1"


def _apply_merchandising_rules(
    query: str, products: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Apply declared merchandising rules and report which ones fired.

    A rule may only reorder candidates that retrieval already surfaced —
    it never injects a product the query did not retrieve, and it never
    overrides a hard constraint, because it runs after valid-candidate
    generation.

    Args:
        query: The shopper's raw query, matched against each rule's trigger.
        products: Candidates in reranked order.

    Returns:
        ``(ordered, rules_applied)`` where each entry in ``rules_applied``
        records the rule id, the promoted product, and its rank movement,
        so the response and the retrieval receipt can disclose the boost.
    """
    if not _MILESTONE_HOME_GIFT_PATTERN.search(query or ""):
        return products, []

    for idx, product in enumerate(products):
        if product.get("name") != "Olive Branch Vessel":
            continue
        if idx == 0:
            # Already the winner on relevance alone; nothing was boosted.
            return products, []
        promoted = [product, *products[:idx], *products[idx + 1:]]
        return promoted, [
            {
                "ruleId": MERCHANDISING_RULE_ID,
                "signal": "curated_hero",
                "product": product.get("name"),
                "fromRank": idx + 1,
                "toRank": 1,
                "reason": (
                    "Declared merchandising rule: curated housewarming hero "
                    "promoted above pure relevance order."
                ),
            }
        ]
    return products, []


_PERSONA_CUSTOMER_IDS = {
    "marco": "CUST-MARCO",
    "anna": "CUST-ANNA",
    "theo": "CUST-THEO",
    "fresh": "CUST-FRESH",
}


def _json_default(value):
    """JSON fallback for timestamps, decimals, and driver-native values."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__float__"):
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return str(value)


def _managed_rail_required(tool_name: str) -> str | None:
    """Reject local mutations in the governed workshop format.

    Delegates the decision to ``services.execution_rail`` so the set of
    mutation-capable tools lives in exactly one place. When that set and
    this guard drift, a governed write silently becomes servable
    in-process — the failure mode this guard exists to prevent.

    Returns a JSON error envelope when the tool may not run on this rail,
    or ``None`` when it may.
    """
    from services.execution_rail import RAIL_GATEWAY_MCP, requires_managed_rail

    if not requires_managed_rail(tool_name):
        return None
    return json.dumps(
        {
            "error": "managed_rail_required",
            "tool": tool_name,
            "required_rail": RAIL_GATEWAY_MCP,
        }
    )


def _infer_customer_id(customer_id: str = "", persona: str = "") -> str:
    """Resolve a customer id from explicit args or the active persona preamble."""
    raw_customer = (customer_id or "").strip()
    if raw_customer:
        if raw_customer.upper().startswith("CUST-"):
            return raw_customer.upper()
        mapped = _PERSONA_CUSTOMER_IDS.get(raw_customer.lower())
        if mapped:
            return mapped
        return raw_customer

    raw_persona = (persona or "").strip().lower()
    if raw_persona in _PERSONA_CUSTOMER_IDS:
        return _PERSONA_CUSTOMER_IDS[raw_persona]

    try:
        from services.persona_context import get_persona_preamble

        preamble = get_persona_preamble()
    except Exception:
        preamble = ""

    match = re.search(r"\bCUST-[A-Z0-9_-]+\b", preamble)
    if match:
        return match.group(0)

    preamble_lower = preamble.lower()
    for persona_id, mapped in _PERSONA_CUSTOMER_IDS.items():
        if re.search(rf"\b{re.escape(persona_id)}\b", preamble_lower):
            return mapped
    return ""


@tool
def preference_snapshot(customer_id: str = "", persona: str = "", limit: int = 5) -> str:
    """Read a safe shopper preference snapshot from Aurora memory tables.

    Use when the shopper asks what Pellier remembers, why a recommendation
    reflects their taste, or which prior orders informed the turn. This is
    read-only: it reads pellier.customers, pellier.orders, and
    pellier.customer_episodic_seed, then returns a compact receipt of the
    profile summary, recent order anchors, and memory facts.

    Args:
        customer_id: Optional explicit customer id such as CUST-MARCO.
            If omitted, the tool infers it from persona or the active
            persona preamble.
        persona: Optional persona alias: marco, anna, theo, or fresh.
        limit: Maximum number of order and memory rows to return.
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        resolved_customer = _infer_customer_id(customer_id, persona)
        if not resolved_customer:
            return json.dumps({
                "status": "no_customer_context",
                "message": (
                    "No customer_id or persona context was available for "
                    "a preference snapshot."
                ),
                "read_only": True,
            })

        safe_limit = max(1, min(int(limit or 5), 10))

        customer = _run_async(_db_service.fetch_one(
            """
            SELECT id, name, preferences_summary
              FROM pellier.customers
             WHERE id = %s
            """,
            resolved_customer,
        ))
        orders = _run_async(_db_service.fetch_all(
            """
            SELECT o.product_id,
                   pc.name,
                   pc.brand,
                   pc.category,
                   pc.color,
                   pc.price,
                   o.quantity,
                   o.placed_at
              FROM pellier.orders o
              JOIN pellier.product_catalog pc
                ON pc."productId" = o.product_id
             WHERE o.customer_id = %s
             ORDER BY o.placed_at DESC
             LIMIT %s
            """,
            resolved_customer,
            safe_limit,
        ))
        facts = _run_async(_db_service.fetch_all(
            """
            SELECT summary_text, ts_offset_days
              FROM pellier.customer_episodic_seed
             WHERE customer_id = %s
             ORDER BY ts_offset_days DESC
             LIMIT %s
            """,
            resolved_customer,
            safe_limit,
        ))

        if not customer:
            return json.dumps({
                "status": "not_found",
                "customer_id": resolved_customer,
                "read_only": True,
            })

        payload = {
            "status": "success",
            "read_only": True,
            "customer": {
                "id": customer.get("id"),
                "name": customer.get("name"),
                "preferences_summary": customer.get("preferences_summary"),
            },
            "recent_orders": [
                {
                    "product_id": row.get("product_id"),
                    "name": row.get("name"),
                    "brand": row.get("brand"),
                    "category": row.get("category"),
                    "color": row.get("color"),
                    "price": row.get("price"),
                    "quantity": row.get("quantity"),
                    "placed_at": row.get("placed_at"),
                }
                for row in orders
            ],
            "memory_facts": [
                {
                    "summary": row.get("summary_text"),
                    "ts_offset_days": row.get("ts_offset_days"),
                }
                for row in facts
            ],
            "sources": [
                "pellier.customers",
                "pellier.orders",
                "pellier.customer_episodic_seed",
            ],
        }
        return json.dumps(payload, indent=2, default=_json_default)
    except Exception as e:
        logger.error("preference_snapshot error: %s", e)
        return json.dumps({"error": str(e)})


def _result_summary(result):
    """Small, stable summary of a JSONB tool result for receipt displays."""
    if isinstance(result, dict):
        status = result.get("status") or result.get("type")
        if status is None and "error" in result:
            status = "error"
        return {
            "status": status or "recorded",
            "keys": sorted(str(k) for k in result.keys())[:10],
        }
    if isinstance(result, list):
        return {"status": "recorded", "items": len(result)}
    if result is None:
        return {"status": "pending", "keys": []}
    return {"status": "recorded", "type": type(result).__name__}


@tool
def trace_receipt(
    session_id: str = "",
    tool_name: str = "",
    caller: str = "",
    limit: int = 3,
) -> str:
    """Read recent tool_audit and governed receipts for a session, tool, or caller rail.

    Use when the shopper or operator asks how Pellier knows, what tool ran,
    whether a Gateway call produced an ALLOW receipt, or how to compare the
    in-process ``caller='agent'`` rail with the managed ``caller='gateway'``
    rail. This is read-only: it reads pellier.tool_audit as the execution
    ledger and, when present, pellier.governed_receipts as the identity /
    Cedar decision receipt. No matching tool_audit row means no ALLOW
    execution receipt was written; for governed Gateway demonstrations that is
    the expected shape of a DENY or missing invocation.

    Args:
        session_id: Optional exact session id to inspect.
        tool_name: Optional tool name such as floor_check or process_return.
        caller: Optional caller rail: agent or gateway.
        limit: Maximum receipts to return.
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        safe_limit = max(1, min(int(limit or 3), 10))
        filters = []
        params = []

        clean_session = (session_id or "").strip()
        clean_tool = (tool_name or "").strip()
        clean_caller = (caller or "").strip().lower()

        if clean_session:
            filters.append("session_id = %s")
            params.append(clean_session)
        if clean_tool:
            filters.append("tool = %s")
            params.append(clean_tool)
        if clean_caller:
            filters.append("caller = %s")
            params.append(clean_caller)

        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = _run_async(_db_service.fetch_all(
            f"""
            SELECT audit_id,
                   session_id,
                   tool,
                   caller,
                   args,
                   result,
                   latency_ms,
                   created_at
              FROM pellier.tool_audit
              {where}
             ORDER BY audit_id DESC
             LIMIT %s
            """,
            *params,
            safe_limit,
        ))

        receipts = [
            {
                "audit_id": row.get("audit_id"),
                "session_id": row.get("session_id"),
                "tool": row.get("tool"),
                "caller": row.get("caller"),
                "decision": "ALLOW",
                "args": row.get("args"),
                "result_summary": _result_summary(row.get("result")),
                "latency_ms": row.get("latency_ms"),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

        governed_receipts = []
        try:
            governed_rows = _run_async(_db_service.fetch_all(
                f"""
                SELECT receipt_id,
                       audit_id,
                       session_id,
                       principal_id,
                       principal_label,
                       tool,
                       caller,
                       decision,
                       args,
                       policy_name,
                       token_fingerprint_sha256,
                       verified_subject,
                       verified_username,
                       issuer,
                       client_id,
                       identity_source,
                       created_at
                  FROM pellier.governed_receipts
                  {where}
                 ORDER BY receipt_id DESC
                 LIMIT %s
                """,
                *params,
                safe_limit,
            ))
            governed_receipts = [
                {
                    "receipt_id": row.get("receipt_id"),
                    "audit_id": row.get("audit_id"),
                    "session_id": row.get("session_id"),
                    "principal_id": row.get("principal_id"),
                    "principal_label": row.get("principal_label"),
                    "tool": row.get("tool"),
                    "caller": row.get("caller"),
                    "decision": row.get("decision"),
                    "args": row.get("args"),
                    "policy_name": row.get("policy_name"),
                    "token_fingerprint_sha256": row.get("token_fingerprint_sha256"),
                    "verified_subject": row.get("verified_subject"),
                    "verified_username": row.get("verified_username"),
                    "issuer": row.get("issuer"),
                    "client_id": row.get("client_id"),
                    "identity_source": row.get("identity_source"),
                    "created_at": row.get("created_at"),
                }
                for row in governed_rows
            ]
        except Exception:
            governed_receipts = []

        if not receipts and not governed_receipts:
            return json.dumps({
                "status": "no_allow_receipt",
                "read_only": True,
                "filters": {
                    "session_id": clean_session or None,
                    "tool_name": clean_tool or None,
                    "caller": clean_caller or None,
                },
                "interpretation": (
                    "No pellier.tool_audit ALLOW row matched these filters. "
                    "For governed Gateway checks, a no-row result is the "
                    "observable DENY/missing-invocation boundary."
                ),
            }, indent=2)

        return json.dumps({
            "status": "success",
            "read_only": True,
            "count": len(receipts),
            "receipts": receipts,
            "governed_receipts": governed_receipts,
            "sources": ["pellier.tool_audit", "pellier.governed_receipts"],
        }, indent=2, default=_json_default)
    except Exception as e:
        logger.error("trace_receipt error: %s", e)
        return json.dumps({"error": str(e)})


@tool
def floor_check(product_query: str = "") -> str:
    """Inventory check across the catalog and three warehouses (BK-01 Brooklyn, ATX-02 Austin, PDX-01 Portland).

    PASS product_query whenever the customer mentions a specific product
    by name — e.g. "Hadley shirt", "Hadley shirt (Pellier Linen Shirt in ecru)",
    "Wabi-Sabi Bowl", "linen overshirt".
    The tool fuzzy-matches the name and returns per-warehouse stock
    counts plus ship windows. Examples:

      floor_check(product_query="Hadley shirt")
        → {status: success, product: {...}, warehouses: [{warehouse_id: BK-01, quantity: 8, ship_window_min: 1, ...}, ...]}

    Call WITHOUT arguments only when the customer asks for an overall
    inventory overview — "what's running low", "stock summary",
    "warehouse health". That returns aggregate stats across the catalog.

    Args:
        product_query: Product name (or partial name) to check stock
            for. Empty string falls back to the aggregate summary mode.
    """
    # === WORKSHOP · Stock Keeper · floor_check: START ===
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        from services.business_logic import BusinessLogic

        logic = BusinessLogic(_db_service)
        query = (product_query or "").strip() or None
        result = _run_async(logic.floor_check(product_query=query))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
    # === WORKSHOP · Stock Keeper · floor_check: END ===

@tool
def whats_trending(limit: int = 5, category: str = None) -> str:
    """Get the most popular and trending products, optionally filtered by category. Use when customers ask about bestsellers, what's hot, or popular items.

    Args:
        limit: Maximum number of products to return (default: 5)
        category: Optional category filter (e.g. "Home Decor", "Apparel")

    Returns:
        JSON string with trending products

    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(_db_service)
        result = _run_async(logic.whats_trending(limit, category))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def price_intelligence(category: str = None) -> str:
    """Get pricing statistics and price distribution analysis for a product category. Use for price comparisons, budget analysis, or average price questions."""
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    
    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(_db_service)
        result = _run_async(logic.price_intelligence(category))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def restock_shelf(
    product_id: int,
    quantity: int,
    idempotency_key: str,
    warehouse_id: str = "BK-01",
) -> str:
    """Restock a specific product by adding inventory quantity. Use when an inventory manager needs to replenish stock for a product ID.

    Args:
        product_id: Integer productId. Workshop inventory exercises use curated IDs 1-40.
        quantity: Units to add to current stock.
        idempotency_key: Stable unique key for this intended write.
        warehouse_id: Warehouse receiving stock; defaults to BK-01.

    """
    governed_error = _managed_rail_required("restock_shelf")
    if governed_error:
        return governed_error
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(_db_service)
        result = _run_async(logic.restock_shelf(
            product_id,
            quantity,
            idempotency_key,
            warehouse_id,
        ))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def process_return(
    customer_id: str,
    product_id: int,
    reason: str,
    idempotency_key: str,
) -> str:
    """Process a customer return. Theo's Experience Guide uses this.

    Two enforcement layers:
      - On the managed Gateway rail, AgentCore Policy can gate the call
        before the Lambda-backed tool target runs. In this workshop that
        managed rail permits the damaged-return path; the in-process
        storefront rail reaches this function directly.
      - SQL gates ownership inside the transaction. The customer must
        have an order row for this product. Cedar can't enforce
        ownership because it requires a JOIN against live data.

    If reason='damaged', the call also decrements
    pellier.product_catalog.quantity by 1 (defloored at 0). All
    three operations — ownership check, INSERT, conditional UPDATE —
    run in a single transaction.

    Args:
        customer_id: Salesforce-style customer ID (must exist in customers
            and must have an order for this product_id).
        product_id: INTEGER productId. Workshop return exercises use ordered curated IDs.
        reason: One of 'damaged', 'wrong_size', 'not_as_described',
            'changed_mind', 'other'. The tool validates this canonical set;
            the managed Gateway policy can narrow which calls execute.
        idempotency_key: Stable unique key for this intended return.
    """
    governed_error = _managed_rail_required("process_return")
    if governed_error:
        return governed_error
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    try:
        from services.business_logic import BusinessLogic
        from services.turn_identity import current_principal_sub

        logic = BusinessLogic(_db_service)
        # A verified principal puts the write on the governed rail: a
        # non-owner role with the principal bound, so Row-Level Security
        # decides which customer's rows may change. Anonymous and
        # simulated-persona turns keep the owner rail, where the only gate is
        # the customer_id argument the caller supplied.
        result = _run_async(logic.process_return(
            customer_id,
            product_id,
            reason,
            idempotency_key,
            principal_sub=current_principal_sub(),
        ))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# === GOVERNED NATURAL-LANGUAGE DATA ACCESS — query_business_records =========
#
# Named for the business question it answers, not for the substrate. The same
# PostgreSQL primitives apply on Amazon RDS for PostgreSQL, so the identifier
# must not encode Aurora; the docstring names the implementation.
#
# The model writes SQL, and `services/governed_query.py` decides whether that
# SQL may run: `pellier_query` (no write grants, no evidence-ledger access), a
# READ ONLY transaction, a statement timeout, a fixed search_path, a schema
# allowlist, an implementation-owned row cap, and Row-Level Security bound to
# the same principal a curated tool would use. Prompt constraints improve the
# generated SQL; they are not the boundary.
#
# Every attempt writes a receipt to `pellier.governed_query_receipts`,
# including refusals — a refusal that leaves no artifact cannot be inspected.


@tool
def query_business_records(question: str) -> str:
    """Answer a question about business records by generating and running read-only SQL.

    Use for questions the curated tools do not cover: aggregate counts,
    comparisons across orders and returns, or ad-hoc reporting on the catalog.
    Do NOT use it for a question another tool already answers precisely.

    The generated statement runs against Aurora PostgreSQL under a read-only
    role inside a read-only transaction, scoped by Row-Level Security to the
    verified principal for this turn, and capped to a fixed number of rows.
    A rejected statement returns the reason rather than an answer.

    Args:
        question: A business question in plain language.

    Returns:
        JSON with the answer rows and the governance evidence for the query.
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    try:
        from services.governed_query import run_governed_query
        from services.governed_query_generation import generate_sql
        from services.turn_identity import (
            current_principal_sub,
            current_turn_id,
        )

        sql = generate_sql(question)
        if not sql:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Could not turn that question into a query.",
                },
                indent=2,
            )

        result = _run_async(
            run_governed_query(
                _db_service,
                sql,
                turn_id=current_turn_id(),
                principal_sub=current_principal_sub(),
                caller="agent",
            )
        )
        payload = {
            "status": "success" if result.accepted else "rejected",
            "question": question,
            "rows": result.rows,
            "evidence": result.evidence(),
        }
        if not result.accepted:
            payload["message"] = (
                "The generated query was refused before it ran: "
                f"{result.rejection_reason}"
            )
        return json.dumps(payload, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
# === ESCAPE HATCH — escalate_to_stylist =====================================
#
# Honest "when the agent shouldn't try to answer" tool. The agent calls
# this when the ask is outside what it can reasonably handle: nuanced
# personal advice (wedding-guest dressing for an unfamiliar culture,
# body-image or pregnancy questions), out-of-policy returns the
# Experience Guide can't process, or catalog misses where the shopper
# deserves a real person rather than another search.
#
# The "stylist" is a placeholder for whatever human escalation channel
# a production deployment would wire in (live chat, email queue, CX
# ticket). The tool emits a structured handoff payload that the chat
# surface renders as a contact card — pure UI, no real human on the
# other end for the workshop. The workshop teaches this as the
# escape hatch every agent needs but most demos skip.
@tool
def escalate_to_stylist(reason: str, customer_id: str = "") -> str:
    """Hand the conversation off to a human stylist when the agent shouldn't try to answer.

    Use this tool when:
      - The shopper asks for advice the agent cannot honestly give
        (cultural dressing norms it doesn't know, body-image or
        pregnancy fit, personal style coaching beyond the catalog).
      - The shopper escalates a return the policy won't cover
        (damaged-in-transit past the window, special-order pieces,
        sentimental exceptions Experience Guide can't process).
      - The catalog cannot match the ask and the shopper deserves a
        real person rather than another search.

    Do NOT use this tool when a different tool can answer (search the
    catalog first; check policy first). Calling escalate_to_stylist
    is an honest fallback, not a way to skip the work.

    Args:
        reason: One short sentence describing why the agent is
            escalating. Surfaced in the handoff card so the customer
            knows what's being routed.
        customer_id: Optional Salesforce-style customer id so the
            stylist queue can pre-load the shopper's order history.

    Returns:
        JSON payload with ``type="escalation"`` so the chat surface
        renders the stylist handoff card. No products, no audit row —
        this is a UI handoff, not a database write.
    """
    return json.dumps({
        "type": "escalation",
        "channel": "stylist",
        "status": "handed_off",
        "reason": (reason or "").strip()
        or "The agent thought a human stylist was the right next step.",
        "customer_id": (customer_id or "").strip() or None,
        "contact": {
            "label": "Talk to a stylist",
            "mailto": "stylist@pellier.example",
            "response_window": "Within 1 business day",
        },
        "next_steps": [
            "A Pellier stylist receives your note with full context.",
            "They reply within one business day.",
            "You can keep browsing — we'll pick up where you left off.",
        ],
    })


_CATEGORY_MAP = {
    # Pellier catalog categories (92 products, 9 categories)
    'linen': 'Linen', 'camp shirt': 'Linen', 'oxford': 'Linen',
    'dress': 'Dresses', 'gown': 'Dresses', 'sundress': 'Dresses', 'maxi': 'Dresses',
    'slip dress': 'Dresses', 'kaftan': 'Dresses', 'shirtdress': 'Dresses',
    'outerwear': 'Outerwear', 'jacket': 'Outerwear', 'cardigan': 'Outerwear',
    'vest': 'Outerwear', 'sweater': 'Outerwear', 'blazer': 'Outerwear',
    'trench': 'Outerwear', 'anorak': 'Outerwear', 'puffer': 'Outerwear',
    'shoe': 'Footwear', 'sneaker': 'Footwear', 'sandal': 'Footwear',
    'boot': 'Footwear', 'loafer': 'Footwear', 'runner': 'Footwear',
    'espadrille': 'Footwear', 'mule': 'Footwear', 'derby': 'Footwear',
    'footwear': 'Footwear', 'trail runner': 'Footwear',
    'accessory': 'Accessories', 'accessories': 'Accessories', 'hat': 'Accessories',
    'bracelet': 'Accessories', 'cuff': 'Accessories', 'earring': 'Accessories',
    'scarf': 'Accessories', 'pocket square': 'Accessories',
    'bag': 'Bags', 'tote': 'Bags', 'backpack': 'Bags', 'crossbody': 'Bags',
    'clutch': 'Bags', 'duffle': 'Bags', 'weekender': 'Bags', 'pouch': 'Bags',
    'handbag': 'Bags', 'purse': 'Bags',
    'home': 'Home', 'candle': 'Home', 'throw': 'Home', 'blanket': 'Home',
    'towel': 'Home', 'rug': 'Home', 'vase': 'Home', 'pillow': 'Home',
    'incense': 'Home', 'tumbler': 'Home', 'napkin': 'Home', 'duvet': 'Home',
    'pitcher': 'Home',
    'top': 'Tops', 'tee': 'Tops', 'blouse': 'Tops', 'camisole': 'Tops',
    'henley': 'Tops', 'polo': 'Tops', 'tank': 'Tops', 'shell': 'Tops',
    'button-down': 'Tops',
    'bottom': 'Bottoms', 'bottoms': 'Bottoms', 'trouser': 'Bottoms',
    'pant': 'Bottoms', 'skirt': 'Bottoms', 'denim': 'Bottoms',
    'palazzo': 'Bottoms', 'chino': 'Bottoms', 'corduroy': 'Bottoms',
}

def _detect_category(query: str) -> str | None:
    """Auto-detect product category from query keywords.
    
    Uses word-boundary matching so "what" doesn't match "hat".
    Prefers longer (more specific) keyword matches so "linen shirt"
    maps to Linen, not Tops. Handles common plural forms (s, es).
    """
    query_lower = query.lower()
    for keyword, cat_name in sorted(_CATEGORY_MAP.items(), key=lambda x: -len(x[0])):
        # Match keyword with optional trailing s/es for plurals
        pattern = r'(?<![a-z])' + re.escape(keyword) + r'(?:e?s)?(?![a-z])'
        if re.search(pattern, query_lower):
            return cat_name
    return None

@tool
def find_pieces(
    query: str,
    max_price: float = None,
    min_rating: float = 0.0,
    category: str = None,
    limit: int = 5
) -> str:
    """Search for products by natural language query with optional price and rating filters. Use for descriptive or intent-based product searches.

    Args:
        query: Natural language search query
        max_price: Maximum price filter (optional)
        min_rating: Minimum star rating (default: 0.0)
        category: Category filter (optional — auto-detected from query if not set)
        limit: Number of results (default: 5)
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        from services.vector_search import VectorSearch
        from services.embeddings import EmbeddingService

        # Track whether the category was explicitly passed by the
        # agent vs. auto-detected from a keyword map. Auto-detected
        # categories (e.g. "linen" → "Linen") are speculative — the
        # Pellier catalog uses higher-level taxonomy ("Apparel",
        # "Home Decor", "Accessories"), so a strict substring filter
        # on an auto-detected category drops every vector-search hit.
        # The query embedding already encodes the user's intent; we
        # use the detected category only for pool sizing, not as a
        # hard post-filter.
        category_was_explicit = bool(category)
        if not category:
            category = _detect_category(query)

        embedding_service = EmbeddingService()
        query_embedding = embedding_service.embed_query(query)

        vector = VectorSearch(_db_service)

        # Concierge uses pure pgvector semantic search — the baseline retrieval
        # teaching surface. The hybrid + rerank pipeline was removed
        # when the concierge switched to semantic-only retrieval.
        pool_size = 30 if category else 20
        rows = _run_async(
            vector.vector_search(query_embedding, pool_size, ef_search=40)
        )
        result = {"results": rows, "method": "semantic"}

        # Normalize field names and apply filters.
        products = result.get("results", [])
        normalized = []
        for p in products:
            reviews_raw = p.get("reviews")
            try:
                reviews_int = int(reviews_raw) if reviews_raw is not None else 0
            except (TypeError, ValueError):
                reviews_int = 0
            product = {
                "productId": p.get("product_id"),
                "name": p.get("name", ""),
                "brand": p.get("brand", ""),
                "color": p.get("color", ""),
                "description": p.get("description", ""),
                "price": float(p["price"]) if hasattr(p.get("price"), '__float__') else p.get("price", 0),
                "rating": float(p["rating"]) if hasattr(p.get("rating"), '__float__') else p.get("rating", 0),
                "reviews": reviews_int,
                "category": p.get("category", ""),
                "imgUrl": p.get("img_url", ""),
                "badge": p.get("badge"),
                "tags": list(p.get("tags") or []),
            }
            if max_price and product["price"] > max_price:
                continue
            if min_rating and product["rating"] < min_rating:
                continue
            # Only apply category as a hard filter when the agent
            # explicitly passed one. Auto-detected categories filter
            # too aggressively against the catalog's higher-level
            # category taxonomy.
            if (
                category_was_explicit
                and category
                and category.lower() not in product["category"].lower()
            ):
                continue
            normalized.append(product)

        # Trim to requested limit after filtering
        normalized = normalized[:limit]

        return json.dumps({
            "status": "success",
            "query": query,
            "count": len(normalized),
            "products": normalized,
            "search_method": result.get("method", "hybrid"),
            "category_detected": category,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def find_pieces_hybrid(
    query: str,
    max_price: float = None,
    min_rating: float = 0.0,
    category: str = None,
    limit: int = 5,
) -> str:
    """Hybrid pgvector + Postgres FTS + Cohere Rerank v3.5. Anna's Curator uses this.

    Three-stage retrieval:
      1. Vector branch (pgvector cosine) and FTS branch (tsvector
         ts_rank_cd) run in parallel against pellier.product_catalog.
      2. Reciprocal Rank Fusion merges the two ranked lists into a
         single candidate pool of ~30 products.
      3. Cohere Rerank v3.5 reorders the pool by relevance to the
         original query and returns the top ``limit``.

    Each stage adds a different kind of signal:
      - Vector catches *meaning*: "something beautiful" → editorial pieces
      - Postgres FTS catches *literals*: "candle" → only candle-shaped products
      - Rerank catches *coherence*: "for a slow Sunday morning" → the
        ceramic mug pulls ahead of the lounge set when the candidate
        pool included both

    Args:
        query: Natural language search query
        max_price: Maximum price filter (optional, applied post-rerank)
        min_rating: Minimum star rating (default: 0.0, applied post-rerank)
        category: Category filter (optional — only applied as a hard
            filter when the agent passes it explicitly, mirroring
            find_pieces' behavior)
        limit: Number of final results (default: 5)
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        from services.embeddings import EmbeddingService
        from services.hybrid_search import HybridSearch
        from services.rerank import get_rerank_service
        from services.search_plan import build_plan

        # Same explicit-vs-auto category guard as find_pieces. Anna's
        # auto-detected categories ("linen" → "Linen") still don't match
        # the catalog's higher-level taxonomy ("Apparel"); only filter
        # when the agent supplies an explicit category.
        category_was_explicit = bool(category)

        # PLAN. The model proposes a typed plan; deterministic code
        # validates it and compiles the predicates. This is the same
        # planner the Observatory comparison surface runs, so the "agentic"
        # strategy the workshop demonstrates is the one shoppers get —
        # not a parallel implementation that only exists in a demo.
        #
        # The plan is also what makes price and category *hard*: its
        # predicates go into both retrieval branches before RRF, so
        # invalid candidates never enter the pool, never consume reranker
        # capacity, and never make the final list unexpectedly short after
        # a post-filter pass.
        extracted = _extract_query_structure(query)
        plan = build_plan(
            query,
            extracted,
            price_max_usd=max_price,
            category=category if category_was_explicit else None,
            top_k=limit,
        )
        hard_clauses, hard_params = plan.compile_predicates()

        embedding_service = EmbeddingService()
        query_embedding = embedding_service.embed_query(query)

        hybrid = HybridSearch(_db_service)
        # Pool size 30 — enough material for the reranker to reorder
        # meaningfully; Cohere bills per call, not per candidate.
        candidates = _run_async(
            hybrid.search(
                query=query,
                query_embedding=query_embedding,
                k_vector=settings.HYBRID_VECTOR_K,
                k_fts=settings.HYBRID_FTS_K,
                top_n=settings.HYBRID_TOP_N,
                hard_clauses=hard_clauses,
                hard_params=hard_params,
            )
        )

        # Build the per-document text the reranker reads. Three fields
        # in priority order: name (carries brand identity), description
        # (carries style + use case), category (coarse semantic anchor).
        # Truncate descriptions at 240 chars to stay well below Cohere's
        # per-document token limit.
        def _doc_for_rerank(p: dict) -> str:
            name = (p.get("name") or "").strip()
            desc = (p.get("description") or "").strip()
            cat = (p.get("category") or "").strip()
            if len(desc) > 240:
                desc = desc[:237] + "…"
            return f"{name} — {desc} ({cat})"

        documents = [_doc_for_rerank(p) for p in candidates]
        rerank_service = get_rerank_service()
        rerank_results = rerank_service.rerank(
            query=query,
            documents=documents,
            top_n=min(limit * 3, settings.RERANK_MAX_DOCUMENTS),  # over-rerank then filter
        )

        # Project candidates by reranked indices. If rerank failed
        # (returned []), fall back to RRF order — the Observatory will show
        # this as a missing rerank stage in telemetry.
        if rerank_results:
            ordered = [
                {**candidates[r["index"]],
                 "rerank_score": float(r["relevance_score"])}
                for r in rerank_results
            ]
            search_method = "hybrid+rerank"
        else:
            ordered = [{**c, "rerank_score": None} for c in candidates]
            search_method = "hybrid (rerank fallback to RRF order)"

        ordered, merchandising_applied = _apply_merchandising_rules(query, ordered)

        # Normalize field shapes to match find_pieces output.
        normalized = []
        for p in ordered:
            reviews_raw = p.get("reviews")
            try:
                reviews_int = int(reviews_raw) if reviews_raw is not None else 0
            except (TypeError, ValueError):
                reviews_int = 0
            product = {
                "productId": p.get("product_id"),
                "name": p.get("name", ""),
                "brand": p.get("brand", ""),
                "color": p.get("color", ""),
                "description": p.get("description", ""),
                "price": float(p["price"]) if hasattr(p.get("price"), '__float__') else p.get("price", 0),
                "rating": float(p["rating"]) if hasattr(p.get("rating"), '__float__') else p.get("rating", 0),
                "reviews": reviews_int,
                "category": p.get("category", ""),
                "imgUrl": p.get("img_url", ""),
                "badge": p.get("badge"),
                "tags": list(p.get("tags") or []),
                "rrf_score": p.get("rrf_score"),
                "rerank_score": p.get("rerank_score"),
            }
            # Hard price/category predicates already ran in SQL, before
            # RRF. These checks are a defence-in-depth assertion, not the
            # enforcement point. min_rating is genuinely post-hoc: it is a
            # preference the caller applies to the reranked list.
            if max_price and product["price"] > max_price:
                continue
            if min_rating and product["rating"] < min_rating:
                continue
            if (
                category_was_explicit
                and category
                and category.lower() not in product["category"].lower()
            ):
                continue
            normalized.append(product)

        normalized = normalized[:limit]

        payload = {
            "status": "success",
            "query": query,
            "count": len(normalized),
            "products": normalized,
            "search_method": search_method,
            "pool_size": len(candidates),
            "hard_constraints_enforced": plan.hard.describe(),
            "constraints_applied_before_rerank": True,
            "search_plan": plan.to_dict(),
        }
        if merchandising_applied:
            # Disclosed, not hidden: a ranking signal other than relevance
            # moved a product, and the response says so.
            payload["merchandising_rules_applied"] = merchandising_applied

        # PROVE. Persist why this result set appeared: the plan, the
        # per-branch ranks, the rerank scores, and any declared
        # merchandising rule. Best-effort — see _write_retrieval_receipt.
        _write_retrieval_receipt(
            query=query,
            plan=plan,
            candidates=candidates,
            ordered=ordered,
            merchandising_rules=merchandising_applied,
            embedding_model=settings.BEDROCK_EMBEDDING_MODEL,
            rerank_model=settings.BEDROCK_RERANK_MODEL,
            retrieval_config={
                "k_vector": settings.HYBRID_VECTOR_K,
                "k_fts": settings.HYBRID_FTS_K,
                "rrf_k": settings.HYBRID_RRF_K,
                "top_n": settings.HYBRID_TOP_N,
                "search_method": search_method,
            },
        )
        return json.dumps(payload, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def explore_collection(
    category: str,
    min_rating: float = 0.0,
    max_price: float = None,
    limit: int = 5
) -> str:
    """Browse products within a specific category with rating and price filters. Use when customers want to browse a known category.
    
    Args:
        category: Product category name
        min_rating: Minimum star rating (default: 4.0)
        max_price: Maximum price filter (optional)
        limit: Number of results (default: 10)
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    
    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(_db_service)
        result = _run_async(logic.get_products_by_category(
            category, min_rating, max_price, limit
        ))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def running_low(limit: int = 5) -> str:
    """Get products that are running low on stock, prioritized by demand. Use to identify items that need restocking soon.

    Args:
        limit: Number of results (default: 5)
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(_db_service)
        result = _run_async(logic.running_low(limit))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def side_by_side(product_id_1: int, product_id_2: int) -> str:
    """Compare two products side by side by their product IDs. Use when customers want to see differences in price, rating, and features.

    Args:
        product_id_1: First integer productId to compare (1-92 in the Pellier catalog).
        product_id_2: Second integer productId to compare (1-92 in the Pellier catalog).
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        query = """
            SELECT "productId", name, brand, color, description, price,
                   rating, reviews, category, "imgUrl", badge, tags
            FROM pellier.product_catalog
            WHERE "productId" = %s
        """
        p1_id = str(product_id_1).strip()
        p2_id = str(product_id_2).strip()
        p1 = _run_async(_db_service.fetch_one(query, p1_id))
        p2 = _run_async(_db_service.fetch_one(query, p2_id))

        if not p1 or not p2:
            missing = []
            if not p1: missing.append(product_id_1)
            if not p2: missing.append(product_id_2)
            return json.dumps({"error": f"Product(s) not found: {', '.join(str(m) for m in missing)}"})

        def fmt(row):
            reviews_raw = row.get("reviews")
            try:
                reviews_int = int(reviews_raw) if reviews_raw is not None else 0
            except (TypeError, ValueError):
                reviews_int = 0
            return {
                "productId": row.get("productId"),
                "name": row.get("name", ""),
                "brand": row.get("brand", ""),
                "color": row.get("color", ""),
                "price": float(row.get("price", 0)),
                "rating": float(row.get("rating", 0)),
                "reviews": reviews_int,
                "category": row.get("category", ""),
                "badge": row.get("badge"),
                "tags": list(row.get("tags") or []),
            }

        product_1 = fmt(p1)
        product_2 = fmt(p2)

        # Determine winner for each metric
        comparison = {
            "price_winner": product_1["productId"] if product_1["price"] <= product_2["price"] else product_2["productId"],
            "rating_winner": product_1["productId"] if product_1["rating"] >= product_2["rating"] else product_2["productId"],
            "reviews_winner": product_1["productId"] if product_1["reviews"] >= product_2["reviews"] else product_2["productId"],
            "price_difference": abs(product_1["price"] - product_2["price"]),
        }

        return json.dumps({
            "status": "success",
            "product_1": product_1,
            "product_2": product_2,
            "comparison": comparison,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# === RETURN POLICY TOOL (backed by pellier.return_policies table) ===

@tool
def returns_and_care(category: str = "default") -> str:
    """Look up the return and refund policy for a specific product category. Use when customers ask about returns, refunds, warranties, or return windows.

    Args:
        category: Product category name (e.g., "Home Decor", "Apparel")

    Returns:
        JSON string with return policy details
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        query = """
            SELECT category_name, return_window_days, conditions, refund_method
            FROM pellier.return_policies
            WHERE category_name = %s
        """
        row = _run_async(_db_service.fetch_one(query, category))

        if not row:
            row = _run_async(_db_service.fetch_one(query, "default"))

        if not row:
            return json.dumps({"error": f"No return policy found for category: {category}"})

        return json.dumps({
            "category": row["category_name"],
            "return_window_days": row["return_window_days"],
            "conditions": row["conditions"],
            "refund_method": row["refund_method"],
        })
    except Exception as e:
        return json.dumps({"error": f"Return policy lookup error: {str(e)}"})


@tool
def style_match(product_id: int, limit: int = 5) -> str:
    """Find complementary pieces that pair well with a given product.

    Uses pgvector cosine similarity to find products whose embeddings
    are closest to the given product's embedding — semantic style
    matching, not keyword overlap. Great for "what goes with this?"

    Args:
        product_id: The product to match against. Curated catalog IDs are 1-40; archive distractors use high IDs.
        limit: Number of matches to return (default: 5)

    Returns:
        JSON with the source product and its closest style matches,
        including cosine similarity scores.
    """
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})

    try:
        product_id_text = str(product_id).strip()
        source = _run_async(_db_service.fetch_one(
            'SELECT "productId", name, brand, price, category, embedding '
            'FROM pellier.product_catalog WHERE "productId" = %s',
            product_id_text,
        ))
        if not source:
            return json.dumps({"error": f"Product {product_id} not found"})
        # ``embedding`` comes back as a numpy array (pgvector adapter).
        # ``if not array`` raises "truth value is ambiguous" — check
        # for None / length-zero explicitly.
        emb = source.get("embedding")
        if emb is None or len(emb) == 0:
            return json.dumps({"error": f"Product {product_id} has no embedding"})

        # pgvector's text I/O wants ``[v1,v2,...]`` (comma-separated).
        # ``str(numpy_array)`` produces space-separated values which
        # the parser rejects with "invalid input syntax for type vector".
        emb_literal = "[" + ",".join(repr(float(v)) for v in emb) + "]"

        limit = max(1, min(int(limit), settings.MAX_SEARCH_LIMIT))
        matches = _run_async(_db_service.fetch_all(
            'SELECT "productId", name, brand, color, price, rating, reviews, '
            'category, "imgUrl", '
            '1 - (embedding <=> %s::vector) AS similarity_score '
            'FROM pellier.product_catalog '
            'WHERE "productId" != %s '
            "AND NOT (tags ? 'archive') "
            'ORDER BY embedding <=> %s::vector '
            'LIMIT %s',
            emb_literal, product_id_text,
            emb_literal, limit,
        ))

        payload = {
            "source": {
                "productId": str(source["productId"]).strip(),
                "name": source["name"],
                "brand": source["brand"],
                "price": float(source["price"]),
            },
            "matches": [
                {
                    "productId": str(m["productId"]).strip(),
                    "name": m["name"],
                    "brand": m["brand"],
                    "color": m.get("color", ""),
                    "price": float(m["price"]),
                    "rating": float(m.get("rating", 0)),
                    "reviews": int(m.get("reviews", 0)),
                    "category": m.get("category") or m.get("category_name", ""),
                    "imgUrl": m.get("imgUrl", ""),
                    "similarity_score": round(float(m.get("similarity_score", 0)), 4),
                }
                for m in matches
            ],
            # Keep compatibility with ProductExtractor, which expects
            # top-level "products" lists from tool outputs.
            "products": [
                {
                    "productId": str(m["productId"]).strip(),
                    "name": m["name"],
                    "brand": m["brand"],
                    "color": m.get("color", ""),
                    "price": float(m["price"]),
                    "rating": float(m.get("rating", 0)),
                    "reviews": int(m.get("reviews", 0)),
                    "category": m.get("category") or m.get("category_name", ""),
                    "imgUrl": m.get("imgUrl", ""),
                    "similarity_score": round(float(m.get("similarity_score", 0)), 4),
                }
                for m in matches
            ],
            "query_type": "pgvector_cosine_similarity",
            "index": "hnsw",
        }
        return json.dumps(payload)
    except Exception as e:
        logger.error(f"style_match error: {e}")
        return json.dumps({"error": str(e)})
