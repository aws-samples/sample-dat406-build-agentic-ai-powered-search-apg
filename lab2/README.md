# Lab 2: Building Blaize Bazaar - Full-Stack AI E-Commerce Application

**Duration**: 80 minutes  
**Level**: 400 (Expert)

## 🎯 Learning Objectives

By the end of this lab, you will:
- ✅ Build a production-grade FastAPI backend with semantic search
- ✅ Create a React frontend with AI chat assistant
- ✅ Implement Model Context Protocol (MCP) for database access
- ✅ Deploy multi-agent system for inventory, pricing, and recommendations
- ✅ Integrate Amazon Bedrock for conversational AI
- ✅ Implement real-time autocomplete and filters

## 📋 Prerequisites

- **Completed Lab 1** - Database with embeddings must be ready
- Python 3.11+ and Node.js 18+ installed
- AWS credentials configured
- Aurora PostgreSQL cluster running with data loaded

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                  │
│  • TypeScript + Tailwind CSS                                 │
│  • AI Chat Assistant (Aurora AI)                             │
│  • Semantic Search UI with Filters                           │
│  • Real-time Autocomplete                                    │
│  • Dark/Light Mode Theme Toggle                              │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Python)                 │
│  • Semantic Search Endpoints                                 │
│  • Chat Service with Strands SDK                             │
│  • Multi-Agent System (Inventory, Pricing, Recommendations) │
│  • MCP Integration for Database Access                       │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────────┐
│ Amazon Bedrock   │    │ Aurora PostgreSQL    │
│ • Cohere Embed   │    │ • pgvector Extension │
│ • Claude 3.7     │    │ • HNSW Index         │
│   Sonnet         │    │ • 21,704 Products    │
└──────────────────┘    └──────────────────────┘
```

## 📁 Lab Structure

```
lab2/
├── backend/              # FastAPI application
│   ├── agents/          # AI agents (inventory, pricing, recommendations)
│   ├── models/          # Pydantic data models
│   ├── services/        # Business logic
│   ├── app.py           # Main FastAPI app
│   ├── config.py        # Configuration
│   └── requirements.txt # Python dependencies
│
├── frontend/            # React application
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── services/    # API client
│   │   └── styles/      # CSS files
│   ├── package.json     # Node dependencies
│   └── vite.config.ts   # Vite configuration
│
├── config/              # Application configuration
│   └── mcp-server-config.json
│
└── data/                # Sample data
    └── amazon-products-sample.csv
```

## 🚀 Getting Started

### Step 1: Backend Setup

```bash
cd lab2/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Aurora and AWS credentials
```

**Required Environment Variables** (`.env`):
```bash
# Database
DB_HOST=your-aurora-cluster.region.rds.amazonaws.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password
DB_CLUSTER_ARN=arn:aws:rds:region:account:cluster:cluster-name
DB_SECRET_ARN=arn:aws:secretsmanager:region:account:secret:secret-name

# AWS
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Bedrock
BEDROCK_EMBEDDING_MODEL=cohere.embed-english-v3
BEDROCK_CHAT_MODEL=us.anthropic.claude-3-7-sonnet-20250219-v1:0
```

**Start Backend**:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### Step 2: Frontend Setup

```bash
cd lab2/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with backend URL
```

**Required Environment Variables** (`.env`):
```bash
VITE_API_URL=http://localhost:8000
```

**Start Frontend**:
```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### Step 3: Verify Setup

1. **Backend Health Check**: Visit `http://localhost:8000/api/health`
2. **Frontend**: Open `http://localhost:5173` in browser
3. **Test Search**: Try searching for "wireless headphones"
4. **Test Chat**: Click Aurora AI bubble and ask "Show me laptops"

## 🎨 Key Features

### 1. Semantic Search
- Natural language product search
- Vector similarity using pgvector
- 60%+ similarity scores for relevant results
- Sub-100ms response times

### 2. Aurora AI Chat Assistant
- Conversational product discovery
- Powered by Claude 3.7 Sonnet
- Direct database access via MCP
- Context-aware recommendations

### 3. Smart Filters
- Price range filtering
- Star rating filters (3★, 4★, 4.5★, 5★)
- Real-time client-side filtering
- Category browsing

### 4. Real-time Autocomplete
- Trigram-based suggestions
- 300ms debounce
- Shows product name and category
- GIN index for fast queries

### 5. Multi-Agent System: "Agents as Tools" Pattern

**What is "Agents as Tools"?**

A hierarchical AI architecture where:
1. **Orchestrator Agent** - Routes queries to domain specialists
2. **Specialist Agents** - Wrapped as `@tool` functions, callable by orchestrator
3. **Custom MCP Tools** - Provide data to specialist agents

