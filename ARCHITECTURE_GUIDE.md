# Architecture Guide - Core Implementation Highlights

This guide highlights where the key technologies are implemented in Blaize Bazaar.

---

## 🔍 1. pgvector Semantic Search

### Location: `lab2/backend/app.py`

**Lines 200-250** - Core semantic search endpoint:

```python
@app.post("/api/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: DatabaseService = Depends(get_db_service),
    embeddings: EmbeddingService = Depends(get_embedding_service),
):
    """
    Semantic search using pgvector HNSW index
    """
    # 1. Generate query embedding using Bedrock
    query_embedding = embeddings.generate_embedding(request.query)
    
    # 2. pgvector similarity search with cosine distance operator (<=>)
    query = """
        SELECT 
            "productId",
            product_description,
            price,
            stars,
            reviews,
            category_name,
            1 - (embedding <=> %s::vector) as similarity_score
        FROM bedrock_integration.product_catalog
        WHERE 1 - (embedding <=> %s::vector) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    
    results = await db.fetch_all(
        query,
        query_embedding,
        query_embedding,
        request.min_similarity,
        query_embedding,
        request.limit
    )
```

**Key Components**:
- ✅ **Cosine Distance Operator**: `<=>` for vector similarity
- ✅ **HNSW Index**: Fast approximate nearest neighbor search
- ✅ **Similarity Score**: `1 - (embedding <=> query)` gives 0-1 score
- ✅ **Bedrock Integration**: Cohere Embed English v3 for embeddings

---

## 🤖 2. Strands SDK Multi-Agent System

### Location: `lab2/backend/agents/`

#### A. Specialized Agents (Agents as Tools Pattern)

**`inventory_agent.py`** - Stock analysis agent:
```python
from strands import tool

@tool
def inventory_restock_agent(query: str, context: str) -> str:
    """
    Analyzes inventory levels and provides restock recommendations.
    
    Uses Strands @tool decorator to wrap agent as callable function.
    """
    system_prompt = """You are an inventory management specialist.
    Analyze stock levels and provide restock recommendations."""
    
    # Agent processes context and returns recommendations
    return agent_response
```

**`recommendation_agent.py`** - Product recommendation agent:
```python
@tool
def product_recommendation_agent(query: str, context: str) -> str:
    """
    Provides personalized product recommendations.
    
    Matches user preferences with product catalog.
    """
    system_prompt = """You are a product recommendation specialist.
    Match products to user needs and preferences."""
    
    return recommendations
```

**`pricing_agent.py`** - Pricing optimization agent:
```python
@tool
def price_optimization_agent(query: str, context: str) -> str:
    """
    Analyzes pricing and suggests deals/bundles.
    """
    system_prompt = """You are a pricing specialist.
    Identify best value products and bundle opportunities."""
    
    return pricing_analysis
```

#### B. Orchestrator Agent

**`orchestrator.py`** - Routes queries to specialized agents:
```python
from strands import Agent

def create_orchestrator():
    """
    Creates orchestrator agent that delegates to specialists.
    
    Implements "Agents as Tools" pattern.
    """
    orchestrator = Agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        tools=[
            inventory_restock_agent,
            product_recommendation_agent,
            price_optimization_agent
        ],
        system_prompt="""You are an orchestrator that routes queries:
        - Inventory queries → inventory_restock_agent
        - Product recommendations → product_recommendation_agent
        - Pricing queries → price_optimization_agent
        """
    )
    
    return orchestrator
```

**Key Strands Features**:
- ✅ **@tool Decorator**: Wraps agents as callable tools
- ✅ **Agent Class**: Creates AI agents with system prompts
- ✅ **Tool Routing**: Orchestrator selects appropriate specialist
- ✅ **Bedrock Integration**: Uses Claude 3.7 Sonnet

---

## 🔗 3. Model Context Protocol (MCP)

### Location: `lab2/backend/services/chat.py`

**Lines 70-120** - MCP client initialization:

```python
from strands.tools.mcp import MCPClient
from mcp import StdioServerParameters, stdio_client

def _create_mcp_client(self):
    """
    Creates MCP client for direct database access.
    
    Allows AI agents to query Aurora PostgreSQL directly.
    """
    # Load MCP config
    config_path = 'lab2/config/mcp-server-config.json'
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    server_config = config['mcpServers']['awslabs.postgres-mcp-server']
    
    # Create MCP client with stdio transport
    mcp_client = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command=server_config['command'],
                args=server_config['args'],
                env=server_config.get('env', {})
            )
        )
    )
    
    return mcp_client
```

