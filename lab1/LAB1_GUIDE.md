# Lab 1: Semantic Product Search with pgvector 0.8.0

**Duration:** 20-25 minutes  
**Goal:** Build a production-ready semantic search system using Amazon Aurora PostgreSQL with pgvector 0.8.0 and Amazon Bedrock Titan embeddings

---

## 🎯 What You'll Build

A semantic search system that understands natural language queries and finds products by meaning, not just keywords:

**Example Queries:**
- "something to keep my drinks cold" → Finds coolers, insulated bottles, ice packs
- "gift for someone who loves reading" → Finds e-readers, book lights, reading accessories
- "make my home more secure" → Finds security cameras, smart locks, alarm systems
- "wireless noise cancelling headphones" → Works with both conceptual and technical queries

**Key Difference from Keyword Search:**
- ❌ **Keyword Search:** "keep drinks cold" → NO RESULTS (exact words not in product descriptions)
- ✅ **Semantic Search:** "keep drinks cold" → FINDS coolers, bottles, ice makers (understands the concept!)

---

## 📋 Prerequisites

Before starting, ensure:

✅ Workshop environment fully deployed  
✅ Aurora PostgreSQL cluster running with pgvector 0.8.0  
✅ Amazon Bedrock access enabled in us-west-2  
✅ Code Editor accessible via CloudFront URL  
✅ Database credentials configured (via Secrets Manager or .env)

---

## 🚀 Step 1: Start Jupyter Lab (2 minutes)

### Access Your Workshop Environment

1. **Via CloudFront URL:**
   - Navigate to your CloudFront URL (provided in workshop instructions)
   - Authenticate with the password: `workshop` (or as provided)

2. **Start Jupyter Lab:**
   ```bash
   # Open a terminal in Code Editor
   start-jupyter
   ```

   **Expected output:**
   ```
   Starting Jupyter Lab on http://localhost:8888
   [I 2025-01-07 10:00:00.000 ServerApp] Jupyter Server is running at:
   [I 2025-01-07 10:00:00.000 ServerApp] http://localhost:8888/lab?token=...
   ```

3. **Access Jupyter:**
   - Click the URL shown in terminal, OR
   - Navigate to: `<CloudFront-URL>/ports/8888/`
   - Jupyter Lab will open in your browser

---

## 📓 Step 2: Open the Notebook (1 minute)

In Jupyter Lab:

1. **Navigate** to the `lab1/` folder in the left sidebar
2. **Open** `Lab_1_Enhanced_Final.ipynb`
3. **Select kernel:** Choose **Python 3.13** when prompted
   - If kernel selection doesn't appear, go to: Kernel → Change Kernel → Python 3.13

---

## 🔬 Step 3: Execute Notebook Cells (15-20 minutes)

### Quick Start Option

**For fastest completion:**
1. Go to menu: **Cell → Run All**
2. Wait ~6-7 minutes for all processing to complete
3. Scroll down to the interactive search widget
4. Try the example queries to see keyword vs. semantic search

### Understanding Each Section

If you prefer to understand each step:

#### **Section 1: Setup & Dependencies (1 minute)**
- Installs required Python packages from `requirements.txt`
- Key packages: boto3, psycopg, pgvector, pandas, ipywidgets

**Action:** Run the first few cells to import libraries

#### **Section 2: Database Connection (2 minutes)**

⚠️ **IMPORTANT UPDATE:** The notebook's database connection cell has been improved!

**What the updated cell does:**
1. **First:** Checks environment variables (from bootstrap scripts)
2. **Second:** Falls back to AWS Secrets Manager (if `DB_SECRET_ARN` is set)
3. **Third:** Explicitly loads from `.env` file

**The old hardcoded fallback has been removed** for security and portability.

**If you see connection errors:**
```bash
# Debug in terminal:
echo $DB_SECRET_ARN
cat /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.env
aws secretsmanager get-secret-value --secret-id $DB_SECRET_ARN
```

**Key Learning:** 
- Connection pooling with psycopg3 for optimized throughput
- pgvector 0.8.0 automatic features (no manual tuning needed!)

#### **Section 3: Load Product Data (2 minutes)**
- Loads **21,704 curated products** from CSV
- Data quality checks (removes duplicates, handles missing values)
- Inserts into `bedrock_integration.product_catalog` table

**What you'll see:**
```
📊 Dataset Statistics:
   • Valid products: 21,704
   • Categories: 15
   • Avg price: $45.67
   • Avg rating: 4.2/5.0 ⭐
   • Total reviews: 1,234,567
```

**Key Learning:** Bulk data loading with UPSERT for idempotency

