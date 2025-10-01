#!/bin/bash
# ==============================================================================
# DAT406 Workshop - Complete Project Setup Script
# ==============================================================================
# Run this script from inside your project root directory:
#   cd sample-dat406-build-agentic-ai-powered-search-apg
#   bash setup-all.sh
# ==============================================================================

set -euo pipefail

echo "=============================================================="
echo "  DAT406 Workshop - Complete Project Setup"
echo "=============================================================="
echo ""

# Verify we're in the right place
if [[ ! $(basename "$PWD") == "sample-dat406-build-agentic-ai-powered-search-apg" ]]; then
    echo "❌ ERROR: Please run this script from inside the project root:"
    echo "   cd sample-dat406-build-agentic-ai-powered-search-apg"
    echo "   bash setup-all.sh"
    exit 1
fi

echo "✅ Running from correct directory: $PWD"
echo ""

# ==============================================================================
# STEP 1: CREATE DIRECTORY STRUCTURE
# ==============================================================================

echo "📁 Creating directory structure..."

mkdir -p scripts
mkdir -p data
mkdir -p backend/{agents,mcp,services,models,tests}
mkdir -p frontend/src/{components,services,hooks}

echo "✅ Directories created"
echo ""

# ==============================================================================
# STEP 2: CREATE ROOT FILES
# ==============================================================================

echo "📝 Creating root files..."

# .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
venv/
env/
ENV/

# Environment variables
.env
.env.local
.env.*.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*

# Frontend build
dist/
dist-ssr/
*.local

# Testing
.coverage
htmlcov/
.pytest_cache/
coverage/

# Jupyter Notebook
.ipynb_checkpoints/

# Temporary files
*.tmp
tmp/
temp/
EOF

echo "✅ Created .gitignore"

# LICENSE
cat > LICENSE << 'EOF'
MIT No Attribution

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
EOF

echo "✅ Created LICENSE"

# ==============================================================================
# STEP 3: CREATE BACKEND FILES
# ==============================================================================

echo ""
echo "📦 Creating backend files..."

# backend/__init__.py
cat > backend/__init__.py << 'EOF'
"""
DAT406 Workshop - Backend Package
"""

__version__ = "1.0.0"
EOF

# backend/requirements.txt
cat > backend/requirements.txt << 'EOF'
# DAT406 Workshop - Backend Dependencies
# Python 3.13+

# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
psycopg[binary,pool]==3.1.18
pgvector==0.2.5
sqlalchemy==2.0.25

# AWS SDK
boto3==1.34.34
botocore==1.34.34

# AI/ML Agents
strands-agents==0.1.0

# Data Processing
pandas==2.2.0
numpy==1.26.3

# Configuration
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0

# HTTP Client
httpx==0.26.0
requests==2.31.0

# Utilities
python-json-logger==2.0.7
tenacity==8.2.3

# Development
pytest==7.4.4
pytest-asyncio==0.23.3
black==24.1.1
flake8==7.0.0
mypy==1.8.0
EOF

# backend/.env.example
cat > backend/.env.example << 'EOF'
# DAT406 Workshop - Backend Environment Variables
# Copy this file to .env and fill in your actual values

# ============================================================
# Database Configuration
# ============================================================
DB_HOST=your-cluster.cluster-xxxxx.us-west-2.rds.amazonaws.com
DB_PORT=5432
DB_NAME=workshop_db
DB_USER=postgres
DB_PASSWORD=your-secure-password

# Full connection URL (alternative to individual params)
DATABASE_URL=postgresql://postgres:password@host:5432/workshop_db

# Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# ============================================================
# AWS Configuration
# ============================================================
AWS_REGION=us-west-2
AWS_DEFAULT_REGION=us-west-2

# Aurora Cluster ARN (for RDS Data API if needed)
DB_CLUSTER_ARN=arn:aws:rds:us-west-2:123456789012:cluster:apg-pgvector-dat406

