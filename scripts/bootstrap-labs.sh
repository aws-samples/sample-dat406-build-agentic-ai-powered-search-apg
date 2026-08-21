#!/bin/bash
# Pellier Workshop - Stage 2: Labs Bootstrap
# Optimizations: Parallel pip installs, reduced redundancy, faster execution
# Duration: ~12-15 minutes

set -euo pipefail

# ============================================================================
# PARAMETERS & LOGGING
# ============================================================================
CODE_EDITOR_USER="${CODE_EDITOR_USER:-participant}"
HOME_FOLDER="${HOME_FOLDER:-/workshop}"
REPO_NAME="sample-pellier-agentic-search-apg"
REPO_PATH="$HOME_FOLDER/$REPO_NAME"
AWS_REGION="${AWS_REGION:-us-east-1}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
fail() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"; exit 1; }
write_status_json() {
    local status="$1"
    local managed_status="$2"
    local managed_path="$3"
    cat > /tmp/workshop-ready.json << EOF
{
    "status": "${status}",
    "timestamp": "$(date -Iseconds)",
    "stage": "labs-bootstrap",
    "components": {
        "pellier_backend": "ready",
        "pellier_frontend": "ready",
        "database_config": "ready"
    },
    "builders_managed_path": {
        "status": "${managed_status}",
        "details_path": "${managed_path}"
    }
}
EOF
    chmod 644 /tmp/workshop-ready.json
}
upsert_env() {
    local key="$1"
    local value="$2"
    local env_file="$3"
    if grep -q "^${key}=" "$env_file" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$env_file"
    else
        echo "${key}=${value}" >> "$env_file"
    fi
}

log "=========================================="
log "Pellier Stage 2: Labs Bootstrap (Optimized)"
log "=========================================="

# ============================================================================
# STEP 1: CLONE REPOSITORY (~30 sec)
# ============================================================================
# On a Workshop Studio box the CloudFormation UserData has already cloned the
# repo at an immutable pinned SHA (RepoRevision) into exactly this path, and it
# exports WORKSHOP_SOURCE_REVISION as the provenance record. So the branch below
# is NOT the event path -- it is the local-dev / manual-rerun fallback, which
# gets whatever origin/HEAD points at. Everything after the clone assumes the
# tree is present, so a failure here must stop rather than warn-and-continue.
REPO_URL="${REPO_URL:-https://github.com/aws-samples/sample-pellier-agentic-search-apg.git}"

log "Cloning repository..."
if [ ! -d "$REPO_PATH" ]; then
    # --depth 1: .git is deleted moments later, so full history is pure
    # download cost. 2>&1 into a variable, not 2>/dev/null: the old code
    # discarded the one line that says why the clone failed.
    clone_log=$(sudo -u "$CODE_EDITOR_USER" git clone --depth 1 \
        "$REPO_URL" "$REPO_PATH" 2>&1) \
        || fail "Clone of ${REPO_URL} failed: ${clone_log}"

    # Record what was delivered BEFORE .git is removed. This is the only
    # post-provision answer to "which content is this box running?".
    resolved_sha=$(sudo -u "$CODE_EDITOR_USER" git -C "$REPO_PATH" rev-parse HEAD 2>/dev/null || echo unknown)
    sudo -u "$CODE_EDITOR_USER" tee "$REPO_PATH/.workshop-ref.json" >/dev/null << EOF
{
    "repo_url": "${REPO_URL}",
    "repo_ref": "<default-branch>",
    "resolved_sha": "${resolved_sha}",
    "cloned_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "clone_path": "bootstrap-fallback"
}
EOF

    log "✅ Repository cloned (default branch @ ${resolved_sha:0:8})"
else
    log "✅ Repository exists"
fi

# Remove .git on BOTH paths, not just the fallback.
#
# The fallback above always deleted it. The event path did not, so a Workshop
# Studio box shipped with a live detached checkout at the pinned SHA and the
# workspace stayed on live git. `"git.enabled": false` hides the Source Control
# panel, but the terminal is untouched: `git checkout -- .` silently reverts the
# floor_check exercise a participant is midway through, and `git stash` loses it
# with no visible trace. Neither is a thing anyone does on purpose; both are
# things people type out of habit.
#
# Safe to remove here because nothing downstream reads it:
#   - the pinned-SHA assertion runs in CloudFormation UserData, before this
#     script (`git rev-parse HEAD` = RepoRevision),
#   - provenance on the event path is WORKSHOP_SOURCE_REVISION, exported by the
#     same UserData, and on the fallback path .workshop-ref.json written above,
#   - no application code shells out to git,
#   - no lab instructs a participant to run git.
if [ -d "$REPO_PATH/.git" ]; then
    # Record provenance for the event path too, so "which content is this box
    # running?" has a file answer after .git is gone, not just an env var that
    # dies with the shell.
    if [ ! -f "$REPO_PATH/.workshop-ref.json" ]; then
        event_sha=$(sudo -u "$CODE_EDITOR_USER" git -C "$REPO_PATH" rev-parse HEAD 2>/dev/null || echo unknown)
        sudo -u "$CODE_EDITOR_USER" tee "$REPO_PATH/.workshop-ref.json" >/dev/null << EOF
{
    "repo_url": "${REPO_URL}",
    "repo_ref": "${WORKSHOP_SOURCE_REVISION:-<pinned>}",
    "resolved_sha": "${event_sha}",
    "cloned_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "clone_path": "cloudformation-userdata"
}
EOF
    fi
    rm -rf "$REPO_PATH/.git"
    log "✅ Workspace detached from git (participants cannot revert the exercise)"
fi

# ============================================================================
# STEP 2: FETCH DB CREDENTIALS (~10 sec)
# ============================================================================
log "Fetching database credentials..."
export DB_HOST="" DB_PORT="5432" DB_USER="" DB_PASSWORD="" DB_NAME="${DB_NAME:-pellier}"

if [ -n "${DB_SECRET_ARN:-}" ]; then
    DB_SECRET=$(aws secretsmanager get-secret-value --secret-id "$DB_SECRET_ARN" --region "$AWS_REGION" --query SecretString --output text 2>/dev/null || echo "")
    if [ -n "$DB_SECRET" ]; then
        export DB_HOST=$(echo "$DB_SECRET" | jq -r '.host // empty')
        export DB_USER=$(echo "$DB_SECRET" | jq -r '.username // empty')
        export DB_PASSWORD=$(echo "$DB_SECRET" | jq -r '.password // empty')
        export DB_NAME=$(echo "$DB_SECRET" | jq -r --arg default_db "${DB_NAME:-pellier}" '.dbname // .database // $default_db')
        log "✅ Database credentials retrieved"
    fi
fi

# ============================================================================
# STEP 3: CREATE .ENV FILES (~5 sec) - CONSOLIDATED
# ============================================================================
log "Creating environment files..."

# Frontend .env (always create).
#
# Single-process model: FastAPI on :8000 serves BOTH the built SPA
# and /api, so the browser hits the same origin for both — no
# separate API base URL is needed. VITE_API_URL stays empty (the
# chat/search services default to '' → relative URLs).
#
# VITE_BASE_PATH is the asset URL prefix baked into the built bundle
# so CloudFront's /ports/8000/* reverse proxy matches what code-server
# forwards. Override to "/" for a pure-local prod-build test.
# VITE_COGNITO_* drive the real sign-in (no demo mode). They come from
# .pellier-env, which CloudFormation populated with the live pool/client.
# The redirect URI resolves from window.location.origin at runtime
# (AuthContext.tsx), so it is intentionally not baked in here.
[ -d "$REPO_PATH/pellier/frontend" ] && cat > "$REPO_PATH/pellier/frontend/.env" << EOF
VITE_API_URL=
VITE_BASE_PATH=/ports/8000/
VITE_AWS_REGION=$AWS_REGION
VITE_ENABLE_LAB2=true
VITE_COGNITO_DOMAIN=${VITE_COGNITO_DOMAIN:-}
VITE_COGNITO_CLIENT_ID=${VITE_COGNITO_CLIENT_ID:-}
EOF

# Backend/Root .env (if DB available)
if [ -n "$DB_HOST" ]; then
    DB_CLUSTER_ARN="${DB_CLUSTER_ARN:-}"
    if [ -z "$DB_CLUSTER_ARN" ]; then
        DB_CLUSTER_ARN="arn:aws:rds:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):cluster:pellier-cluster"
    fi

    # URL-encode the password for DATABASE_URL. Aurora master secrets
    # routinely contain @ : / ? % which must be percent-encoded inside
    # a postgresql:// URL or psycopg will misparse the string.
    DB_PASSWORD_URLENC=$(python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))" "$DB_PASSWORD")

    # Write the .env with single-quoted values so a downstream
    # `set -a; source .env; set +a` reads them as literals. Without
    # the quotes, any $ in DB_PASSWORD would expand at source time
    # — a real failure mode where a generated password containing
    # `$Z…` triggered "unbound variable" errors under `set -u`.
    cat > "$REPO_PATH/.env" << EOF
