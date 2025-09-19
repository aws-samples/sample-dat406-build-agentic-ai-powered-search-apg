#!/usr/bin/env python3
"""
FastAPI backend for Blaize Bazaar
Provides REST API for product search, RAG, and agent capabilities
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Blaize Bazaar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Blaize Bazaar API"}

@app.get("/api/stats")
async def get_stats():
    return {
        "total_products": 0,
        "products_with_embeddings": 0,
        "avg_price": 0,
        "avg_rating": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