This mimics human team dynamics: a manager (orchestrator) coordinates specialists (agents), each with focused expertise.

**Blaize Bazaar Implementation:**
- **Orchestrator Agent** (`blaize_orchestrator.py`): Routes queries like a teacher
- **Inventory Agent**: Stock analysis using `get_inventory_health` MCP tool
- **Recommendation Agent**: Product suggestions using `get_trending_products` MCP tool
- **Pricing Agent**: Price analysis using `get_price_statistics` MCP tool

**Benefits:**
- ✅ Separation of concerns - each agent has focused responsibility
- ✅ Modular architecture - add/remove agents independently
- ✅ Hierarchical delegation - clear routing logic
- ✅ Optimized prompts - each agent tailored to its domain

### 6. Premium UI/UX
- Apple-inspired glassmorphism design
- Dark/light mode support
- Smooth animations and transitions
- Responsive grid layout

## 🔧 API Endpoints

### Search & Autocomplete
```bash
# Semantic search
POST /api/search
{
  "query": "bluetooth headphones",
  "limit": 10,
  "min_similarity": 0.6
}

# Fast category browse
GET /api/products/category/security%20cameras?limit=10

# Autocomplete
GET /api/autocomplete?q=headphone&limit=5
```

### Chat
```bash
# Chat with Aurora AI
POST /api/chat
{
  "message": "Show me gaming laptops under $1500",
  "conversation_history": []
}
```

### Custom MCP Tools
```bash
# List all custom tools
GET /api/mcp/tools

# Get trending products
GET /api/mcp/trending?limit=10

# Get inventory health
GET /api/mcp/inventory-health

# Get price statistics
GET /api/mcp/price-stats?category=Electronics
```

### Products
```bash
# Get single product
GET /api/products/{product_id}

# List products with filters
GET /api/products?limit=20&category=Electronics&min_stars=4.0
```

## 🤖 MCP Integration + Custom Tools

The application uses Model Context Protocol for database access and extends it with custom business logic.

### Base MCP Tools (from Aurora PostgreSQL MCP)
- `run_query` - Execute SQL queries
- `get_schema` - Get database schema

### Custom MCP Tools (Blaize Bazaar Extensions)
- `get_trending_products` - Trending analysis (reviews × stars)
- `get_inventory_health` - Inventory statistics & alerts
- `get_price_statistics` - Price analytics by category
- `list_custom_tools` - Tool discovery

**Configuration**: `lab2/config/mcp-server-config.json`

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "uv",
      "args": ["run", "--with", "awslabs.postgres-mcp-server", "awslabs.postgres-mcp-server", ...],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2"
      }
    }
  }
}
```

## 📊 Performance Metrics

- **Search Latency**: 50-150ms average
- **Autocomplete**: <50ms with trigram index
- **Similarity Scores**: 60-95% for relevant results
- **Database Size**: 21,704 products with embeddings
- **Vector Dimensions**: 1024 (Cohere Embed English v3)

## 🐛 Troubleshooting

### Backend Won't Start
- Check `.env` file has all required variables
- Verify Aurora cluster is accessible
- Ensure Bedrock models are enabled

### Frontend Can't Connect
- Verify backend is running on port 8000
- Check CORS settings in `backend/app.py`
- Confirm `VITE_API_URL` in frontend `.env`

### Chat Not Working
- Verify MCP config path: `lab2/config/mcp-server-config.json`
- Check DB_CLUSTER_ARN and DB_SECRET_ARN are set
- Ensure `uv` is installed: `pip install uv`

### Slow Search Performance
- Verify HNSW index exists (from Lab 1)
- Check database connection latency
- Consider adjusting `min_similarity` threshold

## 🎓 Workshop Exercises

### Exercise 1: Add New Filter
Add a "In Stock Only" filter to the search overlay.

### Exercise 2: Create Custom Agent
Build a new agent for product comparison.

### Exercise 3: Enhance Chat
Add product images to chat responses.

### Exercise 4: Optimize Performance
Implement caching for frequent searches.

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Strands SDK](https://github.com/awslabs/strands)
- [Strands Agents as Tools Pattern](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 🎉 Completion

Congratulations! You've built a production-grade AI-powered e-commerce platform with:
- ✅ Semantic search using pgvector
- ✅ Conversational AI with Claude
- ✅ Multi-agent system
- ✅ Modern React frontend
- ✅ Real-time features

## 📤 Deployment

For production deployment, see `../deployment/` folder for setup scripts.

---

**Questions?** Open an issue or ask your workshop instructor.

**Built with ❤️ for AWS re:Invent 2025 | DAT406 Workshop**
