# Pellier backend guidance

This directory owns FastAPI, Strands specialists, tools, retrieval, memory,
AgentCore adapters, policy integration, SSE streaming, and backend tests.

Read the repository `CLAUDE.md` first and choose participant or maintainer
mode before editing.

## Participant mode: Lab 1 only

The participant may name one of two build sites. Work only inside the named
marker region.

### Stock Keeper definition

File:

```text
agents/stock_keeper.py
```

Markers:

```text
# === WORKSHOP · Stock Keeper · definition: START ===
# === WORKSHOP · Stock Keeper · definition: END ===
```

Fill only the marked definition fields:

1. Set the stub flag so the dispatcher uses the real specialist.
2. Use the Stock Keeper instructions already defined in the module.
3. Use the reporting model setting.
4. Use the reporting/Sonnet max-token setting.
5. Bind the Stock Keeper tools already imported in the module.

Do not add temperature. The active Sonnet profile rejects that deprecated
argument.

### `floor_check` body

File:

```text
services/agent_tools.py
```

Markers:

```text
# === WORKSHOP · Stock Keeper · floor_check: START ===
# === WORKSHOP · Stock Keeper · floor_check: END ===
```

Derive the implementation from `whats_trending` or `price_intelligence` in
the same file:

1. Return a JSON error envelope when `_db_service` is unavailable.
2. Lazily import `BusinessLogic`.
3. Construct it with `_db_service`.
4. Normalize `product_query` with `.strip()` and pass `None` when empty.
5. Call `BusinessLogic.floor_check(...)` through `_run_async(...)`.
6. Return `json.dumps(result, indent=2)`.
7. Catch `Exception` and return a JSON error envelope.

Do not change the decorator, signature, docstring, comments, imports, tests,
or any code outside the markers. Never inspect `solutions/`.

The participant verifies through `/api/atelier/build-state`, Atelier's Tool
Registry, and Marco's Brooklyn warehouse turn. Do not run tests or git for
them.

## Maintainer architecture

- `app.py` owns FastAPI startup, route registration, smoke mode, and SPA
  serving.
- `services/chat.py` owns the streamed turn contract. Preserve SSE ordering,
  terminal events, cumulative versus delta semantics, and error taxonomy.
- `agents/` owns specialist construction and tool grants.
- `services/agent_tools.py` owns deterministic business-tool boundaries.
- `skills/` loads root `skills/*/SKILL.md` files into specialist prompts.
- `routes/atelier_observatory.py` serves evidence read models. It must not
  fabricate readiness or call managed services merely to render a page.
- `agentcore_runtime.py`, `services/agentcore_*`, and `services/managed_policy.py`
  own managed-boundary behavior.

## Backend rules

- Read `../../VOICE.md` before editing model prompts or shopper-visible copy.
- Keep centralized shopper copy in `boutique_copy.py` when practical.
- Preserve JSON/SSE machine fields while improving human-readable messages.
- Distinguish Cedar policy denial, authentication failure, service
  unavailability, and request validation failures.
- Do not call a bare 401 a Cedar DENY.
- Use parameterized SQL and explicit transactions for write paths.
- Keep ALLOW execution rows and DENY absence proof auditable.
- Do not add model parameters unsupported by the configured Bedrock profile.
- If an auto-applied backend file changes, update its solution twin and run
  `tests/test_solutions_parity.py`.

## Backend validation

From `pellier/backend`:

```bash
python -m pytest -q
python tests/test_copy_compliance.py
```

When local settings are unavailable, collection-safe test placeholders are:

```bash
DB_HOST=localhost \
DB_NAME=pellier_test \
DB_USER=pellier_test \
DB_PASSWORD=pellier_test \
python -m pytest -q
```

Never point a test at workshop Aurora unless the test explicitly requires
live integration and the operator has approved it.
