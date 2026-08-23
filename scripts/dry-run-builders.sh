#!/usr/bin/env bash
# =============================================================================
# dry-run-builders.sh — end-to-end simulation of the participant path
# =============================================================================
# Run this before a 100-person room to catch breakage the health gate can't:
# it exercises both required exercises plus the required agent wiring step.
#
#   1. Preconditions  — health gate must be READY
#   2. Exercise 1    — wire and directly verify floor_check while ungranted
#   3. Observe       — grant to Stock Keeper and assert the Strands path
#   4. Exercise 2    — run the exact four-strategy retrieval request
#   5. Action receipt — query the floor_check evidence row
#   6. SQL claims     — Beeswax 40/30/30 split (pin run-of-show number) +
#                       pg_trgm index presence/plan (migration 008 claim)
#
# This applies the floor_check solution and agent grant temporarily and creates
# the same floor_check audit evidence as a participant. It backs both edited
# files up and restores them on exit unless --keep is passed. Run it on a
# workshop environment, not a production database.
#
# Usage:
#   scripts/dry-run-builders.sh            # apply solution, test, restore stub
#   scripts/dry-run-builders.sh --keep     # leave the solution applied
# =============================================================================
set -uo pipefail

REPO="${PELLIER_REPO:-/workshop/sample-pellier-agentic-search-apg}"
ENV_FILE="${REPO}/.env"
BASE="${PELLIER_BASE_URL:-http://localhost:8000}"
TOOLS="${REPO}/pellier/backend/services/agent_tools.py"
STOCK_KEEPER="${REPO}/pellier/backend/agents/stock_keeper.py"
# The participant fills ONLY the floor_check body between the START/END markers
# in the already-in-place agent_tools.py (the builders pre-apply variant, which
# also defines shared application tools). The dry-run mirrors that exactly - it
# patches the body in place rather than swapping the whole file,
# so it can't drift from the live participant artifact. BODY is the canonical
# reference body (same one the required-path's paste-only escape hatch uses).
BODY="${REPO}/solutions/closing-marcos-gap/services/floor_check_tool_body.py"
KEEP=false
[[ "${1:-}" == "--keep" ]] && KEEP=true

GREEN='\033[32m'; RED='\033[31m'; YEL='\033[33m'; NC='\033[0m'
pass() { printf "  ${GREEN}✓${NC} %s\n" "$1"; }
fail() { printf "  ${RED}✗${NC} %s\n" "$1"; FAILED=true; }
info() { printf "  ${YEL}…${NC} %s\n" "$1"; }
# warn: review-worthy but non-fatal (does NOT set FAILED / block the gate).
warn() { printf "  ${YEL}•${NC} %s\n" "$1"; }
FAILED=false

# Load env (safe source)
[[ -f "$ENV_FILE" ]] && { set -a; source "$ENV_FILE"; set +a; }

_psql() {
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" -tAc "$1" 2>/dev/null
}

restore() {
  if ! $KEEP && [[ -f "${TOOLS}.dryrun.bak" ]]; then
    mv "${TOOLS}.dryrun.bak" "$TOOLS"
  fi
  if ! $KEEP && [[ -f "${STOCK_KEEPER}.dryrun.bak" ]]; then
    mv "${STOCK_KEEPER}.dryrun.bak" "$STOCK_KEEPER"
  fi
  if ! $KEEP; then
    info "Restored the original tool and Stock Keeper starter files."
  fi
}
trap restore EXIT

echo "════════════════════════════════════════════════════════════"
echo " Pellier workshop — end-to-end dry run"
echo " base=${BASE}  repo=${REPO}"
echo "════════════════════════════════════════════════════════════"

# --- 1. Preconditions -------------------------------------------------------
echo "[1/6] Preconditions (health gate)"
if bash "${REPO}/scripts/health-gate.sh" >/tmp/dryrun-health.log 2>&1; then
  pass "Health gate READY"
else
  fail "Health gate NOT READY — see /tmp/dryrun-health.log; aborting"
  cat /tmp/dryrun-health.log
  exit 1
fi

# Prove the installed CLI can invoke the pinned global Sonnet 4.6 profile with
# the participant instance role. This catches package, shell, model-access, and
# IAM drift before participants reach the recommended Lab 1 path.
#
# Model selection is left to ANTHROPIC_MODEL on purpose. Passing `--model sonnet`
# here would override the pin with the CLI's floating alias, which a current CLI
# resolves to a newer Sonnet than Workshop Studio accounts expose — so the check
# would either fail on a correctly provisioned account or pass while testing a
# model no participant uses. Bootstrap pins the same variable, so this now
# exercises the participant path.
claude_smoke="$(
  CLAUDE_CODE_USE_BEDROCK=1 \
  ANTHROPIC_MODEL=global.anthropic.claude-sonnet-4-6 \
  AWS_REGION="${AWS_REGION:-us-east-1}" \
  timeout 75 claude -p \
    "Reply with exactly PELLIER_CLAUDE_READY and no other text." \
    2>/tmp/dryrun-claude.err || true
)"
if [[ "$claude_smoke" == *"PELLIER_CLAUDE_READY"* ]]; then
  pass "Claude Code invoked Sonnet through Amazon Bedrock"
