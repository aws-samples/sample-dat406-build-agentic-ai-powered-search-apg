# Governed Workshop Reference Implementations

These files are facilitator recovery paths and readable reference implementations. A participant who uses a reference still runs the same live proof.

## Lab 1: Build a PostgreSQL-Grounded Agent

Complete the Inventory Agent definition:

```bash
cp solutions/waking-the-stock-keeper/agents/inventory_agent_solution.py \
  pellier/backend/agents/inventory_agent.py
```

Wire the `check_inventory` body:

```bash
cp solutions/closing-marcos-gap/services/agent_tools_check_inventory_solution.py \
  pellier/backend/services/agent_tools.py
```

After copying, both `/api/observatory/build-state` markers must read `shipped`. Replay Marco and query the uniquely keyed `check_inventory` row from `pellier.tool_audit`.

## 02 MEASURE HYBRID RETRIEVAL — Search, Filters, and Trade-offs

If the live comparison endpoint stalls, use:

```bash
sed -n '1,120p' solutions/retrieval-eval/reference-output.txt
```

The required Lab 2 build is the psql RRF worksheet. If the room reaches its
cut line, restore only that bounded expression:

```bash
cp solutions/the-quiet-search/sql/lab-2-rrf-solution.sql \
  workshop/lab-2-rrf.sql
```

The reference supports the quality, latency, and cost decision. It does not prove the participant's live endpoint passed.

## 03 OPERATE THE MANAGED AGENT PATH — Runtime, Gateway, Memory, and Trace

The managed Memory, Runtime, Gateway, and JWT path has no local substitute. Move a participant to a ready environment when that proof fails.

The forensic SQL is deterministic:

```bash
psql -v ON_ERROR_STOP=1 \
  -f solutions/the-ledger/sql/forensic_incident.sql
```

Lab 3 also has a bounded OpenTelemetry acceptance contract. Its recovery copy
does not provision or change managed resources:

```bash
cp solutions/the-ledger/observability/lab-3-otel-contract-solution.jq \
  workshop/lab-3-otel-contract.jq
```

It joins `governed_receipts` to `tool_audit` and resolves the authenticated Marco principal against the Theo customer named in tool input.

## 04 GOVERN AND PROVE ACTIONS — Human Decision, Policy, Database, and Receipts

Copy the identity-aware Cedar rule after one failed validation, then add it
through the same pinned AgentCore CLI used by the workshop:

```bash
REPO=/workshop/sample-pellier-agentic-search-apg
PROJECT="$REPO/.agentcore-project/pellier"
cp "$REPO/solutions/the-concierge/policies/identity_match_forbid.cedar" \
  "$REPO/policies/workshop_identity_match_forbid.cedar"

cd "$PROJECT"
npx -y @aws/agentcore@0.26.0 add policy \
  --name workshop_identity_match_forbid \
  --engine pellier_policy_engine \
  --source "$REPO/policies/workshop_identity_match_forbid.cedar" \
  --validation-mode FAIL_ON_ANY_FINDINGS \
  --enforcement-mode ACTIVE \
  --json
npx -y @aws/agentcore@0.26.0 validate --json
npx -y @aws/agentcore@0.26.0 deploy --yes --json
```

The participant must still prove Marco-for-Jessica DENY, prove Jessica-for-Jessica
ALLOW, inspect both receipts, and remove the participant policy through the CLI.

## Bootstrap Reference

The one-hour builders format pre-applies selected reference files. The governed format leaves the Inventory Agent definition and `check_inventory` body incomplete for Lab 1. `scripts/bootstrap-labs.sh` is the source of truth for that branch-specific behavior.

The remaining files under `solutions/` mirror production services or provide test/recovery fixtures. They are not additional workshop labs.