DB_SECRET_ARN='${DB_SECRET_ARN:-}'
DB_CLUSTER_ARN='${DB_CLUSTER_ARN}'
DB_HOST='${DB_HOST}'
DB_PORT='${DB_PORT}'
DB_NAME='${DB_NAME}'
DB_USER='${DB_USER}'
DB_PASSWORD='${DB_PASSWORD}'
DATABASE_URL='postgresql://${DB_USER}:${DB_PASSWORD_URLENC}@${DB_HOST}:${DB_PORT}/${DB_NAME}'
PGHOST='${DB_HOST}'
PGPORT='${DB_PORT}'
PGUSER='${DB_USER}'
PGPASSWORD='${DB_PASSWORD}'
PGDATABASE='${DB_NAME}'
AWS_REGION='${AWS_REGION}'
AWS_DEFAULT_REGION='${AWS_REGION}'
BEDROCK_EMBEDDING_MODEL='${BEDROCK_EMBEDDING_MODEL:-us.cohere.embed-v4:0}'
BEDROCK_RERANK_MODEL='${BEDROCK_RERANK_MODEL:-cohere.rerank-v3-5:0}'
BEDROCK_CHAT_MODEL='${BEDROCK_CHAT_MODEL:-global.anthropic.claude-opus-4-6-v1}'
WORKSHOP_ID='${WORKSHOP_ID:-}'
WORKSHOP_FORMAT='${WORKSHOP_FORMAT:-builders}'
AUTH_MODE='${AUTH_MODE:-cognito}'
COGNITO_USER_POOL_ID='${COGNITO_USER_POOL_ID:-}'
COGNITO_POOL_ID='${COGNITO_USER_POOL_ID:-}'
COGNITO_CLIENT_ID='${COGNITO_CLIENT_ID:-}'
COGNITO_DOMAIN='${VITE_COGNITO_DOMAIN:-}'
APP_BASE_PATH='/ports/8000'
EOF

    chmod 600 "$REPO_PATH/.env"
    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH/.env"

    # Symlink for backend (avoid duplication)
    ln -sf "$REPO_PATH/.env" "$REPO_PATH/pellier/backend/.env" 2>/dev/null

    # .pgpass for psql CLI. The user's home directory is created by
    # `adduser` in bootstrap-environment.sh; we ensure it exists here
    # too in case Stage 2 ran before Stage 1 (defensive).
    PGPASS_DIR="/home/$CODE_EDITOR_USER"
    if [ ! -d "$PGPASS_DIR" ]; then
        mkdir -p "$PGPASS_DIR"
        chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$PGPASS_DIR"
    fi
    echo "$DB_HOST:$DB_PORT:$DB_NAME:$DB_USER:$DB_PASSWORD" > "$PGPASS_DIR/.pgpass"
    chmod 600 "$PGPASS_DIR/.pgpass"
    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$PGPASS_DIR/.pgpass"

    log "✅ Environment files created (.env, .pgpass)"
else
    warn "Database credentials not available - skipping DB configuration"
fi

# Fix permissions
chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH"

# Install workshop-wide Claude Code guidance without overwriting unrelated
# participant preferences. Re-running bootstrap replaces only this managed
# block, so the file is both idempotent and safe to extend.
CLAUDE_HOME="/home/$CODE_EDITOR_USER/.claude"
GLOBAL_CLAUDE="$CLAUDE_HOME/CLAUDE.md"
GLOBAL_CLAUDE_TMP=$(mktemp)
mkdir -p "$CLAUDE_HOME"

if [ -f "$GLOBAL_CLAUDE" ]; then
    awk '
        $0 == "<!-- PELLIER WORKSHOP GUIDANCE:START -->" { managed = 1; next }
        $0 == "<!-- PELLIER WORKSHOP GUIDANCE:END -->" { managed = 0; next }
        !managed { print }
    ' "$GLOBAL_CLAUDE" > "$GLOBAL_CLAUDE_TMP"
else
    : > "$GLOBAL_CLAUDE_TMP"
fi

cat >> "$GLOBAL_CLAUDE_TMP" << 'CLAUDEEOF'
<!-- PELLIER WORKSHOP GUIDANCE:START -->
# Pellier workshop guidance

- Read the repository `CLAUDE.md` and the nearest nested `CLAUDE.md` before editing.
- Treat Lab 1, Stock Keeper, `floor_check`, or workshop-marker requests as participant mode. Edit only the named marker block and never inspect `solutions/`.
- In participant mode, do not run git, install packages, change configuration, or restart services. Stop after one failed attempt and use the guide's escape hatch.
- `.claude/skills/*/SKILL.md` contains coding workflows. `skills/*/SKILL.md` contains Pellier runtime prompt overlays; do not treat runtime skills as coding instructions.
- Read `VOICE.md` before changing shopper-facing copy or model prompts.
- Never expose or commit credentials, tokens, customer data, or copied `.env` values. Do not copy account IDs, ARNs, or private endpoints into tracked files.
- Ask before destructive commands or changes outside the current repository.
<!-- PELLIER WORKSHOP GUIDANCE:END -->
CLAUDEEOF

install -o "$CODE_EDITOR_USER" -g "$CODE_EDITOR_USER" -m 0644 \
    "$GLOBAL_CLAUDE_TMP" "$GLOBAL_CLAUDE"
rm -f "$GLOBAL_CLAUDE_TMP"
log "✅ Participant Claude Code guidance installed at $GLOBAL_CLAUDE"

# ============================================================================
# STEP 4: VERIFY PYTHON DEPENDENCIES
# ============================================================================
# Stage 1 (bootstrap-environment.sh) already installed everything in
# pellier/backend/requirements.lock. Re-running the install here would
# either no-op (best case) or duplicate work without changing the
# environment. We just verify the critical packages reached
# /home/$CODE_EDITOR_USER/.local — if Stage 1's pip failed silently,
# we want to catch it here before the seeder runs and hits
# ModuleNotFoundError.
log "Verifying Python dependencies..."
if sudo -u "$CODE_EDITOR_USER" python3 -c "import amazon_transcribe, boto3, fastapi, psycopg, strands, uvicorn" 2>/dev/null; then
    log "✅ Backend dependencies verified"
else
    warn "Some backend dependencies are missing — re-running pip install"
    if [ -f "$REPO_PATH/pellier/backend/requirements.lock" ]; then
        sudo -u "$CODE_EDITOR_USER" python3 -m pip install --user \
            --require-hashes -r "$REPO_PATH/pellier/backend/requirements.lock" 2>&1 \
            | tee -a /var/log/pellier-pip-install.log >/dev/null
        if sudo -u "$CODE_EDITOR_USER" python3 -c "import amazon_transcribe, boto3, fastapi, psycopg, strands, uvicorn" 2>/dev/null; then
            log "✅ Backend dependencies recovered"
        else
            warn "Backend dependencies still missing after retry — pellier service will fail to start"
            warn "  see /var/log/pellier-pip-install.log"
        fi
    fi
fi

# ============================================================================
# STEP 7: INSTALL UV (~30 sec)
# ============================================================================
log "Installing uv..."
if ! sudo -u "$CODE_EDITOR_USER" bash -c 'export PATH="$HOME/.local/bin:$PATH" && command -v uv' &>/dev/null; then
    sudo -u "$CODE_EDITOR_USER" bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh' &>/dev/null || \
    sudo -u "$CODE_EDITOR_USER" python3 -m pip install --user uv &>/dev/null
    log "✅ uv installed"
else
    log "✅ uv already installed"
fi

# ============================================================================
# STEP 8: MCP CONFIG DIRECTORY & GENERATION
# ============================================================================
log "Setting up MCP configuration..."
mkdir -p "$REPO_PATH/pellier/config"
chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH/pellier/config"

# Generate MCP config if database credentials are available
if [ -n "$DB_HOST" ] && [ -f "$REPO_PATH/pellier/backend/generate_mcp_config.py" ]; then
    cd "$REPO_PATH/pellier/backend"
    
    # Source .env file to get all variables
    if [ -f "$REPO_PATH/.env" ]; then
        set -a
        source "$REPO_PATH/.env"
        set +a
    fi
    
    # Verify required variables are set
    if [ -z "${DB_SECRET_ARN:-}" ] || [ -z "${DB_CLUSTER_ARN:-}" ]; then
        warn "Missing DB_SECRET_ARN or DB_CLUSTER_ARN - MCP config will be generated on backend startup"
    else
        # Generate MCP config with variables from .env
        sudo -u "$CODE_EDITOR_USER" bash -c "export DB_SECRET_ARN='$DB_SECRET_ARN' && \
            export DB_CLUSTER_ARN='$DB_CLUSTER_ARN' && \
            export DB_NAME='$DB_NAME' && \
            export AWS_REGION='$AWS_REGION' && \
            python3 generate_mcp_config.py" 2>&1 | tee /var/log/mcp-config-generation.log
        
        if [ -f "$REPO_PATH/pellier/config/mcp-server-config.json" ]; then
            log "✅ MCP config generated at pellier/config/mcp-server-config.json"
            log "   MCP reference ready: awslabs.postgres-mcp-server via uvx"
        else
            warn "MCP config generation failed - will be generated on backend startup"
        fi
    fi
    cd "$REPO_PATH"
else
    log "ℹ️  MCP config will be generated on backend startup"
fi

# ============================================================================
# STEP 8b: BEDROCK MODEL-ACCESS PREFLIGHT (~10 sec)
# ============================================================================
# Fail fast and loud if the runtime models aren't enabled in this account.
# Without this, a missing grant surfaces much later as an empty storefront
# or a dead chat turn mid-session. Cohere Embed v4 is hard-required because
# every shopper query is embedded live before the pgvector search (the cache
# only covers the catalog corpus). The same preflight also resolves the
# independent Claude Code CLI model for Lab 1.
log "Preflight: checking Bedrock model access (${AWS_REGION})..."
if [ -f "$REPO_PATH/scripts/check_model_access.py" ]; then
    if sudo -u "$CODE_EDITOR_USER" bash -c "
        export AWS_REGION='${AWS_REGION:-us-east-1}'
        cd '$REPO_PATH'
        python3 scripts/check_model_access.py --write-env '$REPO_PATH/pellier/backend/.env'
    " 2>&1 | tee /var/log/model-access-preflight.log; then
        log "✅ Bedrock model-access preflight passed"
    else
        warn "❌ Bedrock model-access preflight FAILED — required models not enabled."
        warn "   See /var/log/model-access-preflight.log and enable models at:"
        warn "   https://console.aws.amazon.com/bedrock/home#/modelaccess"
        warn "   Continuing bootstrap so the IDE is usable, but the session will"
        warn "   not work until model access is granted and the seed is re-run."
    fi
