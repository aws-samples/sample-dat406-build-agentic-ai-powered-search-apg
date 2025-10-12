# Aurora PostgreSQL MCP Server Use Case

## Overview
This document explains how we use Aurora PostgreSQL as an MCP (Model Context Protocol) server to enable agents to perform complex database operations, particularly JOIN queries across multiple tables.

## Architecture: Two Approaches

### Approach 1: Custom Business Logic Tools (Current)
```
Agent → @tool (Strands SDK) → BusinessLogic class → DatabaseService → Aurora
```

**Use Cases:**
- Pre-defined business logic (trending scores, health metrics)
- Optimized queries with specific aggregations
- Fast, predictable operations
- Type-safe with known schemas

**Files:**
- `services/business_logic.py` - Custom business logic
- `services/agent_tools.py` - Strands SDK tool wrappers

### Approach 2: MCP Server Integration (New)
```
Agent → @tool (Strands SDK) → MCP Server Tools → Aurora PostgreSQL
```

**Use Cases:**
- Ad-hoc database exploration
- Complex JOIN queries across tables
- Schema discovery
- Dynamic query generation by LLM

**Files:**
- `services/mcp_server_tools.py` - MCP server integration
- `agents/review_agent.py` - Review analysis agent

## Real-World Use Case: Customer Review Analysis

### Business Problem
Product catalog lacks customer sentiment insights. We need to:
1. Join product data with customer reviews
2. Analyze sentiment by category
3. Find products with review/rating mismatches
4. Generate actionable insights

### Solution: MCP Server + JOIN Queries

#### Database Schema
```sql
-- Existing table
product_catalog (
    productId PK,
    product_description,
    price,
    stars,
    reviews,
    category_name,
    quantity
)

-- New table for MCP demonstration
customer_reviews (
    review_id PK,
    product_id FK → product_catalog.productId,
    customer_name,
    review_text,
    sentiment (positive/negative/neutral),
    verified_purchase,
    helpful_votes,
    review_date
)
```

## MCP Server Tools

### 1. mcp_run_query(sql)
Execute complex SQL queries including JOINs, CTEs, aggregations.

**Example: Find products with negative reviews despite high ratings**
```sql
SELECT 
    p."productId",
    p.product_description,
    p.stars,
    COUNT(r.review_id) as negative_reviews,
    STRING_AGG(r.review_text, ' | ') as sample_reviews
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r 
    ON p."productId" = r.product_id
WHERE r.sentiment = 'negative'
  AND p.stars >= 4.0
GROUP BY p."productId", p.product_description, p.stars
ORDER BY negative_reviews DESC
LIMIT 10;
```

**Agent Usage:**
```python
agent = Agent(tools=[mcp_run_query])
response = agent("Which products have negative reviews despite high ratings?")
# Agent generates and executes the JOIN query above
```

### 2. mcp_get_schema(table_name)
Discover table structure dynamically.

**Example:**
```python
mcp_get_schema("customer_reviews")
# Returns: columns, data types, constraints
```

### 3. mcp_list_tables()
List all available tables in the database.

**Example:**
```python
mcp_list_tables()
# Returns: ["product_catalog", "customer_reviews"]
```

## Example Queries Enabled by MCP

### Query 1: Category Sentiment Analysis
```sql
SELECT 
    p.category_name,
    COUNT(r.review_id) as total_reviews,
    COUNT(CASE WHEN r.sentiment = 'positive' THEN 1 END) as positive,
    COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) as negative,
    ROUND(AVG(p.stars), 2) as avg_rating
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r 
    ON p."productId" = r.product_id
GROUP BY p.category_name
ORDER BY total_reviews DESC
LIMIT 15;
```

**Business Value:** Identify categories with sentiment issues

### Query 2: Verified vs Unverified Purchase Sentiment
```sql
SELECT 
    r.verified_purchase,
    r.sentiment,
    COUNT(*) as review_count,
    ROUND(AVG(r.helpful_votes), 2) as avg_helpful_votes
FROM bedrock_integration.customer_reviews r
GROUP BY r.verified_purchase, r.sentiment
ORDER BY r.verified_purchase DESC, r.sentiment;
```

**Business Value:** Understand if verified purchases have different sentiment patterns