**Lines 150-200** - MCP-enabled chat:

```python
async def _strands_enhanced_chat(
    self,
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Chat with MCP database access.
    """
    mcp_client = self._create_mcp_client()
    
    with mcp_client:
        # Get database tools from MCP server
        tools = mcp_client.list_tools_sync()
        
        # Create agent with database tools
        agent = Agent(
            model=self.model_id,
            tools=tools,  # MCP tools for database access
            system_prompt=self._get_system_prompt()
        )
        
        # Agent can now query database directly
        response = agent(message)
        
        # Extract products from response
        parsed = self._parse_agent_response(str(response))
        
        return {
            "response": parsed["text"],
            "products": parsed["products"],
            "suggestions": parsed["suggestions"]
        }
```

**MCP Configuration**: `lab2/config/mcp-server-config.json`

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "awslabs.postgres-mcp-server",
        "awslabs.postgres-mcp-server",
        "--resource_arn", "arn:aws:rds:...",
        "--secret_arn", "arn:aws:secretsmanager:...",
        "--database", "postgres",
        "--region", "us-west-2"
      ]
    }
  }
}
```

**Key MCP Features**:
- ✅ **Direct Database Access**: AI agents query Aurora directly
- ✅ **Stdio Transport**: Communication via stdin/stdout
- ✅ **Tool Discovery**: `list_tools_sync()` gets available database operations
- ✅ **Secure Access**: Uses AWS IAM and Secrets Manager

---

## 📊 4. Complete Flow Diagram

```
User Query: "Show me laptops under $1000"
         │
         ▼
┌────────────────────────────────────────┐
│  Frontend (React)                      │
│  POST /api/chat                        │
└────────────┬───────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  Backend Chat Service                  │
│  lab2/backend/services/chat.py         │
│                                        │
│  1. Create MCP Client                  │
│  2. Get Database Tools                 │
│  3. Create Strands Agent               │
└────────────┬───────────────────────────┘
             │
             ├─────────────┐
             ▼             ▼
    ┌────────────┐  ┌──────────────┐
    │ MCP Server │  │ Strands Agent│
    │ (Database) │  │ (Claude 3.7) │
    └─────┬──────┘  └──────┬───────┘
          │                │
          ▼                ▼
    ┌─────────────────────────────┐
    │  Aurora PostgreSQL          │
    │  • pgvector similarity      │
    │  • HNSW index               │
    │  • Cosine distance (<=>)    │
    └─────────────┬───────────────┘
                  │
                  ▼
            ┌──────────────┐
            │ Query Results│
            │ • Products   │
            │ • Similarity │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ Parse & Format│
            │ • Extract JSON│
            │ • Add metadata│
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ Return to UI │
            │ • Products   │
            │ • Suggestions│
            └──────────────┘
```

---

## 🎯 5. Key Files Reference

### pgvector Implementation
- **Search Endpoint**: `lab2/backend/app.py` (lines 200-250)
- **Database Service**: `lab2/backend/services/database.py`
- **Embedding Service**: `lab2/backend/services/embeddings.py`

### Strands SDK Implementation
- **Chat Service**: `lab2/backend/services/chat.py` (lines 150-300)
- **Inventory Agent**: `lab2/backend/agents/inventory_agent.py`
- **Recommendation Agent**: `lab2/backend/agents/recommendation_agent.py`
- **Pricing Agent**: `lab2/backend/agents/pricing_agent.py`
- **Orchestrator**: `lab2/backend/agents/orchestrator.py`

### MCP Implementation
- **MCP Client**: `lab2/backend/services/chat.py` (lines 70-120)
- **MCP Config**: `lab2/config/mcp-server-config.json`
- **Agent Integration**: `lab2/backend/services/chat.py` (lines 150-200)

### Frontend Integration
- **Chat Component**: `lab2/frontend/src/components/AIAssistant.tsx`
- **Search Overlay**: `lab2/frontend/src/components/SearchOverlay.tsx`
- **API Client**: `lab2/frontend/src/services/chat.ts`

---

## 🔧 6. Testing the Components

### Test pgvector Search
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "wireless headphones", "limit": 5}'
```

### Test MCP Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me laptops", "conversation_history": []}'
```

### Test Specialized Agents
```bash
curl -X POST "http://localhost:8000/api/agents/query?query=recommend%20laptops&agent_type=recommendation"
```

---

**Built with pgvector + Strands SDK + MCP for AWS re:Invent 2025 🚀**