#### **Section 4: Generate Embeddings (3-4 minutes)**
- Uses **Amazon Bedrock Titan Text Embeddings V2**
- Generates **1024-dimensional vectors** for each product description
- Parallel processing with 10 workers (~3 minutes for 21,704 products)

**What you'll see:**
```
🔄 Generating embeddings... (ETA: ~3 minutes)
✅ Embeddings generated successfully!
   • Total time: 180.5s
   • Processing rate: 120.3 products/sec
   • Vector dimensions: 1024
   • Model: Amazon Titan Text Embeddings V2
```

**Key Learning:** 
- Vector embeddings capture semantic meaning
- Similar products have similar vectors (close in high-dimensional space)
- Example: "wireless headphones" and "Bluetooth earbuds" → similar vectors

#### **Section 5: Create HNSW Index (1-2 minutes)**
- Creates **HNSW (Hierarchical Navigable Small World)** vector index
- Parameters: `m=16`, `ef_construction=64`
- Enables **sub-10ms similarity search** at scale

**What you'll see:**
```
🔨 Building performance indexes...

🎯 HNSW Vector Index: 45.23s
🔍 Full-Text Search (GIN): 12.34s
📂 Category B-Tree: 2.15s
💰 Price Range: 1.87s

✅ All indexes created and optimized!
```

**Key Learning:**
- HNSW enables fast approximate nearest neighbor search
- pgvector 0.8.0's **iterative scanning** ensures complete results automatically
- No manual `ef_search` tuning needed!

#### **Section 6: Interactive Search Widget (10+ minutes of exploration)**

This is the main attraction! A side-by-side comparison of keyword vs. semantic search.

**Features:**
- 🎮 **Interactive UI** with example queries
- 🔴 **Keyword Search (Red):** Traditional text matching
- 🟢 **Semantic Search (Green):** AI-powered meaning-based matching
- 📊 **Performance metrics:** Query latency and result counts
- 🖼️ **Product cards:** Images, prices, ratings, similarity scores

**Try These Example Queries (Designed to Show Keyword Search Failures):**

1. **"something to keep my drinks cold"**
   - ❌ Keyword: NO RESULTS (words not in descriptions)
   - ✅ Semantic: Finds coolers, insulated bottles, ice packs

2. **"gift for someone who loves reading"**
   - ❌ Keyword: NO RESULTS (conceptual query)
   - ✅ Semantic: Finds e-readers, book lights, reading accessories

3. **"make my home more secure"**
   - ❌ Keyword: NO RESULTS (no exact phrase match)
   - ✅ Semantic: Finds security cameras, smart locks, alarms

4. **"wireless noise cancelling headphones"**
   - ✅ Keyword: WORKS (exact vocabulary match)
   - ✅ Semantic: ALSO WORKS (understands intent)