# Secrets Manager (for credential rotation)
DB_SECRET_ARN=arn:aws:secretsmanager:us-west-2:123456789012:secret:apg-pgvector-secret-dat406

# ============================================================
# Amazon Bedrock Configuration
# ============================================================

# Embedding Model (Lab 1: Semantic Search)
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_EMBEDDING_DIMENSIONS=1024

# Chat/LLM Model (Lab 2: Agents)
BEDROCK_CHAT_MODEL=us.anthropic.claude-sonnet-3-7-20250219-v1:0

# Model Parameters
BEDROCK_TEMPERATURE=0.3
BEDROCK_MAX_TOKENS=2048
BEDROCK_TOP_P=0.9

# ============================================================
# Strands Agents Configuration (Lab 2)
# ============================================================
STRANDS_MODEL_ID=us.anthropic.claude-sonnet-3-7-20250219-v1:0
STRANDS_TEMPERATURE=0.3
STRANDS_MAX_TOKENS=2048

# Agent Timeout (seconds)
AGENT_TIMEOUT=30

# ============================================================
# Application Configuration
# ============================================================

# Environment (development, staging, production)
ENVIRONMENT=development

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# CORS Settings (comma-separated origins)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============================================================
# Search Configuration (Lab 1)
# ============================================================

# Vector Search
VECTOR_SEARCH_LIMIT=20
VECTOR_SIMILARITY_THRESHOLD=0.5

# HNSW Index Parameters
HNSW_M=16
HNSW_EF_CONSTRUCTION=64
HNSW_EF_SEARCH=40
EOF

echo "✅ Created backend root files"

# ==============================================================================
# STEP 4: CREATE BACKEND CONFIG
# ==============================================================================

cat > backend/config.py << 'EOFCONFIG'
"""
DAT406 Workshop - Backend Configuration
Centralized configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    db_host: str = Field(..., description="Aurora PostgreSQL cluster endpoint")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="workshop_db", description="Database name")
    db_user: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")
    
    db_pool_size: int = Field(default=10, description="Connection pool size")
    db_max_overflow: int = Field(default=20, description="Max pool overflow")
    db_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    db_pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    
    database_url: Optional[str] = Field(default=None, description="Full database URL")
    
    @property
    def db_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    # AWS Configuration
    aws_region: str = Field(default="us-west-2", description="AWS region")
    aws_default_region: str = Field(default="us-west-2", description="Default AWS region")
    
    db_cluster_arn: Optional[str] = Field(default=None, description="Aurora cluster ARN")
    db_secret_arn: Optional[str] = Field(default=None, description="Secrets Manager ARN")
    
    # Amazon Bedrock Configuration
    bedrock_embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Bedrock embedding model ID"
    )
    bedrock_embedding_dimensions: int = Field(
        default=1024,
        description="Embedding vector dimensions"
    )
    
    bedrock_chat_model: str = Field(
        default="us.anthropic.claude-sonnet-3-7-20250219-v1:0",
        description="Bedrock chat model ID"
    )
    
    bedrock_temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    bedrock_max_tokens: int = Field(default=2048, gt=0)
    bedrock_top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    
    # Strands Agents Configuration (Lab 2)
    strands_model_id: str = Field(
        default="us.anthropic.claude-sonnet-3-7-20250219-v1:0"
    )
    strands_temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    strands_max_tokens: int = Field(default=2048, gt=0)
    agent_timeout: int = Field(default=30, gt=0)
    
    # Application Configuration
    environment: str = Field(default="development")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, gt=0, lt=65536)
    api_workers: int = Field(default=4, gt=0)
    
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # Search Configuration (Lab 1)
    vector_search_limit: int = Field(default=20, gt=0)
    vector_similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    
    hnsw_m: int = Field(default=16, gt=0)
    hnsw_ef_construction: int = Field(default=64, gt=0)
    hnsw_ef_search: int = Field(default=40, gt=0)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == "development"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()
EOFCONFIG

echo "✅ Created backend/config.py"

# ==============================================================================
# STEP 5: CREATE MODELS PACKAGE
# ==============================================================================

echo "📦 Creating models package..."

# Continue in next part due to length...
cat > backend/models/__init__.py << 'EOF'
"""
DAT406 Workshop - Models Package
"""

from .product import (
    Product,
    ProductBase,
    ProductWithEmbedding,
    SearchResult,
    ProductSummary,
    ProductInventory,
    ProductCreate,
    ProductUpdate,
    ProductStats
)

from .search import (
    SearchType,
    SearchRequest,
    SearchResponse,
    SimilarProductsRequest,
    SimilarProductsResponse,
    HealthCheck,
    ErrorResponse
)

__all__ = [
    "Product",
    "ProductBase", 
    "ProductWithEmbedding",
    "SearchResult",
    "ProductSummary",
    "ProductInventory",
    "ProductCreate",
    "ProductUpdate",
    "ProductStats",
    "SearchType",
    "SearchRequest",
    "SearchResponse",
    "SimilarProductsRequest",
    "SimilarProductsResponse",
    "HealthCheck",
    "ErrorResponse"
]
EOF

echo "✅ Created backend/models/__init__.py"
echo "⏳ Creating large model files (this takes a moment)..."

# Due to length, I'll create a separate script for the large files
# Let me continue with a modular approach...

cat > backend/models/product.py << 'EOFPROD'
"""DAT406 Workshop - Product Models"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from decimal import Decimal


