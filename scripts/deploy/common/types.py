"""
Shared types + invocation helpers for Pellier MCP servers.
Packaged into every MCP Lambda zip by deploy_lambda.py.
"""
from typing import Any, Optional, Tuple


class IdentityContext:
    """User identity from Cognito JWT."""
    def __init__(self, username: str = "", sub: str = "", email: str = None):
        self.username = username
        self.sub = sub
        self.email = email


# ---------------------------------------------------------------------------
# Migration-only tool-name aliases
# ---------------------------------------------------------------------------
#
# TEMPORARY. Remove once the live Gateway targets and Cedar policies have
# converged on the current vocabulary.
#
# The published tool names were renamed in source before the Gateway was
# redeployed, so during the migration window the live Gateway still invokes
# retired names against a Lambda that only implements current ones. Without this
# map, deploying the new Lambda first would break every governed call
# immediately, and deploying the Gateway first would leave a window where the
# targets name tools the Lambda cannot serve. Neither intermediate state is
# acceptable, so the Lambda accepts both for the length of one release.
#
# This is DISPATCH ONLY, and the precise scope matters.
#
# Each Lambda surface builds its own `list_tools` response from its TOOLS mapping, which
# holds current names exclusively. So the LAMBDA never advertises a retired name.
#
# That is not the same as Gateway discovery. A Gateway target advertises the tool schema
# stored ON THE TARGET, and on the existing migrated engineering deployment three of the
# four targets still carry the retired vocabulary: MCP `list_tools` there returns
# `pellier-discovery-search-target___floor_check` and twelve siblings. Only the experience
# target was converged.
#
# A fresh workshop provision publishes canonical names only, from
# `gateway_tool_schemas.workshop_published_tools()`. Until the remaining three targets are
# converged, "retired names are never advertised" is true of a fresh stack and false of
# the engineering one. This map is what keeps the engineering stack callable in the
# meantime.
_MIGRATION_TOOL_ALIASES = {
    "floor_check": "check_inventory",
    "running_low": "get_low_stock",
    "restock_shelf": "restock_inventory",
    "process_return": "initiate_return",
    "find_pieces": "search_products",
    "find_pieces_hybrid": "search_products_hybrid",
    "whats_trending": "get_trending_products",
    "price_intelligence": "get_price_analysis",
    "explore_collection": "browse_category",
    "side_by_side": "compare_products",
    "returns_and_care": "get_return_policy",
    "style_match": "get_related_products",
    "preference_snapshot": "get_customer_preferences",
    "trace_receipt": "get_audit_trail",
    "escalate_to_stylist": "escalate_to_human",
}


def canonical_tool_name(tool: str) -> str:
    """Map a retired published name onto its current implementation.

    Current names pass through unchanged, so this is safe to apply
    unconditionally and becomes a no-op the moment the Gateway has converged.
    """
    return _MIGRATION_TOOL_ALIASES.get(tool, tool)


def resolve_invocation(event: dict, context: Any) -> Tuple[str, dict]:
    """Return (tool_name, arguments) for BOTH MCP Lambda invocation paths.

    AgentCore Gateway and a direct/test invoke pass tools differently, and
    getting this wrong silently breaks EVERY Gateway-routed tool call:

    * Gateway path: the tool name arrives in
      ``context.client_context.custom['bedrockAgentCoreToolName']`` PREFIXED with
      ``<gateway-TARGET-name>___`` (triple underscore — e.g.
      ``pellier-concierge-experience-target___initiate_return``), and the tool
      arguments ARE the event dict itself. The bare ``event['name']`` is NOT set
      here, so a naive ``event.get('name')`` returns "" and the call falls
      through to "Unknown tool". NOTE the prefix is the Gateway target name,
      NOT the Lambda function name — dat403's electrify server stripped
      ``<function>___`` and got away with it only because its target and
      function shared a name; ours differ, so a function-name guess misses and
      the full prefixed string leaks through (box-verified 2026-06-12).
    * Direct / test invoke (and the ``list_tools`` probe): ``{"name","arguments"}``.

    Strategy: check the Gateway client_context first, strip everything up to
    the last ``___`` (robust to whatever prefix convention the Gateway uses),
    treat the event as the argument payload; otherwise fall back to the flat
    ``{name, arguments}`` shape.
    """
    if getattr(context, "client_context", None):
        custom = getattr(context.client_context, "custom", {}) or {}
        prefixed = custom.get("bedrockAgentCoreToolName")
        if prefixed:
            tool = canonical_tool_name(prefixed.rsplit("___", 1)[-1])
            args = {k: v for k, v in event.items() if k not in ("name", "arguments")}
            if not args and isinstance(event.get("arguments"), dict):
                args = event["arguments"]
            return tool, args
    return (
        canonical_tool_name(event.get("name", "")),
        (event.get("arguments", {}) or {}),
    )
