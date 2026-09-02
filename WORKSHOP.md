# Pellier L400 Workshop - Co-Speaker Brief

> **Working draft.** This is the staff-facing story of the workshop as it is
> taking shape. The participant guide, recovery steps, and exact commands are
> still being refined in Workshop Studio. Use this brief to understand the
> experience we are building and how to present it coherently.

## The workshop in one minute

Pellier is a governed agentic retail experience. A shopper asks for help in a
premium storefront; a Strands dispatcher selects a bounded specialist; and
Aurora PostgreSQL supplies the facts behind the answer. Participants then move
from an answer that looks credible to evidence that can be queried, measured,
and governed: PostgreSQL proves what is true, AgentCore provides managed
capabilities, and durable receipts make it possible to reconstruct what
happened.

The central idea is simple: a good agent response is not enough. We want people
to distinguish four things:

1. What is true in the system of record.
2. What retrieval or an agent proposed.
3. What identity and policy permitted.
4. What actually executed and what evidence remains.

## Pellier Storefront

The experience starts with **Pellier**, not a dashboard. Marco, Anna, and Theo
make the system feel like a real retail interaction before we reveal the
architecture behind it. Jessica then anchors the governed customer case in
Pellier Operator. Start the room in the Storefront, then use one named customer
anchor per lab.

Each Storefront shopper has a coherent multi-turn conversation. Marco's
warehouse check anchors Lab 1, Anna's bounded gift request anchors Lab 2, and
Theo's three-turn ceramic and morning-ritual thread anchors Lab 3. Jessica is
not added to the Storefront selector; her customer identity and service case
anchor Lab 4. The designed experiences remain the participant's reason to build
and prove the underlying paths.

The rehearsal scripts are fixed because the history depth is part of the
architecture demonstration:

| Lab anchor | Three-turn script |
|---|---|
| **Marco · Lab 1** | `What linen do you have for 10 days in Goa?`<br>`What would go with the Hadley shirt?`<br>`Is the Hadley shirt at the Brooklyn warehouse, and can it still ship in time?` |
| **Anna · Lab 2** | `A thoughtful gift for someone who loves morning rituals`<br>`Keep the gift under $100 and show me the strongest two options.`<br>`Which one should I choose, and prove it stayed in budget and in stock?` |
| **Theo · Lab 3** | `Hand-thrown ceramics for a slower morning routine`<br>`What goes well with the pour-over set?`<br>`Without asking me to repeat the ritual or material, which pairing should I choose and why?` |
| **Jessica · Lab 4 Operator close** | `Investigate Jessica's open service issue (TKT-2026-3015) and recommend the next fair step. Distinguish what the records establish from what a source reports.`<br>`Which customer, order, return, and identity records are authoritative for this decision?`<br>`Prepare the fairest next step for human review without executing it.` |

For each Storefront script, the requests carry `0`, then `2`, then `4` prior
dialogue messages. The third turn therefore proves continuity only when the
agent preserves the earlier product and constraint identities. Jessica's
Operator script uses a separate authenticated staff session and stops at the
human checkpoint.

### Agent and tool model

The Storefront production path is a deterministic Strands dispatcher. Each
shopper turn is routed to exactly one bounded specialist:

- **Search** for catalog discovery and comparison.
- **Personalization** for recommendations and curated choices.
- **Pricing** for price and offer questions.
- **Inventory** for availability and fulfillment facts.
- **Customer Service** for order, return, and support requests.

Each specialist is a Strands `Agent` with an explicit, small `@tool` allowlist.
The tools are typed server-side operations, not an invitation for the model to
invent data or take arbitrary actions. Lab 1 makes this concrete by building
the Inventory Agent's `check_inventory` path; Lab 2 applies the same discipline
to retrieval and eligibility.

Labs 1 and 2 begin on the in-process rail so participants can build and measure
the application boundary directly. In Lab 3, they first prove Gateway and
Runtime with the AgentCore CLI, then set `USE_AGENTCORE_RUNTIME=true` and
restart `pellier` before running the three-turn Storefront path.

That managed Storefront proof requires a signed-in Cognito user. Selecting a
shopper persona is a scenario choice, not authentication, and an unsigned turn
must not be described as a managed fallback. The Runtime status endpoint
(`/api/agentcore/runtime/status`) proves the resource's lifecycle state; a turn
receipt with `rail=gateway-mcp` proves that a request actually used the managed
Runtime and Gateway path.

### Identity and proof guardrails

