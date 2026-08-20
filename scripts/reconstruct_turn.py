#!/usr/bin/env python3
"""Find one governed turn's exported spans by ``turn_id``.

The console-free half of the reconstruction exercise. Given the ``turn_id``
a shopper turn reported, this prints every span Pellier exported for it:
which boundary ran, on whose behalf, what the policy decided, and what the
tool execution reported.

Usage::

    python3 scripts/reconstruct_turn.py turn-3ad398c596164e7eb293417f2b24524e
    python3 scripts/reconstruct_turn.py --minutes 120 turn-3ad3...
    python3 scripts/reconstruct_turn.py --boundaries      # what got exported at all
    python3 scripts/reconstruct_turn.py --aurora turn-3ad3...  # answer key

Two halves, deliberately separate
---------------------------------

By default this reads only spans. Spans locate and correlate a turn; Aurora
proves what actually reached the authoritative system. An operator who can
only see spans has not yet proven anything changed, and keeping the default
span-only is what makes that distinction land.

``--aurora`` performs the correlated join and prints both sides. That is the
**answer key**: the exercise is to run the joins by hand from the SQL this tool
prints, then check the result against it.

Requires ``boto3`` and Transaction Search enabled: spans are not queryable
until they are indexed into the ``aws/spans`` log group.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time
from typing import Any, Dict, List, Optional

LOG_GROUP = "aws/spans"

# Mirrors ``config.Settings.AWS_REGION``. Spans are queryable only in the
# region the app exported them to, and an ambient profile often names a
# different one — silently querying the wrong region returns zero rows and
# looks exactly like "export is broken".
DEFAULT_REGION = "us-east-1"

# Where the Aurora half reads its connection settings from.
_BACKEND_ENV = pathlib.Path(__file__).resolve().parents[1] / "pellier" / "backend" / ".env"

# Attribute reference. `aws/spans` stores span attributes as a flat map whose
# keys contain literal dots, and Insights resolves the dotted path as written:
#
#   attributes.pellier.turn_id      works
#   `attributes.pellier.turn_id`    works (backticks also accepted)
#   attributes.pellier\.turn_id     REJECTED — MalformedQueryException,
#                                   "token recognition error at: '\'"
#
# The escaped form is the intuitive guess and it does not parse. Verified
# against a live aws/spans group on 2026-08-18; do not "fix" this back.
_ATTR = "attributes.pellier.{}"

# Bounded polling. An unbounded wait turns "not indexed yet" or a missing
# permission into a hang, which reads as a broken tool rather than as absent
# evidence.
_POLL_INTERVAL_SECONDS = 2
_POLL_ATTEMPTS = 24

_TURN_QUERY = """
fields @timestamp, name,
       {turn}      as turn,
       {sub}       as principal,
       {auth}      as authenticated,
       {simulated} as persona_simulated,
       {caller}    as caller,
       {tool}      as tool,
       {outcome}   as outcome,
       {mode}      as policy_mode,
       {verdict}   as policy_verdict,
       traceId, durationNano
