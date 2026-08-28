#!/usr/bin/env bash
# Reset the governed two-hour Pellier workshop evidence path.
#
# Safe to re-run. It restores the participant Cedar state, makes sure the
# HNSW index exists, reseeds the deterministic forensic receipt, and then runs
# the normal health gate so facilitators get one readable verdict.

set -euo pipefail

REPO="${PELLIER_REPO:-/workshop/sample-pellier-agentic-search-apg}"
ENV_FILE="${REPO}/.env"
PYTHON="${REPO}/pellier/backend/.venv/bin/python"

GREEN='\033[32m'; RED='\033[31m'; YEL='\033[33m'; NC='\033[0m'
pass() { printf "  ${GREEN}[PASS]${NC} %s\n" "$1"; }
fail() { printf "  ${RED}[FAIL]${NC} %s\n" "$1"; }
warn() { printf "  ${YEL}[WARN]${NC} %s\n" "$1"; }

# A workshop box has $REPO/.env, written by bootstrap and shell-safe. A local clone has
# only pellier/backend/.env, and refusing to run there sends anyone testing the reset to
# hand-rolled SQL - which is exactly how a trigger-firing manual reset gets written.
#
# The fallback is PARSED, not sourced. A dotenv file is not a shell script: a password
# containing "(" makes `source` fail with a syntax error, and a value containing "$"
# would be expanded. `declare -x "k=v"` assigns the bytes verbatim.
_load_dotenv() {
  local file="$1" line key value
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    # Strip one matched pair of surrounding quotes, as dotenv does.
    if [[ "$value" == \"*\" && ${#value} -ge 2 ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && ${#value} -ge 2 ]]; then
      value="${value:1:${#value}-2}"
    fi
    # `export k=v`, not `declare -gx`: macOS ships bash 3.2, where -g does not exist.
    # Both assign the bytes verbatim without expanding them.
    export "$key=$value"
  done < "$file"
}

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
elif [[ -f "${REPO}/pellier/backend/.env" ]]; then
  ENV_FILE="${REPO}/pellier/backend/.env"
  _load_dotenv "$ENV_FILE"
else
  fail "Missing env file: ${REPO}/.env (or pellier/backend/.env)"
  exit 1
fi

cd "$REPO"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"

# This script TRUNCATEs the evidence tables, so it must never guess which
# database to talk to. Require DB_NAME/DB_USER from the sourced .env rather
# than silently defaulting to the `postgres` maintenance database.
: "${DB_NAME:?DB_NAME is not set in $ENV_FILE — refusing to run a destructive reset against a guessed database}"
: "${DB_USER:?DB_USER is not set in $ENV_FILE — refusing to run a destructive reset against a guessed role}"

_psql_file() {
  local file="$1"
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -f "$file"
}

_psql_exec() {
  local sql="$1"
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -c "$sql"
}

echo "Pellier governed reset - $(date '+%H:%M:%S')"
echo "------------------------------------------------------------"

if ! "$PYTHON" "$REPO/scripts/seed_pellier_catalog.py" \
    --from-cache >/tmp/pellier-governed-reset-catalog.log 2>&1; then
  fail "Deterministic catalog reset failed; see /tmp/pellier-governed-reset-catalog.log"
  exit 1
fi
pass "Catalog quantities restored from committed embedding cache"

for migration in \
  006_warehouse_inventory.sql \
  011_governed_write_integrity.sql \
  012_retrieval_receipts.sql \
  013_inventory_ledger.sql \
  014_governed_turn_receipts.sql \
  015_proof_carrying_commerce.sql \
  016_runtime_roles_rls.sql \
  017_governed_query_receipts.sql \
  018_client_book.sql \
  019_operator_desk.sql \
  020_operator_review.sql \
  021_governed_execution.sql \
  022_write_operation_vocabulary.sql \
  023_idempotency_claims_release_on_failure.sql \
  024_operator_episodes.sql \
  025_execution_receipts.sql \
  026_episode_outcome_lineage.sql \
  027_canonical_span_table.sql
do
  if [[ ! -f "$REPO/scripts/migrations/$migration" ]]; then
    fail "Missing scripts/migrations/$migration"
    exit 1
  fi
  _psql_file "$REPO/scripts/migrations/$migration" \
    >>/tmp/pellier-governed-reset-db.log
done
pass "Exactly three warehouse rows per curated product reseeded"

_psql_exec "
TRUNCATE TABLE
    pellier.commerce_payment_events,
    pellier.commerce_receipts,
    pellier.commerce_outbox,
    pellier.commerce_inventory_reservations,
    pellier.commerce_payment_attempts,
    pellier.commerce_order_lines,
    pellier.commerce_orders,
    pellier.commerce_confirmation_grants,
    pellier.commerce_quote_lines,
    pellier.commerce_quotes,
    pellier.governed_receipts,
    pellier.governed_turn_receipts,
    pellier.governed_query_receipts,
    pellier.tool_audit,
    pellier.retrieval_receipts,
    pellier.inventory_ledger,
    pellier.write_operations,
    pellier.returns,
    pellier.store_credits,
    pellier.support_tickets,
    pellier.semantic_cache,
    -- Evidence and memory tables added after this script was first written. Each was
    -- absent from the list, so a reset cluster kept rows a fresh one has never had:
    --   execution_receipts  policy verdicts from engineering runs (migration 025)
    --   operator_episodes   derived memories of those runs (024/026)
    --   conversations       shopper AND Operator Concierge threads (007). Nothing
    --   messages            seeds these, so the fresh baseline is zero and every row
    --                       here is runtime state.
    --   observatory_spans   OTEL spans (002)
    --   session_metadata    per-session scratch (007)
    --   tool_uses           per-turn tool records (007)
    pellier.execution_receipts,
    pellier.operator_episodes,
    pellier.messages,
    pellier.conversations,
    pellier.observatory_spans,
    pellier.session_metadata,
    pellier.tool_uses,
    -- LAST in the list, because execution_receipts and operator_episodes reference it.
    -- One TRUNCATE covers them together, so no CASCADE is needed and nothing is
    -- orphaned. TRUNCATE also fires no row-level triggers: a DELETE here would run
    -- `record_inventory_movement` and `reject_governed_turn_receipt_mutation`, writing
    -- new ledger history while trying to clear history.
    pellier.approvals
RESTART IDENTITY;
" >/tmp/pellier-governed-reset-evidence.log
pass "Cleared: returns, stock movements, write keys, audits, receipts, episodes, conversations, spans, and operator reviews"

_psql_file "$REPO/scripts/migrations/013_inventory_ledger.sql" \
  >>/tmp/pellier-governed-reset-db.log
pass "Inventory ledger reseeded from deterministic warehouse state"

# 019 is re-applied after the TRUNCATE above for the same reason 013 and 015
# are: the truncate empties the operator desk, and the seeded tickets plus
# Sarah's credit on file are the starting state the client book describes. The
# semantic cache is deliberately left empty, so the first paraphrase of the
# run is a real miss and the second is a real hit.
_psql_file "$REPO/scripts/migrations/019_operator_desk.sql" \
  >>/tmp/pellier-governed-reset-db.log
pass "Operator desk reseeded: support tickets, credit on file, empty semantic cache"

# Row-Level Security authorization mapping.
#
# `pellier.principal_customers` is authorization configuration, not turn
# evidence, so it is deliberately absent from the TRUNCATE above. It still
# gets verified here: an empty mapping denies every signed-in shopper their
# own orders, which presents as a broken application rather than as
# governance, and reset is where a deterministic starting state is asserted.
if "$PYTHON" "$REPO/scripts/seed_principal_mappings.py" --check \
     >/tmp/pellier-governed-reset-principals.log 2>&1; then
  pass "RLS principal mappings intact for every named shopper"
else
  warn "RLS principal mappings incomplete — run scripts/seed_principal_mappings.py (see /tmp/pellier-governed-reset-principals.log)"
fi

_psql_file "$REPO/scripts/migrations/015_proof_carrying_commerce.sql" \
  >>/tmp/pellier-governed-reset-db.log
pass "Proof-carrying commerce lifecycle restored"

if [[ ! -f "$REPO/scripts/migrations/010_governed_receipts.sql" ]]; then
  fail "Missing scripts/migrations/010_governed_receipts.sql"
  exit 1
fi
_psql_file "$REPO/scripts/migrations/010_governed_receipts.sql" \
  >>/tmp/pellier-governed-reset-db.log
pass "Canonical governed forensic incident reseeded"

_psql_exec '
CREATE INDEX IF NOT EXISTS product_catalog_embedding_hnsw
    ON pellier.product_catalog
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
ANALYZE pellier.product_catalog;
' >/tmp/pellier-governed-reset-index.log
pass "HNSW index present: product_catalog_embedding_hnsw"

# The AgentCore leg restores participant-mutated Cedar state through the CLI project,
# which means `agentcore deploy`. That is right on a workshop box a participant has been
# editing, and wrong on a deployment whose canonical policies were applied outside the
# CLI project: a deploy would push the project's declarations over them.
#
# So a DATA reset does not require control-plane authority. Set
# PELLIER_RESET_SKIP_AGENTCORE=1 to reset rows only and leave the control plane exactly
# as it is. The Aurora reset above has already completed either way.
if [[ "${PELLIER_RESET_SKIP_AGENTCORE:-0}" == "1" ]]; then
  pass "AgentCore control plane left untouched (PELLIER_RESET_SKIP_AGENTCORE=1)"
  if [[ -x "$REPO/scripts/health-gate.sh" ]]; then
    echo "------------------------------------------------------------"
    PELLIER_REPO="$REPO" bash "$REPO/scripts/health-gate.sh"
  fi
  exit 0
fi

AGENTCORE_PROJECT="$REPO/.agentcore-project/pellier"
AGENTCORE_CONFIG="$AGENTCORE_PROJECT/agentcore/agentcore.json"
POLICY_ENGINE_NAME="pellier_policy_engine"

if [[ ! -f "$AGENTCORE_CONFIG" ]]; then
  fail "AgentCore CLI project missing: $AGENTCORE_CONFIG"
  exit 1
fi

_agentcore() {
  (
    cd "$AGENTCORE_PROJECT"
    if command -v agentcore >/dev/null 2>&1; then
      command agentcore "$@"
    else
      npx -y @aws/agentcore@0.26.0 "$@"
    fi
  )
}

policy_changed=false
for policy_name in workshop_identity_match_forbid; do
  if jq -e \
      --arg engine "$POLICY_ENGINE_NAME" \
      --arg policy "$policy_name" \
      '.policyEngines[] | select(.name == $engine) | .policies[]? | select(.name == $policy)' \
      "$AGENTCORE_CONFIG" >/dev/null; then
    _agentcore remove policy \
      --name "$policy_name" \
      --engine "$POLICY_ENGINE_NAME" \
      --yes \
      --json >>/tmp/pellier-governed-reset-policy.log
    policy_changed=true
  fi
done

if [[ "$policy_changed" == true ]]; then
  _agentcore validate --json >>/tmp/pellier-governed-reset-policy.log
  _agentcore deploy --yes --json >>/tmp/pellier-governed-reset-policy.log
  pass "Participant Cedar rule removed through AgentCore CLI"
else
  pass "Participant Cedar rule absent; shipped CLI project already restored"
fi

if [[ "$(jq -r \
    --arg name pellier-gateway \
    '.agentCoreGateways[] | select(.name == $name) | .policyEngineConfiguration.mode' \
    "$AGENTCORE_CONFIG")" != "ENFORCE" ]]; then
  fail "AgentCore project no longer pins Gateway Policy mode to ENFORCE"
  exit 1
fi
pass "Gateway Policy remains configured in ENFORCE mode"

# The check above reads the CLI project file, which is the declared intent. The
# live engine can disagree: a participant who switches a policy to LOG_ONLY
# during the monitor-mode exercise leaves enforcement off while the file still
# says ENFORCE. Restoring only the file would report a reset workshop whose
# denials silently do not happen, so the live mode is restored at both scopes
# (per-policy `enforcementMode`, gateway `policyEngineConfiguration.mode`).
#
# Non-fatal: many boxes have no AgentCore Policy engine provisioned, and on
# those the policy leg is legitimately NOT_EVALUATED rather than broken.
if "$PYTHON" "$REPO/scripts/policy_mode.py" --restore-shipped \
     >/tmp/pellier-governed-reset-policy-mode.log 2>&1; then
  pass "Live Cedar enforcement mode restored at both scopes"
else
  warn "Could not restore live Cedar enforcement mode (see /tmp/pellier-governed-reset-policy-mode.log)"
fi

if [[ -x "$REPO/scripts/health-gate.sh" ]]; then
  echo "------------------------------------------------------------"
  PELLIER_REPO="$REPO" bash "$REPO/scripts/health-gate.sh"
else
  warn "health-gate.sh missing"
fi