- A persona supplies workshop scenario context; a verified Cognito principal
  supplies authorization. Customer-specific reads require that verified scope.
- Fresh Gateway Cedar policies bind the verified username to the requested
  customer. A deny must be observed before target execution, then paired with
  `psql` evidence that no execution or canonical write occurred.
- Legacy migrated read aliases remain intentionally default-denied while their
  scoped policies converge. The workshop demonstrates only the current
  customer-preference and audit-trail tool names.
- Lab 4's return-ownership rule is deliberately participant-authored. It
  exercises the condition without weakening the shipped RLS backstop.
- Local tests validate the contract, not the deployed AWS path. The live
  rehearsal must capture a real Gateway denial before Lambda and the matching
  Aurora non-execution evidence.

## Pellier Operator

**Pellier Operator** is the authenticated service and human-decision surface.
Use Jessica's client record to close Lab 4. A separately authorized operator
investigates the same business subject after the identity and database boundaries
have been proven.

The Operator uses a separate Strands pattern: a bounded `GraphBuilder` flow
orders **Case Investigator** before **Resolution Planner**. It produces an
investigation and a proposed plan. It does not approve a review, authorize a
write, or mutate business data.

Jessica is not a fourth Storefront persona. She is a real Cognito customer
principal and the required Lab 4 business subject, while the separate
`operator` Cognito user remains the only account authorized for the staff desk.
Marco-for-Jessica demonstrates the cross-customer denial; Jessica-for-Jessica
is the positive control. The required Operator close then runs three turns:

1. Investigate ticket `TKT-2026-3015`, keeping established records separate
   from what the support source reports.
2. Identify which customer, order, return, and identity records are
   authoritative for the decision.
3. Prepare the fairest next step for human review without executing it.

The staff investigation is a separate request and fact from the direct Gateway
proof. It stops at the human checkpoint; no approval or mutation is implied.

## Pellier Observatory

**Pellier Observatory** is the inspection layer across routing, tools, SQL,
Memory, policy, receipts, and telemetry. It makes a live Storefront or Operator
run legible, but it does not replace the terminal as proof.

The Lab Collection and Live Workbench are one Observatory experience, not a
fourth product surface. The Lab Collection selects the current lab; the Live
Workbench carries its context into shared evidence views. Use it to orient the
room, replay a turn, and make the evidence easier to scan.

The required hands-on work remains deliberately concrete:

- **Code Editor** is where participants inspect and make the bounded changes.
- **`psql`** is the primary way to query, measure, and prove Aurora behavior.
- **AgentCore CLI** is used for managed Runtime, Gateway, and Policy
  interactions.

The UI helps participants inspect. PostgreSQL and AgentCore CLI let them prove.
Avoid turning this into a generic API-call workshop.

### Participant delivery model

Workshop Studio exposes one Pellier URL on port `8000`. FastAPI serves both the
built Storefront, Operator, and Observatory application and every `/api/*`
route. The separate Vite and FastAPI ports used during local development are
not part of the participant journey and should not appear in the room's
instructions.

## The four-lab journey

| Lab | Participant moment | What they build or prove | Takeaway |
|---|---|---|---|
| **Lab 1 · Build**<br>**Build a PostgreSQL-Grounded Agent** | Marco needs a live availability answer. | Complete the Inventory Agent and its `check_inventory` tool, then reconcile the response, warehouse rows, and `tool_audit` evidence with `psql`. | An agent answer is grounded only when it can be checked against the system of record and an execution receipt. |
| **Lab 2 · Build & Measure**<br>**Build and Measure PostgreSQL Hybrid Retrieval** | Anna narrows a morning-ritual gift to two in-stock options under $100, then chooses from that same shortlist. | Author the PostgreSQL RRF fusion expression, compare retrieval paths, and use SQL to prove the returned products met price and stock constraints. | Retrieval quality is a measured tradeoff. Relevance can rank results; PostgreSQL enforces eligibility. |
| **Lab 3 · Operate & Observe**<br>**Operate and Observe the AgentCore Managed Path** | Theo's multi-turn ceramic request needs context and a traceable managed path. | Complete an OTEL trace contract, invoke the managed path as Theo with AgentCore CLI, verify Memory across a fresh process, and correlate his three-turn Storefront thread with Runtime, Gateway, and PostgreSQL receipts. | Managed Runtime, Gateway, Memory, and telemetry each prove different parts of the path. A successful answer alone proves none of them. |
| **Lab 4 · Govern**<br>**Enforce Identity and Prove Non-Execution** | Marco and Anna must not act as Jessica; Jessica can act only as Jessica. | Write the Cedar identity condition; run Marco DENY, Anna DENY, Jessica ALLOW, and Jessica replay; use `psql` to prove exact execution and durable-effect counts plus RLS read/write enforcement; then complete Jessica's three-turn Operator investigation and stop before approval. | Authentication, policy authorization, execution, database enforcement, staff access, durable effects, and human approval are separate controls and separate facts. |

