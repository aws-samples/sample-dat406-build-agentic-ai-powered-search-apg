"""
MCP Tool Wrappers - HTTP-based wrappers for MCP tools
Uses FastAPI endpoints instead of direct database connections
"""
from strands import tool
import json
try:
    import requests
except ImportError:
    requests = None

# FastAPI server URL
API_BASE_URL = "http://localhost:8000"


@tool
def get_trending_products_tool(limit: int = 10) -> str:
    """
    Get trending products based on reviews and ratings.
    
    Args:
        limit: Number of trending products to return
        
    Returns:
        JSON string with trending products data
    """
    try:
        response = requests.get(f"{API_BASE_URL}/api/mcp/trending", params={"limit": limit}, timeout=10)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.ConnectionError:
        return json.dumps({"error": "Cannot connect to API server. Please ensure FastAPI server is running on port 8000."})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_inventory_health_tool() -> str:
    """
    Get overall inventory health statistics and alerts.
    
    Returns:
        JSON string with inventory health data
    """
    try:
        response = requests.get(f"{API_BASE_URL}/api/mcp/inventory-health", timeout=10)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.ConnectionError:
        return json.dumps({"error": "Cannot connect to API server. Please ensure FastAPI server is running on port 8000."})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_price_statistics_tool(category: str = None) -> str:
    """
    Get price statistics by category or overall.
    
    Args:
        category: Optional category filter
        
    Returns:
        JSON string with price statistics
    """
    try:
        params = {"category": category} if category else {}
        response = requests.get(f"{API_BASE_URL}/api/mcp/price-stats", params=params, timeout=10)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.ConnectionError:
        return json.dumps({"error": "Cannot connect to API server. Please ensure FastAPI server is running on port 8000."})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def restock_product_tool(product_id: str, quantity: int) -> str:
    """
    Add stock to a product in the inventory.
    
    Args:
        product_id: Product ID (ASIN) to restock
        quantity: Number of units to add
        
    Returns:
        JSON string with restock confirmation
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/mcp/restock",
            json={"product_id": product_id, "quantity": quantity},
            timeout=10
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.ConnectionError:
        return json.dumps({"error": "Cannot connect to API server. Please ensure FastAPI server is running on port 8000."})
    except Exception as e:
        return json.dumps({"error": str(e)})
