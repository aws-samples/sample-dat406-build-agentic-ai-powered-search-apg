# Pellier Governed Agentic AI Search Workshop

This document is the shared teaching map for the governed Pellier workshop. It
explains the retail story, the participant path, the golden journeys, and what
counts as proof. Workshop Studio remains the source for copy-paste commands and
timing.

## Session promise

Participants build and operate a retail agent system in four moves:

1. connect an agent to live PostgreSQL data;
2. evaluate semantic, lexical, hybrid, and reranked retrieval;
3. run the storefront dispatcher through Amazon Bedrock AgentCore Runtime,
   Gateway, and Memory; and
4. authorize a sensitive action with Cedar, then prove the policy and database
   outcomes independently.

The workshop is not a tour of features. Its production pattern is:

```text
customer intent
  -> verified identity
  -> grounded evidence
  -> bounded proposal
  -> human decision when required
  -> policy authorization
  -> database enforcement
  -> durable evidence
  -> customer outcome
```

No one layer answers every question. A model may propose an action. A person may
confirm its exact terms. AgentCore Policy may authorize it. Aurora may still
refuse it. Receipts must show which of those events occurred.

## Delivery contract

This governed repository is delivered to Workshop Studio as an immutable source
revision, not as a mutable working copy:

1. commit and push the application changes on `governed`;
2. update the Workshop Studio launch template's pinned Pellier repository
   revision (`RepoRevision`, or the equivalent source pin owned by that repo);
3. deploy a fresh environment from that pin; and
4. verify `.workshop-ref.json`, `WORKSHOP_SOURCE_REVISION`, and the health gate
   before treating the environment as current.

Workshop Studio owns its lab guide, CloudFormation launch wiring, screenshots,
and static workshop assets. Git operations and S3 asset synchronization in that
repository publish those materials; they do not update the Pellier application
unless the pinned source revision also changes. On the event path, UserData
clones this repository at the pinned SHA and the bootstrap removes `.git`, so a
manual edit or pull on one workshop box is neither the delivery mechanism nor a
product fix.

## The retail world

Pellier has two connected operating surfaces and one shared proof surface:

- **Pellier storefront** is where shoppers discover products, ask questions,
  and request service.
- **Pellier Operator** is where an authorized employee inspects client context,
  reviews consequential proposals, and reconstructs outcomes.
- **Pellier Observatory** is where builders run the production shopper path,
  inspect emitted evidence, and reconstruct the Storefront-to-Operator lineage.
  It does not introduce a third orchestration rail.

Three returning shoppers remain the storefront heroes:

| Persona | Retail need | Workshop lesson |
|---|---|---|
| Marco | Linen, travel, and local availability | A stock claim needs a live inventory read |
| Anna | A constrained gift search | Models propose filters; PostgreSQL enforces eligibility |
| Theo | A damaged product return | Proposal, confirmation, authorization, execution, and evidence are different events |

Jessica and the other operator clients extend the world without turning the
storefront into an identity switcher:

- A hero handoff performs a real Marco, Anna, or Theo persona switch.
- A nonhero handoff opens an authenticated, read-only client preview.
- Opening a client preview clears any active shopper persona first.
- A client preview never grants shopper identity and never enables a write.

Jessica is the evidence-integrity journey. Her support ticket says a return was
received, while the authoritative returns ledger has no row. The correct
first outcome is reconciliation, not an invented completed return. Only after
that investigation may the participant choose an exact order item and reason to
prepare a separate review; the graph never infers those material terms from the
ticket.

## The closed-loop architecture

Pellier uses two Strands orchestration patterns because the two surfaces have
different jobs:

```text
Storefront Dispatcher
  -> one specialist owns the shopper turn
  -> immutable shopper handoff + pending PostgreSQL review

Operator Concierge Strands Graph
  -> Case Investigator Agent
  -> Resolution Planner Agent
  -> persisted operator-safe graph artifact

separate authenticated request
  -> human confirms or declines the exact action hash

separate deterministic execution request
  -> AgentCore Gateway + Policy
  -> PostgreSQL enforcement and receipts
  -> Observatory reconstruction
```

