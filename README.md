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

**Contents:** [Workshop abstract](#workshop-abstract) · [Who this is for](#who-this-is-for) · [What this is](#what-this-is) · [Closed loop](#shopper-to-operator-closed-loop) · [Governance model](#governance-model) · [Personas](#personas-reshape-everything) · [Quick start](#quick-start-local-dev) · [Workshop path](#workshop-path) · [Architecture](#architecture) · [Quality gates](#quality-gates) · [Repository layout](#repository-layout) · [Resources](#resources)

**Team teaching map:** [WORKSHOP.md](WORKSHOP.md) connects the four participant labs
to the guest, Marco, Anna, Theo, and Jessica golden journeys and their proof
boundaries.

---

## Workshop abstract

Build a governed agentic AI search application with Amazon Aurora PostgreSQL and Amazon Bedrock AgentCore. Explore a retail shopping scenario where a Strands SDK dispatcher routes shoppers to specialist agents and a bounded Strands graph coordinates operator investigation and resolution planning. Aurora powers hybrid search with PostgreSQL full-text search for lexical retrieval, pgvector for semantic retrieval, and Cohere Rerank for relevance ranking, while managing inventory, orders, customer records, durable human checkpoints, and queryable JSONB evidence. AgentCore Runtime hosts the managed dispatcher and is the deployment target for the operator graph; Memory preserves context, Gateway exposes tools, Policy applies Cedar authorization before sensitive actions, Aurora Row-Level Security scopes what each shopper's agent can read, and OpenTelemetry traces connect the managed path. Leave with reusable patterns for auditable, policy-aware agentic search applications.

---

## Who this is for

This is a **400-level (expert)** workshop application. "Level 400" is the AWS depth scale — 100 is introductory, 400 is the deepest expert tier. That refers to the **concepts on screen** (agentic orchestration, pgvector retrieval, AgentCore, MCP), not the amount of code you write.

**You will be comfortable here if you:**
- Read Python and SQL (you don't need to write much of either)
- Have used a REST API and a terminal before
- Know, at a high level, what an LLM and a vector embedding are

**You do *not* need to:** build a search system from scratch, know Strands/AgentCore/MCP in advance, or have prior agentic-AI experience. We teach those during the session.

**What you'll actually do — this is the important part.** The application is **already built and running** when you arrive. You are *not* assembling it from nothing. Your hands-on path is small and focused: each lab has one build. Lab 1 completes two marked regions in code, the Inventory Agent definition and its `check_inventory` tool; Labs 2, 3 and 4 each complete a single artifact — `workshop/lab-2-rrf.sql`, `workshop/lab-3-otel-contract.jq`, and `workshop/lab-4-rls.sql` — and every one has a reference copy under `solutions/` if you need it. Around those builds you run **observe / measure / read** steps that prove how the production system behaves. The other specialists, tool contracts, database, and managed services are pre-wired *on purpose* so your attention goes to the agentic pattern, not setup plumbing.

> **If it feels deep, that's by design — the depth is there to learn from, not to rebuild.** Each lab asks for one small build, and every one has a documented recovery path. Everything else is there to explore at your own pace.

---

## What this is

**Pellier is a fictional artisan retailer** with one promise: a shopper asks
for something in their own words, and the search understands what they mean.
Behind the storefront, specialist agents ground answers in retrieved catalog
data, read live inventory through deterministic tools, preserve useful context,
cite sources, and hand off to a human stylist when they should.

The application has three connected surfaces:

- **Pellier** (`/`) – the customer-facing storefront. Editorial photography, AI search, persona-aware recommendations, and a conversational drawer.
- **Pellier Operator** (`/operator`) – the authenticated client desk. A two-agent Strands graph separates case investigation from resolution planning; durable reviews, human decisions, and governed execution stay outside the graph invocation.
- **Pellier Observatory** (`/observatory`) – the live inspection surface. It exposes both production orchestration paths and reconstructs the shopper handoff, pending review, graph artifact, human decision, and execution evidence from their owning records.

The surfaces share design tokens and a typed agent vocabulary, so an attendee
crossing between them sees the same system rather than three unrelated demos.

The storefront also includes a dismissible, once-per-session four-step
orientation covering browse, profile, concierge, and evidence inspection. It
never mounts over Pellier Observatory, where the proof surface itself provides the
workshop orientation.

### What it demonstrates

Every claim in the workshop abstract maps to something runnable in this repo:

| Claim | Where it lives |
|---|---|
| **Grounded retrieval** on **Aurora PostgreSQL** | `pellier.product_catalog.embedding vector(1024)` · pgvector 0.8.1 · HNSW index · `<=>` cosine operator · hybrid (FTS + RRF) merge · Cohere Rerank v3.5 |
| **Agentic AI – reasoning + tool use** | Strands Agents SDK · deterministic Storefront Dispatcher routes intent to one of 5 specialists · each specialist receives an explicit tool allowlist · Operator Concierge uses `GraphBuilder` for an ordered Case Investigator -> Resolution Planner graph |
| **Model Context Protocol (MCP)** | [`awslabs.postgres-mcp-server`](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) installed via `uvx`, read-only against the Aurora cluster ARN · `pellier/config/mcp-server-config.json` is the literal contract · any MCP host (VS Code chat extension, Claude Code, Strands `MCPClient`, AgentCore Gateway) consumes the same JSON |
| **Managed tool catalog (AgentCore Gateway)** | `services/agentcore_gateway.py` lists the Gateway catalog via `MCPClient.list_tools_sync()`, then selects the routed specialist's explicit allowlist · governed Runtime requests pass the shopper's access token through (`Authorization: Bearer`) and fail closed if Gateway is unavailable |
| **Memory and personalization** | AgentCore Memory stores session events and durable preferences extracted by a `USER_PREFERENCE` strategy · Aurora customer events provide episodic history · runtime skills and MCP schemas provide procedural know-how · `tool_audit` remains operational evidence, not memory |
| **Managed AgentCore path** | One `@aws/agentcore@0.26.0` project owns Runtime, Memory, Gateway, four Lambda target registrations, AgentCore-managed service roles, the Policy engine, and Cedar policies · `deploy_lambda.py` separately creates the external Lambda functions and their Lambda execution roles · `@app.entrypoint` in `pellier/backend/agentcore_runtime.py` · CUSTOM_JWT invocation must return `rail=gateway-mcp` · encrypted, retention-bounded Runtime and trace log groups carry correlated agent, model, and structured tool spans |
| **Durable human handoff** | The shopper turn stores an immutable, explicitly untrusted `handoff_context` beside its terminal receipt · `pellier.approvals` owns the pending review and exact action hash · the graph persists only operator-safe artifacts · confirmation and execution are later authenticated requests |

### Shopper-to-operator closed loop

The customer and operator experiences share durable business state, not model
memory or an in-process callback. A storefront specialist can prepare a bounded
proposal, but it cannot approve or execute it:

```text
shopper request
  -> Storefront Dispatcher selects one specialist
  -> PostgreSQL stores an immutable, untrusted handoff
  -> PostgreSQL stores a pending review and exact action hash

authorized operator opens the review
  -> Case Investigator Agent reads current evidence
  -> Resolution Planner Agent proposes a bounded resolution
  -> PostgreSQL stores the operator-safe graph artifact

separate authenticated requests
  -> human confirms or declines the exact action hash
  -> a confirmed, published action enters AgentCore Gateway and Policy
  -> PostgreSQL enforces the write and stores the outcome evidence
  -> Observatory reconstructs the complete lineage
```

This is intentionally not one long-running agent invocation. The Strands graph
ends after investigation and planning; human decision, policy authorization,
database enforcement, and outcome evidence remain separate, replayable
boundaries. `initiate_return` follows that complete managed path.
`issue_credit` remains deliberately unpublished and therefore has no Cedar
verdict; its operator-group API boundary and PostgreSQL controls must not be
misreported as policy enforcement. See [WORKSHOP.md](WORKSHOP.md) for the Marco,
Anna, Theo, Jessica, and guest journeys that teach this pattern.

## Governance model

Pellier treats governance as several enforcement and evidence boundaries, not
as one policy engine:

| Boundary | Current implementation | What it proves |
|---|---|---|
| Identity | Cognito JWT verified on the managed rail | Which authenticated human initiated the request |
| Managed execution | AgentCore Runtime with JWT passthrough | Which orchestrator ran and on which managed rail |
| Tool contract | AgentCore Gateway exposes a 17-tool target-qualified MCP catalog, 15 of them published to participants | Which callable capability and input schema the agent received |
| Authorization | AgentCore Policy evaluates Cedar before Gateway target execution | Which of five states the call reached: `ALLOW`, `DENY`, `WOULD_DENY` (a real LOG_ONLY decision flip), `EVALUATION_INCOMPLETE` (the engine could not be read), or `POLICY_INFERRED` (a match against policy text, which is never presented as a decision) |
| Data authorization | Aurora SQL functions validate ownership and write invariants | Which records the permitted tool could actually read or mutate |
| Row-level authorization | PostgreSQL RLS policies on `orders` and `returns`, enforced against the `pellier_agent` and `pellier_query` roles (neither holds `BYPASSRLS`) and scoped by the `pellier.principal_sub` GUC through `pellier.principal_customers` | That a permitted tool holding a valid token still cannot read another shopper's rows, enforced by the database rather than by application code |
| Generated-SQL authorization | `services/governed_query.py` wraps model-generated SQL as a subquery, inspects the plan with `EXPLAIN (FORMAT JSON, VERBOSE)`, and executes read-only under a statement timeout, fixed `search_path`, schema allowlist, and row cap | That structure and privilege, not prompt wording, decide what a natural-language question may reach |
| Application evidence | `pellier.governed_receipts`, `pellier.tool_audit`, `pellier.governed_turn_receipts`, `pellier.governed_query_receipts`, `pellier.retrieval_receipts`, `pellier.policy_decisions`, `pellier.workshop_runs`, and the inventory ledger | Which decision was made, which tool ran, and what reached Aurora |
| Evidence immutability | Migration 047 makes `governed_receipts` and `execution_receipts` append-only by trigger, and lets `tool_audit` and `write_operations` be filled exactly once, with the unrestricted UPDATE grant revoked | That a receipt cannot be edited after the fact by the application that wrote it |
| Fail-closed writes | In governed format a write refuses when the Gateway URL, the access token, or the policy engine is missing, recording a receipt with rail `refused` and returning HTTP 409 | That an ungoverned write is refused and recorded, rather than quietly falling back to the in-process rail |
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

Pellier Observatory provides the operator reconstruction layer: one correlated policy,
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

The **signed-out state** is the editorial baseline – a nine-piece grid anchored by the Nocturne Leather Weekender, no prior context, no profile embedding. It is the hero state, not a fourth persona.

Each of the three personas ships with 10 curated products carrying real Cohere
Embed v4 1024-dim embeddings, alongside 10 pieces for the signed-out edit, 10
house pieces the client book owns, and 10 signature investment pieces. Those 60
story products stay stable for persona
grids, orders, inventory, and policy exercises. The governed retrieval lab
expands `pellier.product_catalog` to 1,000 rows with generated high-ID archive
distractors and deterministic derived vectors. The extra rows create enough
near-miss candidates to compare retrieval strategies without adding 940 images
or concepts for participants to learn. They are excluded from shopper-facing
tools and included only by the evaluation path.

This split is deliberate, not a scale benchmark: 60 products are the
participant-facing domain; 1,000 rows are a compact retrieval test corpus.
Pellier does not use that corpus to teach HNSW capacity planning. That deeper
retrieval-engineering work belongs in the separate Mosaic Builder Session.

---

## Quick start (local dev)

The production flow is a single FastAPI process on `:8000` serving both the built React SPA and the API. For interactive frontend work, `npm run dev` starts an isolated Pellier API on `:8003`, waits for it to become healthy, then starts Vite on `:5173` with a same-origin API proxy. When the configured Aurora cluster is private and its security group names a Pellier SSM tunnel, the launcher opens that approved tunnel and reads its database credentials from the configured Secrets Manager ARN. This keeps Aurora private and prevents another local workshop using `:8000` from being mistaken for Pellier.

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
python3 scripts/seed_pellier_catalog.py --from-cache
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
  015_proof_carrying_commerce.sql \
  016_runtime_roles_rls.sql \
  017_governed_query_receipts.sql \
  018_client_book.sql \
  019_operator_desk.sql \
  020_operator_review.sql \
  021_governed_execution.sql \
  022_write_operation_vocabulary.sql \
  023_idempotency_claims_release_on_failure.sql \
  024_operator_episodes.sql \
  025_execution_receipts.sql \
  026_episode_outcome_lineage.sql \
  027_canonical_span_table.sql \
  028_shopper_operator_handoff.sql \
  029_live_surface_data.sql \
  030_storefront_editorial_order.sql \
  031_refine_fresh_storefront_edit.sql \
  032_restore_fresh_runner_edit.sql \
  033_extend_curated_inventory.sql \
  034_refine_persona_personalities.sql \
  035_expand_persona_discovery_grids.sql \
  036_refresh_persona_hero_alt_text.sql \
  037_serve_persona_hero_masters.sql \
  038_principal_customer_cardinality.sql \
  039_return_replay_scope.sql \
  040_resequence_theo_governed_turn.sql \
  041_align_theo_pairing_preview.sql \
  042_align_anna_guided_previews.sql \
  043_evidence_ledger.sql \
  044_operator_lifecycle_ledger.sql \
  045_persona_blurbs.sql \
  046_retrieval_citation_snapshots.sql \
  047_evidence_immutability.sql \
  048_policy_decisions.sql \
  049_workshop_runs.sql
do
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -f "scripts/migrations/$migration"
done

# 3. HMR development stack
cd pellier/backend
python3 -m venv .venv
./.venv/bin/python -m pip install --require-hashes -r requirements.lock
cd pellier/frontend
npm ci
npm run dev        # API on :8003, Vite on :5173
```

For a production-style local run, build the frontend, then start FastAPI on
`:8000`:

```bash
cd pellier/frontend
npm run build
cd ../backend
./.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

With the production build, open <http://localhost:8000>,
<http://localhost:8000/operator>, or <http://localhost:8000/observatory>.
With `npm run dev`, use the same paths on <http://127.0.0.1:5173>.

### Local PostgreSQL journey rehearsal

After migrations `001-030` and the catalog seed have been applied to a local
`pellier_dev` database, prepare the Theo shopper-to-operator checkpoint and
survey Jessica's deliberately contradictory evidence:

```bash
# Read-only survey of the current local state.
python3 scripts/seed_local_golden_journeys.py

# Add only Theo's pending review and immutable shopper handoff.
python3 scripts/seed_local_golden_journeys.py --apply

# Verify the resulting local state.
python3 scripts/seed_local_golden_journeys.py
```

The helper refuses non-loopback hosts and database names that do not end in
`_dev`. It never confirms or executes the review and never writes an AgentCore
or Cedar verdict. Local PostgreSQL proves the application workflow and durable
lineage; the managed Runtime, Gateway, Memory, and Policy proofs still require
the workshop AWS environment.

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

By default the SPA is served at `/`. The nginx layer ([`scripts/bootstrap-environment.sh:339-340`](scripts/bootstrap-environment.sh#L315-L324)) strips the `/app/` prefix (`proxy_pass http://127.0.0.1:8000/`) before forwarding to FastAPI, so root-mount works behind both Workshop Studio's `/ports/8000/*` proxy and the `/app/*` shortcut. If you ever deploy behind a proxy that forwards `/app/*` verbatim (no prefix-stripping), set:

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
| Introduction | Open the workspace and land in Pellier + Pellier Observatory — both already running, nothing to set up or start. Frame the architecture and the one production path attendees will wire and prove. |
| Lab 1: Build a PostgreSQL-Grounded Agent | Complete Inventory Agent and `check_inventory`, then prove Marco's answer against live inventory and `tool_audit`. |
| 02 MEASURE HYBRID RETRIEVAL — Search, Filters, and Trade-offs | Compare Anna's query across vector, hybrid, hybrid + rerank, and agentic retrieval, then make a quality, latency, and cost decision. |
| 03 OPERATE THE MANAGED AGENT PATH — Runtime, Gateway, Memory, and Trace | Invoke Runtime, enumerate Gateway tools, read turn one from Memory in a fresh process, prove turn-two recall, and reconstruct the seeded identity mismatch from Aurora evidence. |
| 04 GOVERN AND PROVE ACTIONS — Human Decision, Policy, Database, and Receipts | Author one Cedar rule, prove Gateway DENY prevents execution, confirm the matching identity is allowed, complete Jessica's Operator investigation up to the human checkpoint, prove Row-Level Security refuses another shopper's rows, replay a write to show it applies exactly once, and reset participant policy. |
| Close | Map the pattern to your own stack, wrap up, and Q&A. |

Make canonical edits to the lab manual in the Workshop Studio repo, not here.

### Workshop run tooling

Four commands carry a participant through that path. Bootstrap aliases each one,
and every one of them is scoped to a single run.

| Command | Script | What it does |
|---|---|---|
| `workshop-start [persona]` | `scripts/workshop-start.sh` | Mints one run id, records it in `pellier.workshop_runs`, exports `PELLIER_RUN_ID` to the service, and restarts. Idempotent: a second call reuses the existing id. |
| `doctor --lab N` | `scripts/workshop_doctor.py` | Checks that lab's prerequisites and prints PASS or FAIL per check with the reason. Exits 1 on any failure. |
| `lab3-start` | `scripts/lab3-start.sh` | Verifies Gateway and Runtime, validates the provisioning receipt, switches the storefront to the managed rail, restarts, and proves one authenticated turn reported `gateway-mcp`. Refuses if either resource is missing. |
| `receipt` | `scripts/build_receipt.py` | Assembles the portable evidence receipt for the run. `--strict` exits 1 unless every lab's contract is proved **and** the evidence was scoped to that run, so an unapplied migration 049 fails rather than grading someone else's rows; the default reports honestly and exits 0. |

`scripts/prove-reset-cycles.sh` is the release check behind those commands: it
runs the governed reset, a journey smoke, then both again, and exits non-zero
unless both cycles pass. A reset that only works once is not a reset.

Migration 049 gives every evidence table a `run_id` column defaulted from the
`pellier.run_id` session setting, which `services/database.py` binds on each
pooled connection from `services/workshop_run.py`. No writer names the column,
so one participant's evidence is separable from a seeded incident or a previous
run without changing a single INSERT. Rows written outside that pool carry no
run id, and the receipt reports them as unattributed rather than as absent.

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
managed AgentCore Runtime both use that routing contract; Pellier Observatory runs it
live and reports the route actually observed.

| Agent              | Role                                            | Model            |
| ------------------ | ----------------------------------------------- | ---------------- |
| **Search Agent**      | Interprets intent, runs semantic search         | Claude Opus 4.6  |
| **Personalization Agent**            | Pairing, palette, occasion, editorial picks     | Claude Opus 4.6  |
| **Pricing Agent**      | Price intelligence, deals, percentile context   | Claude Sonnet 4.6 |
| **Inventory Agent**       | Warehouse stock, restocks, low-inventory alerts | Claude Sonnet 4.6 |
| **Customer Service Agent**   | Returns, care, post-purchase                    | Claude Opus 4.6  |

The Operator Concierge adds two bounded graph nodes:

| Graph node | Responsibility |
|---|---|
| **Case Investigator Agent** | Reconstruct current customer, order, ticket, review, and handoff evidence without treating shopper text as authoritative |
| **Resolution Planner Agent** | Turn the investigation artifact into a constrained recommendation tied to the pending review |

`GraphBuilder` orders those nodes and persists the graph result. Neither node
decides the review, invokes the governed write, or substitutes for AgentCore
Policy where it applies or PostgreSQL enforcement.

Per-agent model choice is an architectural decision – Inventory Agent's terse warehouse answers run on Sonnet; the Personalization Agent's editorial prose earns Opus. Factories load **`BEDROCK_OPUS_MODEL`** for editorial agents, **`BEDROCK_REPORTING_MODEL`** for reporting specialists, **`BEDROCK_ROUTER_MODEL`** for routing, and **`BEDROCK_FAST_MODEL`** for the explicit Fast response mode – see `pellier/backend/config.py`. The fast profile is Claude Haiku 4.5 (`global.anthropic.claude-haiku-4-5-20251001-v1:0`) and is preflighted before the workshop is marked ready. **`BEDROCK_SONNET_MODEL`** is the canonical Sonnet profile (`global.anthropic.claude-sonnet-4-6`); the model-access preflight may also write it into `BEDROCK_OPUS_MODEL` when Opus 4.6 is not reachable on the account. **`BEDROCK_CHAT_MODEL`** is the legacy alias kept only for older scripts. Pellier Observatory surfaces the configured mix and the exact model used by each live run.

### Tools

17 `@tool` functions form the Gateway catalog. Discovery returns all 17 by
exact name; this iteration publishes 15 of them to participants, holding back
`issue_credit` and `get_ticket_history`. The 15 published names are:

`search_products` · `search_products_hybrid` · `get_related_products` · `get_trending_products` · `get_price_analysis` · `browse_category` · `compare_products` · `check_inventory` · `restock_inventory` · `get_low_stock` · `get_return_policy` · `initiate_return` · `get_customer_preferences` · `get_audit_trail` · `escalate_to_human`

#### One search executor

`services/planned_hybrid_retrieval.execute_search_plan` is the single pipeline
behind the shipped path: a typed plan, hard predicates pushed into **both**
branches, vector and full-text retrieval, RRF, a bounded rerank, a final
eligibility recheck, then the rows returned. The storefront's
`search_products_hybrid`, the Observatory's strategy comparison, the Lab 2
receipt and `scripts/eval_retrieval_harness.py` all call it, which is what lets
the evaluation speak for the shipped path rather than for a parallel copy of it.

Two surfaces keep their own pipelines on purpose and say so at the top of each
file: `services/replacement_search.find_replacements` enforces predicates the
executor has no parameter for and exits its relaxation ladder on a different
signal, and `app.explain_search` exists to expose the stages the executor
collapses.

`GET /api/observatory/search-strategies/micro-eval` compares rerank pool sizes
on one canonical query and reports candidate coverage, context precision,
reciprocal rank, hard-constraint violations, short-result rate, citation
coverage, and p50/p95 latency. Its cost is bounded: repetitions are capped,
deterministic metrics are scored once, and a request may compare at most four
pool sizes.

Retrieval receipts cite the rows the shopper actually received, not the whole
rerank pool, and freeze the cited text, source URI and revision with a SHA-256
snapshot at retrieval time, so a later catalog edit cannot rewrite what an
answer was based on.

An 18th tool, `query_business_records`, is **implemented for the in-process rail
only, and is currently bound to no specialist**, so nothing invokes it today.
That is 18 `@tool` functions in total: the 17-tool Gateway catalog plus this one.
Wiring it is a deliberate product decision, not an oversight: it needs an owning
specialist, prompt language that makes it the last resort behind the curated
tools, and a receipt surface. Until then it ships governed and unreachable
rather than reachable and ungoverned. `tests/test_tool_ownership.py` records
that decision and fails if a specialist quietly imports it.

It is off the Gateway for separate reasons, and not because the Gateway path is
incapable. The RDS Data API is single-statement
per `execute_statement` call ("Multistatements aren't supported", box-verified:
a prepended `SET` once killed every read tool on the Gateway path), but it does
support explicit transactions, and session-local state persists across calls
that share a `transactionId`. Measured on the live cluster:

```
begin_transaction()
  SET LOCAL ROLE pellier_query          -> current_user becomes pellier_query
  SET TRANSACTION READ ONLY             -> a subsequent write is refused
  set_config('pellier.principal_sub',…) -> readable in the next call
  SELECT DISTINCT customer_id FROM pellier.orders
      as CUST-THEO -> ['CUST-THEO']     (own row visible)
      as CUST-ANNA -> []                (someone else's row invisible)
```

So the owner identity behind the fixed `--secret_arn` is not the obstacle
either: `SET LOCAL ROLE` drops into a role that holds neither `BYPASSRLS` nor
superuser, and RLS then applies to the rest of the transaction.

It stays off the Gateway for two other reasons. First, cost shape: each
statement is one HTTPS round trip, so a governed query needs seven where the
existing read tools need one. Second, and decisive, publishing it would mean a
second copy of the boundary (subquery wrap, plan inspection, schema allowlist,
row cap, receipt write) living in a Lambda deploy artifact, reviewed and tested
apart from `services/governed_query.py`. These same Lambdas already record two
drift incidents against the in-process rail: column names (`42703`) and
`hnsw.iterative_scan` tuning. Duplicating a query is a bug; duplicating a
security boundary is a class of bug. If it is ever published, the target should
call the reviewed boundary rather than restate it.

`tests/test_managed_gateway_tool_contract.py` pins this: the assertion is
`in-process == CANONICAL | IN_PROCESS_ONLY`, so adding a tool without deciding
which category it belongs to fails rather than silently diverging.

Aurora also stores a semantic tool registry for the retrieval-strategy teaching
surface. It is not the governed execution selector. The managed Dispatcher
classifies intent, chooses one specialist, lists Gateway tools, and filters that
catalog against the specialist's checked-in allowlist.

### Governed natural-language data access

A shopper question becomes SQL only through a boundary the model cannot argue
with. Generation is constrained (approved schema context, temperature 0,
explicit read-only contract), but generation is not the security boundary.
Every statement is wrapped as a subquery, planned before it runs, and executed
as `pellier_query`:

```
READ ONLY · statement_timeout = 3s · fixed search_path
SET LOCAL ROLE pellier_query · pellier.principal_sub bound for RLS
schema allowlist from the plan · implementation-owned row cap
```

A write, a utility statement, a data-modifying CTE, or a stacked statement
fails on the planner's grammar rather than on a keyword blocklist. Every
attempt writes a row to `pellier.governed_query_receipts`, refusals included,
because a rejected statement leaves no trace anywhere else: it never reached
the database. The receipt is written by `run_governed_query` itself, so no
caller can produce an unreceipted attempt.

`scripts/compare_query_lanes.py` runs the same question through this lane and
through the Postgres MCP lane and reports what each leaves behind. The point is
not that one is better. The MCP lane's credential is the table owner, so it
sees every customer and can read the authorization map itself; the governed
lane answers to a shopper's identity. Choosing between them is a governance
decision, and the difference is visible in the evidence.

### Observability and reconstruction

Evidence spans carry `turn_id`, identity, policy verdict, and execution
outcome, and export collectorless to the CloudWatch X-Ray OTLP endpoint. The
endpoint accepts SigV4 only, and signing happens in a `requests` auth hook so
the bytes signed are the bytes sent, with refreshable credentials so a rotating
instance role keeps exporting. Spans land in the `aws/spans` log group through
Transaction Search at 100% indexing, because the reconstruction exercise asks a
participant to find one specific turn and a sampled turn cannot be found by
`turn_id`.

Model prompts and completions are withheld: Strands' attribute redaction is
installed before the tracer is constructed, so `gen_ai.input.messages` and its
siblings export as `[REDACTED]` while `pellier.*` correlation attributes pass
through untouched. Spans locate a turn. Aurora proves what it did.

| Script | What it does |
|---|---|
| `scripts/reconstruct_turn.py <turn_id>` | Reconstructs one turn from exported spans. `--aurora` adds the correlated Aurora artifacts, which is the answer key for the forensic exercise. Prints the Aurora side even when a turn has no spans, since the seeded turns are Aurora-only |
| `scripts/policy_mode.py` | Reads live Cedar modes, and changes them through the AgentCore CLI project rather than boto3. `--restore-shipped` resets. Refuses to edit a declaration it cannot deploy |
| `scripts/prove_governance_windows.py` | Runs the same forbidden request in both enforcement windows. Restores the shipped mode in a `finally` block so a crashed run cannot leave the account in monitor mode |
| `scripts/score_governance_evidence.py` | Scores the governance invariants from evidence alone, with no model and no managed evaluation service |
| `scripts/seed_forensic_dataset.py` | Seeds the three reconstruction turns: allowed, enforce-denied, and log-only dual refusal |
| `scripts/seed_principal_mappings.py` | Maps each named shopper's Cognito subject to their customer id. An empty mapping denies every signed-in shopper their own orders, so `--check` runs during reset |

Cedar enforcement has two independent scopes with different vocabularies, and
conflating them is the usual mistake: a policy carries
`UpdatePolicy.enforcementMode` (`ACTIVE` or `LOG_ONLY`), while the gateway
attachment carries `policyEngineConfiguration.mode` (`ENFORCE` or `LOG_ONLY`).
The "on" value differs by scope, `UpdatePolicyEngine` carries no mode at all,
and effective behavior is the conjunction: `LOG_ONLY` at either scope means no
denial.

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
| Models           | Claude Opus 4.6 (`global.anthropic.claude-opus-4-6-v1`, editorial) · Claude Sonnet 4.6 (`global.anthropic.claude-sonnet-4-6`, routing/reporting, no temperature override) · Claude Haiku 4.5 (`global.anthropic.claude-haiku-4-5-20251001-v1:0`, explicit Fast response mode) · Cohere Embed v4 (`us.cohere.embed-v4:0`, 1024-dim via output_dimension, inference profile) · Cohere Rerank v3.5 (`cohere.rerank-v3-5:0`) |
| Agent framework  | Strands Agents SDK – `Agent`, `@tool`, deterministic Storefront Dispatcher, bounded Operator Concierge `GraphBuilder`, and before/after tool-call hooks |
| Agent infra      | Bedrock AgentCore – Runtime (CUSTOM_JWT, fail-closed Gateway MCP rail; managed Storefront proof and Operator graph deployment target) · Memory (STM, 30-day event expiry + `USER_PREFERENCE` semantic extraction strategy for durable taste) · Gateway (15-tool governed workshop subset from Pellier's 17-tool MCP catalog, Cognito access-token passthrough) · Policy (Cedar ENFORCE with live ALLOW/DENY proof) · Identity |
| MCP              | [`awslabs.postgres-mcp-server`](https://github.com/awslabs/mcp/tree/main/src/postgres-mcp-server) pinned to `==1.1.6` and installed via `uvx`, registered against the Aurora cluster ARN over `--connection_method RDS_API --db_type APG` (enum-name flag, not the lowercase value; read-only by default — writes require opting in via `--allow_write_query`); `pellier/config/mcp-server-config.json` is the literal contract; AgentCore Gateway is the managed-host counterpart |
| Backend          | FastAPI · Python 3.14 · psycopg3 · boto3 · SSE streaming                                                  |
| Frontend         | React 18 · TypeScript 5 · Vite 6 · Tailwind CSS 3 · Framer Motion 12                                                      |
| Editorial system | Fraunces Variable and Instrument Serif (display) · Instrument Sans (body) · JetBrains Mono (code) · self-hosted fonts     |

---

## Quality gates

The `governed-quality` workflow runs on pushes and pull requests to `governed`.
Its backend job runs the test suite and validates every shell script; its
frontend job runs the tests, type-check, lint, build and production dependency
audit. Copy compliance is not a separate CI step: `test_copy_compliance.py`
defines a test and is collected by `pytest -q` like any other. `git diff --check`
is a local habit rather than a gate.

Run the whole thing locally with:

```bash
cd pellier/backend
./.venv/bin/python -m pytest -q

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

The `e2e` workflow is a manual release gate for a newly provisioned Workshop
Studio deployment. It runs the storefront, operator, Observatory, persona,
streaming, reset, and Cognito checks against that real URL; it does not start
a simulated local data plane or claim to validate Aurora and AgentCore without
them.

---

## Repository layout

```
sample-pellier-agentic-search-apg/
├── .claude/
│   └── skills/                             Claude Code project workflows
├── CLAUDE.md                               Project and branch contract
├── WORKSHOP.md                             Teaching map and golden journeys
├── VOICE.md                                Pellier editorial voice contract
├── pellier/
│   ├── backend/                           FastAPI server, agents, services
│   │   ├── CLAUDE.md                        Backend and Lab 1 rules
│   │   ├── agents/                          Search Agent, Personalization Agent, Inventory Agent, ...
│   │   ├── services/                        Dispatcher, Operator graph, handoff, tools, AgentCore, database
│   │   ├── routes/                          FastAPI routers (agent, auth, commerce,
│   │   │                                    observatory, operator, products, search,
│   │   │                                    storefront, user, workshop)
│   │   └── app.py
│   └── frontend/                          React 18 + TS + Vite SPA
│       ├── CLAUDE.md                        Storefront and Pellier Observatory rules
│       └── src/
│           ├── components/                  PellierHero, ChatDrawer, ProductCard, ...
│           ├── operator/                    Client desk, concierge graph, reviews, actions
│           ├── shared/                      Cross-surface atoms – TraceChip, PresencePill
│           ├── observatory/                 Shopper and operator orchestration evidence
│           └── data/                        36 displayed product records + persona curation
│
├── workshop/                              Participant build surface: lab-2-rrf.sql,
│                                          lab-3-otel-contract.jq, lab-4-rls.sql,
│                                          starters/, architecture-diagrams/
├── policies/                              Cedar policy set applied to the policy engine
├── skills/                                Strands runtime skills (5) + scoped guidance
├── solutions/                             Reference implementations (drop-in escape hatches)
│   ├── waking-the-stock-keeper/             Lab 1 Inventory Agent reference
│   ├── closing-marcos-gap/                  Lab 1 check_inventory reference
│   ├── the-quiet-search/                    Lab 2 RRF reference
│   ├── the-ledger/                          Lab 3 forensic SQL + OTEL contract reference
│   ├── the-concierge/                       Lab 4 MCP and Gateway reference
│   └── retrieval-eval/                      Retrieval evaluation reference
│
└── scripts/
    ├── migrations/                         Ordered fresh-cluster SQL (001-049)
    ├── seed_pellier_catalog.py             60 story products + 940 retrieval distractors
    ├── seed_local_golden_journeys.py       Local Theo handoff + Jessica evidence rehearsal
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
