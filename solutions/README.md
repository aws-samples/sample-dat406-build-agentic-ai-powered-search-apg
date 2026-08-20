# Governed Workshop Reference Implementations

These files are facilitator recovery paths and readable reference implementations. A participant who uses a reference still runs the same live proof.

## Lab 1: Ground Answers in Live Data

Complete the Stock Keeper definition:

```bash
cp solutions/waking-the-stock-keeper/agents/stock_keeper_solution.py \
  pellier/backend/agents/stock_keeper.py
```

Wire the `floor_check` body:

```bash
cp solutions/closing-marcos-gap/services/agent_tools_floor_check_solution.py \
  pellier/backend/services/agent_tools.py
```

After copying, both `/api/observatory/build-state` markers must read `shipped`. Replay Marco and query the uniquely keyed `floor_check` row from `pellier.tool_audit`.

## Lab 2: Design the Retrieval Strategy

If the live comparison endpoint stalls, use:

```bash
sed -n '1,120p' solutions/retrieval-eval/reference-output.txt
```

The reference supports the quality, latency, and cost decision. It does not prove the participant's live endpoint passed.

## Lab 3: Run Agents in a Managed Runtime

The managed Memory, Runtime, Gateway, and JWT path has no local substitute. Move a participant to a ready environment when that proof fails.

The forensic SQL is deterministic:

```bash
psql -v ON_ERROR_STOP=1 \
  -f solutions/the-ledger/sql/forensic_incident.sql
```

It joins `governed_receipts` to `tool_audit` and resolves the authenticated Marco principal against the Theo customer named in tool input.

## Lab 4: Govern and Trace Agent Actions

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

The participant must still prove Marco-for-Theo DENY, prove Theo-for-Theo
ALLOW, inspect both receipts, and remove the participant policy through the CLI.

## Bootstrap Reference

The one-hour builders format pre-applies selected reference files. The governed format leaves the Stock Keeper definition and `floor_check` body incomplete for Lab 1. `scripts/bootstrap-labs.sh` is the source of truth for that branch-specific behavior.

The remaining files under `solutions/` mirror production services or provide test/recovery fixtures. They are not additional workshop labs.
