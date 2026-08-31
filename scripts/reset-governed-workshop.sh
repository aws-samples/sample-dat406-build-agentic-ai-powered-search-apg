#!/usr/bin/env bash
# Reset the governed two-hour Pellier workshop evidence path.
#
# Safe to re-run, and idempotent: a second run produces no semantic delta.
#
# THE LIFECYCLE, in order. Each step exists because skipping it produced a defect:
#
#   1. Quiesce the application.        A truncate underneath a live turn can clear an
#                                      idempotency claim after its write committed.
#   2. Prove nothing is executing.     No active Pellier database session.
#   3. Reset Aurora runtime state.     TRUNCATE, never DELETE: DELETE fires the ledger
#                                      and receipt-immutability triggers, writing new
#                                      history while trying to clear history.
#   4. Clean AgentCore Memory runtime. Aurora is not the whole workshop; preference
#                                      records are actor-scoped and outlive a session.
#   5. Restore participant Cedar state through the CLI project.
#   6. Restart the application.        On a trap, so a mid-script failure cannot leave
#                                      the box with the backend down.
#   7. Verify the baseline, then run the health gate.
#
# DOES RESET REQUIRE SERVICES TO BE STOPPED? Yes. On a workshop box this script stops
# and restarts `pellier.service` itself, so the answer costs the operator nothing. On a
# host with no such unit it refuses while a backend is listening, rather than racing.
# Four escape hatches, all explicit:
#
#   PELLIER_RESET_ALLOW_LIVE=1   proceed without quiescing (accepts the race)
#   PELLIER_BACKEND_PORT=8003    probe a different port; a governed dev stack does not
#                                run on :8000, and the default would otherwise detect an
#                                unrelated backend and refuse
#   PELLIER_RESET_SKIP_MEMORY=1  data-only reset on a box with no AWS credentials
#   PELLIER_RESET_SKIP_AGENTCORE=1  leave the control plane exactly as it is

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
# A WORKSHOP BOX HAS NO VENV. `bootstrap-environment.sh` installs
# `pellier/backend/requirements.lock` into the participant's `~/.local` with
# `pip install --user`, and the systemd unit runs the ambient interpreter. So `python3`
# there IS the validated interpreter, carrying the same pinned botocore 1.43.51 as a
# developer venv. Do not "fix" this fallback away: `deploy_all.sh` resolves it the same
# way for the same reason.
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
# Whether it resolves at all is a separate question from which path it is. `[[ -x name ]]`
# is a file test relative to the working directory and performs no PATH lookup, so
# testing the bare string "python3" is always false and would silently skip every step
# guarded by it.
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  fail "No usable Python interpreter (tried the backend venv, then python3)."
  exit 1
fi
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"

# This script TRUNCATEs the evidence tables, so it must never guess which
# database to talk to. Require DB_NAME/DB_USER from the sourced .env rather
# than silently defaulting to the `postgres` maintenance database.
: "${DB_NAME:?DB_NAME is not set in $ENV_FILE — refusing to run a destructive reset against a guessed database}"
: "${DB_USER:?DB_USER is not set in $ENV_FILE — refusing to run a destructive reset against a guessed role}"

# -X on every invocation. A developer's ~/.psqlrc printed "Null display is (null). Timing
# is on." into the scalar reads below, so an in-flight count of 0 parsed as noise and the
# reset refused a database with nothing running at all. A workshop box has no .psqlrc,
# which is precisely why a defect like this only ever appears off-box.
_psql_file() {
  local file="$1"
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -d "$DB_NAME" \
    -X -v ON_ERROR_STOP=1 \
    -f "$file"
}

_psql_exec() {
  local sql="$1"
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -d "$DB_NAME" \
    -X -v ON_ERROR_STOP=1 \
    -c "$sql"
}

# One value, no headers, no padding. The lifecycle checks below compare counts, and a
# formatted table would make every comparison a string-trimming exercise.
_psql_scalar() {
  local sql="$1"
  PGPASSWORD="${DB_PASSWORD:-}" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -d "$DB_NAME" \
    -X -v ON_ERROR_STOP=1 -t -A \
    -c "$sql"
}

