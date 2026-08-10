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

if ! "$PYTHON" "$REPO/scripts/seed_boutique_catalog.py" \
    --from-cache >/tmp/pellier-governed-reset-catalog.log 2>&1; then
  fail "Deterministic catalog reset failed; see /tmp/pellier-governed-reset-catalog.log"
  exit 1
fi
pass "Catalog quantities restored from committed embedding cache"

for migration in \
  006_warehouse_inventory.sql \
  011_governed_write_integrity.sql
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
    pellier.governed_receipts,
    pellier.tool_audit,
    pellier.write_operations,
    pellier.returns
RESTART IDENTITY;
" >/tmp/pellier-governed-reset-evidence.log
pass "Live returns, write keys, audits, and receipts cleared"

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

if [[ -n "${AGENTCORE_POLICY_ENGINE_ID:-}" ]] && [[ -f "$REPO/scripts/deploy/workshop_policy_rule.py" ]]; then
  if "$PYTHON" "$REPO/scripts/deploy/workshop_policy_rule.py" \
      --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
      --region "$AWS_REGION" \
      reset >/tmp/pellier-governed-reset-policy.log 2>&1; then
    pass "Participant Cedar rule removed; shipped policy state restored"
  else
    fail "Could not reset participant Cedar rule; see /tmp/pellier-governed-reset-policy.log"
    exit 1
  fi

  if [[ -n "${AGENTCORE_GATEWAY_ARN:-}" ]]; then
    if "$PYTHON" "$REPO/scripts/deploy/workshop_policy_rule.py" mode \
        --set ENFORCE \
        --policy-engine-id "$AGENTCORE_POLICY_ENGINE_ID" \
        --gateway-arn "$AGENTCORE_GATEWAY_ARN" \
        --region "$AWS_REGION" >/tmp/pellier-governed-reset-mode.log 2>&1; then
      pass "Gateway Policy attachment restored to ENFORCE mode"
    else
      fail "Could not confirm Gateway Policy ENFORCE mode; see /tmp/pellier-governed-reset-mode.log"
      exit 1
    fi
  else
    fail "Gateway Policy mode reset requires AGENTCORE_GATEWAY_ARN"
    exit 1
  fi
else
  fail "Policy reset requires AGENTCORE_POLICY_ENGINE_ID"
  exit 1
fi

if [[ -x "$REPO/scripts/health-gate.sh" ]]; then
  echo "------------------------------------------------------------"
  PELLIER_REPO="$REPO" bash "$REPO/scripts/health-gate.sh"
else
  warn "health-gate.sh missing"
fi
