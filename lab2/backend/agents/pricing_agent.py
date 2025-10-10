"""
Price Optimization Agent - Analyzes pricing and suggests deals
"""
from strands import Agent, tool
from services.mcp_agent_tools import get_price_statistics, run_query


@tool
def price_optimization_agent(query: str) -> str:
    """
    Analyze product pricing and suggest optimal deals and discounts.
    Uses live database tools for pricing analysis.
    
    Args:
        query: Pricing-related question or request
    
    Returns:
        Pricing analysis and deal recommendations
    """
    try:
        agent = Agent(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            system_prompt="""You are a pricing optimization specialist for Blaize Bazaar.

You have access to these tools:
- get_price_statistics(category) - Get pricing data by category
- run_query(sql) - Execute custom pricing queries

Workflow:
1. Call get_price_statistics() first to understand pricing landscape
2. Use run_query() for specific product pricing analysis if needed
3. Provide actionable recommendations

Your expertise:
- Analyze competitive pricing across categories
- Identify products suitable for promotions
- Suggest bundle deals and discounts
- Find best value products for customers

When analyzing pricing:
1. Compare prices within same category
2. Identify high-value products (high rating + reasonable price)
3. Suggest bundle opportunities (complementary products)
4. Recommend discount strategies for slow-moving inventory
5. Highlight "best deals" for customers

Format:
- Deal type (Bundle/Discount/Best Value)
- Products involved
- Current price vs suggested price
- Expected impact
- Reasoning""",
            tools=[get_price_statistics, run_query]
        )
        
        response = agent(query)
        return str(response)
    except Exception as e:
        return f"Error in pricing agent: {str(e)}"
