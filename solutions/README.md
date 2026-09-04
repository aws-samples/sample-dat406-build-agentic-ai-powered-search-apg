# Solutions — drop-in replacements

Copy a solution file over its runtime counterpart and the backend
auto-restarts. These are the reference implementations and "short on
time" escape hatches for the one-hour builders path on `main`.

```
solutions/
├── the-quiet-search/   → semantic search reference (observe-only)
├── closing-marcos-gap/ → floor_check body + Stock Keeper grant
└── the-ledger/         → AgentCore production references (observe-only)
```

---

## Workshop required path

**Two participant code edits and one required observation.** This is the
authoritative in-repo statement of the participant contract. It must agree
with `scripts/builders_starter.py`, which installs the gaps, and with the
Workshop Studio guide, which asks participants to close them.
`pellier/backend/tests/test_participant_contract.py` fails if this section
and the starter script disagree.

| Step | Guide section | File the participant edits | State after |
|---|---|---|---|
| 1 | Ground answers in live data | `pellier/backend/services/agent_tools.py` (the `floor_check` body) | tool `shipped`, agent `exercise` |
| 2 | Design the retrieval strategy | none — observation only | unchanged |
| 3 | Trace agent actions | `pellier/backend/agents/stock_keeper.py` (`INVENTORY_AGENT_TOOLS`) | both `shipped` |

Step 3 is a separate edit, not a restatement of step 1. Implementing a
capability and granting it to an agent are two different acts, and keeping
them apart is the lesson: a working tool the agent cannot select still
leaves Marco's answer ungrounded.

The `cp` commands below are the "short on time" escape hatches referenced
from each lab page.

### Step 1 (mandatory) — `floor_check` body

Replaces the stubbed `floor_check` tool body with the working
implementation that calls `BusinessLogic.floor_check()` against
`pellier.warehouse_inventory`.

```bash
cp solutions/closing-marcos-gap/services/agent_tools_floor_check_solution.py \
   pellier/backend/services/agent_tools.py
```

Paste-only option (just the 9-line body, between `START` / `END`
markers): `solutions/closing-marcos-gap/services/floor_check_tool_body.py`.

### Step 3 (mandatory) — grant `floor_check` to Stock Keeper

Adds `floor_check` to `INVENTORY_AGENT_TOOLS` inside the marked block in
`pellier/backend/agents/stock_keeper.py`. This is an agent-configuration
edit, not a code drop, so there is no file to copy. The scripted recovery
path is:

```bash
python3 scripts/builders_starter.py complete-agent
uv run scripts/builders_lab.py build-state --expect shipped
```

The proof is the durable receipt for the invocation the grant unlocks:

```bash
uv run scripts/builders_lab.py receipt
```

`receipt` is scoped to the last 30 minutes so a rehearsal row or a
neighbour's turn cannot satisfy it. Pass `--session <id>` to bind it to one
exact session instead.

### Optional fast-finisher A — Anna skill edit

The fast-finisher on the *Prove rerank* page asks attendees to change
one guidance line in `skills/the-gift-table/SKILL.md` and prove the
edit landed with SQL against `pellier.tool_audit`. **There is no
solution file** — the change is a single rule in the skill markdown,
and the proof is a `SELECT`, not a code drop.

### Optional fast-finisher B — `logger.info` observability hook

Adds one `logger.info("agentcore.invoke ...")` line to
`run_agent_on_runtime()` so every managed `InvokeRuntime` call shows up
in `uvicorn.log`.

```bash
cp solutions/the-ledger/services/agentcore_runtime_with_invoke_log.py \
   pellier/backend/services/agentcore_runtime.py
```

---

## What bootstrap pre-applies (reference)

The workshop image ships with everything **already wired except** the
two gaps in the table above — the `floor_check` tool body and the Stock
Keeper grant. At
provision time `scripts/bootstrap-labs.sh` (the `WORKSHOP_FORMAT=builders`
block) copies the reference files below into place. This list mirrors the
actual `copy_solution` calls in that script — it is for transparency and
manual recovery, not an in-room step. (Keep it in sync if you add a
pre-apply.)

Dispatcher + specialists (the agents Marco's turns 2/5 use) — note Stock
Keeper is **not** copied here; it ships live in the repo:

```bash
cp solutions/closing-marcos-gap/agents/curator.py          pellier/backend/agents/curator.py
cp solutions/closing-marcos-gap/agents/experience_guide.py pellier/backend/agents/experience_guide.py
cp solutions/closing-marcos-gap/agents/orchestrator.py     pellier/backend/agents/orchestrator.py
```

The builders variant of `agent_tools.py` — wires everything Stock
Keeper-adjacent (`restock_shelf`, `running_low`) **except** the
`floor_check` body, which participants add in step 1:

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
# Policy is managed by the pinned AgentCore CLI project. The backend ships
# services/managed_policy.py in-tree as a read-only inspection adapter.
cp solutions/the-ledger/services/agentcore_identity.py       pellier/backend/services/agentcore_identity.py
cp solutions/the-ledger/services/cognito_auth.py             pellier/backend/services/cognito_auth.py
cp solutions/the-ledger/services/otel_trace_extractor.py     pellier/backend/services/otel_trace_extractor.py
cp solutions/the-ledger/frontend/agentIdentity.ts            pellier/frontend/src/utils/agentIdentity.ts
```

The `the-quiet-search/` retrieval references (`hybrid_search.py`,
`business_logic.py`, `hybrid_search_with_rerank.py`) and the
`the-concierge/` MCP references are **observe-only** — bootstrap does not
copy them, because those files already ship live in the repo. They are
here as readable reference implementations for the Act I rerank
comparison and the Act III MCP read.

The files participants change in-room are the `floor_check` body in
`pellier/backend/services/agent_tools.py` (step 1, with the
`agent_tools_floor_check_solution.py` escape hatch above) and the
`INVENTORY_AGENT_TOOLS` grant in `pellier/backend/agents/stock_keeper.py`
(step 3, with the `complete-agent` recovery command above).
