# Solutions - drop-in replacements

Copy a solution file over its runtime counterpart and the backend
auto-restarts. These are the reference implementations and "short on
time" escape hatches for the governed workshop path.

```
solutions/
├── waking-the-stock-keeper/ → Stock Keeper definition scaffold solution
├── closing-marcos-gap/      → floor_check + Stock Keeper tool solution
├── the-quiet-search/        → retrieval references + HNSW rebuild SQL
├── the-ledger/              → AgentCore production + audit ledger
└── the-concierge/           → Gateway/MCP and Cedar rule references
```

---

## Workshop required path

**Two Act I code checkpoints, one skill edit, one retrieval/index proof,
two SQL proofs, and one Cedar policy exercise.** The commands below are the
"short on time" escape hatches referenced from each lab page.

### Exercise 1A - Wake Stock Keeper: Stock Keeper definition (Act I)

Replaces the governed starter scaffold in `stock_keeper.py` with the
working Stock Keeper definition. It leaves `floor_check` stubbed so the
midpoint still proves the tool layer separately.

```bash
cp solutions/waking-the-stock-keeper/agents/stock_keeper_solution.py \
   pellier/backend/agents/stock_keeper.py
```

### Exercise 1B - Wake Stock Keeper: `floor_check` body (Act I)

Replaces the stubbed `floor_check` tool body with the working
implementation that calls `BusinessLogic.floor_check()` against
`pellier.warehouse_inventory`.

```bash
cp solutions/closing-marcos-gap/services/agent_tools_floor_check_solution.py \
   pellier/backend/services/agent_tools.py
```

Paste-only option (just the 9-line body, between `START` / `END`
markers): `solutions/closing-marcos-gap/services/floor_check_tool_body.py`.

### Exercise 2 - Shape the Packing List (Act I)

This exercise edits `skills/the-packing-list/SKILL.md` and then replays
Marco's Boutique turn. There is no solution file to copy: the lab has the
participant back up the file first, add one markdown bullet, and restore it
from `/tmp/the-packing-list.before` or `git restore` if needed.

### Exercise 3 - Run the Search Lab: HNSW index rebuild (Act I)

After participants drop `pellier.product_catalog_embedding_hnsw`, this
reference rebuilds the exact provisioned pgvector HNSW index and refreshes
planner statistics.

```bash
psql -f solutions/the-quiet-search/sql/hnsw_index_lab.sql
```

### Exercise 4 - Query the Ledger (Act II)

Generate a tool call, then **author** three queries that interrogate the
Aurora ledger, building in difficulty: the raw row (`SELECT`), JSONB
extraction (`->>` pulls `reason`/`return_id` out as columns), and
rail-label reasoning. In the governed format, an allowed managed write records
`caller='gateway'`; a Cedar DENY stops before a row exists. The builders format
retains the in-process `caller='agent'` path. This is SQL the participant
writes, not a code drop. The reference recap is a canned query a facilitator
can run live:

```bash
psql -f solutions/the-ledger/sql/tool_audit_recap.sql
```

Bare `psql` picks up the `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` /
`PGDATABASE` variables bootstrap already exports, so no connection string
is needed. It prints the most recent allowed `process_return` session, the
raw rows, and a JSONB-extracted view; pass an optional customer override
with `-v customer=<customer_id>` (e.g. `-v customer=theo`).

### Exercise 5 - Investigate the Incident (Act II)

Reconstructs the seeded governed incident: Marco is the authenticated
principal, but the tool arguments processed a return for Theo. The SQL
joins `pellier.governed_receipts`, `pellier.tool_audit`,
`pellier.customers`, `pellier.product_catalog`, and `pellier.orders`.

```bash
psql -f solutions/the-ledger/sql/forensic_incident.sql
```

### Exercise 6 - Add a Policy Rule (Act III)

The lab has participants edit `policies/workshop_final_sale_forbid.cedar`,
validate it, and apply it with `scripts/deploy/workshop_policy_rule.py`.
The reference Cedar shape is here for facilitator recovery:

```bash
cat solutions/the-concierge/policies/final_sale_forbid.cedar
cp solutions/the-concierge/policies/final_sale_forbid.cedar \
   policies/workshop_final_sale_forbid.cedar
python3 scripts/deploy/workshop_policy_rule.py \
  --cedar-file policies/workshop_final_sale_forbid.cedar \
  validate
python3 scripts/deploy/workshop_policy_rule.py \
  --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
  --gateway-arn "$AGENTCORE_GATEWAY_ARN" \
  --cedar-file policies/workshop_final_sale_forbid.cedar \
  apply
python3 scripts/deploy/workshop_policy_rule.py \
  --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
  reset
```

### Optional rail - identity-aware Cedar (Act III)

