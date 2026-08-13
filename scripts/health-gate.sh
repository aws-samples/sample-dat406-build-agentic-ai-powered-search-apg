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
#   2. Catalog row count == expected (40)
#   3. Warehouse inventory present (~120 rows)
#   4. Required Bedrock model preflight passed
#
# Exit 0 only if the core one-hour path passes: backend, frontend, catalog,
# warehouse, and required model access.
# =============================================================================
set -uo pipefail

REPO="${PELLIER_REPO:-/workshop/sample-pellier-agentic-search-apg}"
ENV_FILE="${REPO}/.env"
EXPECTED_CATALOG="${EXPECTED_CATALOG:-40}"
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
# so /api/health alone can read green while the Boutique + Pellier Labs are blank.
# Check that / returns HTML, not that JSON note: this is what a participant
# sees in the browser. (Root cause when it fails: the frontend build failed,
# usually `npm run build` in pellier/frontend; recover with `rebuild-frontend`.)
root_body="$(curl -fs --max-time 5 "${ROOT_URL:-http://localhost:8000/}" 2>/dev/null || true)"
if echo "$root_body" | grep -qiE '<!doctype html|<div id="root"'; then
  pass "Frontend SPA built and served at / (Boutique + Pellier Labs render)"
else
  fail "Frontend SPA not served at / - bundle missing (got: ${root_body:0:80}). Run 'rebuild-frontend' (builds pellier/frontend, restarts pellier)."
  ok=false
fi

# psql helper using env creds
_psql() {
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" \
    -tAc "$1" 2>/dev/null
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

# 4. Required Bedrock model access
if [[ "${BEDROCK_MODEL_ACCESS_READY:-}" == "true" ]]; then
  pass "Required Bedrock model-access preflight passed"
else
  fail "Required Bedrock model-access preflight did not pass"
  ok=false
fi

echo "------------------------------------------------------------"
if $ok; then
  printf "${GREEN}● READY${NC} — all required checks passed.\n"
  exit 0
else
  printf "${RED}● NOT READY${NC} — see failed checks above.\n"
  exit 1
fi
