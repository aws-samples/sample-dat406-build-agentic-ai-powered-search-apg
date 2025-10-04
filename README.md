# Blaize Bazaar - Agentic Search Platform

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
**AWS re:Invent 2025** • **Level 400 (Expert)**

</div>

---

## 🚀 Overview

**Production-grade AI commerce platform** demonstrating intelligent product discovery through semantic search and multi-agent orchestration. Built with **Amazon Aurora PostgreSQL 17.5** (pgvector), **Amazon Bedrock**, and modern web technologies.

### ✨ Key Features

| Feature | Description | Performance |
|---------|-------------|-------------|
| 📦 **Product Catalog** | Amazon dataset with embeddings | 21,704 products |
| 🔍 **Semantic Search** | Natural language product queries | 60%+ similarity scores |
| 🤖 **Agent Assist** | Multi-agent orchestration | Claude Sonnet 4 |
| 🎯 **Smart Filters** | Dynamic price & rating filters | Instant updates |
| 🔌 **MCP Integration** | Model Context Protocol | Custom tools |
| ⚡ **Real-time Autocomplete** | Trigram-based suggestions | <50ms response |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         React + TypeScript + Tailwind       │
│         Semantic Search • Autocomplete      │
└──────────────────┬──────────────────────────┘
                   │ REST API
                   ▼
┌─────────────────────────────────────────────┐
│         FastAPI + Python 3.13               │
│         Vector Search • Multi-Agent System  │
└──────────────┬──────────────┬───────────────┘
               │              │
               ▼              ▼
    ┌──────────────┐  ┌──────────────────────┐
    │   Bedrock    │  │  Aurora PostgreSQL   │
    │ Titan Embed  │  │  17.5 + pgvector     │
    │  (1024d)     │  │  HNSW • Trigram      │
    │ Claude 4     │  │                      │
    └──────────────┘  └──────────────────────┘
```

### 🎯 Multi-Agent System

**Agents as Tools Pattern** with specialized agents:

```
┌─────────────────────────────────────────┐
│         Orchestrator Agent              │
│     (Intent Analysis & Routing)         │
└────────────┬────────────────────────────┘
             │
       ┌─────┴─────┬─────────────┐
       ▼           ▼             ▼
  ┌─────────┐ ┌─────────┐  ┌─────────┐
  │Inventory│ │  Reco   │  │ Pricing │
  │  Agent  │ │ Agent   │  │ Agent   │
  └─────────┘ └─────────┘  └─────────┘
       │           │             │
       └───────────┴─────────────┘
                   │
                   ▼
          Aurora PostgreSQL 17.5
```

## 📚 Workshop Structure

### Lab 1: Semantic Search Foundation
**Duration**: 20 minutes | **Location**: `lab1/`

- ✅ Load 21,704 products into Aurora PostgreSQL 17.5
- ✅ Generate embeddings with Amazon Bedrock Titan v2
- ✅ Create HNSW indexes for vector similarity
- ✅ Execute semantic search queries

[📖 Start Lab 1 →](./lab1/README.md)

### Lab 2: Full-Stack Application
**Duration**: 80 minutes | **Location**: `lab2/`

- ✅ FastAPI backend with semantic search API
- ✅ React frontend with AI chat assistant
- ✅ Multi-agent system (Agents as Tools pattern)
- ✅ Model Context Protocol (MCP) integration

[📖 Start Lab 2 →](./lab2/README.md)

**📚 Complete Guide**: [WORKSHOP_GUIDE.md](./WORKSHOP_GUIDE.md)

---

## ⚡ Quick Start

### Prerequisites

```bash
✓ Python 3.13+
✓ Node.js 18+
✓ Aurora PostgreSQL 17.5 with pgvector
✓ AWS Account with Bedrock access (Titan Embeddings v2, Claude Sonnet 4)
```

### Backend Setup

```bash
cd backend
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env with Aurora credentials
cp .env.example .env

uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Backend URL**: `http://localhost:8000`  
**API Docs**: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

**Frontend URL**: `http://localhost:5173`

---

## 🗄️ Database Schema

**Table**: `bedrock_integration.product_catalog`

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| productId | VARCHAR(255) | Unique identifier | PRIMARY KEY |
| product_description | TEXT | Product details | GIN, GIN Trigram |
| embedding | VECTOR(1024) | Titan v2 embedding | HNSW |
| price | NUMERIC | USD price | B-tree |
| stars | NUMERIC | Rating (0-5) | — |
| reviews | INTEGER | Review count | — |
| quantity | INTEGER | Stock level | — |
| category_name | VARCHAR(255) | Product category | B-tree |
| imgurl | TEXT | Product image URL | — |
| producturl | TEXT | Amazon product link | — |
| isbestseller | BOOLEAN | Bestseller flag | — |
| boughtinlastmonth | INTEGER | Recent sales | — |

### 📊 Indexes

```sql
-- Vector similarity (HNSW)
CREATE INDEX idx_product_embedding_hnsw 
ON bedrock_integration.product_catalog 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search (GIN)
CREATE INDEX idx_product_fts 
ON bedrock_integration.product_catalog
USING GIN (to_tsvector('english', product_description));

-- Autocomplete (GIN Trigram)
CREATE INDEX idx_product_trgm 
ON bedrock_integration.product_catalog
USING GIN (product_description gin_trgm_ops);

-- Filtering (B-tree)
CREATE INDEX idx_product_category ON bedrock_integration.product_catalog(category_name);
CREATE INDEX idx_product_price ON bedrock_integration.product_catalog(price);
```

---

## 🔌 API Endpoints

### Search & Autocomplete

```bash
# Semantic search
POST /api/search
Content-Type: application/json

{
  "query": "wireless headphones with noise cancellation",
  "limit": 10,
  "min_similarity": 0.0
}

# Autocomplete suggestions
GET /api/autocomplete?q=headphone&limit=5
```

### Products

```bash
# Get single product
GET /api/products/{product_id}

# List products with filters
GET /api/products?limit=20&category=Electronics&min_stars=4.0&min_price=50&max_price=500
```

### MCP Tools

```bash
# List custom tools
GET /api/mcp/tools

# Get trending products
GET /api/mcp/trending?limit=5

# Inventory health
GET /api/mcp/inventory

# Price statistics
GET /api/mcp/pricing
```

### Health Check

```bash
GET /api/health
```

---

## 🛠️ Technology Stack

<table>
<tr>
<td><strong>Frontend</strong></td>
<td>React 18 • TypeScript 5 • Tailwind CSS • Vite • Lucide React</td>
</tr>
<tr>
<td><strong>Backend</strong></td>
<td>FastAPI • Python 3.13 • psycopg3 • boto3 • Pydantic</td>
</tr>
<tr>
<td><strong>Database</strong></td>
<td>Aurora PostgreSQL 17.5 • pgvector</td>
</tr>
<tr>
<td><strong>AI/ML</strong></td>
<td>Amazon Bedrock (Titan Embeddings v2, Claude Sonnet 4)</td>
</tr>
<tr>
<td><strong>Search</strong></td>
<td>HNSW index • Trigram index • Cosine similarity</td>
</tr>
</table>

---

## 🎓 Learning Outcomes

By completing this workshop, you will learn:

1. ✅ **Vector Embeddings** - Generate and store semantic embeddings with Titan v2
2. ✅ **Similarity Search** - Use pgvector for fast nearest neighbor search
3. ✅ **HNSW Indexing** - Optimize vector search performance
4. ✅ **Multi-Agent Systems** - Orchestrator with specialized agents (Agents as Tools pattern)
5. ✅ **Custom MCP Tools** - Extend Aurora PostgreSQL MCP with business logic
6. ✅ **AWS Integration** - Use Bedrock for embeddings (Titan v2) and chat (Claude Sonnet 4)
7. ✅ **Real-time UX** - Build responsive search interfaces

