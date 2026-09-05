# Pellier L400 Workshop - Co-Speaker Brief

> **Working draft.** This is the staff-facing story of the workshop as it is
> taking shape. The participant guide, recovery steps, and detailed instructions are
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
| **Marco · Lab 1** | "What linen do you have for 10 days in Goa?"<br>"What would go with the Hadley shirt?"<br>"Is the Hadley shirt at the Brooklyn warehouse, and can it still ship in time?" |
| **Anna · Lab 2** | "A thoughtful gift for someone who loves morning rituals"<br>"Keep the gift under $100 and show me the strongest two options."<br>"Which one should I choose, and prove it stayed in budget and in stock?" |
| **Theo · Lab 3** | "Hand-thrown ceramics for a slower morning routine"<br>"What goes well with the pour-over set?"<br>"My Wabi-Sabi Bowl arrived chipped. Please help me return it." |
| **Jessica · Lab 4 Operator close** | "Investigate Jessica's open service issue (TKT-2026-3015) and recommend the next fair step. Distinguish what the records establish from what a source reports."<br>"Which customer, order, return, and identity records are authoritative for this decision?"<br>"Prepare the fairest next step for human review without executing it." |

For each Storefront script, the requests carry 0, then 2, then 4 prior
dialogue messages. Theo's third turn closes the managed thread with a
consequential return request: the session history is available to AgentCore
Memory, while the identity, policy, Aurora, and human-review boundaries remain
separate. Jessica's Operator script uses a separate authenticated staff session
and stops at the human checkpoint.

### What the room sees in the Storefront (updated 2026-09-03)

- A first visit opens a short welcome tour. Once it is dismissed, the persona
  choice lives in the header pill. Signed out, that pill opens the same
  three-card chooser ("Choose who enters Pellier") as the signed-in pill; the
  old compact dropdown is gone. The hero no longer repeats the question.
- Before Lab 1 is built, Marco's warehouse question returns a quiet card,
  "Still being set up", with the reference code `workshop_build_required`.
  That is the designed state, not an error: the inventory tool does not exist
  yet. After Lab 1 the same question returns live stock. Tell the room this
  before they try it. Anna's third turn ("prove it stayed in budget and in
  stock") needs the same tool, so it shows the same card until Lab 1 is
  built: run the labs in order.
- Rehearsal timing: an editorial turn (Marco or Anna's first two, Theo's
  first two) takes about 30 to 35 seconds to answer on Opus. Theo's return
  and the build-state card come back in a second or two. Keep talking while
  the first answer streams.
- Shopper copy never names Aurora, Cognito, agents or tools. The product page
  says "Checked just now" and "Counts by warehouse"; the persona card says the
  choice "does not sign you in as that customer". The Observatory is where
  the architecture words live.
- The product page title, the home hero and every Observatory page title use
  the same display typeface, so the three surfaces read as one product. The
  product photograph opens enlarged on click; Escape closes it. Stories and
  About in the header are real pages again rather than links back home.
- About names all three surfaces in plain words: the boutique, the Operator
  desk (where a return, a credit or a held action is decided by a person and
  the decision is kept) and the Observatory (which specialist took the
  request, what it read, what it was allowed to do, what the database
  changed). The stack chips are the real stack; Amazon Transcribe is gone
  and Cohere Rerank is listed. Stories carries three volumes and four field
  notes; the notes now match the seeded orders (Marco's linen-then-travel
  run, Anna's gift under a hundred, Theo's incense holder to wabi-sabi bowl).
  The three Stories photographs and the About photograph are our own
  generated stills, served as local WebP and AVIF, so neither page needs the
  internet in the room.
- The header's Pellier Operator and Pellier Observatory links are the same
  size as the primary nav, still in the muted colour.
- Marco, Anna and Theo have new portraits from one shoot (warm plaster wall,
  raking light, linen and knit in their own palettes). The chooser's photo
  row is taller so each face is a full headshot. Jessica keeps her
  client-book portrait: she is the Lab 4 customer, not a shopper persona,
  and her photo must stay the same face in the client book and the lab
  cards.
