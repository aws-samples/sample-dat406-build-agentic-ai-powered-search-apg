#!/usr/bin/env python3
"""
Blaize Bazaar Orchestrator Agent

A specialized Strands agent that routes queries to domain experts:
- Inventory Agent: Stock analysis and restocking
- Recommendation Agent: Product recommendations
- Pricing Agent: Price analysis and deals
"""

from strands import Agent
from agents.inventory_agent import inventory_restock_agent
from agents.recommendation_agent import product_recommendation_agent
from agents.pricing_agent import price_optimization_agent


# Orchestrator system prompt
BLAIZE_ORCHESTRATOR_PROMPT = """
You are Aurora AI, the orchestrator for Blaize Bazaar e-commerce platform.

Your role is to analyze customer queries and route them to specialized agents:

1. **Inventory Agent** - For stock levels, restocking, availability
   - Keywords: inventory, stock, restock, available, out of stock
   - Example: "What products need restocking?"

2. **Recommendation Agent** - For product suggestions and recommendations
   - Keywords: recommend, suggest, best, top, looking for, need
   - Example: "Recommend laptops for gaming"

3. **Pricing Agent** - For pricing analysis, deals, and discounts
   - Keywords: price, deal, discount, cheap, expensive, bundle
   - Example: "What are the best deals?"

Decision Protocol:
- If query involves stock/inventory → Use inventory_restock_agent
- If query asks for recommendations → Use product_recommendation_agent
- If query involves pricing/deals → Use price_optimization_agent
- For general product search, provide helpful guidance

Always route to the most appropriate specialist for accurate assistance.
"""


def create_blaize_orchestrator():
    """
    Create the Blaize Bazaar orchestrator agent.
    
    Returns:
        Agent configured with specialized tools
    """
    return Agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        system_prompt=BLAIZE_ORCHESTRATOR_PROMPT,
        tools=[
            inventory_restock_agent,
            product_recommendation_agent,
            price_optimization_agent
        ]
    )


# Example usage
if __name__ == "__main__":
    print("\n🛍️ Blaize Bazaar Orchestrator 🛍️\n")
    print("Ask about inventory, recommendations, or pricing!")
    print("Type 'exit' to quit.")

    orchestrator = create_blaize_orchestrator()

    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() == "exit":
                print("\nGoodbye! 👋")
                break

            response = orchestrator(user_input)
            print(str(response))
            
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try asking a different question.")
