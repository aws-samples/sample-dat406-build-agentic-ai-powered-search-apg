# 🤖 Blaize Bazaar Agent Examples

Complete guide to using the multi-agent system with real examples.

---

## 🎯 Orchestrator Agent

The orchestrator routes queries to specialized agents based on intent.

### Usage

```bash
cd lab2/backend
python -m agents.blaize_orchestrator
```

### How It Works

The orchestrator analyzes your query and delegates to:
- **Inventory Agent** - Stock levels, restocking, availability
- **Recommendation Agent** - Product suggestions, trending items
- **Pricing Agent** - Price analysis, deals, discounts

---

## 📦 Inventory Agent

Monitors stock levels, identifies restocking needs, and executes inventory updates.

### Example 1: Check Inventory Health

**Query:**
```
What products need restocking?
```

**Response:**
```
Inventory Overview:
- Total Products: 21,704
- Out of Stock: 0
- Low Stock: 1,916 (need attention)
- Healthy Stock: 19,788
- Health Score: 91

Top Priority Items:
1. ZUMIMALL Doorbell Camera (B07X134Z5Y) - 1 unit
2. Ring Alarm 8-piece kit (B07ZPMCW64) - 2 units
3. Schick Intuition Refills (B00HT6E31A) - 3 units

Recommended Actions:
- Restock high-demand items (100+ reviews): 50 units
- Restock medium-demand items (50-100 reviews): 30 units
```

### Example 2: Restock a Product

**Query:**
```
Restock product B07X134Z5Y with 50 units
```

**Response:**
```
✅ Restocking Confirmation

Successfully added 50 units to ZUMIMALL Doorbell Camera Wireless 2K FHD

Details:
- Product ID: B07X134Z5Y
- Previous stock: 1 unit (critically low)
- Added: 50 units
- New stock level: 51 units (healthy)
- Rating: 4.1 stars (4,173 reviews)
```

### Example 3: Check Low Stock Items

**Query:**
```
Show me all low stock items
```

**Response:**
```
Low Stock Alert (< 10 units):

Critical Items (1-3 units):
1. ZUMIMALL Doorbell Camera - 1 unit (4.1★, 4,173 reviews)
2. Ring Alarm 8-piece kit - 2 units (4.6★, 12,450 reviews)
3. Schick Intuition Refills - 3 units (4.5★, 8,234 reviews)

Medium Priority (4-9 units):
- 1,913 additional items need monitoring

Recommendation: Prioritize restocking items with 4+ stars and 100+ reviews
```

### Example 4: Bulk Restock Multiple Items

**Query:**
```
Restock B07X134Z5Y with 50 units and B07ZPMCW64 with 100 units
```

**Response:**
```
✅ Bulk Restocking Complete

1. ZUMIMALL Doorbell Camera (B07X134Z5Y)
   - Added: 50 units (1 → 51)

2. Ring Alarm 8-piece kit (B07ZPMCW64)
   - Added: 100 units (2 → 102)

Total units added: 150
Inventory health improved from 91 to 92
```

---

## 🎁 Recommendation Agent

Suggests trending products based on reviews, ratings, and popularity.

### Example 1: Get Trending Products

**Query:**
```
What are the trending products?
```

**Response:**
```
🔥 Top 10 Trending Products

1. Fire TV Stick 4K (4.7★, 456,789 reviews) - $49.99
   Trending Score: 2,146,907

2. Echo Dot (5th Gen) (4.8★, 234,567 reviews) - $49.99
   Trending Score: 1,125,922

3. Ring Video Doorbell (4.5★, 189,234 reviews) - $99.99
   Trending Score: 851,553

Criteria: Reviews × Stars, min 4.0★, min 50 reviews
```

### Example 2: Recommend Products by Category

**Query:**
```
Recommend gaming laptops
```

**Response:**
```
🎮 Gaming Laptop Recommendations

Top Picks:
1. ASUS ROG Strix G15 (4.6★, 3,456 reviews) - $1,299.99
   - RTX 3060, 16GB RAM, 512GB SSD
   
2. MSI GF63 Thin (4.4★, 2,789 reviews) - $899.99
   - GTX 1650, 8GB RAM, 256GB SSD

3. Acer Nitro 5 (4.5★, 4,123 reviews) - $1,099.99
   - RTX 3050, 16GB RAM, 512GB SSD
```

### Example 3: Best Deals

**Query:**
```
Show me the best deals under $50
```

**Response:**
```
💰 Best Deals Under $50

1. Fire TV Stick 4K - $49.99 (4.7★)
   Regular: $59.99 | Save: $10

2. Echo Dot (5th Gen) - $49.99 (4.8★)
   Regular: $59.99 | Save: $10

3. Anker PowerCore 20000 - $45.99 (4.6★)
   Regular: $59.99 | Save: $14
```