- The chooser blurbs now match the seeded orders (migration 045: Marco's
  "seven orders of linen and leather", no invented "Maren tunic", no em
  dashes). Fresh boxes get it from bootstrap; an existing cluster needs the
  migration applied once.
- Signed out, "Ask Pellier" in the header and the search icon open the
  persona chooser instead of doing nothing, because the concierge needs a
  shopper. The hero card and the chooser use the same words: "Choose who
  enters Pellier."
- Shopper copy no longer says Aurora, "workshop profile" or "tag weights".
  The chat eyebrow reads "Signed in as Marco", the hero badge "Live
  catalog". The Observatory is still where the architecture words live.

### Agent and tool model

The Storefront production path is a deterministic Strands dispatcher. Each
shopper turn is routed to exactly one bounded specialist:

- **Search** for catalog discovery and comparison.
- **Personalization** for recommendations and curated choices.
- **Pricing** for price and offer questions.
- **Inventory** for availability and fulfillment facts.
- **Customer Service** for order, return, and support requests.

Each specialist is a Strands agent with an explicit, small tool allowlist.
The tools are typed server-side operations, not an invitation for the model to
invent data or take arbitrary actions. Lab 1 makes this concrete by building
the Inventory Agent's inventory-check path; Lab 2 applies the same discipline
to retrieval and eligibility.

The Live Workbench exposes three response settings without changing the
deterministic routing or authorization path: **Balanced** uses the established
Opus/Sonnet specialist mix, **Editorial** selects the configured Opus profile for
the responding specialist, and **Fast** selects the configured Claude Haiku
4.5 profile for a concise grounded response. The Workbench records the exact
model identifier used by each turn rather than relying on the selected label.

| Concern | Fixed model contract | What the presenter should show |
|---|---|---|
| Dispatcher, routing, structured extraction, reporting | Claude Sonnet 4.6, global profile | The route is deterministic. Changing a response setting does not reroute the request. |
| Search, Personalization, Customer Service | Claude Opus 4.6, global profile by default | Balanced preserves the editorial/reporting split; Editorial uses the configured Opus profile for the responding specialist. |
| Fast response composition | Claude Haiku 4.5, global profile | Fast is concise composition after the same routing and tool boundary, not a shortcut around grounding. |
| Retrieval | Cohere Embed v4 and Cohere Rerank v3.5 | These remain retrieval infrastructure, not a Run setup option. |

The Bedrock preflight verifies required Sonnet, Haiku, embedding, and rerank
profiles and resolves the editorial Opus-or-Sonnet path before the workshop is
marked ready. Say that Run setup changes *how the selected specialist composes
the answer*. Do not say that Fast disables retrieval, Memory, policy, telemetry,
Aurora enforcement, or authentication; those boundaries remain fixed and must
be proven independently.

Labs 1 and 2 begin on the in-process rail so participants can build and measure
the application boundary directly. In Lab 3, they first verify Gateway and
Runtime, then move the Storefront onto the managed path before running Theo's
three-turn journey.

That managed Storefront proof requires a signed-in Cognito user. Selecting a
shopper persona is a scenario choice, not authentication, and an unsigned turn
must not be described as a managed fallback. The Runtime status indicator
proves the resource's lifecycle state; a managed-path receipt proves that a
request actually used the Runtime and Gateway path.

### Identity and proof guardrails

- A persona supplies workshop scenario context; a verified Cognito principal
  supplies authorization. Customer-specific reads require that verified scope.
- Fresh Gateway policies bind the verified user to the requested
  customer. A deny must be observed before target execution, then paired with
  PostgreSQL evidence that no execution or canonical write occurred.
- Only the current managed read paths are demonstrated; older migrated paths
  remain deliberately unavailable until their scoped policies converge.
- Lab 4's return-ownership rule is deliberately participant-authored. It
  exercises the condition without weakening the shipped row-level-security
  backstop.
- Local tests validate the contract, not the deployed AWS path. The live
  rehearsal must capture a real Gateway denial before Lambda and the matching
  Aurora non-execution evidence.