The labs intentionally form one narrative:

```text
Ground the answer
  -> measure the retrieval decision
  -> operate the managed path and inspect its traces
  -> govern a consequential action and prove its outcome
```

## Architecture and proof boundaries

Keep the explanation at this level unless someone asks to go deeper:

```text
Shopper request in Pellier Storefront
  -> Strands dispatcher selects one bounded specialist
  -> Aurora-backed tool or retrieval path
  -> response plus durable evidence

Customer-authenticated consequential request
  -> AgentCore Gateway and Cedar policy
  -> bounded tool execution
  -> Aurora RLS and durable effect

Staff investigation in Pellier Operator
  -> authenticated operator group membership
  -> Case Investigator then Resolution Planner
  -> human checkpoint, no execution

Observatory
  -> reconstruction from receipts, SQL, and traces
```

This is not one long-running super-agent. Storefront orchestration, Operator
investigation, human decision, policy authorization, database execution, and
Observatory reconstruction are deliberately separate boundaries. That is why
the room can ask, "What happened here?" and receive an answer that is more
precise than "the agent did it."

## Suggested flow for speakers

1. **Narrative lead:** Open in the storefront. Establish the retail problem and
   choose the persona that will anchor the next lab.
2. **Lab lead:** Move to Code Editor and the terminal. Keep the build moment
   small. Participants can work in the Manual or Claude Code pane, open hints
   in order, and use the solution only as a recovery path. Both panes converge
   on the same `psql` or AgentCore CLI proof.
3. **Platform lead:** Use the Workbench and Observatory to make the resulting
   routing, Memory, tool, SQL, and trace evidence readable.
4. **Governance lead:** Run the four-case identity matrix, then the RLS
   read/write worksheet. Make authorization, execution, durable effect, and
   database enforcement separate claims.
5. **Operator lead:** Open Jessica's client record as the separate `operator`
   account and run the three guided turns. Show Case Investigator before
   Resolution Planner, then stop at the human checkpoint. Do not call the
   direct Gateway invocation a human-approved action.

## Speaker anchors

Use these lines to keep the story consistent:

- "Pellier starts with a customer outcome, then earns the right to make a
  technical claim."
- "The UI helps us inspect; `psql` and AgentCore CLI let us prove."
- "A retrieval result can be relevant without being eligible."
- "Memory carries context; Aurora remains the system of record."
- "An `ALLOW` is not an execution receipt, and a `DENY` needs named
  non-execution evidence."
- "The database is not a passive store behind the agent. It independently
  enforces the final boundary."

Avoid saying that a configured managed service was necessarily invoked on every
Storefront turn. Runtime, Gateway, Memory, policy, and telemetry must be shown
with their own evidence in the managed-path labs.

## What staff should take away

The product is a connected teaching system, not four unrelated demos:

- The **Storefront** gives the architecture a human reason to exist.
- The **labs** add a real build or authoring moment before asking for proof.
- **PostgreSQL** makes data truth, retrieval behavior, and enforcement
  inspectable.
- **AgentCore** makes managed execution, tool exposure, Memory, and policy
  tangible.
- **Observatory** makes the invisible path legible without competing with the
  terminal.
- **Operator** makes clear that meaningful actions require a durable human and
  governance boundary.

The core participant outcome is not simply "I used an agent." It is: "I can
explain which layer supplied the fact, made the decision, enforced the
constraint, and recorded the evidence."

## Before the session

- Confirm the Workshop Studio source pin and the intended governed revision.
- Rehearse the exact four-lab path with the participant environment.
- Verify that `psql`, the AgentCore CLI, and the required credentials are ready.
- Choose speaker ownership for Storefront narrative, labs, managed path, and
  governance.
- Rehearse Jessica's required three-turn Operator close and verify it stops at
  the human checkpoint without preparing or executing a business action.

The run-of-show is still being polished. This brief is the shared map for the
team: customer experience first, a meaningful build moment in each lab,
evidence over assertion, and governance that holds at more than one layer.
