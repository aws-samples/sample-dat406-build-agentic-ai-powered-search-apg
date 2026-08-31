# Pellier L400 Workshop — Co-Speaker Brief

This is the single internal briefing to share with co-presenters. It describes
the story we tell, the four required participant labs, the proof boundaries, the
suggested handoffs, and how the governed application is delivered to Workshop
Studio. It is not the participant manual: Workshop Studio owns copy-paste
commands, screenshots, and minute-by-minute recovery instructions.

## The session in one paragraph

Pellier is a governed agentic retail application built on a curated workshop
dataset in a live Aurora PostgreSQL environment. A shopper asks for help; a
Strands dispatcher routes the request to a bounded specialist; typed tools and
PostgreSQL establish what is true; and durable records show what actually ran.
For consequential service actions, an Operator investigates a persisted
proposal, a human confirms or declines its exact terms, AgentCore Policy
authorizes the request, and Aurora still independently enforces ownership,
constraints, and idempotency. The workshop's argument is simple: a plausible
model response is never enough. We need grounding, authorization, data
enforcement, and evidence that can be reconstructed later.

## What participants leave with

- A practical pattern for grounding agent answers in a system of record.
- A way to compare semantic, lexical, hybrid, reranked, and agentic retrieval
  without treating relevance as eligibility.
- A working mental model for AgentCore Runtime, Gateway, Memory, and traces.
- A precise governance model: human decision, policy decision, database result,
  and evidence are separate facts that can disagree.

## The four-lab arc

The official Workshop Studio title and sequence are canonical.

| Time | Lab | Story and participant outcome | What counts as proof |
|---|---|---|---|
| 0–8 | Introduction | Open Code Editor and Pellier; confirm the two Lab 1 build markers are still exercises. | The starting state is visible and reproducible. |
| 8–30 | **01 GROUND THE ANSWER — Live Data and Evidence** | Marco asks whether the Hadley shirt is available in Brooklyn and can still ship in time. Participants complete the typed `check_inventory` path. | Marco's answer, the Aurora inventory row, the tool trace, and the correlated `pellier.tool_audit` row agree. |
| 30–45 | **02 MEASURE HYBRID RETRIEVAL — Search, Filters, and Trade-offs** | Anna needs an in-stock housewarming gift under $100. Participants compare vector-only, hybrid RRF, hybrid plus rerank, and agentic retrieval. | A defensible quality/latency/cost choice plus SQL showing that PostgreSQL enforced price and stock eligibility. |
| 45–70 | **03 OPERATE THE MANAGED AGENT PATH — Runtime, Gateway, Memory, and Trace** | Operate the pre-provisioned Dispatcher through AgentCore and reconstruct the Marco-for-Theo identity mismatch. | Authenticated Gateway tool list, Runtime receipt with `rail=gateway-mcp`, active managed Memory, fresh-process recall, and a correlated agent/model/tool trace. |
| 70–95 | **04 GOVERN AND PROVE ACTIONS — Human Decision, Policy, Database, and Receipts** | Bind JWT identity to the requested customer id. Marco-for-Theo is denied; Theo-for-Theo is allowed; Aurora scopes the same data independently. | Cedar `DENY` plus verified non-execution, Cedar `ALLOW` plus linked execution evidence, scoped RLS reads, and participant-policy reset. |
| 95–110 | Recovery buffer | Finish a required checkpoint or reset a table. | Every table leaves the managed policy and data state clean. |
| 110–120 | Close | Transfer the boundaries to the audience's own architecture. | Participants can name the owner of each fact, decision, effect, and receipt. |

### The one sentence for each lab

1. **Ground the answer:** “The database establishes what is true, and the audit
   row establishes that the read happened.”
2. **Measure hybrid retrieval:** “The model can propose constraints; PostgreSQL
   must enforce them.”
3. **Operate the managed path:** “A managed runtime changes the execution
   envelope, not the proof standard.”
4. **Govern and prove actions:** “An allowed action is not necessarily an
   executed action, and a human confirmation is not an authorization.”

## The architecture story to keep straight