- A successful Runtime invocation does not prove the participant's revision
  ran. The invoke response carries no version and `qualifier=DEFAULT` is an
  alias, so a green answer is equally consistent with a silently failed deploy
  and yesterday's package. The Proof Board's managed receipt carries a build
  fingerprint for exactly this: **This checkout** means the deployed package
  was built from their source, **Older deployment** names both digests, and
  **Not reported** means the runtime predates the mechanism, which is not the
  same finding as stale.
- Lab 4's RLS proof now asserts its own preconditions before claiming a
  denial. A policy decides nothing if the role holds BYPASSRLS or SUPERUSER,
  if the proof runs as the table owner (`pellier.returns` is ENABLE, not
  FORCE), or if a second permissive policy has been added — permissive
  policies are OR-ed, so they can only widen. Each of those now fails with a
  named diagnosis rather than a bare "out-of-scope write succeeded", which
  reads as a broken policy rather than a skipped one.

## Pellier Operator

**Pellier Operator** is the authenticated service and human-decision surface.
Use Jessica's client record and ticket **TKT-2026-3015** to close Lab 4. A separately authorized operator
investigates the same business subject after the identity and database boundaries
have been proven.

The Operator uses a separate bounded investigation flow that orders **Case
Investigator** before **Resolution Planner**. It produces an
investigation and a proposed plan. It does not approve a review, authorize a
write, or mutate business data.

What the desk looks like now (updated 2026-09-03): the sign-in control is the
same round pill as the Storefront's, so the two surfaces read as one product;
it opens the Cognito sign-in, not the persona chooser. Each browser tab is titled by the desk view (Clients, Action
Queue, Client, Review). Action Queue rows carry an outcome glyph and word,
pending, declined, approved, refused or executed, so a policy refusal and a
carried-out write never look alike in the list, and the queue can be filtered
by those outcomes. The client book has a name filter beside the membership
ladder. On a phone the review record stacks every card, including the
proposed action's parameters, above the decision buttons. Every signed-out
desk view, including the Action Queue and a single review, carries its own
Sign in button, and a decision that fails for a reason other than changed
parameters or an expired sign-in reads as a sentence, not a raw error code.

Jessica is not a fourth Storefront persona. She is a real Cognito customer
principal and the required Lab 4 business subject, while the separate
operator sign-in remains the only account authorized for the staff desk.
Marco-for-Jessica demonstrates the cross-customer denial; Jessica-for-Jessica
is the positive control. The required Operator close then runs three turns:

1. Investigate Jessica's service issue, keeping established records separate
   from what the support source reports.
2. Identify which customer, order, return, and identity records are
   authoritative for the decision.
3. Prepare the fairest next step for human review without executing it.

The staff investigation is a separate request and fact from the direct Gateway
proof. It stops at the human checkpoint; no approval or mutation is implied.
The Operator deep link keeps that boundary visible: an unsigned visitor is
asked to sign in to the staff desk, while an unavailable governed service is
reported as unavailable rather than leaving the case in a permanent loading
state.

After the terminal shopper receipt, the Evidence Ledger can project the
Operator lifecycle as a separate typed follow-up: **review opened**, **review
confirmed or declined**, and, only when a reviewed action is attempted, the
resulting **execution receipt**. Those events stay after the immutable shopper
turn. They do not make a staff action look like a Storefront mutation, and
they do not expose action arguments, principal identifiers, or customer
mapping details.

## Pellier Observatory

**Pellier Observatory** is the inspection layer across routing, tools, database
evidence, Memory, policy, receipts, and telemetry. It makes a live Storefront or Operator
run legible, but it does not replace the evidence process.

The Lab Collection and Live Workbench are one Observatory experience, not a
fourth product surface. The Lab Collection selects the current lab; the Live
Workbench carries its context into shared evidence views. Use it to orient the
room, replay a turn, and make the evidence easier to scan. For the Jessica
handoff, it also makes the boundary explicit: the shopper turn ends, then the
typed Operator review and, if one occurs, execution lifecycle follows as
separate evidence.

What to point at in the Workbench (updated 2026-09-04):

