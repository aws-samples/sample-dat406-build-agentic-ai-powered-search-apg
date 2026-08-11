# Governed fresh-account release probe

Run this checklist on a newly provisioned Workshop Studio environment as the
participant user. It is the live complement to the repository test suite.

## 1. Prerequisites

```bash
cd /workshop/sample-pellier-agentic-search-apg
test "$(node --version | sed 's/^v//' | cut -d. -f1)" -ge 20
npx -y @aws/agentcore@0.26.0 --version
test "$(aws configure get region)" = "us-east-1"
```

## 2. Release gate

```bash
python3 scripts/check_model_access.py
bash scripts/health-gate.sh
jq -e '
  .status == "ready" and
  .verification.targets_attached == true and
  .verification.gateway_tool_count == 15 and
  .verification.memory_seeded == true and
  .verification.live_policy_allow == true and
  .verification.live_policy_deny == true and
  .verification.runtime_invoke_smoke.rail == "gateway-mcp"
' /tmp/pellier-agentcore-managed.json
```

## 3. CLI-owned resources

```bash
PROJECT=/workshop/sample-pellier-agentic-search-apg/.agentcore-project/pellier
cd "$PROJECT"
npx -y @aws/agentcore@0.26.0 validate --json
npx -y @aws/agentcore@0.26.0 status --json

jq -e '
  .managedBy == "CDK" and
  (.runtimes | length) == 1 and
  (.memories | length) == 1 and
  (.agentCoreGateways[0].targets | length) == 4 and
  (.policyEngines | length) == 1 and
  (.runtimes[0] | has("executionRoleArn") | not)
' agentcore/agentcore.json
```

## 4. Managed Runtime and Gateway

```bash
cd /workshop/sample-pellier-agentic-search-apg
source ~/pellier-token.sh marco

python3 scripts/deploy/test_gateway_tools.py \
  --gateway-url "$AGENTCORE_GATEWAY_URL" \
  --token "$PELLIER_TOKEN"

cd .agentcore-project/pellier
npx -y @aws/agentcore@0.26.0 invoke \
  --runtime pellier_orchestrator \
  --prompt "Find a linen shirt for a warm-weather trip. Do not mutate data." \
  --bearer-token "$PELLIER_TOKEN" \
  --session-id "release-probe-$(date +%s)-0000000000000001" \
  --json
cd ../..
```

The Gateway probe must discover exactly 15 tools. The Runtime response must
include `rail=gateway-mcp`.

## 5. Participant policy path

Complete Lab 4 exactly as written. Require all three outcomes:

1. Marco acting for Theo is `DENY` with `absence_verified=true` and no
   `tool_audit` row.
2. Theo acting for Theo is `ALLOW` with a linked `tool_audit` row.
3. `agentcore remove policy`, `agentcore validate`, and `agentcore deploy`
   restore the baseline policy set.

## 6. Reset

```bash
cd /workshop/sample-pellier-agentic-search-apg
bash scripts/reset-governed-workshop.sh
bash scripts/health-gate.sh
```

Do not publish a source revision until this probe and Workshop Studio release
validation both pass.
