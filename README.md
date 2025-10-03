# 🛍️ Blaize Bazaar - AI-Powered Semantic Search E-Commerce

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS](https://img.shields.io/badge/AWS-Aurora%20%7C%20Bedrock-orange)](https://aws.amazon.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB)](https://reactjs.org)

> **DAT406 Workshop**: Build Agentic AI-Powered Search with Amazon Aurora  
> **Event**: AWS re:Invent 2025 | **Level**: 400 (Expert)

## 🎯 Project Overview

**Blaize Bazaar** is a production-grade AI-powered e-commerce platform that demonstrates intelligent product discovery using semantic search. Built with Amazon Aurora PostgreSQL (pgvector), Amazon Bedrock, and modern web technologies, it showcases how to create a premium shopping experience with real-time semantic search capabilities.

### ✨ Key Features

- 🔍 **Semantic Search** - Natural language product search using vector embeddings (60%+ similarity scores)
- ⚡ **Real-time Autocomplete** - Fast trigram-based suggestions with 300ms debounce
- 🎨 **Premium UI/UX** - Apple-inspired design with dark/light mode support
- 🤖 **AI Assistant** - Interactive Aurora AI chatbot for product recommendations
- 🏷️ **Smart Filters** - Price range and star rating filters with real-time updates
- 📊 **21,704 Products** - Full Amazon product catalog with embeddings
- 🔗 **MCP Integration** - Model Context Protocol server for database access
- 🌐 **Responsive Design** - Glassmorphism effects and smooth animations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                  │
│  • TypeScript + Tailwind CSS                                 │
│  • Semantic Search UI with Filters                           │
│  • Real-time Autocomplete                                    │
│  • Dark/Light Mode Theme Toggle                              │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Python)                 │
│  • Semantic Search Endpoints                                 │
│  • Autocomplete with Trigram Index                           │
│  • Product CRUD Operations                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────────┐
│ Amazon Bedrock   │    │ Aurora PostgreSQL    │
│ • Cohere Embed   │    │ • pgvector Extension │
│   English v3     │    │ • HNSW Index         │
│ • 1024 dims      │    │ • Trigram Index      │
└──────────────────┘    └──────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS Account with Bedrock access
- Aurora PostgreSQL cluster with pgvector

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Aurora and AWS credentials

# Run the FastAPI server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env
# Edit .env with backend API URL

# Run the development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

## 📊 Database Schema


**Table**: `bedrock_integration.product_catalog`

| Column | Type | Description |
|--------|------|-------------|
| productId | VARCHAR | Unique product identifier |
| product_description | TEXT | Product name/description |
| imgurl | TEXT | Product image URL |
| producturl | TEXT | Amazon product link |
| stars | FLOAT | Average rating (0-5) |
| reviews | INTEGER | Number of reviews |
| price | FLOAT | Product price in USD |
| category_name | VARCHAR | Product category |
| quantity | INTEGER | Stock quantity |
| embedding | VECTOR(1024) | Cohere embedding vector |

**Indexes**:
- HNSW index on `embedding` for fast vector similarity search
- GIN trigram index on `product_description` for autocomplete

## 🔍 API Endpoints

### Search & Autocomplete

```bash
# Semantic search
POST /api/search
{
  "query": "bluetooth headphones",
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

## 🎨 Features in Detail

### Semantic Search
- Uses Cohere Embed English v3 (1024 dimensions)
- pgvector HNSW index for fast similarity search
- Cosine distance operator (`<=>`) for relevance scoring
- Achieves 60%+ similarity scores for relevant queries
- Sub-100ms response times

### Autocomplete
- Trigram-based ILIKE search with GIN index
- 300ms debounce for optimal UX
- Shows product name and category
- Faster than full-text search for real-time suggestions

### Smart Filters
- **Price Range**: Min/max price inputs with real-time filtering
- **Star Ratings**: Quick-select buttons (All, 3★, 4★, 4.5★, 5★)
- **Client-side filtering**: Instant results without API calls
- **Reset functionality**: Clear all filters with one click

### UI/UX
- Apple-inspired glassmorphism design
- Dark/light mode with smooth transitions
- Responsive grid layout for search results
- Product cards with images, ratings, and prices
- Clickable Amazon links with `target="_blank"`
- Animated product showcase carousel

## 🤖 MCP Server Integration

Connect AI assistants to your Aurora database using Model Context Protocol:

```bash
# Copy MCP configuration
mkdir -p ~/.aws/amazonq/
cp mcp-server-config.json ~/.aws/amazonq/mcp-servers.json

# Restart your IDE
```

See [MCP_SETUP.md](./MCP_SETUP.md) for detailed instructions.

## 📁 Project Structure

```
blaize-bazaar/
├── backend/
│   ├── models/           # Pydantic models
│   ├── services/         # Business logic
│   ├── notebooks/        # Data loading scripts
│   ├── app.py           # FastAPI application
│   ├── config.py        # Configuration
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── services/    # API client
│   │   └── styles/      # CSS files
│   ├── package.json
│   └── vite.config.ts
├── data/
│   └── amazon-products-sample.csv
├── scripts/             # Setup scripts
├── mcp-server-config.json
└── README.md
```

## 🛠️ Technology Stack

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

### Backend
- **FastAPI** - Web framework
- **Python 3.11+** - Programming language
- **Pydantic** - Data validation
- **psycopg3** - PostgreSQL driver
- **boto3** - AWS SDK

### Database & AI
- **Amazon Aurora PostgreSQL** - Database
- **pgvector** - Vector similarity search
- **Amazon Bedrock** - Embeddings (Cohere Embed English v3)
- **HNSW Index** - Fast approximate nearest neighbor search

## 🔧 Configuration

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
BEDROCK_EMBEDDING_MODEL=cohere.embed-english-v3
BEDROCK_CHAT_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

### Frontend Environment Variables

```bash
VITE_API_URL=http://localhost:8000
```

## 📊 Performance Metrics

- **Search Latency**: 50-150ms average
- **Autocomplete**: <50ms with trigram index
- **Similarity Scores**: 60-95% for relevant results
- **Database Size**: 21,704 products with embeddings
- **Vector Dimensions**: 1024 (Cohere Embed English v3)

## 🎓 Learning Outcomes

This project demonstrates:

1. **Vector Embeddings** - Generate and store semantic embeddings
2. **Similarity Search** - Use pgvector for fast nearest neighbor search
3. **HNSW Indexing** - Optimize vector search performance
4. **Hybrid Search** - Combine vector search with traditional filters
5. **Real-time UX** - Build responsive search interfaces
6. **AWS Integration** - Use Bedrock for embeddings
7. **MCP Protocol** - Enable AI assistant database access

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- **AWS re:Invent 2025** - DAT406 Workshop
- **Amazon Aurora** - PostgreSQL with pgvector
- **Amazon Bedrock** - Cohere embeddings
- **Model Context Protocol** - AI assistant integration

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Check [MCP_SETUP.md](./MCP_SETUP.md) for MCP configuration
- Review backend/notebooks for data loading examples

---

**Built with ❤️ for AWS re:Invent 2025 | DAT406 Workshop**
