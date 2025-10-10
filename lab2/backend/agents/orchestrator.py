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

A. SPECIALIZED AGENTS (for complex analysis):
1. **inventory_restock_agent** - Comprehensive stock analysis and restocking
2. **product_recommendation_agent** - Personalized product recommendations
3. **price_optimization_agent** - Pricing analysis and deal suggestions

B. DIRECT DATABASE TOOLS (for simple queries):
1. **run_query(sql)** - Execute SQL queries directly
2. **get_inventory_health()** - Quick inventory stats
3. **get_trending_products(limit)** - Popular products
4. **get_price_statistics(category)** - Pricing data

ROUTING STRATEGY:

Simple queries → Use direct database tools:
- "Show trending products" → get_trending_products(10)
- "What's in stock?" → get_inventory_health()
- "Price stats for electronics" → get_price_statistics("Electronics")

Complex queries → Delegate to specialist agents:
- "What products need restocking and why?" → inventory_restock_agent
- "Recommend wireless headphones under $100" → product_recommendation_agent
- "What are the best deals?" → price_optimization_agent

For simple greetings, respond directly without tools.

When extended thinking is enabled:
- Think carefully about query complexity
- Choose between direct tools vs specialist agents
- Coordinate multiple tools if needed

The specialist agents will handle their own tool calls - you just need to route to them!"""


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