class ProductBase(BaseModel):
    """Base product model"""
    
    product_id: str = Field(..., alias="productId")
    product_description: str = Field(...)
    price: Decimal = Field(..., ge=0)
    stars: Optional[Decimal] = Field(None, ge=0, le=5)
    reviews: Optional[int] = Field(None, ge=0)
    category_name: Optional[str] = None
    category_id: Optional[int] = None
    
    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }


class Product(ProductBase):
    """Full product model"""
    
    imgurl: Optional[str] = Field(None, alias="imgUrl")
    producturl: Optional[str] = Field(None, alias="productURL")
    isbestseller: Optional[bool] = Field(None, alias="isBestSeller")
    boughtinlastmonth: Optional[int] = Field(None, alias="boughtInLastMonth", ge=0)
    quantity: Optional[int] = Field(None, ge=0)


class ProductWithEmbedding(Product):
    """Product with embedding vector"""
    embedding: Optional[List[float]] = None


class SearchResult(Product):
    """Search result with similarity score"""
    similarity_score: float = Field(..., ge=0, le=1)
    rank: Optional[int] = Field(None, ge=1)


class ProductSummary(BaseModel):
    """Lightweight product summary"""
    product_id: str = Field(..., alias="productId")
    product_description: str = Field(..., max_length=200)
    price: Decimal
    stars: Optional[Decimal] = None
    
    model_config = {"populate_by_name": True, "from_attributes": True}


class ProductInventory(BaseModel):
    """Product inventory info"""
    product_id: str = Field(..., alias="productId")
    product_description: str
    quantity: int = Field(..., ge=0)
    price: Decimal
    
    model_config = {"populate_by_name": True, "from_attributes": True}


class ProductCreate(BaseModel):
    """Create new product"""
    product_id: str = Field(..., alias="productId")
    product_description: str = Field(..., min_length=10)
    price: Decimal = Field(..., ge=0)
    
    model_config = {"populate_by_name": True}


class ProductUpdate(BaseModel):
    """Update existing product"""
    product_description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=0)
    
    model_config = {"populate_by_name": True}


class ProductStats(BaseModel):
    """Product statistics"""
    total_products: int = Field(..., ge=0)
    total_categories: int = Field(..., ge=0)
    avg_price: Decimal = Field(..., ge=0)
    avg_rating: Decimal = Field(..., ge=0, le=5)
EOFPROD

