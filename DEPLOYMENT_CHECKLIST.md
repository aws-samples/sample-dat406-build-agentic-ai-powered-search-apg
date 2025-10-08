# Lab 2 Deployment Checklist

## Pre-Deployment Verification

### 1. CloudFormation Template
**File:** `deployment/cfn/dat406-code-editor.yml`

✅ **IAM Permissions:**
- [x] `rds-data:ExecuteStatement` - For MCP to query database
- [x] `rds-data:BatchExecuteStatement` - For batch queries
- [x] `ec2:DescribeTags` - For CloudFront URL detection
- [x] `secretsmanager:GetSecretValue` - For database credentials
- [x] `bedrock:InvokeModel` - For Titan embeddings and Claude

✅ **EC2 Instance Tagging:**
- [x] Lambda function to tag instance with CloudFront URL
- [x] Custom resource runs after CloudFront distribution created
- [x] Tag: `CloudFrontURL=https://${CloudFrontDistribution.DomainName}`

### 2. Bootstrap Script
**File:** `deployment/bootstrap-labs.sh`

✅ **Environment Setup:**
- [x] Clones repository
- [x] Removes `.git` directory (no source control for participants)
- [x] Fetches DB credentials from Secrets Manager
- [x] Calculates DB_CLUSTER_ARN from account ID
- [x] Detects CloudFront URL from EC2 tags

✅ **Frontend .env:**
- [x] `VITE_API_URL=/ports/8000` (relative path for CloudFront)
- [x] `VITE_AWS_REGION=us-west-2`
- [x] `CLOUDFRONT_URL` stored for reference

