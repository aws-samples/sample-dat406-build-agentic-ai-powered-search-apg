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

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
else
  fail "Missing env file: $ENV_FILE"
  exit 1
fi

cd "$REPO"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"

_psql_file() {
  local file="$1"
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" \
    -v ON_ERROR_STOP=1 \
    -f "$file"
}

_psql_exec() {
  local sql="$1"
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" \
    -v ON_ERROR_STOP=1 \
    -c "$sql"
}

echo "Pellier governed reset - $(date '+%H:%M:%S')"
echo "------------------------------------------------------------"

if [[ -f "$REPO/scripts/migrations/010_governed_receipts.sql" ]]; then
  _psql_file "$REPO/scripts/migrations/010_governed_receipts.sql" >/tmp/pellier-governed-reset-db.log
  pass "Governed receipt table and forensic incident reseeded"
else
  fail "Missing scripts/migrations/010_governed_receipts.sql"
  exit 1
fi

_psql_exec '
CREATE INDEX IF NOT EXISTS product_catalog_embedding_hnsw
    ON pellier.product_catalog
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
ANALYZE pellier.product_catalog;
' >/tmp/pellier-governed-reset-index.log
pass "HNSW index present: product_catalog_embedding_hnsw"

# Optional RLS rail: participants apply it by hand from solutions/; remove it
# here so a reset always lands back on the shipped single-user state.
if [[ -f "$REPO/solutions/the-ledger/sql/rls_rail_reset.sql" ]]; then
  _psql_file "$REPO/solutions/the-ledger/sql/rls_rail_reset.sql" >/tmp/pellier-governed-reset-rls.log
  pass "Optional RLS rail removed (no-op if it was never applied)"
else
  warn "Missing solutions/the-ledger/sql/rls_rail_reset.sql; RLS reset skipped"
fi

if [[ -n "${AGENTCORE_POLICY_ENGINE_ID:-}" ]] && [[ -f "$REPO/scripts/deploy/workshop_policy_rule.py" ]]; then
  if "$PYTHON" "$REPO/scripts/deploy/workshop_policy_rule.py" \
      --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
      --region "$AWS_REGION" \
      reset >/tmp/pellier-governed-reset-policy.log 2>&1; then
    pass "Participant Cedar rule removed; shipped policy state restored"
  else
    warn "Could not reset participant Cedar rule; see /tmp/pellier-governed-reset-policy.log"
  fi

  if [[ -n "${AGENTCORE_GATEWAY_ARN:-}" ]]; then
    if "$PYTHON" "$REPO/scripts/deploy/workshop_policy_rule.py" mode \
        --set ENFORCE \
        --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
        --gateway-arn "$AGENTCORE_GATEWAY_ARN" \
        --region "$AWS_REGION" >/tmp/pellier-governed-reset-mode.log 2>&1; then
      pass "Gateway Policy attachment restored to ENFORCE mode"
    else
      warn "Could not confirm Gateway Policy ENFORCE mode; see /tmp/pellier-governed-reset-mode.log"
    fi
  else
    warn "Gateway Policy mode reset skipped; AGENTCORE_GATEWAY_ARN not set"
  fi
else
  warn "Policy reset skipped; AGENTCORE_POLICY_ENGINE_ID not set"
fi

if [[ -x "$REPO/scripts/health-gate.sh" ]]; then
  echo "------------------------------------------------------------"
  PELLIER_REPO="$REPO" bash "$REPO/scripts/health-gate.sh"
else
  warn "health-gate.sh missing"
fi