```text
Shopper request
  -> Storefront Dispatcher
  -> one bounded specialist
  -> typed Aurora-backed tool or retrieval path
  -> streamed response + tool evidence

Consequential request
  -> immutable shopper handoff + pending review
  -> Operator Concierge graph:
       Case Investigator -> Resolution Planner
  -> persisted bounded recommendation
  -> later human confirmation or decline
  -> later Gateway + AgentCore Policy request
  -> Aurora enforcement
  -> durable receipts and reconstruction
```

There are deliberately **two Strands patterns**, not one shared agent:

- **Storefront Dispatcher:** one specialist owns a shopper turn. It is the
  required AgentCore Runtime proof in Lab 3.
- **Operator Concierge graph:** investigation and resolution planning are
  separate responsibilities. The graph persists an operator-safe result; it
  does not create a review, wait for a human, authorize a write, or mutate
  business state.

The human checkpoint is a durable, later request. It preserves the exact action
terms across restarts and ensures that “the agent proposed it” never becomes
“the system did it.”

## The proof model

Use this distinction consistently. It is the intellectual center of the
workshop.

| Fact | Owner | What it does **not** prove |
|---|---|---|
| A model or graph proposed an action | Application workflow | That a person agreed, policy allowed it, or data changed |
| A person confirmed exact terms | Operator review | That the Gateway invocation ran or Aurora accepted it |
| AgentCore Policy returned `ALLOW` | Policy receipt | That a tool or database statement executed |
| AgentCore Policy returned `DENY` | Policy receipt + named attempt | A database refusal; verify non-execution evidence separately |
| Aurora refused a statement | Database result | “Not reached” — the tool reached Aurora and its guard rejected it |
| `tool_audit`, `execution_receipts`, and domain/write rows exist | Durable evidence | That every preceding layer made the same decision |

The participant path queries three evidence classes:

- **Policy receipt:** `pellier.governed_receipts` answers whether the action was
  permitted.
- **Execution evidence:** `pellier.tool_audit` shows what reached the
  application/tool boundary; `pellier.execution_receipts` preserves attempts
  across the operator path, including an Aurora refusal.
- **Data evidence:** `pellier.write_operations`, domain rows, and
  `inventory_ledger` show what reached the system of record and what durable
  state resulted.

## Surface roles and demo choices

| Surface | Role in the workshop | Presenter guidance |
|---|---|---|
| **Pellier storefront** | Primary retail experience for Marco, Anna, and Theo. | Start here. It makes the technical boundaries feel like customer outcomes. |
| **Code Editor + terminal** | Canonical proof surface. | Use it for all required build, curl, SQL, policy, and reset evidence. |
| **Pellier Observatory** | Optional visual lens over a live shopper run. | Open it when it helps the room read routing, tool calls, SQL receipts, or the grounded answer. Do not make it another required app at minute zero. |
| **Pellier Operator** | Separate human clienteling and service-recovery surface. | Use it for the optional human-in-the-loop close, not as a substitute for the Lab 4 Gateway evidence. |

### The optional Operator close

If time allows after Lab 4, use **Theo** or **Jessica** to make the human
boundary tangible:

- **Theo:** the storefront request becomes an immutable handoff and a pending
  review. Operator Concierge investigates, then prepares a bounded plan. A
  signed-in operator confirms the exact action; a separate request executes it.
- **Jessica:** a support ticket says a return was received, while the returns
  ledger has no row. The correct outcome is investigation and reconciliation,
  not an invented completed return. The participant supplies missing material
  terms before any proposal can be prepared.

Say explicitly: support narrative is context, not system-of-record fact.

## Suggested speaker handoffs

Assign names to these roles in the pre-brief; the handoffs are intentionally
content-based rather than person-based.

| Speaker role | Owns | Handoff line |
|---|---|---|
| **Narrative lead** | Opening, Marco, Anna, and the product story. | “We have shown what is true and how results become eligible. Now let’s move the same dispatcher into the managed execution path.” |
| **Platform lead** | Lab 3, Runtime, Gateway, Memory, and traces. | “Runtime proves how the request travelled. It does not by itself decide whether a sensitive action should happen.” |
| **Governance lead** | Lab 4, RLS, receipts, and the Operator close. | “Now we will make the identity mismatch fail twice: first at policy, then independently at the database boundary.” |
| **Table/facilitation lead** | Timebox, recoveries, and reset. | “Record an unavailable managed checkpoint as unproven; do not convert it into a claimed pass. Preserve time for the reset.” |

