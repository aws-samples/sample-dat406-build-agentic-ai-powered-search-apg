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
#   2. Catalog row count == expected (1,000 by default: 60 curated + 940 archive)
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
#  10. Provisioning receipt proves managed resources, Runtime smoke, and traces
#  11. Operator group authorizes the desk, and no shopper is in it
#
# In WORKSHOP_FORMAT=governed, all managed AgentCore checks are required because
# Labs 3 and 4 and the session abstract depend on them. The separate one-hour
# builders format retains warning-only managed checks.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${PELLIER_REPO:-/workshop/sample-pellier-agentic-search-apg}"
ENV_FILE="${REPO}/.env"
EXPECTED_CATALOG="${EXPECTED_CATALOG:-1000}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/api/health}"

GREEN='\033[32m'; RED='\033[31m'; YEL='\033[33m'; NC='\033[0m'
pass() { printf "  ${GREEN}✓ PASS${NC}  %s\n" "$1"; }
fail() { printf "  ${RED}✗ FAIL${NC}  %s\n" "$1"; }
warn() { printf "  ${YEL}• WARN${NC}  %s\n" "$1"; }

ok=true

# Load configuration as dotenv data, never as executable shell. A fresh
# Workshop Studio root `.env` is shell-safe today, but local and recovery
# paths also read backend dotenv files where generated passwords may not be.
# Keeping this entrypoint parser-based makes the health result about service
# readiness, not punctuation in a secret.
DOTENV_HELPER="${SCRIPT_DIR}/lib/dotenv.sh"
if [[ ! -r "$DOTENV_HELPER" ]]; then
  fail "Missing dotenv parser: $DOTENV_HELPER"
  exit 1
fi
# shellcheck source=lib/dotenv.sh
source "$DOTENV_HELPER"
if [[ -f "$ENV_FILE" ]]; then
  pellier_load_dotenv "$ENV_FILE"