The Storefront favors a fast, deterministic handoff to one specialist. The
Operator Concierge earns a graph because investigation and resolution planning
are different model responsibilities with an explicit dependency.

The graph does not create the review, wait for a person, authorize a write, or
mutate business state. The pending review exists first. The graph reads current
PostgreSQL evidence plus explicitly untrusted shopper context, then persists its
bounded result. A later request records the human decision, and another request
runs the confirmed action from the persisted proposal. This keeps every Runtime
invocation finite and makes the human checkpoint durable across restarts.

Local development runs the graph under application orchestration. Amazon Bedrock
AgentCore Runtime is the deployment target. The Storefront Dispatcher is the
required managed Runtime proof in Lab 3; the operator graph is the production
architecture participants inspect and transfer.

### Why there are 60 products and 1,000 rows

Both numbers are intentional:

- **60 story products** are the stable participant-facing domain used by
  storefront grids, orders, inventory, and policy exercises.
- **1,000 catalog rows** form the retrieval corpus. High-ID archive distractors
  create enough near misses to compare retrieval strategies.

The additional rows are retrieval test material, not 940 more products for a
participant to learn. This workshop does not use the corpus as an HNSW scale
benchmark.

## The proof contract

Every golden journey uses the same nine stages:

| Stage | Question | Primary owner |
|---|---|---|
| Intent | What did the person actually ask for? | Storefront or operator request |
| Identity | Who is acting, and which customer is the business subject? | Cognito and server mapping |
| Grounding | Which system-of-record facts support the response? | PostgreSQL tools |
| Proposal | What exact action and material parameters are prepared? | Application workflow |
| Human decision | Did a person approve those exact terms? | Operator review |
| Authorization | May this principal invoke this action? | AgentCore Policy |
| Data enforcement | May the statement read or write these rows? | Aurora roles, RLS, and constraints |
| Durable evidence | What proves the attempt and its result? | Receipts, audit rows, and correlation ids |
| Customer outcome | What can the system now truthfully tell the customer? | Response built from actual results |

Read journeys do not fabricate proposal, approval, or policy stages. A local
fixture may prove source behavior and PostgreSQL state, but it may not claim a
managed AgentCore verdict.

## Required participant path

The current Workshop Studio titles are canonical. The shorter descriptions in
the second column state the participant outcome in plain language.

| Lab | Participant outcome | Anchor journey |
|---|---|---|
| **01 GROUND: Ground Answers in Live Data** | Connect an agent to live data | Marco checks Brooklyn inventory |
| **02 RETRIEVE: Measure Hybrid Retrieval Trade-offs** | Evaluate hybrid search | Anna finds an eligible gift |
| **03 OPERATE: Operate the Managed Agent Path** | Run agents on AgentCore | Marco uses Runtime, Gateway, and Memory; Theo exposes an identity gap |
| **04 GOVERN & PROVE: Govern Actions and Prove Outcomes** | Authorize agent actions and prove outcomes | Marco-for-Theo is denied; Theo-for-Theo is allowed |

### Lab 1: Marco connects an agent to live data

Participant flow:

1. Sign in as Marco and ask:

   ```text
   Is the Hadley shirt at the Brooklyn warehouse, and can it still ship in time?
   ```

2. Observe the honest pre-build response. The dispatcher reaches Inventory
   Agent, but the unfinished tool does not invent stock.
3. Query `warehouse_inventory`, `warehouses`, and `product_catalog` with SQL.
   Aurora already contains the quantity and shipping window.
4. Complete only the two marked regions in:
   - `pellier/backend/agents/inventory_agent.py`
   - `pellier/backend/services/agent_tools.py`
5. Check `/api/observatory/build-state`; both Inventory Agent and
   `check_inventory` must report `shipped`.
