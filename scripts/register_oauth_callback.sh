#!/usr/bin/env bash
# =============================================================================
# register_oauth_callback.sh — register the CloudFront OAuth callback on the
# Cognito app client after the distribution exists.
# =============================================================================
# WHY THIS RUNS POST-BOOT INSTEAD OF IN CLOUDFORMATION
#
# The template cannot register the callback statically: the distribution's
# origin is the Code Editor instance (CloudFront -> Instance), and the
# instance UserData reads the app client id (Instance -> Client), so a client
# property referencing the distribution (Client -> CloudFront) would close a
# circular dependency. The distribution is also created only AFTER UserData
# signals success, so bootstrap itself cannot see it either. This script is
# started as a detached systemd oneshot at the end of bootstrap and polls
# until the distribution appears.
#
# It then does three idempotent things:
#
#   1. Registers https://<cf-domain>/api/auth/callback (and a logout URL) on
#      the Cognito app client. Cognito exact-matches redirect_uri against
#      CallbackURLs and rejects non-localhost http URLs, so without this the
#      hosted-UI sign-in always fails with redirect_mismatch.
#   2. Pins OAUTH_REDIRECT_URI and APP_BASE_URL in the repo .env. The backend
#      falls back to X-Forwarded-Proto derivation, but CloudFront does not
#      send that header, so the derived scheme behind nginx is http — which
#      Cognito rejects. An explicit https URI removes the ambiguity.
#   3. Restarts the pellier unit so the backend picks up the new .env.
#
# Failure mode is benign: if the distribution never appears the unit times
# out, sign-in stays unregistered (its prior state), and nothing else on the
# box is affected. Requires cognito-idp:UpdateUserPoolClient and
# cloudfront:ListDistributions on the instance role.
# =============================================================================
set -uo pipefail

HOME_FOLDER="${HOME_FOLDER:-/workshop}"
REPO_PATH="${REPO_PATH:-$HOME_FOLDER/sample-pellier-agentic-search-apg}"
ENV_FILE="$REPO_PATH/.env"
POLL_ATTEMPTS="${POLL_ATTEMPTS:-40}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-30}"

log() { echo "[$(date +'%H:%M:%S')] $1"; }

get_env() {
    # Values in .env are written as KEY='value' by bootstrap; accept unquoted
    # too. Last occurrence wins, matching dotenv semantics.
    sed -n "s/^$1='\{0,1\}\([^']*\)'\{0,1\}$/\1/p" "$ENV_FILE" | tail -1
}

if [ ! -f "$ENV_FILE" ]; then
    log "no $ENV_FILE — not a bootstrapped box; nothing to register"
    exit 0
fi

AUTH_MODE="$(get_env AUTH_MODE)"
POOL_ID="$(get_env COGNITO_USER_POOL_ID)"
CLIENT_ID="$(get_env COGNITO_CLIENT_ID)"
AWS_REGION="$(get_env AWS_DEFAULT_REGION)"
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"

if [ "$AUTH_MODE" != "cognito" ] || [ -z "$POOL_ID" ] || [ -z "$CLIENT_ID" ]; then
    log "Cognito not configured (AUTH_MODE=$AUTH_MODE) — nothing to register"
    exit 0
fi

for tool in aws jq curl; do
    command -v "$tool" >/dev/null || { log "ERROR: $tool not on PATH"; exit 1; }
done

# --- Discover this instance's CloudFront distribution ------------------------
# The distribution's sole origin is this instance's public DNS name, so match
# on that rather than on tags (list-distributions does not return tags).
imds_public_hostname() {
    local token
    token="$(curl -sS --max-time 5 -X PUT \
        'http://169.254.169.254/latest/api/token' \
        -H 'X-aws-ec2-metadata-token-ttl-seconds: 300')" || return 1
    curl -sS --max-time 5 \
        -H "X-aws-ec2-metadata-token: $token" \
        'http://169.254.169.254/latest/meta-data/public-hostname'
}