### Query 3: Products Needing Attention
```sql
SELECT 
    p."productId",
    p.product_description,
    p.stars,
    p.quantity,
    COUNT(r.review_id) as total_reviews,
    COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) as negative_count,
    ROUND(
        COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END)::numeric / 
        COUNT(r.review_id) * 100, 
        2
    ) as negative_percentage
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r 
    ON p."productId" = r.product_id
GROUP BY p."productId", p.product_description, p.stars, p.quantity
HAVING COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) >= 2
ORDER BY negative_percentage DESC, p.stars DESC
LIMIT 20;
```

**Business Value:** Prioritize products for quality improvement

## Review Analysis Agent

### Agent Configuration
```python
@tool
def review_analysis_agent(query: str) -> str:
    agent = Agent(
        model="claude-sonnet-4",
        tools=[
            mcp_run_query,      # Complex JOINs
            mcp_get_schema,     # Schema discovery
            mcp_list_tables,    # Table listing
            run_query           # Simple queries
        ]
    )
    return agent(query)
```

### Example Interactions

**User:** "Which products have negative reviews despite high ratings?"

**Agent Reasoning:**
1. Calls `mcp_list_tables()` to see available tables
2. Calls `mcp_get_schema("customer_reviews")` to understand structure
3. Generates JOIN query to find mismatches
4. Calls `mcp_run_query(sql)` to execute
5. Formats results with insights

**Response:**
```
Found 5 products with negative reviews despite 4+ star ratings:

1. Sony WH-1000XM5 (4.8 stars, 3 negative reviews)
   - "Product stopped working after a week"
   - "Overpriced for what you get"
   
2. Bose QC45 (4.7 stars, 2 negative reviews)
   - "Doesn't work as advertised"
   
Recommendation: Investigate quality control for these high-rated products.
```

## When to Use MCP vs Custom Tools

### Use MCP Server Tools When:
- ✅ Need ad-hoc database exploration
- ✅ Complex JOIN queries across multiple tables
- ✅ Schema discovery required
- ✅ LLM should generate SQL dynamically
- ✅ Unpredictable query patterns

### Use Custom Business Logic Tools When:
- ✅ Pre-defined business logic (trending scores)
- ✅ Optimized, frequently-used queries
- ✅ Type-safe operations with known schemas
- ✅ Performance-critical operations
- ✅ Predictable query patterns

## Setup Instructions

### 1. Create Reviews Table
```bash
psql -h your-aurora-cluster.region.rds.amazonaws.com \
     -U postgres -d postgres \
     -f lab2/scripts/create_reviews_table.sql
```

### 2. Seed Review Data
```bash
cd lab2/backend
python ../scripts/seed_reviews_data.py
```

### 3. Test Review Agent
```bash
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me sentiment analysis by category"}'
```

## Benefits of MCP Integration

1. **Dynamic Query Generation**: LLM generates SQL based on natural language
2. **Schema Discovery**: Agents explore database structure automatically
3. **Complex Analysis**: JOIN queries across multiple tables
4. **Flexibility**: No need to pre-define all possible queries
5. **Educational Value**: Demonstrates Aurora PostgreSQL + MCP power

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Review Analysis Agent                  │
│  "Which products have negative reviews?"                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│mcp_run_query │ │mcp_get   │ │mcp_list      │
│              │ │_schema   │ │_tables       │
└──────┬───────┘ └────┬─────┘ └──────┬───────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
                      ▼
        ┌─────────────────────────┐
        │  Aurora PostgreSQL      │
        │                         │
        │  ┌──────────────────┐   │
        │  │ product_catalog  │   │
        │  └────────┬─────────┘   │
        │           │             │
        │           │ JOIN        │
        │           │             │
        │  ┌────────▼─────────┐   │
        │  │ customer_reviews │   │
        │  └──────────────────┘   │
        └─────────────────────────┘
```

## Performance Considerations

- **Indexes**: Created on product_id, sentiment, review_date
- **Query Optimization**: Use LIMIT clauses for large result sets
- **Connection Pooling**: Reuse database connections
- **Caching**: Consider caching frequent queries (future enhancement)

## Future Enhancements

1. **Semantic Search on Reviews**: Add embeddings to review_text
2. **Real-time Sentiment**: Integrate with Amazon Comprehend
3. **Review Summarization**: Use Bedrock to summarize reviews
4. **Trend Analysis**: Track sentiment changes over time
5. **Product Recommendations**: Use reviews to improve recommendations
