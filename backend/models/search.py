"""
Search request and response models
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .product import ProductWithScore


class SearchRequest(BaseModel):
    """Search request model for Lab 1 semantic search"""
    
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Search query text"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    min_similarity: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Minimum similarity score threshold (0-1)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "wireless headphones with noise cancellation",
                "limit": 10,
                "min_similarity": 0.6
            }
        }


class SearchResult(BaseModel):
    """Individual search result"""
    
    product: ProductWithScore
    explanation: Optional[str] = Field(
        None, 
        description="Optional explanation of why this result matches"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "product": {
                    "productId": "B07XYZ1234",
                    "product_description": "Premium wireless headphones",
                    "stars": 4.5,
                    "price": 199.99,
                    "similarity_score": 0.89
                },
                "explanation": "High relevance match for 'wireless headphones'"
            }
        }


class SearchResponse(BaseModel):
    """Search response model containing results and metadata"""
    
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results found")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    search_type: str = Field(
        default="semantic",
        description="Type of search performed (semantic, agent, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "wireless headphones",
                "results": [
                    {
                        "product": {
                            "productId": "B07XYZ1234",
                            "product_description": "Premium wireless headphones",
                            "stars": 4.5,
                            "price": 199.99,
                            "similarity_score": 0.89
                        }
                    }
                ],
                "total_results": 10,
                "search_time_ms": 45.3,
                "search_type": "semantic"
            }
        }


class RecommendationRequest(BaseModel):
    """Recommendation request model for Lab 2"""
    
    productId: str = Field(..., description="Product ID to base recommendations on")
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of recommendations to return"
    )
    exclude_same_product: bool = Field(
        default=True,
        description="Whether to exclude the input product from results"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "productId": "B07XYZ1234",
                "limit": 5,
                "exclude_same_product": True
            }
        }


class AgentResponse(BaseModel):
    """Response from multi-agent system (Lab 2)"""
    
    agent_name: str = Field(..., description="Name of the agent that processed the request")
    response: str = Field(..., description="Agent's response text")
    data: Optional[dict] = Field(None, description="Structured data from agent")
    execution_time_ms: float = Field(..., description="Agent execution time in milliseconds")
    tools_used: List[str] = Field(default_factory=list, description="List of tools/MCP functions used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "InventoryAgent",
                "response": "Found 42 products with low stock requiring attention",
                "data": {
                    "low_stock_products": 42,
                    "categories_affected": ["Electronics", "Books"]
                },
                "execution_time_ms": 234.5,
                "tools_used": ["query_database", "analyze_inventory"]
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")
    bedrock: str = Field(..., description="Bedrock service status")
    mcp: Optional[str] = Field(None, description="MCP server status (Lab 2)")
    version: str = Field(..., description="API version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "database": "connected",
                "bedrock": "accessible",
                "mcp": "connected",
                "version": "1.0.0"
            }
        }