Apply the second participant policy that compares the Cognito `username`
claim to `context.input.customer_id`.

```bash
cat solutions/the-concierge/policies/identity_match_forbid.cedar
cp solutions/the-concierge/policies/identity_match_forbid.cedar \
   policies/workshop_identity_match_forbid.cedar
python3 scripts/deploy/workshop_policy_rule.py --rule identity_match \
  --cedar-file policies/workshop_identity_match_forbid.cedar \
  validate
python3 scripts/deploy/workshop_policy_rule.py --rule identity_match \
  --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
  --gateway-arn "$AGENTCORE_GATEWAY_ARN" \
  --cedar-file policies/workshop_identity_match_forbid.cedar \
  apply
```

### Optional rail - LOG_ONLY then ENFORCE (Act III)

Flip the whole Gateway attachment to LOG_ONLY, run the proof call, then flip
back to ENFORCE.

```bash
python3 scripts/deploy/workshop_policy_rule.py mode --set LOG_ONLY \
  --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
  --gateway-arn "$AGENTCORE_GATEWAY_ARN"
python3 scripts/deploy/workshop_policy_rule.py mode --set ENFORCE \
  --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
  --gateway-arn "$AGENTCORE_GATEWAY_ARN"
```

### Optional rail - Postgres RLS (Act II)

The RLS rail is opt-in and resettable. It creates `pellier_agent_rls`, binds
one policy to `pellier.returns`, then proves Aurora refuses a cross-customer
write inside the database engine.

```bash
psql -f solutions/the-ledger/sql/rls_rail_setup.sql
psql -f solutions/the-ledger/sql/rls_rail_reset.sql
```

### Managed Runtime invocation log (Act II)

The canonical `services/agentcore_runtime.py` already emits a token-safe
`agentcore.invoke` record with session, user, prompt length, and Runtime id.
No solution-file replacement is required.

---

## What bootstrap pre-applies (reference)

The builder-session image ships with everything **already wired except**
the `floor_check` tool body. The governed two-hour branch deliberately
keeps the Stock Keeper definition scaffolded too. At provision time
`scripts/bootstrap-labs.sh` (the `WORKSHOP_FORMAT=builders` block) copies
the reference files below into place for the one-hour builder flow. This
list mirrors the actual `copy_solution` calls in that script – it is for
transparency and manual recovery, not an in-room step. (Keep it in sync if
you add a pre-apply.)

Dispatcher + specialists (the agents Marco's turns 2/5 use) – note Stock
Keeper is **not** copied here; it ships live in the repo:

```bash
cp solutions/closing-marcos-gap/agents/curator.py          pellier/backend/agents/curator.py
cp solutions/closing-marcos-gap/agents/experience_guide.py pellier/backend/agents/experience_guide.py
cp solutions/closing-marcos-gap/agents/orchestrator.py     pellier/backend/agents/orchestrator.py
```

The builders variant of `agent_tools.py` – wires everything Stock
Keeper-adjacent (`restock_shelf`, `running_low`) **except** the
`floor_check` body, which participants add in Exercise 1:

```bash
cp solutions/closing-marcos-gap/services/agent_tools_builders_preapply.py \
   pellier/backend/services/agent_tools.py
```

AgentCore production services (Runtime, Memory, Gateway, identity, auth,
OTEL) plus the frontend identity hook:

```bash
cp solutions/the-ledger/services/agentcore_runtime.py        pellier/backend/services/agentcore_runtime.py
cp solutions/the-ledger/services/agentcore_memory.py         pellier/backend/services/agentcore_memory.py
cp solutions/the-ledger/services/agentcore_gateway.py        pellier/backend/services/agentcore_gateway.py
# Policy is managed (Cedar at the Gateway, provisioned by scripts/deploy/deploy_policy.py).
# The backend ships services/managed_policy.py in-tree – there is no local policy file to copy.
cp solutions/the-ledger/services/agentcore_identity.py       pellier/backend/services/agentcore_identity.py
cp solutions/the-ledger/services/cognito_auth.py             pellier/backend/services/cognito_auth.py
cp solutions/the-ledger/services/otel_trace_extractor.py     pellier/backend/services/otel_trace_extractor.py
cp solutions/the-ledger/frontend/agentIdentity.ts            pellier/frontend/src/utils/agentIdentity.ts
```

The `the-quiet-search/` retrieval references (`hybrid_search.py`,
`business_logic.py`, `hybrid_search_with_rerank.py`) and the
`the-concierge/` MCP references are **observe-only** – bootstrap does not
copy them, because those files already ship live in the repo. They are
here as readable reference implementations for the Act I rerank
comparison and the Act III MCP read.

In the governed branch, participants complete the Stock Keeper definition,
wire the `floor_check` body, and rebuild the HNSW index by hand.