---

## 🤖 Multi-Agent System

Aurora AI uses an **Agents as Tools** pattern with specialized agents:

### Orchestrator Agent
Routes customer queries to the appropriate specialist based on intent analysis.

### Specialized Agents

#### 1. **Inventory Agent** (`inventory_agent.py`)
```python
✓ Stock level analysis and monitoring
✓ Restocking recommendations
✓ Low inventory alerts
✓ Out-of-stock product identification
```

#### 2. **Recommendation Agent** (`recommendation_agent.py`)
```python
✓ Personalized product suggestions
✓ Feature-based matching
✓ Budget-conscious recommendations
✓ Category-specific guidance
```

#### 3. **Pricing Agent** (`pricing_agent.py`)
```python
✓ Price analysis and optimization
✓ Deal identification
✓ Bundle recommendations
✓ Best value suggestions
```

**Each agent connects directly to Aurora PostgreSQL for real-time data access.**

---

## 🔌 MCP Server Integration

Connect AI assistants to Aurora database using **Model Context Protocol**.

### Base MCP ([Aurora PostgreSQL](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server))
Provides 2 out-of-the-box tools:
- **run_query** - Execute SQL queries against the database
- **get_table_schema** - List all tables with schema information

### Custom MCP Tools (Blaize Bazaar)
- **get_trending_products** - Trending analysis based on sales velocity
- **get_inventory_health** - Stock statistics & low inventory alerts
- **get_price_statistics** - Price analytics across categories
- **list_custom_tools** - Tool discovery endpoint

```bash
# Test custom tools
curl http://localhost:8000/api/mcp/tools
curl http://localhost:8000/api/mcp/trending?limit=5
curl http://localhost:8000/api/mcp/inventory
curl http://localhost:8000/api/mcp/pricing
```

**See [ARCHITECTURE_GUIDE.md](./ARCHITECTURE_GUIDE.md) for implementation details.**

---

## 📁 Project Structure

```
blaize-bazaar/
├── lab1/                    # Lab 1: Jupyter notebooks
├── lab2/                    # Lab 2: Full application
│   ├── backend/            # FastAPI application
│   │   ├── models/        # Pydantic models
│   │   ├── services/      # Business logic
│   │   ├── agents/        # AI agents
│   │   └── app.py         # Main app
│   ├── frontend/          # React application
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── services/
│   │   │   └── styles/
│   │   └── package.json
│   └── config/            # MCP configuration
├── data/                  # Sample data
├── deployment/            # Setup scripts
└── docs/                  # Documentation
```

---

## ⚙️ Configuration

### Backend Environment Variables

```bash
# Database
DB_HOST=your-aurora-cluster.region.rds.amazonaws.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password

# AWS
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Bedrock
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_CHAT_MODEL=us.anthropic.claude-3-7-sonnet-20250219-v1:0
```

### Frontend Environment Variables

```bash
VITE_API_URL=http://localhost:8000
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

---

## 💬 Support

For questions or issues:
- 📝 Open an issue on GitHub
- 🔧 Check [MCP_SETUP.md](./MCP_SETUP.md) for MCP configuration
- 📚 Review [WORKSHOP_GUIDE.md](./WORKSHOP_GUIDE.md) for complete instructions

---

<div align="center">

**© 2025 Shayon Sanyal | AWS re:Invent 2025 | DAT406 Workshop**

[![GitHub](https://img.shields.io/badge/GitHub-Blaize--Bazaar-181717?style=flat-square&logo=github)](https://github.com)
[![AWS](https://img.shields.io/badge/AWS-Workshop-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![Aurora](https://img.shields.io/badge/Aurora-PostgreSQL%2017.5-336791?style=flat-square&logo=postgresql&logoColor=white)](https://aws.amazon.com/rds/aurora/)

</div>