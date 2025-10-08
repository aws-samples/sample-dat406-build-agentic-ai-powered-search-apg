# Lab 2: Full-Stack Agentic Search Application

**Duration:** 80 minutes  
**Prerequisites:** Lab 1 completed (database loaded with embeddings)

---

## Overview

Build a production-grade e-commerce search platform with:
- FastAPI backend with semantic search
- React frontend with AI chat assistant
- Multi-agent system (Orchestrator + 3 specialized agents)
- Model Context Protocol (MCP) integration with Aurora PostgreSQL

---

## Part 1: Start the Application (10 minutes)

### Step 1: Start Backend (Terminal 1)

```bash
start-backend
```

**What happens:**
- Generates MCP config with your AWS account ARNs
- Starts FastAPI backend
- Initializes database connection
- Loads custom MCP tools (trending, inventory, pricing)
- Registers 4 agents (orchestrator, inventory, recommendation, pricing)

**Verify:** Backend should show "🚀 DAT406 Workshop API is ready!"

### Step 2: Start Frontend (Terminal 2)

```bash
start-frontend
```

**What happens:**
- Builds React app with Vite
- Serves production build
- Connects to backend API via CloudFront

**Access:** Open the CloudFront URL provided in your Workshop Studio environment

---

## Part 2: Test Semantic Search (15 minutes)

### Step 3: Search Interface

1. **Try searches (using products in our dataset):**
   - "wireless headphones"
   - "security camera"
   - "vacuum cleaner"
   - "gaming headset"

2. **Observe:**
   - Vector similarity scores (0-100%)
   - Response time (~250-300ms)
   - Product cards with images, prices, ratings

3. **Apply filters:**
   - Price range: $50-$500
   - Min rating: 4+ stars
   - Category filtering

### Step 4: Explore Search Features

**Try different search types:**

1. **Semantic Search** - Natural language queries
   - "noise canceling headphones for travel"
   - "security camera for outdoor monitoring"
   - "vacuum cleaner for pet hair"
   - "fitness tracker with heart rate monitor"

2. **Category Browse** - Specific categories
   - "security cameras"
   - "vacuum cleaners"
   - "smart watches"
   - "gaming accessories"

3. **Observe the technology:**
   - Vector similarity scores (shown as percentages)
   - Fast response times (~250-300ms)
   - pgvector HNSW index in action

---

## Part 3: Custom MCP Tools (15 minutes)

### Step 5: Understand MCP Tools

Aurora PostgreSQL MCP provides 2 base tools:
- `run_query` - Execute SQL
- `get_table_schema` - List tables

We extended it with 4 custom tools:
- `get_trending_products` - Trending analysis
- `get_inventory_health` - Stock statistics
- `get_price_statistics` - Price analytics
- `restock_product` - Inventory management

**These tools are used by the agents to answer your questions!**

### Step 6: Explore MCP Config

```bash
cat lab2/config/mcp-server-config.json
```

**Key components:**
- `command`: `uv` (Python package manager)
- `args`: Aurora cluster ARN, secret ARN, database name
- `env`: AWS region, credentials

---

## Part 4: Multi-Agent System (25 minutes)

### Step 7: Understanding the Architecture

**Agents as Tools Pattern:**

```
┌─────────────────────────────────┐
│     Orchestrator Agent          │
│  (Routes to specialists)        │
└────────────┬────────────────────┘
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
          Aurora PostgreSQL
```

### Step 8: Test Agents via Chat Interface

**Open the chat assistant** (click chat icon in bottom right)

**Test each agent type with these proven examples:**

1. **Inventory Agent** - Ask about stock:
   - "What products need restocking?"
   - "Show me low stock items"
   - "Which high-demand products are running low?"
   - **Expected:** Shows agent chain: `Orchestrator → Inventory Agent → Analyzing stock levels ✓`

2. **Recommendation Agent** - Ask for suggestions (use products that exist in our dataset):
   - "Recommend wireless headphones under $100"
   - "I need a security camera for my home"
   - "Show me the best vacuum cleaners"
   - "What gaming accessories do you have?"
   - **Expected:** Shows agent chain: `Orchestrator → Recommendation Agent → Finding products ✓`

3. **Pricing Agent** - Ask about deals:
   - "What are the best deals on headphones?"
   - "Show me budget-friendly security cameras"
   - "Which products offer the best value under $50?"
   - **Expected:** Shows agent chain: `Orchestrator → Pricing Agent → Analyzing prices ✓`

4. **Orchestrator Multi-Agent** - Complex queries:
   - "Help me find affordable home security products"
   - "What should I buy for a home office setup?"
   - "I need gaming accessories that are well-reviewed"
   - **Expected:** May show multiple agents in chain

