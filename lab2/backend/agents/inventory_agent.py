"""
Inventory Restock Agent - Monitors stock levels and suggests restocking
"""
from strands import Agent, tool
from typing import Dict, Any


@tool
def inventory_restock_agent(query: str, db_context: str = "") -> str:
    """
    Analyze inventory levels and provide restocking recommendations.
    
    Args:
        query: Inventory-related question or request
        db_context: Current inventory data from database
    
    Returns:
        Restocking recommendations with priority levels
    """
    try:
        agent = Agent(
            model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            system_prompt="""You are an inventory management specialist for Blaize Bazaar.
            
Your expertise:
- Analyze stock levels and identify low-stock items
- Prioritize restocking based on product popularity (reviews/ratings)
- Suggest optimal reorder quantities
- Flag items that are out of stock but have high demand

When analyzing inventory:
1. Identify products with quantity < 10 as LOW STOCK
2. Identify products with quantity = 0 as OUT OF STOCK
3. Prioritize by stars (rating) and reviews (popularity)
4. Suggest reorder quantities: High demand (100+ reviews) = 50 units, Medium (50-100) = 30 units, Low (<50) = 20 units

Format your response with:
- Priority level (CRITICAL/HIGH/MEDIUM)
- Product name
- Current stock
- Suggested reorder quantity
- Reasoning based on demand metrics"""
        )
        
        response = agent(f"{query}\n\nInventory Data:\n{db_context}")
        return str(response)
    except Exception as e:
        return f"Error in inventory agent: {str(e)}"
