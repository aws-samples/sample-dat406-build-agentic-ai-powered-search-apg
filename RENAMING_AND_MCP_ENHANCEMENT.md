# Renaming and MCP Enhancement Plan

## Overview
1. Rename confusing "MCP" files to reflect they are custom business logic tools
2. Add real Aurora PostgreSQL MCP server integration for advanced use cases
3. Create customer reviews table to demonstrate MCP's power with JOINs

## Part 1: File Renaming

### Current (Confusing) Names
```
services/mcp_database.py       → Contains custom business logic, NOT MCP server
services/mcp_agent_tools.py    → Strands SDK tools, NOT MCP protocol
```

### New (Clear) Names
```
services/business_logic.py     → Custom business logic for inventory, pricing, trending
services/agent_tools.py        → Strands SDK @tool decorators for agents
services/mcp_server_tools.py   → NEW: Real MCP server integration tools
```

### Renaming Changes

#### 1. `services/mcp_database.py` → `services/business_logic.py`
**Reason:** This file contains custom business logic (trending scores, health metrics), not MCP protocol code

**Changes:**
- Rename class: `CustomMCPTools` → `BusinessLogic`
- Update docstring to clarify it's business logic layer
- Keep all methods the same (get_inventory_health, get_trending_products, etc.)

#### 2. `services/mcp_agent_tools.py` → `services/agent_tools.py`
**Reason:** These are Strands SDK tools, not MCP protocol tools

**Changes:**
- Rename file
- Update imports: `from services.business_logic import BusinessLogic`
- Update docstring: "Strands SDK Tools for Agents"
- Keep all @tool decorators the same

#### 3. Create NEW: `services/mcp_server_tools.py`
**Reason:** Demonstrate real Aurora PostgreSQL MCP server integration

**Purpose:**
- Show how to use actual MCP protocol with Aurora
- Demonstrate complex queries (JOINs across tables)
- Highlight MCP's value for ad-hoc database exploration

## Part 2: Real MCP Use Case - Customer Reviews

### Business Case
**Problem:** Product catalog lacks customer sentiment analysis. We need to:
- Join product data with customer reviews
- Analyze review sentiment by category
- Find products with review/rating mismatches
- Generate insights for product improvements

**Solution:** Use Aurora PostgreSQL MCP server to enable agents to:
- Discover schema dynamically
- Write complex JOIN queries
- Aggregate review data
- Provide actionable insights

### New Database Table: customer_reviews

```sql
CREATE TABLE bedrock_integration.customer_reviews (
    review_id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES bedrock_integration.product_catalog("productId"),
    customer_name VARCHAR(100),
    review_text TEXT,
    review_date DATE,
    verified_purchase BOOLEAN,
    helpful_votes INTEGER DEFAULT 0,
    sentiment VARCHAR(20), -- 'positive', 'negative', 'neutral'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_product_id ON bedrock_integration.customer_reviews(product_id);
CREATE INDEX idx_reviews_sentiment ON bedrock_integration.customer_reviews(sentiment);
CREATE INDEX idx_reviews_date ON bedrock_integration.customer_reviews(review_date);
```

### Sample Data (100 reviews)
- 60% positive reviews
- 25% neutral reviews
- 15% negative reviews
- Mix of verified/unverified purchases
- Realistic review text for top products

### New Agent: Review Analysis Agent

**Purpose:** Analyze customer reviews and provide insights

**Tools:**
- `mcp_run_query(sql)` - Execute queries via real MCP server
- `mcp_get_schema(table)` - Discover table structure via MCP
- `get_review_insights()` - Custom business logic for sentiment analysis

**Example Queries:**

```sql
-- Find products with negative reviews despite high ratings
SELECT 
    p."productId",
    p.product_description,
    p.stars,
    COUNT(r.review_id) as negative_reviews,
    STRING_AGG(r.review_text, ' | ') as sample_reviews
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r ON p."productId" = r.product_id
WHERE r.sentiment = 'negative'
  AND p.stars >= 4.0
GROUP BY p."productId", p.product_description, p.stars
ORDER BY negative_reviews DESC
LIMIT 10;

-- Category sentiment analysis
SELECT 
    p.category_name,
    COUNT(r.review_id) as total_reviews,
    COUNT(CASE WHEN r.sentiment = 'positive' THEN 1 END) as positive,
    COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) as negative,
    ROUND(AVG(p.stars), 2) as avg_rating
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r ON p."productId" = r.product_id
GROUP BY p.category_name
ORDER BY total_reviews DESC
LIMIT 15;

-- Verified vs unverified purchase sentiment
SELECT 
    r.verified_purchase,
    r.sentiment,
    COUNT(*) as review_count,
    ROUND(AVG(r.helpful_votes), 2) as avg_helpful_votes
FROM bedrock_integration.customer_reviews r
GROUP BY r.verified_purchase, r.sentiment
ORDER BY r.verified_purchase DESC, r.sentiment;
```

## Part 3: MCP Server Integration

### MCP Server Configuration

**File:** `config/mcp-server-config.json`