- The Evidence ledger opens with the three receipts for the turn: **Policy**
  (the decisions recorded), **Execution** (tool calls audited) and **Data**
  (Aurora receipts, with any rejected statement counted). "Not recorded" is
  printed rather than hidden.
- Every ledger event can open its receipt fields: a policy event shows the
  decision, principal, action, resource and policy; a model event shows model
  id and tokens; an Aurora event shows the database role, statement timeout,
  rows returned and whether it was accepted; a tool event shows the recorded
  arguments and result. Retrieval events show the candidate table with vector
  rank, lexical rank, RRF and rerank score, and a "Trace this retrieval" link
  that opens the Search pipeline on the shopper's own query.
- The Sessions telemetry tab shows the same details per panel, and stacks
  properly on a phone.
- Performance says "not recorded in this window" for any panel without data
  and never prints a zero as a median.
- The reference views under the Lab Collection are an index table: each view,
  what it shows and the table or service it reads from. In the live Workbench
  the same index is collapsed behind "Explore reference views" so the ledger
  keeps the space.
- Sessions can be narrowed by a typed query or a status chip. The Tool Registry
  lists tools one line each and opens a tool's signature only when selected.
  The registry reads the `pellier.tools` table; it should show the current
  `search_products` and `check_inventory` names. If it does not, re-run
  `scripts/seed_tool_registry.py` against that cluster. A fresh bootstrap
  seeds the current names.
- In the Evidence ledger the round node beside each row marks the event's
  status, not its kind: dashed ring pending, check succeeded, shield denied,
  cross failed. The kind is the small label next to it.
- Every Observatory view sits on the same warm paper as the Storefront and the
  Operator desk. The cooler grey backdrop behind the Proof Board and the
  reference views is gone; the instrument feel comes from the mono type and
  the receipts, not from a different colour.
  Lab labels read "Lab 1 · Build a PostgreSQL-Grounded Agent" and so on, with
  no dashes; small Observatory labels are never below 11px.
- The Observatory and the Operator desk now resolve to the same type scale as
  the Storefront: one display face for page and section titles, weight capped
  at 600, and one control family, where a pill is something you press and a
  4px chip is something you read. If a surface suddenly looks louder or
  smaller than its neighbour, that is a regression, not a house style.
- On the Proof Board, the managed receipt names the **executed revision**.
  Point at it in Lab 3: it is the difference between "the service answered"
  and "the service ran the code I just packaged".

The required hands-on work remains deliberately concrete:

- **Workshop workspace** is where participants inspect and make one bounded
  change.
- **PostgreSQL** is where participants query, measure, and prove Aurora
  behavior.
- **AgentCore** is where participants inspect managed Runtime, Gateway, Memory,
  and policy evidence.

The UI helps participants inspect. PostgreSQL and AgentCore evidence let them
prove. Avoid turning this into a generic API-call workshop.

### Participant delivery model

Workshop Studio exposes one Pellier link for the Storefront, Operator, and
Observatory. Development setup is an implementation detail and should not
appear in the room's instructions.

## The four-lab journey

Every lab carries two bounded builds, a and b, anchored to one person. The
difficulty climbs across the four: Lab 1 completes a capability, Lab 2 decides
what "relevant" means and measures it, Lab 3 puts the participant's own work on
the managed control plane, Lab 4 governs a consequential action and proves the
outcome four separate ways.

