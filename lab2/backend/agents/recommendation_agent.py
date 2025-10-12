"""
Product Recommendation Agent - Suggests products based on user preferences
"""
from strands import Agent, tool
from services.agent_tools import get_trending_products, run_query


@tool
def product_recommendation_agent(query: str) -> str:
    """
    Provide personalized product recommendations based on user preferences.
    Uses live database tools to search and recommend products.
    
    Args:
        query: User's product inquiry with preferences
    
    Returns:
        Personalized product recommendations with reasoning
    """
    try:
        agent = Agent(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            system_prompt="""You are a product recommendation specialist for Blaize Bazaar.

OUR CATALOG: 21,704 products including headphones, security cameras, vacuums, gaming gear, wearables, and tech accessories.

You have access to these tools:
- get_trending_products(limit) - Get popular products
- run_query(sql) - Search product catalog with SQL

Workflow:
1. Understand user's needs (budget, features, category)
2. Use run_query() to search for matching products:
   SELECT "productId", product_description as name, price, stars, reviews,
          category_name as category, quantity, imgurl as image_url
   FROM bedrock_integration.product_catalog
   WHERE product_description ILIKE '%search_term%'
     AND price > 0 AND quantity > 0
   ORDER BY stars DESC, reviews DESC
   LIMIT 5
3. Provide 3-5 recommendations with reasoning

Guidelines:
- Prioritize highly-rated products (4+ stars)
- Match features to stated use case
- Consider budget constraints
- Highlight best value options

Format:
- Product name, price, rating
- Why it's a good fit
- Key features""",
            tools=[get_trending_products, run_query]
        )
        
        response = agent(query)
        return str(response)
    except Exception as e:
        return f"Error in recommendation agent: {str(e)}"