cat > backend/models/search.py << 'EOFSEARCH'
"""DAT406 Workshop - Search Models"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum
from .product import SearchResult


class SearchType(str, Enum):
    """Type of search"""
    VECTOR = "vector"
    HYBRID = "hybrid"
    KEYWORD = "keyword"


class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    category_filter: Optional[str] = None
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Search query cannot be empty")
        return cleaned


class SearchResponse(BaseModel):
    """Search response"""
    results: List[SearchResult]
    total_results: int = Field(..., ge=0)
    query: str
    execution_time_ms: float = Field(..., ge=0)
    search_type: SearchType = SearchType.VECTOR


class SimilarProductsRequest(BaseModel):
    """Similar products request"""
    product_id: str = Field(..., alias="productId")
    limit: int = Field(default=5, ge=1, le=50)
    
    model_config = {"populate_by_name": True}


class SimilarProductsResponse(BaseModel):
    """Similar products response"""
    source_product_id: str = Field(..., alias="sourceProductId")
    results: List[SearchResult]
    total_results: int = Field(..., ge=0)
    
    model_config = {"populate_by_name": True}


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    database_connected: bool
    bedrock_accessible: bool
    uptime_seconds: float = Field(..., ge=0)


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
EOFSEARCH

echo "✅ Created backend/models/"

# ==============================================================================
# STEP 6: CREATE SERVICES PACKAGE
# ==============================================================================

echo "📦 Creating services package..."

cat > backend/services/__init__.py << 'EOF'
"""DAT406 Workshop - Services Package"""

from .database import DatabaseService, get_db_service, close_db_service, db
from .embeddings import EmbeddingsService, get_embeddings_service, embeddings

__all__ = [
    "DatabaseService",
    "get_db_service",
    "close_db_service",
    "db",
    "EmbeddingsService",
    "get_embeddings_service",
    "embeddings"
]
EOF

# Note: Full service files are too large for single script
# Creating simplified versions with TODO markers

cat > backend/services/database.py << 'EOFDB'
"""
DAT406 Workshop - Database Service
TODO: Full implementation with psycopg connection pooling
"""

import psycopg
from psycopg_pool import ConnectionPool
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service for PostgreSQL connections"""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._initialized = False
    
    def initialize(self, connection_string: str):
        """Initialize connection pool"""
        try:
            self._pool = ConnectionPool(
                conninfo=connection_string,
                min_size=2,
                max_size=10
            )
            self._initialized = True
            logger.info("Database service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection"""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        with self._pool.connection() as conn:
            yield conn
    
    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return cur.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """Get global database service"""
    global _db_service
    if _db_service is None:
        from ..config import settings
        _db_service = DatabaseService()
        _db_service.initialize(settings.db_connection_string)
    return _db_service


def close_db_service():
    """Close database service"""
    global _db_service
    if _db_service and _db_service._pool:
        _db_service._pool.close()
    _db_service = None


db = get_db_service()
EOFDB

cat > backend/services/embeddings.py << 'EOFEMBED'
"""
DAT406 Workshop - Embeddings Service
TODO: Full implementation with Bedrock Titan v2
"""

import boto3
import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating embeddings"""
    
    def __init__(self, model_id: str = "amazon.titan-embed-text-v2:0", region: str = "us-west-2"):
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.dimensions = 1024
        logger.info(f"Initialized embeddings service: {model_id}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not text or text.strip() == "":
            raise ValueError("Text cannot be empty")
        
        text = text.strip()[:2000]
        
        try:
            request_body = {
                "inputText": text,
                "dimensions": self.dimensions,
                "normalize": True
            }
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding')
            
            if not embedding or len(embedding) != self.dimensions:
                raise ValueError("Invalid embedding returned")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if service is accessible"""
        try:
            self.generate_embedding("test")
            return True
        except Exception:
            return False


_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """Get global embeddings service"""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service


embeddings = get_embeddings_service()
EOFEMBED

echo "✅ Created backend/services/"

# ==============================================================================
# STEP 7: CREATE AGENTS AND MCP PLACEHOLDERS
# ==============================================================================

echo "📦 Creating agents and MCP packages..."

cat > backend/agents/__init__.py << 'EOF'
"""DAT406 Workshop - Agents Package (Lab 2)"""
__all__ = []
EOF

cat > backend/mcp/__init__.py << 'EOF'
"""DAT406 Workshop - MCP Package (Lab 2)"""
__all__ = []
EOF

echo "✅ Created backend/agents/ and backend/mcp/"

# ==============================================================================
# STEP 8: CREATE DATA DIRECTORY FILES
# ==============================================================================

echo "📦 Creating data directory files..."

cat > data/README.md << 'EOFDATA'
# DAT406 Workshop - Sample Data

## Amazon Products Dataset

**File**: `amazon-products-sample.csv`  
**Size**: 21,704 products  
**Format**: CSV with headers

### Schema

| Column | Type | Description |
|--------|------|-------------|
| productId | string | Unique product identifier |
| product_description | text | Full product description |
| price | decimal | Product price in USD |
| stars | decimal | Average rating (0-5) |
| reviews | integer | Number of reviews |
| category_name | string | Product category |
| quantity | integer | Current stock |

### Loading the Data

Run `scripts/setup-database.sh` to:
1. Create database schema
2. Load 21,704 products
3. Generate embeddings
4. Create HNSW index

**Note**: Place CSV file in this directory before running setup.
EOFDATA

touch data/.gitkeep

echo "✅ Created data/"

# ==============================================================================
# STEP 9: CREATE SCRIPTS DIRECTORY
# ==============================================================================

echo "📦 Creating scripts directory..."

touch scripts/.gitkeep

cat > scripts/README.md << 'EOF'
# DAT406 Workshop - Scripts

## Available Scripts

- `bootstrap-code-editor.sh` - Set up VS Code environment
- `setup-database.sh` - Initialize database and load data
- `cleanup.sh` - Clean up workshop resources

TODO: Add scripts from project documentation
EOF

echo "✅ Created scripts/"

# ==============================================================================
# STEP 10: CREATE FRONTEND PLACEHOLDERS
# ==============================================================================

echo "📦 Creating frontend placeholders..."

cat > frontend/README.md << 'EOF'
# DAT406 Workshop - Frontend

React + TypeScript + Vite application

TODO: Add frontend implementation

## Quick Start

```bash
npm install
npm run dev
```
EOF

touch frontend/src/.gitkeep
touch frontend/src/components/.gitkeep
touch frontend/src/services/.gitkeep
touch frontend/src/hooks/.gitkeep

echo "✅ Created frontend/"

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

echo ""
echo "=============================================================="
echo "  ✅ PROJECT SETUP COMPLETE!"
echo "=============================================================="
echo ""
echo "Directory structure:"
tree -L 3 -I '__pycache__|*.pyc|venv' || find . -type d -not -path '*/\.*' | head -20
echo ""
echo "Created files:"
echo "  ✅ .gitignore, LICENSE"
echo "  ✅ backend/requirements.txt"
echo "  ✅ backend/.env.example"
echo "  ✅ backend/config.py"
echo "  ✅ backend/models/ (product.py, search.py)"
echo "  ✅ backend/services/ (database.py, embeddings.py)"
echo "  ✅ backend/agents/ (placeholder)"
echo "  ✅ backend/mcp/ (placeholder)"
echo "  ✅ data/README.md"
echo "  ✅ scripts/README.md"
echo "  ✅ frontend/ (placeholder)"
echo ""
echo "Next steps:"
echo "  1. cd backend"
echo "  2. python3.13 -m venv venv"
echo "  3. source venv/bin/activate"
echo "  4. pip install -r requirements.txt"
echo "  5. cp .env.example .env"
echo "  6. Edit .env with your credentials"
echo "  7. Implement backend/app.py"
echo ""
echo "=============================================================="