| Lab | Participant moment | What they build or prove | Takeaway |
|---|---|---|---|
| **Lab 1 · Build**<br>**Build a PostgreSQL-Grounded Agent** | Marco needs a live availability answer. | Complete the Inventory Agent's warehouse capability, then reconcile the response, warehouse rows, and execution evidence in PostgreSQL. | An agent answer is grounded only when it can be checked against the system of record and an execution receipt. |
| **Lab 2 · Build & Measure**<br>**Build and Measure PostgreSQL Hybrid Retrieval** | Anna narrows a morning-ritual gift to two in-stock options under $100, then chooses from that same shortlist. | **2a** Restore the hybrid-ranking calculation. **2b** Label the rows that count as relevant, then read the micro-eval that divides by them. Prove the returned products met price and stock constraints. | Retrieval quality is a measured tradeoff, and the measurement rests on a labeling judgment a person makes. Relevance can rank results; PostgreSQL enforces eligibility. |
| **Lab 3 · Deploy & Operate**<br>**Deploy and Operate the Managed Agent Path** | Theo's return request reaches a support specialist the managed Gateway cannot yet serve. | **3a** Publish the customer-scoped read the specialist needs, and keep the money movement deferred. **3b** Reconcile what the Runtime asks the Gateway for, and bind that read to the authenticated caller. Deploy, then verify Memory beyond the application process and confirm the build fingerprint on the managed receipt is their own. | Deploying is not the proof. The published catalogue, the executed revision, managed Memory, and the trace each prove a different part of the path, and a successful answer proves none of them. |
| **Lab 4 · Govern**<br>**Govern and Prove Agent Actions** | Jessica's return action is allowed only for Jessica; Marco and Anna are the negative controls. | **4a** Define the identity-to-customer Cedar rule, then run the deny, allow, and replay cases. **4b** Author the OpenTelemetry trace contract that says what a complete managed trace must contain. Prove policy, execution, durable-effect, and database-enforcement outcomes separately, then complete Jessica's Operator investigation and stop before approval. | Authentication, policy authorization, execution, database enforcement, staff access, durable effects, and human approval are separate controls and separate facts. Observability is how you find that out after the fact. |

### Time box

Two hours, and the room is self-paced, so these are budgets rather than a
schedule. A lab that runs over does not steal from the next one: it steals
from the close, which is why the close is last and short.

| Segment | Budget | Why it costs what it costs |
|---|---|---|
| Orientation and `workshop-start` | 10 min | One run id, the two surfaces, and the shape of the proof. No architecture tour. |
| **Lab 1 · Marco** | 20 min | Two small edits in one file each, and the first receipt. Most of the cost is the first read of an unfamiliar tree. |
| **Lab 2 · Anna** | 20 min | One SQL expression, one labeling query, and the comparison. Both builds are short; reading the measurement is the work. |
| **Lab 3 · Theo** | 30 min | Two edits plus a real deploy. The deploy has wall clock nobody can compress, so this lab gets the extra ten minutes rather than borrowing them. |
| **Lab 4 · Jessica** | 30 min | A Cedar rule, four principals, the trace contract, and the RLS proof. Four separate outcomes to establish, and establishing them separately is the point. |
| Close | 10 min | What travels off the box. |

Two labs at 20 and two at 30 is deliberate. Labs 1 and 2 are bounded edits with
fast feedback; Labs 3 and 4 each wait on something real, a deploy and a policy
evaluation, and a room that has not been given time for that will skip the
proof and keep the answer.

If the room is running behind, cut Lab 4's Operator investigation and the
close, in that order. Never cut a Prove beat: a lab without its proof teaches
that the demo worked.

### Exact participant exercises

Every lab follows the same five-beat rhythm, and the beats are named on the
page so nobody has to infer where they are:

**Predict** what the system will do, and say it out loud before running
anything. **Change** exactly one bounded thing. **Run** the named person's
scenario. **Prove** the result from a durable row, not from the answer text.
**Explain** which layer supplied the fact, so the pattern travels off this
box.

Predict is not a warm-up. A participant who has committed to an expected
outcome learns something from being wrong; one who runs first and reads the
result afterwards learns that the demo worked. Bootstrap restores the starter
gaps; a solution file is a timed recovery path, never a substitute for the
exercise or its proof.

Before Lab 1, each participant runs `workshop-start`. It mints one run id,
records it in `pellier.workshop_runs`, and puts it in front of the service, so
every evidence row the next two hours produce carries that id. That is what
lets `receipt` and `doctor` answer questions about *their* run rather than
about whatever the cluster saw most recently. If a lab will not start, the
first move is `doctor --lab N`, which names the unmet prerequisite instead of
leaving the participant to guess from a symptom.

#### Lab 1 - Marco grounds a warehouse answer

- **Predict.** Marco's warehouse turn currently returns the quiet
  "Still being set up" card with the reference code `workshop_build_required`.
  Ask the room what the answer should contain once the tool exists, and what
  would have to be true in the database for it to be trustworthy.
