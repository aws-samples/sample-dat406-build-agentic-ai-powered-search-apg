# Sample Queries Guide - DAT406 Workshop

## Quick Reference: Test All Agents

### 1. Inventory Agent Queries

#### Check Low Stock Products
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What products are low on stock?",
    "agent_type": "inventory"
  }'
```

#### Get Inventory Health Report
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Give me an inventory health report",
    "agent_type": "inventory"
  }'
```

#### Restock a Product
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Restock product B001 with 50 units",
    "agent_type": "inventory"
  }'
```

### 2. Recommendation Agent Queries

#### Find Wireless Headphones
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Recommend wireless headphones under $200",
    "agent_type": "recommendation"
  }'
```

#### Gaming Accessories
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need gaming accessories for my PC setup",
    "agent_type": "recommendation"
  }'
```

#### Smart Home Devices
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me smart home security cameras",
    "agent_type": "recommendation"
  }'
```

### 3. Pricing Agent Queries

#### Best Deals in Electronics
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the best deals in electronics?",
    "agent_type": "pricing"
  }'
```

#### Bundle Opportunities
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Suggest bundle deals for headphones and accessories",
    "agent_type": "pricing"
  }'
```

#### Price Analysis by Category
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze pricing for vacuum cleaners",
    "agent_type": "pricing"
  }'
```

### 4. Orchestrator Queries (Multi-Agent)

#### Complex Query - Trending + Low Stock
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me trending products that are low on stock",
    "agent_type": "orchestrator"
  }'
```

#### Complex Query - Recommendations + Pricing
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Recommend noise-canceling headphones and tell me which ones are the best value",
    "agent_type": "orchestrator"
  }'
```

#### Complex Query - All Agents
```bash
curl -X POST "http://localhost:8000/api/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are our best-selling products that need restocking, and what deals can we offer?",
    "agent_type": "orchestrator"
  }'
```

### 5. Review Analysis Agent Queries (After Setup)

#### Products with Negative Reviews
```bash
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which products have negative reviews despite high ratings?"
  }'
```

#### Sentiment by Category
```bash
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me sentiment analysis by product category"
  }'
```

#### Verified Purchase Analysis
```bash
curl -X POST "http://localhost:8000/api/agents/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare sentiment between verified and unverified purchases"
  }'
```

## Direct SQL Queries (via run_query tool)

### Query 1: Top Rated Products by Category
```sql
SELECT 
    category_name,
    product_description,
    stars,
    reviews,
    price,
    quantity
FROM bedrock_integration.product_catalog
WHERE stars >= 4.5 
  AND reviews > 100
  AND quantity > 0
ORDER BY category_name, stars DESC, reviews DESC
LIMIT 20;
```

### Query 2: Price Distribution by Category
```sql
SELECT 
    category_name,
    COUNT(*) as product_count,
    ROUND(MIN(price), 2) as min_price,
    ROUND(MAX(price), 2) as max_price,
    ROUND(AVG(price), 2) as avg_price,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price), 2) as median_price
FROM bedrock_integration.product_catalog
WHERE quantity > 0
GROUP BY category_name
ORDER BY product_count DESC
LIMIT 15;
```

### Query 3: Inventory Alert - Critical Items
```sql
SELECT 
    "productId",
    product_description,
    category_name,
    quantity,
    stars,
    reviews,
    price
FROM bedrock_integration.product_catalog
WHERE quantity < 10
  AND stars >= 4.0
  AND reviews > 50
ORDER BY quantity ASC, reviews DESC
LIMIT 20;
```

### Query 4: Best Value Products (High Rating, Low Price)
```sql
SELECT 
    "productId",
    product_description,
    category_name,
    price,
    stars,
    reviews,
    ROUND((stars * reviews) / NULLIF(price, 0), 2) as value_score
FROM bedrock_integration.product_catalog
WHERE quantity > 0
  AND stars >= 4.0
  AND price > 0
ORDER BY value_score DESC
LIMIT 20;
```

## MCP Queries (After Reviews Table Setup)

### Query 5: Products with Review/Rating Mismatch
```sql
SELECT 
    p."productId",
    p.product_description,
    p.stars,
    COUNT(r.review_id) as total_reviews,
    COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) as negative_reviews,
    ROUND(
        COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END)::numeric / 
        COUNT(r.review_id) * 100, 
        2
    ) as negative_percentage
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r 
    ON p."productId" = r.product_id
