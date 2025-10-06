"""
Orchestrator Agent - Routes queries to specialized agents with interleaved thinking
"""
from strands import Agent
from strands.models import BedrockModel
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

When extended thinking is enabled:
- Think carefully about which agent(s) to use
- Reflect on results between tool calls
- Adapt your strategy based on what you learn
- Coordinate multiple agents if needed for comprehensive answers

Always select the most appropriate agent based on the user's query."""


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
