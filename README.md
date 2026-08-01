# Build governed agentic AI search with Aurora, RDS, & Bedrock AgentCore

<div align="center">

_Agentic search on Aurora PostgreSQL · Bedrock AgentCore · Strands Agents · MCP_

<br/>

[![Aurora PostgreSQL 18.3](https://img.shields.io/badge/Aurora_PostgreSQL-18.3_·_pgvector-2D72D9?style=flat-square&logo=postgresql&logoColor=white)](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)
[![Bedrock AgentCore](https://img.shields.io/badge/Bedrock-AgentCore-FF9900?style=flat-square)](https://aws.amazon.com/bedrock/agentcore/)
[![Strands Agents](https://img.shields.io/badge/Strands-Agents_SDK-232F3E?style=flat-square)](https://strandsagents.com)
[![MCP](https://img.shields.io/badge/MCP-postgres--mcp--server-4A154B?style=flat-square)](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

[![License: MIT](https://img.shields.io/github/license/aws-samples/sample-pellier-agentic-search-apg?style=flat-square&color=00b300&label=License)](LICENSE)
[![Stars](https://img.shields.io/github/stars/aws-samples/sample-pellier-agentic-search-apg?style=flat-square&color=yellow)](https://github.com/aws-samples/sample-pellier-agentic-search-apg/stargazers)

</div>

> Educational reference implementation for a governed agentic AI search workshop.
> Not intended for production deployment without security hardening.

**Contents:** [Workshop abstract](#workshop-abstract) · [Who this is for](#who-this-is-for) · [What this is](#what-this-is) · [Personas](#personas-reshape-everything) · [Quick start](#quick-start-local-dev) · [Workshop path](#workshop-path) · [Architecture](#architecture) · [Repository layout](#repository-layout) · [Resources](#resources)

---

## Workshop abstract

Build a governed agentic AI search application with Amazon Aurora PostgreSQL and Amazon Bedrock AgentCore. Explore a retail shopping scenario where a Strands SDK dispatcher routes shoppers to specialist agents. Aurora powers hybrid search with PostgreSQL full-text search for lexical retrieval, pgvector for semantic retrieval, and Cohere Rerank for relevance ranking, while managing inventory, orders, customer records, and a queryable JSONB audit ledger. AgentCore Runtime, Memory, Gateway, and Policy orchestrate agents, preserve context, expose tools, and apply Cedar authorization to sensitive actions. Leave with reusable patterns for auditable, policy-aware agentic search applications.

---

## Who this is for

This is a **400-level (expert)** workshop application. "Level 400" is the AWS depth scale — 100 is introductory, 400 is the deepest expert tier. That refers to the **concepts on screen** (agentic orchestration, pgvector retrieval, AgentCore, MCP), not the amount of code you write.

**You will be comfortable here if you:**
- Read Python and SQL (you don't need to write much of either)
- Have used a REST API and a terminal before
- Know, at a high level, what an LLM and a vector embedding are

**You do *not* need to:** build a search system from scratch, know Strands/AgentCore/MCP in advance, or have prior agentic-AI experience. We teach those during the session.

**What you'll actually do — this is the important part.** The application is **already built and running** when you arrive. You are *not* assembling it from nothing. Your hands-on path is small and focused: you implement **one function** (`floor_check`), then run a series of **observe / measure / read** steps that prove how the production system behaves. The five agents, 15 tools, database, and managed runtime are pre-wired *on purpose* — so your attention goes to the agentic pattern, not the plumbing.

> **If it feels deep, that's by design — the depth is there to learn from, not to rebuild.** You only need to complete the one guided exercise to succeed. Everything else is there to explore at your own pace.

---

## What this is

**Pellier** is a small editorial boutique with one quiet promise – a shopper asks for something in their own words, and the search understands what they mean. Behind the storefront sits an agentic search system – specialist agents that ground every answer in retrieved catalog data, read live inventory through deterministic tools, remember your taste across turns, cite every source, and hand off to a human stylist when they should.

The application has two surfaces:

- **Boutique** (`/`) – the customer-facing storefront. Editorial photography, AI search bar, persona-aware recommendations, conversational chat drawer.
- **Atelier** (`/atelier`) – the operator's observatory. Every agent decision, tool call, memory read, retrieval comparison, and routing hop in editorial detail. Same agent, different lens.

The two surfaces share design tokens, presence pill, trace chips, and a typed agent vocabulary, so an attendee crossing between them sees the same atoms in both places.

### What it demonstrates

Every claim in the workshop abstract maps to something runnable in this repo:

| Claim | Where it lives |
|---|---|
| **Grounded retrieval** on **Aurora PostgreSQL** | `pellier.product_catalog.embedding vector(1024)` · pgvector 0.8.1 · HNSW index · `<=>` cosine operator · hybrid (FTS + RRF) merge · Cohere Rerank v3.5 |
| **Agentic AI – reasoning + tool use** | Strands Agents SDK · 5 specialists × 15 `@tool` functions · dispatcher routes intent → one specialist → cosine-discovered tools |
| **Model Context Protocol (MCP)** | [`awslabs.postgres-mcp-server`](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) installed via `uvx`, read-only against the Aurora cluster ARN · `pellier/config/mcp-server-config.json` is the literal contract · any MCP host (VS Code chat extension, Claude Code, Strands `MCPClient`, AgentCore Gateway) consumes the same JSON |
| **Managed tool catalog (AgentCore Gateway)** | `services/agentcore_gateway.py` discovers tools at runtime via `MCPClient.list_tools_sync()` over a Cognito-JWT-gated Gateway · the shopper's JWT is passed through (`Authorization: Bearer`) so tool calls carry the caller's identity · in-process tools stay the default; Gateway is the demonstrable side-path (Atelier Card 7) |
| **Personalization** | Long-term taste in `pellier.customers` + `pellier.customer_episodic_seed` · session-scoped working memory (AgentCore STM) + durable taste extracted by a `USER_PREFERENCE` semantic strategy (`get_semantic_memories`, surfaced in the Atelier) — both via Bedrock AgentCore Memory |
| **Managed agent runtime** | `@app.entrypoint` in `pellier/backend/agentcore_runtime.py` · `bedrock-agentcore:InvokeAgentRuntime` from `services/agentcore_runtime.py` · deploy path uses the pinned AgentCore CLI (`npx -y @aws/agentcore@0.18.0 deploy -y --json`) |

---

## Personas reshape everything

Sign in as one of the three returning customers and the entire storefront – hero photograph, suggestion pills, featured product, weekend edit copy, curated grid (10 exclusive products per persona, zero overlap), editorial cards, chat greeting – reshapes immediately.

| Persona  | Profile                          | Signature piece              |
| -------- | -------------------------------- | ---------------------------- |
| *Marco*  | Natural fibers, travel, linen    | Italian Linen Camp Shirt     |
| *Anna*   | Gifts, milestones, candles       | Beeswax Taper Candles        |
| *Theo*   | Slow craft, ceramics, ritual     | Stoneware Pour-Over Set      |

The **signed-out state** is the editorial baseline – a 10-piece grid anchored by the Nocturne Leather Weekender, no prior context, no profile embedding. It is the hero state, not a fourth persona.

Each persona ships with 10 curated products carrying real Cohere Embed v4 1024-dim embeddings. Those 40 story products stay stable for persona grids, orders, inventory, and policy exercises. The governed retrieval lab expands `pellier.product_catalog` to 1,000 rows by adding generated high-ID archive distractors with deterministic derived vectors, so HNSW, rerank, and eval behavior are measurable without calling Bedrock during bootstrap. The app tags those rows as `archive` and excludes them from shopper-facing product tools; the standalone eval harness includes them deliberately.

---

## Quick start (local dev)

The production flow is a single FastAPI process on `:8000` serving both the built React SPA and the API. For interactive iteration, run the backend with `--reload` and rebuild the frontend on save.

```bash
# 1. Aurora + Bedrock credentials
cp pellier/backend/.env.example pellier/backend/.env
# edit DB_HOST, DB_USER, DB_PASSWORD, AWS_REGION, BEDROCK_*
set -a; source pellier/backend/.env; set +a

# 2. Apply schema + seed expanded catalog + required workshop tables (one-time)
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
  -U "$DB_USER" -d "$DB_NAME" \
  -v ON_ERROR_STOP=1 \
  -f scripts/migrations/001_schema.sql
python3 scripts/seed_boutique_catalog.py --from-cache
for migration in \
  002_workshop_telemetry.sql \
  003_persona_seed.sql \
  004_anna_hybrid_search.sql \
  005_theo_returns.sql \
  006_warehouse_inventory.sql \
  007_chat_session_tables.sql \
  008_search_performance_indexes.sql \
  009_return_policies.sql
do
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -f "scripts/migrations/$migration"
done

# 3. Backend
cd pellier/backend
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 4. Frontend (separate terminal)
cd pellier/frontend
npm install
npm run build      # production build → served by FastAPI on :8000
# or: npm run dev   for HMR on :5173 (still hits backend on :8000)
```

Open <http://localhost:8000> for the Boutique, or <http://localhost:8000/atelier> for the Atelier.

### AgentCore CLI (pinned)

Pellier uses the Node-based AgentCore CLI (`@aws/agentcore`, Node.js ≥ 20), **pinned to the version this workshop is tested against**:

```bash
npx -y @aws/agentcore@0.18.0 --version
npx -y @aws/agentcore@0.18.0 deploy -y --json
```

The workshop bootstrap installs the same pinned version globally and provides an `agentcore` alias for read-only inspection (`status`, `logs`). The CLI is pre-1.0 and its command surface may change between releases – if you experiment with a newer version, expect differences from the commands documented here. This Node CLI replaces the older `agentcore configure` / `agentcore launch` starter-toolkit flow.

### Facilitator note: `SPA_MOUNT_PATH`

By default the SPA is served at `/`. The nginx layer ([`scripts/bootstrap-environment.sh:315-324`](scripts/bootstrap-environment.sh#L315-L324)) strips the `/app/` prefix (`proxy_pass http://127.0.0.1:8000/`) before forwarding to FastAPI, so root-mount works behind both Workshop Studio's `/ports/8000/*` proxy and the `/app/*` shortcut. If you ever deploy behind a proxy that forwards `/app/*` verbatim (no prefix-stripping), set:

```bash
SPA_MOUNT_PATH=/app
VITE_BASE_PATH=/app/   # bake the prefix into the bundle at build time
```

The app moves to `/app/`, `GET /app` 307-redirects to `/app/`, and the real API stays at `/api/*`. Do not register new FastAPI routes below the SPA catch-all – its `{full_path:path}` pattern shadows everything under the mount.

---

## Workshop path

This repo is the source of truth for the application behind the **governed agentic AI search workshop**, framed as a **400-level guided build + evidence walkthrough**: small code surface, deep production proof. The required path wires Marco's inventory tool path end to end, compares retrieval strategies, and proves the audit ledger from `pellier.tool_audit`. Runtime, Gateway, Memory, Policy, and MCP are exposed as guided governance reads and optional deeper inspection surfaces. Exact pacing and participant wording live in the separate Workshop Studio repo.

The session content (lab manual, CloudFormation, prereq images) lives in the separate Workshop Studio repository, which is the single source of truth for everything under its `content/`, `assets/`, and `static/` trees. This repo holds the running application the session is built on. The flagship path is structured as:

| Section | What attendees do |
|---|---|
| Introduction | Open the workspace and land in Boutique + Atelier — both already running, nothing to set up or start. Frame the architecture and the one production path attendees will wire and prove. |
| Core Lab 1: Build and Trace | Complete Stock Keeper and `floor_check`, then prove Marco's turn across routing, Aurora inventory, `tool_audit`, and execution evidence. |
| Core Lab 2: Measure Retrieval | Compare Anna's query across vector, hybrid, hybrid + rerank, and agentic retrieval, then make a quality, latency, and cost decision. |
| Core Lab 3: Query Evidence | Trigger Theo's return, query the JSONB audit ledger, reconstruct the seeded identity mismatch, and optionally inspect AgentCore Memory readback. |
| Core Lab 4: Enforce Policy | Author one Cedar rule, prove Gateway DENY prevents execution, confirm the safe path still works, and reset participant policy. |
| Optional Labs | Explore runtime skills, working memory, retrieval evaluation, HNSW behavior, multimodal search, RLS, or deeper policy only after the current core checkpoint. |
| Close | Map the pattern to your own stack, wrap up, and Q&A. |

Make canonical edits to the lab manual in the Workshop Studio repo, not here.

---

## Architecture

### Agents

Five specialist agents + one orchestrator. Three orchestration patterns ship in the codebase; the boutique runs the dispatcher pattern in production and exposes the other two as Atelier toggles.

| Agent              | Role                                            | Model            |
| ------------------ | ----------------------------------------------- | ---------------- |
| **Style Advisor**      | Interprets intent, runs semantic search         | Claude Opus 4.8  |
| **Curator**            | Pairing, palette, occasion, editorial picks     | Claude Opus 4.8  |
| **Value Analyst**      | Price intelligence, deals, percentile context   | Claude Sonnet 5 |
| **Stock Keeper**       | Warehouse stock, restocks, low-inventory alerts | Claude Sonnet 5 |
| **Experience Guide**   | Returns, care, post-purchase                    | Claude Opus 4.8  |

Per-agent model choice is an architectural decision – Stock Keeper's terse warehouse answers run on Sonnet; the Curator's editorial prose earns Opus. Factories load **`BEDROCK_OPUS_MODEL`** for editorial agents, **`BEDROCK_REPORTING_MODEL`** for reporting specialists, and **`BEDROCK_ROUTER_MODEL`** for routing – see `pellier/backend/config.py`. **`BEDROCK_SONNET_MODEL`** is the canonical Sonnet profile (`global.anthropic.claude-sonnet-5`); the model-access preflight may also write it into `BEDROCK_OPUS_MODEL` when Opus 4.8 is not reachable on the account. **`BEDROCK_CHAT_MODEL`** is the legacy alias kept only for older scripts. The Atelier surfaces the mix.

### Tools

15 `@tool` functions across the agent set:

`find_pieces` · `find_pieces_hybrid` · `style_match` · `whats_trending` · `price_intelligence` · `explore_collection` · `side_by_side` · `floor_check` · `restock_shelf` · `running_low` · `returns_and_care` · `process_return` · `preference_snapshot` · `trace_receipt` · `escalate_to_stylist`

The tool registry is itself stored in Aurora pgvector; the orchestrator uses cosine similarity to discover the right tool from a natural-language query – the same primitive that powers product search, applied to capabilities.

### Skills

Five skills loaded per turn by the SkillRouter to shape voice, handling, proof, and care language without changing product selection:

[`skills/the-packing-list/`](skills/the-packing-list/) (Marco) · [`skills/the-gift-table/`](skills/the-gift-table/) (Anna) · [`skills/the-makers-shelf/`](skills/the-makers-shelf/) (Theo) · [`skills/the-care-card/`](skills/the-care-card/) (shared care/returns) · [`skills/the-proof-counter/`](skills/the-proof-counter/) (shared proof/audit)

### Claude Code instructions and project skills

The repo deliberately demonstrates a layered coding-agent setup:

| Layer | Purpose |
|---|---|
| `~/.claude/CLAUDE.md` | Participant-global safety and workshop defaults, installed idempotently by `scripts/bootstrap-labs.sh` |
| [`CLAUDE.md`](CLAUDE.md) | Project contract, branch ownership, participant versus maintainer mode, and release gates |
| [`pellier/backend/CLAUDE.md`](pellier/backend/CLAUDE.md), [`pellier/frontend/CLAUDE.md`](pellier/frontend/CLAUDE.md), [`skills/CLAUDE.md`](skills/CLAUDE.md) | Nearest-scope engineering rules |
| [`.claude/skills/`](.claude/skills/) | On-demand Claude Code workflows for workshop verification and Pellier copy |
| [`VOICE.md`](VOICE.md) | Shared editorial voice and grounding contract |
| [`skills/*/SKILL.md`](skills/) | Pellier runtime prompt overlays loaded at backend start and selected per turn; these are application data, not Claude Code instructions |

Claude Code resolves `CLAUDE.md` guidance by scope. The backend separately loads root `skills/*/SKILL.md` at startup, and its `SkillRouter` selects from that registry during shopper turns. Keeping those systems distinct prevents a coding workflow from accidentally becoming model prompt data, or vice versa.

### Stack

| Layer            | Technology                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Database         | **Aurora PostgreSQL Serverless v2** (engine 18.3) · elastic ACU scaling · standard PostgreSQL primitives throughout (extension, schemas, SQL) |
| Vector retrieval | pgvector 0.8.1 · `vector(1024)` column · HNSW (m=16, ef_construction=64, `vector_cosine_ops`) · `<=>` cosine operator |
| Lexical retrieval | Postgres FTS – `tsvector` + GIN + `ts_rank_cd` (no native BM25; `pg_trgm` for fuzzy match) |
| Hybrid merge     | Reciprocal Rank Fusion (RRF) – fuses pgvector + FTS rank lists without normalizing raw scores |
| Models           | Claude Opus 4.8 (`global.anthropic.claude-opus-4-8`, editorial) · Claude Sonnet 5 (`global.anthropic.claude-sonnet-5`, routing/reporting, no temperature override) · Cohere Embed v4 (`us.cohere.embed-v4:0`, 1024-dim via output_dimension, inference profile) · Cohere Rerank v3.5 (`cohere.rerank-v3-5:0`) |
| Agent framework  | Strands Agents SDK – `Agent`, `@tool`, `GraphBuilder`, `BeforeToolCallEvent` hooks                                       |
| Agent infra      | Bedrock AgentCore – Runtime (`@app.entrypoint` → `InvokeAgentRuntime`) · Memory (STM, 30-day event expiry + `USER_PREFERENCE` semantic extraction strategy for durable taste) · Gateway (MCP tool catalog, Cognito-JWT auth with shopper identity passthrough) · Identity     |
| MCP              | [`awslabs.postgres-mcp-server`](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) pinned to `==1.1.6` and installed via `uvx`, registered against the Aurora cluster ARN over `--connection_method RDS_API --db_type APG` (enum-name flag, not the lowercase value; read-only by default — writes require opting in via `--allow_write_query`); `pellier/config/mcp-server-config.json` is the literal contract; AgentCore Gateway is the managed-host counterpart |
| Backend          | FastAPI · Python 3.14 · psycopg3 · boto3 · SSE streaming                                                  |
| Frontend         | React 18 · TypeScript 5 · Vite · Tailwind · Framer Motion 12                                                             |
| Editorial system | Fraunces Variable (display) · Inter (body) · JetBrains Mono (code) · cream / espresso / terracotta palette               |

---

## Repository layout

```
sample-pellier-agentic-search-apg/
├── .claude/
│   └── skills/                             Claude Code project workflows
├── CLAUDE.md                               Project and branch contract
├── VOICE.md                                Pellier editorial voice contract
├── pellier/
│   ├── backend/                           FastAPI server, agents, services
│   │   ├── CLAUDE.md                        Backend and Core Lab 1 rules
│   │   ├── agents/                          Style Advisor, Curator, Stock Keeper, ...
│   │   ├── services/                        agent_tools, chat, agentcore_*, db
│   │   ├── routes/                          FastAPI routers (transcribe, atelier, chat)
│   │   └── app.py
│   └── frontend/                          React 18 + TS + Vite SPA
│       ├── CLAUDE.md                        Boutique and Atelier rules
│       └── src/
│           ├── components/                  BoutiqueHero, ChatDrawer, ProductCard, ...
│           ├── shared/                      Cross-surface atoms – TraceChip, PresencePill
│           ├── atelier/                     Operator's surface
│           └── data/                        showcaseProducts.ts (40), personaCurations.ts
│
├── skills/                                Strands runtime skills (5) + scoped guidance
├── solutions/                             Reference implementations (drop-in escape hatches)
│   ├── the-quiet-search/                    Semantic retrieval reference
│   ├── closing-marcos-gap/                  Core Lab 1 floor_check reference
│   ├── the-ledger/                          Core Lab 3 AgentCore + audit reference
│   └── the-concierge/                       Core Lab 4 MCP and Gateway reference
│
└── scripts/
    ├── migrations/                         Ordered fresh-cluster SQL (001-009)
    ├── seed_boutique_catalog.py             40 curated products + generated retrieval distractors
    ├── bootstrap-environment.sh             Code Editor + nginx + systemd
    └── bootstrap-labs.sh                    DB seed + frontend build + service start
```

The lab manual, CloudFormation templates, and prereq images live in the separate Workshop Studio repository, which is the source of truth for all session content.

---

## Resources

- [Aurora PostgreSQL with pgvector](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)
- [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- [Model Context Protocol (MCP) specification](https://modelcontextprotocol.io/)
- [Strands Agents SDK](https://strandsagents.com/latest/)
- [pgvector 0.8.1 performance on Aurora](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)

---

## Credits

Built and curated by **Shayon Sanyal** (<shayons@amazon.com>).

## License & attribution

Licensed under the **MIT License** — © 2026 Amazon Web Services. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

**If you reuse this code, attribution is required — not optional.** MIT is deliberately chosen over MIT-0 for exactly this reason: copying any substantial portion obligates you to keep the copyright and permission notice intact. Concretely, when you fork, vendor, adapt, or build on this work:

- **Retain** the `LICENSE` and `NOTICE` files (or reproduce their text) in your distribution.
- **Credit the source** — cite the original author, *Shayon Sanyal*, and link back to <https://github.com/aws-samples/sample-pellier-agentic-search-apg>.
- **Keep this notice** in copies or substantial portions of the software, per the MIT terms.

This applies to talks, blog posts, derived workshops, and internal forks alike: take the code, but carry the credit with it. See [NOTICE](NOTICE) for the canonical attribution text to copy.
