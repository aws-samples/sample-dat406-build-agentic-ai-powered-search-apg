# Local Development Setup Guide

Quick guide to run Blaize Bazaar locally for testing and development.

## Prerequisites

- ✅ Python 3.11+ installed
- ✅ Node.js 18+ installed
- ✅ AWS credentials configured
- ✅ Aurora PostgreSQL cluster with data loaded (from Lab 1)
- ✅ `.env` files populated with your credentials

## 🚀 Quick Start

### Step 1: Start Backend

```bash
# Navigate to backend
cd lab2/backend

# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Verify .env file has all values populated
cat .env

# Start FastAPI server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be running at**: `http://localhost:8000`

**Test it**: Open `http://localhost:8000/api/health` in browser

---

### Step 2: Start Frontend (New Terminal)

```bash
# Navigate to frontend
cd lab2/frontend

# Install dependencies (first time only)
npm install

# Verify .env file exists
cat .env

# Start Vite dev server
npm run dev
```

**Frontend will be running at**: `http://localhost:5173`

**Open in browser**: `http://localhost:5173`

---

## ✅ Verification Checklist

### Backend Health Check
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "bedrock": "accessible",
  "mcp": "connected"
}
```

### Test Semantic Search
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "wireless headphones", "limit": 5}'
```

### Test Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me laptops", "conversation_history": []}'
```

---

## 📝 Environment Variables

### Backend `.env` (lab2/backend/.env)

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

### Frontend `.env` (lab2/frontend/.env)

```bash
VITE_API_URL=http://localhost:8000
```

---

## 🐛 Troubleshooting

### Backend won't start

**Issue**: `ModuleNotFoundError: No module named 'fastapi'`  
**Solution**: Activate venv and install dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Issue**: `Database connection failed`  
**Solution**: Check `.env` has correct DB_HOST and credentials

**Issue**: `Bedrock access denied`  
**Solution**: Verify AWS credentials and Bedrock model access

---

### Frontend won't start

**Issue**: `Cannot find module 'vite'`  
**Solution**: Install dependencies
```bash
npm install
```

**Issue**: `Failed to fetch from backend`  
**Solution**: Verify backend is running on port 8000

---

### Chat not working

**Issue**: `MCP config file not found`  
**Solution**: Verify `lab2/config/mcp-server-config.json` exists

**Issue**: `uv command not found`  
**Solution**: Install uv
```bash
pip install uv
```

---

## 🔄 Restart Services

### Restart Backend
```bash
# In backend terminal, press Ctrl+C to stop
# Then restart
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Restart Frontend
```bash
# In frontend terminal, press Ctrl+C to stop
# Then restart
npm run dev
```

---

## 🛑 Stop Services

### Stop Backend
```bash
# Press Ctrl+C in backend terminal
# Deactivate virtual environment
deactivate
```

### Stop Frontend
```bash
# Press Ctrl+C in frontend terminal
```

---

## 📦 Clean Install (If Issues Persist)

### Backend
```bash
cd lab2/backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend
```bash
cd lab2/frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 🎯 Quick Commands Reference

```bash
# Backend
cd lab2/backend && source venv/bin/activate && uvicorn app:app --reload

# Frontend
cd lab2/frontend && npm run dev

# Health check
curl http://localhost:8000/api/health

# Test search
curl -X POST http://localhost:8000/api/search -H "Content-Type: application/json" -d '{"query":"laptops","limit":5}'
```

---

## 🌐 Access URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

---

**Happy Coding! 🚀**
