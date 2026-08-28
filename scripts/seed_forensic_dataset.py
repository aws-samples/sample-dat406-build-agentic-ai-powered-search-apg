#!/usr/bin/env python3
"""Seed three reconstructable turns for the forensic exercise.

The closing exercise does not generate every artifact from scratch — a live
Cedar ENFORCE denial and a LOG_ONLY dual-verdict cannot both be produced in one
sitting, because they need opposite enforcement modes. So the dataset is
seeded, and the business question stays constant while enforcement changes:

    "Theo disputes a return. What happened?"

    turn A  allowed             Cedar ALLOW, tool ran, business state changed
    turn B  ENFORCE denial      Cedar DENY, tool never ran, no execution row
    turn C  LOG_ONLY dual       Cedar WOULD_DENY, tool ran, database refused

ANSWER-KEY INVARIANT
--------------------

Every answer must be derivable from evidence alone — no instructor knowledge,
no hidden application logs, no source reading, no assumption about what
*should* have happened. That constrains the seed in a specific way: each turn
must carry enough artifacts that its story is readable, and no more. In
particular turn B deliberately writes **no** `tool_audit` row, because the
absence is the evidence that the tool never ran. Adding one "for completeness"
would destroy the exercise.

What each turn leaves, and where:

    governed_turn_receipts   identity, rail, terminal status, policy events
    tool_audit               execution rows (absent for the denied turn)
    governed_receipts        the Cedar decision, joined via audit_id
    returns / orders         business state

TWO SCHEMA CONSTRAINTS THAT SHAPE THE DATASET
---------------------------------------------

`terminal_status` is constrained to the schema's own vocabulary, and one value
is exactly right for turn B: `denied-before-execution`. That is stronger
evidence than a generic failure, because it states *when* the denial happened
relative to execution — the distinction the whole exercise turns on.

`governed_receipts.decision` is constrained to ALLOW or DENY, so a LOG_ONLY
**WOULD_DENY cannot be stored there at all**. That is not a bug to work
around: `governed_receipts` records what the managed rail *enforced*, and a
would-deny enforced nothing. The monitor verdict therefore lives in
`governed_turn_receipts.policy_events`, and turn C has no per-tool Cedar
receipt. A participant reconstructing turn C needs that fact, or the missing
row reads as lost evidence.

Usage::

    python3 scripts/seed_forensic_dataset.py            # seed
    python3 scripts/seed_forensic_dataset.py --show     # list seeded turns
    python3 scripts/seed_forensic_dataset.py --clear    # remove
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from typing import Dict, List, Optional

_BACKEND = pathlib.Path(__file__).resolve().parents[1] / "pellier" / "backend"

# Stable ids so the exercise, its answer key, and any lab content can name the
# same turns. Prefixed so `--clear` can find them without touching real turns.
PREFIX = "turn-forensic-"
TURN_ALLOWED = f"{PREFIX}allowed"
TURN_ENFORCE_DENIED = f"{PREFIX}enforce-denied"
TURN_LOG_ONLY = f"{PREFIX}logonly-dual"

_SESSION = "forensic-exercise"
_CUSTOMER = "CUST-THEO"
_PRODUCT = "31"
_PRINCIPAL = "forensic-sub-theo"


def _load_env() -> Dict[str, str]:
    values: Dict[str, str] = {}
    env_path = _BACKEND / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({k: v for k, v in os.environ.items() if k.startswith("DB_")})
    return values


def _psql(cfg: Dict[str, str], sql: str) -> subprocess.CompletedProcess:
    """Run SQL through psql, passing the password via the environment only."""
    child = os.environ.copy()
    child["PGPASSWORD"] = cfg["DB_PASSWORD"]
    return subprocess.run(
        [
            "psql", "-h", cfg["DB_HOST"], "-p", cfg.get("DB_PORT", "5432"),
            "-U", cfg["DB_USER"], "-d", cfg["DB_NAME"],
            "-X", "-q", "-v", "ON_ERROR_STOP=1", "-t", "-A", "-c", sql,
        ],
        env=child, capture_output=True, text=True,
    )


def _policy_events(decision: str, source: str, policy: Optional[str]) -> str:
    """Build the policy_events JSON a turn receipt carries.

    `source` must name where the decision can actually be read back from.
    Claiming `governed_receipts` for a turn that has no row there sends a
    participant looking for evidence that does not exist, which is the same
    failure as fabricating it.
    """
    event = {"decision": decision, "source": source}
    if policy:
        event["policy_name"] = policy
    return json.dumps([event])


def clear_sql() -> str:
    """Remove the removable seeded artifacts, in dependency order.

    `governed_turn_receipts` is append-only by trigger, so its rows survive.
    That is correct — evidence should not be quietly deletable — and it means a
    corrected seed needs `reset-governed-workshop.sh`, which truncates.
    """
    return f"""