✅ **Backend .env:**
- [x] `DB_CLUSTER_ARN` - Calculated dynamically
- [x] `DB_SECRET_ARN` - From CloudFormation
- [x] `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - From Secrets Manager
- [x] `AWS_REGION` - From environment
- [x] `BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0`
- [x] `BEDROCK_CHAT_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0`

✅ **MCP Config Generation:**
- [x] Step 8 generates `lab2/config/mcp-server-config.json`
- [x] Uses environment variables (no hardcoded ARNs)
- [x] Includes AWS credentials passthrough

✅ **Dependencies:**
- [x] Lab 1: Jupyter, pandas, psycopg, pgvector, boto3
- [x] Lab 2 Backend: FastAPI, uvicorn, strands-agents, mcp
- [x] Lab 2 Frontend: npm install
- [x] UV/UVX for MCP server

✅ **Bash Aliases:**
- [x] `start-backend` - Generates MCP config, starts uvicorn
- [x] `start-frontend` - Production build with http-server
- [x] `start-jupyter` - Launches Jupyter Lab

### 3. Backend Components

✅ **Core Services:**
- [x] `services/database.py` - PostgreSQL connection
- [x] `services/embeddings.py` - Titan embeddings
- [x] `services/bedrock.py` - Bedrock client
- [x] `services/chat.py` - Chat with MCP integration

✅ **MCP Tools:**
- [x] `services/mcp_database.py` - CustomMCPTools class (database queries)
- [x] `services/mcp_agent_tools.py` - @tool decorated functions for agents
- [x] Pre-fetched data at startup for fast agent responses

✅ **Agents (all with @tool decorator):**
- [x] `agents/orchestrator.py` - Routes to specialists
- [x] `agents/inventory_agent.py` - Stock management
- [x] `agents/recommendation_agent.py` - Product suggestions
- [x] `agents/pricing_agent.py` - Price optimization

✅ **API Endpoints:**
- [x] `/api/health` - Health check
- [x] `/api/search` - Semantic search (min_similarity=0.0)
- [x] `/api/autocomplete` - Trigram suggestions
- [x] `/api/products/*` - Product endpoints
- [x] `/api/mcp/*` - Custom MCP tool endpoints
- [x] `/api/agents/query` - Agent query endpoint
- [x] `/api/chat` - Chat endpoint (requires RDS Data API permissions)

✅ **Models:**
- [x] `models/search.py` - SearchRequest with min_similarity=0.0 default
- [x] `models/product.py` - Product models

### 4. Frontend Components

✅ **Configuration:**
- [x] `vite.config.ts` - host: true, base: '/ports/5173/'
- [x] `.env` - VITE_API_URL=/ports/8000 (relative path)
- [x] `START_FRONTEND.sh` - Production build + http-server

✅ **Components:**
- [x] `SearchOverlay.tsx` - min_similarity: 0.0 in search requests
- [x] `Header.tsx` - Search bar
- [x] `AIAssistant.tsx` - Chat interface
- [x] `ProductCard.tsx` - Product display

✅ **Services:**
- [x] `api.ts` - API client with relative URL
- [x] `chat.ts` - Chat service
- [x] `types.ts` - SearchQuery with min_similarity field

### 5. File Naming & Structure

✅ **Cleaned Up:**
- [x] Removed `mcp_tool_wrappers.py` (unused)
- [x] Renamed `mcp_tools.py` → `mcp_database.py`
- [x] Renamed `mcp_tool_direct.py` → `mcp_agent_tools.py`
- [x] All imports updated in agents and app.py
- [x] Removed test scripts (fix-cloudfront.sh, UPDATE_FRONTEND.sh, FIXES_APPLIED.md)
- [x] Created `.gitignore` to ignore .ipynb files

---

## Deployment Flow

### 1. CloudFormation Stack Creation
```
1. VPC + Subnets created
2. Aurora PostgreSQL cluster created
3. EC2 instance launched
4. IAM role attached with all permissions
5. SSM document runs bootstrap-environment.sh (Stage 1)
6. CloudFormation signals success
7. CloudFront distribution created
8. Lambda tags EC2 instance with CloudFront URL
9. bootstrap-labs.sh runs in background (Stage 2)
```

### 2. Bootstrap Stage 1 (Environment)
```
1. Install Code Editor (code-server)
2. Install Python 3.13
3. Install Node.js 18
4. Install PostgreSQL 16 client
5. Configure VS Code extensions
6. Signal CloudFormation success
7. Trigger Stage 2 in background
```

### 3. Bootstrap Stage 2 (Labs)
```
1. Clone repository
2. Remove .git directory
3. Fetch DB credentials from Secrets Manager
4. Calculate DB_CLUSTER_ARN
5. Detect CloudFront URL from EC2 tags
6. Create .env files (root, backend, frontend)
7. Install Lab 1 dependencies (Jupyter)
8. Generate MCP config with dynamic ARNs
9. Install Lab 2 backend dependencies (FastAPI, Strands)
10. Install Lab 2 frontend dependencies (npm)
11. Configure bash aliases
12. Create status marker
```

### 4. Participant Experience
```
1. Access CloudFront URL
2. Open VS Code in browser
3. Terminal 1: start-backend
4. Terminal 2: start-frontend
5. Access frontend via CloudFront URL
6. Test search, agents, chat
```

---

## Critical Success Factors

### ✅ Search Works
- [x] min_similarity=0.0 default (backend)
- [x] min_similarity: 0.0 in frontend requests
- [x] Embeddings generated with Titan v2
- [x] pgvector HNSW index used
- [x] Results returned with similarity scores

### ✅ Agents Work
- [x] All agents use @tool decorator
- [x] MCP config generated with correct ARNs
- [x] IAM permissions include rds-data:ExecuteStatement
- [x] AWS credentials passed to MCP subprocess
- [x] Pre-fetched data available to agents
- [x] /api/agents/query endpoint functional

### ✅ Chat Works
- [x] Chat service uses Strands SDK
- [x] MCP client connects to Aurora
- [x] IAM permissions include rds-data:ExecuteStatement
- [x] Product extraction from responses
- [x] /api/chat endpoint functional (if IAM permissions present)

### ✅ Frontend Works
- [x] VITE_API_URL=/ports/8000 (relative path)
- [x] Production build served via http-server
- [x] CloudFront proxies to backend
- [x] No CORS issues
- [x] Hard refresh clears cache

### ✅ MCP Works
- [x] Config auto-generated with correct ARNs
- [x] UV/UVX installed
- [x] AWS credentials passed to subprocess
- [x] Custom tools pre-fetched at startup
- [x] Base MCP tools (run_query, get_table_schema) available

---

## Testing Commands (On EC2 Instance)

### Backend Health
```bash
# Should return: {"status":"healthy","database":"connected","bedrock":"accessible","mcp":"available"}
curl http://localhost:8000/api/health
```

### Search
```bash
# Should return 10 results
curl -s -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"laptop","limit":10,"min_similarity":0.0}' | jq '.total_results'
```

### Agents
```bash
# Should return agent response
curl -s -X POST "http://localhost:8000/api/agents/query?query=What%20products%20need%20restocking&agent_type=inventory" | jq '.success'
```

### MCP Tools
```bash
# Should return trending products
curl -s "http://localhost:8000/api/mcp/trending?limit=5" | jq '.count'
```

### Frontend
```bash
# Should return HTML
curl -s "http://localhost:5173" | head -5
```

---

## Known Issues & Workarounds

### Issue 1: Chat Requires IAM Permissions
**Problem:** /api/chat needs rds-data:ExecuteStatement  
**Status:** ✅ Fixed in CloudFormation template  
**Workaround:** Use /api/agents/query instead

### Issue 2: Browser Cache
**Problem:** Frontend changes not visible  
**Solution:** Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)

### Issue 3: CloudFront URL Detection
**Problem:** CLOUDFRONT_URL not set during bootstrap  
**Status:** ✅ Fixed - Lambda tags instance after CloudFront created  
**Fallback:** Relative path /ports/8000 works regardless

---

## Post-Deployment Verification

### 1. Check Logs
```bash
# Stage 1 (Environment)
tail -100 /var/log/bootstrap-main.log

# Stage 2 (Labs)
tail -100 /var/log/bootstrap-labs.log
```

### 2. Check Status
```bash
cat /tmp/workshop-ready.json
```

### 3. Check Services
```bash
# Backend running
ps aux | grep uvicorn

# Frontend running
ps aux | grep http-server
```

### 4. Check Files
```bash
# .env files created
ls -la /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.env
ls -la /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/backend/.env
ls -la /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/frontend/.env

# MCP config generated
cat /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/config/mcp-server-config.json

# Git removed
ls -la /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.git
# Should show: No such file or directory
```

---

## Success Criteria

✅ **All green means ready for deployment:**

- [x] CloudFormation template has all IAM permissions
- [x] EC2 instance tagged with CloudFront URL
- [x] Bootstrap script removes .git
- [x] Bootstrap script generates MCP config dynamically
- [x] Frontend uses relative API URL (/ports/8000)
- [x] Backend has min_similarity=0.0 default
- [x] All agents use @tool decorator
- [x] MCP tools renamed (mcp_database.py, mcp_agent_tools.py)
- [x] All imports updated
- [x] Test files removed
- [x] Lab 2 guide created
- [x] No localhost references in guide

**Status: ✅ READY FOR DEPLOYMENT**
