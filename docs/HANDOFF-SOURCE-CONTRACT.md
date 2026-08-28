# Handoff source contract

The stable anchors to author lab content, screenshots, and validation steps against.
Everything here is verified in source on this branch (`governed`, DAT416). Where a number
can be recomputed, the command that recomputes it is given instead of a copy: a hand-kept
number is how the eighteen-versus-three policy drift survived for weeks.

Read `CLAUDE.md` first for the repository contract and the participant/maintainer modes.

## Two tool counts, and why both are correct

| number | meaning | source |
|---|---|---|
| **17** | the canonical tool vocabulary. Every Gateway surface Lambda and every schema in `TOOL_SCHEMAS` covers all of them, and `/api/observatory/build-state` reports all of them. | `scripts/deploy/gateway_tool_schemas.py` |
| **15** | what this workshop iteration **publishes**. `issue_credit` and `get_ticket_history` are deferred: their governance is undecided, so a fresh provision must not expose them. | `WORKSHOP_DEFERRED_TOOLS` in the same module |

Conflating them produces a step that counts tools and gets the wrong answer. Recompute
both, plus the per-target split and the baseline Cedar, with:

```bash
python3 scripts/describe_workshop_publication.py
```

`schema_for(surface, workshop=...)` has **no default** on purpose. Publication paths pass
`workshop=True`; the Gateway vocabulary migration passes `workshop=False` because it needs
the full vocabulary to compute what it is deliberately not publishing.

## Baseline authorization on a fresh stack

Three policies, not one per tool:

| policy | effect | shape |
|---|---|---|
| `baseline_permit_workshop_tools` | permit | `action in [...]` over 13 explicit action ids. No wildcard, so a tool published later is denied by default. |
| `initiate_return_damaged_only` | permit | conditional on `context.input.reason == "damaged"` |
| `initiate_return_deny_other_reasons` | forbid | the complement |

`restock_inventory` is published **without** a baseline permit. Published and
unauthorized is a real Cedar DENY rather than a missing tool, which is what the operator
desk needs in order to show a refusal.

The Lab 4 identity condition (`principal.getTag("username")` bound to
`context.input.customer_id`) is **absent from the baseline on purpose**. A fresh stack
that shipped it would make Lab 4 step 3's DENY fire before the participant wrote
anything. `pellier/backend/tests/test_fresh_policy_set.py` owns this contract.

## Participant agent names, exact

    Search Agent · Personalization Agent · Pricing Agent · Inventory Agent
    Customer Service Agent

`Inventory Agent` is the Lab 1 exercise and reports `"exercise"` in build-state until it
is wired.

## Lab 1 edit points, the only safe edit sites

| file | markers |
|---|---|
| `pellier/backend/agents/inventory_agent.py` | `# === WORKSHOP · Inventory Agent · definition: START ===` / `: END ===` |
| `pellier/backend/services/agent_tools.py` | `# === WORKSHOP · Inventory Agent · check_inventory: START ===` / `: END ===` |

The separator is U+00B7. A participant searches the file for the string the guide quotes,
so an ASCII substitution breaks the only instruction that lane gives.

Five fields in the definition block: `_INVENTORY_AGENT_STUBBED`,
`_INVENTORY_SYSTEM_PROMPT_FOR_AGENT`, `_INVENTORY_MODEL_ID`, `_INVENTORY_MAX_TOKENS`,
`_INVENTORY_TOOLS`. No `temperature`; the configured Sonnet profile rejects it. The tool
body calls `BusinessLogic.check_inventory` through `_run_async`.

## Recovery paths

    solutions/waking-the-stock-keeper/agents/inventory_agent_solution.py
      -> pellier/backend/agents/inventory_agent.py
    solutions/closing-marcos-gap/services/agent_tools_check_inventory_solution.py
      -> pellier/backend/services/agent_tools.py
    solutions/the-concierge/policies/identity_match_forbid.cedar
      -> policies/workshop_identity_match_forbid.cedar

Directory names keep their historical form deliberately; the **file** names are canonical.
Both Lab 1 copies retain the marker regions, so a participant who takes the fallback can
still read what changed.

`pellier/backend/tests/test_workshop_marker_contract.py` asserts every anchor above from
the source side, including that the Lab 4 starter still holds `unless { false }` rather
than the answer.

## Proof endpoints

    GET  /api/observatory/build-state          {"agents": {...}, "tools": {...}} -> "shipped"|"exercise"
    GET  /api/observatory/readiness            10 checks; status ready|attention|not_ready
    GET  /api/observatory/executions[/{id}]    execution reconstruction, principal-scoped
    GET  /api/observatory/proof-board          the assembled proof view
    POST /api/observatory/tools/discover       Aurora semantic tool-registry search
    GET  /api/operator/capabilities            live governance truth per capability
    GET  /api/operator/reviews[/{id}]          review + four assurance axes + execution receipt
    POST /api/operator/reviews/{id}/confirm    human decision, then execution

