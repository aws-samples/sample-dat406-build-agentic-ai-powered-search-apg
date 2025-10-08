# Lab 1: Semantic Search with pgvector

**Duration:** 20 minutes  
**Goal:** Build semantic product search using Amazon Aurora PostgreSQL with pgvector and Amazon Bedrock Titan embeddings

---

## 🎯 What You'll Build

A semantic search system that understands natural language queries like:
- "wireless headphones with noise cancellation"
- "affordable laptop for students"
- "gaming console with best graphics"

---

## 📋 Prerequisites

✅ Workshop environment deployed  
✅ Aurora PostgreSQL cluster running  
✅ Amazon Bedrock access enabled

---

## 🚀 Step 1: Start Jupyter Lab (2 minutes)

Open a terminal and run:

```bash
start-jupyter
```

**Expected output:**
```
Starting Jupyter Lab on http://localhost:8888
[I 2025-01-07 10:00:00.000 ServerApp] Jupyter Server is running at:
[I 2025-01-07 10:00:00.000 ServerApp] http://localhost:8888/lab?token=...
```

**Access Jupyter:**
- Click the URL in the terminal output
- Or navigate to the CloudFront URL + `/ports/8888/`

---

## 📓 Step 2: Open the Notebook (1 minute)

In Jupyter Lab:

1. Navigate to `lab1/` folder in the file browser
2. Open `Lab_1_Building_Semantic_Product_Search_with_pgvector.ipynb`
3. Select kernel: **Python 3.13**

---

## 🔬 Step 3: Execute Notebook Cells (15 minutes)

Work through the notebook sections:

### Section 1: Setup & Connection (2 minutes)
- Import libraries
- Connect to Aurora PostgreSQL
- Verify database connection

**Key Learning:** Database connectivity with psycopg3

### Section 2: Load Product Data (3 minutes)
- Load 21,704 Amazon products from CSV
- Insert into `bedrock_integration.product_catalog` table
- Verify data loaded successfully

**Key Learning:** Bulk data loading into PostgreSQL

### Section 3: Generate Embeddings (5 minutes)
- Use Amazon Bedrock Titan Embeddings v2
- Generate 1024-dimensional vectors for each product
- Store embeddings in `embedding` column

**Key Learning:** Vector embeddings with Amazon Bedrock

### Section 4: Create HNSW Index (2 minutes)
- Create pgvector HNSW index for fast similarity search
- Configure index parameters (m=16, ef_construction=64)

**Key Learning:** Vector indexing for performance

### Section 5: Semantic Search (3 minutes)
- Execute semantic search queries
- Compare with traditional keyword search
- Analyze similarity scores and response times

**Key Learning:** Vector similarity search with cosine distance

---

## 🎓 Key Concepts

### pgvector
- PostgreSQL extension for vector similarity search
- Stores embeddings as native vector type
- Supports multiple distance metrics (cosine, L2, inner product)

### HNSW Index
- Hierarchical Navigable Small World algorithm
- Fast approximate nearest neighbor search
- Trade-off between speed and accuracy

### Titan Embeddings v2
- Amazon Bedrock's text embedding model
- Generates 1024-dimensional vectors
- Optimized for semantic similarity

### Cosine Similarity
- Measures angle between vectors (0-1)
- 1 = identical, 0 = orthogonal
- Used for semantic similarity

---

## 📊 Expected Results

### Search Performance
- **Query time:** ~250-300ms
- **Results:** Top 10 most similar products
- **Similarity scores:** 0.3-0.7 (typical for Titan v2)

### Sample Query
```sql
SELECT product_description, 
       1 - (embedding <=> query_vector) as similarity
FROM bedrock_integration.product_catalog
ORDER BY embedding <=> query_vector
LIMIT 10;
```

---

## ✅ Success Criteria

By the end of Lab 1, you should have:

- [x] Connected to Aurora PostgreSQL
- [x] Loaded 21,704 products into database
- [x] Generated embeddings for all products
- [x] Created HNSW index for fast search
- [x] Executed semantic search queries
- [x] Understood vector similarity concepts

---

## 🐛 Troubleshooting

**Jupyter won't start:**
```bash
# Check if port 8888 is in use
lsof -i :8888

# Restart Jupyter
pkill jupyter
start-jupyter
```

**Database connection fails:**
```bash
# Verify credentials
cat ~/.pgpass

# Test connection
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c "SELECT 1"
```

**Bedrock access denied:**
- Verify IAM role has `bedrock:InvokeModel` permission
- Check AWS region is `us-west-2`

**Embeddings generation slow:**
- Normal: ~2-3 minutes for 21,704 products
- Uses batch processing for efficiency

---

## 🎯 Next Steps

**Ready for Lab 2?**

Lab 2 builds on this foundation:
- FastAPI backend with semantic search API
- React frontend with AI chat assistant
- Multi-agent system with MCP integration
- Production-ready full-stack application

**Continue to:** `lab2/LAB2_GUIDE.md`

---

## 📚 Additional Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Amazon Bedrock Titan Embeddings](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)
- [Aurora PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraPostgreSQL.html)

---

**Time Check:** ⏱️ 20 minutes total  
**Next Lab:** Lab 2 (80 minutes)