- **Change.** Complete the deliberately unfinished inventory capability: the
  Inventory Agent definition and the `check_inventory` body, inside their
  marker blocks and nowhere else.
- **Run.** Replay Marco's three turns: linen for Goa, the pairing question,
  then the Brooklyn fulfillment question.
- **Prove.** Reconcile the answer against Aurora warehouse rows and the
  execution row in `pellier.tool_audit`. The receipt line is
  `01.execution_row`. An answer that reads correct and leaves no row has
  proved nothing.
- **Explain.** An agent answer is grounded only when it can be checked against
  the system of record and an execution receipt. The same shape applies to any
  entitlement, claim-status, or capacity lookup.

#### Lab 2 - Anna measures hybrid retrieval

- **Predict.** The retrieval comparison runs one fixed request, "A housewarming
  gift under $100 that is currently in stock." That is not one of Anna's three
  storefront turns above. It is the single request the comparison surface, the
  golden journey, and the eval harness golden set all measure, and it is what
  her memory chip fires when a participant clicks instead of typing. Before
  running it, ask which strategy will win and why, and which constraint ranking
  cannot enforce.
- **Change (2a).** Restore the deliberately incomplete hybrid-ranking
  calculation.
- **Change (2b).** Label the rows that count as relevant for that request. The
  micro-eval divides by this set, so with it empty coverage, precision and MRR
  all read 0.0 for want of a denominator, and the surface says so rather than
  showing bare zeros. The definition is a query, not a taste test: the in-stock
  Home Decor pieces tagged both `gift` and `home` at or under $100. Derive them
  in the Code Editor rather than guessing; the exercise carries the psql.
- **Run.** Replay Anna's gift thread in the storefront, then compare the four
  retrieval paths on that one fixed request. Comparing four strategies is only
  meaningful when all four answer the same question, which is why the wording is
  fixed.
- **Prove.** Read the retrieval receipt: vector ranks, lexical ranks, and their
  fusion all populated, and every returned product inside the price and stock
  constraints. The receipt line is `02.hybrid_receipt`. Then read the rerank
  pool micro-eval, which now has a denominator: pool 20 and pool 3 separate.
- **Explain.** Retrieval quality is a measured tradeoff, and every metric is a
  ratio against a labeling somebody chose. Relevance can rank results;
  PostgreSQL enforces eligibility. A reranker cannot recover a candidate that
  retrieval never surfaced, which is what candidate coverage measures.

#### Lab 3 - Theo lands the build on the managed path

- **Predict.** Theo's third turn is a return request, which routes to the
  support specialist. Ask what the managed rail will do with it before running
  it. Then ask what a successful managed answer would and would not prove: it
  does not prove the participant's revision ran, because the invoke response
  carries no version and `qualifier=DEFAULT` is an alias.
- **Change (3a).** The support specialist reads a customer's past tickets
  before answering, and the Gateway does not publish that tool. Publish
  `get_ticket_history`; leave `issue_credit` deferred. That second half is the
  decision, not an oversight: a read scoped to one customer is safe to hand a
  shopper-facing specialist, and money movement belongs to the operator review
  desk.
- **Change (3b).** Reconcile the Runtime side. The managed dispatcher asks the
  Gateway for exactly the tools it names and raises `Gateway is missing support
  tools` when one is absent, so the two catalogues have to agree. Then bind the
  new read to the authenticated caller, or the model chooses whose tickets to
  read.
- **Run.** Deploy, then use Theo's three turns as a signed-in caller, with 0,
  then 2, then 4 prior messages.
- **Prove.** Theo's third turn now completes on the managed rail. Confirm the
  build fingerprint on the managed receipt reads **This checkout**: the file
  edited in 3b is packaged into the Runtime, so the deployed digest changed and
  that is what proves the participant's own build answered. Verify Memory
  beyond the application process, and correlate the thread with Runtime,
  Gateway, and PostgreSQL evidence.
- **Explain.** Deploying is not the proof. A published tool contract, an
  executed revision, managed Memory, and a trace each prove a different part of
  the path. The same split applies wherever a control plane and a data plane
  are deployed separately.