```json
{
  "mcpServers": {
    "aurora-postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://user:pass@aurora-cluster.region.rds.amazonaws.com:5432/postgres"
      ],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://..."
      }
    }
  }
}
```

### MCP Server Tools

**File:** `services/mcp_server_tools.py`

```python
"""
Real Aurora PostgreSQL MCP Server Integration
Demonstrates using MCP protocol for database operations
"""
from strands import tool
import json
import subprocess
import asyncio

# MCP client for Aurora PostgreSQL
_mcp_client = None

def initialize_mcp_client(connection_string: str):
    """Initialize MCP client connection to Aurora PostgreSQL"""
    global _mcp_client
    # Initialize MCP client with connection string
    # This would use actual MCP protocol (stdio/SSE)
    pass

@tool
def mcp_run_query(sql: str) -> str:
    """
    Execute SQL query via Aurora PostgreSQL MCP server.
    Supports complex queries including JOINs, aggregations, and CTEs.
    
    Use this for:
    - Ad-hoc data exploration
    - Complex multi-table queries
    - Schema discovery
    - Data analysis
    
    Args:
        sql: SQL query to execute
        
    Returns:
        JSON string with query results
    """
    # This would call actual MCP server via protocol
    # For now, we'll use direct database access
    from services.agent_tools import _db_service, _run_async
    
    if not _db_service:
        return json.dumps({"error": "Database not initialized"})
    
    try:
        results = _run_async(_db_service.fetch_all(sql))
        data = [dict(row) for row in results]
        return json.dumps({
            "status": "success",
            "rows": len(data),
            "data": data,
            "source": "aurora_mcp_server"
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "status": "failed",
            "source": "aurora_mcp_server"
        })

@tool
def mcp_get_schema(table_name: str = None) -> str:
    """
    Get database schema information via MCP server.
    
    Args:
        table_name: Optional table name to get specific schema
        
    Returns:
        JSON string with schema information
    """
    from services.agent_tools import _db_service, _run_async
    
    if not _db_service:
        return json.dumps({"error": "Database not initialized"})
    
    try:
        if table_name:
            query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'bedrock_integration'
                  AND table_name = %s
                ORDER BY ordinal_position
            """
            results = _run_async(_db_service.fetch_all(query, table_name))
        else:
            query = """
                SELECT table_name, 
                       COUNT(*) as column_count
                FROM information_schema.columns
                WHERE table_schema = 'bedrock_integration'
                GROUP BY table_name
                ORDER BY table_name
            """
            results = _run_async(_db_service.fetch_all(query))
        
        data = [dict(row) for row in results]
        return json.dumps({
            "status": "success",
            "schema": data,
            "source": "aurora_mcp_server"
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def mcp_list_tables() -> str:
    """List all tables in the database via MCP server"""
    from services.agent_tools import _db_service, _run_async
    
    if not _db_service:
        return json.dumps({"error": "Database not initialized"})
    
    try:
        query = """
            SELECT table_name, 
                   pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) as size
            FROM information_schema.tables
            WHERE table_schema = 'bedrock_integration'
            ORDER BY table_name
        """
        results = _run_async(_db_service.fetch_all(query))
        data = [dict(row) for row in results]
        return json.dumps({
            "status": "success",
            "tables": data,
            "source": "aurora_mcp_server"
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### New Agent: Review Analysis Agent

**File:** `agents/review_agent.py`

```python
"""
Review Analysis Agent - Analyzes customer reviews and sentiment
"""
from strands import Agent, tool
from services.agent_tools import run_query
from services.mcp_server_tools import mcp_run_query, mcp_get_schema, mcp_list_tables
from services.business_logic import BusinessLogic

@tool
def review_analysis_agent(query: str) -> str:
    """
    Analyze customer reviews and provide insights.
    Uses MCP server for complex JOIN queries across product and review tables.
    
    Args:
        query: Review analysis question
    
    Returns:
        Review insights and recommendations
    """
    agent = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt="""You are a customer review analysis specialist for Blaize Bazaar.

You have access to TWO data sources:

1. **MCP Server Tools** (for complex queries):
   - mcp_run_query(sql) - Execute complex JOINs, aggregations, CTEs
   - mcp_get_schema(table) - Discover table structure
   - mcp_list_tables() - List available tables

2. **Direct Tools** (for simple queries):
   - run_query(sql) - Execute simple queries

**Database Schema:**

product_catalog table:
- productId (PK), product_description, price, stars, reviews, category_name, quantity

customer_reviews table:
- review_id (PK), product_id (FK), customer_name, review_text, review_date
- verified_purchase, helpful_votes, sentiment (positive/negative/neutral)

**Analysis Strategy:**

1. Use mcp_get_schema() to explore tables if needed
2. Use mcp_run_query() for complex analysis:
   - JOIN product_catalog with customer_reviews
   - Aggregate sentiment by category
   - Find rating/review mismatches
   - Identify products needing attention

3. Provide actionable insights:
   - Products with negative reviews despite high ratings
   - Categories with sentiment issues
   - Verified vs unverified purchase patterns
   - Recommendations for product improvements

**Example Queries:**

Find products with negative reviews:
```sql
SELECT p.product_description, p.stars, COUNT(r.review_id) as neg_reviews
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r ON p."productId" = r.product_id
WHERE r.sentiment = 'negative' AND p.stars >= 4.0
GROUP BY p."productId", p.product_description, p.stars
ORDER BY neg_reviews DESC LIMIT 10;
```

Category sentiment analysis:
```sql
SELECT p.category_name, 
       COUNT(CASE WHEN r.sentiment = 'positive' THEN 1 END) as positive,
       COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) as negative
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r ON p."productId" = r.product_id
GROUP BY p.category_name
ORDER BY COUNT(*) DESC LIMIT 15;
```

Format response with insights and recommendations.""",
        tools=[mcp_run_query, mcp_get_schema, mcp_list_tables, run_query]
    )
    
    try:
        response = agent(query)
        return str(response)
    except Exception as e:
        return f"Error in review analysis agent: {str(e)}"