6. Replay Marco's question and inspect `tool.check_inventory`.
7. send a uniquely keyed turn and query `pellier.tool_audit` for the same
   session id.

Completion proof:

```text
live inventory answer
  + check_inventory tool trace
  + correlated tool_audit row
```

Pattern taught: an answer is grounded only when a system-of-record read and
evidence of that read agree.

### Lab 2: Anna evaluates hybrid search

Participant flow:

1. Switch to Anna and use the milestone-gift prompt.
2. Confirm the `gift-table` skill and `search_products_hybrid` tool were used.
3. Run one comparison across:
   - pgvector semantic retrieval;
   - PostgreSQL full-text retrieval plus reciprocal rank fusion;
   - hybrid retrieval plus Cohere Rerank; and
   - agent-proposed filters plus retrieval and reranking.
4. Compare top results, one-run observed latency, and modeled cost.
5. Carry the exact vector-only and agentic product ids into SQL.
6. Inspect whether each candidate satisfies `price <= 100` and `quantity > 0`,
   and whether the agentic path kept it.
7. State which strategy should serve this query class and when its extra cost
   is not justified.

Completion proof:

```text
retrieval result sets
  + measured latency and modeled cost
  + SQL eligibility result
  + one defensible strategy decision
```

Pattern taught: a model can extract a constraint, but a deterministic predicate
must enforce it. Reranking is ordering, not authorization or eligibility.

### Lab 3: Operate the managed AgentCore path

Participant flow:

1. Mint Marco's Cognito token and enumerate the 15 workshop-published Gateway
   MCP tools.
2. Invoke the dispatcher in AgentCore Runtime and require
   `rail=gateway-mcp`.
3. Confirm AgentCore Memory is live, active, and SDK-backed.
4. Send one turn containing destination, duration, and fabric, then omit all
   three facts from turn two.
5. Read turn one from a separate process and confirm turn two recalls it.
6. Inspect a unified trace containing correlated agent, model, and tool spans.
7. Query the seeded forensic incident where Marco's authenticated principal
   invoked a return whose arguments named Theo.
8. Explain separately what the policy receipt and `tool_audit` row prove.
9. Run Theo's damaged-return request and inspect the immutable shopper handoff,
   pending review, action fingerprint, and untrusted-context label in SQL.

Completion proof:

```text
Runtime receipt on gateway-mcp
  + authenticated Gateway tool list
  + fresh-process Memory read
  + recalled context
  + correlated agent/model/tool trace
  + SQL reconstruction
```

Pattern taught: moving an agent into a managed runtime changes the execution
envelope, not the evidence standard.

If Runtime, Gateway, Memory, or trace delivery is unavailable, mark that
checkpoint **unproven**. The SQL reconstruction preserves the room path but is
not a substitute for managed proof.

### Lab 4: Authorize the action and prove the outcome

Participant flow:

1. Complete the Cedar rule that binds Cognito usernames to Aurora customer ids.
2. Add, validate, and deploy the rule with the AgentCore CLI.
3. Invoke Theo's return with Marco's token.
4. Require `DENY`, no linked execution row, and
   `absence_verified=true`.
5. Repeat the same invocation with Theo's token.
6. Require `ALLOW` and a linked `tool_audit` row.
7. Run the same order query as the table owner, as Theo's scoped runtime role,
   and as Anna's scoped runtime role.
8. Confirm Theo sees his row and Anna does not.
9. Remove the participant policy and deploy the reset before leaving the lab.

Completion proof:

```text
mismatch policy receipt: DENY + verified non-execution
  + matching policy receipt: ALLOW + linked execution
  + scoped Aurora reads: owner / Theo / Anna
  + participant policy reset
```

Pattern taught: policy authorization and database authorization are independent.
An `ALLOW` does not prove execution. A `DENY` needs a named attempt plus
verified absence of execution.

## Golden retail journeys

The required labs teach the mechanisms. These golden journeys keep the
mechanisms attached to realistic customer outcomes.