else
  fail "Claude Code Bedrock smoke failed — see /tmp/dryrun-claude.err"
fi

if python3 "${REPO}/scripts/builders_starter.py" \
    --repo "$REPO" verify --expect starter >/tmp/dryrun-starter-state.json; then
  pass "Both intentional starter gaps are installed"
else
  fail "Dry run must start from the verified tool + agent starter state"
  exit 1
fi

# --- 2. Exercise 1: apply and directly verify the tool ----------------------
# Fill ONLY the floor_check body between the START/END markers in the live
# agent_tools.py — exactly what the checked-in participant recovery does.
echo "[2/6] Exercise 1 - wire and directly verify floor_check"
if [[ ! -f "$BODY" ]]; then
  fail "Reference body file missing: $BODY"; exit 1
fi
if ! cp "$TOOLS" "${TOOLS}.dryrun.bak"; then
  fail "Could not back up agent_tools.py - refusing to patch in place"; exit 1
fi
if ! python3 "${REPO}/scripts/builders_starter.py" \
    --repo "$REPO" complete-tool >/tmp/dryrun-tool-solution.json; then
  fail "Could not patch floor_check body into agent_tools.py"; exit 1
fi
pass "Filled floor_check body in agent_tools.py (other tools untouched)"

info "Waiting 4s for uvicorn --reload to pick up the tool change..."
sleep 4
if uv run "${REPO}/scripts/builders_lab.py" \
    --base-url "$BASE" tool-check >/tmp/dryrun-tool-check.json; then
  pass "Direct tool check returned Brooklyn quantity and ship window"
else
  fail "Direct floor_check verification failed"; exit 1
fi
if uv run "${REPO}/scripts/builders_lab.py" \
    --base-url "$BASE" build-state \
    --expect-tool shipped --expect-agent exercise \
    >/tmp/dryrun-tool-wired-state.json; then
  pass "Intermediate state is tool shipped / agent ungranted"
else
  fail "Exercise 1 did not preserve the independent agent gap"; exit 1
fi

# --- 3. Grant the tool and observe the Strands path -------------------------
echo "[3/6] Trace Agent Actions - grant floor_check and invoke Stock Keeper"
if ! cp "$STOCK_KEEPER" "${STOCK_KEEPER}.dryrun.bak"; then
  fail "Could not back up stock_keeper.py - refusing to edit the agent grant"; exit 1
fi
if python3 "${REPO}/scripts/builders_starter.py" \
    --repo "$REPO" complete-agent >/tmp/dryrun-agent-grant.json; then
  pass "Granted floor_check to the Strands Stock Keeper"
else
  fail "Could not grant floor_check to Stock Keeper"; exit 1
fi
info "Waiting 4s for uvicorn --reload to pick up the agent grant..."
sleep 4

if uv run "${REPO}/scripts/builders_lab.py" \
    --base-url "$BASE" build-state --expect shipped \
    >/tmp/dryrun-complete-state.json; then
  pass "Complete state is tool shipped / Stock Keeper shipped"
else
  fail "Agent grant did not produce the complete build state"; exit 1
fi

SESSION="dryrun-$(date +%s)"
SESSION_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
turn5='{"message":"Hadley availability in Brooklyn","session_id":"'"$SESSION"'","customer_id":"CUST-MARCO"}'
reply="$(curl -fsN --max-time 60 -X POST "${BASE}/api/chat/stream" \
  -H 'Content-Type: application/json' \
  -H "X-Pellier-Session-Token: ${SESSION_TOKEN}" \
  -d "$turn5" 2>/dev/null || true)"
if echo "$reply" | grep -qiE 'brooklyn|BK-01' \
    && echo "$reply" | grep -qiE '[0-9]+[^[:cntrl:]]*(unit|shirt|available|stock|floor)|"quantity"[[:space:]]*:[[:space:]]*[0-9]+' \
    && echo "$reply" | grep -qiE 'ship|business day|[0-9]+[[:space:]]*(-|to)[[:space:]]*[0-9]+[[:space:]]*day'; then
  pass "Reply names Brooklyn with a quantity and ship window"
else
  fail "Reply did not prove Brooklyn + quantity + ship window"
  info "First 300 chars: ${reply:0:300}"
fi
if echo "$reply" | grep -qi 'floor_check is in stub state'; then
  fail "Stub envelope still present — solution did not take effect"
fi

