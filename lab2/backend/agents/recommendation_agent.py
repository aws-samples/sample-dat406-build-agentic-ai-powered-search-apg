"""
Product Recommendation Agent - Suggests products based on user preferences
"""
from strands import tool


@tool
def product_recommendation_agent(query: str) -> str:
    """
    Provide personalized product recommendations based on user preferences.
    Returns instructions for the orchestrator to query the database.
    
    Args:
        query: User's product inquiry with preferences
    
    Returns:
        Instructions for orchestrator to use run_query MCP tool
    """
    # Extract search terms and constraints from query
    query_lower = query.lower()
    
    # Determine product category
    if any(word in query_lower for word in ['headphone', 'earbud', 'audio']):
        category = 'headphone'
    elif any(word in query_lower for word in ['camera', 'security']):
        category = 'camera'
    elif any(word in query_lower for word in ['vacuum', 'clean']):
        category = 'vacuum'
    elif any(word in query_lower for word in ['gaming', 'game', 'controller']):
        category = 'gaming'
    else:
        category = query_lower.split()[0] if query_lower else 'product'
    
    # Extract price constraint
    price_constraint = ''
    if 'under' in query_lower:
        import re
        price_match = re.search(r'under\s+\$?(\d+)', query_lower)
        if price_match:
            price_constraint = f" AND price <= {price_match.group(1)}"
    
    return f"""INSTRUCTION: Use the 'run_query' MCP tool to search our database.

OUR CATALOG HAS: Headphones, cameras, vacuums, gaming gear, wearables, tech accessories (21,704 products)

SQL Query:
SELECT "productId", product_description as name, price, stars, reviews, 
       category_name as category, quantity, imgurl as image_url
FROM bedrock_integration.product_catalog 
WHERE product_description ILIKE '%{category}%'{price_constraint}
  AND price > 0
  AND quantity > 0
ORDER BY stars DESC, reviews DESC
LIMIT 5

After getting results, format as JSON and provide recommendations."""}
