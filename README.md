# DAT406: Build Agentic AI-Powered Search with Amazon Aurora PostgreSQL

## Blaize Bazaar - Enterprise-Grade Agentic Search Platform

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.5-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=white)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)

[![AWS](https://img.shields.io/badge/AWS-Aurora%20%7C%20Bedrock-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

[![Architecture](https://img.shields.io/badge/Architecture-Multi--Agent-6a1b9a?style=flat-square&labelColor=4a148c)](README.md)
[![Search](https://img.shields.io/badge/Search-Vector%20Powered-ba68c8?style=flat-square&labelColor=6a1b9a)](README.md)
[![AI](https://img.shields.io/badge/AI-Semantic%20%7C%20Agentic-8e24aa?style=flat-square&labelColor=4a148c)](README.md)
[![Database](https://img.shields.io/badge/Database-pgvector%20HNSW-9c27b0?style=flat-square&labelColor=6a1b9a)](README.md)

</div>

---

<div align="center">

### 🎯 **DAT406 Workshop** | Build Agentic AI-Powered Search with Amazon Aurora PostgreSQL
**AWS re:Invent 2025** • **Level 400 (Expert)** • **Duration: 2 Hours**

</div>

---

## 🚀 Overview

Blaize Bazaar is an enterprise AI e-commerce platform demonstrating intelligent product discovery through **semantic search** and **multi-agent orchestration**. Built on **Amazon Aurora PostgreSQL 17.5** with pgvector 0.8.0, **Amazon Bedrock**, and modern full-stack technologies.

### ✨ Core Capabilities

| Feature | Technology | Description |
|---------|-----------|-------------|
| 🔍 **Semantic Search** | pgvector 0.8.0 HNSW | Natural language product queries with sub-10ms latency |
| 🤖 **Agentic AI** | Claude Sonnet 4 | Multi-agent orchestration with Agents as Tools pattern |
| 🔌 **MCP Integration** | PostgreSQL MCP Server | Custom business logic tools for Aurora database |
| 🎯 **Smart Filtering** | Vector + SQL hybrid | Dynamic price, rating, and category filters |
| 📊 **Analytics Dashboard** | FastAPI + React | Real-time inventory and pricing insights |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│      React 18 + TypeScript + Tailwind      │
│      Modern UI • Real-time Search          │
└──────────────────┬──────────────────────────┘
                   │ REST API
                   ▼
┌─────────────────────────────────────────────┐
│      FastAPI + Python 3.13 Backend         │
│      Vector Search • Multi-Agent System     │
└──────────┬─────────────────┬────────────────┘
           │                 │
           ▼                 ▼
    ┌─────────────┐   ┌───────────────────────┐
    │   Bedrock   │   │  Aurora PostgreSQL    │
    │ Titan v2    │   │  17.5 + pgvector 0.8  │
    │ Claude 4    │   │  HNSW • Trigram       │
    └─────────────┘   └───────────────────────┘
```

### 🎯 Multi-Agent System (Agents as Tools)

```
┌──────────────────────────────────────────┐
│       Orchestrator Agent (Claude)        │
│     Intent Analysis & Task Routing       │
└────────────┬─────────────────────────────┘
             │
       ┌─────┴─────┬──────────────┐
       ▼           ▼              ▼
  ┌─────────┐ ┌─────────┐  ┌──────────┐
  │Inventory│ │  Reco   │  │ Pricing  │
  │  Agent  │ │ Agent   │  │  Agent   │
  └────┬────┘ └────┬────┘  └────┬─────┘
       └──────────┴─────────────┘
                   │
                   ▼
          Aurora PostgreSQL
          (MCP Tools Layer)
```

---

## 📚 Workshop Structure

**Total Duration:** 2 hours | **Level:** 400 (Expert) | **Format:** Hands-on

### Lab 1: Semantic Search Foundation (20 min)
**📂 Location:** `lab1/` | **📖 Guide:** [LAB1_GUIDE.md](lab1/LAB1_GUIDE.md)

Build the semantic search engine:
- ✅ Load 21,704 Amazon products into Aurora PostgreSQL 17.5
- ✅ Generate 1024-dimensional embeddings with Bedrock Titan v2
- ✅ Create optimized HNSW indexes for vector similarity search
- ✅ Execute semantic queries with interactive UI comparison

**Quick Start:**
```bash
Run through all cells from top to bottom in VSCode Editor
```

### Lab 2: Full-Stack Agentic Application (80 min)
**📂 Location:** `lab2/` | **📖 Guide:** [LAB2_GUIDE.md](lab2/LAB2_GUIDE.md)

Build the complete AI-powered application:
- ✅ FastAPI backend with semantic search REST API
- ✅ React + TypeScript frontend with modern UI
- ✅ Multi-agent system with specialized agents
- ✅ Model Context Protocol (MCP) custom tools
- ✅ Real-time autocomplete and smart filters

**Quick Start:**
```bash
start-backend   # Terminal 1: FastAPI on port 8000
start-frontend  # Terminal 2: React on port 5173
```

**Access Points:**
- 🌐 Frontend: `<CloudFront-URL>/ports/5173/`
- 🔌 Backend API: `<CloudFront-URL>/ports/8000/`
- 📚 API Docs: `<CloudFront-URL>/ports/8000/docs`

---

## ⚡ Quick Start

### Workshop Participants

Everything is pre-configured via bootstrap scripts! All commands work from any directory:

```bash
# Lab 2: Backend + Frontend
start-backend   # Terminal 1
start-frontend  # Terminal 2

# Utilities
workshop        # Navigate to workshop root
lab1           # Navigate to Lab 1
lab2           # Navigate to Lab 2
```

### Local Development Setup

**Prerequisites:**
- Python 3.13+ with pip
- Node.js 18+ with npm
- Aurora PostgreSQL 17.5 with pgvector 0.8.0
- AWS Account with Bedrock access (us-west-2)

**Installation:**
```bash
# 1. Clone repository
git clone <repo-url>
cd sample-dat406-build-agentic-ai-powered-search-apg

# 2. Install dependencies
pip install -r lab1/requirements.txt
pip install -r lab2/backend/requirements.txt
cd lab2/frontend && npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your database credentials and AWS settings

# 4. Start services
cd lab2/backend && uvicorn app:app --reload    # Backend
cd lab2/frontend && npm run build              # Frontend
```

**Access URLs (Local):**
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

---

## 🗄️ Database Schema

**Table:** `bedrock_integration.product_catalog`

| Column | Type | Index | Description |
|--------|------|-------|-------------|
| `productId` | VARCHAR(255) | PRIMARY KEY | Unique product identifier |
| `product_description` | TEXT | GIN, Trigram | Full product details for search |
| `embedding` | VECTOR(1024) | HNSW | Titan v2 semantic embedding |
| `price` | NUMERIC(10,2) | B-tree | Product price in USD |
| `stars` | NUMERIC(3,2) | — | Rating (0.0-5.0) |
| `reviews` | INTEGER | — | Number of customer reviews |
| `quantity` | INTEGER | — | Available stock quantity |
| `category_name` | VARCHAR(255) | B-tree | Product category |

### 📊 Performance-Optimized Indexes

```sql
-- Vector similarity search (sub-10ms queries)
CREATE INDEX idx_product_embedding_hnsw 
ON bedrock_integration.product_catalog 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search
CREATE INDEX idx_product_fts 
ON bedrock_integration.product_catalog
USING GIN (to_tsvector('english', product_description));

-- Autocomplete (trigram)
CREATE INDEX idx_product_trgm 
ON bedrock_integration.product_catalog
USING GIN (product_description gin_trgm_ops);

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
  "query": "wireless gaming headphones with noise cancellation",
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

### Product Endpoints

```bash
# Get product details
GET /api/products/{product_id}

# List products with filters
GET /api/products?limit=20&category=Electronics&min_stars=4.0
```

### MCP Custom Tools

```bash
# List all custom tools
GET /api/mcp/tools

# Trending products (by sales velocity)
GET /api/mcp/trending?limit=5

# Inventory health metrics
GET /api/mcp/inventory

# Price statistics by category
GET /api/mcp/pricing
```

### System Health

```bash
# Health check
GET /api/health

# Database connectivity
GET /api/health/db
```

---

## 🤖 Multi-Agent Architecture

### Orchestrator Agent (Claude Sonnet 4)
**Role:** Intent analysis and task routing  
**Features:**
- 🧠 Extended thinking capability for complex queries
- 🔄 Adaptive strategy based on tool responses
- 📊 Context-aware agent selection

### Specialized Agents (Agents as Tools Pattern)

#### 1. **Inventory Agent**
```python
✓ Real-time stock monitoring
✓ Low inventory alerts (<10 units)
✓ Out-of-stock identification
✓ Restocking recommendations
```

#### 2. **Recommendation Agent**
```python
✓ Personalized product suggestions
✓ Feature-based matching
✓ Budget-conscious alternatives
✓ Cross-category recommendations
```

#### 3. **Pricing Agent**
```python
✓ Price trend analysis
✓ Deal identification (>20% off)
✓ Bundle optimization
✓ Value-for-money rankings
```

**Data Access:** Each agent connects directly to Aurora PostgreSQL for real-time insights.

---

## 🔌 Model Context Protocol (MCP)

Extends the [Aurora PostgreSQL MCP Server](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) with custom business logic.

### Base MCP Tools (Out-of-the-Box)
- `run_query` - Execute SQL queries
- `get_table_schema` - Database schema inspection

### Custom MCP Tools (Blaize Bazaar)
- `get_trending_products` - Sales velocity analysis
- `get_inventory_health` - Stock statistics & alerts
- `get_price_statistics` - Category-wise pricing analytics
- `list_custom_tools` - Tool discovery endpoint

**Configuration:** Auto-generated during deployment with correct AWS account ARNs.

**Testing:**
```bash
curl http://localhost:8000/api/mcp/tools
curl http://localhost:8000/api/mcp/trending?limit=5
curl http://localhost:8000/api/mcp/inventory
curl http://localhost:8000/api/mcp/pricing
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18 • TypeScript 5 • Tailwind CSS • Vite • Lucide Icons |
| **Backend** | FastAPI • Python 3.13 • psycopg3 • boto3 • Pydantic |
| **Database** | Aurora PostgreSQL 17.5 • pgvector 0.8.0 |
| **AI/ML** | Amazon Bedrock (Titan Embeddings v2, Claude Sonnet 4) |
| **Search** | HNSW indexes • Trigram indexes • Cosine similarity |
| **Agent Framework** | Strands AI • Agents as Tools pattern |

---

## 🎓 Learning Outcomes

By completing this workshop, you will:

1. ✅ **Master Vector Embeddings** - Generate and store semantic embeddings at scale
2. ✅ **Build Semantic Search** - Implement sub-10ms vector similarity search with HNSW
3. ✅ **Design Multi-Agent Systems** - Orchestrator + specialized agents (Agents as Tools)
4. ✅ **Extend MCP Servers** - Create custom tools for Aurora PostgreSQL
5. ✅ **Integrate AWS AI Services** - Bedrock for embeddings (Titan v2) and chat (Claude 4)
6. ✅ **Optimize Database Performance** - Index strategies for hybrid vector+SQL queries
7. ✅ **Deploy Full-Stack AI Apps** - FastAPI + React enterprise architecture

---

## 🚀 Deployment Automation

### Bootstrap Scripts

The workshop environment is fully automated via `deployment/bootstrap-labs.sh`:

**Automated Setup:**
1. ✅ Fetches database credentials from AWS Secrets Manager
2. ✅ Calculates `DB_CLUSTER_ARN` from AWS account metadata
3. ✅ Generates `.env` files (root, backend, frontend)
4. ✅ Creates MCP configuration with correct ARNs
5. ✅ Installs Python and Node.js dependencies
6. ✅ Configures bash aliases for quick commands

**Configuration Files Created:**

`.env` (Backend):
```bash
DB_CLUSTER_ARN=arn:aws:rds:{region}:{account}:cluster:apg-pgvector-dat406
DB_SECRET_ARN=arn:aws:secretsmanager:{region}:{account}:secret:...
DB_HOST=cluster.{region}.rds.amazonaws.com
AWS_REGION=us-west-2
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_CHAT_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0
```

`.env` (Frontend):
```bash
VITE_API_URL=/ports/8000
VITE_AWS_REGION=us-west-2
```

`lab2/config/mcp-server-config.json`:
```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "uv",
      "args": ["--resource_arn", "{DB_CLUSTER_ARN}", ...]
    }
  }
}
```

### IAM Permissions Required

EC2 instance role must have:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds-data:ExecuteStatement",
        "rds:DescribeDBClusters"
      ],
      "Resource": "arn:aws:rds:*:*:cluster:apg-pgvector-dat406"
    },
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:*:*:secret:apg-pgvector-secret-dat406-*"
    },
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "*"
    }
  ]
}
```

### Zero Manual Configuration

Participants simply run `start-backend` and `start-frontend` - everything works immediately!

---

## 📁 Project Structure

```
sample-dat406-build-agentic-ai-powered-search-apg/
├── lab1/                           # Lab 1: Semantic Search
│   ├── Lab_1_Enhanced_Final.ipynb  # Main notebook
│   ├── requirements.txt            # Python dependencies
│   └── LAB1_GUIDE.md              # Step-by-step guide
│
├── lab2/                           # Lab 2: Full Application
│   ├── backend/                    # FastAPI Backend
│   │   ├── app.py                 # Main application
│   │   ├── models/                # Pydantic models
│   │   ├── services/              # Business logic
│   │   │   ├── search_service.py  # Semantic search
│   │   │   ├── mcp_service.py     # MCP tools
│   │   │   └── bedrock_service.py # Bedrock integration
│   │   ├── agents/                # Multi-agent system
│   │   │   ├── inventory_agent.py
│   │   │   ├── recommendation_agent.py
│   │   │   └── pricing_agent.py
│   │   └── requirements.txt
│   │
│   ├── frontend/                   # React Frontend
│   │   ├── src/
│   │   │   ├── components/        # React components
│   │   │   ├── services/          # API client
│   │   │   └── styles/            # Tailwind CSS
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── config/                     # MCP Configuration
│   │   └── mcp-server-config.json # Auto-generated
│   │
│   └── LAB2_GUIDE.md              # Step-by-step guide
│
├── data/                           # Sample Data
│   └── amazon-products-curated-10k.csv
│
├── deployment/                     # Bootstrap Scripts
│   ├── bootstrap-environment.sh   # Stage 1: Code Editor setup
│   └── bootstrap-labs.sh          # Stage 2: Labs installation
│
└── docs/                          # Documentation
    └── architecture/
```

---

## 💡 Key Insights

### Why pgvector 0.8.0?

**Automatic Iterative Scanning:**
- Eliminates manual `ef_search` tuning
- Guarantees complete results across all queries
- 100% recall with minimal latency overhead

**Before (pgvector 0.7.x):**
```sql
-- Might miss results with strict filters
SET hnsw.ef_search = 40;  -- Manual tuning required
```

**After (pgvector 0.8.0):**
```sql
-- Always returns complete results
SET hnsw.iterative_scan = 'relaxed_order';  -- Just works!
```

### Why Agents as Tools Pattern?

**Traditional Approach:** Monolithic agent with all capabilities  
**Agents as Tools:** Orchestrator delegates to specialists

**Benefits:**
- 🎯 **Focused Expertise** - Each agent masters one domain
- 🔄 **Easy Maintenance** - Update agents independently
- ⚡ **Better Performance** - Parallel execution possible
- 📈 **Scalable** - Add new agents without refactoring

---

## 🤝 Support & Resources

### Workshop Support
- 👨‍🏫 Ask your workshop instructor or TAs
- 📧 Refer to lab guides in `lab1/` and `lab2/`

### Additional Resources
- 📘 [Aurora PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- 📗 [pgvector 0.8.0 Blog Post](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- 📙 [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- 📕 [Model Context Protocol Specification](https://modelcontextprotocol.io/)

### Community
- 🐛 Report issues on GitHub
- 💬 Join the discussion in workshop Slack

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---

<div align="center">

**© 2025 Shayon Sanyal | AWS re:Invent 2025 | DAT406 Workshop**

[![GitHub](https://img.shields.io/badge/GitHub-Blaize--Bazaar-181717?style=flat-square&logo=github)](https://github.com)
[![AWS](https://img.shields.io/badge/AWS-Workshop-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![Aurora](https://img.shields.io/badge/Aurora-PostgreSQL%2017.5-336791?style=flat-square&logo=postgresql&logoColor=white)](https://aws.amazon.com/rds/aurora/)

**⭐ Star this repo if you found it helpful! ⭐**

</div>