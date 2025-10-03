"""
DAT406 Workshop - Main FastAPI Application
FastAPI app with semantic search (Lab 1) and multi-agent system (Lab 2)
"""

import time
import logging
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

# Lab 2 imports (optional)
try:
    from agents.search_agent import SearchAgent  # type: ignore
    from agents.inventory_agent import InventoryAgent  # type: ignore
    from agents.recommendation_agent import RecommendationAgent  # type: ignore
    LAB2_AVAILABLE = True
except ImportError:
    LAB2_AVAILABLE = False
    logging.warning("Lab 2 agents not available - MCP features disabled")

# Configure logging for Strands SDK
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)

# Configure app logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Global service instances
db_service: DatabaseService = None
embedding_service: EmbeddingService = None
bedrock_service: BedrockService = None
chat_service: ChatService = None

# Lab 2 agents (optional)
search_agent = None  # type: ignore
inventory_agent = None  # type: ignore
recommendation_agent = None  # type: ignore


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
        
        # Initialize Lab 2 agents if available
        if LAB2_AVAILABLE:
            try:
                search_agent = SearchAgent(db_service, embedding_service)
                inventory_agent = InventoryAgent(db_service)
                recommendation_agent = RecommendationAgent(db_service, embedding_service)
                logger.info("✅ Lab 2 agents initialized")
            except Exception as e:
                logger.warning(f"Lab 2 agents initialization failed: {e}")
        
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
    if LAB2_AVAILABLE and search_agent:
        try:
            # Simple check that agent is initialized
            health_status["mcp"] = "connected"
        except Exception:
            health_status["mcp"] = "disconnected"
    
    return HealthResponse(**health_status)


# ============================================================================
# LAB 1: SEMANTIC SEARCH ENDPOINTS
# ============================================================================

