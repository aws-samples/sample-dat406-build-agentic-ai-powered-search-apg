# 🤖 Chat Implementation with Aurora AI

## Overview

The chat functionality connects the AI Assistant to Amazon Bedrock (Claude) with Aurora PostgreSQL database context through MCP (Model Context Protocol).

## Architecture

```
Frontend (AIAssistant.tsx)
    ↓ WebSocket/REST
Backend (FastAPI /api/chat)
    ↓
ChatService
    ↓
Amazon Bedrock (Claude Sonnet)
    ↓ (via MCP)
Aurora PostgreSQL (21,704 products)
```

## Implementation Details

### Backend Components

1. **ChatService** (`backend/services/chat.py`)
   - Manages conversation with Bedrock Claude
   - Provides system prompt with database schema
   - Handles MCP integration for database access
   - Fallback responses when Bedrock unavailable

2. **Chat Models** (`backend/models/search.py`)
   - `ChatRequest`: User message + conversation history
   - `ChatResponse`: AI response + tool calls + metadata
   - `ChatMessage`: Individual message (role + content)

3. **API Endpoint** (`backend/app.py`)
   - `POST /api/chat`: Send message, get AI response
   - Maintains conversation context
   - Error handling and logging

### Frontend Components

1. **AIAssistant** (`frontend/src/components/AIAssistant.tsx`)
   - Real-time chat interface
   - Conversation history management
   - Typing indicators
   - Error handling

2. **API Client** (`frontend/src/services/api.ts`)
   - `chat()` method for API calls
   - Conversation history serialization

## System Prompt

The AI assistant has knowledge of:
- Database schema (bedrock_integration.product_catalog)
- 21,704 products with embeddings
- Product attributes (price, rating, reviews, stock)
- Categories and inventory

## Usage

### Start Chat:

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app:app --reload

# Frontend
cd frontend
npm run dev
```

### Example Queries:

- "Show me bluetooth headphones under $200"
- "What are the top-rated laptops?"
- "Find products with 5-star ratings"
- "Check inventory for wireless earbuds"

## MCP Integration

The MCP server configuration (`mcp-server-config.json`) enables:
- Direct SQL queries to Aurora
- Real-time inventory checks
- Product recommendations
- Category analysis

## Features

✅ Real-time chat with Claude Sonnet
✅ Database-aware responses
✅ Conversation history
✅ Fallback responses
✅ Error handling
✅ Typing indicators
✅ Premium UI/UX

## Next Steps

To enable full MCP functionality:
1. Install Node.js MCP server: `npm install -g @modelcontextprotocol/server-postgres`
2. Configure MCP in IDE: Copy `mcp-server-config.json` to `~/.aws/amazonq/mcp-servers.json`
3. Restart IDE to load MCP server

## Testing

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the best headphones",
    "conversation_history": []
  }'
```

Expected response:
```json
{
  "response": "Based on our catalog...",
  "tool_calls": [],
  "model": "anthropic.claude-3-sonnet-20240229-v1:0",
  "success": true
}
```