---

## 💰 Pricing Agent

Analyzes pricing data, identifies deals, and provides price statistics.

### Example 1: Price Statistics by Category

**Query:**
```
What are the price statistics for Electronics?
```

**Response:**
```
📊 Electronics Price Statistics

Overall:
- Total Products: 5,432
- Min Price: $9.99
- Max Price: $2,499.99
- Average Price: $287.45
- Median Price: $149.99

Top Categories:
1. Headphones: $89.99 avg (1,234 products)
2. Smartphones: $599.99 avg (456 products)
3. Laptops: $899.99 avg (789 products)
```

### Example 2: Find Best Value Products

**Query:**
```
What are the best value products with high ratings?
```

**Response:**
```
⭐ Best Value Products (4.5+ stars, under $100)

1. Anker PowerCore 20000 - $45.99 (4.6★, 23,456 reviews)
   Value Score: 102.3

2. TP-Link WiFi Extender - $29.99 (4.5★, 12,345 reviews)
   Value Score: 98.7

3. SanDisk 128GB SD Card - $19.99 (4.7★, 34,567 reviews)
   Value Score: 162.4

Value Score = (Stars × Reviews) / Price
```

### Example 3: Price Comparison

**Query:**
```
Compare prices for wireless headphones
```

**Response:**
```
🎧 Wireless Headphones Price Comparison

Budget ($20-$50):
- Anker Soundcore Q20 - $49.99 (4.5★)
- JBL Tune 510BT - $39.99 (4.4★)

Mid-Range ($50-$150):
- Sony WH-CH710N - $99.99 (4.6★)
- Beats Solo3 - $129.99 (4.5★)

Premium ($150+):
- Sony WH-1000XM5 - $399.99 (4.8★)
- Bose QuietComfort 45 - $329.99 (4.7★)
```

---

## 🔧 Custom MCP Tools

Extend Aurora PostgreSQL with business-specific functionality.

### Tool 1: get_trending_products

**HTTP Endpoint:**
```bash
curl http://localhost:8000/api/mcp/trending?limit=10
```

**Response:**
```json
{
  "status": "success",
  "count": 10,
  "products": [
    {
      "productId": "B08C1W5N87",
      "product_description": "Fire TV Stick 4K",
      "price": 49.99,
      "stars": 4.7,
      "reviews": 456789,
      "trending_score": 2146907
    }
  ],
  "metadata": {
    "criteria": "reviews * stars, min 4.0 stars, min 50 reviews",
    "limit": 10
  }
}
```

### Tool 2: get_inventory_health

**HTTP Endpoint:**
```bash
curl http://localhost:8000/api/mcp/inventory-health
```

**Response:**
```json
{
  "status": "success",
  "health_score": 91,
  "statistics": {
    "total_products": 21704,
    "out_of_stock": 0,
    "low_stock": 1916,
    "healthy_stock": 19788,
    "avg_quantity": 50.7,
    "total_quantity": 1099908
  },
  "critical_items": [
    {
      "productId": "B07X134Z5Y",
      "product_description": "ZUMIMALL Doorbell Camera",
      "stars": 4.1,
      "reviews": 4173,
      "quantity": 1
    }
  ],
  "alerts": [
    "⚠️ 1916 products need monitoring"
  ]
}
```

### Tool 3: get_price_statistics

**HTTP Endpoint:**
```bash
curl "http://localhost:8000/api/mcp/price-stats?category=Electronics"
```

**Response:**
```json
{
  "status": "success",
  "overall": {
    "total_products": 5432,
    "min_price": 9.99,
    "max_price": 2499.99,
    "avg_price": 287.45,
    "median_price": 149.99
  },
  "by_category": [
    {
      "category_name": "Headphones",
      "product_count": 1234,
      "min_price": 19.99,
      "max_price": 399.99,
      "avg_price": 89.99,
      "median_price": 79.99
    }
  ],
  "filter": "Electronics"
}
```

### Tool 4: restock_product

**HTTP Endpoint:**
```bash
curl -X POST http://localhost:8000/api/mcp/restock \
  -H "Content-Type: application/json" \
  -d '{"product_id": "B07X134Z5Y", "quantity": 50}'
```

**Response:**
```json
{
  "status": "success",
  "product_id": "B07X134Z5Y",
  "product_name": "ZUMIMALL Doorbell Camera Wireless 2K FHD",
  "old_quantity": 1,
  "added_quantity": 50,
  "new_quantity": 51,
  "message": "✅ Added 50 units to ZUMIMALL Doorbell Camera Wireless 2K FHD"
}
```

---

## 🔍 pgvector Semantic Search

Vector similarity search using Amazon Bedrock embeddings.

### Example 1: Semantic Product Search

**HTTP Endpoint:**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wireless noise cancelling headphones",
    "limit": 5,
    "min_similarity": 0.6
  }'