else
    warn "check_model_access.py not found — skipping model preflight"
fi

# ============================================================================
# STEP 9-10: PARALLEL FRONTEND + DATABASE (~8 min vs 8.5 min)
# ============================================================================
log "Setting up frontend and database (parallel)..."

setup_frontend() {
    if [ -d "$REPO_PATH/pellier/frontend" ]; then
        cd "$REPO_PATH/pellier/frontend"
        # npm ci is reproducible (uses package-lock.json verbatim) and
        # fails loudly when the lock is out of sync — the right behavior
        # for a controlled workshop env. Output goes to a log file, not
        # /dev/null, so install failures aren't invisible.
        if [ -f package-lock.json ]; then
            sudo -u "$CODE_EDITOR_USER" npm ci \
                >> /var/log/pellier-npm-install.log 2>&1
        else
            warn "package-lock.json missing — falling back to npm install"
            sudo -u "$CODE_EDITOR_USER" npm install \
                >> /var/log/pellier-npm-install.log 2>&1
        fi
    fi
}

setup_database() {
    if [ -n "$DB_HOST" ] && [ -f "$REPO_PATH/scripts/seed_pellier_catalog.py" ]; then
        cd "$REPO_PATH"
        export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD AWS_REGION
        export ASSETS_BUCKET_NAME ASSETS_BUCKET_PREFIX
        export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

        if ! command -v psql >/dev/null 2>&1; then
            warn "psql is not installed or not on PATH — database setup cannot run"
            return 1
        fi

        # ---- 1. Schema bootstrap (CREATE EXTENSION vector + schema +
        # product_catalog table + HNSW index). pellier-database.yml
        # provisions an empty Aurora cluster; this migration is what
        # makes the cluster Pellier-ready. Runs first because the
        # seeder INSERTs into pellier.product_catalog and assumes the
        # vector(1024) column exists. ----
        if [ -f "$REPO_PATH/scripts/migrations/001_schema.sql" ]; then
            log "Applying migration 001_schema.sql..."
            PGPASSWORD="$DB_PASSWORD" psql \
                -h "$DB_HOST" -p "$DB_PORT" \
                -U "$DB_USER" -d "$DB_NAME" \
                -v ON_ERROR_STOP=1 \
                -f "$REPO_PATH/scripts/migrations/001_schema.sql" \
                2>&1 | tee /var/log/database-schema.log
            local rc=${PIPESTATUS[0]}
            if [ "$rc" -ne 0 ]; then
                warn "Schema bootstrap failed (rc=$rc) — see /var/log/database-schema.log"
                return "$rc"
            fi
        else
            warn "001_schema.sql not found — seeder will fail without the table"
        fi

        # ---- 2. Pellier catalog seeder — 40 hand-curated products
        # across the four personas (Marco / Anna / Theo / Fresh), plus
        # generated high-ID archive distractors for retrieval measurement.
        # Authoritative source for pellier.product_catalog.
        #
        # Embeddings come from the COMMITTED cache (data/embeddings_cache.json)
        # via --from-cache. The cache stores the 40 real Cohere vectors; the
        # archive distractors derive deterministic vectors from that committed
        # cache. This removes the slowest, most throttle-prone step from the
        # bootstrap critical path and makes the seed a deterministic SQL load.
        # To regenerate the cache after a curated catalog change, run
        # `python scripts/seed_pellier_catalog.py --csv-only --no-distractors`
        # on a machine with Bedrock access and commit the updated cache.
        #
        # Must run as $CODE_EDITOR_USER: psycopg is installed via
        # `pip install --user` for that user in Stage 1, so root's python3
        # cannot import it. Without sudo -u the seeder dies with
        # ModuleNotFoundError and the catalog stays empty — cascading silent
        # failures into 003's persona-orders JOIN. ----
        sudo -u "$CODE_EDITOR_USER" bash -c "
            export DB_HOST='$DB_HOST' DB_PORT='$DB_PORT' DB_NAME='$DB_NAME'
            export DB_USER='$DB_USER' DB_PASSWORD='$DB_PASSWORD'
            export AWS_REGION='$AWS_REGION'
            export ASSETS_BUCKET_NAME='${ASSETS_BUCKET_NAME:-}'
            export ASSETS_BUCKET_PREFIX='${ASSETS_BUCKET_PREFIX:-}'
            export DATABASE_URL='$DATABASE_URL'
            cd '$REPO_PATH'
            python3 scripts/seed_pellier_catalog.py --from-cache
        " 2>&1 | tee /var/log/database-setup.log
        local seed_rc=${PIPESTATUS[0]}
        if [ "$seed_rc" -ne 0 ]; then
            warn "Pellier catalog seed failed (rc=$seed_rc) — see /var/log/database-setup.log"
            return "$seed_rc"
        fi

        # ---- 3. Required fresh-cluster migrations. These are intentionally
        # idempotent and run after the catalog exists because several
        # tables FK into pellier.product_catalog. Ordering matters:
        # telemetry creates customers/orders, persona seed populates them,
        # Theo returns references them, and warehouse inventory powers
        # floor_check. ----
        local migration
        for migration in \
            002_workshop_telemetry.sql \
            003_persona_seed.sql \
            004_anna_hybrid_search.sql \
            005_theo_returns.sql \
            006_warehouse_inventory.sql \
            007_chat_session_tables.sql \
            008_search_performance_indexes.sql \
            009_return_policies.sql \
            010_governed_receipts.sql \
            011_governed_write_integrity.sql \
            012_retrieval_receipts.sql \
            013_inventory_ledger.sql \
            014_governed_turn_receipts.sql \
            015_proof_carrying_commerce.sql \
            016_runtime_roles_rls.sql \
            017_governed_query_receipts.sql
        do
            if [ -f "$REPO_PATH/scripts/migrations/$migration" ]; then
                log "Applying migration $migration..."
                PGPASSWORD="$DB_PASSWORD" psql \
                    -h "$DB_HOST" -p "$DB_PORT" \
                    -U "$DB_USER" -d "$DB_NAME" \
                    -v ON_ERROR_STOP=1 \
                    -f "$REPO_PATH/scripts/migrations/$migration" \
                    2>&1 | tee -a /var/log/database-setup.log
                local migration_rc=${PIPESTATUS[0]}
                if [ "$migration_rc" -ne 0 ]; then
                    warn "Migration $migration failed (rc=$migration_rc) — see /var/log/database-setup.log"
                    return "$migration_rc"
                fi
            else
                warn "Migration $migration not found — skipping"
            fi
        done

        # ---- 4. Tool registry seed — populates pellier.tools (created
        # empty by migration 002) with the 15 canonical Gateway tool names
        # plus their Cohere Embed v4 descriptions. The Observatory
        # Observatory's tool-registry tab and the pgvector
        # tool-discovery card both read from this table and silently
        # render zero rows if the seed is skipped. ----
        if [ -f "$REPO_PATH/scripts/seed_tool_registry.py" ]; then
            log "Seeding pellier.tools registry..."
            sudo -u "$CODE_EDITOR_USER" bash -c "
                export DB_HOST='$DB_HOST' DB_PORT='$DB_PORT' DB_NAME='$DB_NAME'
                export DB_USER='$DB_USER' DB_PASSWORD='$DB_PASSWORD'
                export AWS_REGION='$AWS_REGION'
                export DATABASE_URL='$DATABASE_URL'
                cd '$REPO_PATH'
                python3 scripts/seed_tool_registry.py
            " 2>&1 | tee -a /var/log/database-setup.log
            local tool_rc=${PIPESTATUS[0]}
            if [ "$tool_rc" -ne 0 ]; then
                warn "Tool registry seed failed (rc=$tool_rc) — Observatory tool-registry tab will show zero rows"
            fi
        fi

        return 0
    fi
    return 1
}

setup_frontend & PID_FE=$!
setup_database & PID_DB=$!
wait $PID_FE && log "✅ Frontend dependencies installed" || warn "Frontend install issues"
if wait $PID_DB; then
    log "✅ Database setup complete (expanded catalog, HNSW index, workshop tables)"
else
    warn "Database setup had issues - check /var/log/database-setup.log"
fi

# ============================================================================
# Memory is created once in STEP 16 as part of the same AgentCore CLI project
# as Runtime, Gateway, targets, and Policy. Data-plane seed events are added
# only after the CLI-managed Memory and USER_PREFERENCE strategy are ACTIVE.

# ============================================================================
# STEP 11: CREATE START SCRIPTS (~5 sec)
# ============================================================================
log "Creating start scripts..."

# Single-process model: FastAPI on :8000 serves both /api/* and the
# built SPA. The legacy start-frontend.sh / http-server on 5173 is
# gone — attendees point their browser at /ports/8000/* only.
# Single source of truth for the restart command is
# scripts/start-backend-builders.sh (safe `set -a; source .env` env
# loading — avoids the unquoted-env word-splitting bug that bit us with
# special chars in DB passwords). This convenience wrapper just delegates
# so there is exactly ONE definition of "how the backend restarts".
cat > "$REPO_PATH/pellier/start-backend.sh" << EOF
#!/bin/bash
# Convenience wrapper — delegates to the canonical builders start script.
# Do not duplicate the uvicorn invocation here; edit
# scripts/start-backend-builders.sh instead.
exec "$REPO_PATH/scripts/start-backend-builders.sh" "\$@"
EOF

chmod +x "$REPO_PATH/pellier/start-backend.sh"
chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH/pellier/start-backend.sh"
log "✅ Start scripts created"

# ============================================================================
# STEP 12: BASH ENVIRONMENT (~5 sec)
# ============================================================================
log "Configuring bash environment..."

