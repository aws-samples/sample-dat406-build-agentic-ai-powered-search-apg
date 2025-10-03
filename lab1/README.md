# Lab 1: Building AI-Powered Semantic Search with pgvector and Amazon Bedrock

**Duration**: 20 minutes  
**Level**: 300 (Intermediate)

## 🎯 Learning Objectives

By the end of this lab, you will:
- ✅ Set up Amazon Aurora PostgreSQL with pgvector extension
- ✅ Load product catalog data into Aurora
- ✅ Generate vector embeddings using Amazon Bedrock (Cohere Embed English v3)
- ✅ Create HNSW indexes for fast similarity search
- ✅ Perform semantic search queries using pgvector
- ✅ Understand vector similarity and cosine distance

## 📋 Prerequisites

- AWS Account with access to:
  - Amazon Aurora PostgreSQL
  - Amazon Bedrock (Cohere Embed English v3 model enabled)
- Python 3.11+ installed
- Jupyter Notebook environment
- Basic SQL knowledge

## 🏗️ Architecture

```
┌─────────────────┐
│  Product Data   │
│  (21,704 items) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ Amazon Bedrock  │◄─────│  Python Script   │
│ Cohere Embed v3 │      │  (Batch Process) │
│ 1024 dimensions │      └──────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Aurora PostgreSQL + pgvector  │
│   • Vector embeddings (1024d)   │
│   • HNSW index for fast search  │
│   • Cosine similarity operator  │
└─────────────────────────────────┘
```

## 📁 Lab Contents

- `Part 1_Building AI-Powered Semantic Product Search with pgvector and Amazon Bedrock (1).ipynb` - Main lab notebook
- Sample product data (loaded from `../data/amazon-products-sample.csv`)

## 🚀 Getting Started

### Step 1: Open the Notebook

```bash
cd lab1
jupyter notebook
```

Open: `Part 1_Building AI-Powered Semantic Product Search with pgvector and Amazon Bedrock (1).ipynb`

### Step 2: Configure AWS Credentials

Ensure your AWS credentials are configured:

```bash
aws configure
# OR set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-west-2
```

### Step 3: Set Database Connection

Update the notebook with your Aurora cluster endpoint:

```python
DB_HOST = "your-aurora-cluster.region.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "your-password"
```

### Step 4: Run Through the Notebook

Follow the notebook cells sequentially:

1. **Setup** - Install dependencies and import libraries
2. **Database Connection** - Connect to Aurora PostgreSQL
3. **Enable pgvector** - Install and configure pgvector extension
4. **Load Data** - Import product catalog (21,704 products)
5. **Generate Embeddings** - Use Bedrock to create vector embeddings
6. **Create Indexes** - Build HNSW index for fast similarity search
7. **Semantic Search** - Query products using natural language
8. **Analysis** - Explore similarity scores and results

## 🔍 Key Concepts

### Vector Embeddings
- Transform text into 1024-dimensional vectors
- Capture semantic meaning of product descriptions
- Enable similarity-based search

### pgvector Extension
- PostgreSQL extension for vector operations
- Supports cosine distance (`<=>` operator)
- HNSW index for approximate nearest neighbor search

### HNSW Index
- Hierarchical Navigable Small World graphs
- Fast approximate similarity search
- Sub-100ms query times on 21K+ products

### Similarity Scoring
- Cosine similarity: 1 - (embedding1 <=> embedding2)
- Scores range from 0 (dissimilar) to 1 (identical)
- Typical relevant results: 60%+ similarity

## 📊 Expected Results

After completing this lab:
- ✅ 21,704 products loaded with embeddings
- ✅ HNSW index created (m=16, ef_construction=64)
- ✅ Semantic search queries return relevant results
- ✅ Query latency: 50-150ms average

## 🎓 Sample Queries

```sql
-- Find wireless headphones
SELECT product_description, price, stars, 
       1 - (embedding <=> query_embedding) as similarity
FROM bedrock_integration.product_catalog
WHERE 1 - (embedding <=> query_embedding) > 0.6
ORDER BY embedding <=> query_embedding
LIMIT 10;

-- Find laptops under $1000
SELECT product_description, price, stars,
       1 - (embedding <=> query_embedding) as similarity
FROM bedrock_integration.product_catalog
WHERE price < 1000 
  AND 1 - (embedding <=> query_embedding) > 0.6
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

## 🐛 Troubleshooting

### Issue: Bedrock Access Denied
**Solution**: Enable Cohere Embed English v3 model in Bedrock console

### Issue: pgvector Extension Not Found
**Solution**: Ensure Aurora PostgreSQL version supports pgvector (15.3+)

### Issue: Slow Embedding Generation
**Solution**: Use batch processing (100 products per batch) as shown in notebook

### Issue: Low Similarity Scores
**Solution**: Adjust `min_similarity` threshold (try 0.5 or 0.4)

## 📚 Additional Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/)
- [Aurora PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)

## ⏭️ Next Steps

After completing Lab 1, proceed to **Lab 2** to build the full Blaize Bazaar application with:
- FastAPI backend with semantic search API
- React frontend with AI chat assistant
- Multi-agent system with MCP integration
- Real-time product recommendations

---

**Questions?** Open an issue or ask your workshop instructor.
