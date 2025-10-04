# Blaize Bazaar - AI-Powered Semantic Search E-Commerce

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.5-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=white)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![AWS](https://img.shields.io/badge/AWS-Aurora%20%7C%20Bedrock-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **DAT406 Workshop**: Build Agentic AI-Powered Search with Amazon Aurora PostgreSQL  
> **Event**: AWS re:Invent 2025 | **Level**: 400 (Expert)

## Overview

Production-grade AI e-commerce platform showcasing intelligent product discovery through semantic search. Built with **Amazon Aurora PostgreSQL 17.5** (pgvector), **Amazon Bedrock**, and modern web technologies.

### Key Features

- **Semantic Search** - Natural language product queries with 60%+ similarity scores
- **Real-time Autocomplete** - Trigram-based suggestions (<50ms response)
- **AI Assistant** - Aurora AI chatbot powered by Claude Sonnet 4 with multi-agent orchestration
- **Premium UI/UX** - Modern design with dark/light themes and glassmorphism effects
- **Smart Filters** - Price range and star ratings with instant updates
- **21,704 Products** - Full Amazon catalog with vector embeddings
- **MCP Integration** - Model Context Protocol with custom tools

## Architecture

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

## Workshop Structure

### Lab 1: Semantic Search Foundation (20 min)

**Location**: `lab1/`

- Load 21,704 products into Aurora PostgreSQL 17.5
- Generate embeddings with Amazon Bedrock Titan v2
- Create HNSW indexes for vector similarity
- Execute semantic search queries

[Start Lab 1 →](./lab1/README.md)

### Lab 2: Full-Stack Application (80 min)

**Location**: `lab2/`

- FastAPI backend with semantic search API
- React frontend with AI chat assistant
- Multi-agent system (Agents as Tools pattern)
- Model Context Protocol (MCP) integration

[Start Lab 2 →](./lab2/README.md)

**Complete Guide**: [WORKSHOP_GUIDE.md](./WORKSHOP_GUIDE.md)

---

## Quick Start

### Prerequisites

- **Python 3.13+**
- **Node.js 18+**
- **Aurora PostgreSQL 17.5** with pgvector
- **AWS Account** with Bedrock access (Titan Embeddings v2, Claude Sonnet 4)

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

Backend available at: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend available at: `http://localhost:5173`

## Database Schema

**Table**: `bedrock_integration.product_catalog`

| Column | Type | Description |
|--------|------|-------------|
| productId | VARCHAR(255) | Unique identifier (Primary Key) |
| product_description | TEXT | Product details |
| embedding | VECTOR(1024) | Titan v2 embedding |
| price | NUMERIC | USD price |
| stars | NUMERIC | Rating (0-5) |
| reviews | INTEGER | Review count |
| quantity | INTEGER | Stock level |
| category_name | VARCHAR(255) | Product category |
| imgurl | TEXT | Product image URL |
| producturl | TEXT | Amazon product link |
| isbestseller | BOOLEAN | Bestseller flag |
| boughtinlastmonth | INTEGER | Recent sales |

**Indexes**:
- **HNSW** on `embedding` - Vector similarity (m=16, ef_construction=64, cosine distance)
- **GIN** on `product_description` - Full-text search (English)
- **GIN Trigram** on `product_description` - Autocomplete
- **B-tree** on `category_name`, `price` - Filtering

## API Endpoints

### Search & Autocomplete

```bash
# Semantic search
POST /api/search
{
  "query": "wireless headphones",
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
GET /api/products?limit=20&category=Electronics&min_stars=4.0
```

### Health Check

```bash
GET /api/health
```

## Technology Stack

**Frontend**: React 18 • TypeScript 5 • Tailwind CSS • Vite • Lucide React  
**Backend**: FastAPI • Python 3.13 • psycopg3 • boto3 • Pydantic  
**Database**: Aurora PostgreSQL 17.5 • pgvector  
**AI**: Amazon Bedrock (Titan Embeddings v2, Claude Sonnet 4)  
**Search**: HNSW index • Trigram index • Cosine similarity

## Learning Outcomes

1. **Vector Embeddings** - Generate and store semantic embeddings with Titan v2
2. **Similarity Search** - Use pgvector for fast nearest neighbor search
3. **HNSW Indexing** - Optimize vector search performance
4. **Multi-Agent Systems** - Orchestrator with specialized agents (Agents as Tools pattern)
5. **Custom MCP Tools** - Extend Aurora PostgreSQL MCP with business logic
6. **AWS Integration** - Use Bedrock for embeddings (Titan v2) and chat (Claude Sonnet 4)
7. **Real-time UX** - Build responsive search interfaces

## MCP Server Integration

Connect AI assistants to Aurora database using Model Context Protocol.

### Base MCP (Aurora PostgreSQL)
- Direct database access for AI agents
- SQL query execution
- Schema introspection

### Custom MCP Tools (Blaize Bazaar)
- **get_trending_products**: Trending analysis
- **get_inventory_health**: Stock statistics & alerts
- **get_price_statistics**: Price analytics
- **list_custom_tools**: Tool discovery

```bash
# Test custom tools
curl http://localhost:8000/api/mcp/tools
curl http://localhost:8000/api/mcp/trending?limit=5
```

See [ARCHITECTURE_GUIDE.md](./ARCHITECTURE_GUIDE.md) for details.

## Project Structure

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

## Configuration

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

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

## Acknowledgments

- **AWS re:Invent 2025** - DAT406 Workshop
- **Amazon Aurora PostgreSQL 17.5** - Vector database with pgvector
- **Amazon Bedrock** - Titan Embeddings v2 and Claude Sonnet 4
- **Model Context Protocol** - AI assistant integration

## Support

For questions or issues:
- Open an issue on GitHub
- Check [MCP_SETUP.md](./MCP_SETUP.md) for MCP configuration
- Review [WORKSHOP_GUIDE.md](./WORKSHOP_GUIDE.md) for complete instructions

---

**© 2025 Shayon Sanyal | AWS re:Invent 2025 | DAT406 Workshop**