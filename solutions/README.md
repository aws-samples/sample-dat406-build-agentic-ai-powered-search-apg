# Governed Workshop Reference Implementations

These files are facilitator recovery paths and readable reference implementations. A participant who uses a reference still runs the same live proof.

## Lab 1: Build & Trace

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

After copying, both `/api/atelier/build-state` markers must read `shipped`. Replay Marco and query the uniquely keyed `floor_check` row from `pellier.tool_audit`.

## Lab 2: Retrieval Quality

If the live comparison endpoint stalls, use:

```bash
sed -n '1,120p' solutions/retrieval-eval/reference-output.txt
```

The reference supports the quality, latency, and cost decision. It does not prove the participant's live endpoint passed.

## Lab 3: Managed Execution & Audit

The managed Memory, Runtime, Gateway, and JWT path has no local substitute. Move a participant to a ready environment when that proof fails.

The forensic SQL is deterministic:

```bash
psql -v ON_ERROR_STOP=1 \
  -f solutions/the-ledger/sql/forensic_incident.sql
```

It joins `governed_receipts` to `tool_audit` and resolves the authenticated Marco principal against the Theo customer named in tool input.

## Lab 4: Govern Actions

Copy the identity-aware Cedar rule after one failed validation:

```bash
cp solutions/the-concierge/policies/identity_match_forbid.cedar \
  policies/workshop_identity_match_forbid.cedar

python3 scripts/deploy/workshop_policy_rule.py --rule identity_match \
  --cedar-file policies/workshop_identity_match_forbid.cedar \
  validate
```

The participant must still apply the rule, prove Marco-for-Theo DENY, prove Theo-for-Theo ALLOW, inspect both receipts, and reset the participant policy.

## Bootstrap Reference

The one-hour builders format pre-applies selected reference files. The governed format leaves the Stock Keeper definition and `floor_check` body incomplete for Lab 1. `scripts/bootstrap-labs.sh` is the source of truth for that branch-specific behavior.

The remaining files under `solutions/` mirror production services or provide test/recovery fixtures. They are not additional workshop labs.