| filter {turn} = '{turn_id}'
| sort @timestamp asc
| limit 100
"""

_BOUNDARY_QUERY = """
fields name, scope.name as scope
| stats count(*) as spans by name, scope
| sort spans desc
| limit 40
"""


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruct one governed turn from its exported spans.",
    )
    parser.add_argument(
        "turn_id",
        nargs="?",
        help="turn_id the shopper turn reported (e.g. turn-3ad3...).",
    )
    parser.add_argument(
        "--boundaries",
        action="store_true",
        help="List every exported span name instead of one turn.",
    )
    parser.add_argument(
        "--aurora",
        action="store_true",
        help="Also print the correlated Aurora artifacts (the answer key).",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=60,
        help="How far back to search (default: 60).",
    )
    parser.add_argument(
        "--log-group",
        default=LOG_GROUP,
        help=f"Log group Transaction Search indexes into (default: {LOG_GROUP}).",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or DEFAULT_REGION,
        help=f"Region the app exported spans to (default: {DEFAULT_REGION}).",
    )
    args = parser.parse_args(argv)
    if not args.boundaries and not args.turn_id:
        parser.error("pass a turn_id, or --boundaries to list exported spans")
    return args


def run_query(client: Any, log_group: str, query: str, minutes: int) -> List[Dict[str, str]]:
    """Run one Insights query and return its rows.

    Raises:
        TimeoutError: The query did not reach a terminal state in the bounded
            polling window.
        RuntimeError: The query reached a non-Complete terminal state.
    """
    end = int(time.time())
    start = end - minutes * 60
    query_id = client.start_query(
        logGroupNames=[log_group],
        startTime=start,
        endTime=end,
        queryString=query,
    )["queryId"]

    for _ in range(_POLL_ATTEMPTS):
        time.sleep(_POLL_INTERVAL_SECONDS)
        response = client.get_query_results(queryId=query_id)
        status = response["status"]
        if status == "Complete":
            return [
                {f["field"]: f["value"] for f in row if f["field"] != "@ptr"}
                for row in response.get("results", [])
            ]
        if status in {"Failed", "Cancelled", "Timeout"}:
            raise RuntimeError(f"query {status.lower()}")
    raise TimeoutError("query did not complete in the polling window")


def _millis(nanos: Optional[str]) -> str:
    try:
        return f"{int(nanos) / 1_000_000:.0f}ms"
    except (TypeError, ValueError):
        return "-"


def _detail(row: Dict[str, str]) -> str:
    """Summarize one span's evidence fields, omitting what it did not carry."""
    parts = []
    if row.get("tool"):
        parts.append(f"tool={row['tool']}")
    if row.get("outcome"):
        parts.append(f"outcome={row['outcome']}")
    if row.get("policy_verdict"):
        # Mode is Gateway engine configuration, not turn data, so it is
        # usually absent. Printing a placeholder for it would imply the turn
        # failed to report something it never carries.
        mode = row.get("policy_mode")
        parts.append(
            f"{mode}/{row['policy_verdict']}" if mode else row["policy_verdict"]
        )
    if row.get("caller"):
        parts.append(f"caller={row['caller']}")
    return ", ".join(parts)


def print_boundaries(rows: List[Dict[str, str]]) -> None:
    print(f"{'spans':>6}  {'name':<36} scope")
    print("-" * 88)
    for row in rows:
        print(f"{row.get('spans', '?'):>6}  {row.get('name', '?'):<36} {row.get('scope', '')}")


def _identity_line(rows: List[Dict[str, str]]) -> str:
    """Describe the turn's acting identity from whichever span carries it.

    Identity is a property of the turn, not of each boundary: the routing
    span is the identity boundary, and `turn_id` carries the correlation to
    the rest. Reporting it once, at the top, avoids printing a blank
    identity column on spans that legitimately do not restate it.

    Booleans arrive from Insights as "1"/"0".
    """
    for row in rows:
        if row.get("principal"):
            return f"{row['principal']} (verified principal)"
    for row in rows:
        if row.get("authenticated") is None and row.get("persona_simulated") is None:
            continue
        if row.get("persona_simulated") == "1":
            return (
                "anonymous, persona simulated — this turn's scope came from a "
                "UI selection, not a token, and is not valid for authorization"
            )
        return "anonymous — no verified principal and no persona"
    return "not reported on any span for this turn"


def print_turn(rows: List[Dict[str, str]], turn_id: str) -> None:
    traces = {row["traceId"] for row in rows if row.get("traceId")}

    print(f"identity  : {_identity_line(rows)}")
    print(f"spans     : {len(rows)} across {len(traces)} trace(s)")
    if len(traces) > 1:
        # Worth stating plainly: the framework roots its own trace per agent
        # invocation, so one turn legitimately spans several traces. That is
        # exactly why turn_id is the correlation key and trace_id is not.
        print("            (one turn spans several traces; turn_id is what joins them)")
    print()

    print(f"{'boundary':<30} {'detail':<44} {'took':>8}")
    print("-" * 86)
    for row in rows:
        print(
            f"{row.get('name', '?'):<30} "
            f"{_detail(row):<44} "
            f"{_millis(row.get('durationNano')):>8}"
        )

    print()
    print("Spans locate the turn. For what actually reached Aurora, read the")
    print("execution rows this turn wrote:")
    print()
    print("  SELECT tool, caller, latency_ms, result")
    print("    FROM pellier.tool_audit")
    print(f"   WHERE args::text LIKE '%{turn_id}%';")
    print()
    print("An ALLOW span with no matching row is not a contradiction — it")
    print("means authorization succeeded and execution did not.")


def _no_rows_help() -> None:
    print("No spans matched.")
    print()
    print("Check, in order:")
    print("  1. Transaction Search is enabled and indexing. Spans are not")
    print("     queryable until indexed; bootstrap STEP 13b configures this.")
    print("  2. The turn ran inside the search window (widen --minutes).")
    print("  3. The backend logged the signing exporter as attached at")
    print("     startup. Without it, spans never leave the process.")
    print("  4. The region above matches the one the backend exports to.")