5. **"portable power for camping"**
   - ❌ Keyword: FAILS (doesn't know camping = outdoor)
   - ✅ Semantic: Finds power banks, solar chargers, generators

**Key Insight:** Semantic search works for ALL query types, while keyword search only works when users guess the exact product terminology!

---

## 🎓 Key Concepts Explained

### Vector Embeddings
**What:** Numerical representations of text in high-dimensional space (1024 dimensions)  
**How:** AI models convert text → vectors that capture semantic meaning  
**Why:** Similar concepts have similar vectors, enabling mathematical similarity search

**Example:**
```
"wireless headphones"     → [0.23, -0.45, 0.67, ...]  
"Bluetooth earbuds"       → [0.24, -0.44, 0.66, ...]  ← Very similar!
"refrigerator"            → [-0.89, 0.12, -0.34, ...] ← Very different!
```

### pgvector 0.8.0 Features

#### 1. **Automatic Iterative Index Scanning**
- **Problem (Old):** HNSW might miss results with strict filters
- **Solution (New):** Automatically expands search until all matches found
- **Benefit:** Complete results without manual tuning

#### 2. **Improved Query Cost Estimation**
- PostgreSQL's query planner makes smarter decisions
- Better index usage and execution paths

#### 3. **Relaxed Ordering Mode**
- Faster queries with minimal accuracy trade-off
- Perfect for production workloads
- Enable with: `SET hnsw.iterative_scan = 'relaxed_order';`

### HNSW Index

**Full Name:** Hierarchical Navigable Small World  
**Type:** Graph-based algorithm for approximate nearest neighbor search  
**Speed:** Sub-10ms queries even with millions of vectors  

**Parameters:**
- `m=16`: Number of connections per layer (8-64 range)
  - Higher = more accurate but slower builds
- `ef_construction=64`: Search breadth during index building (32-128 range)
  - Higher = better quality but longer build time
- `ef_search=100`: Search breadth at query time (runtime setting)
  - With pgvector 0.8.0, iterative scanning compensates for low values!

**Distance Metrics:**
- **Cosine Distance:** `<=>` operator (used in this lab)
  - Measures angle between vectors (0-1)
  - 0 = identical, 1 = orthogonal
  - Best for normalized vectors
- **L2 Distance:** `<->` operator
- **Inner Product:** `<#>` operator

### Titan Embeddings V2

**Model:** `amazon.titan-embed-text-v2:0`  
**Dimensions:** 1024 (customizable: 256, 384, 1024)  
**Normalization:** Enabled by default  
**Use Case:** General-purpose semantic similarity  
**Advantages:** 
- High quality embeddings
- Fast inference
- No infrastructure management

---

## 📊 Expected Results & Performance

### Query Performance

With pgvector 0.8.0 on Aurora PostgreSQL:

| Query Type | Latency | Results | Recall |
|------------|---------|---------|--------|
| Simple semantic search | 5-10ms | 10 | 100% |
| With 1-2 filters | 10-20ms | 10 | 100% |
| With 3+ filters | 20-50ms | 10 | 100% |
| Complex multi-filter | 50-100ms | 10 | 100% |

**Note:** 100% recall guaranteed by iterative scanning!

### Similarity Scores

For Titan Text V2 embeddings:

- **0.6-0.8:** Highly relevant (exact matches, synonyms)
- **0.4-0.6:** Relevant (related concepts, similar products)
- **0.2-0.4:** Somewhat relevant (broad category matches)
- **<0.2:** Not very relevant

### Sample Search Results

**Query:** "wireless gaming mouse"

```sql
SELECT product_description, 
       price,
       stars,
       1 - (embedding <=> query_vector) as similarity
FROM bedrock_integration.product_catalog
ORDER BY embedding <=> query_vector
LIMIT 5;
```

**Expected:**
1. Wireless Gaming Mouse RGB (similarity: 0.72)
2. Ergonomic Gaming Mouse 6400 DPI (similarity: 0.68)
3. Wireless Mouse for Gaming (similarity: 0.67)
4. Gaming Mouse Pad RGB (similarity: 0.45)
5. Wireless Keyboard and Mouse Combo (similarity: 0.42)

---

## ✅ Success Criteria

By the end of Lab 1, you should have:

- [x] ✅ Connected to Aurora PostgreSQL with pgvector 0.8.0
- [x] ✅ Loaded 21,704 products into database
- [x] ✅ Generated 1024-dimensional embeddings for all products
- [x] ✅ Created HNSW index with optimal parameters
- [x] ✅ Executed semantic search queries successfully
- [x] ✅ Compared keyword vs. semantic search results
- [x] ✅ Understood key concepts: embeddings, HNSW, iterative scanning

**Bonus achievements:**
- [x] 🎨 Explored t-SNE embedding visualization (optional)
- [x] ⚙️ Tested scalar quantization for memory optimization (optional)
- [x] 📊 Analyzed query execution plans with EXPLAIN ANALYZE (optional)

---

## 🛠 Troubleshooting

### Jupyter Won't Start

```bash
# Check if port 8888 is in use
lsof -i :8888

# Kill existing processes
pkill jupyter

# Restart Jupyter
start-jupyter
```

### Database Connection Fails

**Error:** "Database credentials not found"

**Solution:**
```bash
# 1. Check environment variables
echo $DB_SECRET_ARN
echo $DB_HOST

# 2. Verify .env file exists
cat /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.env

# 3. Test Secrets Manager access
aws secretsmanager get-secret-value --secret-id $DB_SECRET_ARN

# 4. Test direct connection
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c "SELECT 1"
```

**If bootstrap scripts didn't run:**
```bash
# Check bootstrap logs
sudo tail -f /var/log/bootstrap-labs.log

# Verify workshop-ready marker
cat /tmp/workshop-ready.json
```

### Bedrock Access Denied

**Error:** "AccessDeniedException" when generating embeddings

**Causes:**
- IAM role missing `bedrock:InvokeModel` permission
- Wrong AWS region (must be us-west-2)
- Model not enabled in Bedrock console

**Solution:**
```bash
# Check IAM role
aws sts get-caller-identity

# Verify region
echo $AWS_REGION

# Test Bedrock access
aws bedrock-runtime invoke-model \
  --model-id amazon.titan-embed-text-v2:0 \
  --body '{"inputText":"test"}' \
  --region us-west-2 \
  response.json
```

### Embeddings Generation Slow

**Expected Time:** ~3 minutes for 21,704 products

**If much slower:**
- Check network connectivity to Bedrock
- Verify parallel processing is working (should see progress bar)
- Monitor CloudWatch for Bedrock throttling

**Normal behavior:**
```
🔄 Generating embeddings... (ETA: ~3 minutes)
INFO: Parallelizing on 10 workers
[Progress bar showing completion]
✅ Embeddings generated successfully!
   • Processing rate: 120.3 products/sec
```

### Interactive Widget Not Working

**Issue:** Widget doesn't appear or doesn't respond

**Solutions:**
1. **Restart kernel:** Kernel → Restart Kernel & Run All Cells
2. **Check widget cell was run only once** (running multiple times creates duplicates)
3. **Enable widgets:** `jupyter nbextension enable --py widgetsnbextension`
4. **Use "Run All" from menu** to ensure proper execution order

### Memory Issues

**Error:** "MemoryError" or kernel crashes

**Solutions:**
- Reduce batch size in embedding generation
- Close other applications
- If on small instance, consider upgrading
- Use quantization to reduce memory footprint

---

## 🎯 Next Steps

### Ready for Lab 2?

**Lab 2** builds a full-stack agentic AI application on top of this semantic search foundation:

**What you'll build:**
- 🤖 **Multi-agent AI system** with reasoning and tool use
- 🔧 **Model Context Protocol (MCP)** integration for custom business logic
- ⚡ **FastAPI backend** with real-time semantic search API
- 🎨 **Modern React frontend** with beautiful UI
- 🗣️ **Conversational AI assistant** powered by Claude Sonnet 4

**Duration:** 60-80 minutes  
**Prerequisites:** Completed Lab 1 ✅

**Continue to:** `lab2/LAB2_GUIDE.md`

### Alternative Paths

**Option 1: Explore Optional Sections**
- 🎨 Embedding space visualization with t-SNE
- ⚙️ Scalar quantization demonstration
- 📊 Advanced query plan analysis

**Option 2: Experiment Further**
- Try your own search queries in the widget
- Modify HNSW parameters and observe effects
- Test different `ef_search` values
- Analyze query plans with `EXPLAIN ANALYZE`

**Option 3: Deep Dive into Documentation**
- [pgvector 0.8.0 Blog Post](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- [Aurora PostgreSQL Vector DB Guide](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [pgvector GitHub Repository](https://github.com/pgvector/pgvector)

---

## 📚 Additional Resources

### Technical Documentation

- **pgvector 0.8.0 Features:** [AWS Blog Post](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- **Aurora PostgreSQL:** [User Guide](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- **Amazon Bedrock:** [Developer Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- **Titan Embeddings:** [Model Card](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)

### Academic Papers

- **HNSW Algorithm:** [Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs](https://arxiv.org/abs/1603.09320)
- **Vector Embeddings:** [Efficient Estimation of Word Representations in Vector Space](https://arxiv.org/abs/1301.3781)

### Related Workshops

- **DAT407:** Generative AI with Amazon Aurora and pgvector
- **DAT408:** Building production RAG systems with Aurora
- **AIM401:** Foundation models on Amazon Bedrock

---

## 🎓 Learning Outcomes

After completing this lab, you now understand:

### Technical Skills ✅
- How to generate and store vector embeddings at scale
- How to create and optimize HNSW indexes for vector search
- How to query vector databases with cosine similarity
- How to use Amazon Bedrock for embedding generation
- How to leverage pgvector 0.8.0's automatic features

### Conceptual Knowledge ✅
- The difference between keyword and semantic search
- How vector embeddings capture semantic meaning
- Why HNSW enables fast approximate nearest neighbor search
- How pgvector 0.8.0's iterative scanning ensures completeness
- When to use vector databases vs. traditional databases

### Production Best Practices ✅
- Connection pooling for database performance
- Batch processing for large-scale embedding generation
- Index optimization and maintenance strategies
- Query performance monitoring and analysis
- Memory optimization with quantization

---

## ⏱️ Time Breakdown

| Activity | Duration |
|----------|----------|
| Jupyter setup | 2 min |
| Open notebook | 1 min |
| Install dependencies | 1 min |
| Database connection | 1 min |
| Load product data | 2 min |
| Generate embeddings | 3-4 min |
| Create indexes | 2 min |
| Interactive exploration | 8-10 min |
| **Total** | **20-25 min** |

**Optional sections:** +15-30 min

---

**🎉 Congratulations on completing Lab 1!**

You've built a production-ready semantic search system. Now take these skills to Lab 2 and build a complete agentic AI application! 🚀

---

**Questions?** Ask your workshop instructors or TAs!  
**Found a bug?** Create an issue in the workshop repository  
**Want to share?** Tweet with #AWSreInvent #DAT406