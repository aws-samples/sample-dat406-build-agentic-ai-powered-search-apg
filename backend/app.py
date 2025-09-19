#!/usr/bin/env python3
"""
FastAPI backend for Blaize Bazaar
Updated for psycopg3 and us-west-2 region with correct model IDs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import boto3
import numpy as np
import os
import logging

# Use psycopg3 (from Lambda layer)
try:
    import psycopg
    from psycopg.rows import dict_row
    USING_PSYCOPG3 = True
except ImportError:
    # Fallback to psycopg2 for local testing
    import psycopg2 as psycopg
    from psycopg2.extras import RealDictCursor
    USING_PSYCOPG3 = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Blaize Bazaar API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global database connection
db_conn = None
bedrock_client = None

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None

class Product(BaseModel):
    product_id: str
    product_description: str
    img_url: Optional[str]
    price: float
    stars: float
    reviews: int
    category_name: str
    is_best_seller: bool
    quantity: int
    similarity_score: Optional[float] = None

class SearchResponse(BaseModel):
    products: List[Product]
    query_time_ms: float
    total_results: int

class RAGRequest(BaseModel):
    query: str
    max_context_items: int = 5

class RAGResponse(BaseModel):
    answer: str
    context_items: List[Dict]
    query_time_ms: float

# Database connection
def get_db_connection():
    """Get or create database connection using psycopg3"""
    global db_conn
    if db_conn is None or db_conn.closed:
        if os.environ.get('DB_SECRET_ARN'):
            # Get from Secrets Manager
            sm_client = boto3.client('secretsmanager', region_name='us-west-2')
            secret = sm_client.get_secret_value(SecretId=os.environ['DB_SECRET_ARN'])
            config = json.loads(secret['SecretString'])
            conn_str = f"host={config['host']} port={config['port']} dbname={config.get('dbname', 'postgres')} user={config['username']} password={config['password']}"
        else:
            # Get from environment variables
            conn_str = f"host={os.environ.get('PGHOST', 'localhost')} port={os.environ.get('PGPORT', 5432)} dbname={os.environ.get('PGDATABASE', 'postgres')} user={os.environ.get('PGUSER', 'postgres')} password={os.environ.get('PGPASSWORD', '')}"
        
        db_conn = psycopg.connect(conn_str)
    return db_conn

def get_bedrock_client():
    """Get Bedrock client for us-west-2"""
    global bedrock_client
    if bedrock_client is None:
        bedrock_client = boto3.client(
            'bedrock-runtime', 
            region_name='us-west-2'
        )
    return bedrock_client

def get_cursor(conn):
    """Get cursor with proper row factory based on psycopg version"""
    if USING_PSYCOPG3:
        return conn.cursor(row_factory=dict_row)
    else:
        return conn.cursor(cursor_factory=RealDictCursor)

def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Amazon Titan"""
    try:
        client = get_bedrock_client()
        response = client.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            body=json.dumps({
                'inputText': text[:8000]
            })
        )
        result = json.loads(response['body'].read())
        return result['embedding']
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return [0.0] * 1024

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    try:
        get_db_connection()
        get_bedrock_client()
        logger.info("API server started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Blaize Bazaar API", "region": "us-west-2"}