elif [[ -f "${REPO}/pellier/backend/.env" ]]; then
  ENV_FILE="${REPO}/pellier/backend/.env"
  pellier_load_dotenv "$ENV_FILE"
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
# so /api/health alone can read green while Pellier and Pellier Observatory are blank.
# Check that / returns HTML, not that JSON note: this is what a participant
# sees in the browser. (Root cause when it fails: the frontend build failed,
# usually `npm run build` in pellier/frontend; recover with `rebuild-frontend`.)
root_body="$(curl -fs --max-time 5 "${ROOT_URL:-http://localhost:8000/}" 2>/dev/null || true)"
if echo "$root_body" | grep -qiE '<!doctype html|<div id="root"'; then
  pass "Frontend SPA built and served at / (Pellier + Pellier Observatory render)"
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
if [[ "$wh_n" == "120" ]]; then
  pass "Warehouse inventory has exactly 120 curated rows"
else
  fail "Warehouse inventory row count is ${wh_n:-none}, expected exactly 120"
  ok=false
fi

inventory_drift="$(_psql "
/* inventory_consistency_check */
SELECT count(*)
  FROM pellier.product_catalog pc
 WHERE pc.\"productId\" ~ '^[0-9]+$'
   AND pc.\"productId\"::int BETWEEN 1 AND 40
   AND pc.quantity <> (
       SELECT COALESCE(sum(wi.quantity), 0)
         FROM pellier.warehouse_inventory wi
        WHERE wi.product_id = pc.\"productId\"
   );" || echo '')"
if [[ "$inventory_drift" == "0" ]]; then
  pass "Catalog quantity matches warehouse aggregate for all 40 curated products"
else
  fail "Catalog/warehouse inventory drift detected (${inventory_drift:-unknown} products)"
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
  if [[ "${order_n:-0}" =~ ^[0-9]+$ ]] && (( order_n >= 20 )); then
    pass "Orders queryable and fully seeded ($order_n rows)"
  else
    fail "Orders incomplete or missing (got: ${order_n:-none}, expected at least 20)"
    ok=false
  fi

  audit_n="$(_psql "SELECT count(*) FROM pellier.tool_audit WHERE caller IN ('agent', 'gateway') AND jsonb_typeof(args) = 'object' AND args <> '{}'::jsonb AND jsonb_typeof(result) = 'object' AND result <> '{}'::jsonb;" || echo '')"
  if [[ "${audit_n:-0}" =~ ^[0-9]+$ ]] && (( audit_n > 0 )); then
    pass "JSONB tool execution ledger queryable ($audit_n structured rows)"
  else
    fail "JSONB tool execution ledger has no completed agent or Gateway actions (got: ${audit_n:-none})"
    ok=false
  fi

  retrieval_receipts_table="$(_psql "SELECT to_regclass('pellier.retrieval_receipts');" || echo '')"
  if [[ "$retrieval_receipts_table" == "pellier.retrieval_receipts" ]]; then
    pass "Retrieval receipt schema is installed"
  else
    fail "Retrieval receipt schema missing. Apply scripts/migrations/012_retrieval_receipts.sql."
    ok=false
  fi

  governed_turn_receipts_table="$(_psql "SELECT to_regclass('pellier.governed_turn_receipts');" || echo '')"
  if [[ "$governed_turn_receipts_table" == "pellier.governed_turn_receipts" ]]; then
    pass "Governed turn receipt schema is installed"
  else
    fail "Governed turn receipt schema missing. Apply scripts/migrations/014_governed_turn_receipts.sql."
    ok=false
  fi

  commerce_receipts_table="$(_psql "SELECT to_regclass('pellier.commerce_receipts');" || echo '')"
  commerce_payment_events_table="$(_psql "SELECT to_regclass('pellier.commerce_payment_events');" || echo '')"
  if [[ "$commerce_receipts_table" == "pellier.commerce_receipts" ]] \
      && [[ "$commerce_payment_events_table" == "pellier.commerce_payment_events" ]]; then
    pass "Proof-carrying commerce schema is installed"
  else
    fail "Proof-carrying commerce schema missing. Apply scripts/migrations/015_proof_carrying_commerce.sql."
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

gateway_identifier="${AGENTCORE_GATEWAY_ARN:-${GATEWAY_ARN:-}}"
gateway_identifier="${gateway_identifier##*/}"
policy_mode=""
if [[ -n "$gateway_identifier" ]] && command -v aws >/dev/null 2>&1; then
  policy_mode="$(aws bedrock-agentcore-control get-gateway \
    --gateway-identifier "$gateway_identifier" \
    --region "${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}" \
    --query 'policyEngineConfiguration.mode' \
    --output text 2>/dev/null || true)"
fi
if [[ "$policy_mode" == "ENFORCE" ]]; then
  pass "Gateway Policy is currently in ENFORCE mode"
else
  managed_missing "Gateway Policy mode is ${policy_mode:-unavailable}, expected ENFORCE"
fi

# 10. Structured provisioning receipt. This is stronger than checking env vars:
# it proves all Gateway targets were attached, Policy attached successfully, the
# authenticated Runtime smoke returned through Gateway MCP, the Runtime payload
# log group uses a customer-managed KMS key with bounded retention, and unified
# telemetry delivered agent/model/tool spans, redacted tool I/O, and step latency.
managed_receipt="${AGENTCORE_MANAGED_OUTPUT_JSON:-/tmp/pellier-agentcore-managed.json}"
receipt_validator="$SCRIPT_DIR/validate_agentcore_receipt.py"
if [[ -f "$managed_receipt" ]] && [[ -f "$receipt_validator" ]] \
    && command -v python3 >/dev/null 2>&1; then
  if receipt_error="$(python3 "$receipt_validator" "$managed_receipt" 2>&1)"; then
    pass "Managed receipt proves AgentCore resources, Policy ALLOW/DENY, gateway-mcp Runtime smoke, encrypted bounded Runtime logs, and sanitized trace delivery"
  else
    managed_missing "Managed provisioning receipt is incomplete or degraded: ${receipt_error:-unknown contract failure}"
  fi
else
  managed_missing "Managed provisioning receipt, validator, or python3 unavailable: $managed_receipt"
fi

echo "------------------------------------------------------------"
# 11. The operator authorization group.
#
# The Pellier Operator desk is authorized by membership in one Cognito group. Two failure
# modes, and both must be loud rather than latent:
#
#   group missing / operator not a member  -> the desk refuses every caller with 403
#   a SHOPPER is in the group              -> authentication is authorization again
#
# The second is the finding this check exists for. `require_operator` used to accept any
# valid token, so `marco` could confirm, decline and execute any review. A shopper
# accidentally added to the group restores exactly that, and nothing else would notice.
if [[ -n "${COGNITO_USER_POOL_ID:-${COGNITO_POOL_ID:-}}" ]]; then
  operator_pool="${COGNITO_USER_POOL_ID:-${COGNITO_POOL_ID:-}}"
  operator_group="pellier-operators"
  operator_user="${PELLIER_OPERATOR_USERNAME:-operator}"
  in_group() {
    aws cognito-idp admin-list-groups-for-user \
      --user-pool-id "$operator_pool" --username "$1" \
      --region "${AWS_REGION:-us-east-1}" \
      --query "Groups[?GroupName=='${operator_group}'].GroupName" \
      --output text 2>/dev/null | grep -q "$operator_group"
  }
  if in_group "$operator_user"; then
    pass "Operator group ${operator_group} authorizes ${operator_user}"
  else
    managed_missing "${operator_user} is not in ${operator_group} — the Operator desk refuses every caller with 403"
  fi
  shopper_in_group=""
  for shopper in marco anna theo; do
    if in_group "$shopper"; then
      shopper_in_group="$shopper_in_group $shopper"
    fi
  done
  if [[ -n "$shopper_in_group" ]]; then
    fail "shopper(s) in ${operator_group}:${shopper_in_group} — a valid shopper token would authorize the desk"
    ok=false
  else
    pass "No shopper is in ${operator_group}"
  fi
else
  managed_missing "No Cognito pool id — operator group authorization is unverified"
fi

if $ok; then
  printf "${GREEN}● READY${NC} — all required checks passed.\n"
  exit 0
else
  printf "${RED}● NOT READY${NC} — see failed checks above.\n"
  exit 1
fi
