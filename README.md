# DAT406 - Build Agentic AI-Powered Search with Amazon Aurora PostgreSQL

<div align="center">

### Platform & Infrastructure
[![AWS Aurora](https://img.shields.io/badge/Aurora_PostgreSQL-17.5-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com/rds/aurora/)
[![pgvector](https://img.shields.io/badge/pgvector-0.8.0_HNSW-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Bedrock](https://img.shields.io/badge/Amazon_Bedrock-Titan_v2_|_Claude_4-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com/bedrock/)

### Languages & Frameworks
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=white)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

### Architecture & Capabilities
[![Architecture](https://img.shields.io/badge/Architecture-Multi--Agent-6a1b9a?style=flat-square&labelColor=4a148c)](README.md)
[![Search](https://img.shields.io/badge/Search-Vector%20Powered-ba68c8?style=flat-square&labelColor=6a1b9a)](README.md)
[![AI](https://img.shields.io/badge/AI-Semantic%20%7C%20Agentic-8e24aa?style=flat-square&labelColor=4a148c)](README.md)
[![Database](https://img.shields.io/badge/Database-pgvector%20HNSW-9c27b0?style=flat-square&labelColor=6a1b9a)](README.md)

[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Workshop Level](https://img.shields.io/badge/Level-400_Expert-orange?style=for-the-badge)]()
[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-00ADD8?style=for-the-badge)](https://modelcontextprotocol.io/)

</div>

> ⚠️ **WARNING**: For demonstration and educational purposes only. Not intended for production use.

## 🚀 Quick Start

**Workshop Duration**: 2 hours | **Lab 1**: 20 min | **Lab 2**: 80 min

Build enterprise-grade agentic AI applications with semantic search, multi-agent orchestration, and Model Context Protocol integration. Leverage Amazon Aurora PostgreSQL 17.5 with pgvector 0.8.0, Amazon Bedrock, and modern full-stack technologies.

**Pre-configured Workshop Environment**:
```bash
start-backend   # Terminal 1: FastAPI backend (port 8000)
start-frontend  # Terminal 2: React frontend (port 5173)
```

## 📁 Repository Structure

```
├── lab1/                           # Lab 1: Semantic Search Foundation
│   ├── notebook/
│   │   └── Lab_1_Enhanced_Final.ipynb
│   └── requirements.txt
├── lab2/                           # Lab 2: Full-Stack Agentic Application
│   ├── backend/                    # FastAPI + Multi-Agent System
│   │   ├── agents/                # Inventory, Recommendation, Pricing
│   │   ├── services/              # Search, MCP, Bedrock
│   │   └── app.py
│   ├── frontend/                   # React + TypeScript UI
│   │   └── src/
│   ├── config/                     # MCP Server Configuration
│   └── LAB2_GUIDE.md
├── deployment/                     # Bootstrap & Setup Scripts
│   ├── bootstrap-environment.sh
│   └── bootstrap-labs.sh
└── data/
    └── amazon-products-curated-10k.csv  # 21,704 products
```

## 🎯 Labs

### Lab 1: Semantic Search Foundation (20 min)

Build enterprise-grade vector search over 21,704 products with Aurora PostgreSQL 17.5 and pgvector 0.8.0.

**Technical Implementation:**
- **Vector Storage**: 1024-dimensional Titan Embeddings v2 via Amazon Bedrock
- **HNSW Indexing**: M=16, ef_construction=64 for fast similarity search
- **Automatic Iterative Scanning**: pgvector 0.8.0's new feature for guaranteed complete results
- **Hybrid Indexes**: GIN full-text search + trigram similarity for lexical matching

```bash
cd /workshop/lab1/notebook
# Open Lab_1_Enhanced_Final.ipynb in VS Code
```

**Key Concepts:**
- Distance metrics: L2 (`<->`), cosine (`<=>`), inner product (`<#>`)
- Index optimization: HNSW vs IVFFlat trade-offs
- pgvector 0.8.0 eliminates manual `ef_search` tuning with iterative scanning

**Learning Outcomes:**
- Generate and store semantic embeddings at scale
- Implement fast vector similarity search with HNSW
- Optimize database performance for hybrid vector+SQL queries

---

### Lab 2: Full-Stack Agentic Application (80 min)

Build complete AI-powered e-commerce platform with conversational search, multi-agent orchestration, and Model Context Protocol.

**Architecture:**
```
React 18 Frontend (TypeScript, Tailwind)
         ↓
FastAPI Backend (Python 3.13)
    ↓           ↓
Orchestrator → Specialized Agents (Agents as Tools)
    ↓           ↓           ↓
Inventory   Recommendation  Pricing
    └───────────┴───────────┘
              ↓
Aurora PostgreSQL (MCP Tools Layer)
```

**Technical Implementation:**
- **Multi-Agent System**: Orchestrator (Claude Sonnet 4) with extended thinking + specialized agents
- **Agents as Tools Pattern**: Focused agents for inventory, pricing, and recommendations
- **MCP Integration**: Custom tools extending Aurora PostgreSQL MCP Server
- **Real-time Features**: Autocomplete, smart filters, semantic search API

```bash
cd /workshop/lab2
start-backend   # Terminal 1: uvicorn app:app on port 8000
start-frontend  # Terminal 2: npm run dev on port 5173
```

**Access Points:**
- 🌐 Frontend: `<CloudFront-URL>/ports/5173/`
- 🔌 API Docs: `<CloudFront-URL>/ports/8000/docs`

**Key Concepts:**
- **Agentic Architecture**: Orchestrator analyzes intent → routes to specialist agents
- **MCP Tools**: `get_trending_products`, `get_inventory_health`, `get_price_statistics`
- **Agent Pattern**: Each agent connects directly to Aurora for real-time insights
- **Extended Thinking**: Claude Sonnet 4's advanced reasoning for complex queries

**Learning Outcomes:**
- Design multi-agent systems with Agents as Tools pattern
- Extend MCP servers with custom business logic
- Integrate AWS AI services (Bedrock Titan v2, Claude Sonnet 4)
- Deploy full-stack AI applications (FastAPI + React)

---

## 🗄️ Database Schema

**Table**: `bedrock_integration.product_catalog`

| Column | Type | Index | Description |
|--------|------|-------|-------------|
| `productId` | VARCHAR(255) | PRIMARY KEY | Unique identifier |
| `product_description` | TEXT | GIN, Trigram | Full product details |
| `embedding` | VECTOR(1024) | HNSW | Titan v2 semantic vector |
| `price` | NUMERIC(10,2) | B-tree | Price in USD |
| `stars` | NUMERIC(3,2) | — | Rating (0.0-5.0) |
| `reviews` | INTEGER | — | Customer review count |
| `quantity` | INTEGER | — | Available stock |
| `category_name` | VARCHAR(255) | B-tree | Product category |

**Performance-Optimized Indexes:**
```sql
-- Vector similarity search
CREATE INDEX idx_product_embedding_hnsw 
ON product_catalog USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search
CREATE INDEX idx_product_fts 
ON product_catalog USING GIN (to_tsvector('english', product_description));

-- Filter optimization
CREATE INDEX idx_product_category ON product_catalog(category_name);
CREATE INDEX idx_product_price ON product_catalog(price) WHERE price > 0;
```

---

## 🔌 API Reference

### Search Endpoints
```bash
# Semantic search with filters
POST /api/search
{
  "query": "wireless gaming headphones noise cancellation",
  "limit": 10,
  "min_similarity": 0.3,
  "filters": {
    "category": "Electronics",
    "min_price": 50,
    "max_price": 200,
    "min_stars": 4.0
  }
}

# Autocomplete suggestions
GET /api/autocomplete?q=headphone&limit=5
```

### MCP Custom Tools
```bash
# Trending products by sales velocity
GET /api/mcp/trending?limit=5

# Inventory health metrics
GET /api/mcp/inventory

# Price statistics by category
GET /api/mcp/pricing

# List all custom tools
GET /api/mcp/tools
```

### System Health
```bash
GET /api/health      # Overall health check
GET /api/health/db   # Database connectivity
```

---

## 🤖 Multi-Agent Architecture

### Orchestrator Agent (Claude Sonnet 4)
**Capabilities:**
- 🧠 Extended thinking for complex query analysis
- 🔄 Adaptive task routing based on tool responses
- 📊 Context-aware agent selection

### Specialized Agents (Agents as Tools)

**1. Inventory Agent**
```python
✓ Real-time stock monitoring
✓ Low inventory alerts (<10 units)
✓ Restocking recommendations
```

**2. Recommendation Agent**
```python
✓ Personalized product suggestions
✓ Feature-based matching
✓ Budget-conscious alternatives
```

**3. Pricing Agent**
```python
✓ Price trend analysis
✓ Deal identification (>20% off)
✓ Value-for-money rankings
```

**Data Access:** Direct Aurora PostgreSQL connection per agent for real-time insights.

---

## 🔧 Model Context Protocol (MCP)

Extends [Aurora PostgreSQL MCP Server](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) with custom business logic.

### Base MCP Tools (Out-of-the-Box)
- `run_query` - SQL execution
- `get_table_schema` - Schema inspection

### Custom Tools (Blaize Bazaar)
- `get_trending_products` - Sales velocity analysis
- `get_inventory_health` - Stock statistics & alerts
- `get_price_statistics` - Category-wise pricing
- `list_custom_tools` - Tool discovery

**Auto-configured** during deployment with correct AWS account ARNs.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Database** | Aurora PostgreSQL 17.5 • pgvector 0.8.0 (HNSW) |
| **AI/ML** | Amazon Bedrock (Titan Embeddings v2, Claude Sonnet 4) |
| **Backend** | FastAPI • Python 3.13 • psycopg3 • boto3 • Pydantic |
| **Frontend** | React 18 • TypeScript 5 • Tailwind CSS • Vite • Lucide Icons |
| **Search** | HNSW indexes • Trigram indexes • Cosine similarity |
| **Agent Framework** | Strands AI • Agents as Tools pattern |

---

## 💡 Key Technical Insights

### Why pgvector 0.8.0?

**Automatic Iterative Scanning** eliminates manual tuning:

**Before (0.7.x):**
```sql
SET hnsw.ef_search = 40;  -- Manual tuning required
-- Risk: May miss results with strict filters
```

**After (0.8.0):**
```sql
SET hnsw.iterative_scan = 'relaxed_order';
-- Guarantees complete results with minimal latency
-- 100% recall across all queries
```

### Why Agents as Tools?

| Traditional Approach | Agents as Tools |
|---------------------|-----------------|
| Monolithic agent | Orchestrator + specialists |
| All capabilities in one | Focused expertise per agent |
| Hard to maintain | Easy independent updates |
| Sequential execution | Parallel execution possible |

**Benefits:** 🎯 Domain expertise • 🔄 Easy maintenance • ⚡ Better performance • 📈 Scalable architecture

---

## 🎓 Learning Outcomes

By completing this workshop, you will:

1. ✅ **Understand Vector Embeddings** - Generate and store at scale with Titan v2
2. ✅ **Build Semantic Search** - Fast HNSW similarity search
3. ✅ **Design Multi-Agent Systems** - Orchestrator + specialists (Agents as Tools)
4. ✅ **Extend MCP Servers** - Custom tools for Aurora PostgreSQL
5. ✅ **Integrate AWS AI** - Bedrock for embeddings and conversational AI
6. ✅ **Optimize Database Performance** - Index strategies for hybrid queries
7. ✅ **Deploy Full-Stack AI** - FastAPI + React enterprise architecture

---

## 📚 Resources

- 📘 [Aurora PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- 📗 [pgvector 0.8.0 Blog Post](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- 📙 [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- 📕 [AWS Labs MCP Servers](https://awslabs.github.io/mcp/)
- 📔 [Model Context Protocol](https://modelcontextprotocol.io/)

---

## ⭐ Like This Workshop?

If you find this helpful:
- **Star this repository** to show support
- **Fork it** to customize for your use cases
- **Report issues** to help improve
- **Share it** with your community

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details

---

<div align="center">

**© 2025 Shayon Sanyal | AWS re:Invent 2025 | DAT406 Workshop**

[![GitHub](https://img.shields.io/badge/GitHub-aws--samples-181717?style=flat-square&logo=github)](https://github.com/aws-samples)
[![AWS](https://img.shields.io/badge/AWS-Workshop-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)

**⭐ Star this repo if you found it helpful! ⭐**

</div>