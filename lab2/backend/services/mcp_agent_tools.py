"""
Direct MCP Tools - Live database access for agents
"""
from strands import tool
import json
import asyncio

# Global database service reference
_db_service = None

def set_db_service(db_service):
    """Set the database service instance"""
    global _db_service
    _db_service = db_service

def _run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@tool
def get_inventory_health() -> str:
    """Get current inventory health statistics with live data from database"""
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    
    try:
        from services.mcp_database import CustomMCPTools
        mcp = CustomMCPTools(_db_service)
        result = _run_async(mcp.get_inventory_health())
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_trending_products(limit: int = 10) -> str:
    """Get trending products with live data from database"""
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    
    try:
        from services.mcp_database import CustomMCPTools
        mcp = CustomMCPTools(_db_service)
        result = _run_async(mcp.get_trending_products(limit))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_price_statistics(category: str = None) -> str:
    """Get price statistics by category with live data from database"""
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    
    try:
        from services.mcp_database import CustomMCPTools
        mcp = CustomMCPTools(_db_service)
        result = _run_async(mcp.get_price_statistics(category))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def restock_product(product_id: str, quantity: int) -> str:
    """Restock a product in database with live execution"""
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    
    try:
        from services.mcp_database import CustomMCPTools
        mcp = CustomMCPTools(_db_service)
        result = _run_async(mcp.restock_product(product_id, quantity))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def run_query(sql: str) -> str:
    """Execute arbitrary SQL query on the database"""
    if not _db_service:
        return json.dumps({"error": "Database service not initialized"})
    
    try:
        result = _run_async(_db_service.fetch_all(sql))
        # Convert to list of dicts
        data = [dict(row) for row in result]
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