@app.get("/api/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=5, ge=1, le=10),
    db: DatabaseService = Depends(get_db_service),
):
    """Fast autocomplete using trigram similarity"""
    try:
        query = """
            SELECT DISTINCT 
                LEFT(product_description, 60) as suggestion,
                category_name
            FROM bedrock_integration.product_catalog
            WHERE product_description ILIKE %s
            LIMIT %s
        """
        
        results = await db.fetch_all(query, f"%{q}%", limit)
        
        return {
            "suggestions": [
                {"text": dict(r)["suggestion"], "category": dict(r)["category_name"]}
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Autocomplete failed: {e}")
        return {"suggestions": []}


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
        # Generate query embedding
        query_embedding = embeddings.generate_embedding(request.query)
        
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
        
        # Convert to response model
        search_results = []
        for row in results:
            product = ProductWithScore(**dict(row))
            search_result = SearchResult(product=product)
            search_results.append(search_result)
        
        search_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            search_time_ms=search_time_ms,
            search_type="semantic"
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
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
        logger.error(f"Category browse failed: {e}")
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

if LAB2_AVAILABLE:
    
    @app.post("/api/agent/search", response_model=AgentResponse)
    async def agent_search(
        request: SearchRequest,
    ):
        """
        LAB 2: Agent-based search using MCP
        """
        if not search_agent:
            raise HTTPException(status_code=503, detail="Search agent not available")
        
        start_time = time.time()
        
        try:
            response = await search_agent.search(
                query=request.query,
                limit=request.limit
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return AgentResponse(
                agent_name="SearchAgent",
                response=response.get("message", "Search completed"),
                data=response.get("data"),
                execution_time_ms=execution_time_ms,
                tools_used=response.get("tools_used", [])
            )
            
        except Exception as e:
            logger.error(f"Agent search failed: {e}")
            raise HTTPException(status_code=500, detail=f"Agent search failed: {str(e)}")
    
    
    @app.get("/api/inventory/analyze", response_model=AgentResponse)
    async def analyze_inventory():
        """
        LAB 2: Analyze inventory using inventory agent
        """
        if not inventory_agent:
            raise HTTPException(status_code=503, detail="Inventory agent not available")
        
        start_time = time.time()
        
        try:
            response = await inventory_agent.analyze_inventory()
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return AgentResponse(
                agent_name="InventoryAgent",
                response=response.get("message", "Analysis completed"),
                data=response.get("data"),
                execution_time_ms=execution_time_ms,
                tools_used=response.get("tools_used", [])
            )
            
        except Exception as e:
            logger.error(f"Inventory analysis failed: {e}")
            raise HTTPException(status_code=500, detail=f"Inventory analysis failed: {str(e)}")
    
    
    @app.get("/api/inventory/low-stock", response_model=List[Product])
    async def get_low_stock(
        threshold: int = Query(default=10, ge=0),
        db: DatabaseService = Depends(get_db_service),
    ):
        """
        LAB 2: Get products with low stock
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
                WHERE quantity <= $1 AND quantity > 0
                ORDER BY quantity ASC, reviews DESC
                LIMIT 50
            """
            
            results = await db.fetch_all(query, threshold)
            
            return [Product(**dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to fetch low stock products: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch low stock: {str(e)}")
    
    
    @app.post("/api/recommendations", response_model=List[ProductWithScore])
    async def get_recommendations(
        request: RecommendationRequest,
    ):
        """
        LAB 2: Get product recommendations using recommendation agent
        """
        if not recommendation_agent:
            raise HTTPException(status_code=503, detail="Recommendation agent not available")
        
        try:
            recommendations = await recommendation_agent.get_recommendations(
                product_id=request.productId,
                limit=request.limit,
                exclude_same=request.exclude_same_product
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendations failed: {e}")
            raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")


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


@app.post("/api/agents/query")
async def agent_query(
    query: str,
    agent_type: str = "orchestrator",
    db: DatabaseService = Depends(get_db_service)
):
    """
    Query specialized agents (inventory, recommendation, pricing)
    """
    try:
        from agents.orchestrator import create_orchestrator
        from agents.inventory_agent import inventory_restock_agent
        from agents.recommendation_agent import product_recommendation_agent
        from agents.pricing_agent import price_optimization_agent
        
        # Get relevant context from database based on query
        context = ""
        
        # Extract category/product type from query
        query_lower = query.lower()
        category_filter = ""
        
        # Detect product categories
        if any(word in query_lower for word in ["headphone", "earbud", "audio"]):
            category_filter = "AND category_name ILIKE '%Headphones%'"
        elif any(word in query_lower for word in ["laptop", "computer", "pc"]):
            category_filter = "AND (category_name ILIKE '%Computer%' OR category_name ILIKE '%Tablet%' OR product_description ILIKE '%laptop%')"
        elif any(word in query_lower for word in ["phone", "smartphone", "mobile"]):
            category_filter = "AND (category_name ILIKE '%Phone%' OR product_description ILIKE '%phone%')"
        
        if "inventory" in query_lower or "stock" in query_lower or "restock" in query_lower:
            stock_query = f"""
                SELECT "productId", product_description, quantity, stars, reviews, price, category_name
                FROM bedrock_integration.product_catalog
                WHERE quantity < 20 {category_filter}
                ORDER BY stars DESC, reviews DESC
                LIMIT 15
            """
            results = await db.fetch_all(stock_query)
            context = "\n".join([f"{dict(r)}" for r in results])
        elif "recommend" in query_lower or "suggest" in query_lower or "need" in query_lower:
            rec_query = f"""
                SELECT "productId", product_description, price, stars, reviews, category_name, imgurl
                FROM bedrock_integration.product_catalog
                WHERE stars >= 4.0 AND quantity > 0 {category_filter}
                ORDER BY stars DESC, reviews DESC
                LIMIT 25
            """
            results = await db.fetch_all(rec_query)
            context = "\n".join([f"{dict(r)}" for r in results])
        elif "price" in query_lower or "deal" in query_lower or "bundle" in query_lower:
            price_query = f"""
                SELECT "productId", product_description, price, stars, reviews, category_name
                FROM bedrock_integration.product_catalog
                WHERE quantity > 0 {category_filter}
                ORDER BY stars DESC, reviews DESC
                LIMIT 25
            """
            results = await db.fetch_all(price_query)
            context = "\n".join([f"{dict(r)}" for r in results])
        
        # Use orchestrator or specific agent (always pass context)
        if agent_type == "orchestrator":
            # Orchestrator will call specialized agents with context
            if "inventory" in query.lower() or "stock" in query.lower():
                response = inventory_restock_agent(query, context)
            elif "recommend" in query.lower() or "suggest" in query.lower():
                response = product_recommendation_agent(query, context)
            elif "price" in query.lower() or "deal" in query.lower():
                response = price_optimization_agent(query, context)
            else:
                orchestrator = create_orchestrator()
                response = orchestrator(query)
        elif agent_type == "inventory":
            response = inventory_restock_agent(query, context)
        elif agent_type == "recommendation":
            response = product_recommendation_agent(query, context)
        elif agent_type == "pricing":
            response = price_optimization_agent(query, context)
        else:
            raise HTTPException(status_code=400, detail="Invalid agent type")
        
        return {
            "response": str(response),
            "agent_type": agent_type,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")