cat >> "/home/$CODE_EDITOR_USER/.bashrc" << 'EOF'

# ============================================================================
# Pellier Workshop Environment
# ============================================================================

# Readable colored prompt (matches the dat403 workshop look): bold-green
# user, bold-blue path, then reset to default (light) for the $ and
# everything you type. The green/white contrast makes the active command
# line easy to find when scrolling back through output during the lab.
export PS1='\[\033[01;32m\]\u:\[\033[01;34m\]\w\[\033[00m\]\$ '

if [ -f /workshop/sample-pellier-agentic-search-apg/.env ]; then
    set -a
    source /workshop/sample-pellier-agentic-search-apg/.env
    set +a
    
    # Explicitly export PostgreSQL variables for psql
    export PGHOST
    export PGPORT
    export PGUSER
    export PGPASSWORD
    export PGDATABASE
fi

# Workshop Navigation Aliases
alias workshop='cd /workshop/sample-pellier-agentic-search-apg'
alias pellier='cd /workshop/sample-pellier-agentic-search-apg/pellier'
alias backend='cd /workshop/sample-pellier-agentic-search-apg/pellier/backend'
alias frontend='cd /workshop/sample-pellier-agentic-search-apg/pellier/frontend'

# One-shot readiness check (catalog / warehouse / memory id / runtime / health)
alias health='bash /workshop/sample-pellier-agentic-search-apg/scripts/health-gate.sh'

# AgentCore CLI (pinned 0.26.0). Labs inspect the managed resources, then add,
# validate, deploy, and remove one participant Cedar policy in the same
# declarative project. A FUNCTION (not an alias) ensures every command runs
# from the project root that owns agentcore/.cli/deployed-state.json.
# It cd's into the deployed project root so the CLI finds
# agentcore/.cli/deployed-state.json from wherever you are, prefers the
# global binary warmed at bootstrap (no registry call), and falls back to the
# pinned npx form if the global install is missing. Runtime invocation still
# goes through the app because the CLI invoke command cannot supply the
# workshop's Cognito bearer-token contract.
agentcore() {
    ( cd /workshop/sample-pellier-agentic-search-apg/.agentcore-project/pellier 2>/dev/null \
        && if _ac_bin="$(type -P agentcore)"; then "$_ac_bin" "$@"; else npx -y @aws/agentcore@0.26.0 "$@"; fi )
        # type -P, NOT command -v: command -v matches THIS function (always
        # true), then `command agentcore` finds no binary when the global npm
        # install was skipped -> "command not found" instead of the npx
        # fallback (box-verified 2026-06-12). type -P searches PATH only.
}

# Pellier service shortcuts — see FORMAT_ALIASES below (workshop vs builders).

# Database Shortcut (psql uses PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE from .env)
alias psql='psql'

# AWS Region for boto3
export AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}

# Claude Code CLI → Amazon Bedrock (Claude Code lane, Lab 1).
# CLAUDE_CODE_USE_BEDROCK=1 makes the CLI authenticate through THIS box's IAM
# instance role (the same ambient-credential chain psql/boto3/agentcore already
# use) — no Anthropic API key, no per-participant login, nothing to paste.
# Model: the `sonnet` alias lets the latest installed Claude Code release choose
# its current Sonnet model at workshop time. This lane is intentionally
# independent of the app's tested Opus/Sonnet model resolution.
export CLAUDE_CODE_USE_BEDROCK=1
export ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-sonnet}
export AWS_REGION=${AWS_REGION:-us-east-1}
# The CLI is installed globally as root (/usr/bin/claude) but runs as the
# participant user, so its auto-updater can't write the root-owned npm prefix
# and warns once at startup ("Auto-update failed: no write permission..."). The
# warning is harmless, but this composite flag suppresses it at the source by
# disabling all non-essential phone-home (auto-updater + telemetry + error
# reporting + feedback) — the right posture for a root-managed workshop box.
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

# Ensure uv is in PATH (required for MCP)
export PATH="$HOME/.local/bin:$PATH"

# Auto-navigate to workshop directory on terminal open
if [ "$PWD" = "$HOME" ] || [ "$PWD" = "/workshop" ]; then
    cd /workshop/sample-pellier-agentic-search-apg 2>/dev/null || true
fi
EOF

# Format-specific aliases (builders: no sudo; workshop: systemctl — passwordless via STEP 14 sudoers)
# Both formats run the backend via the pellier systemd unit (builders gets
# --reload baked into ExecStart). The backend is ALWAYS running, so
# `start-backend` is really "restart" and most participants never need it.
# `rebuild-frontend` is only for the rare .tsx edit (the lab is backend Python).
cat >> "/home/$CODE_EDITOR_USER/.bashrc" << 'ALS'
# --- Pellier aliases (systemd unit ``pellier``, serves SPA + /api on :8000) ---
# Backend runs automatically and (builders) reloads on .py save — you normally
# never run these. Restart only if you want a clean bounce.
alias start-backend='sudo systemctl restart pellier && journalctl -fu pellier --no-pager'
alias rebuild-frontend='bash /workshop/sample-pellier-agentic-search-apg/scripts/rebuild-frontend-builders.sh'
alias reset-governed='bash /workshop/sample-pellier-agentic-search-apg/scripts/reset-governed-workshop.sh'
ALS

log "✅ Bash environment configured (.bashrc updated with psql support)"

# ============================================================================
# STEP 13: FINAL VERIFICATION
# ============================================================================
log "Performing final verification..."

# Verify database setup
if [ -n "$DB_HOST" ]; then
    PRODUCT_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM pellier.product_catalog;" 2>/dev/null | xargs || echo "0")
    if [ "$PRODUCT_COUNT" -gt 0 ]; then
        log "✅ Database verified ($PRODUCT_COUNT products)"
    else
        warn "⚠️  Database may not be set up correctly (0 products found)"
    fi

    WAREHOUSE_ROWS=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM pellier.warehouse_inventory;" 2>/dev/null | xargs || echo "0")
    if [ "$WAREHOUSE_ROWS" -gt 0 ]; then
        log "✅ Warehouse inventory verified ($WAREHOUSE_ROWS rows)"
    else
        warn "⚠️  Warehouse inventory missing — floor_check exercise will not land"
    fi
fi

# Verify Python packages
if sudo -u "$CODE_EDITOR_USER" python3 -c "import amazon_transcribe, fastapi, strands, uvicorn" 2>/dev/null; then
    log "✅ Pellier Backend dependencies verified"
else
    warn "⚠️  Some Pellier Backend dependencies may be missing"
fi

# ============================================================================
# STEP 13b: CLOUDWATCH TRANSACTION SEARCH (observability prerequisite)
# ============================================================================
# The governed workshop reconstructs one agent turn from CloudWatch spans plus
# Aurora evidence. Spans only reach CloudWatch once Transaction Search routes
# trace segments to CloudWatch Logs, and AWS requires that to be enabled
# BEFORE the OTLP traces endpoint will accept data.
#
# Idempotent by design: this checks first and only mutates what is missing, so
# re-running bootstrap on an account that already has it is a no-op.
#
# Deliberately non-fatal. A missing prerequisite degrades the observability
# exercise, but the required application path still works, so this warns
# loudly rather than aborting a workshop box. Silent absence of spans is the
# one outcome that is unacceptable.
log "Verifying CloudWatch Transaction Search..."

TS_LOG_GROUPS="arn:aws:logs:${AWS_REGION}:*:log-group:aws/spans:*"
TS_DESIRED_SAMPLING=100

ts_account_id="$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")"

if [ -z "$ts_account_id" ]; then
    warn "⚠️  Transaction Search: no AWS credentials resolved — skipping."
    warn "    Observability proof will read: unavailable (credentials)"
else
    # 1. Resource policy so X-Ray may write spans into CloudWatch Logs.
    if aws logs describe-resource-policies --region "$AWS_REGION" \
        --query "resourcePolicies[?policyName=='TransactionSearchXRayAccess'].policyName" \
        --output text 2>/dev/null | grep -q "TransactionSearchXRayAccess"; then
        log "✅ Transaction Search resource policy present"
    else
        log "Creating Transaction Search resource policy..."
        if aws logs put-resource-policy \
            --region "$AWS_REGION" \
            --policy-name TransactionSearchXRayAccess \
            --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"TransactionSearchXRayAccess\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"xray.amazonaws.com\"},\"Action\":\"logs:PutLogEvents\",\"Resource\":[\"arn:aws:logs:${AWS_REGION}:${ts_account_id}:log-group:aws/spans:*\",\"arn:aws:logs:${AWS_REGION}:${ts_account_id}:log-group:/aws/application-signals/data:*\"],\"Condition\":{\"ArnLike\":{\"aws:SourceArn\":\"arn:aws:xray:${AWS_REGION}:${ts_account_id}:*\"},\"StringEquals\":{\"aws:SourceAccount\":\"${ts_account_id}\"}}}]}" \
            >/dev/null 2>&1; then
            log "✅ Transaction Search resource policy created"
        else
            warn "⚠️  Could not create Transaction Search resource policy (needs logs:PutResourcePolicy)"
        fi
    fi

    # 2. Route trace segments to CloudWatch Logs. This is the actual switch.
    ts_destination="$(aws xray get-trace-segment-destination --region "$AWS_REGION" \
        --query Destination --output text 2>/dev/null || echo "")"
    ts_status="$(aws xray get-trace-segment-destination --region "$AWS_REGION" \
        --query Status --output text 2>/dev/null || echo "")"

    if [ "$ts_destination" = "CloudWatchLogs" ] && [ "$ts_status" = "ACTIVE" ]; then
        log "✅ Transaction Search active (destination=CloudWatchLogs)"
    else
        log "Enabling Transaction Search (destination=CloudWatchLogs)..."
        if aws xray update-trace-segment-destination \
            --region "$AWS_REGION" --destination CloudWatchLogs >/dev/null 2>&1; then
            log "✅ Transaction Search enabled"
        else
            warn "⚠️  Could not enable Transaction Search (needs xray:UpdateTraceSegmentDestination)"
            warn "    Observability proof will read: unavailable (Transaction Search)"
        fi
    fi

    # 3. Index every workshop span. Participant proof must be deterministic, so
    #    probabilistic sampling below 100% is not acceptable here even though
    #    production guidance differs.
    ts_sampling="$(aws xray get-indexing-rules --region "$AWS_REGION" \
        --query "IndexingRules[?Name=='Default'].Rule.Probabilistic.DesiredSamplingPercentage | [0]" \
        --output text 2>/dev/null || echo "")"

    if [ "${ts_sampling%.*}" = "$TS_DESIRED_SAMPLING" ]; then
        log "✅ Span indexing at ${TS_DESIRED_SAMPLING}% (deterministic capture)"
    else
        log "Setting span indexing to ${TS_DESIRED_SAMPLING}% (was: ${ts_sampling:-unset})..."
        if aws xray update-indexing-rule --region "$AWS_REGION" --name "Default" \
            --rule "{\"Probabilistic\":{\"DesiredSamplingPercentage\":${TS_DESIRED_SAMPLING}}}" \
            >/dev/null 2>&1; then
            log "✅ Span indexing set to ${TS_DESIRED_SAMPLING}%"
        else
            warn "⚠️  Could not set span indexing to ${TS_DESIRED_SAMPLING}% — workshop turns may not all be indexed"
        fi
    fi
