#!/usr/bin/env bash
# =============================================================================
# health-gate.sh — one-shot post-boot readiness check for the workshop
# =============================================================================
# Prints one PASS/FAIL line per check and a single overall verdict. Safe to
# re-run any time (read-only). Intended to run at the end of bootstrap and to
# be available to facilitators as the `health` alias.
#
# Checks:
#   1. Backend /api/health is green (DB connected)
#   2. Catalog row count == expected (1,000 by default: 40 curated + 960 archive)
#   3. Warehouse inventory present (~120 rows)
#   3b. Governed customer, order, and JSONB audit evidence present
#   4. node --version >= 20                       (required for governed format;
#      warning for builders format; ROOT CAUSE diagnostic:
#      the @aws/agentcore CLI needs Node 20; on Node 18 every agentcore command
#      silently no-ops, so Runtime/Gateway/Policy never deploy and checks 6-7
#      below read empty. Surfacing the Node version turns "endpoints empty, why?"
#      into a named cause.)
#   5. Required Bedrock model preflight passed     (required)
#   6. AGENTCORE_MEMORY_ID set and SDK-backed
#   7. AGENTCORE_RUNTIME_ENDPOINT set and enabled
#   8. AGENTCORE_GATEWAY_URL + ARN set
#   9. AGENTCORE_POLICY_ENGINE_ID set
#  10. Provisioning receipt proves targets, Policy, and gateway-mcp Runtime smoke
#
# In WORKSHOP_FORMAT=governed, all managed AgentCore checks are required because
# Core Lab 4 and the session abstract depend on them. The separate one-hour
# builders format retains warning-only managed checks.
# =============================================================================
set -uo pipefail

REPO="${PELLIER_REPO:-/workshop/sample-pellier-agentic-search-apg}"
ENV_FILE="${REPO}/.env"
EXPECTED_CATALOG="${EXPECTED_CATALOG:-1000}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/api/health}"

GREEN='\033[32m'; RED='\033[31m'; YEL='\033[33m'; NC='\033[0m'
pass() { printf "  ${GREEN}✓ PASS${NC}  %s\n" "$1"; }
fail() { printf "  ${RED}✗ FAIL${NC}  %s\n" "$1"; }
warn() { printf "  ${YEL}• WARN${NC}  %s\n" "$1"; }

ok=true

# Load env (safe: set -a + source, no word-splitting)
if [[ -f "$ENV_FILE" ]]; then
  set -a; # shellcheck source=/dev/null
  source "$ENV_FILE"; set +a
fi

managed_required=false
if [[ "${WORKSHOP_FORMAT:-builders}" == "governed" ]]; then
  managed_required=true
fi

managed_missing() {
  local message="$1"
  if $managed_required; then
    fail "$message"
    ok=false
  else
    warn "$message"
  fi
}

echo "Pellier health gate — $(date '+%H:%M:%S')"
echo "------------------------------------------------------------"

# 1. Backend health
health_json="$(curl -fs --max-time 5 "$HEALTH_URL" 2>/dev/null || true)"
if echo "$health_json" | grep -q '"status".*"healthy"'; then
  pass "Backend /api/health is healthy"
else
  fail "Backend /api/health not healthy (got: ${health_json:-no response})"
  ok=false
fi