#### Lab 4 - Jessica governs a consequential action

- **Predict.** Same request, four principals. Ask the room which cases will be
  denied, which will execute, and what the replay will and will not change.
- **Change (4a).** Complete the fail-closed identity-to-customer rule in the
  Cedar policy. It is deliberately participant-authored and exercises the
  condition without weakening the shipped row-level-security backstop.
- **Change (4b).** Author the OpenTelemetry trace contract: the predicates that
  say what a complete managed trace must contain. They start `false`, which is
  the honest starting position. Deciding that an agent span, a model span, a
  tool span and a session-correlated span are each required is the exercise;
  running the contract afterwards is arithmetic.
- **Run.** Exercise the deny, allow, and replay cases, run the trace contract
  against a real managed trace, then complete Jessica's three-turn Operator
  investigation and stop before approval.
- **Prove.** Establish four separate outcomes: the policy decision, the
  execution row (or its keyed absence), the durable write, and the database
  enforcement result. The receipt lines are `04.deny_did_not_execute` beside
  `04.durable_effect`.
- **Explain.** Authentication, policy authorization, execution, database
  enforcement, staff access, durable effects, and human approval are separate
  controls and separate facts. An ALLOW is not an execution receipt, and an
  execution row is not a commit.

Theo's thread and Jessica's return are deliberately different journeys. Theo's
ends at a prepared review with the human decision still pending, which is where
a shopper turn honestly stops. Jessica's is where authorization, database
enforcement, and durable evidence are proved, because there identity is the
only variable that changes between the denied and allowed cases.

The labs intentionally form one narrative: ground the answer, measure the
retrieval decision against a labeling you chose, deploy that work onto the
managed path, then govern a consequential action and prove its outcome from
policy, execution, durable effect, database enforcement, and trace.

## The memory distinction

This is the single point attendees most often leave still conflating, so state it the
same way every time. "The agent has memory" is four systems with four owners, four
lifetimes, and four failure modes. AgentCore Memory holds two of them.

| Substrate | Owner | Keyed by | What it holds |
|---|---|---|---|
| **Working** | AgentCore Memory, short-term | actor **and session** | The session timeline. Raw turns, 30-day event expiry. |
| **Semantic** | AgentCore Memory, long-term | **actor** | Preferences a single `USER_PREFERENCE` strategy extracts, under `/pellier/preferences/{actorId}/`. |
| **Episodic** | **Aurora PostgreSQL** | customer | Orders, returns, events. A system of record queried with SQL, not a recall service. |
| **Procedural** | **The repository** | file path | `skills/*/SKILL.md` and the MCP tool schemas. Reviewable source, changed by pull request. |

`pellier.tool_audit` is deliberately not on that list. It is execution history: which
tool ran, with what arguments, at what latency. Nothing reads it back as context, so it
teaches the agent nothing. Describing aggregates over it as procedural memory was an
earlier model and is wrong.

Short-term and long-term are not the same records with different retention; they have
different keys. End the session and working memory stops growing, while semantic records
are still there tomorrow on a new device. That is why they cannot be collapsed behind one
retention setting.

Lab 3 proves this hands-on, and the workshop appendix carries the full reference with a
symptom-to-substrate table. The reason to be pedantic is operational: each substrate
fails differently, so conflating them produces the wrong fix. A forgotten sentence is a
session-id problem; a wrong order history is a database problem; a misused tool is a pull
request. Commercially, two of these are a managed-service bill, one is your database, and
one is your git history.

## Architecture and proof boundaries

Keep the explanation at this level unless someone asks to go deeper:

- A shopper request moves from the Storefront, through one bounded specialist,
  to an Aurora-backed fact or retrieval path, then to a response with durable
  evidence.
- A customer-authenticated consequential request passes through Gateway policy,
  bounded tool execution, and Aurora row-level security before any durable
  effect can occur.
- A staff investigation in Operator requires authorized staff access, moves
  from Case Investigator to Resolution Planner, and ends at a human checkpoint
  without execution in the required participant path. If a reviewer acts
  later, the decision and any execution receipt are projected as typed
  follow-up evidence after the shopper receipt.