# ---------------------------------------------------------------------------
# SERVICE STATE CONTRACT
#
# The reset TRUNCATEs the evidence and runtime tables. Postgres will not corrupt
# anything while the application is running, but "not corrupt" is not the property this
# workshop needs. A turn in flight during the truncate can leave a half-story that is
# worse than either outcome:
#
#   * a `write_operations` idempotency claim cleared after its domain write committed,
#     so a replay applies the effect a second time;
#   * an `approvals` row cleared after the execution it authorized, so an execution
#     receipt references a review that no longer exists;
#   * a conversation or Memory event written a moment after the truncate, so the
#     "clean" baseline starts with one shopper's residue in it.
#
# So reset OWNS the service state: it stops the application, proves nothing is
# executing, resets, and starts it again. One box, one unit, one database. That does not
# need a distributed lock, and building one would add a failure mode the workshop does
# not have.
#
# Documented answer to "does reset require services to be stopped": YES, and the script
# does it for you where it has the authority. Where it does not (a developer clone with
# no systemd), it REFUSES rather than racing, unless PELLIER_RESET_ALLOW_LIVE=1 says the
# operator accepts the risk.
PELLIER_SERVICE="${PELLIER_SERVICE:-pellier}"
BACKEND_PORT="${PELLIER_BACKEND_PORT:-8000}"
_service_was_running=false

_have_systemd_unit() {
  command -v systemctl >/dev/null 2>&1 \
    && systemctl list-unit-files "${PELLIER_SERVICE}.service" >/dev/null 2>&1
}

_backend_listening() {
  curl -fs --max-time 3 "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1
}

# Restore the service even when a later step fails. Without this, one failing psql on a
# workshop box leaves the participant with a stopped backend and no message that says so.
_resume_services() {
  if [[ "$_service_was_running" == true ]]; then
    if systemctl start "$PELLIER_SERVICE" >/dev/null 2>&1; then
      pass "Application service restarted: ${PELLIER_SERVICE}"
    else
      fail "Could not restart ${PELLIER_SERVICE}; run: sudo systemctl start ${PELLIER_SERVICE}"
    fi
    _service_was_running=false
  fi
}
trap _resume_services EXIT

_quiesce_services() {
  if _have_systemd_unit; then
    if systemctl is-active --quiet "$PELLIER_SERVICE"; then
      if systemctl stop "$PELLIER_SERVICE" >/dev/null 2>&1; then
        _service_was_running=true
        pass "Application quiesced: ${PELLIER_SERVICE} stopped for the reset"
      else
        fail "Could not stop ${PELLIER_SERVICE}. Reset refuses to race live writes."
        exit 1
      fi
    else
      pass "Application already stopped: ${PELLIER_SERVICE}"
    fi
    return 0
  fi

  # No unit to manage. Either nothing is serving, which is fine, or something is, which
  # is the race this contract exists to prevent.
  if ! _backend_listening; then
    pass "No application serving on :${BACKEND_PORT}; nothing to quiesce"
    return 0
  fi
  if [[ "${PELLIER_RESET_ALLOW_LIVE:-0}" == "1" ]]; then
    warn "Backend is live on :${BACKEND_PORT} and PELLIER_RESET_ALLOW_LIVE=1 was set; proceeding without quiescing"
    return 0
  fi
  fail "A backend is serving on :${BACKEND_PORT} and this host has no ${PELLIER_SERVICE}.service to stop."
  fail "Stop it first, or set PELLIER_RESET_ALLOW_LIVE=1 to accept a racing reset."
  exit 1
}

# Run AFTER quiescing. Before that, an unfinished claim may be a live execution; after
# it, the only sessions left are ones this script does not control, and an unfinished
# claim is residue that the TRUNCATE correctly clears.
_assert_no_active_execution() {
  local active claims
  active="$(_psql_scalar "
    SELECT count(*) FROM pg_stat_activity
     WHERE datname = current_database()
       AND pid <> pg_backend_pid()
       AND state = 'active'
       AND query ILIKE '%pellier.%'
       AND query NOT ILIKE '%pg_stat_activity%';
  " 2>/dev/null | tr -d '[:space:]')" || active=""
  if [[ -n "$active" && "$active" != "0" ]]; then
    fail "${active} database session(s) are actively running Pellier statements."
    fail "Reset refuses to truncate underneath them. Stop the application and re-run."
    exit 1
  fi
  pass "No active Pellier database session; nothing is mid-execution"

  claims="$(_psql_scalar "
    SELECT count(*) FROM pellier.write_operations WHERE completed_at IS NULL;
  " 2>/dev/null | tr -d '[:space:]')" || claims=""
  if [[ -n "$claims" && "$claims" != "0" ]]; then
    warn "${claims} idempotency claim(s) never completed. They are interrupted residue and the reset clears them."
  else
    pass "No unfinished idempotency claim"
  fi
}