# 1b. Frontend SPA actually built + served. The backend serves /api even when
# the Vite bundle is absent (it returns a JSON "bundle not found" note at /),
# so /api/health alone can read green while the Boutique + Atelier are blank.
# Check that / returns HTML, not that JSON note: this is what a participant
# sees in the browser. (Root cause when it fails: the frontend build failed,
# usually `npm run build` in pellier/frontend; recover with `rebuild-frontend`.)
root_body="$(curl -fs --max-time 5 "${ROOT_URL:-http://localhost:8000/}" 2>/dev/null || true)"
if echo "$root_body" | grep -qiE '<!doctype html|<div id="root"'; then
  pass "Frontend SPA built and served at / (Boutique + Atelier render)"
else
  fail "Frontend SPA not served at / - bundle missing (got: ${root_body:0:80}). Run 'rebuild-frontend' (builds pellier/frontend, restarts pellier)."
  ok=false
fi

# psql helper using env creds
_psql() {
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" \
    -X -q -tAc "$1" 2>/dev/null
}

# 2. Catalog count
catalog_n="$(_psql 'SELECT count(*) FROM pellier.product_catalog;' || echo '')"
if [[ "$catalog_n" == "$EXPECTED_CATALOG" ]]; then
  pass "Catalog seeded ($catalog_n products)"
else
  fail "Catalog count is '${catalog_n:-unknown}', expected $EXPECTED_CATALOG"
  ok=false
fi

# 3. Warehouse inventory
wh_n="$(_psql 'SELECT count(*) FROM pellier.warehouse_inventory;' || echo '')"
if [[ "${wh_n:-0}" =~ ^[0-9]+$ ]] && (( wh_n > 0 )); then
  pass "Warehouse inventory present ($wh_n rows)"
else
  fail "Warehouse inventory empty or missing (got: ${wh_n:-none})"
  ok=false
fi

# 3b. Governed forensic receipt seed
receipt_n="$(_psql "SELECT count(*) FROM pellier.governed_receipts WHERE session_id = 'gateway-marco-for-theo-incident';" || echo '')"
if [[ "${receipt_n:-0}" =~ ^[0-9]+$ ]] && (( receipt_n == 1 )); then
  pass "Governed forensic receipt seeded"
else
  fail "Governed forensic receipt missing (got: ${receipt_n:-none}). Run 'reset-governed'."
  ok=false
fi

# 3c. Governed operational data. These tables are part of the DAT416 contract,
# not optional demo context: the labs query customer identity and prior orders.
if $managed_required; then
  customer_n="$(_psql 'SELECT count(*) FROM pellier.customers;' || echo '')"
  if [[ "${customer_n:-0}" =~ ^[0-9]+$ ]] && (( customer_n > 0 )); then
    pass "Customer records queryable ($customer_n rows)"
  else
    fail "Customer records empty or missing (got: ${customer_n:-none})"
    ok=false
  fi

  order_n="$(_psql 'SELECT count(*) FROM pellier.orders;' || echo '')"
  if [[ "${order_n:-0}" =~ ^[0-9]+$ ]] && (( order_n > 0 )); then
    pass "Orders queryable ($order_n rows)"
  else
    fail "Orders empty or missing (got: ${order_n:-none})"
    ok=false
  fi

  audit_n="$(_psql "SELECT count(*) FROM pellier.tool_audit WHERE caller IN ('agent', 'gateway') AND jsonb_typeof(args) = 'object' AND args <> '{}'::jsonb AND jsonb_typeof(result) = 'object' AND result <> '{}'::jsonb;" || echo '')"
  if [[ "${audit_n:-0}" =~ ^[0-9]+$ ]] && (( audit_n > 0 )); then
    pass "JSONB tool execution ledger queryable ($audit_n structured rows)"
  else
    fail "JSONB tool execution ledger has no completed agent or Gateway actions (got: ${audit_n:-none})"
    ok=false
  fi
fi

# 4. Node version (warn — root-cause diagnostic for the managed pillars below).
# The @aws/agentcore CLI is Node-based and requires Node >= 20; on Node 18 it
# crashes at module load (regex `v`/unicodeSets flag) BEFORE doing any work, so
# `agentcore deploy` silently produces nothing and the Runtime/Gateway/Policy
# endpoints below stay empty. We surface the version here so an empty
# AGENTCORE_RUNTIME_ENDPOINT (check 6) reads as a consequence, not a mystery.
node_ver="$(node --version 2>/dev/null || true)"
node_major="$(echo "$node_ver" | sed 's/^v//' | cut -d. -f1)"
if [[ "$node_major" =~ ^[0-9]+$ ]] && (( node_major >= 20 )); then
  pass "Node $node_ver (>= 20 — @aws/agentcore CLI can run)"
else
  managed_missing "Node ${node_ver:-not found} (< 20) — the @aws/agentcore CLI cannot run, so Runtime/Gateway/Policy cannot deploy. Recover: 'sudo dnf remove -y nodejs && curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash - && sudo dnf install -y --allowerasing nodejs' then re-run scripts/deploy/deploy_all.sh."
fi

# 5. Required Bedrock model access
if [[ "${BEDROCK_MODEL_ACCESS_READY:-}" == "true" ]]; then
  pass "Required Bedrock model-access preflight passed"
else
  fail "Required Bedrock model-access preflight did not pass"
  ok=false
fi

# 6. AgentCore Memory id and live SDK path
if [[ -n "${AGENTCORE_MEMORY_ID:-}" ]]; then
  pass "AGENTCORE_MEMORY_ID set"
else
  managed_missing "AGENTCORE_MEMORY_ID empty — managed Memory unavailable"
fi

memory_json="$(curl -fs --max-time 5 "${MEMORY_STATUS_URL:-http://localhost:8000/api/agentcore/memory/status}" 2>/dev/null || true)"
if echo "$memory_json" | grep -q '"live"[[:space:]]*:[[:space:]]*true' \
    && echo "$memory_json" | grep -q '"source"[[:space:]]*:[[:space:]]*"agentcore-sdk"' \
    && echo "$memory_json" | grep -q '"resource_status"[[:space:]]*:[[:space:]]*"ACTIVE"'; then
  pass "AgentCore Memory resource is ACTIVE through the SDK path"
else
  managed_missing "AgentCore Memory is not ACTIVE through the SDK path (got: ${memory_json:-no response})"
fi

# 7. AgentCore Runtime endpoint and active backend switch
if [[ -n "${AGENTCORE_RUNTIME_ENDPOINT:-}" ]]; then
  pass "AGENTCORE_RUNTIME_ENDPOINT set"
else
  managed_missing "AGENTCORE_RUNTIME_ENDPOINT empty — managed Runtime unavailable"
fi
if [[ "${USE_AGENTCORE_RUNTIME:-false}" == "true" ]]; then
  pass "USE_AGENTCORE_RUNTIME=true"
else
  managed_missing "USE_AGENTCORE_RUNTIME is not true — /api/agent/chat would not use managed Runtime"
fi

# 8. AgentCore Gateway endpoint and ARN
if [[ -n "${AGENTCORE_GATEWAY_URL:-${MCP_GATEWAY_URL:-}}" ]]; then
  pass "AGENTCORE_GATEWAY_URL set"
else
  managed_missing "AGENTCORE_GATEWAY_URL empty — managed Gateway unavailable"
fi

if [[ -n "${AGENTCORE_GATEWAY_ARN:-${GATEWAY_ARN:-}}" ]]; then
  pass "AGENTCORE_GATEWAY_ARN set"
else
  managed_missing "AGENTCORE_GATEWAY_ARN empty — the Cedar apply helper cannot target the Gateway"
fi

# 9. Managed AgentCore Policy engine
if [[ -n "${AGENTCORE_POLICY_ENGINE_ID:-}" ]]; then
  pass "AGENTCORE_POLICY_ENGINE_ID set (managed Cedar policy attached)"
else
  managed_missing "AGENTCORE_POLICY_ENGINE_ID empty — managed Cedar enforcement unavailable. See /var/log/pellier-agentcore.log."
fi

# 10. Structured provisioning receipt. This is stronger than checking env vars:
# it proves all Gateway targets were attached, Policy attached successfully, and
# the authenticated Runtime smoke returned through the Gateway MCP rail.
managed_receipt="${AGENTCORE_MANAGED_OUTPUT_JSON:-/tmp/pellier-agentcore-managed.json}"
if [[ -f "$managed_receipt" ]] && command -v jq >/dev/null 2>&1; then
  if jq -e '
      .status == "ready"
      and .verification.targets_attached == true
      and .verification.prefixed_tools_verified == true
      and .verification.managed_policy_attached == true
      and .verification.runtime_control_plane_visible == true
      and .verification.authenticated_runtime_invoke_smoke == true
      and .verification.runtime_invoke_smoke.rail == "gateway-mcp"
    ' "$managed_receipt" >/dev/null 2>&1; then
    pass "Managed receipt proves Gateway tools, Policy, and gateway-mcp Runtime smoke"
  else
    managed_missing "Managed provisioning receipt is incomplete or degraded: $managed_receipt"
  fi
else
  managed_missing "Managed provisioning receipt missing or jq unavailable: $managed_receipt"
fi

echo "------------------------------------------------------------"
if $ok; then
  printf "${GREEN}● READY${NC} — all required checks passed.\n"
  exit 0
else
  printf "${RED}● NOT READY${NC} — see failed checks above.\n"
  exit 1
fi