WHERE p.stars >= 4.0
GROUP BY p."productId", p.product_description, p.stars
HAVING COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) >= 2
ORDER BY negative_percentage DESC
LIMIT 10;
```

### Query 6: Category Sentiment Analysis
```sql
SELECT 
    p.category_name,
    COUNT(r.review_id) as total_reviews,
    COUNT(CASE WHEN r.sentiment = 'positive' THEN 1 END) as positive,
    COUNT(CASE WHEN r.sentiment = 'neutral' THEN 1 END) as neutral,
    COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) as negative,
    ROUND(AVG(p.stars), 2) as avg_rating,
    ROUND(
        COUNT(CASE WHEN r.sentiment = 'positive' THEN 1 END)::numeric / 
        COUNT(r.review_id) * 100, 
        2
    ) as positive_percentage
FROM bedrock_integration.product_catalog p
JOIN bedrock_integration.customer_reviews r 
    ON p."productId" = r.product_id
GROUP BY p.category_name
ORDER BY total_reviews DESC
LIMIT 15;
```

### Query 7: Verified vs Unverified Purchase Sentiment
```sql
SELECT 
    r.verified_purchase,
    r.sentiment,
    COUNT(*) as review_count,
    ROUND(AVG(r.helpful_votes), 2) as avg_helpful_votes,
    ROUND(
        COUNT(*)::numeric / 
        SUM(COUNT(*)) OVER (PARTITION BY r.verified_purchase) * 100,
        2
    ) as percentage
FROM bedrock_integration.customer_reviews r
GROUP BY r.verified_purchase, r.sentiment
ORDER BY r.verified_purchase DESC, r.sentiment;
```

### Query 8: Most Helpful Reviews
```sql
SELECT 
    p.product_description,
    r.customer_name,
    r.review_text,
    r.sentiment,
    r.helpful_votes,
    r.verified_purchase,
    r.review_date
FROM bedrock_integration.customer_reviews r
JOIN bedrock_integration.product_catalog p 
    ON r.product_id = p."productId"