```

**SQL Query (Behind the Scenes):**
```sql
SELECT 
    "productId",
    product_description,
    price,
    stars,
    reviews,
    1 - (embedding <=> %s::vector) as similarity_score
FROM bedrock_integration.product_catalog
WHERE 1 - (embedding <=> %s::vector) >= 0.6
ORDER BY embedding <=> %s::vector
LIMIT 5;
```

**Response:**
```json
{
  "query": "wireless noise cancelling headphones",
  "results": [
    {
      "product": {
        "productId": "B08MVGF24M",
        "product_description": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "price": 399.99,
        "stars": 4.8,
        "reviews": 12456,
        "similarity_score": 0.89
      }
    },
    {
      "product": {
        "productId": "B09JQMJHXY",
        "product_description": "Bose QuietComfort 45 Bluetooth Wireless Noise Cancelling",
        "price": 329.99,
        "stars": 4.7,
        "reviews": 8934,
        "similarity_score": 0.87
      }
    }
  ],
  "total_results": 2,
  "search_time_ms": 87.3,
  "search_type": "semantic"
}
```

### Example 2: HNSW Index Performance

**Index Creation:**
```sql
CREATE INDEX product_embedding_hnsw_idx 
ON bedrock_integration.product_catalog 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Performance Metrics:**
- Search latency: 50-150ms average
- Similarity scores: 60-95% for relevant results
- Vector dimensions: 1024 (Cohere Embed English v3)
- Index type: HNSW (Hierarchical Navigable Small World)

### Example 3: Hybrid Search (Vector + Filters)

**Query:**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "gaming laptop",
    "limit": 10,
    "min_similarity": 0.6,
    "filters": {
      "min_stars": 4.5,
      "max_price": 1500,
      "category": "Computers & Tablets"
    }
  }'
```

**SQL Query:**
```sql
SELECT 
    "productId",
    product_description,
    price,
    stars,
    reviews,
    category_name,
    1 - (embedding <=> %s::vector) as similarity_score
FROM bedrock_integration.product_catalog
WHERE 1 - (embedding <=> %s::vector) >= 0.6
  AND stars >= 4.5
  AND price <= 1500
  AND category_name = 'Computers & Tablets'
ORDER BY embedding <=> %s::vector
LIMIT 10;
```

### Example 4: Autocomplete with Trigram Index

**HTTP Endpoint:**
```bash
curl "http://localhost:8000/api/autocomplete?q=headphone&limit=5"
```

**SQL Query:**
```sql
SELECT DISTINCT 
    LEFT(product_description, 60) as suggestion,
    category_name
FROM bedrock_integration.product_catalog
WHERE product_description ILIKE '%headphone%'
LIMIT 5;
```

**Trigram Index:**
```sql
CREATE INDEX product_description_trgm_idx 
ON bedrock_integration.product_catalog 
USING gin (product_description gin_trgm_ops);
```

**Response:**
```json
{
  "suggestions": [
    {
      "text": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
      "category": "Headphones"
    },
    {
      "text": "Bose QuietComfort 45 Bluetooth Wireless Headphones",
      "category": "Headphones"
    }
  ]
}
```

---

## 🚀 Quick Start Commands

### Start the Orchestrator CLI
```bash
cd lab2/backend
python -m agents.blaize_orchestrator
```

### Test Custom MCP Tools
```bash
# List all tools
curl http://localhost:8000/api/mcp/tools

# Get trending products
curl http://localhost:8000/api/mcp/trending?limit=10

# Check inventory health
curl http://localhost:8000/api/mcp/inventory-health

# Get price statistics
curl http://localhost:8000/api/mcp/price-stats

# Restock a product
curl -X POST http://localhost:8000/api/mcp/restock \
  -H "Content-Type: application/json" \
  -d '{"product_id": "B07X134Z5Y", "quantity": 50}'
```

### Semantic Search
```bash
# Search products
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "bluetooth headphones", "limit": 10}'

# Autocomplete
curl "http://localhost:8000/api/autocomplete?q=laptop&limit=5"

# Browse by category (fast, no embeddings)
curl "http://localhost:8000/api/products/category/Gaming%20Consoles?limit=10"
```

---

## 📊 Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│              (Routes to specialized agents)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Inventory   │ │Recommendation│ │   Pricing    │
│    Agent     │ │    Agent     │ │    Agent     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
              ┌──────────────────┐
              │  Custom MCP Tools │
              │  - get_trending  │
              │  - get_inventory │
              │  - get_pricing   │
              │  - restock       │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │ Aurora PostgreSQL│
              │   + pgvector     │
              │   + HNSW Index   │
              └──────────────────┘
```

---

**Built with ❤️ for AWS re:Invent 2025 | DAT406 Workshop**
