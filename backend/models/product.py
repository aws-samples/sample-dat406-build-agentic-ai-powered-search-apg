"""
DAT406 Workshop - Pydantic Models
Data models for API requests and responses
"""

from .product import Product, ProductWithScore
from .search import SearchRequest, SearchResponse, SearchResult

__all__ = [
    "Product",
    "ProductWithScore",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
]