"""
Orchestrator Agent - Routes queries to specialized agents with interleaved thinking
"""
from strands import Agent
from strands.models import BedrockModel
from .inventory_agent import inventory_restock_agent
from .recommendation_agent import product_recommendation_agent
from .pricing_agent import price_optimization_agent


ORCHESTRATOR_PROMPT = """You are the main assistant for Blaize Bazaar e-commerce platform.

OUR CATALOG: 21,704 products including headphones, security cameras, vacuums, gaming gear, wearables, and tech accessories.

You have access to TWO types of tools:

A. SPECIALIZED AGENTS (for strategy):
1. **inventory_restock_agent** - Stock analysis and restocking recommendations
2. **product_recommendation_agent** - Returns search strategy and SQL queries
3. **price_optimization_agent** - Pricing analysis and deal suggestions

B. DATABASE TOOLS (for execution):
1. **run_query** - Execute SQL queries to get actual product data
2. **get_table_schema** - Get database schema information
3. **get_inventory_health** - Get inventory statistics
4. **get_trending_products** - Get trending product data
5. **get_price_statistics** - Get price analytics

CRITICAL WORKFLOW for product searches:
1. Call recommendation agent → get SQL query strategy
2. Call run_query tool → execute SQL and get actual products
3. Format results as JSON for frontend

EXAMPLE:
User: "wireless headphones under $100"
→ Call product_recommendation_agent(query)
→ Agent returns SQL query
→ Call run_query(sql) to get products
→ Return formatted JSON with products

For simple greetings, respond directly without tools.

When extended thinking is enabled:
- Think carefully about which tools to use
- Execute database queries after getting search strategy
- Coordinate multiple tools for comprehensive answers

ALWAYS execute run_query to get actual products - don't just return search instructions!"""


def create_orchestrator(enable_interleaved_thinking: bool = False):
    """Create the orchestrator agent with all specialized agents as tools
    
    Args:
        enable_interleaved_thinking: Enable Claude Sonnet 4's extended thinking (default: False)
    
    Returns:
        Agent configured with or without interleaved thinking
    """
    if enable_interleaved_thinking:
        # Claude 4 with interleaved thinking
        model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            max_tokens=4096,
            temperature=1,  # Required when thinking is enabled
            additional_request_fields={
                "anthropic_beta": ["interleaved-thinking-2025-05-14"],
                "reasoning_config": {
                    "type": "enabled",
                    "budget_tokens": 3000
                }
            }
        )
    else:
        # Standard Claude 4 without thinking
        model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            max_tokens=4096,
            temperature=1
        )
    
    return Agent(
        model=model,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            inventory_restock_agent,
            product_recommendation_agent,
            price_optimization_agent,
        ]
    )