# ---------------------------------------------------------------------------
# The Aurora half
# ---------------------------------------------------------------------------
#
# Spans say a turn happened. Aurora says what it did. The join is on `turn_id`,
# with one hop that surprises everyone the first time:
#
#   governed_turn_receipts.turn_id        <- the turn summary, direct
#   tool_audit                            <- args->>'turn_id', NOT a column
#   governed_receipts                     <- NO turn_id at all; joins through
#                                            tool_audit.audit_id
#   governed_query_receipts.turn_id       <- generated-SQL attempts, direct
#
# A participant looking for `governed_receipts.turn_id` will not find one. The
# Cedar decision is attached to a *tool call*, not to a turn, which is the
# correct shape — one turn can make several tool calls with different verdicts.

_AURORA_QUERIES = {
    "turn receipt": """
        SELECT principal_sub, principal_verified, rail, terminal_status,
               terminal_outcome, latency_ms, policy_events, tool_audit_ids,
               created_at
          FROM pellier.governed_turn_receipts
         WHERE turn_id = %s
    """,
    "tool executions": """
        SELECT audit_id, tool, caller, latency_ms,
               result IS NOT NULL AS completed, created_at
          FROM pellier.tool_audit
         WHERE args->>'turn_id' = %s
         ORDER BY audit_id
    """,
    "policy decisions": """
        SELECT gr.receipt_id, gr.audit_id, gr.tool, gr.caller, gr.decision,
               gr.policy_name, gr.principal_label
          FROM pellier.governed_receipts gr
          JOIN pellier.tool_audit ta ON ta.audit_id = gr.audit_id
         WHERE ta.args->>'turn_id' = %s
         ORDER BY gr.receipt_id
    """,
    "generated queries": """
        SELECT receipt_id, accepted, validation, role_used, row_count,
               execution_outcome, rejection_reason
          FROM pellier.governed_query_receipts
         WHERE turn_id = %s
         ORDER BY receipt_id
    """,
}


def _db_config(env_path: pathlib.Path) -> Optional[Dict[str, str]]:
    """Parse the backend .env without shell interpolation."""
    if not env_path.exists():
        return None
    cfg: Dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip().strip('"').strip("'")
    if not all(cfg.get(k) for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")):
        return None
    return cfg


def read_aurora_evidence(turn_id: str, env_path: pathlib.Path) -> Dict[str, Any]:
    """Return every Aurora artifact correlated to one turn.

    Read as the owner on purpose: this is the operator's forensic view, not the
    agent's. An operator reconstructing an incident must be able to see rows the
    agent could not, including another customer's, which is exactly the
    distinction Row-Level Security draws for the runtime roles.
    """
    cfg = _db_config(env_path)
    if cfg is None:
        return {"available": False, "reason": "backend .env has no database settings"}

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return {"available": False, "reason": "psycopg not installed"}

    from urllib.parse import quote_plus

    dsn = (
        f"postgresql://{cfg['DB_USER']}:{quote_plus(cfg['DB_PASSWORD'])}"
        f"@{cfg['DB_HOST']}:{cfg.get('DB_PORT', '5432')}/{cfg['DB_NAME']}"
    )
    evidence: Dict[str, Any] = {"available": True}
    try:
        with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=15) as conn:
            for label, sql in _AURORA_QUERIES.items():
                with conn.cursor() as cur:
                    cur.execute(sql, (turn_id,))
                    evidence[label] = cur.fetchall()
    except Exception as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {str(exc)[:160]}"}
    return evidence


def _has_aurora_artifacts(evidence: Dict[str, Any]) -> bool:
    """Return True when at least one correlated row was read.

    Distinguishes "the turn is reconstructable from Aurora alone" from "the
    turn_id matched nothing anywhere", so a caller with no spans still exits
    non-zero on a turn_id that simply does not exist.
    """
    if not evidence.get("available"):
        return False
    return any(
        isinstance(rows, list) and rows
        for label, rows in evidence.items()
        if label not in {"available", "reason"}
    )


