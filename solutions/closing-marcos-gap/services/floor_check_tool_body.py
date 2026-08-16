# Paste inside floor_check(product_query: str = "") in
# pellier/backend/services/agent_tools.py, replacing the stub return block.

    if not _db_service:
        return json.dumps({
            "error": "inventory_unavailable",
            "message": "The inventory lookup is temporarily unavailable.",
        })

    try:
        from services.business_logic import BusinessLogic

        logic = BusinessLogic(_db_service)
        query = (product_query or "").strip() or None
        result = _run_async(logic.floor_check(product_query=query))
        return json.dumps(result, indent=2)
    except Exception:
        logger.exception("floor_check failed")
        return json.dumps({
            "error": "inventory_lookup_failed",
            "message": "The inventory lookup could not be completed.",
        })
