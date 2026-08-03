# Deploy to AgentCore

Deploy Pellier's governed agent path using Amazon Bedrock AgentCore.

This directory deploys the four Lambda tool targets, Gateway, managed Policy,
and Runtime. `scripts/bootstrap-labs.sh` provisions AgentCore Memory before
this sequence and the governed health gate requires all four AgentCore
capabilities to be live.

## What Gets Deployed

1. **4 Lambda MCP Servers** — 15 canonical tools packaged as Lambda functions:
   - `pellier-search-server` — Hybrid search + inventory tools
   - `pellier-pricing-server` — Price analysis + deal finding
   - `pellier-recommend-server` — Curation, preferences, and audit reads
   - `pellier-experience-server` — Returns and stylist escalation

2. **AgentCore Gateway** — MCP Gateway that registers all four Lambda targets with:
   - Cognito JWT authentication
   - Runtime tool discovery over MCP streamable HTTP
   - Exact parity with the 15-tool in-process contract

   Docs: [Gateway overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)

3. **AgentCore Policy** — A managed Cedar engine attached to Gateway in
   `ENFORCE` mode:
   - Baseline permit for this Gateway's tool catalog
   - `process_return` allowed only for `reason == "damaged"`
   - Provisioning executes a real ALLOW and DENY before reporting ready

4. **AgentCore Runtime** — The orchestrator deployed as a managed HTTP runtime:
   - Requires a Cognito access token through `CUSTOM_JWT`
   - Discovers tools via Gateway
   - Fails closed if identity or Gateway is unavailable
   - Uses AgentCore Memory context supplied by the application request path

   Docs: [Runtime overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)

## Prerequisites

The Workshop Studio AMI ships with the `@aws/agentcore` Node CLI preinstalled. Verify before starting:

```bash
which agentcore && agentcore --version   # pinned workshop CLI: 0.18.0
node --version                           # >= 20.x
```

If the CLI is missing (or you're testing a fresh AMI build):

```bash
npm install -g @aws/agentcore@0.18.0
```

CLI repo: https://github.com/aws/agentcore-cli

## Quick Deploy (15 min workshop version)

```bash
source deploy_all.sh
```

The `source` form is required — later steps consume env vars (`SEARCH_LAMBDA_ARN`, `MCP_GATEWAY_URL`, etc.) exported by earlier steps. Running with `bash deploy_all.sh` would silently lose those exports.

## Deployment Sequence

`deploy_all.sh` is the executable source of truth. It runs these phases:

1. Deploy search, pricing, recommendation, and experience Lambdas.
2. Create or update Gateway and wait for all four targets to reach `READY`.
3. Attach the managed Cedar engine in `ENFORCE` mode.
4. Scaffold the stateful `@aws/agentcore@0.18.0` project with
   `create -> add agent --type byo -> deploy`.
5. Patch the generated Runtime config with the execution role, Gateway URL,
   model, Python runtime, request-header allowlist, and `CUSTOM_JWT` settings.
6. Invoke the Runtime over raw HTTPS with a Cognito bearer token and require
   `rail=gateway-mcp`.

For unattended bootstrap, use
`scripts/provision_agentcore_end_to_end.py`; it adds target/tool verification,
live Policy ALLOW/DENY proof, and a structured readiness receipt.

## Files

| File                              | Purpose                                        |
| --------------------------------- | ---------------------------------------------- |
| `pellier_search_server.py`         | Lambda MCP server for search + inventory       |
| `pellier_pricing_server.py`        | Lambda MCP server for pricing                  |
| `pellier_recommend_server.py`      | Lambda MCP server for curation + evidence      |
| `pellier_experience_server.py`     | Lambda MCP server for returns + escalation     |
| `deploy_lambda.py`                | Lambda deployment script (adapted from DAT403) |
| `deploy_gateway.py`               | AgentCore Gateway deployment                   |
| `deploy_policy.py`                | Managed Cedar engine and Gateway attachment    |
| `gateway_process_return.py`       | Live ALLOW/DENY and JWT-bound receipt proof    |
| `../../pellier/backend/agentcore_runtime.py` | **Deployed** BYO Runtime entrypoint; JWT + Gateway required |
| `../../pellier/backend/pyproject.toml` | CodeZip deps for the BYO agent (0.18 uses uv, not requirements.txt) |
| `deploy_all.sh`                   | End-to-end deployment script                   |
| `test_runtime.py`                 | Raw CUSTOM_JWT Runtime smoke probe              |
| `check_traces.py`                 | Recent Runtime CloudWatch event inspection      |
| `requirements.txt`                | Pinned deployment-helper dependencies          |

## Where to look when something breaks

- **`agentcore deploy` fails with `AccessDenied` on `iam:PassRole`** — the calling principal needs permission to pass the AgentCore execution role. Workshop Studio CFN grants this; outside Workshop Studio, attach a policy that allows `iam:PassRole` on the role ARN in `agentcore.json`.
- **Gateway returns `401`** — Cognito access token expired (1-hour default). Re-run the `cognito-idp initiate-auth` block from `deploy_all.sh` step 7.
- **Runtime returns `managed_gateway_unavailable`** — `AGENTCORE_GATEWAY_URL` was absent or Gateway discovery failed. Repair the generated Runtime env, redeploy, and rerun `test_runtime.py`; do not enable a local fallback.
- **`agentcore deploy` fails on a missing CDKToolkit / `cdk-hnb659fds` stack** — the account isn't CDK-bootstrapped. Run `npx -y aws-cdk@2 bootstrap aws://<account>/<region>` (bootstrap-environment.sh does this automatically on fresh accounts).
- **CloudWatch logs** — runtime invocations land in `/aws/bedrock-agentcore/runtimes/<runtime-id>`. Search by `session.id` to follow a single multi-step turn.

Run `bash scripts/health-gate.sh` for the governed readiness verdict. It also
requires active Memory, exactly 120 warehouse rows, Policy `ENFORCE`, and the
structured provisioning receipt.