**💡 Dataset Overview:** Our sample contains 21,704 products with strong representation in:
- 🎧 **Audio & Headphones** (wireless, noise-canceling, gaming headsets)
- 📹 **Security & Cameras** (indoor/outdoor cameras, smart doorbells)
- 🧹 **Home Appliances** (vacuums, air purifiers, kitchen gadgets)
- 🎮 **Gaming & Electronics** (accessories, controllers, tech gear)
- ⌚ **Wearables** (smart watches, fitness trackers, health monitors)
- 🔌 **Tech Accessories** (chargers, cables, phone cases, stands)

**Note:** Laptops and computers have limited representation in this sample dataset, so use the categories above for best results!

### Step 9: Explore Agent Code

**Open in VS Code:**

1. **Orchestrator** (`lab2/backend/agents/orchestrator.py`)
   - Routes queries to specialists
   - Supports Claude 4 extended thinking mode

2. **Inventory Agent** (`lab2/backend/agents/inventory_agent.py`)
   - Uses `@tool` decorator
   - Calls `get_inventory_health()` and `restock_product()`

3. **Recommendation Agent** (`lab2/backend/agents/recommendation_agent.py`)
   - Uses `@tool` decorator
   - Calls `get_trending_products(limit)`

4. **Pricing Agent** (`lab2/backend/agents/pricing_agent.py`)
   - Uses `@tool` decorator
   - Calls `get_price_statistics()`

### Step 10: Understand MCP Agent Tools

**Open:** `lab2/backend/services/mcp_agent_tools.py`

**Key functions (all with `@tool` decorator):**
- `get_inventory_health()` - Returns pre-fetched inventory data
- `get_trending_products(limit)` - Returns trending products
- `get_price_statistics()` - Returns price analytics
- `restock_product(product_id, quantity)` - Simulates restocking

**Why pre-fetched?**
- Data loaded at startup for fast agent responses
- Avoids repeated database queries
- Agents get instant access to business data

---

## Part 5: AI Chat Assistant (15 minutes)

### Step 11: Test Chat Interface

**In the frontend:**

1. Click the chat icon (bottom right)
2. Try queries:
   - "Show me trending products"
   - "What's in low stock?"
   - "Recommend a laptop under $1000"
   - "What are the best deals?"

**Observe:**
- Agent routing (which agent handles the query)
- Product cards in chat responses
- Quick action suggestions

### Step 12: Chat Service Architecture

**Open:** `lab2/backend/services/chat.py`

**Key features:**
- Uses Strands SDK with MCP client
- Connects to Aurora PostgreSQL via MCP
- Extracts product data from agent responses
- Returns structured JSON with products array

**Flow:**
1. User sends message
2. Chat service creates MCP client
3. Agent queries database via MCP
4. Response parsed for products
5. Frontend displays product cards

---

## Part 6: Extended Thinking (Optional - 10 minutes)

### Step 13: Claude 4 Extended Thinking

**Try complex queries in the chat (using products in our dataset):**

- "Find the best value wireless headphones considering price, reviews, and features"
- "Compare security cameras and recommend the best one for home monitoring"
- "What products should we restock based on demand and current inventory?"
- "Help me choose between different vacuum cleaners for pet owners"

**What happens behind the scenes:**
- Agent "thinks" between tool calls
- Reflects on results before responding
- Adapts strategy based on findings
- Uses up to 3000 thinking tokens

**Use cases:**
- Complex multi-step queries
- Queries requiring reasoning
- Situations needing multiple agents

---

## Key Takeaways

✅ **Semantic Search:** pgvector + HNSW for fast similarity search  
✅ **Custom MCP Tools:** Extended Aurora PostgreSQL MCP with business logic  
✅ **Multi-Agent System:** Orchestrator + 3 specialists using Agents as Tools pattern  
✅ **Strands SDK:** `@tool` decorator for agent functions  
✅ **Production Ready:** FastAPI + React + CloudFront deployment  

---

## Troubleshooting

**Backend won't start:**
- Check terminal output for errors
- Verify database credentials in `.env`
- Check logs: `tail -f /var/log/bootstrap-labs.log`

**Frontend shows 404 or errors:**
- Refresh browser (F5) - cache busting is automatic
- Check browser console for API errors
- Verify CloudFront URL is accessible
- If issues persist, try hard refresh (Cmd+Shift+R or Ctrl+Shift+R)

**Agents not working:**
- Verify IAM permissions (rds-data:ExecuteStatement)
- Check MCP config: `cat lab2/config/mcp-server-config.json`

**Chat not responding:**
- Requires RDS Data API IAM permissions (rds-data:BeginTransaction, rds-data:CommitTransaction, rds-data:RollbackTransaction)
- Check IAM role: `genai-dat-406-labs-CodeEditorStack-1-CodeEditorRole`
- Add missing permissions via AWS Console → IAM → Roles

---

## Next Steps

- Experiment with different agent queries
- Modify agent prompts in `agents/*.py`
- Add new custom MCP tools in `services/mcp_database.py`
- Extend frontend with new features

**Time permitting:**
- Add a 4th specialized agent
- Implement product comparison feature
- Add shopping cart persistence
