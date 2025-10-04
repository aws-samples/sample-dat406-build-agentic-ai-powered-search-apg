"""
Inventory Restock Agent - Monitors stock levels and suggests restocking
"""
from strands import Agent, tool
from services.mcp_tool_wrappers import get_inventory_health_tool


@tool
def inventory_restock_agent(query: str) -> str:
    """
    Analyze inventory levels and provide restocking recommendations.
    Can also execute restock actions when user provides product ID and quantity.
    
    Args:
        query: Inventory-related question or restock command
    
    Returns:
        Restocking recommendations or restock confirmation
    """
    try:
        from services.mcp_tool_wrappers import restock_product_tool
        
        # Get inventory data from custom MCP tool
        inventory_data = get_inventory_health_tool()
        
        agent = Agent(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            system_prompt="""You are an inventory management specialist for Blaize Bazaar.
            
Analyze stock levels and provide ONE concise restocking report.

Guidelines:
1. LOW STOCK: quantity < 10 | OUT OF STOCK: quantity = 0
2. Prioritize by stars and reviews
3. Reorder quantities: High demand (100+ reviews) = 50 units, Medium (50-100) = 30 units, Low (<50) = 20 units
4. List critical items with product IDs if available
5. Keep response under 200 words - no repetition

For restock requests:
- Use restock_product_tool(product_id, quantity) to add stock
- Confirm the action with old and new quantities

Format:
- Summary stats
- Top priority items (if names provided)
- Recommended actions""",
            tools=[restock_product_tool]
        )
        
        response = agent(f"{query}\n\nInventory Health Data:\n{inventory_data}")
        return str(response)
    except Exception as e:
        return f"Error in inventory agent: {str(e)}"