@app.post("/api/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Perform semantic search on products using pgvector
    """
    import time
    start_time = time.time()
    
    # Generate embedding for query
    query_embedding = generate_embedding(request.query)
    
    # Build SQL query with filters
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    sql = """
        SELECT 
            product_id,
            product_description,
            img_url,
            price,
            stars,
            reviews,
            category_name,
            is_best_seller,
            quantity,
            1 - (embedding <=> %s::vector) as similarity_score
        FROM products
        WHERE embedding IS NOT NULL
    """
    
    params = [query_embedding]
    
    # Add filters
    if request.category:
        sql += " AND category_name = %s"
        params.append(request.category)
    
    if request.min_price is not None:
        sql += " AND price >= %s"
        params.append(request.min_price)
    
    if request.max_price is not None:
        sql += " AND price <= %s"
        params.append(request.max_price)
    
    if request.min_rating is not None:
        sql += " AND stars >= %s"
        params.append(request.min_rating)
    
    sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
    params.extend([query_embedding, request.limit])
    
    try:
        cur.execute(sql, params)
        results = cur.fetchall()
        
        products = [Product(**row) for row in results]
        
        # Get total count
        count_sql = "SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL"
        cur.execute(count_sql)
        result = cur.fetchone()
        total = result['count'] if isinstance(result, dict) else result[0]
        
        query_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            products=products,
            query_time_ms=query_time,
            total_results=total
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@app.get("/api/products/categories")
async def get_categories():
    """Get all product categories"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    try:
        cur.execute("""
            SELECT DISTINCT category_name, COUNT(*) as product_count
            FROM products
            WHERE category_name IS NOT NULL
            GROUP BY category_name
            ORDER BY product_count DESC
        """)
        return cur.fetchall()
    finally:
        cur.close()

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    try:
        stats = {}
        
        # Get various statistics
        queries = {
            'total_products': "SELECT COUNT(*) as count FROM products",
            'products_with_embeddings': "SELECT COUNT(*) as count FROM products WHERE embedding IS NOT NULL",
            'avg_price': "SELECT AVG(price) as avg FROM products",
            'avg_rating': "SELECT AVG(stars) as avg FROM products",
            'total_categories': "SELECT COUNT(DISTINCT category_name) as count FROM products",
            'best_sellers': "SELECT COUNT(*) as count FROM products WHERE is_best_seller = true"
        }
        
        for key, query in queries.items():
            try:
                cur.execute(query)
                result = cur.fetchone()
                if isinstance(result, dict):
                    stats[key] = result.get('count') or result.get('avg') or 0
                else:
                    stats[key] = result[0] if result else 0
            except:
                stats[key] = 0
        
        return stats
    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        return {
            'total_products': 0,
            'products_with_embeddings': 0,
            'avg_price': 0,
            'avg_rating': 0,
            'total_categories': 0,
            'best_sellers': 0
        }
    finally:
        cur.close()

@app.post("/api/rag", response_model=RAGResponse)
async def rag_query(request: RAGRequest):
    """
    Perform RAG (Retrieval Augmented Generation) query
    """
    import time
    start_time = time.time()
    
    # Get relevant products using semantic search
    query_embedding = generate_embedding(request.query)
    
    conn = get_db_connection()
    cur = get_cursor(conn)
    
    # Retrieve relevant context
    cur.execute("""
        SELECT 
            product_id,
            product_description,
            price,
            stars,
            reviews,
            category_name
        FROM products
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, request.max_context_items))
    
    context_items = cur.fetchall()
    
    # Build context string
    context = "\n".join([
        f"Product: {item['product_description']}, Price: ${item['price']}, Rating: {item['stars']} stars, Category: {item['category_name']}"
        for item in context_items
    ])
    
    # Generate response using Claude via Bedrock
    try:
        client = get_bedrock_client()
        
        prompt = f"""Based on the following product information, answer the user's question.

Context:
{context}

User Question: {request.query}

Please provide a helpful and accurate answer based on the product information provided."""
        
        # Use the correct Claude model ID for us-west-2
        response = client.invoke_model(
            modelId='us.anthropic.claude-3-7-sonnet-20250219-v1:0',
            body=json.dumps({
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 500,
                'temperature': 0.7,
                'anthropic_version': 'bedrock-2023-05-31'
            })
        )
        
        result = json.loads(response['body'].read())
        answer = result['content'][0]['text']
        
        query_time = (time.time() - start_time) * 1000
        
        return RAGResponse(
            answer=answer,
            context_items=context_items,
            query_time_ms=query_time
        )
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        # Return a fallback response
        return RAGResponse(
            answer="I'm unable to process your question at the moment. Please try again.",
            context_items=context_items,
            query_time_ms=(time.time() - start_time) * 1000
        )
    finally:
        cur.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)