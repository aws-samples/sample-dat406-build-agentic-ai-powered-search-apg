---
inclusion: always
---

# Pellier — Project Context

## What This Is

Pellier is a hands-on workshop application that teaches developers how to build agentic AI-powered search using Amazon Aurora PostgreSQL, pgvector, Amazon Bedrock, Strands SDK, and Amazon Bedrock AgentCore. It's a real e-commerce storefront (React + FastAPI) where participants progressively build features by editing the actual application code.

## Delivery Format

- **Governed agentic AI search workshop** — the storefront ships mostly wired. Participants complete the required Marco inventory path, compare retrieval strategies, prove the audit ledger in SQL, and inspect Runtime, Gateway, Memory, and Policy as guided governance surfaces.

Lab guide content lives in the separate Workshop Studio repo
(`build-governed-agentic-ai-search-with-aurora-rds-bedrock-agentcore`),
the source of truth for all session content. This repo is the running app.

## Session Structure

Three Acts. Required path first, optional deeper reads after the evidence proof lands.

- **Act I: The Boutique**
  - Observe Marco's broken warehouse turn
  - **Required build:** wire the `floor_check` tool body against `pellier.warehouse_inventory`
  - Replay Marco end to end and compare vector / hybrid / hybrid+rerank / agentic retrieval for Anna's anchor query
  - *Optional fast-finisher:* edit Anna's skill rule and prove it via SQL
- **Act II: The Ledger**
  - Read memory substrates (AgentCore STM) + long-term taste in Aurora
  - Invoke the managed AgentCore Runtime
  - **Required proof:** `SELECT` from `pellier.tool_audit` to reconstruct the agent's actions
  - *Optional fast-finisher:* add a `logger.info` observability hook on the Runtime path
- **Act III: The Concierge**
  - Dispatcher + specialists routing (production default for curated intents)
  - Gateway / MCP boundary and JWT identity passthrough

## Key Directories

- `pellier/backend/` — FastAPI Python backend with Strands SDK agents
- `pellier/frontend/` — React + Vite + Tailwind storefront
- `solutions/` — Drop-in reference files / escape hatches (cp and restart)
  - `solutions/the-quiet-search/` (semantic search), `solutions/closing-marcos-gap/` (floor_check + specialists), `solutions/the-ledger/` (AgentCore production)
- `scripts/` — Bootstrap and seed scripts for the session environment
- `data/` — Product catalog CSV with pre-generated Cohere Embed v4 embeddings
- `.kiro/specs/` — Feature specs (requirements, design, tasks)
- `.claude/prompts/` — Claude Code prompt playbooks

## Database

- Amazon Aurora PostgreSQL (latest available at session time; currently 18.3) Serverless v2 (0–16 ACU, scale-to-zero)
- Schema: `pellier` (product_catalog, warehouse_inventory, customers, customer_episodic_seed, tool_audit, and supporting tables)
- pgvector 0.8.0 with HNSW indexes for 1024-dim Cohere Embed v4 vectors
- 40 curated products (10 signed-out baseline + 10 per persona) with pre-generated embeddings
- Session management: AgentCore Memory (STM) via `agentcore_memory.py`
- User preferences stored in AgentCore Memory keyed by verified Cognito user_id

## Authentication

Real Amazon Cognito + AgentCore Identity (not simulated). Cognito User Pool with hosted UI federated to Google + Apple + email/password. JWT validated via Cognito JWKS. AgentCore Identity wraps verified user context for agents and scopes AgentCore Memory keys by user_id. The shopper's JWT is also passed through to the AgentCore Gateway so MCP tool calls carry the caller's identity.

The workshop runs in demo auth mode by default (`AUTH_MODE=demo`); the Cognito/JWT path is fully wired and used for the signed-in Gateway demo.