# --- 4. Exercise 2 retrieval comparison ------------------------------------
echo "[4/6] Exercise 2 - GET /api/agent-trace/search-strategies/compare"
QUERY='A housewarming gift under $100 that is in stock'
retrieval=""
if retrieval="$(curl --fail --silent --show-error --max-time 75 \
    --get --data-urlencode "query=${QUERY}" \
    "${BASE}/api/agent-trace/search-strategies/compare" 2>/tmp/dryrun-retrieval.err)"; then
  printf '%s\n' "$retrieval" > /tmp/retrieval-comparison.json
  if printf '%s' "$retrieval" | jq -e '
      (.strategies | length) == 4
      and all(.strategies[];
        (.observedMs | type) == "number"
        and (.modeledCostPerThousandUsd | type) == "number"
        and (.products | type) == "array")
      and (.strategies[-1].extractedFilters | type) == "object"
      and .strategies[-1].extractedFilters.priceMaxUsd == 100
      and .strategies[-1].extractedFilters.inStockOnly == true
      and (.costModel.pricingReviewedOn | type) == "string"
      and (.costModel.components.rerank.formula | type) == "string"
      and (.measurementAssumptions.latency | contains("not a percentile"))
    ' >/dev/null 2>&1; then
    pass "Four retrieval rows returned with observed latency and modeled cost"
  else
    fail "Retrieval comparison response contract is incomplete"
    info "First 300 chars: ${retrieval:0:300}"
  fi
else
  fail "Exercise 2 comparison failed - see /tmp/dryrun-retrieval.err"
fi

# --- 5. Optional deeper action receipt -------------------------------------
echo "[5/6] Optional deeper trace - pellier.tool_audit"
n="$(_psql "SELECT count(*) FROM pellier.tool_audit WHERE tool='floor_check' AND session_id LIKE 'dryrun-%';")"
if [[ "${n:-0}" =~ ^[0-9]+$ ]] && (( n > 0 )); then
  pass "tool_audit has $n floor_check row(s) for this dry run"
else
  fail "No tool_audit row for floor_check — audit writer not firing"
fi

# --- 6. SQL-claim checks (pin run-of-show numbers + verify pg_trgm) ----------
# These tighten facilitator accuracy rather than gate the participant path, so
# a surprising value WARNs (review it) rather than FAILs (blocks the room).
# Only a structurally-broken catalog (no warehouse rows at all) is fatal.
echo "[6/6] SQL claims — Beeswax warehouse split + pg_trgm index"

# 6a. Beeswax at Brooklyn: confirm the 40/30/30 split holds (BK-01 is the
# largest share) and surface the live number so the run-of-show success
# check can quote observed data instead of a guessed figure.
bees_bk="$(_psql "SELECT wi.quantity FROM pellier.warehouse_inventory wi JOIN pellier.product_catalog pc ON pc.\"productId\" = wi.product_id WHERE pc.name ILIKE '%beeswax taper%' AND wi.warehouse_id = 'BK-01';")"
bees_other="$(_psql "SELECT COALESCE(max(wi.quantity),0) FROM pellier.warehouse_inventory wi JOIN pellier.product_catalog pc ON pc.\"productId\" = wi.product_id WHERE pc.name ILIKE '%beeswax taper%' AND wi.warehouse_id <> 'BK-01';")"
if [[ -z "${bees_bk}" ]]; then
  fail "No Beeswax Taper warehouse rows — catalog/warehouse seed incomplete"
elif [[ "${bees_bk}" =~ ^[0-9]+$ && "${bees_other}" =~ ^[0-9]+$ ]] && (( bees_bk >= bees_other )); then
  pass "Beeswax split correct — BK-01=${bees_bk} ≥ other warehouses (max ${bees_other}). Quote BK-01=${bees_bk} in the run-of-show."
else
  warn "Beeswax BK-01=${bees_bk} is NOT the largest (other max=${bees_other}) — 40/30/30 split may have re-seeded oddly; recheck run-of-show number."
fi

# 6b. pg_trgm: confirm migration 008's "prevents sequential scans" claim by
# asking the planner. At 40 rows Postgres seq-scans regardless (correct +
# cheap), so this is informational — what we're checking is that the trigram
# index EXISTS and that the plan is what the migration comment implies.
trgm_idx="$(_psql "SELECT count(*) FROM pg_indexes WHERE schemaname='pellier' AND indexname='product_catalog_name_trgm_idx';")"
if [[ "${trgm_idx:-0}" == "1" ]]; then
  plan="$(_psql "EXPLAIN SELECT \"productId\" FROM pellier.product_catalog WHERE lower(name) LIKE '%hadley%';" | tr '\n' ' ')"
  if echo "$plan" | grep -qi "trgm\|bitmap index scan"; then
    pass "pg_trgm index exists and the planner uses it for lower(name) LIKE '%…%'."
  else
    info "pg_trgm index exists; at this row count the planner seq-scans (expected). Plan: ${plan:0:120}"
    info "  → migration 008's 'prevents seq scans' claim is a production-scale statement, not a 40-row one. Comment is accurate as written."
  fi
else
  warn "pg_trgm index product_catalog_name_trgm_idx missing — migration 008 may not have applied."
fi

echo "════════════════════════════════════════════════════════════"
if $FAILED; then
  printf "${RED}● DRY RUN FAILED${NC} — fix the ✗ items before the room opens.\n"
  exit 1
else
  printf "${GREEN}● DRY RUN PASSED${NC} — the participant path works end to end.\n"
  exit 0
fi