`POST /api/observatory/tools/discover` is an Aurora search, **not** MCP `list_tools`. MCP
tool discovery is reached only through `MCPClient(streamablehttp_client(...))` with a
Cognito bearer token; no HTTP endpoint proxies it.

## Evidence surfaces, and the question each answers

    pellier.approvals            was it authorized by a human, and against which turn
    pellier.execution_receipts   what the policy, Aurora and evidence verdicts were,
                                 one row per attempt, append-only
    pellier.tool_audit           which tools actually ran. Absent on a Cedar DENY, by
                                 design: that absence is the evidence
    pellier.write_operations     the idempotency claim; completed = applied exactly once
    pellier.operator_episodes    derived memory of terminal outcomes
    pellier.observatory_spans    OTEL spans. This is the canonical span table name;
                                 migration 027 converges the retired one

An ALLOW never proves execution occurred. Keep policy, execution and data evidence
separate.

## Reset

```bash
PELLIER_REPO=<repo> PELLIER_RESET_SKIP_AGENTCORE=1 bash scripts/reset-governed-workshop.sh
./pellier/backend/.venv/bin/python scripts/reset_memory_runtime.py --apply
```

Aurora alone is not enough. AgentCore Memory holds actor-scoped `USER_PREFERENCE`
records, and a new session id does not isolate an actor-scoped namespace, so an operator
who ran engineering turns leaves preferences that the next first turn recalls.
`reset_memory_runtime.py` is dry-run by default and preserves the three seeded persona
actors.

### Expected baseline after reset

Derived from the canonical seed contract (migrations plus `seed_pellier_catalog.py`), not
from a live count minus known rows:

    customers 17 · orders 66 · product_catalog 1000 · warehouses 3
    warehouse_inventory 120 · inventory_ledger 120 · customer_episodic_seed 9
    return_policies 5 · tools 15 · principal_customers 3
    returns 1 · tool_audit 1 · governed_receipts 1   (all three: the migration 010 forensic incident)
    store_credits 1 (CUST-SARAH) · support_tickets 3
    approvals 0 · conversations 0 · messages 0 · operator_episodes 0
    execution_receipts 0 · write_operations 0 · semantic_cache 0 · observatory_spans 0

`reconcile_inventory()` returns no rows on a clean baseline.

**Do not author against serial ids.** Reset uses `RESTART IDENTITY`, so review and return
ids restart from 1 on every reset. Screenshot a review by its content, not `#40`.

## Canonical personas and clients

    Marco   CUST-MARCO    maison      7 orders
    Anna    CUST-ANNA     circle      5 orders
    Theo    CUST-THEO     registered  4 orders
    Jessica CUST-JESSICA  circle      5 orders   ticket asserts a return with no row (deliberate)
    Rachel  CUST-RACHEL   registered  3 orders
    Amara   CUST-AMARA    maison      5 orders   no principal_customers mapping (deliberate RLS fixture)

The three personas are shoppers with Cognito users; the remaining twelve are
operator-side client records only. A client id must never resolve as a signed-in shopper.

## Product assets

Catalog imagery is a release asset, not a local convenience. A file on disk that git does
not track renders as a broken image in a clean clone while looking finished locally.

```bash
python3 scripts/audit_product_assets.py --table
python3 scripts/audit_product_assets.py --print-untracked | xargs git add
```

The contract: a committed 4:5 PNG master per SKU, plus `-480` and `-960` derivatives in
both WebP and AVIF, all tracked. Hero and landing slots are intentionally landscape and
some publish a 1600 variant; `scripts/derive_product_variants.py` treats the widths a
master already publishes as its contract and refuses to crop a master that fails the 4:5
rule. `pellier/backend/tests/test_product_asset_tracking.py` fails on an untracked
required asset, a half-tracked srcset, or a fixture path that resolves to nothing.

Client and persona portraits are composed at runtime from a slug list in
`personaPhotos.ts`, so no literal exists to grep. That list is parsed by the audit; adding
a client without a portrait fails rather than resolving to an initial circle.

## Intentional historical names, do not "fix"

    process_return_idempotent            Postgres function, stable identifier
    solutions/waking-the-stock-keeper/   recovery path directory
    _MIGRATION_TOOL_ALIASES              Lambda dispatch compatibility, marked TEMPORARY
    migration 002 ALTER TABLE, 027       one-time convergence of an existing cluster

## Validation gates

```bash
cd pellier/backend && python -m pytest -q
cd pellier/frontend && npm test -- --run && npm run type-check && npm run lint && npm run build
python3 scripts/audit_product_assets.py
python3 scripts/describe_workshop_publication.py
git diff --check
find scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

None of these need AWS. Anything that does is called out where it appears; a green suite
is not evidence that a live environment matches this source.
