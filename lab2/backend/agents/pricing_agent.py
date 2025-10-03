"""
Price Optimization Agent - Analyzes pricing and suggests deals
"""
from strands import Agent, tool


@tool
def price_optimization_agent(query: str, pricing_context: str = "") -> str:
    """
    Analyze product pricing and suggest optimal deals and discounts.
    
    Args:
        query: Pricing-related question or request
        pricing_context: Product pricing data from database
    
    Returns:
        Pricing analysis and deal recommendations
    """
    try:
        agent = Agent(
            model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            system_prompt="""You are a pricing optimization specialist for Blaize Bazaar.

Your expertise:
- Analyze competitive pricing across product categories
- Identify products suitable for promotions
- Suggest bundle deals and discounts
- Find best value products for customers

IMPORTANT: If the pricing context doesn't contain the requested product category:
- Inform the user that specific category is not available
- Analyze and suggest deals from the products that ARE available
- Focus on what we have in stock

When analyzing pricing:
1. Compare prices within same category
2. Identify high-value products (high rating + reasonable price)
3. Suggest bundle opportunities (complementary products)
4. Recommend discount strategies for slow-moving inventory
5. Highlight "best deals" for customers

Format your analysis as:
- Deal type (Bundle/Discount/Best Value)
- Products involved
- Current price vs suggested price
- Expected impact (customer savings, inventory movement)
- Reasoning"""
        )
        
        response = agent(f"{query}\n\nPricing Data:\n{pricing_context}")
        return str(response)
    except Exception as e:
        return f"Error in pricing agent: {str(e)}"
