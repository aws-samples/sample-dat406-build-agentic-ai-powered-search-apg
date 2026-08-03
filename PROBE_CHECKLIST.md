# Fresh-account probe checklist

The authoritative gate before the Pellier workshop is participant-ready. Run this
**on a freshly-provisioned Workshop Studio box, as the participant user**, after
CloudFormation → bootstrap has completed. The checks are safe to repeat; the
governed dry run uses idempotent writes and restores the participant state.

Why this exists: most of the recent work is statically green but carries
"confirm on-box" markers — the dev sandbox has no AWS creds, no npm registry, and
no provisioned stack. This run is where "believed fixed" becomes "proven," and
where content `> probe note:` markers get reconciled to real captured output.

> **Capture + sanitize as you go.** Where a step says CAPTURE, copy the real
> output into the matching content `> probe note`, and **replace any ARN /
> account id / gateway id with `<placeholder>`** before it lands in published
> content.

---

> **Region: us-east-1.** Confirm the stack launched in us-east-1 and that `.env`
> reads `AWS_REGION=us-east-1` before you start. The commands below read
> `$AWS_REGION` / `.env`, and the Bedrock access gate plus AgentCore availability
> assumption are both validated in us-east-1.

## 0. Prereqs (fail fast here)

```bash
cd /workshop/sample-pellier-agentic-search-apg

node --version                 # MUST be >= v20  (Gate #1: Node-20 robustness fix)
type agentcore                 # should print the shell FUNCTION (not "not found", not an alias)
which -a agentcore             # confirm no stale Python starter-toolkit binary shadows it

# Region + required managed pieces. AWS_REGION must read us-east-1; an empty
# Memory, Runtime, Gateway, or Policy value is a failed governed environment.
grep -E 'AWS_REGION|USE_AGENTCORE_RUNTIME|AGENTCORE_RUNTIME_ENDPOINT|AGENTCORE_GATEWAY_URL|MCP_GATEWAY_URL|AGENTCORE_POLICY_ENGINE_ID|AGENTCORE_MEMORY_ID' \
  pellier/backend/.env
```

**Pass:** Node ≥ 20; `agentcore` is a function; `AWS_REGION=us-east-1`; `.env` has
Memory, Runtime, Gateway, and Policy identifiers. If Node < 20 →
the NodeSource fix regressed; stop and fix bootstrap before anything else.

---

## 1. Provisioning health (Gate #1: the 4 fresh-account fixes + model access)

```bash
python3 scripts/check_model_access.py        # Gate #5: Bedrock access (Opus, Sonnet, Embed v4, Rerank v3.5)
bash scripts/health-gate.sh                  # Requires 120 rows + Memory/Runtime/Gateway/Policy proof
jq '.status, .verification' /tmp/pellier-agentcore-managed.json
cat /var/log/pellier-agentcore.log           # the STEP-16 provisioning transcript
```

What each fix is being confirmed against (these were the bugs from the *last*
fresh-account run):
- **Cedar action self-correct** — grep the log for `accepted action identifier:` →
  **CAPTURE which candidate won** (`pellier-concierge-experience-target___process_return`
  triple-underscore is the dat403-verified guess; the engine's `did you mean` hint
  wins if different). This tells us the real GA action format.
- **Node 20** — provisioning didn't die on `SyntaxError: Invalid regular expression flags`.
- **CDK `s3:PutLifecycleConfiguration`** — no `CDKToolkit StagingBucket CREATE_FAILED`.
- **`deploy_all.sh` env self-resolve** — only relevant if you hand-re-run it; it
  should resolve CFN outputs from `STACKNAME` or print a clean export list (no
  `PGHOSTARN: unbound variable` crash).

**Pass:** `check_model_access` all-green (or clean Sonnet fallback);
health-gate `READY`; the receipt proves exactly four Gateway targets and 15
live-discovered MCP tools, says `runtime_invoke_smoke.rail=gateway-mcp`, and
records both live Policy decisions as true. If model access flaps "still
processing," wait ~15 min and re-run.

---

## 2. AgentCore CLI and generated Runtime config

```bash
agentcore --version
agentcore status --json
jq '.runtimes[] | {
  name,
  authorizerType,
  authorizerConfiguration,
  requestHeaderAllowlist,
  envVars
}' .agentcore-project/pellier/agentcore/agentcore.json
```

**Pass:** version is `0.18.0`; status reports the deployed Runtime `READY`; the
generated config shows `CUSTOM_JWT`, an `Authorization` request-header
allowlist, and the live Gateway URL.

---

## 3. Cloud Runtime beat — Act II §5 (Gate #3 cont.)