CF_DOMAIN=""
for attempt in $(seq 1 "$POLL_ATTEMPTS"); do
    SELF_DNS="$(imds_public_hostname)" || SELF_DNS=""
    if [ -n "$SELF_DNS" ]; then
        CF_DOMAIN="$(aws cloudfront list-distributions --output text --query \
            "DistributionList.Items[?Origins.Items[?DomainName=='$SELF_DNS']].DomainName | [0]" \
            2>/dev/null)" || CF_DOMAIN=""
        [ "$CF_DOMAIN" = "None" ] && CF_DOMAIN=""
    fi
    if [ -n "$CF_DOMAIN" ]; then
        log "found distribution $CF_DOMAIN fronting $SELF_DNS (attempt $attempt)"
        break
    fi
    log "distribution not visible yet (attempt $attempt/$POLL_ATTEMPTS); retrying in ${POLL_INTERVAL_SECONDS}s"
    sleep "$POLL_INTERVAL_SECONDS"
done

if [ -z "$CF_DOMAIN" ]; then
    log "ERROR: no CloudFront distribution found for this instance after $POLL_ATTEMPTS attempts"
    exit 1
fi

CALLBACK_URL="https://$CF_DOMAIN/api/auth/callback"
LOGOUT_URL="https://$CF_DOMAIN/ports/8000/"

# --- Register the callback on the app client ---------------------------------
# UpdateUserPoolClient resets every omitted field to its default, so rebuild
# the request from the fields the template actually sets (plus the required
# ids) instead of echoing the whole describe payload back — describe includes
# read-only fields (ClientSecret, timestamps) that update rejects.
CLIENT_JSON="$(aws cognito-idp describe-user-pool-client \
    --user-pool-id "$POOL_ID" --client-id "$CLIENT_ID" \
    --query 'UserPoolClient' --output json)" || {
    log "ERROR: describe-user-pool-client failed for $CLIENT_ID"
    exit 1
}

if printf '%s' "$CLIENT_JSON" | jq -e --arg cb "$CALLBACK_URL" \
    '(.CallbackURLs // []) | index($cb)' >/dev/null; then
    log "callback already registered: $CALLBACK_URL"
else
    UPDATE_JSON="$(printf '%s' "$CLIENT_JSON" | jq \
        --arg cb "$CALLBACK_URL" --arg lo "$LOGOUT_URL" '
        {
          UserPoolId, ClientId, ClientName,
          RefreshTokenValidity, AccessTokenValidity, IdTokenValidity,
          TokenValidityUnits, ExplicitAuthFlows, SupportedIdentityProviders,
          AllowedOAuthFlows, AllowedOAuthScopes, AllowedOAuthFlowsUserPoolClient,
          CallbackURLs: ((.CallbackURLs // []) + [$cb] | unique),
          LogoutURLs: ((.LogoutURLs // []) + [$lo] | unique)
        } | with_entries(select(.value != null))')"
    aws cognito-idp update-user-pool-client \
        --cli-input-json "$UPDATE_JSON" >/dev/null || {
        log "ERROR: update-user-pool-client failed"
        exit 1
    }
    log "registered callback $CALLBACK_URL and logout $LOGOUT_URL"
fi

# --- Pin the redirect in .env and restart the backend ------------------------
if [ "$(get_env OAUTH_REDIRECT_URI)" = "$CALLBACK_URL" ] &&
   [ "$(get_env APP_BASE_URL)" = "https://$CF_DOMAIN" ]; then
    log ".env already pinned to $CF_DOMAIN — no restart needed"
    exit 0
fi

sed -i "/^OAUTH_REDIRECT_URI=/d;/^APP_BASE_URL=/d" "$ENV_FILE"
{
    echo "OAUTH_REDIRECT_URI='$CALLBACK_URL'"
    echo "APP_BASE_URL='https://$CF_DOMAIN'"
} >> "$ENV_FILE"
log "pinned OAUTH_REDIRECT_URI and APP_BASE_URL in $ENV_FILE"

if systemctl is-enabled pellier >/dev/null 2>&1; then
    systemctl restart pellier || log "WARNING: pellier restart failed — restart it manually"
    log "restarted pellier to pick up the pinned redirect"
fi
log "OAuth callback registration complete"