fi

# ============================================================================
# STEP 14: AUTO-START PELLIER SERVICE (single-process, port 8000)
# ============================================================================
# Single systemd service. FastAPI serves:
#   - the built SPA at /, /observatory, /storyboard, /discover, ...
#   - the API at /api/*
#   - self-hosted fonts + hashed bundles at /assets/*, /fonts/*
#
# One port, one process, one unit to troubleshoot. Drop-in migration
# from the earlier two/three-service layout: after running this
# bootstrap on a host that had pellier-{backend,frontend,frontend-watcher}
# services, those are stopped + disabled below so there's no port-5173
# collision at restart.
log "Creating pellier auto-start service (single process, port 8000)..."

# Cleanup of the legacy two/three-service layout. Safe to run
# unconditionally — absent services return non-zero and we swallow.
systemctl stop pellier-backend pellier-frontend pellier-frontend-watcher 2>/dev/null || true
systemctl disable pellier-backend pellier-frontend pellier-frontend-watcher 2>/dev/null || true
rm -f /etc/systemd/system/pellier-backend.service \
      /etc/systemd/system/pellier-frontend.service \
      /etc/systemd/system/pellier-frontend-watcher.service

# --- pellier.service: build frontend (best-effort), then run python -m uvicorn ---
#
# ONE unit for BOTH formats. The only per-format difference is whether
# uvicorn carries --reload: builders participants edit .py files and want
# live restarts on save; workshop format runs static. Everything else —
# Restart=always, boot-survival, best-effort frontend build — is identical.
#
# RELOAD_ARGS is computed here so there is a single heredoc, not two.
# --reload-dir pins the watch to the backend dir (avoids watching
# frontend/node_modules and re-triggering on dist/ writes).
if [ "${WORKSHOP_FORMAT:-builders}" = "builders" ] || [ "${WORKSHOP_FORMAT:-builders}" = "governed" ]; then
    UVICORN_RELOAD_ARGS="--reload --reload-dir $REPO_PATH/pellier/backend"
else
    UVICORN_RELOAD_ARGS=""
fi

cat > /etc/systemd/system/pellier.service << EOF
[Unit]
Description=Pellier (FastAPI + built SPA on :8000)
After=network.target

[Service]
Type=simple
User=$CODE_EDITOR_USER
Group=$CODE_EDITOR_USER
WorkingDirectory=$REPO_PATH/pellier/backend
EnvironmentFile=$REPO_PATH/.env
Environment=PATH=/home/$CODE_EDITOR_USER/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=/home/$CODE_EDITOR_USER
Environment=PYTHONUNBUFFERED=1
# VITE_BASE_PATH is baked into the built bundle so asset URLs match
# the CloudFront /ports/8000/* reverse-proxy prefix.
Environment=VITE_BASE_PATH=/ports/8000/
# ExecStartPre is BEST-EFFORT (leading '-' tells systemd to ignore a
# non-zero exit; '|| true' keeps the bash -c itself at 0). A frontend
# build failure must NEVER block the backend: app.py serves /api/* even
# when dist/ is absent (the SPA 404s with a clear log line). This is the
# fix for the prior failure mode where an unguarded `npm run build` under
# `set -e` aborted bootstrap before uvicorn ever started.
ExecStartPre=-/bin/bash -c 'cd $REPO_PATH/pellier/backend && python3 generate_mcp_config.py 2>/dev/null || true'
ExecStartPre=-/bin/bash -c 'cd $REPO_PATH/pellier/frontend && npm run build || true'
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 $UVICORN_RELOAD_ARGS
Restart=always
RestartSec=3
StandardOutput=append:/tmp/pellier/uvicorn.log
StandardError=append:/tmp/pellier/uvicorn.log

[Install]
WantedBy=multi-user.target
EOF

# Let the workshop user restart the pellier unit without an interactive
# sudo password (rebuild-frontend / start-backend use systemctl).
SYSTEMCTL_BIN="$(command -v systemctl 2>/dev/null || echo /usr/bin/systemctl)"
SUDOERS_FILE="/etc/sudoers.d/99-pellier-systemctl-${CODE_EDITOR_USER}"
if printf '%s\n' \
    "${CODE_EDITOR_USER} ALL=(ALL) NOPASSWD: ${SYSTEMCTL_BIN} start pellier, ${SYSTEMCTL_BIN} stop pellier, ${SYSTEMCTL_BIN} restart pellier, ${SYSTEMCTL_BIN} is-active pellier, ${SYSTEMCTL_BIN} status pellier" \
    >"$SUDOERS_FILE" 2>/dev/null; then
    chmod 440 "$SUDOERS_FILE"
    if visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
        log "✅ Passwordless systemctl for unit pellier (${CODE_EDITOR_USER})"
    else
        warn "sudoers drop-in failed visudo check — removing $SUDOERS_FILE"
        rm -f "$SUDOERS_FILE"
    fi
else
    warn "Could not write sudoers drop-in at $SUDOERS_FILE"
fi

# Create log directory
mkdir -p /tmp/pellier
chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" /tmp/pellier

# Enable + start the single service for BOTH formats. builders gets
# --reload (baked into ExecStart above); workshop runs static. The
# frontend build is best-effort inside ExecStartPre, so the backend
# always comes up on :8000 even if the build or AgentCore provisioning
# fails. No format branch, no separate nohup path.
systemctl daemon-reload
systemctl enable pellier
systemctl start pellier

# Verify it started
sleep 8
if systemctl is-active --quiet pellier; then
    log "✅ pellier service running (port 8000, serves SPA + /api)"
else
    warn "pellier service failed to start — check: journalctl -u pellier"
fi

log "✅ Auto-start service configured"
log "   App URL (Workshop Studio): https://<cloudfront>/ports/8000/"
log "   App URL (local):           http://localhost:8000/"
log "   Frontend rebuild: run 'rebuild-frontend' alias or restart the service"

# ============================================================================
# STEP 15: STATUS MARKER
# ============================================================================
write_status_json "in_progress" "pending" ""
log "✅ Status marker created"

