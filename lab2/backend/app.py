"""
DAT406 Workshop - Main FastAPI Application
FastAPI app with semantic search (Lab 1) and multi-agent system (Lab 2)
"""

import time
import logging
import json
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    RecommendationRequest,
    AgentResponse,
    HealthResponse,
    ChatRequest,
    ChatResponse,
)
from models.product import Product, ProductWithScore, InventoryStats
from services.database import DatabaseService
from services.embeddings import EmbeddingService
from services.bedrock import BedrockService
from services.chat import ChatService

# Lab 2 agents use Strands SDK function pattern (not class-based)
# Agents are available via /api/agents/query endpoint
LAB2_AVAILABLE = True

# Configure logging for Strands SDK
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.INFO)

# Configure app logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Global service instances
db_service: DatabaseService = None
embedding_service: EmbeddingService = None
bedrock_service: BedrockService = None
chat_service: ChatService = None

# Lab 2 agents use function pattern - no global instances needed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting DAT406 Workshop API...")
    
    global db_service, embedding_service, bedrock_service, chat_service
    global search_agent, inventory_agent, recommendation_agent
    
    try:
        # Initialize core services
        db_service = DatabaseService()
        await db_service.connect()
        logger.info("✅ Database service initialized")
        
        embedding_service = EmbeddingService()
        logger.info("✅ Embedding service initialized")
        
        bedrock_service = BedrockService()
        logger.info("✅ Bedrock service initialized")
        
        chat_service = ChatService()
        logger.info("✅ Chat service initialized")
        
        # Set chat service logger to INFO
        logging.getLogger('services.chat').setLevel(logging.INFO)
        
        # Initialize direct MCP tools with database service reference (live data)
        from services.mcp_agent_tools import set_db_service
        set_db_service(db_service)
        logger.info("✅ Direct MCP tools initialized with live database access")
        
        # Lab 2 agents use Strands SDK function pattern
        logger.info("✅ Lab 2 agents available via /api/agents/query")
        
        logger.info("🚀 DAT406 Workshop API is ready!")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down DAT406 Workshop API...")
    
    if db_service:
        await db_service.disconnect()
    
    logger.info("👋 Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="DAT406 Workshop API",
    description="Agentic AI-Powered Search with Amazon Aurora PostgreSQL and pgvector",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
async def get_db_service() -> DatabaseService:
    """Get database service instance"""
    if not db_service:
        raise HTTPException(
            status_code=503, 
            detail="Database unavailable - check network connectivity to Aurora cluster"
        )
    return db_service


async def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    if not embedding_service:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    return embedding_service


async def get_bedrock_service() -> BedrockService:
    """Get Bedrock service instance"""
    if not bedrock_service:
        raise HTTPException(status_code=503, detail="Bedrock service not initialized")
    return bedrock_service


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "message": "DAT406 Workshop API",
        "version": "1.0.0",
        "lab1": "Semantic Search with pgvector",
        "lab2": "Multi-Agent System with MCP" if LAB2_AVAILABLE else "Not Available"
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check(
    db: DatabaseService = Depends(get_db_service),
):
    """
    Health check endpoint
    Returns status of all services
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "bedrock": "unknown",
        "mcp": "unknown" if LAB2_AVAILABLE else "not_available",
        "version": "1.0.0"
    }
    
    # Check database connection
    try:
        await db.execute_query("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"
    
    # Check Bedrock access
    try:
        embedding_service.generate_embedding("test")
        health_status["bedrock"] = "accessible"
    except Exception as e:
        logger.error(f"Bedrock health check failed: {e}")
        health_status["bedrock"] = "inaccessible"
        health_status["status"] = "degraded"
    
    # Check MCP if Lab 2 is available
    if LAB2_AVAILABLE:
        health_status["mcp"] = "available"
    
    return HealthResponse(**health_status)


# ============================================================================
# LAB 1: SEMANTIC SEARCH ENDPOINTS
# ============================================================================

@app.post("/api/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: DatabaseService = Depends(get_db_service),
    embeddings: EmbeddingService = Depends(get_embedding_service),
):
    """
    LAB 1: Semantic search endpoint using vector similarity
    
    Performs pure vector similarity search using pgvector HNSW index
    and Amazon Titan embeddings.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Semantic search: '{request.query}' (limit={request.limit})")
        
        # Generate query embedding
        query_embedding = embeddings.generate_embedding(request.query)
        logger.info(f"✅ Generated embedding vector (1024 dimensions)")
        
        # Perform vector similarity search
        query = """
            SELECT 
                "productId",
                product_description,
                imgurl,
                producturl,
                stars,
                reviews,
                price,
                category_id,
                isbestseller,
                boughtinlastmonth,
                category_name,
                quantity,
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
        
        logger.info(f"📦 Found {len(results)} products")
        
        # Convert to response model
        search_results = []
        for row in results:
            product = ProductWithScore(**dict(row))
            search_result = SearchResult(product=product)
            search_results.append(search_result)
        
        search_time_ms = (time.time() - start_time) * 1000
        logger.info(f"⚡ Search completed in {search_time_ms:.2f}ms")
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            search_time_ms=search_time_ms,
            search_type="semantic"
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get a single product by ID
    """
    try:
        query = """
            SELECT 
                "productId",
                product_description,
                imgurl,
                producturl,
                stars,
                reviews,
                price,
                category_id,
                isbestseller,
                boughtinlastmonth,
                category_name,
                quantity
            FROM bedrock_integration.product_catalog
            WHERE "productId" = $1
        """
        
        result = await db.fetch_one(query, product_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return Product(**dict(result))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch product: {str(e)}")


@app.get("/api/products/category/{category_query}")
async def browse_category(
    category_query: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: DatabaseService = Depends(get_db_service),
):
    """Fast category browsing without embeddings"""
    try:
        logger.info(f"📂 Category browse: '{category_query}' (limit={limit})")
        
        query = """
            SELECT 
                "productId",
                product_description,
                imgurl,
                producturl,
                stars,
                reviews,
                price,
                category_name,
                quantity,
                1.0 as similarity_score
            FROM bedrock_integration.product_catalog
            WHERE (category_name ILIKE %s OR product_description ILIKE %s)
              AND quantity > 0
            ORDER BY stars DESC, reviews DESC
            LIMIT %s
        """
        
        results = await db.fetch_all(query, f"%{category_query}%", f"%{category_query}%", limit)
        logger.info(f"📦 Found {len(results)} products in category")
        
        return {
            "results": [
                {
                    "product": dict(row),
                    "similarity_score": 1.0
                }
                for row in results
            ],
            "total_results": len(results),
            "search_type": "category"
        }
    except Exception as e:
        logger.error(f"❌ Category browse failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products", response_model=List[Product])
async def list_products(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: str = Query(default=None),
    min_stars: float = Query(default=None, ge=0, le=5),
    max_price: float = Query(default=None, ge=0),
    db: DatabaseService = Depends(get_db_service),
):
    """
    List products with optional filters
    """
    try:
        # Build dynamic query
        conditions = []
        params = []
        param_count = 1
        
        if category:
            conditions.append(f"category_name = ${param_count}")
            params.append(category)
            param_count += 1
        
        if min_stars is not None:
            conditions.append(f"stars >= ${param_count}")
            params.append(min_stars)
            param_count += 1
        
        if max_price is not None:
            conditions.append(f"price <= ${param_count}")
            params.append(max_price)
            param_count += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT 
                "productId",
                product_description,
                imgurl,
                producturl,
                stars,
                reviews,
                price,
                category_id,
                isbestseller,
                boughtinlastmonth,
                category_name,
                quantity
            FROM bedrock_integration.product_catalog
            {where_clause}
            ORDER BY reviews DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        params.extend([limit, offset])
        results = await db.fetch_all(query, *params)
        
        return [Product(**dict(row)) for row in results]
        
    except Exception as e:
        logger.error(f"Failed to list products: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


# ============================================================================
# LAB 2: MULTI-AGENT ENDPOINTS (Optional)
# ============================================================================

# Lab 2 agents use Strands SDK function pattern - available via /api/agents/query
# No class-based agent endpoints needed


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/api/mcp/tools")
async def list_mcp_tools(
    db: DatabaseService = Depends(get_db_service)
):
    """List all custom MCP tools available"""
    try:
        from services.mcp_database import CustomMCPTools
        mcp_tools = CustomMCPTools(db)
        return await mcp_tools.list_custom_tools()
    except Exception as e:
        logger.error(f"Failed to list MCP tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/trending")
async def get_trending(
    limit: int = Query(default=10, ge=1, le=50),
    db: DatabaseService = Depends(get_db_service)
):
    """Get trending products using custom MCP tool"""
    try:
        from services.mcp_database import CustomMCPTools
        mcp_tools = CustomMCPTools(db)
        return await mcp_tools.get_trending_products(limit)
    except Exception as e:
        logger.error(f"Failed to get trending products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/inventory-health")
async def get_inventory_health_endpoint(
    db: DatabaseService = Depends(get_db_service)
):
    """Get inventory health using custom MCP tool"""
    try:
        from services.mcp_database import CustomMCPTools
        mcp_tools = CustomMCPTools(db)
        return await mcp_tools.get_inventory_health()
    except Exception as e:
        logger.error(f"Failed to get inventory health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp/price-stats")
async def get_price_stats(
    category: str = Query(default=None),
    db: DatabaseService = Depends(get_db_service)
):
    """Get price statistics using custom MCP tool"""
    try:
        from services.mcp_database import CustomMCPTools
        mcp_tools = CustomMCPTools(db)
        return await mcp_tools.get_price_statistics(category)
    except Exception as e:
        logger.error(f"Failed to get price statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mcp/restock")
async def restock_product_endpoint(
    request: dict,
    db: DatabaseService = Depends(get_db_service)
):
    """Restock a product using custom MCP tool"""
    try:
        from services.mcp_database import CustomMCPTools
        mcp_tools = CustomMCPTools(db)
        return await mcp_tools.restock_product(
            product_id=request["product_id"],
            quantity=request["quantity"]
        )
    except Exception as e:
        logger.error(f"Failed to restock product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint with Aurora AI using Strands SDK and MCP
    """
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")
    
    try:
        # Convert conversation history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
        
        # Get chat response
        response = await chat_service.chat(
            message=request.message,
            conversation_history=history
        )
        
        return ChatResponse(**response)
        
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint - sends agent thinking process in real-time
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")
    
    async def event_generator():
        try:
            # Send initial event
            data = json.dumps({'type': 'start', 'content': 'Initializing agent...'})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.1)
            
            # Send orchestrator step
            data = json.dumps({'type': 'agent_step', 'agent': 'Orchestrator', 'action': 'Analyzing query and routing to specialists', 'status': 'in_progress'})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.3)
            
            # Determine which agent to use
            query_lower = request.message.lower()
            if 'inventory' in query_lower or 'stock' in query_lower or 'restock' in query_lower:
                agent_name = 'Inventory Agent'
                agent_action = 'Analyzing stock levels and inventory health'
            elif 'recommend' in query_lower or 'suggest' in query_lower or 'need' in query_lower:
                agent_name = 'Recommendation Agent'
                agent_action = 'Finding matching products'
            elif 'price' in query_lower or 'deal' in query_lower:
                agent_name = 'Pricing Agent'
                agent_action = 'Analyzing prices and deals'
            else:
                agent_name = 'Search Agent'
                agent_action = 'Searching product catalog'
            
            # Send specialist agent step
            data = json.dumps({'type': 'agent_step', 'agent': agent_name, 'action': agent_action, 'status': 'in_progress'})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.2)
            
            # Send tool call event
            data = json.dumps({'type': 'tool_call', 'tool': 'run_query', 'status': 'executing'})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.3)
            
            # Get actual response
            history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
            response = await chat_service.chat(
                message=request.message,
                conversation_history=history
            )
            
            # Send completion event
            data = json.dumps({'type': 'agent_step', 'agent': agent_name, 'action': agent_action, 'status': 'completed'})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.1)
            
            # Stream response content word by word
            words = response['response'].split(' ')
            current_text = ''
            for i, word in enumerate(words):
                current_text += word + ' '
                data = json.dumps({'type': 'content', 'content': current_text.strip()})
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.03)  # 30ms delay between words
            
            # Send final response with all data
            data = json.dumps({'type': 'complete', 'response': response})
            yield f"data: {data}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}")
            data = json.dumps({'type': 'error', 'error': str(e)})
            yield f"data: {data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/agents/query")
async def agent_query(
    query: str,
    agent_type: str = "orchestrator",
    enable_thinking: bool = False,
    db: DatabaseService = Depends(get_db_service)
):
    """
    Query specialized agents (inventory, recommendation, pricing)
    Uses custom MCP tools to provide data to agents
    
    Args:
        query: User query
        agent_type: Type of agent (orchestrator, inventory, recommendation, pricing)
        enable_thinking: Enable Claude Sonnet 4's extended thinking (default: False)
    """
    try:
        from agents.orchestrator import create_orchestrator
        from agents.inventory_agent import inventory_restock_agent
        from agents.recommendation_agent import product_recommendation_agent
        from agents.pricing_agent import price_optimization_agent
        
        # Agents now handle their own tool calls - no need to pre-fetch context
        if agent_type == "orchestrator":
            orchestrator = create_orchestrator(enable_interleaved_thinking=enable_thinking)
            response = orchestrator(query)
        elif agent_type == "inventory":
            response = inventory_restock_agent(query)
        elif agent_type == "recommendation":
            response = product_recommendation_agent(query)
        elif agent_type == "pricing":
            response = price_optimization_agent(query)
        else:
            raise HTTPException(status_code=400, detail="Invalid agent type")
        
        return {
            "response": str(response),
            "agent_type": agent_type,
            "success": True,
            "note": "Agents use live database tools for fresh data"
        }
        
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")