## Claims to make — and claims to avoid

### Say

- “This is a live, provisioned workshop environment with a curated retail
  dataset and real Aurora/AgentCore integrations on the required managed path.”
- “Local PostgreSQL rehearsal proves application behavior and fixture shape; it
  does not prove Aurora, AgentCore Runtime, Gateway, Memory, Cedar, or deployed
  RLS.”
- “Observatory is a visual view of evidence; Code Editor, curl, and SQL are the
  required source of proof.”
- “The operator desk is protected by the `pellier-operators` Cognito-group
  boundary. Its API authorization and Cedar action authorization are different
  controls.”
- “A missing execution row is meaningful only when paired with a policy receipt
  naming the denied attempt.”

### Do not say

- “One agent works both channels.” Storefront Dispatcher and Operator Concierge
  use different Strands patterns for different jobs.
- “Reranking enforces the budget or inventory rule.” It changes ordering;
  PostgreSQL enforces eligibility.
- “Policy allowed it, so it happened.” `ALLOW` is not a database receipt.
- “Aurora was not reached” when Aurora rejected a guard or constraint. That is
  an attempted execution with a database refusal.
- “The graph executes the action.” It investigates and plans; human decision,
  authorization, execution, and data enforcement happen later.

## Delivery and release contract

The governed source and Workshop Studio are different products with a strict
handoff:

1. Commit and push application changes on the `governed` branch.
2. Update the exact immutable SHA in Workshop Studio using
   `python3 scripts/set_source_revision.py <full-sha>`. It updates the
   `RepoRevision` values in `contentspec.yaml`, `static/pellier-builders.yml`,
   and `assets/pellier-code-editor.yml`.
3. Commit/publish the Workshop Studio content and asset changes through its own
   repository workflow and asset synchronization.
4. A fresh Workshop Studio environment clones that pinned SHA, verifies it
   before bootstrap, exports `WORKSHOP_SOURCE_REVISION`, writes
   `.workshop-ref.json`, and must pass `scripts/health-gate.sh`.
5. Complete a fresh-account rehearsal before claiming an end-to-end release.

Git operations and S3 synchronization in Workshop Studio publish the guide and
assets. They do **not** update the Pellier application unless the immutable
source pin changes too. A repair on one workshop box is never a product fix.

## Pre-session checklist

- Confirm the Studio pin matches the intended pushed `governed` commit.
- Verify the environment exposes only **CodeEditorURL** and **PellierURL** to
  participants; Observatory remains an optional in-app link.
- Require the health gate to report `READY` before the room starts.
- Confirm the Lab 1 markers start at `exercise`.
- Confirm the Operator account is available for the optional close; do not
  distribute it as a shopper identity.
- Keep the Lab 4 participant Cedar reset and the global workshop reset in the
  room plan.
- Capture managed proof as it happens: Runtime receipt, Gateway rail, Memory
  read, trace, policy decision, execution evidence, and database result.

## Authoritative references

| Need | Source |
|---|---|
| Participant instructions, commands, screenshots, and timing | Governed Workshop Studio `content/00-*` through `content/40-*` |
| Workshop/source publication boundary | `docs/HANDOFF-SOURCE-CONTRACT.md` |
| Machine-readable golden journeys | `pellier/backend/tests/golden/journeys.json` |
| Golden journey tests | `pellier/backend/tests/test_golden_journeys.py` |
| Operator graph | `pellier/backend/services/operator_graph.py` |
| Operator review lifecycle | `pellier/backend/services/operator_concierge.py` and `operator_concierge_sessions.py` |
| Cross-surface reconstruction | `pellier/backend/routes/observatory.py` and `OperatorLineage.tsx` |
| Readiness gate | `scripts/health-gate.sh` |

The workshop succeeds when participants can explain not only what an agent
answered, but which layer supplied each fact, decision, effect, and receipt.