BEGIN;
DELETE FROM pellier.governed_receipts
 WHERE audit_id IN (
   SELECT audit_id FROM pellier.tool_audit
    WHERE args->>'turn_id' LIKE '{PREFIX}%'
 );
DELETE FROM pellier.tool_audit WHERE args->>'turn_id' LIKE '{PREFIX}%';
-- NOT governed_turn_receipts: migration 014 installs an append-only trigger
-- that rejects DELETE, which is the schema protecting evidence immutability.
-- Only a TRUNCATE removes them, and that is reset's job. Re-seeding is
-- therefore ON CONFLICT DO NOTHING rather than delete-then-insert.
DELETE FROM pellier.returns WHERE reason = 'damaged' AND customer_id = '{_CUSTOMER}'
   AND order_id IN (SELECT id FROM pellier.orders WHERE customer_id = '{_CUSTOMER}');
DELETE FROM pellier.orders WHERE customer_id = '{_CUSTOMER}';
COMMIT;
"""


def seed_sql() -> str:
    """Build the whole dataset as one transaction.

    Written as explicit SQL rather than driven through the application so the
    three enforcement outcomes can coexist: producing them live would require
    flipping Cedar mode between turns and would leave the account in whichever
    mode the last turn used.
    """
    return f"""
BEGIN;

-- The disputed order. One order, so the business question is identical
-- across all three turns.
INSERT INTO pellier.orders (customer_id, product_id, quantity)
VALUES ('{_CUSTOMER}', '{_PRODUCT}', 2);

-- ---------------------------------------------------------------- turn A
-- Allowed: Cedar permitted it, the tool ran, and business state changed.
INSERT INTO pellier.governed_turn_receipts
    (turn_id, session_id, principal_sub, principal_verified, rail,
     policy_events, terminal_status, latency_ms)
VALUES ('{TURN_ALLOWED}', '{_SESSION}', '{_PRINCIPAL}', true, 'gateway-mcp',
        '{_policy_events("ALLOW", "governed_receipts", "initiate_return_allow_damaged")}'::jsonb,
        'complete', 1840)
ON CONFLICT (turn_id) DO NOTHING;

WITH executed AS (
    INSERT INTO pellier.tool_audit (session_id, tool, caller, args, result, latency_ms)
    VALUES ('{_SESSION}', 'initiate_return', 'agent',
            jsonb_build_object('turn_id', '{TURN_ALLOWED}',
                               'customer_id', '{_CUSTOMER}',
                               'product_id', '{_PRODUCT}',
                               'reason', 'damaged'),
            jsonb_build_object('status', 'success'), 1477)
    RETURNING audit_id
)
INSERT INTO pellier.governed_receipts
    (audit_id, session_id, principal_id, principal_label, tool, caller,
     decision, args, policy_name)
SELECT audit_id, '{_SESSION}', '{_PRINCIPAL}', 'theo', 'initiate_return',
       'gateway', 'ALLOW',
       jsonb_build_object('reason', 'damaged'),
       'initiate_return_allow_damaged'
  FROM executed;

-- The business change turn A caused.
INSERT INTO pellier.returns (customer_id, product_id, reason, status, quantity, order_id)
SELECT '{_CUSTOMER}', '{_PRODUCT}', 'damaged', 'approved', 1, id
  FROM pellier.orders WHERE customer_id = '{_CUSTOMER}' ORDER BY id DESC LIMIT 1;

-- ---------------------------------------------------------------- turn B
-- Cedar ENFORCE denial. The tool never ran, so there is deliberately NO
-- tool_audit row: its absence is the evidence. Because governed_receipts
-- joins through audit_id, a denial with no execution has no per-tool receipt
-- either — the decision lives on the turn receipt's policy_events.
INSERT INTO pellier.governed_turn_receipts
    (turn_id, session_id, principal_sub, principal_verified, rail,
     policy_events, terminal_status, terminal_outcome, latency_ms)