# ============================================================================
# STEP 16: WORKSHOP FORMAT — Pre-apply everything participants don't build
# ============================================================================
#
# The required path wires the floor_check tool body in
# services/agent_tools.py and then proves the same production path
# through retrieval, memory, Runtime, Gateway, Policy, and the Aurora
# audit ledger. Stock Keeper's system prompt and orchestrator are
# already in place before participants arrive.
#
# This block copies finished reference files from solutions/ into
# their runtime locations under pellier/backend/ and pellier/frontend/.
# Every src path is verified against the actual repo layout — if
# you add new pre-applies, double-check both src and dest exist.
#
# Solutions directory layout:
#   solutions/the-quiet-search/   — retrieval reference (observe-only)
#   solutions/closing-marcos-gap/ — the required-path (the only edited module)
#   solutions/the-ledger/    — governance reference (observe-only)
#
# Files we explicitly do NOT copy (participants build these):
#   inside agent_tools.py — the floor_check tool body only
if [ "${WORKSHOP_FORMAT:-builders}" = "builders" ] || [ "${WORKSHOP_FORMAT:-builders}" = "governed" ]; then
    log "=========================================="
    log "Workshop: processing ${WORKSHOP_FORMAT:-builders} managed path"
    log "=========================================="

    copy_solution() {
        local src="$1" dest="$2" label="$3"
        if [ -f "$REPO_PATH/$src" ]; then
            cp "$REPO_PATH/$src" "$REPO_PATH/$dest" && \
                log "  builders: $label" || warn "  builders: $label copy failed"
        else
            warn "  builders: $label — source missing at $src (skipped)"
        fi
    }

    if [ "${WORKSHOP_FORMAT:-builders}" = "builders" ]; then

    # ---- Specialist agents that aren't Stock Keeper ----
    # Curator handles recommendation turns (find_pieces_hybrid, style_match).
    # Experience Guide handles returns/care (returns_and_care, process_return,
    # escalate_to_stylist). Orchestrator is the dispatcher that routes between them.
    copy_solution "solutions/closing-marcos-gap/agents/curator.py" \
                  "pellier/backend/agents/curator.py" "Curator agent"
    copy_solution "solutions/closing-marcos-gap/agents/experience_guide.py" \
                  "pellier/backend/agents/experience_guide.py" "Experience Guide agent"
    copy_solution "solutions/closing-marcos-gap/agents/orchestrator.py" \
                  "pellier/backend/agents/orchestrator.py" "Orchestrator"

    # ---- agent_tools.py builders variant ----
    # Wires restock_shelf + running_low (everything Stock Keeper-adjacent
    # except floor_check itself). Participants will edit this file in
    # the required-path to add the floor_check body — and only that body.
    copy_solution "solutions/closing-marcos-gap/services/agent_tools_builders_preapply.py" \
                  "pellier/backend/services/agent_tools.py" "Agent tools (builders variant)"

    # ---- AgentCore production plumbing ----
    # Memory + Gateway + Policy + Runtime + Identity all import each
    # other and are referenced from pellier/backend/routes/*.py. Without
    # these the FastAPI app won't even start. Note the destination is
    # services/agentcore_runtime.py (NOT backend/agentcore_runtime.py
    # — the routes import services.agentcore_runtime).
    copy_solution "solutions/the-ledger/services/agentcore_runtime.py" \
                  "pellier/backend/services/agentcore_runtime.py" "AgentCore runtime"
    copy_solution "solutions/the-ledger/services/agentcore_memory.py" \
                  "pellier/backend/services/agentcore_memory.py" "AgentCore memory"
    copy_solution "solutions/the-ledger/services/agentcore_gateway.py" \
                  "pellier/backend/services/agentcore_gateway.py" "AgentCore gateway"
    # Policy is managed at the Gateway by the AgentCore CLI project. The old
    # local fake-Cedar service was removed; services/managed_policy.py is the
    # read side used by the operator surface.
    copy_solution "solutions/the-ledger/services/agentcore_identity.py" \
                  "pellier/backend/services/agentcore_identity.py" "AgentCore identity"
    copy_solution "solutions/the-ledger/services/cognito_auth.py" \
                  "pellier/backend/services/cognito_auth.py" "Cognito auth helper"
    copy_solution "solutions/the-ledger/services/otel_trace_extractor.py" \
                  "pellier/backend/services/otel_trace_extractor.py" "OTEL trace extractor"

    # ---- Frontend agent-identity hook ----
    # The Pellier chat drawer reads this to attach an identity claim to
    # every agent call. auth.ts + AuthModal + PreferencesModal +
    # AuthContext already ship complete in the live frontend tree (real
    # Cognito sign-in, no demo mode), so only the agent-identity hook is
    # dropped in here; the rest are not overwritten.
    copy_solution "solutions/the-ledger/frontend/agentIdentity.ts" \
                  "pellier/frontend/src/utils/agentIdentity.ts" "Frontend agent identity"
    else
        log "Governed format: preserving Stock Keeper and floor_check scaffolds for participant build"
    fi

    # ---- AgentCore full managed path ----
    #
    # Keep provisioning failures non-fatal until the backend has launched so
    # facilitators retain logs and a recoverable shell. The final health gate is
    # strict for WORKSHOP_FORMAT=governed and exits bootstrap non-zero unless
    # Memory, Runtime, Gateway, and Policy are all ready. Builders format keeps
    # the managed path optional.
    log "Provisioning full AgentCore managed path (Lambdas + Gateway + Runtime)..."
    export REPO_PATH="$REPO_PATH"
    MANAGED_OUTPUT_JSON="/tmp/pellier-agentcore-managed.json"
    AGENTCORE_OK=true

    # Keep both variable names during the transition; backend config resolves
    # either COGNITO_POOL_ID or COGNITO_USER_POOL_ID.
    export COGNITO_POOL="${COGNITO_POOL:-${COGNITO_POOL_ID:-${COGNITO_USER_POOL_ID:-}}}"
    export COGNITO_CLIENT="${COGNITO_CLIENT:-${COGNITO_CLIENT_ID:-}}"

    # Persist every provisioning INPUT to a recovery file so an operator can
    # re-run scripts/deploy/deploy_all.sh by hand if STEP 16 fails. These come
    # from CFN outputs and are in scope only here in UserData — they are NOT in
    # backend/.env (which holds runtime config, not provisioning inputs) and
    # vanish from an interactive shell. deploy_all.sh auto-sources this file.
    # Written BEFORE provisioning runs so it exists even on a failed deploy.
    PROVISION_ENV="$REPO_PATH/.provision.env"
    cat > "$PROVISION_ENV" << EOF