### Guest: useful discovery without invented identity

1. Enter the storefront signed out.
2. Ask for a thoughtful gift for someone who runs.
3. Retrieve from the curated catalog without assigning a customer id.
4. Return a grounded shortlist and retain a turn id.

Safe boundary: no customer profile, consequential proposal, or policy verdict
is inferred for an anonymous visitor.

### Marco: grounded availability

1. Discover travel-ready linen pieces.
2. Ask for Brooklyn availability and a shipping window.
3. Route the location-specific question to `check_inventory`.
4. Read warehouse quantity and shipping fields from PostgreSQL.
5. Link the shopper answer to its tool evidence by turn id.

Safe boundary: product similarity cannot stand in for stock.

### Anna: constrained gift retrieval

1. Ask for a housewarming gift under $100 that is in stock.
2. Extract the price and stock constraints.
3. Compare lexical, semantic, hybrid, and reranked candidates.
4. Apply price and stock predicates before final ranking.
5. Return only eligible products with an explainable strategy choice.

Safe boundary: an attractive but ineligible result is still wrong.

### Theo: governed damaged-return loop

1. Theo asks to return his chipped Wabi-Sabi Bowl.
2. The service path reads return policy and proves order ownership.
3. Pellier prepares `initiate_return` with exact customer, product, and reason.
4. The same terminal shopper receipt stores an immutable, explicitly untrusted
   handoff linked to the pending review.
5. A canonical hash binds those material parameters in one pending review.
6. Operator Concierge runs Case Investigator, then Resolution Planner, and
   persists the graph artifact without changing the review.
7. An authenticated member of `pellier-operators` reviews the proposal.
8. Confirmation records human agreement in a later request; it does not execute
   the action.
9. A separate managed execution request carries only the persisted proposal
   through Gateway and AgentCore Policy.
10. Aurora independently applies ownership, RLS, constraints, and idempotency.
11. Observatory reconstructs the handoff, graph nodes, human decision, policy
    receipt, execution evidence, domain row, and episodic outcome.

Important layer boundary: the API operator group authorizes access to the desk.
The current Cedar baseline authorizes published action semantics; it does not
recheck operator-group membership. Do not claim the two layers enforce the
same condition.

### Jessica: reconcile conflicting evidence

1. Open Jessica's operator client record.
2. Start a fresh guided Concierge investigation rather than replaying a prior
   completed session.
3. Watch the observable operations arrive progressively: client record, order
   history, service context, return records, and the bounded Strands graph.
4. Keep the operator identity and Jessica customer subject distinct.
5. Label the ticket as context, zero return rows as fact, and reconciliation as
   the next inference.
6. Complete the investigation without preparing an action or making a
   completed-return claim.
7. At the explicit human checkpoint, choose the disputed order item and reason.
   Those material terms come from the participant, not from model inference.
8. Prepare one exact `initiate_return` proposal for Action Queue. Preparation
   does not authorize or execute it.
9. A signed-in operator confirms or declines the exact action in a later
   request. If confirmed, a separate execution request lets AgentCore Policy
   and Aurora independently decide the outcome.

Safe boundary: context may explain why someone is investigating; it does not
become system-of-record fact. The Concierge may prepare a bounded proposal only
after a person supplies the missing material terms, and no database change
occurs at that checkpoint.

### Other operator clients

Every client in the operator book can be brought into the storefront as
read-only context. This supports demos with Amara, Catherine, Sarah, Julian,
David, Priya, Elena, Thomas, Michael, Rachel, Kevin, and other seeded records
without expanding the hero selector.

This is preview, not impersonation:

- the record still comes from the operator-gated API;
- any active shopper persona is cleared before render;
- no shopper token is minted for the client; and
- writes remain on the review and execution rails.

## Local rehearsal

The local stack uses PostgreSQL and intentionally does not claim Aurora or
AgentCore proof.

Prepare the local journey state:

