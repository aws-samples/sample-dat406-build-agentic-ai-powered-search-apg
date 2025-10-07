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
- "Show similar items"
- "Different price range"
- "Other brands"

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
        """Enhanced chat using Strands with product extraction"""
        logger.info(f"🤖 Processing query with Strands Agent")
        
        # This will raise an exception if it fails
        mcp_client = self._create_mcp_client()
        
        try:
            with mcp_client:
                # Get database tools
                tools = mcp_client.list_tools_sync()
                logger.info(f"✅ Connected to database with {len(tools)} tools available")
                
                if len(tools) == 0:
                    raise RuntimeError("No database tools available from MCP server")
                
                # Build conversation context with product info
                conversation_context = ""
                if conversation_history:
                    # Include last 4 exchanges for context
                    recent_history = conversation_history[-8:]  # Last 4 user+assistant pairs
                    for msg in recent_history:
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        # Truncate long responses but keep key info
                        if len(content) > 500:
                            content = content[:500] + "..."
                        conversation_context += f"{role.upper()}: {content}\n\n"
                
                # Prepend context to current message
                full_message = message
                if conversation_context:
                    full_message = f"""CONVERSATION HISTORY (use this to understand context):
{conversation_context}
---
CURRENT USER QUERY: {message}

IMPORTANT: If the user asks about "cheapest", "best", "recommend", etc., look at the CONVERSATION HISTORY above to understand what product category they're referring to."""
                    logger.info(f"📜 Including conversation history ({len(recent_history)} messages)")
                    logger.info(f"📝 Full context: {full_message[:300]}...")
                
                # Create agent
                agent = self.Agent(
                    model=self.model_id,
                    tools=tools,
                    system_prompt=self._get_system_prompt()
                )
                
                # Invoke agent with full context
                logger.info(f"🔍 Agent searching database...")
                response = agent(full_message)
                response_text = str(response)
                
                logger.info(f"✅ Agent completed")
                logger.info(f"📝 Agent response: {response_text[:500]}...")
                
                # Extract structured data from response
                parsed = self._parse_agent_response(response_text)
                logger.info(f"📦 Parsed products: {parsed['products']}")
                
                logger.info(f"📦 Found {len(parsed['products'])} products")
                
                result = {
                    "response": parsed["text"],
                    "products": parsed["products"],
                    "suggestions": parsed["suggestions"],
                    "success": True,
                    "mcp_enabled": True,
                    "model": self.model_id,
                    "tool_calls": []
                }
                
                logger.info(f"📤 Returning {len(result['products'])} products to frontend")
                return result
                
        except Exception as e:
            logger.error(f"❌ Strands agent execution failed: {e}", exc_info=True)
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
        
        # Extract suggestions (lines starting with - )
        suggestion_pattern = r'^-\s+"([^"]+)"'
        suggestions = re.findall(suggestion_pattern, response_text, re.MULTILINE)
        
        # Also extract inline suggestions from quotes (e.g., "show me smartphones")
        inline_pattern = r'"([^"]+?)"'
        inline_suggestions = re.findall(inline_pattern, response_text)
        
        # Combine and filter out productId references
        all_suggestions = suggestions + [s for s in inline_suggestions if len(s) > 5 and len(s) < 50]
        filtered = [s for s in all_suggestions if 'productid' not in s.lower() and not re.match(r'^B[0-9A-Z]{9}$', s)]
        
        # Add smart suggestions based on context
        smart_suggestions = self._generate_smart_suggestions(query, result["products"])
        filtered.extend(smart_suggestions)
        
        result["suggestions"] = list(dict.fromkeys(filtered))[:5]  # Dedupe and limit to 5
        
        # Clean text (remove JSON blocks and suggestions)
        clean_text = re.sub(json_pattern, '', response_text, flags=re.DOTALL)
        clean_text = re.sub(suggestion_pattern, '', clean_text, flags=re.MULTILINE)
        clean_text = re.sub(r'Products:.*?Suggestions:', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
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