VALUES ('{TURN_ENFORCE_DENIED}', '{_SESSION}', '{_PRINCIPAL}', true, 'gateway-mcp',
        '{_policy_events("DENY", "managed_runtime_error", "initiate_return_damaged_only")}'::jsonb,
        'denied-before-execution', '{{"error_code": "policy_denied"}}'::jsonb, 240)
ON CONFLICT (turn_id) DO NOTHING;

-- ---------------------------------------------------------------- turn C
-- LOG_ONLY dual verdict. Cedar would have denied, the request continued, the
-- tool ran, and the database refused. Two verdicts, one turn: the tool_audit
-- row proves execution was attempted; the unchanged business state proves
-- nothing landed.
INSERT INTO pellier.governed_turn_receipts
    (turn_id, session_id, principal_sub, principal_verified, rail,
     policy_events, terminal_status, terminal_outcome, latency_ms)
VALUES ('{TURN_LOG_ONLY}', '{_SESSION}', '{_PRINCIPAL}', true, 'gateway-mcp',
        '{_policy_events("WOULD_DENY", "monitor_mode", "initiate_return_damaged_only")}'::jsonb,
        'complete', '{{"error_code": "database_row_level_security"}}'::jsonb, 1615)
ON CONFLICT (turn_id) DO NOTHING;

-- No governed_receipts row here, deliberately: its `decision` column is
-- constrained to ALLOW or DENY, and a would-deny enforced neither. The monitor
-- verdict is on the turn receipt's policy_events above; this execution row is
-- what proves the request continued anyway.
INSERT INTO pellier.tool_audit (session_id, tool, caller, args, result, latency_ms)
VALUES ('{_SESSION}', 'initiate_return', 'agent',
        jsonb_build_object('turn_id', '{TURN_LOG_ONLY}',
                           'customer_id', 'CUST-ANNA',
                           'product_id', '21',
                           'reason', 'changed_mind'),
        jsonb_build_object('status', 'policy_blocked',
                           'denied_by', 'database_row_level_security'), 512);

COMMIT;
"""


SHOW_SQL = f"""
SELECT gtr.turn_id
       || ' | policy=' || coalesce(gtr.policy_events->0->>'decision', 'none')
       || ' | executions=' || (
            SELECT count(*) FROM pellier.tool_audit ta
             WHERE ta.args->>'turn_id' = gtr.turn_id)
       || ' | terminal=' || gtr.terminal_status
  FROM pellier.governed_turn_receipts gtr
 WHERE gtr.turn_id LIKE '{PREFIX}%'
 ORDER BY gtr.turn_id
"""


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--clear", action="store_true", help="Remove the dataset.")
    parser.add_argument("--show", action="store_true", help="List seeded turns.")
    args = parser.parse_args(argv)

    cfg = _load_env()
    missing = [k for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not cfg.get(k)]
    if missing:
        print(f"Database not configured (missing {', '.join(missing)}).", file=sys.stderr)
        return 2

    if args.show:
        result = _psql(cfg, SHOW_SQL)
        if result.returncode != 0:
            print(result.stderr.strip(), file=sys.stderr)
            return 1
        rows = [line for line in result.stdout.splitlines() if line.strip()]
        print("\n".join(f"  {row}" for row in rows) or "  (no forensic turns seeded)")
        return 0

    # Always clear first: seeding twice would double the artifacts and make the
    # exercise ambiguous about how many times something happened.
    result = _psql(cfg, clear_sql())
    if result.returncode != 0:
        print(f"clear failed: {result.stderr.strip()[:300]}", file=sys.stderr)
        return 1
    if args.clear:
        print("✅ forensic dataset removed")
        return 0

    result = _psql(cfg, seed_sql())
    if result.returncode != 0:
        print(f"seed failed: {result.stderr.strip()[:400]}", file=sys.stderr)
        return 1

    print("✅ seeded three reconstructable turns:")
    print(f"     {TURN_ALLOWED:<34} Cedar ALLOW, tool ran, state changed")
    print(f"     {TURN_ENFORCE_DENIED:<34} Cedar DENY, no execution row at all")
    print(f"     {TURN_LOG_ONLY:<34} Cedar WOULD_DENY, tool ran, database refused")
    print()
    print("  Reconstruct one with:")
    print(f"     python3 scripts/reconstruct_turn.py --aurora {TURN_ALLOWED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
