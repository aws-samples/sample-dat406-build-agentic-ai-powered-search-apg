"""
Direct MCP Tools - Sync wrappers for database access
"""
from strands import tool
import json

# Global MCP tools instance
_mcp_tools = None

def set_mcp_tools(mcp):
    """Set the MCP tools instance"""
    global _mcp_tools
    _mcp_tools = mcp

@tool
def get_inventory_health() -> str:
    """Get inventory health statistics from database"""
    if not _mcp_tools:
        return json.dumps({"error": "MCP tools not initialized"})
    
    try:
        return _mcp_tools.get("inventory_health", json.dumps({"error": "No data available"}))
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_trending_products(limit: int = 10) -> str:
    """Get trending products from database"""
    if not _mcp_tools:
        return json.dumps({"error": "MCP tools not initialized"})
    
    try:
        return _mcp_tools.get("trending_products", json.dumps({"error": "No data available"}))
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_price_statistics() -> str:
    """Get price statistics by category"""
    if not _mcp_tools:
        return json.dumps({"error": "MCP tools not initialized"})
    
    try:
        return _mcp_tools.get("price_statistics", json.dumps({"error": "No data available"}))
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def restock_product(product_id: str, quantity: int) -> str:
    """Restock a product in database"""
    return json.dumps({
        "status": "success",
        "message": f"Would restock {product_id} with {quantity} units",
        "note": "Use /api/mcp/restock endpoint for actual restocking"
    })