WHERE r.helpful_votes > 10
ORDER BY r.helpful_votes DESC
LIMIT 20;
```

## Python Test Script

Save as `test_agents.py`:

```python
#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_agent(agent_type, query):
    """Test an agent with a query"""
    print(f"\n{'='*60}")
    print(f"Agent: {agent_type.upper()}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    response = requests.post(
        f"{BASE_URL}/api/agents/query",
        json={"query": query, "agent_type": agent_type}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse:\n{result['response']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

# Test all agents
test_agent("inventory", "What products are low on stock?")
test_agent("recommendation", "Recommend wireless headphones under $200")
test_agent("pricing", "What are the best deals in electronics?")
test_agent("orchestrator", "Show me trending products that need restocking")
```

Run with:
```bash
python test_agents.py
```

## Natural Language Queries (UI/Chat Interface)

### Customer Shopping Queries

#### 1. Gift Shopping
```
"I need a gift for my dad who loves tech gadgets, budget around $150"
"What's a good birthday present for a teenager who games?"
"Help me find a Mother's Day gift - she likes smart home devices"
```

#### 2. Specific Product Needs
```
"I work from home and need good headphones for video calls"
"Looking for a vacuum that works well with pet hair"
"Need a security camera for my front door that works at night"
"What's the best fitness tracker for running?"
```

#### 3. Budget-Conscious Shopping
```
"Show me the best wireless earbuds under $100"
"What are your cheapest noise-canceling headphones?"
"I want quality headphones but don't want to spend more than $75"
"Best value gaming mouse?"
```

#### 4. Comparison Shopping
```
"Compare Sony and Bose noise-canceling headphones"
"What's better - Ring or Nest security cameras?"
"Should I get AirPods or Sony earbuds?"
"Which robot vacuum is best - Roomba or Shark?"
```

#### 5. Feature-Based Search
```
"I need headphones with at least 20 hours battery life"
"Show me cameras with night vision and motion detection"
"Looking for a smartwatch that tracks sleep"
"Need a portable speaker that's waterproof"
```

#### 6. Use Case Queries
```
"What do I need for a home office setup?"
"I'm starting a podcast, what equipment should I get?"
"Setting up a smart home - where do I start?"
"Best products for college dorm room?"
```

#### 7. Trending & Popular
```
"What are your most popular products right now?"
"Show me what's trending in electronics"
"What are people buying for Christmas?"
"Best sellers in headphones?"
```

#### 8. Quality-Focused
```
"Show me only 5-star rated products"
"What are your highest quality headphones?"
"I want the best, price doesn't matter"
"Most reliable security cameras?"
```

#### 9. Brand Preferences
```
"Show me all Sony products"
"Do you have any Apple accessories?"
"What Anker products do you carry?"
"Looking for Samsung electronics"
```

#### 10. Problem-Solving
```
"My current headphones hurt my ears, need comfortable ones"
"I keep losing my earbuds, need something with a case"
"My vacuum doesn't pick up dog hair well"
"Need a camera that's easy to install"
```

### Business/Admin Queries

#### 11. Inventory Management
```
"Which products are running low?"
"Show me out of stock items"
"What needs to be reordered urgently?"
"Inventory status for headphones category"
```

#### 12. Sales Analysis
```
"What are our top selling products this month?"
"Which categories are performing best?"
"Show me products with high ratings but low sales"
"What's not selling well?"
```

#### 13. Pricing Strategy
```
"What products should we discount?"
"Show me overpriced items compared to competitors"
"Which products have the best profit margins?"
"Suggest bundle deals for gaming accessories"
```

#### 14. Customer Insights (with Reviews)
```
"What are customers complaining about?"
"Show me products with negative reviews"
"Which products have the best customer feedback?"
"Are verified buyers happier than non-verified?"
```

#### 15. Operational Queries
```
"How many products do we have in total?"
"What's our average product rating?"
"Show me all categories"
"Which products were added recently?"
```

## Sample UI Chat Conversations

### Conversation 1: Gift Shopping
```
User: "I need a gift for my dad who loves tech, around $150"

Agent: "Great! I found some perfect tech gifts for your dad:

1. Sony WH-CH720N Headphones ($149.99) ⭐ 4.6
   - Wireless noise-canceling
   - 35-hour battery life
   - Perfect for music lovers

2. Anker PowerCore 26800 ($139.99) ⭐ 4.7
   - Massive battery capacity
   - Charges multiple devices
   - Great for travelers

3. Ring Video Doorbell ($129.99) ⭐ 4.5
   - Smart home security
   - See visitors from phone
   - Easy installation

All are highly rated and in stock! Which interests you most?"

User: "Tell me more about the Sony headphones"

Agent: "The Sony WH-CH720N are excellent mid-range headphones:

✅ Features:
- Active Noise Cancellation
- 35-hour battery (50 hours without ANC)
- Lightweight and comfortable
- Multipoint connection (2 devices)
- Voice assistant compatible

⭐ Customer Reviews: 4.6 stars (2,341 reviews)
💰 Price: $149.99 (great value!)
📦 In Stock: Ready to ship

Customers love the comfort and battery life. Perfect for daily use!"
```

### Conversation 2: Problem Solving
```
User: "My vacuum doesn't pick up dog hair well"

Agent: "I understand the struggle! Here are vacuums specifically great for pet hair:

1. Shark Navigator Lift-Away ($199.99) ⭐ 4.7
   - Anti-allergen seal
   - Pet power brush included
   - 1,234 reviews mention 'excellent for pet hair'

2. Bissell Pet Hair Eraser ($149.99) ⭐ 4.6
   - Tangle-free brush roll
   - Specialized pet tools
   - Easy to empty

3. Dyson V8 Animal ($299.99) ⭐ 4.8
   - Powerful suction
   - Converts to handheld
   - HEPA filtration

All have 4.5+ stars and specifically designed for pet owners!"
```

### Conversation 3: Budget Shopping
```
User: "Best wireless earbuds under $100?"

Agent: "Here are the top-rated wireless earbuds under $100:

1. Anker Soundcore Life P3 ($79.99) ⭐ 4.6
   - Active noise cancellation
   - 8,932 reviews - best value!
   - 35-hour total battery

2. JLab Go Air Pop ($24.99) ⭐ 4.4
   - Budget-friendly
   - 8-hour battery
   - Great for workouts

3. Skullcandy Dime ($29.99) ⭐ 4.3
   - Compact design
   - IPX4 water resistant
   - Good sound quality

The Anker Soundcore Life P3 offers the best features for the price!"
```

### Conversation 4: Multi-Agent (Complex)
```
User: "What are your best-selling headphones that are running low on stock?"

Agent: "Let me check our trending products and inventory...

🔥 High-Demand Headphones with Low Stock:

1. Sony WH-1000XM5 ($399.99) ⭐ 4.8
   ⚠️ Only 3 units left!
   - #1 trending in headphones
   - 1,234 reviews
   - Premium noise cancellation

2. Bose QC45 ($329.99) ⭐ 4.7
   ⚠️ Only 5 units left!
   - #2 trending
   - 892 reviews
   - Legendary comfort

💡 Recommendation: These are flying off shelves! 
Order soon or consider these in-stock alternatives:
- Sony WH-CH720N ($149.99) - 50+ in stock
- Anker Soundcore Q30 ($79.99) - 100+ in stock

Would you like me to reserve one for you?"
```

### Conversation 5: Comparison
```
User: "Compare Sony WH-1000XM5 vs Bose QC45"

Agent: "Great question! Here's a detailed comparison:

🎧 Sony WH-1000XM5 ($399.99) ⭐ 4.8
✅ Better noise cancellation
✅ Longer battery (30 hours)
✅ More advanced features
❌ Slightly more expensive
❌ Don't fold as compact

🎧 Bose QC45 ($329.99) ⭐ 4.7
✅ More comfortable for long wear
✅ Better for phone calls
✅ Folds more compact
❌ Shorter battery (24 hours)
❌ Fewer features

🏆 Winner depends on your needs:
- Best overall: Sony (if budget allows)
- Best comfort: Bose
- Best value: Sony WH-CH720N ($149.99)

Both are excellent choices with 4.7+ stars!"
```

## Expected Response Examples

### Inventory Agent Response
```json
{
  "response": "📊 Inventory Health Report:\n\nHealth Score: 87/100\n\n⚠️ Critical Items (Low Stock + High Demand):\n1. Sony WH-1000XM5 - Only 3 units left (4.8★, 1,234 reviews)\n2. Bose QC45 - Only 5 units left (4.7★, 892 reviews)\n\n📈 Statistics:\n- Total products: 21,704\n- Out of stock: 234\n- Low stock (<10): 567\n\nRecommendation: Restock high-demand items immediately.",
  "agent_type": "inventory",
  "success": true
}
```

### Recommendation Agent Response
```json
{
  "response": "Here are my top 5 wireless headphone recommendations under $200:\n\n1. Sony WH-CH720N ($149.99) - 4.6★, 2,341 reviews\n   ✓ Excellent noise cancellation\n   ✓ 35-hour battery life\n\n2. Anker Soundcore Q30 ($79.99) - 4.5★, 8,932 reviews\n   ✓ Best value option\n   ✓ Multi-mode ANC\n\n[...3 more products...]\n\nAll products are in stock and highly rated!",
  "agent_type": "recommendation",
  "success": true
}
```

### Pricing Agent Response
```json
{
  "response": "💰 Best Deals in Electronics:\n\n🎯 Bundle Deal:\n- Logitech Webcam + Microphone: $89.99 (Save $30)\n\n⚡ Best Value:\n- Anker PowerBank 20000mAh: $39.99 (4.7★, 12K reviews)\n- Value score: 1,200 (rating × reviews / price)\n\n🔥 Discount Opportunity:\n- Samsung Galaxy Buds: Suggest 15% off to move inventory\n\nExpected impact: 25% increase in sales velocity",
  "agent_type": "pricing",
  "success": true
}
```

## Tips for Natural Language Testing

### Best Practices
1. **Be Conversational**: Use natural language like talking to a person
2. **Provide Context**: "I need X for Y" works better than just "show me X"
3. **Ask Follow-ups**: Agents maintain conversation context
4. **Be Specific**: "wireless headphones under $200" vs "headphones"
5. **Test Edge Cases**: Misspellings, vague requests, impossible criteria

### Query Patterns That Work Well
```
✅ "I need [product] for [use case], budget [amount]"
✅ "Show me [product] with [feature]"
✅ "Compare [product A] vs [product B]"
✅ "What's the best [product] for [situation]?"
✅ "Help me find [product] that [requirement]"
```

### Query Patterns to Avoid
```
❌ Single words: "headphones" (too vague)
❌ SQL-like: "SELECT * FROM products" (use natural language)
❌ Too many requirements: "cheap, high-quality, wireless, noise-canceling, comfortable, long battery" (prioritize)
```

## Tips for Testing

1. **Start Simple**: Test individual agents before orchestrator
2. **Check Logs**: Monitor backend logs for tool calls
3. **Vary Queries**: Try different phrasings to see agent reasoning
4. **Enable Thinking**: Add `"enable_thinking": true` to see Claude's reasoning process
5. **Test Edge Cases**: Try queries with no results, ambiguous requests
6. **Use Natural Language**: Write queries as you would speak them

## Troubleshooting

**Agent returns error:**
- Check database connection
- Verify tools are initialized (`set_db_service` called)
- Check backend logs for stack traces

**No results returned:**
- Verify products exist matching criteria
- Check SQL syntax in agent prompts
- Test SQL directly in database first

**Slow responses:**
- Check database indexes
- Monitor query execution time
- Consider caching frequent queries
