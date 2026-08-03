# Pellier - Claude Code project guidance

This repository is the application behind the flagship two-hour governed
agentic search workshop. Read this file before editing.

## Instruction map

Claude Code guidance is intentionally layered:

1. `~/.claude/CLAUDE.md` contains account-wide defaults.
2. This file defines the repository contract and operating modes.
3. The nearest nested `CLAUDE.md` adds module-specific rules:
   - `pellier/backend/CLAUDE.md`
   - `pellier/frontend/CLAUDE.md`
   - `skills/CLAUDE.md`
4. `.claude/skills/<name>/SKILL.md` contains on-demand Claude Code workflows.
5. `skills/<name>/SKILL.md` contains Pellier runtime skills loaded into
   Strands specialists per shopper turn. These are application data, not
   Claude Code instructions.

Read `VOICE.md` before changing shopper-facing copy, editorial model prompts,
or runtime skills.

## Branch and source contract

- `governed` is the flagship two-hour re:Invent workshop application.
- `main` supports the shorter one-hour builders session. Do not backport,
  merge, or simplify `governed` changes into `main` unless explicitly asked.
- The application repository is the source of truth for code and runtime
  claims.
- The sibling Workshop Studio repository
  `build-governed-agentic-ai-search-with-aurora-rds-bedrock-agentcore` is the
  source of truth for the flagship lab guide, launch wiring, and screenshots.
- Keep code and workshop claims aligned, but do not edit generated workshop
  artifacts or push the Workshop Studio repository unless explicitly asked.

## Choose the operating mode

### Participant mode

Use participant mode when the request names Lab 1, Stock Keeper,
`floor_check`, the workshop markers, or asks Claude Code to complete the
guided build.

In participant mode:

- Edit only the named marker region in
  `pellier/backend/agents/stock_keeper.py` or
  `pellier/backend/services/agent_tools.py`.
- Read the backend `CLAUDE.md` for the exact exercise contract.
- Never inspect or copy from `solutions/`.
- Do not edit tests, config, other tools, or other files.
- Do not run git commands, install packages, or restart services.
- Stop after one failed attempt and direct the participant to the lab guide's
  fallback lane.

These limits protect the learning objective. Do not relax them because a
broader edit would be faster.

### Maintainer mode

Use maintainer mode only when the request explicitly asks for a review,
bugfix, feature, documentation update, test work, release work, or workshop
hardening.

In maintainer mode:

- Inspect the relevant code and tests before editing.
- Preserve the five-lab participant path and terminal-first proof contract.
- Work with existing changes; do not reset or overwrite unrelated work.
- Keep solution copies byte-identical when bootstrap auto-applies them.
- Update Workshop Studio content when a participant-facing claim changes.
- Run the validation gates listed below before committing.

## Flagship workshop contract

**Title:** Build governed agentic AI search with Aurora, RDS, & Bedrock
AgentCore

The application must continue to demonstrate:

- A Strands SDK dispatcher routing shoppers to specialist agents.
- Aurora PostgreSQL hybrid retrieval using full-text search and pgvector.
- Cohere Rerank relevance ranking.
- Aurora-backed inventory, orders, customer records, returns, and a queryable
  JSONB audit ledger.
- AgentCore Runtime, Memory, Gateway, and Policy.
- Cedar authorization on sensitive tool actions.
- Inspectable ALLOW execution and DENY non-execution evidence.

The required participant path is:

1. Lab 1 - Build a Specialist Agent
2. Lab 2 - Measure Hybrid Search
3. Lab 3 - Prove AgentCore Memory
4. Lab 4 - Audit Agent Actions
5. Lab 5 - Enforce Cedar Policy

Do not reintroduce the old Act I/II/III taxonomy into flagship navigation or
documentation.

## Architecture invariants

- Aurora is the source of truth for catalog, inventory, customer, order,
  return, and audit data.
- Tool results and SQL rows are evidence. UI state alone is not proof.
- A Cedar DENY receipt and the absence of a matching `tool_audit` execution
  row are distinct, intentional evidence.
- Cognito identity travels in the signed token. Do not invent ambient identity
  or correlation fields across managed boundaries.
- Boutique is shopper-facing, Atelier is an assisted inspection surface, and
  Code Editor plus SQL/curl remain canonical workshop proof.
- Editorial specialists use the configured Opus profile when available;
  reporting and routing specialists use the configured Sonnet profile.
- Never hardcode credentials, JWTs, account IDs, endpoints, or `.env` values
  into tracked files.

## Validation gates

Run checks from the repository root unless a command changes directory.

```bash
# Backend
cd pellier/backend
python -m pytest -q

# Frontend
cd pellier/frontend
npm test -- --run
npm run type-check
npm run lint
npm run build
npm audit --omit=dev --audit-level=high

# Repository
git diff --check
find scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

Use focused tests during iteration. Run the full backend and frontend gates
before a flagship workshop release or a broad product-pass commit.