```bash
python3 scripts/seed_local_golden_journeys.py
python3 scripts/seed_local_golden_journeys.py --apply
```

The helper is dry-run by default, refuses non-loopback hosts and databases that
do not end in `_dev`, and writes only one pending Theo review plus its immutable
shopper handoff receipt. It never updates, decides, or deletes an existing
review, and it never writes a return, credit, policy verdict, audit row, or
execution receipt.

Local review checkpoints:

```text
http://localhost:5173/
http://localhost:5173/observatory
http://localhost:5173/observatory/operator-lineage
http://localhost:5173/operator/reviews
http://localhost:5173/?clientPreview=CUST-JESSICA
```

Open Theo's current review from the queue rather than relying on a database
sequence value. On shared local state, inspect it without confirming, declining,
or executing it. `--clear` can remove only an untouched pending review and
refuses to erase a decided or executed one.

Run the deterministic journey gates:

```bash
cd pellier/backend
.venv/bin/pytest -q tests/test_golden_journeys.py \
  tests/test_local_golden_journey_seed.py \
  tests/test_persona_arc_contract.py

cd ../frontend
npm test -- --run
```

Local proof may establish:

- route and identity boundaries;
- fixture tool ordering;
- PostgreSQL facts;
- pending review shape and fingerprint;
- immutable shopper handoff integrity;
- application-orchestrated graph ordering and persisted artifact shape;
- read-only preview behavior; and
- operator/storefront navigation.

Local proof may not establish:

- AgentCore Runtime execution;
- Gateway MCP publication;
- managed Memory durability;
- Cedar `ALLOW` or `DENY`;
- Aurora RLS behavior in the deployed role path; or
- a final managed business outcome.

## Fresh AWS rehearsal

Before release, run the exact Workshop Studio pin in a clean account:

1. require CloudFormation success;
2. require the health gate to report `READY`;
3. complete all four labs in order;
4. record Runtime, Gateway, Memory, trace, Cedar, RLS, and reset evidence;
5. test operator access with the operator account and shopper refusal with
   Marco;
6. run Theo's full review and managed execution loop;
7. inspect the resulting policy, execution, data, and customer-outcome
   receipts; and
8. fix any failure in its owning source, bootstrap, or template, repin Studio,
   and repeat from another clean account.

A repair made only on the workshop box is not a product fix.

## Source of truth

| Contract | Source |
|---|---|
| Machine-readable golden journeys | `pellier/backend/tests/golden/journeys.json` |
| Golden journey gates | `pellier/backend/tests/test_golden_journeys.py` |
| Local pending-review helper | `scripts/seed_local_golden_journeys.py` |
| Immutable shopper handoff | `pellier/backend/services/shopper_handoff.py` |
| Operator Concierge Strands graph | `pellier/backend/services/operator_graph.py` |
| Operator graph lifecycle and persistence | `pellier/backend/services/operator_concierge.py` and `operator_concierge_sessions.py` |
| Operator authorization | `pellier/backend/services/auth.py` |
| Operator routes and review workflow | `pellier/backend/routes/operator.py` |
| Cross-surface reconstruction | `pellier/backend/routes/observatory.py` and `OperatorLineage.tsx` |
| Storefront-to-review handoff | `pellier/backend/services/chat.py` and `PellierChatBody.tsx` |
| Operator service-recovery entry | `pellier/frontend/src/operator/surfaces/ClientBook.tsx` |
| Storefront client preview | `pellier/frontend/src/components/OperatorClientPreview.tsx` |
| Client-to-storefront handoff | `pellier/frontend/src/operator/surfaces/ClientRecord.tsx` |
| Deployment and lab contract | `docs/HANDOFF-SOURCE-CONTRACT.md` |
| Participant instructions | sibling Workshop Studio repository under `content/10-*` through `content/40-*` |

The workshop is complete only when the participant can explain not just what
the agent answered, but which layer supplied each fact, decision, effect, and
receipt.
