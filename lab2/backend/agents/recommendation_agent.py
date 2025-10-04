"""
Product Recommendation Agent - Suggests products based on user preferences
"""
from strands import Agent, tool
from services.mcp_tool_wrappers import get_trending_products_tool


@tool
def product_recommendation_agent(query: str) -> str:
    """
    Provide personalized product recommendations based on user preferences.
    Uses custom MCP tool 'get_trending_products' for data.
    
    Args:
        query: User's product inquiry with preferences
    
    Returns:
        Personalized product recommendations with reasoning
    """
    try:
        # Get trending products from custom MCP tool
        trending_data = get_trending_products_tool(limit=15)
        
        agent = Agent(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            system_prompt="""You are a product recommendation specialist for Blaize Bazaar.

Your expertise:
- Understand user preferences (budget, features, brand, use case)
- Match products to user needs based on ratings, reviews, and features
- Provide 3-5 tailored recommendations
- Explain why each product fits the user's requirements

IMPORTANT: If the product context is empty or doesn't contain relevant products:
- Politely inform the user that the specific product category is not currently available
- Suggest alternative categories that ARE available in our catalog
- Offer to help with products we do have in stock

When recommending products:
1. Consider user's budget constraints
2. Prioritize highly-rated products (4+ stars)
3. Match features to stated use case
4. Highlight best value options
5. Mention any standout features or benefits

Format recommendations as:
- Product name
- Price
- Rating & review count
- Why it's a good fit
- Key features"""
        )
        
        response = agent(f"{query}\n\nTrending Products Data:\n{trending_data}")
        return str(response)
    except Exception as e:
        return f"Error in recommendation agent: {str(e)}"