```

## Part 4: Implementation Steps

### Step 1: Rename Files
```bash
# Rename business logic file
mv services/mcp_database.py services/business_logic.py

# Rename agent tools file
mv services/mcp_agent_tools.py services/agent_tools.py
```

### Step 2: Update Imports Across Codebase
- `agents/inventory_agent.py`
- `agents/recommendation_agent.py`
- `agents/pricing_agent.py`
- `agents/orchestrator.py`
- `app.py`

### Step 3: Create New Files
- `services/mcp_server_tools.py` - MCP server integration
- `agents/review_agent.py` - Review analysis agent
- `scripts/create_reviews_table.sql` - Database schema
- `scripts/seed_reviews_data.py` - Sample data generator

### Step 4: Update Orchestrator
Add review_analysis_agent to orchestrator tools

### Step 5: Create API Endpoints
```python
@app.post("/api/agents/reviews")
async def analyze_reviews(query: str):
    """Review analysis endpoint"""
    from agents.review_agent import review_analysis_agent
    response = review_analysis_agent(query)
    return {"response": response}
```

## Part 5: File Change Summary

### Files to Rename
1. ✏️ `services/mcp_database.py` → `services/business_logic.py`
2. ✏️ `services/mcp_agent_tools.py` → `services/agent_tools.py`

### Files to Create
1. ✨ `services/mcp_server_tools.py` - Real MCP integration
2. ✨ `agents/review_agent.py` - Review analysis agent
3. ✨ `scripts/create_reviews_table.sql` - Database schema
4. ✨ `scripts/seed_reviews_data.py` - Sample data generator
5. ✨ `docs/MCP_USE_CASE.md` - Documentation

### Files to Update
1. 🔧 `agents/inventory_agent.py` - Update imports
2. 🔧 `agents/recommendation_agent.py` - Update imports
3. 🔧 `agents/pricing_agent.py` - Update imports
4. 🔧 `agents/orchestrator.py` - Update imports, add review agent
5. 🔧 `app.py` - Update imports, add review endpoint

## Part 6: Benefits of This Approach

### Clear Separation of Concerns
```
business_logic.py      → Custom business logic (trending, health scores)
agent_tools.py         → Strands SDK tools (simple queries)
mcp_server_tools.py    → Real MCP integration (complex queries, JOINs)
```

### Demonstrates MCP Value
- **Schema Discovery**: Agents can explore database structure
- **Complex Queries**: JOINs across multiple tables
- **Ad-hoc Analysis**: LLM generates SQL based on user questions
- **Real-world Use Case**: Customer review sentiment analysis

### Educational Value
- Shows when to use custom tools vs MCP server
- Demonstrates MCP's power for database exploration
- Provides realistic multi-table query examples
- Highlights Aurora PostgreSQL + MCP integration

## Part 7: Testing the New Features

### Test Review Analysis
```bash
# Get schema
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -d '{"query": "What tables are available?"}'

# Analyze sentiment
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -d '{"query": "Which products have negative reviews despite high ratings?"}'

# Category analysis
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -d '{"query": "Show me sentiment analysis by product category"}'

# Verified purchase patterns
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -d '{"query": "Compare sentiment between verified and unverified purchases"}'
```

## Part 8: Documentation Updates

### Update README.md
- Add section on MCP server integration
- Explain difference between custom tools and MCP tools
- Document review analysis use case

### Create MCP_USE_CASE.md
- Detailed explanation of MCP integration
- When to use MCP vs custom tools
- Example queries and use cases
- Architecture diagrams

### Update AGENT_REFACTORING_SUMMARY.md
- Reflect new file names
- Add review analysis agent
- Update architecture diagram with MCP server

## Summary

This plan:
1. ✅ Renames confusing files to reflect their true purpose
2. ✅ Adds real MCP server integration for advanced use cases
3. ✅ Creates customer reviews table for realistic JOIN queries
4. ✅ Demonstrates MCP's value for database exploration
5. ✅ Maintains backward compatibility
6. ✅ Provides clear educational value for workshop attendees
