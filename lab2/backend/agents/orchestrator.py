"""
Orchestrator Agent - Routes queries to specialized agents
"""
from strands import Agent
from .inventory_agent import inventory_restock_agent
from .recommendation_agent import product_recommendation_agent
from .pricing_agent import price_optimization_agent


ORCHESTRATOR_PROMPT = """You are the main assistant for Blaize Bazaar e-commerce platform.

You coordinate specialized agents to handle different types of requests:

1. **inventory_restock_agent** - Use for:
   - Stock level inquiries
   - Restocking recommendations
   - Low inventory alerts
   - Out-of-stock analysis

2. **product_recommendation_agent** - Use for:
   - Product suggestions based on user needs
   - "What should I buy" questions
   - Feature-based product matching
   - Budget-conscious recommendations

3. **price_optimization_agent** - Use for:
   - Pricing analysis
   - Deal suggestions
   - Bundle recommendations
   - Best value inquiries

For simple greetings or general questions, respond directly without using tools.

Always select the most appropriate agent based on the user's query."""


def create_orchestrator():
    """Create the orchestrator agent with all specialized agents as tools"""
    return Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            inventory_restock_agent,
            product_recommendation_agent,
            price_optimization_agent,
        ]
    )
