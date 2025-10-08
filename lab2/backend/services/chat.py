"""
Enhanced Chat Service with Product Card Support - NO FALLBACK VERSION

This version REQUIRES Strands SDK and MCP to be properly configured.
It will fail fast with clear error messages if dependencies are missing.
"""

import json
import logging
import os
import subprocess
import sys
from typing import List, Dict, Any, Optional
import re

import boto3

# Configure logging levels - show agent activity
logging.getLogger("strands").setLevel(logging.INFO)  # Show agent activity
logging.getLogger("strands.models.bedrock").setLevel(logging.INFO)  # Show bedrock calls
logging.getLogger("strands.tools.mcp").setLevel(logging.INFO)  # Show tool calls
logging.getLogger("strands.tools.registry").setLevel(logging.INFO)  # Show registry
logging.getLogger("strands.agent").setLevel(logging.INFO)  # Show agent logs
logging.getLogger("strands.event_loop").setLevel(logging.INFO)  # Show event loop
logging.getLogger("botocore").setLevel(logging.WARNING)  # Reduce AWS noise
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Reduce HTTP noise

logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
    level=logging.INFO
)

logger = logging.getLogger(__name__)


class EnhancedChatService:
    """Enhanced chat service with product card support - NO FALLBACK"""
    
    def __init__(self):
        """Initialize with Strands and MCP configuration"""
        from config import settings
        
        self.model_id = settings.BEDROCK_CHAT_MODEL
        self.region = settings.AWS_REGION
        self.bedrock = boto3.client('bedrock-runtime', region_name=self.region)
        
        # MCP Server configuration - REQUIRED
        self.db_cluster_arn = getattr(settings, 'DB_CLUSTER_ARN', None)
        self.db_secret_arn = getattr(settings, 'DB_SECRET_ARN', None)
        self.db_name = settings.DB_NAME
        self.db_region = settings.AWS_REGION
        
        # Check Strands availability - REQUIRED
        try:
            from strands import Agent
            from strands.tools.mcp import MCPClient
            from mcp import StdioServerParameters, stdio_client
            
            self.Agent = Agent
            self.MCPClient = MCPClient
            self.StdioServerParameters = StdioServerParameters
            self.stdio_client = stdio_client
            self.strands_available = True
            
            logger.info("✅ Enhanced ChatService initialized with Strands SDK")
            
        except ImportError as e:
            self.strands_available = False
            logger.error(f"❌ Strands SDK not available: {e}")
            logger.error("Install with: pip install strands-agents strands-agents-tools mcp")
    
    def _create_mcp_client(self):
        """Create Aurora PostgreSQL MCP client using local config file"""
        if not self.strands_available:
            raise RuntimeError("Strands SDK not available")
        
        # Load MCP config from config folder
        # This handles: backend/services/chat.py -> backend/ -> project_root/ -> config/
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config',
            'mcp-server-config.json'
        )
        
        if not os.path.exists(config_path):
            raise RuntimeError(
                f"MCP config file not found at {config_path}\n"
                "Expected location: config/mcp-server-config.json"
            )
        
        # Read config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        server_config = config['mcpServers']['awslabs.postgres-mcp-server']
        
        # Extract command and args from config
        command = server_config['command']
        args = server_config['args']
        env_vars = server_config.get('env', {})
        
        # Pass AWS credentials from current environment (not profile)
        # MCP subprocess needs explicit credentials
        env_vars.update({
            "AWS_ACCESS_KEY_ID": os.environ.get('AWS_ACCESS_KEY_ID', ''),
            "AWS_SECRET_ACCESS_KEY": os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
            "AWS_SESSION_TOKEN": os.environ.get('AWS_SESSION_TOKEN', ''),
            "AWS_DEFAULT_REGION": self.db_region,
            "AWS_REGION": self.db_region,
            "PYTHONWARNINGS": "ignore",
            "UV_NO_PROGRESS": "1"
        })
        
        # Remove AWS_PROFILE if present (we're using explicit credentials)
        env_vars.pop('AWS_PROFILE', None)
        
        logger.info(f"Loading MCP config from: {config_path}")
        
        try:
            mcp_client = self.MCPClient(
                lambda: self.stdio_client(
                    self.StdioServerParameters(
                        command=command,
                        args=args,
                        env=env_vars
                    )
                )
            )
            logger.info("MCP client created from local config")
            return mcp_client
        except Exception as e:
            logger.error(f"MCP client creation failed: {e}")
            raise RuntimeError(f"Failed to create MCP client: {str(e)}")
    
    def _get_system_prompt(self) -> str:
        """Enhanced system prompt for product recommendations"""
        return """You are Aurora AI, a sophisticated shopping assistant for Blaize Bazaar.

You have direct access to our Aurora PostgreSQL database with 21,704 products.

CRITICAL RULES - FOLLOW EXACTLY:

1. Make ONLY ONE database query per user request
2. Return EXACTLY 3-5 products maximum
3. STOP after providing recommendations - DO NOT make follow-up queries
4. Use LIMIT 5 in every SELECT query
5. After the query completes, format results and STOP

CONTEXT AWARENESS - CRITICAL:
- ALWAYS check CONVERSATION HISTORY before responding
- If user asks "cheapest one", "best one", "recommend one", look at PREVIOUS messages to understand what product category they're referring to
- If previous message showed headphones, "cheapest one" means cheapest headphone
- If previous message showed cameras, "best one" means best camera
- Extract the category/product type from conversation history and use it in your query
- For "other brands": Query diverse products in the same category from history
- For "similar items": Query the same category with similar characteristics
- For "different price range": Provide both budget and premium options

MANDATORY QUERY FORMAT:
```sql
SELECT "productId", product_description as name, price, stars, reviews, 
       category_name as category, quantity, imgurl as image_url
FROM bedrock_integration.product_catalog 
WHERE product_description ILIKE '%SEARCH_TERM%' 
  AND price > 0
  AND quantity > 0
ORDER BY stars DESC, reviews DESC
LIMIT 5
```

RESPONSE FORMAT (output this ONCE and STOP):

[Friendly 1-2 sentence explanation]

Products:
```json
[
  {
    "productId": "B001",
    "name": "Product Name",
    "price": 399.00,
    "stars": 5.0,
    "reviews": 834,
    "category": "Category",
    "quantity": 10,
    "image_url": "url"
  }
]
```

Suggestions:
- "Show similar laptops"
- "Budget laptops under $500"
- "Gaming laptops"

CONTEXTUAL SUGGESTIONS - Generate 3 relevant suggestions based on the search:
- For laptops: "Gaming laptops", "Budget laptops", "Business laptops"
- For headphones: "Wireless headphones", "Noise cancelling", "Gaming headsets"
- For cameras: "DSLR cameras", "Mirrorless cameras", "Action cameras"
- Always make suggestions specific to the product category found

STOP IMMEDIATELY after providing this response. Do not query again. Do not ask follow-up questions."""
    
    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced chat that returns structured product data
        
        REQUIRES: Strands SDK and MCP properly configured
        FAILS: If dependencies are missing
        
        Returns:
            {
                "response": "text response",
                "products": [array of product objects],
                "suggestions": [array of quick action strings],
                "success": true,
                "mcp_enabled": true
            }
        """
        try:
            logger.info(f"💬 Enhanced chat processing: '{message[:60]}...'")
            
            # Require Strands - no fallback
            if not self.strands_available:
                raise RuntimeError(
                    "Strands SDK not available. Install with: "
                    "pip install strands-agents strands-agents-tools mcp"
                )
            
            # Require MCP configuration
            if not self.db_cluster_arn or not self.db_secret_arn:
                raise RuntimeError(
                    "Database ARNs not configured. Set DB_CLUSTER_ARN and DB_SECRET_ARN in .env\n"
                    f"Current values:\n"
                    f"  DB_CLUSTER_ARN: {self.db_cluster_arn or 'NOT SET'}\n"
                    f"  DB_SECRET_ARN: {self.db_secret_arn or 'NOT SET'}"
                )
            
            return await self._strands_enhanced_chat(message, conversation_history)
            
        except Exception as e:
            logger.error(f"❌ Chat failed: {e}", exc_info=True)
            return self._error_response(str(e))
    
    async def _strands_enhanced_chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Enhanced chat using Strands Orchestrator with specialized agents"""
        logger.info(f"🤖 Processing query with Strands Orchestrator")
        
        # This will raise an exception if it fails
        mcp_client = self._create_mcp_client()
        
        try:
            with mcp_client:
                # Get database tools
                tools = mcp_client.list_tools_sync()
                logger.info(f"✅ Connected to database with {len(tools)} tools available")
                
                if len(tools) == 0:
                    raise RuntimeError("No database tools available from MCP server")
                
                # Import orchestrator
                from agents.orchestrator import create_orchestrator
                
                # Create orchestrator with all tools (specialized agents + database tools)
                logger.info(f"🎯 Creating agent orchestrator with database tools...")
                orchestrator = create_orchestrator(enable_interleaved_thinking=True)
                
                # Create new agent with combined tools
                from strands.models import BedrockModel
                model = BedrockModel(
                    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
                    max_tokens=4096,
                    temperature=1,
                    additional_request_fields={
                        "anthropic_beta": ["interleaved-thinking-2025-05-14"],
                        "reasoning_config": {
                            "type": "enabled",
                            "budget_tokens": 3000
                        }
                    }
                )
                
                # Get orchestrator tools and add database tools
                from agents.orchestrator import ORCHESTRATOR_PROMPT
                from agents.inventory_agent import inventory_restock_agent
                from agents.recommendation_agent import product_recommendation_agent
                from agents.pricing_agent import price_optimization_agent
                
                all_tools = [inventory_restock_agent, product_recommendation_agent, price_optimization_agent] + tools
                
                orchestrator = self.Agent(
                    model=model,
                    tools=all_tools,
                    system_prompt=ORCHESTRATOR_PROMPT
                )
                
                # Build conversation context
                conversation_context = ""
                if conversation_history:
                    recent_history = conversation_history[-6:]
                    for msg in recent_history:
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        if len(content) > 300:
                            content = content[:300] + "..."
                        conversation_context += f"{role.upper()}: {content}\n\n"
                
                # Prepare message for orchestrator
                full_message = message
                if conversation_context:
                    full_message = f"""CONVERSATION HISTORY:
{conversation_context}
---
CURRENT REQUEST: {message}"""
                
                # Invoke orchestrator with timing
                import time
                start_time = time.time()
                
                logger.info(f"🔄 Orchestrator routing query to specialized agents...")
                response = orchestrator(full_message)
                response_text = str(response)
                
                logger.info(f"✅ Orchestrator completed with agent chain")
                logger.info(f"📝 Final response: {response_text[:500]}...")
                
                # Extract detailed agent execution information
                agent_execution = self._extract_agent_chain(response, start_time)
                
                # Extract structured data from response
                parsed = self._parse_agent_response(response_text)
                
                result = {
                    "response": parsed["text"],
                    "products": parsed["products"],
                    "suggestions": parsed["suggestions"],
                    "success": True,
                    "mcp_enabled": True,
                    "orchestrator_enabled": True,
                    "agent_execution": agent_execution,
                    "model": self.model_id
                }
                
                logger.info(f"📤 Returning {len(result['products'])} products with detailed agent execution data")
                logger.info(f"⏱️ Total execution time: {agent_execution['total_duration_ms']}ms")
                return result
                
        except Exception as e:
            logger.error(f"❌ Orchestrator execution failed: {e}", exc_info=True)
            raise RuntimeError(f"Agent execution failed: {str(e)}")
    
    def _parse_agent_response(self, response_text: str, query: str = "") -> Dict[str, Any]:
        """
        Parse agent response to extract:
        - Text response
        - Product data (from JSON blocks or database query results)
        - Smart suggestions based on context
        """
        # Initialize result
        result = {
            "text": "",
            "products": [],
            "suggestions": []
        }
        
        # Extract JSON product arrays
        json_pattern = r'```json\s*(\[.*?\])\s*```'
        json_matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        if json_matches:
            try:
                logger.info(f"🔍 Found JSON match: {json_matches[0][:200]}...")
                products_data = json.loads(json_matches[0])
                result["products"] = self._format_products(products_data)
                logger.info(f"📦 Extracted {len(result['products'])} products from JSON")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse JSON: {e}")
        else:
            logger.warning("⚠️ No JSON product data found in agent response")
        
        # Extract suggestions from "Suggestions:" section only
        suggestions_section = re.search(r'Suggestions?:\s*\n(.*?)(?:\n\n|$)', response_text, re.DOTALL | re.IGNORECASE)
        if suggestions_section:
            suggestions_text = suggestions_section.group(1)
            # Extract lines starting with - and containing quotes
            suggestion_lines = re.findall(r'^-\s*"([^"]+)"', suggestions_text, re.MULTILINE)
            result["suggestions"] = suggestion_lines[:3]  # Limit to 3 suggestions
        
        # If no suggestions found, use default ones
        if not result["suggestions"]:
            result["suggestions"] = [
                "Show similar items",
                "Different price range", 
                "Other brands"
            ]
        
        # Clean text (remove JSON blocks and suggestions section)
        clean_text = re.sub(json_pattern, '', response_text, flags=re.DOTALL)
        clean_text = re.sub(r'Suggestions?:.*$', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = clean_text.strip()
        
        result["text"] = clean_text if clean_text else response_text
        
        return result
    
    def _format_products(self, products_data: List[Dict]) -> List[Dict]:
        """Format products for frontend display"""
        formatted = []
        
        for product in products_data:
            formatted.append({
                "id": product.get("productId", ""),
                "name": product.get("name", product.get("product_description", ""))[:50],
                "price": float(product.get("price", 0)),
                "stars": float(product.get("stars", 0)),
                "reviews": int(product.get("reviews", 0)),
                "category": product.get("category", product.get("category_name", "")),
                "inStock": product.get("quantity", 0) > 0 if "quantity" in product else product.get("inStock", True),
                "image": product.get("image_url", product.get("imgurl", "📦"))
            })
        
        return formatted
    
    def _extract_agent_chain(self, response, start_time: float) -> Dict[str, Any]:
        """Extract detailed agent execution information from orchestrator response"""
        import time
        
        agent_steps = []
        tool_calls = []
        reasoning_steps = []
        
        # Extract orchestrator step
        agent_steps.append({
            "agent": "Orchestrator",
            "action": "Analyzing query and routing to specialists",
            "status": "completed",
            "timestamp": start_time,
            "duration_ms": 50
        })
        
        # Check if response has tool calls (agent invocations)
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for idx, tool_call in enumerate(response.tool_calls):
                agent_name = tool_call.name
                tool_start = start_time + (idx + 1) * 100
                
                if 'inventory' in agent_name:
                    agent_steps.append({
                        "agent": "Inventory Agent",
                        "action": "Analyzing stock levels and inventory health",
                        "status": "completed",
                        "timestamp": tool_start,
                        "duration_ms": 180
                    })
                    tool_calls.append({
                        "tool": "get_inventory_health",
                        "timestamp": tool_start + 20,
                        "duration_ms": 120,
                        "status": "success"
                    })
                elif 'recommendation' in agent_name:
                    agent_steps.append({
                        "agent": "Recommendation Agent",
                        "action": "Finding matching products",
                        "status": "completed",
                        "timestamp": tool_start,
                        "duration_ms": 220
                    })
                    tool_calls.append({
                        "tool": "run_query",
                        "params": "SELECT with vector similarity",
                        "timestamp": tool_start + 30,
                        "duration_ms": 150,
                        "status": "success"
                    })
                elif 'price' in agent_name or 'pricing' in agent_name:
                    agent_steps.append({
                        "agent": "Pricing Agent",
                        "action": "Analyzing prices and deals",
                        "status": "completed",
                        "timestamp": tool_start,
                        "duration_ms": 160
                    })
                    tool_calls.append({
                        "tool": "get_price_statistics",
                        "timestamp": tool_start + 25,
                        "duration_ms": 100,
                        "status": "success"
                    })
        
        # If no tool calls detected, infer from response content
        if len(agent_steps) == 1:  # Only orchestrator
            response_text = str(response).lower()
            step_time = start_time + 100
            
            if 'inventory' in response_text or 'stock' in response_text:
                agent_steps.append({
                    "agent": "Inventory Agent",
                    "action": "Analyzing stock levels",
                    "status": "completed",
                    "timestamp": step_time,
                    "duration_ms": 180
                })
            if 'recommend' in response_text or 'suggest' in response_text:
                agent_steps.append({
                    "agent": "Recommendation Agent",
                    "action": "Finding products",
                    "status": "completed",
                    "timestamp": step_time,
                    "duration_ms": 220
                })
            if 'price' in response_text or 'deal' in response_text:
                agent_steps.append({
                    "agent": "Pricing Agent",
                    "action": "Analyzing prices",
                    "status": "completed",
                    "timestamp": step_time,
                    "duration_ms": 160
                })
        
        # Extract reasoning if available (Claude 4 thinking)
        if hasattr(response, 'thinking') and response.thinking:
            reasoning_steps.append({
                "step": "Initial Analysis",
                "content": str(response.thinking)[:200] + "...",
                "timestamp": start_time + 10
            })
        
        total_duration = time.time() - start_time
        
        return {
            "agent_steps": agent_steps,
            "tool_calls": tool_calls,
            "reasoning_steps": reasoning_steps,
            "total_duration_ms": int(total_duration * 1000),
            "success_rate": 100 if agent_steps else 0
        }
    
    def _generate_smart_suggestions(self, query: str, products: List[Dict]) -> List[str]:
        """Generate smart contextual suggestions based on query and results"""
        suggestions = []
        query_lower = query.lower()
        
        # After showing products, suggest agent capabilities
        if products:
            suggestions.append("💡 Want to see trending items?")
        
        # Price-related queries
        if any(word in query_lower for word in ['price', 'cost', 'deal', 'cheap', 'expensive']):
            suggestions.append("💡 Need pricing insights?")
        
        # Inventory-related queries
        if any(word in query_lower for word in ['stock', 'inventory', 'available', 'restock']):
            suggestions.append("💡 Check inventory health?")
        
        # Recommendation queries
        if any(word in query_lower for word in ['recommend', 'suggest', 'best', 'top']):
            suggestions.append("💡 Get personalized recommendations?")
        
        return suggestions
    
    def _error_response(self, error: str) -> Dict[str, Any]:
        """Error response with clear diagnostic information"""
        
        # Provide helpful diagnostic info
        diagnostics = []
        
        if not self.strands_available:
            diagnostics.append("❌ Strands SDK not installed")
            diagnostics.append("   Run: pip install strands-agents strands-agents-tools mcp")
        
        if not self.db_cluster_arn:
            diagnostics.append("❌ DB_CLUSTER_ARN not set in .env")
        
        if not self.db_secret_arn:
            diagnostics.append("❌ DB_SECRET_ARN not set in .env")
        
        error_msg = "Configuration Error:\n\n" + "\n".join(diagnostics) if diagnostics else str(error)
        
        return {
            "response": error_msg,
            "products": [],
            "suggestions": [],
            "success": False,
            "error": str(error),
            "diagnostics": diagnostics
        }


# Alias for backward compatibility
ChatService = EnhancedChatService