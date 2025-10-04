# DAT406 Workshop - Backend API

FastAPI backend for the DAT406 workshop: **Build Agentic AI-Powered Search with Amazon Aurora PostgreSQL and pgvector**.

## 🏗️ Architecture

### **Lab 1: Semantic Search**
- Pure vector similarity search using pgvector HNSW index
- Amazon Titan Text Embeddings v2 (1024 dimensions)
- PostgreSQL with pgvector extension
- Async I/O with psycopg 3

### **Lab 2: Multi-Agent System with MCP**
- Strands Agents SDK for agent orchestration
- Aurora PostgreSQL MCP Server for database access
- Three specialized agents:
  - **SearchAgent**: Semantic search with context
  - **InventoryAgent**: Stock analysis and alerts
  - **RecommendationAgent**: Product recommendations

## 📋 Prerequisites

- **Python 3.13+** (tested with 3.13)
- **Amazon Aurora PostgreSQL 17.5** with pgvector 0.8.0
- **AWS Account** with access to:
  - Amazon Bedrock (Titan Embeddings v2 + Claude Sonnet 3.7)
  - Amazon Aurora PostgreSQL
  - AWS Secrets Manager (optional)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd backend

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required settings:**
```bash
DB_HOST=your-aurora-cluster.us-west-2.rds.amazonaws.com
DB_PORT=5432
DB_NAME=workshop_db
DB_USER=postgres
DB_PASSWORD=your-password

AWS_REGION=us-west-2
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_CHAT_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0
```

### 3. Verify Database Setup

```bash
# Test database connection
python -c "
import asyncio
import psycopg
from config import settings

async def test():
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    cur = await conn.cursor()
    await cur.execute('SELECT version();')
    result = await cur.fetchone()
    print(f'✅ Connected: {result[0]}')
    await conn.close()

asyncio.run(test())
"
```

### 4. Run the API

```bash
# Development mode (with auto-reload)
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at: http://localhost:8000

## 📚 API Documentation

Once running, access interactive docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔍 API Endpoints

### Health & Info

```bash
# Root endpoint
GET /

# Health check
GET /api/health
```

### Lab 1: Semantic Search

```bash
# Vector similarity search
POST /api/search
{
  "query": "wireless headphones with noise cancellation",
  "limit": 10,
  "min_similarity": 0.6
}

# Get single product
GET /api/products/{product_id}

# List products with filters
GET /api/products?category=Electronics&min_stars=4&limit=20
```

### Lab 2: Multi-Agent System (Optional)

```bash
# Agent-based search (using MCP)
POST /api/agent/search
{
  "query": "best laptops for programming",
  "limit": 5
}

# Inventory analysis
GET /api/inventory/analyze

# Low stock alerts
GET /api/inventory/low-stock?threshold=10

# Product recommendations
POST /api/recommendations
{
  "productId": "B07XYZ1234",
  "limit": 5
}
```

## 🧪 Testing

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/api/health

# Search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "laptop computer",
    "limit": 5
  }'

# Get product
curl http://localhost:8000/api/products/B07XYZ1234
```

### Python Testing

```python
import httpx
import asyncio

async def test_search():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/search",
            json={
                "query": "wireless headphones",
                "limit": 5
            }
        )
        print(response.json())

asyncio.run(test_search())
```

## 📁 Project Structure

```
backend/
├── app.py                 # Main FastAPI application
├── config.py              # Configuration & settings
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
│
├── models/               # Pydantic models
│   ├── __init__.py
│   ├── product.py        # Product models
│   └── search.py         # Search request/response models
│
├── services/             # Core services
│   ├── __init__.py
│   ├── database.py       # PostgreSQL connection pool
│   ├── embeddings.py     # Titan embeddings
│   └── bedrock.py        # Claude chat (Lab 2)
│
└── agents/               # Multi-agent system (Lab 2)
    ├── __init__.py
    ├── search_agent.py
    ├── inventory_agent.py
    └── recommendation_agent.py
```

## 🔧 Configuration

### Database Pool Settings

```python
DB_POOL_MIN_SIZE=2    # Minimum connections
DB_POOL_MAX_SIZE=10   # Maximum connections
DB_POOL_TIMEOUT=30    # Connection timeout (seconds)
```

### Search Settings

```python
DEFAULT_SEARCH_LIMIT=10           # Default results per search
MIN_SIMILARITY_THRESHOLD=0.5      # Minimum cosine similarity
```

## 🐛 Troubleshooting

### Connection Issues

```bash
# Check if Aurora is accessible
psql -h your-cluster.us-west-2.rds.amazonaws.com \
     -U postgres -d workshop_db

# Verify pgvector extension
psql -h your-cluster.us-west-2.rds.amazonaws.com \
     -U postgres -d workshop_db \
     -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

### Bedrock Access

```bash
# Test Bedrock embeddings
aws bedrock-runtime invoke-model \
  --model-id amazon.titan-embed-text-v2:0 \
  --body '{"inputText":"test","dimensions":1024}' \
  --region us-west-2 \
  output.json

# List available models
aws bedrock list-foundation-models --region us-west-2
```

### Common Errors

**"Database service not connected"**
- Ensure `connect()` is called during app startup
- Check database credentials in `.env`
- Verify network connectivity to Aurora

**"Bedrock model not accessible"**
- Enable Titan Embeddings v2 in Bedrock console
- Check AWS credentials and region
- Verify IAM permissions for Bedrock

**"pgvector extension not found"**
- Install pgvector: `CREATE EXTENSION vector;`
- Verify Aurora supports pgvector (16.9+)

## 📊 Performance Tips

1. **Connection Pooling**: Adjust pool size based on load
   ```python
   DB_POOL_MIN_SIZE=5
   DB_POOL_MAX_SIZE=20
   ```

2. **HNSW Index Tuning**: For better search performance
   ```sql
   CREATE INDEX idx_product_embedding 
   ON product_catalog 
   USING hnsw (embedding vector_cosine_ops)
   WITH (m = 16, ef_construction = 64);
   ```

3. **Async Operations**: Use async/await throughout
   ```python
   async with db.get_connection() as conn:
       results = await conn.fetch_all(query)
   ```

## 🔐 Security Notes

- **Never commit `.env`** to version control
- Use AWS Secrets Manager for production credentials
- Implement rate limiting for public APIs
- Enable CORS only for trusted origins
- Use IAM roles instead of access keys when possible

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [psycopg 3 Documentation](https://www.psycopg.org/psycopg3/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Strands Agents SDK](https://github.com/strands-agents/strands)

## 🤝 Support

For workshop-specific issues:
- Check the main repository README
- Review CloudFormation templates
- Contact workshop facilitators

## 📄 License

See LICENSE file in repository root.