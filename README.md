# Build governed agentic AI search with Aurora, RDS, & Bedrock AgentCore

<div align="center">

_Agentic search on Aurora PostgreSQL · Bedrock AgentCore · Strands Agents · MCP_

<br/>

[![Aurora PostgreSQL 18.3](https://img.shields.io/badge/Aurora_PostgreSQL-18.3_·_pgvector-2D72D9?style=flat-square&logo=postgresql&logoColor=white)](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)
[![Bedrock AgentCore](https://img.shields.io/badge/Bedrock-AgentCore-FF9900?style=flat-square)](https://aws.amazon.com/bedrock/agentcore/)
[![Strands Agents](https://img.shields.io/badge/Strands-Agents_SDK-232F3E?style=flat-square)](https://strandsagents.com)
[![MCP](https://img.shields.io/badge/MCP-postgres--mcp--server-4A154B?style=flat-square)](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Governed quality](https://github.com/aws-samples/sample-pellier-agentic-search-apg/actions/workflows/quality.yml/badge.svg?branch=governed)](https://github.com/aws-samples/sample-pellier-agentic-search-apg/actions/workflows/quality.yml?query=branch%3Agoverned)
[![E2E](https://github.com/aws-samples/sample-pellier-agentic-search-apg/actions/workflows/e2e.yml/badge.svg?branch=governed)](https://github.com/aws-samples/sample-pellier-agentic-search-apg/actions/workflows/e2e.yml?query=branch%3Agoverned)

[![License: MIT](https://img.shields.io/github/license/aws-samples/sample-pellier-agentic-search-apg?style=flat-square&color=00b300&label=License)](LICENSE)
[![Stars](https://img.shields.io/github/stars/aws-samples/sample-pellier-agentic-search-apg?style=flat-square&color=yellow)](https://github.com/aws-samples/sample-pellier-agentic-search-apg/stargazers)

</div>

> Educational reference implementation for a governed agentic AI search workshop.
> Not intended for production deployment without security hardening.

**Contents:** [Workshop abstract](#workshop-abstract) · [Who this is for](#who-this-is-for) · [What this is](#what-this-is) · [Governance model](#governance-model) · [Personas](#personas-reshape-everything) · [Quick start](#quick-start-local-dev) · [Workshop path](#workshop-path) · [Architecture](#architecture) · [Quality gates](#quality-gates) · [Repository layout](#repository-layout) · [Resources](#resources)

---

## Workshop abstract

Build a governed agentic AI search application with Amazon Aurora PostgreSQL and Amazon Bedrock AgentCore. Explore a retail shopping scenario where a Strands SDK dispatcher routes shoppers to specialist agents. Aurora powers hybrid search with PostgreSQL full-text search for lexical retrieval, pgvector for semantic retrieval, and Cohere Rerank for relevance ranking, while managing inventory, orders, customer records, and a queryable JSONB audit ledger. AgentCore Runtime hosts the dispatcher, Memory preserves context, Gateway exposes tools, Policy applies Cedar authorization before sensitive actions, and OpenTelemetry traces connect the managed path. Leave with reusable patterns for auditable, policy-aware agentic search applications.

---

## Who this is for

This is a **400-level (expert)** workshop application. "Level 400" is the AWS depth scale — 100 is introductory, 400 is the deepest expert tier. That refers to the **concepts on screen** (agentic orchestration, pgvector retrieval, AgentCore, MCP), not the amount of code you write.

**You will be comfortable here if you:**
- Read Python and SQL (you don't need to write much of either)
- Have used a REST API and a terminal before
- Know, at a high level, what an LLM and a vector embedding are

**You do *not* need to:** build a search system from scratch, know Strands/AgentCore/MCP in advance, or have prior agentic-AI experience. We teach those during the session.

**What you'll actually do — this is the important part.** The application is **already built and running** when you arrive. You are *not* assembling it from nothing. Your hands-on path is small and focused: you complete two marked regions — the Stock Keeper definition and its `floor_check` tool — then run **observe / measure / read** steps that prove how the production system behaves. The other specialists, tool contracts, database, and managed services are pre-wired *on purpose* so your attention goes to the agentic pattern, not setup plumbing.

> **If it feels deep, that's by design — the depth is there to learn from, not to rebuild.** You only need to complete the one guided exercise to succeed. Everything else is there to explore at your own pace.

---

## What this is

**Pellier is a fictional artisan retailer** with one promise: a shopper asks
for something in their own words, and the search understands what they mean.
Behind the storefront, specialist agents ground answers in retrieved catalog
data, read live inventory through deterministic tools, preserve useful context,
cite sources, and hand off to a human stylist when they should.

The application has two surfaces:

- **Pellier** (`/`) – the customer-facing storefront. Editorial photography, AI search, persona-aware recommendations, and a conversational drawer.
- **Pellier Labs** (`/pellier-labs`) – the live inspection surface. It runs the same Dispatcher path and exposes emitted routing, tool, Aurora, memory, and safety evidence from the current turn.

The two surfaces share design tokens, presence pill, trace chips, and a typed agent vocabulary, so an attendee crossing between them sees the same atoms in both places.

The storefront also includes a dismissible, once-per-session four-step
orientation covering browse, profile, concierge, and evidence inspection. It
never mounts over Pellier Labs, where the proof surface itself provides the
workshop orientation.

### What it demonstrates

Every claim in the workshop abstract maps to something runnable in this repo:

| Claim | Where it lives |
|---|---|
| **Grounded retrieval** on **Aurora PostgreSQL** | `pellier.product_catalog.embedding vector(1024)` · pgvector 0.8.1 · HNSW index · `<=>` cosine operator · hybrid (FTS + RRF) merge · Cohere Rerank v3.5 |
| **Agentic AI – reasoning + tool use** | Strands Agents SDK · 5 specialists × 15 `@tool` functions · deterministic dispatcher routes intent to one specialist · each specialist receives an explicit tool allowlist |
| **Model Context Protocol (MCP)** | [`awslabs.postgres-mcp-server`](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) installed via `uvx`, read-only against the Aurora cluster ARN · `pellier/config/mcp-server-config.json` is the literal contract · any MCP host (VS Code chat extension, Claude Code, Strands `MCPClient`, AgentCore Gateway) consumes the same JSON |
| **Managed tool catalog (AgentCore Gateway)** | `services/agentcore_gateway.py` lists the Gateway catalog via `MCPClient.list_tools_sync()`, then selects the routed specialist's explicit allowlist · governed Runtime requests pass the shopper's access token through (`Authorization: Bearer`) and fail closed if Gateway is unavailable |
| **Memory and personalization** | AgentCore Memory stores session events and durable preferences extracted by a `USER_PREFERENCE` strategy · Aurora customer events provide episodic history · runtime skills and MCP schemas provide procedural know-how · `tool_audit` remains operational evidence, not memory |
| **Managed AgentCore path** | One `@aws/agentcore@0.26.0` project owns Runtime, Memory, Gateway, four Lambda target registrations, AgentCore-managed service roles, the Policy engine, and Cedar policies · `deploy_lambda.py` separately creates the external Lambda functions and their Lambda execution roles · `@app.entrypoint` in `pellier/backend/agentcore_runtime.py` · CUSTOM_JWT invocation must return `rail=gateway-mcp` · encrypted, retention-bounded Runtime and trace log groups carry correlated agent, model, and structured tool spans |

## Governance model

Pellier treats governance as several enforcement and evidence boundaries, not
as one policy engine:

| Boundary | Current implementation | What it proves |
|---|---|---|
| Identity | Cognito JWT verified on the managed rail | Which authenticated human initiated the request |
| Managed execution | AgentCore Runtime with JWT passthrough | Which orchestrator ran and on which managed rail |
| Tool contract | AgentCore Gateway exposes 15 target-qualified MCP tools | Which callable capability and input schema the agent received |
| Authorization | AgentCore Policy evaluates Cedar before Gateway target execution | Whether a tool call was allowed or denied |
| Data authorization | Aurora SQL functions validate ownership and write invariants | Which records the permitted tool could actually read or mutate |
| Application evidence | `pellier.governed_receipts`, `pellier.tool_audit`, and the inventory ledger | Which decision was made, which tool ran, and what reached Aurora |
| Commerce execution | Aurora quotes, confirmation grants, reservations, payment events, outbox rows, and immutable commerce receipts | Which authenticated shopper confirmed which total, what inventory moved, and which payment state completed |

Pellier is not merely conversational commerce. It is proof-carrying commerce:
an agent can recommend pieces and prepare a cart, but it cannot complete a
purchase. Cognito identity, a short-lived server-priced quote, explicit shopper
consent, deterministic shipping and tax rules, idempotent execution, sandbox
payment state, and durable Aurora evidence determine what actually executes.
Each idempotency key is bound to one confirmation grant, and the immutable
receipt hashes the purchased line snapshot alongside identity, consent,
inventory, payment, and outbox evidence. The API recomputes that hash when the
receipt is read. The sandbox adapter is intentionally labeled in the API and
storefront; this sample does not claim to process cards or move money.

Glue Data Catalog, Amazon DataZone, and SageMaker governance are deliberately
outside this execution boundary. They can govern analytical data products,
catalog metadata, and model development, but they do not prove that a shopper
confirmed a specific total or that an order, payment state, and inventory
movement agree. Adding them to the required path would broaden the architecture
without strengthening the transaction claim.

The observability provisioner changes account-level X-Ray Transaction Search
delivery and creates three workshop log groups. Inspect the bounded cleanup plan
before an event account is retired, then run it while the workshop role still
exists:

```bash
python3 scripts/teardown_agentcore_observability.py --dry-run
python3 scripts/teardown_agentcore_observability.py --confirm-workshop-cleanup
```

The receipt records the prior account-level destination, resource policy, KMS,
and retention state. Cleanup restores resources that already existed and
deletes only log groups or policy state created by this workshop run.

### Memory model

Pellier separates four memory categories by owner and lifetime:

| Category | Current owner | What the workshop proves |
|---|---|---|
| Working / session | AgentCore Memory events | A separate Python process reads turn one before Runtime handles turn two |
| Semantic, long-term | AgentCore `USER_PREFERENCE` records | Durable preferences are extracted and retrieved by actor |
| Episodic, long-term | Aurora customer events, orders, and returns | Business history remains queryable in the system of record |
| Procedural, long-term | Checked-in runtime skills and MCP tool schemas | Instructions and tool contracts are reviewable source |

`pellier.tool_audit` is intentionally outside that table. It records what
executed and how long it took; it does not teach the agent how to work. When
managed Runtime is enabled, AgentCore Memory reads fail closed before
invocation. A post-invocation Memory write failure is surfaced as partial
evidence without recasting an action that may already have executed as failed.
The governed path never substitutes a process-local store for managed proof.

Pellier Labs provides the operator reconstruction layer: one correlated policy,
execution, trace, and Aurora data story for a selected turn.

The durable join is intentionally small. `session_id` follows the conversation
and managed invocation, `turn_id` follows an application turn, `receipt_id`
identifies the policy record, and `audit_id` links an ALLOW to the Aurora tool
row. A DENY has no `audit_id`; the absence is proof only after the receipt
helper verifies that no matching execution row exists.

RLS, column protection, pgAudit, CloudTrail, and Dogwood temporal policy are
documented production layers, not hidden claims about this sample. The required
workshop does not configure them. The checked-in
[`advanced_verified_customer_context.dogwood`](policies/advanced_verified_customer_context.dogwood)
shows how a session-history rule could require a successful context lookup
before a sensitive write. It also states the critical permit interaction:
Pellier's broad workshop permit must be narrowed before that rule can enforce
the sequence.

---

## Personas reshape everything

Sign in as one of the three returning customers and the entire storefront – hero photograph, suggestion pills, featured product, weekend edit copy, curated grid (10 exclusive products per persona, zero overlap), editorial cards, chat greeting – reshapes immediately.

| Persona  | Profile                          | Signature piece              |
| -------- | -------------------------------- | ---------------------------- |
| *Marco*  | Natural fibers, travel, linen    | Italian Linen Camp Shirt     |
| *Anna*   | Gifts, milestones, candles       | Beeswax Taper Candles        |
| *Theo*   | Slow craft, ceramics, ritual     | Stoneware Pour-Over Set      |

The **signed-out state** is the editorial baseline – a 10-piece grid anchored by the Nocturne Leather Weekender, no prior context, no profile embedding. It is the hero state, not a fourth persona.

Each persona ships with 10 curated products carrying real Cohere Embed v4
1024-dim embeddings. Those 40 story products stay stable for persona grids,
orders, inventory, and policy exercises. The governed retrieval lab expands
`pellier.product_catalog` to 1,000 rows with generated high-ID archive
distractors and deterministic derived vectors. The extra rows create enough
near-miss candidates to compare retrieval strategies without adding 960 images
or concepts for participants to learn. They are excluded from shopper-facing
tools and included only by the evaluation path.

This split is deliberate, not a scale benchmark: 40 products are the
participant-facing domain; 1,000 rows are a compact retrieval test corpus.
Pellier does not use that corpus to teach HNSW capacity planning. That deeper
retrieval-engineering work belongs in the separate Mosaic Builder Session.

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
  009_return_policies.sql \
  010_governed_receipts.sql \
  011_governed_write_integrity.sql \
  012_retrieval_receipts.sql \
  013_inventory_ledger.sql \
  014_governed_turn_receipts.sql \
  015_proof_carrying_commerce.sql
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
npm ci
npm run build      # production build → served by FastAPI on :8000
# or: npm run dev   for HMR on :5173 (still hits backend on :8000)
```

Open <http://localhost:8000> for Pellier, or <http://localhost:8000/pellier-labs> for Pellier Labs.

### AgentCore CLI (pinned)

Pellier uses the Node-based AgentCore CLI (`@aws/agentcore`, Node.js ≥ 20), **pinned to the version this workshop is tested against**:

```bash
npx -y @aws/agentcore@0.26.0 --version
cd .agentcore-project/pellier
npx -y @aws/agentcore@0.26.0 validate --json
npx -y @aws/agentcore@0.26.0 deploy --yes --json
```

The workshop bootstrap installs the same pin globally and provides an
`agentcore` shell function for inspection and participant policy changes. The
CLI is the only control-plane authority for AgentCore resources in this repo.
`deploy_lambda.py` separately creates the external Lambda functions and their
Lambda execution roles. Other Python and AWS CLI helpers remain limited to
authentication, Memory data seeding, and post-deploy verification.

Claude Code is a separate participant helper. Bootstrap installs the latest
CLI release without a package-version pin and uses its `sonnet` alias through
Amazon Bedrock, so the helper follows the current Sonnet model available at
workshop time. Pellier's application model IDs remain explicit because the
preflight invokes those exact profiles before declaring the environment ready.

### Facilitator note: `SPA_MOUNT_PATH`

By default the SPA is served at `/`. The nginx layer ([`scripts/bootstrap-environment.sh:315-324`](scripts/bootstrap-environment.sh#L315-L324)) strips the `/app/` prefix (`proxy_pass http://127.0.0.1:8000/`) before forwarding to FastAPI, so root-mount works behind both Workshop Studio's `/ports/8000/*` proxy and the `/app/*` shortcut. If you ever deploy behind a proxy that forwards `/app/*` verbatim (no prefix-stripping), set:

```bash
SPA_MOUNT_PATH=/app
VITE_BASE_PATH=/app/   # bake the prefix into the bundle at build time
```

The app moves to `/app/`, `GET /app` 307-redirects to `/app/`, and the real API stays at `/api/*`. Do not register new FastAPI routes below the SPA catch-all – its `{full_path:path}` pattern shadows everything under the mount.

---

## Workshop path

This repo is the source of truth for the application behind the **governed agentic AI search workshop**, framed as a **400-level guided build + evidence walkthrough**: small code surface, deep production proof. The required path wires Marco's inventory tool path end to end, compares retrieval strategies, proves cross-turn AgentCore Memory, invokes managed Runtime through Gateway, queries the audit ledger, and demonstrates a real Cedar ALLOW/DENY pair. Exact pacing and participant wording live in the separate Workshop Studio repo.

The session content (lab manual, CloudFormation, prereq images) lives in the separate Workshop Studio repository, which is the single source of truth for everything under its `content/`, `assets/`, and `static/` trees. This repo holds the running application the session is built on. The flagship path is structured as:

| Section | What attendees do |
|---|---|
| Introduction | Open the workspace and land in Pellier + Pellier Labs — both already running, nothing to set up or start. Frame the architecture and the one production path attendees will wire and prove. |
| Lab 1: Ground Answers in Live Data | Complete Stock Keeper and `floor_check`, then prove Marco's answer against live inventory and `tool_audit`. |
| Lab 2: Design the Retrieval Strategy | Compare Anna's query across vector, hybrid, hybrid + rerank, and agentic retrieval, then make a quality, latency, and cost decision. |
| Lab 3: Run Agents in a Managed Runtime | Invoke Runtime, enumerate Gateway tools, read turn one from Memory in a fresh process, prove turn-two recall, and reconstruct the seeded identity mismatch from Aurora evidence. |
| Lab 4: Govern and Trace Agent Actions | Author one Cedar rule, prove Gateway DENY prevents execution, confirm the matching identity is allowed, and reset participant policy. |
| Close | Map the pattern to your own stack, wrap up, and Q&A. |

Make canonical edits to the lab manual in the Workshop Studio repo, not here.

### Boundary with Mosaic

Pellier treats hybrid retrieval as one existing agent capability. Its retrieval
lab asks builders to choose among vector, hybrid, reranked, and agent-planned
strategies, then moves on to managed execution, policy, and evidence. Mosaic is
the deep retrieval-engineering session for lexical and semantic retrieval,
RRF, reranking, filters, typo tolerance, HNSW tuning, evaluation, and search
performance. Neither workshop depends on the other.

---

## Architecture

### Agents

Five specialist agents sit behind one deterministic Dispatcher. Pellier and the
managed AgentCore Runtime both use that routing contract; Pellier Labs runs it
live and reports the route actually observed.

| Agent              | Role                                            | Model            |
| ------------------ | ----------------------------------------------- | ---------------- |
| **Style Advisor**      | Interprets intent, runs semantic search         | Claude Opus 5  |
| **Curator**            | Pairing, palette, occasion, editorial picks     | Claude Opus 5  |
| **Value Analyst**      | Price intelligence, deals, percentile context   | Claude Sonnet 5 |
| **Stock Keeper**       | Warehouse stock, restocks, low-inventory alerts | Claude Sonnet 5 |
| **Experience Guide**   | Returns, care, post-purchase                    | Claude Opus 5  |

Per-agent model choice is an architectural decision – Stock Keeper's terse warehouse answers run on Sonnet; the Curator's editorial prose earns Opus. Factories load **`BEDROCK_OPUS_MODEL`** for editorial agents, **`BEDROCK_REPORTING_MODEL`** for reporting specialists, and **`BEDROCK_ROUTER_MODEL`** for routing – see `pellier/backend/config.py`. **`BEDROCK_SONNET_MODEL`** is the canonical Sonnet profile (`global.anthropic.claude-sonnet-5`); the model-access preflight may also write it into `BEDROCK_OPUS_MODEL` when Opus 5 is not reachable on the account. **`BEDROCK_CHAT_MODEL`** is the legacy alias kept only for older scripts. Pellier Labs surfaces the mix.

### Tools

15 `@tool` functions across the agent set:

`find_pieces` · `find_pieces_hybrid` · `style_match` · `whats_trending` · `price_intelligence` · `explore_collection` · `side_by_side` · `floor_check` · `restock_shelf` · `running_low` · `returns_and_care` · `process_return` · `preference_snapshot` · `trace_receipt` · `escalate_to_stylist`

Aurora also stores a semantic tool registry for the retrieval-strategy teaching
surface. It is not the governed execution selector. The managed Dispatcher
classifies intent, chooses one specialist, lists Gateway tools, and filters that
catalog against the specialist's checked-in allowlist.

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
| Models           | Claude Opus 5 (`global.anthropic.claude-opus-5`, editorial) · Claude Sonnet 5 (`global.anthropic.claude-sonnet-5`, routing/reporting, no temperature override) · Cohere Embed v4 (`us.cohere.embed-v4:0`, 1024-dim via output_dimension, inference profile) · Cohere Rerank v3.5 (`cohere.rerank-v3-5:0`) |
| Agent framework  | Strands Agents SDK – `Agent`, `@tool`, deterministic Dispatcher, and before/after tool-call hooks |
| Agent infra      | Bedrock AgentCore – Runtime (CUSTOM_JWT, fail-closed Gateway MCP rail) · Memory (STM, 30-day event expiry + `USER_PREFERENCE` semantic extraction strategy for durable taste) · Gateway (15-tool MCP catalog, Cognito access-token passthrough) · Policy (Cedar ENFORCE with live ALLOW/DENY proof) · Identity |
| MCP              | [`awslabs.postgres-mcp-server`](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) pinned to `==1.1.6` and installed via `uvx`, registered against the Aurora cluster ARN over `--connection_method RDS_API --db_type APG` (enum-name flag, not the lowercase value; read-only by default — writes require opting in via `--allow_write_query`); `pellier/config/mcp-server-config.json` is the literal contract; AgentCore Gateway is the managed-host counterpart |
| Backend          | FastAPI · Python 3.14 · psycopg3 · boto3 · SSE streaming                                                  |
| Frontend         | React 18 · TypeScript 5 · Vite 6 · Tailwind CSS 3 · Framer Motion 12                                                      |
| Editorial system | Fraunces Variable and Instrument Serif (display) · Instrument Sans (body) · JetBrains Mono (code) · self-hosted fonts     |

---

## Quality gates

The `governed-quality` workflow runs the complete backend and frontend release
gate on pushes and pull requests to `governed`:

```bash
cd pellier/backend
python -m pytest -q
python tests/test_copy_compliance.py

cd ../frontend
npm test -- --run
npm run type-check
npm run lint
npm run build
npm audit --omit=dev --audit-level=high

cd ../..
git diff --check
find scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

The `e2e` workflow builds the production SPA, serves it through FastAPI in
smoke mode, and walks the storefront, Pellier Labs, personas, streaming, and
reset path in Chromium. The optional Cognito suite runs only when its isolated
development-pool secrets are configured.

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
│   │   ├── CLAUDE.md                        Backend and Lab 1 rules
│   │   ├── agents/                          Style Advisor, Curator, Stock Keeper, ...
│   │   ├── services/                        agent_tools, chat, agentcore_*, db
│   │   ├── routes/                          FastAPI routers (transcribe, agent_trace, chat)
│   │   └── app.py
│   └── frontend/                          React 18 + TS + Vite SPA
│       ├── CLAUDE.md                        Storefront and Pellier Labs rules
│       └── src/
│           ├── components/                  BoutiqueHero, ChatDrawer, ProductCard, ...
│           ├── shared/                      Cross-surface atoms – TraceChip, PresencePill
│           ├── agent-trace/                    Operator evidence surface
│           └── data/                        showcaseProducts.ts (40), personaCurations.ts
│
├── skills/                                Strands runtime skills (5) + scoped guidance
├── solutions/                             Reference implementations (drop-in escape hatches)
│   ├── the-quiet-search/                    Semantic retrieval reference
│   ├── closing-marcos-gap/                  Lab 1 floor_check reference
│   ├── the-ledger/                          Labs 3-4 AgentCore + audit reference
│   └── the-concierge/                       Lab 4 MCP and Gateway reference
│
└── scripts/
    ├── migrations/                         Ordered fresh-cluster SQL (001-015)
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

## Credits and license

Built and curated by **Shayon Sanyal** (<shayons@amazon.com>).

Licensed under the [MIT License](LICENSE), copyright 2026 Amazon Web Services.
The license requires the copyright and permission notice to remain in copies or
substantial portions of the software. See [NOTICE](NOTICE) for the project's
requested attribution format for derived workshops, talks, and other reuse.