def print_aurora_evidence(evidence: Dict[str, Any], turn_id: str) -> None:
    """Print the Aurora side, labelling every claim with its source."""
    print()
    print("Aurora evidence")
    print("=" * 100)
    if not evidence.get("available"):
        print(f"  unavailable: {evidence.get('reason')}")
        return

    receipts = evidence.get("turn receipt") or []
    if receipts:
        row = receipts[0]
        principal = row.get("principal_sub") or "(anonymous)"
        verified = "verified" if row.get("principal_verified") else "not verified"
        print(f"  identity   : {principal} ({verified})            [governed_turn_receipts]")
        print(f"  rail       : {row.get('rail')}                    [governed_turn_receipts]")
        print(f"  outcome    : {row.get('terminal_status')}         [governed_turn_receipts]")
        for event in row.get("policy_events") or []:
            decision = event.get("decision")
            source = event.get("source")
            print(f"  policy     : {decision} (source={source})     [governed_turn_receipts.policy_events]")
    else:
        print("  no turn receipt for this turn_id             [governed_turn_receipts]")

    decisions = evidence.get("policy decisions") or []
    if decisions:
        for row in decisions:
            print(
                f"  cedar      : {row['decision']} on {row['tool']} "
                f"by {row.get('principal_label') or '(none)'} "
                f"policy={row.get('policy_name')}   [governed_receipts via audit_id]"
            )
    else:
        print("  no per-tool Cedar receipt                    [governed_receipts]")

    executions = evidence.get("tool executions") or []
    if executions:
        for row in executions:
            state = "completed" if row["completed"] else "started, no result"
            print(
                f"  executed   : {row['tool']} ({row['caller']}) "
                f"{row['latency_ms']}ms, {state}          [tool_audit]"
            )
    else:
        print("  no tool executed on this turn                [tool_audit]")

    queries = evidence.get("generated queries") or []
    for row in queries:
        verdict = "accepted" if row["accepted"] else f"refused ({row['validation']})"
        print(
            f"  generated SQL: {verdict} as {row['role_used']}, "
            f"rows={row['row_count']}            [governed_query_receipts]"
        )

    print()
    print("  Reading the combination:")
    print("  - a Cedar ALLOW with no tool_audit row means authorization succeeded")
    print("    and execution did not; the two are separate facts.")
    print("  - a Cedar DENY should have NO tool_audit row: the tool never ran, so")
    print("    the absence IS the evidence.")
    print("  - a tool_audit row with no business-state change means the database")
    print("    refused what policy allowed.")


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    try:
        import boto3
    except ImportError:
        print("boto3 is required. Install it or run inside the backend venv.", file=sys.stderr)
        return 1

    client = boto3.client("logs", region_name=args.region)

    if args.boundaries:
        query = _BOUNDARY_QUERY
    else:
        query = _TURN_QUERY.format(
            turn=_ATTR.format("turn_id"),
            sub=_ATTR.format("principal_sub"),
            auth=_ATTR.format("authenticated"),
            simulated=_ATTR.format("persona_is_simulated"),
            caller=_ATTR.format("caller"),
            tool=_ATTR.format("tool"),
            outcome=_ATTR.format("execution_outcome"),
            mode=_ATTR.format("policy_mode"),
            verdict=_ATTR.format("policy_verdict"),
            turn_id=args.turn_id,
        )

    print(f"log group : {args.log_group}")
    print(f"region    : {args.region}")
    print(f"window    : last {args.minutes}m")
    if args.turn_id:
        print(f"turn_id   : {args.turn_id}")
    print()

    try:
        rows = run_query(client, args.log_group, query, args.minutes)
    except (TimeoutError, RuntimeError) as exc:
        print(f"query did not return results: {exc}", file=sys.stderr)
        return 1

    if not rows:
        _no_rows_help()
        if not args.aurora:
            return 2
        # A turn can exist in Aurora with no spans at all: the seeded forensic
        # dataset is written straight to the tables, and a turn from before
        # export was wired has artifacts but no trace. Refusing to print the
        # authoritative side because the locating side is missing would make
        # the answer key unusable on exactly those turns.
        print()
        print("No spans for this turn. The Aurora side follows; it is the")
        print("authoritative record, and it stands on its own.")
        aurora = read_aurora_evidence(args.turn_id or "", _BACKEND_ENV)
        print_aurora_evidence(aurora, args.turn_id or "")
        return 0 if _has_aurora_artifacts(aurora) else 2

    if args.boundaries:
        print_boundaries(rows)
        return 0

    print_turn(rows, args.turn_id or "")
    if args.aurora:
        print_aurora_evidence(
            read_aurora_evidence(args.turn_id or "", _BACKEND_ENV), args.turn_id or ""
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