- Observatory reconstructs the path from receipts, database evidence, and
  traces.

This is not one long-running super-agent. Storefront orchestration, Operator
investigation, human decision, policy authorization, database execution, and
Observatory reconstruction are deliberately separate boundaries. That is why
the room can ask, "What happened here?" and receive an answer that is more
precise than "the agent did it."

## Suggested flow for speakers

1. **Narrative lead:** Open in the storefront. Establish the retail problem and
   choose the persona that will anchor the next lab.
2. **Lab lead:** Move to the workshop workspace. Keep the build moment small.
   Participants can work manually or with the assisted pane, open hints in
   order, and use the solution only as a recovery path. Both paths converge on
   the same evidence.
3. **Platform lead:** Use the Workbench and Observatory to make the resulting
   routing, Memory, tool, database, and trace evidence readable.
4. **Governance lead:** Run the four-case identity matrix, then the database
   read/write proof. Make authorization, execution, durable effect, and
   database enforcement separate claims.
5. **Operator lead:** Open Jessica's client record from the separate staff
   account and run the three guided turns. Show Case Investigator before
   Resolution Planner, then stop at the human checkpoint. Do not call the
   direct Gateway invocation a human-approved action.
6. **Close:** Run `workshop/close-architecture-defense.md`. Do not recap.
   Put an authorized-but-uncommitted evidence set on screen, ask the room
   whether the return happened, and let them answer before you do. Then have
   participants run `receipt` and answer the four questions from their own
   evidence — the receipt lines they point at are `01.execution_row`,
   `02.hybrid_receipt`, the managed receipt's build fingerprint, and
   `04.deny_did_not_execute` beside `04.durable_effect`. Eight minutes, and
   it lands the separation the whole session was built on: authorization,
   execution, and commit are three transitions, each needing its own proof.
   The close doc also carries a live query for the contradiction; an empty
   result is a finding worth saying out loud, not a failed demo.

## Speaker anchors

Use these lines to keep the story consistent:

- "Pellier starts with a customer outcome, then earns the right to make a
  technical claim."
- "The UI helps us inspect; durable evidence lets us prove."
- "A retrieval result can be relevant without being eligible."
- "Memory is four systems, not one. Two live in AgentCore, one is Aurora, and one is
  the repository. `tool_audit` is none of them."
- "An allow decision is not an execution receipt, and a deny decision needs named
  non-execution evidence."
- "The shopper turn ends before the staff review begins. The ledger shows that
  handoff without collapsing the two into one action."
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
- **Observatory** makes the invisible path legible without replacing the
  evidence.
- **Operator** makes clear that meaningful actions require a durable human and
  governance boundary.

The core participant outcome is not simply "I used an agent." It is: "I can
explain which layer supplied the fact, made the decision, enforced the
constraint, and recorded the evidence."

## Before the session

- Confirm the Workshop Studio source pin and the intended governed revision.
- Rehearse the exact four-lab path with the participant environment.
- Verify that PostgreSQL access, AgentCore access, and the required credentials
  are ready.
- Choose speaker ownership for Storefront narrative, labs, managed path, and
  governance.
- Rehearse Jessica's required three-turn Operator close and verify it stops at
  the human checkpoint after preparing, but without approving or executing, a
  business action.
- Run `receipt` on the rehearsal box after the four labs. It reports each
  boundary as PROVED, NOT YET, or UNCHECKED, and the third is the one to read
  carefully: UNCHECKED means the query could not run, not that the step
  failed. It is also the fastest table-lead diagnostic during the session.
- After deploying in Lab 3, confirm the Proof Board's executed revision reads
  **This checkout**. **Older deployment** means the deploy did not land and the
  managed answers are coming from a previous package.
- Rehearsing locally: the dev script's tunnel to Aurora expires after about an
  hour. If the storefront starts stalling for thirty seconds on every request,
  restart the dev script before blaming the app.

The run-of-show is still being polished. This brief is the shared map for the
team: customer experience first, a meaningful build moment in each lab,
evidence over assertion, and governance that holds at more than one layer.