echo "Pellier governed reset - $(date '+%H:%M:%S')"
echo "------------------------------------------------------------"

_quiesce_services
_assert_no_active_execution

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
  027_canonical_span_table.sql \
  028_shopper_operator_handoff.sql \
  029_live_surface_data.sql \
  030_storefront_editorial_order.sql \
  031_refine_fresh_storefront_edit.sql
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
    -- Persona profiles and workshop scenarios are provisioned source data.
    -- Shopper sessions are runtime state and must not survive a reset.
    pellier.shopper_sessions,
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
# ---------------------------------------------------------------------------
# STEP 4: AgentCore Memory runtime state.
#
# Aurora is not the whole workshop. AgentCore Memory holds actor-scoped
# USER_PREFERENCE records under /pellier/preferences/{actorId}/, and a new session id
# does NOT isolate an actor-scoped namespace. Measured on 2026-08-27: the authenticated
# Operator subject held four preference records extracted from engineering Concierge
# runs, phrased as the operator's own tastes. A reset that left them behind hands the
# next participant someone else's client situation on their first turn.
#
# This used to be a separate manual command, which means it was a step someone had to
# remember. It is part of the lifecycle now. `reset_memory_runtime.py` preserves the
# three seeded persona actors, deletes per event and per record rather than per
# namespace, and never touches the Memory RESOURCE.
#
# Skippable, because it needs AWS credentials and a data-only reset on a box without
# them must still complete.
if [[ "${PELLIER_RESET_SKIP_MEMORY:-0}" == "1" ]]; then
  pass "AgentCore Memory runtime left untouched (PELLIER_RESET_SKIP_MEMORY=1)"
elif "$PYTHON" "$REPO/scripts/reset_memory_runtime.py" --apply \
       >/tmp/pellier-governed-reset-memory.log 2>&1; then
  pass "AgentCore Memory runtime cleaned; seeded persona actors preserved"
else
  warn "Could not clean AgentCore Memory runtime (see /tmp/pellier-governed-reset-memory.log)"
fi

# ---------------------------------------------------------------------------
# STEP 7: baseline verification.
#
# The reset above asserts each step it performs. This asserts the RESULT, which is a
# different claim: every table that should be empty is empty, and the tables that carry
# the deterministic forensic incident carry exactly one row each. A reset that reported
# eleven passes and left a stray review behind would otherwise look complete.
_verify_baseline() {
  local empty_tables=(
    approvals execution_receipts operator_episodes write_operations
    conversations messages observatory_spans semantic_cache
    session_metadata tool_uses retrieval_receipts
  )
  local table count bad=0
  for table in "${empty_tables[@]}"; do
    count="$(_psql_scalar "SELECT count(*) FROM pellier.${table};" 2>/dev/null | tr -d '[:space:]')"
    if [[ "$count" != "0" ]]; then
      fail "Baseline: pellier.${table} should be empty, has ${count}"
      bad=$((bad + 1))
    fi
  done
  # The migration 010 forensic incident is the ONE intentional row in each of these.
  # It is the fixture the Observatory reconstructs, so zero is as wrong as two.
  for table in returns tool_audit governed_receipts; do
    count="$(_psql_scalar "SELECT count(*) FROM pellier.${table};" 2>/dev/null | tr -d '[:space:]')"
    if [[ "$count" != "1" ]]; then
      fail "Baseline: pellier.${table} should hold exactly the forensic incident (1 row), has ${count}"
      bad=$((bad + 1))
    fi
  done
  if [[ "$bad" -gt 0 ]]; then
    fail "Baseline verification failed on ${bad} table(s); this reset did not land a clean state"
    return 1
  fi
  pass "Baseline verified: runtime tables empty, forensic incident intact"
}

if ! _verify_baseline; then
  exit 1
fi

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