# Pellier provisioning inputs (CFN outputs) — auto-sourced by scripts/deploy/deploy_all.sh.
# Written by bootstrap-labs.sh STEP 16. Safe to re-source; contains no secrets
# beyond ARNs (the actual DB password lives in Secrets Manager, referenced by ARN).
export AWS_REGION='${AWS_REGION}'
export AWS_DEFAULT_REGION='${AWS_REGION}'
export STACKNAME='${STACKNAME:-${WORKSHOP_STACK_NAME:-}}'
export PGHOSTARN='${DB_CLUSTER_ARN:-}'
export PGSECRET='${DB_SECRET_ARN:-}'
export PGDATABASE='${DB_NAME:-pellier}'
export DB_CLUSTER_ARN='${DB_CLUSTER_ARN:-}'
export DB_SECRET_ARN='${DB_SECRET_ARN:-}'
export DB_NAME='${DB_NAME:-pellier}'
export COGNITO_POOL='${COGNITO_POOL:-}'
export COGNITO_CLIENT='${COGNITO_CLIENT:-}'
export COGNITO_TEST_CREDENTIALS_SECRET_ARN='${COGNITO_TEST_CREDENTIALS_SECRET_ARN:-}'
export COGNITO_CLIENT_SECRET_ARN='${COGNITO_CLIENT_SECRET_ARN:-}'
export AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN='${AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN:-}'
export AGENTCORE_RUNTIME_LOG_RETENTION_DAYS='${AGENTCORE_RUNTIME_LOG_RETENTION_DAYS:-30}'
EOF
    chmod 600 "$PROVISION_ENV" 2>/dev/null || true
    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$PROVISION_ENV" 2>/dev/null || true
    log "Wrote provisioning recovery file: $PROVISION_ENV"

    if ! command -v npx &>/dev/null || ! command -v python3 &>/dev/null; then
        warn "Missing npx or python3 — skipping managed AgentCore provisioning (backend will still start)"
        write_status_json "failed" "failed" "$MANAGED_OUTPUT_JSON"
        AGENTCORE_OK=false
    fi

    # The pinned CLI requires Node 20 or newer. Fail this managed provisioning
    # beat cleanly if the base image fell back to an older runtime.
    if [ "$AGENTCORE_OK" = true ]; then
        _ac_node_major="$(node --version 2>/dev/null | sed 's/^v//' | cut -d. -f1)"
        if ! echo "$_ac_node_major" | grep -qE '^[0-9]+$' || [ "$_ac_node_major" -lt 20 ]; then
            warn "Node $(node --version 2>/dev/null || echo 'none') (<20) — @aws/agentcore Runtime deploy cannot run. Skipping managed AgentCore provisioning; Pellier still starts. Fix: install Node 20 (see bootstrap-environment.sh) and re-run scripts/deploy/deploy_all.sh."
            write_status_json "failed" "failed" "$MANAGED_OUTPUT_JSON"
            AGENTCORE_OK=false
        fi
    fi

    # Tee the full provisioning run (incl. `agentcore deploy` stdout/stderr) to
    # a dedicated log so a failed run has a single, predictable place to look —
    # /var/log/pellier-agentcore.log — instead of grepping the master bootstrap
    # log. pipefail propagates the python3 exit status through the pipe.
    AGENTCORE_LOG="/var/log/pellier-agentcore.log"
    if [ "$AGENTCORE_OK" = true ] && ! sudo -u "$CODE_EDITOR_USER" bash -c "
        export PATH=\"/usr/bin:/usr/local/bin:\$HOME/.local/bin:\$PATH\"
        node --version  # log the node the CLI will actually use
        export AWS_REGION='$AWS_REGION'
        export AWS_DEFAULT_REGION='$AWS_REGION'
        export REPO_PATH='$REPO_PATH'
        export DB_CLUSTER_ARN='${DB_CLUSTER_ARN:-}'
        export DB_SECRET_ARN='${DB_SECRET_ARN:-}'
        export DB_NAME='${DB_NAME:-pellier}'
        export COGNITO_POOL='${COGNITO_POOL:-}'
        export COGNITO_CLIENT='${COGNITO_CLIENT:-}'
        export COGNITO_TEST_CREDENTIALS_SECRET_ARN='${COGNITO_TEST_CREDENTIALS_SECRET_ARN:-}'
        export COGNITO_CLIENT_SECRET_ARN='${COGNITO_CLIENT_SECRET_ARN:-}'
        export AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN='${AGENTCORE_RUNTIME_LOG_KMS_KEY_ARN:-}'
        export AGENTCORE_RUNTIME_LOG_RETENTION_DAYS='${AGENTCORE_RUNTIME_LOG_RETENTION_DAYS:-30}'
        python3 '$REPO_PATH/scripts/provision_agentcore_end_to_end.py' \
            --repo-path '$REPO_PATH' \
            --output-json '$MANAGED_OUTPUT_JSON'
    " 2>&1 | tee "$AGENTCORE_LOG"; then
        warn "Managed AgentCore provisioning failed; see $AGENTCORE_LOG and $MANAGED_OUTPUT_JSON (backend will still start)"
        write_status_json "failed" "failed" "$MANAGED_OUTPUT_JSON"
        AGENTCORE_OK=false
    fi

    if [ "$AGENTCORE_OK" = true ]; then
        RUNTIME_ARN="$(jq -r '.runtime.runtime_arn // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        MEMORY_ID="$(jq -r '.memory.memory_id // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        GATEWAY_ID="$(jq -r '.gateway.gateway_id // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        GATEWAY_URL="$(jq -r '.gateway.gateway_url // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        GATEWAY_ARN="$(jq -r '.gateway.gateway_arn // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        POLICY_ENGINE_ID="$(jq -r '.policy.policy_engine_id // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        MANAGED_STATUS="$(jq -r '.status // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        if [ -z "$RUNTIME_ARN" ] || [ -z "$MEMORY_ID" ] \
            || [ -z "$GATEWAY_ID" ] || [ -z "$GATEWAY_URL" ] \
            || [ -z "$GATEWAY_ARN" ] || [ -z "$POLICY_ENGINE_ID" ] \
            || [ "$MANAGED_STATUS" != "ready" ]; then
            warn "Managed provisioning output missing Runtime/Memory/Gateway/Policy readiness (backend will still start)"
            write_status_json "failed" "failed" "$MANAGED_OUTPUT_JSON"
            AGENTCORE_OK=false
        fi
    fi

    if [ "$AGENTCORE_OK" = true ]; then
        upsert_env "AGENTCORE_RUNTIME_ENDPOINT" "$RUNTIME_ARN" "$REPO_PATH/.env"
        upsert_env "AGENTCORE_MEMORY_ID" "$MEMORY_ID" "$REPO_PATH/.env"
        upsert_env "AGENTCORE_GATEWAY_ID" "$GATEWAY_ID" "$REPO_PATH/.env"
        upsert_env "AGENTCORE_GATEWAY_ARN" "$GATEWAY_ARN" "$REPO_PATH/.env"
        upsert_env "AGENTCORE_GATEWAY_URL" "$GATEWAY_URL" "$REPO_PATH/.env"
        upsert_env "USE_AGENTCORE_RUNTIME" "true" "$REPO_PATH/.env"
        # Managed AgentCore Policy engine (4th pillar). The provisioner cannot
        # report ready without this id; keep the explicit guard because Lab 4
        # and the Pellier Observatory Policy surface both read it.
        if [ -n "$POLICY_ENGINE_ID" ]; then
            upsert_env "AGENTCORE_POLICY_ENGINE_ID" "$POLICY_ENGINE_ID" "$REPO_PATH/.env"
            log "✅ Managed AgentCore Policy engine: $POLICY_ENGINE_ID"
        fi
        chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH/.env"
        write_status_json "complete" "ready" "$MANAGED_OUTPUT_JSON"
        log "✅ AgentCore managed path ready"
    else
        warn "AgentCore managed path NOT ready — continuing so the backend launches. The health gate will flag this; see $AGENTCORE_LOG, then re-run provisioning to recover the Runtime/Gateway path."
        # Preserve CLI-created resources in backend configuration even when a
        # later live proof fails. AGENTCORE_RUNTIME_ENDPOINT stays unset on
        # purpose so the health gate cannot report the Runtime as ready.
        PARTIAL_MEMORY_ID="$(jq -r '.memory.memory_id // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        PARTIAL_GATEWAY_ID="$(jq -r '.gateway.gateway_id // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        PARTIAL_GATEWAY_URL="$(jq -r '.gateway.gateway_url // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        PARTIAL_GATEWAY_ARN="$(jq -r '.gateway.gateway_arn // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        PARTIAL_POLICY_ID="$(jq -r '.policy.policy_engine_id // empty' "$MANAGED_OUTPUT_JSON" 2>/dev/null || true)"
        if [ -n "$PARTIAL_MEMORY_ID" ]; then
            upsert_env "AGENTCORE_MEMORY_ID" "$PARTIAL_MEMORY_ID" "$REPO_PATH/.env"
            log "Salvaged CLI-managed Memory id into .env despite failed proof"
        fi
        if [ -n "$PARTIAL_GATEWAY_ID" ]; then
            upsert_env "AGENTCORE_GATEWAY_ID" "$PARTIAL_GATEWAY_ID" "$REPO_PATH/.env"
        fi
        if [ -n "$PARTIAL_GATEWAY_URL" ]; then
            upsert_env "AGENTCORE_GATEWAY_URL" "$PARTIAL_GATEWAY_URL" "$REPO_PATH/.env"
            log "Salvaged live Gateway endpoint into .env despite failed provisioning"
        fi
        if [ -n "$PARTIAL_GATEWAY_ARN" ]; then
            upsert_env "AGENTCORE_GATEWAY_ARN" "$PARTIAL_GATEWAY_ARN" "$REPO_PATH/.env"
            log "Salvaged live Gateway ARN into .env despite failed provisioning"
        fi
        if [ -n "$PARTIAL_POLICY_ID" ]; then
            upsert_env "AGENTCORE_POLICY_ENGINE_ID" "$PARTIAL_POLICY_ID" "$REPO_PATH/.env"
            log "Salvaged live Policy engine id into .env despite failed provisioning"
        fi
        chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH/.env" 2>/dev/null || true
    fi

    # Recursively re-own the app tree as the participant.
    chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH/pellier/"

    # The AgentCore project lives at REPO level (.agentcore-project/), OUTSIDE
    # backend_dir — the CodeZip packager copies the whole code-location, so a
    # project rooted inside it copied itself recursively (ENAMETOOLONG,
    # box-verified 2026-06-12). Own it for the participant so the `agentcore`
    # function can read agentcore/.cli/deployed-state.json — the file
    # `agentcore status` needs. If you ever narrow this chown, keep the
    # .agentcore-project subtree participant-owned or the cloud-inspection beat breaks.
    if [ -d "$REPO_PATH/.agentcore-project" ]; then
        chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$REPO_PATH/.agentcore-project/"
    fi

    # Install the exact AgentCore CLI used by provisioning. Lab 4 deploys one
    # participant policy, so an npx registry fetch cannot sit on the room clock.
    # NOT gated on AGENTCORE_OK: a Runtime-only failure still leaves Gateway +
    # Policy independently usable, and `agentcore status` is exactly the tool
    # for diagnosing the failed beat (box-verified cascade 2026-06-12: gating
    # this on AGENTCORE_OK left the participant with no CLI at all).
    if command -v npm &>/dev/null; then
        log "Installing pinned AgentCore CLI globally (@aws/agentcore@0.26.0)..."
        npm install -g @aws/agentcore@0.26.0 >/dev/null 2>&1 \
            && log "✅ agentcore CLI installed globally ($(command agentcore --version 2>/dev/null || echo 'version check skipped'))" \
            || warn "Global @aws/agentcore@0.26.0 install failed — the agentcore function will fall back to npx; see npm logs."
    fi

    # The pellier.service unit (STEP 14) already runs uvicorn with --reload
    # for builders format and rebuilds the frontend in ExecStartPre. Now
    # that the solution files + AgentCore env are in place, restart the unit
    # once so it picks them up. systemd owns the process — no nohup, no PID
    # file, no second backend fighting for :8000. A restart failure is
    # non-fatal (the health gate reports it); --reload keeps the live-edit DX.
    log "Restarting pellier service to pick up ${WORKSHOP_FORMAT:-builders} env..."
    systemctl restart pellier || warn "pellier restart failed — check: journalctl -u pellier"

    sleep 8
    if systemctl is-active --quiet pellier; then
        log "✅ ${WORKSHOP_FORMAT:-builders}: pellier service running (systemd)"
    else
        warn "pellier service not active after restart — check: journalctl -u pellier"
    fi

    if [ "${WORKSHOP_FORMAT:-builders}" = "governed" ] && [ "$AGENTCORE_OK" = true ]; then
        log "Restoring canonical governed state after live Runtime and Policy proof..."
        if sudo -u "$CODE_EDITOR_USER" bash -c "
            export PELLIER_REPO='$REPO_PATH'
            bash '$REPO_PATH/scripts/reset-governed-workshop.sh'
        " 2>&1 | tee /var/log/pellier-governed-reset.log; then
            log "✅ Governed database, evidence, and Policy state reset"
        else
            fail "Governed reset failed; see /var/log/pellier-governed-reset.log"
        fi
    fi

    log "✅ ${WORKSHOP_FORMAT:-builders} managed path processed, pellier service restarted"
fi

if [ "${WORKSHOP_FORMAT:-builders}" != "builders" ] && [ "${WORKSHOP_FORMAT:-builders}" != "governed" ]; then
    write_status_json "complete" "not_applicable" ""
fi

# ============================================================================
# STEP 17: WRITE TEST CREDENTIALS FILE
# ============================================================================
if [ -n "${COGNITO_TEST_CREDENTIALS_SECRET_ARN:-}" ] && [ -x "$REPO_PATH/scripts/write-test-credentials.sh" ]; then
    log "Writing test credentials file..."
    export COGNITO_TEST_CREDENTIALS_SECRET_ARN COGNITO_HOSTED_UI_URL AWS_REGION \
           CODE_EDITOR_USER HOME_FOLDER
    bash "$REPO_PATH/scripts/write-test-credentials.sh" 2>&1 | tee /var/log/pellier-write-credentials.log || \
        warn "write-test-credentials.sh reported issues"
fi

# ============================================================================
# STEP 17b: PRE-BAKE THE GOVERNED BEARER TOKEN HELPER
# ============================================================================
# Labs 3 and 4 run on the authenticated managed rail and
# needs a Cognito access token. In a self-paced room (no facilitator to unblock
# a failed `admin-initiate-auth`), typing that command is the #1 friction +
# failure mode. So we pre-bake a one-command helper that mints a FRESH token
# (tokens expire ~1h, so we generate on demand rather than bake a stale one):
#
#     source ~/pellier-token.sh      # sets $PELLIER_TOKEN for the curl below
#
# The participant never types Cognito plumbing — they get the learning (managed
# Cedar gates at the Gateway), not the auth ceremony. Identity is still REAL:
# the token is a genuine Cognito JWT the Gateway validates.
if [ -n "${COGNITO_TEST_CREDENTIALS_SECRET_ARN:-}" ] && [ -n "${COGNITO_POOL:-${COGNITO_POOL_ID:-}}" ]; then
    log "Writing governed token helper (~/pellier-token.sh)..."
    _TOKEN_POOL="${COGNITO_POOL:-${COGNITO_POOL_ID}}"
    _TOKEN_CLIENT="${COGNITO_CLIENT:-${COGNITO_CLIENT_ID:-}}"
    # The participant's ~ is /home/$CODE_EDITOR_USER, NOT $HOME_FOLDER
    # (/workshop) — writing only to $HOME_FOLDER made `source
    # ~/pellier-token.sh` a No-such-file (box-verified 2026-06-12). Write to
    # the real home; symlink at $HOME_FOLDER for any content that used it.
    _TOKEN_HELPER="/home/$CODE_EDITOR_USER/pellier-token.sh"
    cat > "$_TOKEN_HELPER" <<TOKENEOF
#!/usr/bin/env bash
# Mint a fresh Cognito access token for the governed Runtime and Policy proof.
# Usage:  source ~/pellier-token.sh          # default persona (Marco)
#         source ~/pellier-token.sh anna     # mint Anna's token instead
#         source ~/pellier-token.sh theo     # mint Theo's
# The Cognito users are named after the personas, so the access token carries
# the chosen name (the access token's \`username\` claim, lowercased — NOT
# cognito:username, that's the ID token; box-verified 2026-06-12) through the
# JWT-gated Gateway – identity passthrough you can see. Case-insensitive match;
# an unknown/no arg falls back to the first user (Marco). Sets \$PELLIER_TOKEN.
_want="\${1:-}"
_creds=\$(aws secretsmanager get-secret-value \\
  --secret-id "$COGNITO_TEST_CREDENTIALS_SECRET_ARN" --region "$AWS_REGION" \\
  --query SecretString --output text 2>/dev/null)
_u=\$(echo "\$_creds" | python3 -c 'import sys,json;w=(sys.argv[1] if len(sys.argv)>1 else "").strip().lower();us=json.load(sys.stdin)["users"];print(next((x for x in us if x["username"].lower()==w), us[0])["username"])' "\$_want" 2>/dev/null)
_p=\$(echo "\$_creds" | python3 -c 'import sys,json;w=(sys.argv[1] if len(sys.argv)>1 else "").strip().lower();us=json.load(sys.stdin)["users"];print(next((x for x in us if x["username"].lower()==w), us[0])["password"])' "\$_want" 2>/dev/null)
# The app client is configured WITH a secret, so admin-initiate-auth must
# send SECRET_HASH = b64(hmac-sha256(client_secret, username+client_id)) or
# Cognito rejects with NotAuthorizedException (box-verified 2026-06-12).
_ap="USERNAME=\$_u,PASSWORD=\$_p"
_csarn='${COGNITO_CLIENT_SECRET_ARN:-}'
if [ -n "\$_csarn" ]; then
  _csec=\$(aws secretsmanager get-secret-value --secret-id "\$_csarn" --region "$AWS_REGION" --query SecretString --output text 2>/dev/null)
  _csec=\$(echo "\$_csec" | python3 -c 'import sys,json;s=sys.stdin.read().strip();print(json.loads(s).get("client_secret",s) if s.startswith("{") else s)' 2>/dev/null)
  _sh=\$(python3 -c 'import sys,hmac,hashlib,base64;u,c,k=sys.argv[1:4];print(base64.b64encode(hmac.new(k.encode(),(u+c).encode(),hashlib.sha256).digest()).decode())' "\$_u" "$_TOKEN_CLIENT" "\$_csec" 2>/dev/null)
  [ -n "\$_sh" ] && _ap="\$_ap,SECRET_HASH=\$_sh"
fi
export PELLIER_TOKEN=\$(aws cognito-idp admin-initiate-auth \\
  --user-pool-id "$_TOKEN_POOL" --client-id "$_TOKEN_CLIENT" \\
  --auth-flow ADMIN_USER_PASSWORD_AUTH \\
  --auth-parameters "\$_ap" \\
  --query 'AuthenticationResult.AccessToken' --output text 2>/dev/null)
if [ -n "\$PELLIER_TOKEN" ] && [ "\$PELLIER_TOKEN" != "None" ]; then
  echo "✅ \$PELLIER_TOKEN minted for \$_u (use: -H \"Authorization: Bearer \\\$PELLIER_TOKEN\")"
else
  echo "✗ Token mint failed – check Cognito provisioning (/var/log/pellier-agentcore.log)"
fi
TOKENEOF
    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$_TOKEN_HELPER" 2>/dev/null || true
    ln -sf "$_TOKEN_HELPER" "$HOME_FOLDER/pellier-token.sh" 2>/dev/null || true
    log "✅ Governed token helper ready: source ~/pellier-token.sh"
fi

# ============================================================================
# STEP 18: SEED SAMPLE PREFERENCES (users 1-3)
# ============================================================================
if [ -n "${COGNITO_USER_POOL_ID:-}" ] && [ -x "$REPO_PATH/scripts/seed-sample-preferences.sh" ]; then
    log "Seeding sample preferences for test users 1-3..."
    export COGNITO_USER_POOL_ID COGNITO_CLIENT_ID COGNITO_CLIENT_SECRET_ARN \
           COGNITO_TEST_CREDENTIALS_SECRET_ARN AWS_REGION
    export BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
    bash "$REPO_PATH/scripts/seed-sample-preferences.sh" 2>&1 | tee /var/log/pellier-seed-preferences.log || \
        warn "seed-sample-preferences.sh reported issues"
fi

# ============================================================================
# STEP 18b: SEED RLS PRINCIPAL MAPPINGS
#
# Migration 016 keys its Row-Level Security policies on a verified Cognito
# subject, and Cognito assigns each subject at user-creation time, so no
# migration can carry them. Until this runs the mapping table is empty — which
# does not read as "governance", it reads as a broken application: every
# signed-in shopper is denied their own orders.
#
# Runs after Cognito provisioning because it resolves username -> sub against
# the live pool. Non-fatal: the app connects as the table owner today, so an
# unseeded mapping degrades the governed exercise rather than the storefront.
# ============================================================================
if [ -n "${COGNITO_USER_POOL_ID:-${COGNITO_POOL_ID:-}}" ] \
   && [ -f "$REPO_PATH/scripts/seed_principal_mappings.py" ]; then
    log "Seeding RLS principal mappings (Cognito subject -> customer scope)..."
    export COGNITO_POOL_ID="${COGNITO_POOL_ID:-$COGNITO_USER_POOL_ID}"
    export COGNITO_REGION="${COGNITO_REGION:-$AWS_REGION}"
    if python3 "$REPO_PATH/scripts/seed_principal_mappings.py" 2>&1 \
         | tee /var/log/pellier-seed-principal-mappings.log; then
        log "✅ Principal mappings seeded"
    else
        warn "seed_principal_mappings.py reported issues — RLS will deny signed-in shoppers until it succeeds"
    fi
fi

# ============================================================================
# SUMMARY
# ============================================================================
log "=========================================="
log "Stage 2: Labs Bootstrap Complete!"
log "=========================================="
echo ""
echo "✅ Pellier Backend (FastAPI + Strands) installed"
echo "✅ Pellier Frontend (React) dependencies installed"
echo "✅ Database setup complete (expanded product corpus + warehouse inventory)"
echo "✅ MCP server config written to pellier/config/mcp-server-config.json"
echo "✅ Bash environment configured (psql ready)"
if [ "${WORKSHOP_FORMAT:-builders}" = "builders" ]; then
    echo "✅ pellier systemd service enabled — python3 -m uvicorn --reload on :8000 (live .py edits)"
else
    echo "✅ pellier systemd service enabled (single process on :8000)"
fi
echo ""
echo "🌐 App is live at: https://<cloudfront>/ports/8000/"
echo "   Frontend + API both served by one uvicorn process (systemd)."
echo "   Edits to pellier/backend/*.py reload automatically (builders)."
echo "   Edits to pellier/frontend/src/ require: rebuild-frontend"
echo ""
echo "Quick Commands:"
echo "  psql                             # Connect to database"
echo "  journalctl -fu pellier           # Backend service log (both formats)"
echo "  cat /var/log/pellier-agentcore.log # AgentCore deploy log (Gateway + Runtime)"
echo "  rebuild-frontend                 # Rebuild SPA + restart app"
echo "  health                           # One-shot readiness check (catalog/memory/runtime)"
echo ""

# ============================================================================
# STEP 19: POST-BOOT HEALTH GATE
# ============================================================================
# One consolidated PASS/FAIL summary so the facilitator sees readiness at a
# glance. Give the backend a moment to come up first. A failed gate is fatal for
# the governed workshop and warning-only for the one-hour builders format.
HEALTH_GATE_OK=true
if [ -x "$REPO_PATH/scripts/health-gate.sh" ]; then
    log "Running post-boot health gate..."
    sleep 5
    if ! sudo -u "$CODE_EDITOR_USER" bash -c "
        export PELLIER_REPO='$REPO_PATH'
        bash '$REPO_PATH/scripts/health-gate.sh'
    " 2>&1 | tee /var/log/pellier-health-gate.log; then
        HEALTH_GATE_OK=false
        warn "Health gate reported NOT READY — see /var/log/pellier-health-gate.log"
    fi
fi

log "=========================================="

if [ "$HEALTH_GATE_OK" != true ] && [ "${WORKSHOP_FORMAT:-builders}" = "governed" ]; then
    fail "Governed workshop readiness failed; CloudFormation must not report this environment ready"
fi

exit 0