```bash
# Project dir readable by participant? (repo-level chown in bootstrap-labs.sh covers it)
ls -la .agentcore-project/pellier/agentcore/.cli/deployed-state.json

agentcore status --json        # RESOLVED 2026-06-13 (box-captured, reconciled into §5): top-level
                               # {success, projectName, targetName, targetRegion, resources[],
                               # deployedState{}, logPath}; the agent resource carries
                               # deploymentState:"deployed" + detail:"READY" + identifier (runtime
                               # ARN) + invocationUrl (URL-encoded ARN — same data plane the raw
                               # curl uses). NOTE: CUSTOM_JWT does NOT appear in status output —
                               # it's in agentcore/agentcore.json; §5 "Expected" no longer claims it.
agentcore status               # run again from ~ : `cd ~ && agentcore status` confirms the function's cd works anywhere

source ~/pellier-token.sh marco   # must print "✅ … minted for Marco" + set non-empty $PELLIER_TOKEN
#   CAPTURE: confirm the print names "Marco" (not a UUID / email). Then confirm the
#   token literally CARRIES that identity — decode the access-token payload:
echo "$PELLIER_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool | grep -E 'username|client_id|token_use'
#   KEY CLAIM (Act II §5 identity-passthrough expand + Act III §2a): RESOLVED
#   on-box 2026-06-12 — the access token's field is `username` (NOT
#   `cognito:username`, that's the ID token) and the value is LOWERCASED
#   ("marco"/"anna" — Cognito normalizes case-insensitive usernames). Content
#   reconciled. Also try: `source ~/pellier-token.sh anna` -> payload
#   username == "anna" (proves the persona arg selects the user).
#   DO NOT paste a real token anywhere.

# PRIMARY: the same raw CUSTOM_JWT transport used by the production backend.
set -a; source .env; set +a
python3 scripts/deploy/test_runtime.py \
  --runtime-arn "$AGENTCORE_RUNTIME_ENDPOINT" \
  --token "$PELLIER_TOKEN" \
  --prompt "Find linen travel pieces for a warm-weather trip."
#   CAPTURE the JSON response. It must include rail="gateway-mcp".

# SECONDARY: the application SSE route must reach the same Runtime rail.
SESSION="probe-$(date +%s)"
curl -sN -X POST http://localhost:8000/api/agent/chat \
  -H "Authorization: Bearer ${PELLIER_TOKEN}" -H 'Content-Type: application/json' \
  -d "{\"message\":\"Find linen travel pieces for a warm-weather trip.\",\"session_id\":\"${SESSION}\"}"
#   CAPTURE session -> chunk -> done. The done receipt must show
#   runtime=agentcore-managed, jwtPassthrough=true, gatewayPassthrough=true.

# OPTIONAL: run only if the Code Editor role has logs:FilterLogEvents.
agentcore logs -n 20 --since 30m   # CAPTURE: does the platform-side record show the invoke?

# FAIL-CLOSED CHECK: the same managed route with NO Authorization header
curl -sN -X POST http://localhost:8000/api/agent/chat \
  -H 'Content-Type: application/json' \
  -d "{\"message\":\"Is the Hadley shirt at the Brooklyn warehouse?\",\"session_id\":\"anon-probe\"}"
#   MUST emit error code authentication_required and MUST NOT run in-process.
```

**Pass:** `agentcore status` shows a cloud ARN; the raw probe returns a
catalog/search answer with `rail=gateway-mcp`; the authenticated SSE route
shows Runtime/JWT/Gateway receipt fields; the anonymous request fails closed.

---

## 4. MCP on the wire — Act III §2a (Gate #4: the two scripts)

```bash
# Movement A — local stdio baseline (no token, always works)
python3 solutions/the-concierge/mcp_handshake.py
#   CAPTURE local tools/list + the chosen read-only call result -> reconcile Movement A "Expected"

# Movement B — custom tools through the managed Gateway ($PELLIER_TOKEN already set in step 3)
python3 solutions/the-concierge/gateway_tools_list.py
#   KEY UNKNOWN: did `initialize` succeed against AGENTCORE_GATEWAY_URL AS-IS?
#   If it FAILS, retry once with a trailing '/mcp' appended to the URL and note which form worked:
#     AGENTCORE_GATEWAY_URL="${AGENTCORE_GATEWAY_URL%/}/mcp" python3 solutions/the-concierge/gateway_tools_list.py
#   CAPTURE the real Gateway tool names (pellier-*-target__*) + read-call result;
#   confirm the by-pattern tool picker matched one -> reconcile Movement B "Expected".

# DEGRADATION: unset the token -> must exit 0 with "source ~/pellier-token.sh" guidance (Card 7 fallback)
( unset PELLIER_TOKEN; python3 solutions/the-concierge/gateway_tools_list.py )
```

**Pass:** both scripts complete the handshake and return data; the Gateway URL
form (`/mcp` or not) is recorded; the tool-pick patterns matched the real names.
If the picker missed (Gateway tools are prefixed `pellier-discovery-search-target__…`),
note the actual names so the substring patterns can be tightened.

---

## 5. End-to-end governed participant path (required)

```bash
bash scripts/dry-run-builders.sh     # non-destructive: wires floor_check, fires Marco T4, checks tool_audit, restores stub
```

**Pass:** PASS exit; Marco T4 names Brooklyn/BK-01; current-session Policy
ALLOW and DENY receipts are present; the ALLOW has an execution audit id and
the DENY proves no Lambda audit row was written.

---

## After the probe: reconcile + publish

1. Replace every content `> probe note:` with the real captured command/output (ARNs sanitized).
2. If the Cedar action format differed from the triple-underscore guess, the
   self-correct already handled provisioning — just record the winning token in
   `scripts/deploy/deploy_policy.py`'s comment for the next maintainer.
3. If the Gateway needed `/mcp`, note it in `gateway_tools_list.py` and the §2a probe note.

## Still open (not gated by this probe)
- **Landing `architecture.png` / `.svg`** — still shows Cedar inside the Runtime
  boundary + "working and semantic" memory. Alt text is fixed; the rendered image
  needs regeneration (image work, owned separately). Highest-leverage remaining artifact.
- **`act2-arc.svg/.png`** — new card-02 caption supplied out-of-band; confirm the
  swap lands at 1188×446.
