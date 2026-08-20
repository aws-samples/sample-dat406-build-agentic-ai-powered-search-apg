#!/usr/bin/env python3
"""Score governance invariants from evidence alone.

Demonstrated only. No evaluation dependency enters required lab completion, and
nothing here calls a model or a managed evaluation service.

The close of the workshop is a claim worth making concrete: once evidence is
structured and correlated on `turn_id`, the same artifacts a human reads during
reconstruction can be read by a machine. The forensic exercise asks a
participant to reason about three turns; this scores the same three turns
against the invariants the design states, using the same tables.

The invariants, and why each is checkable rather than a matter of opinion:

    identity recorded          a turn with no principal record cannot be
                               attributed to anyone
    denial means non-execution a DENY with an execution row would mean the tool
                               ran after being refused
    monitor means execution    a WOULD_DENY with no execution row would mean
                               Cedar blocked it after all, so the mode never
                               took effect
    refusal changes nothing    any refused turn must leave business state
                               untouched
    correlation holds          every artifact must join back to the turn

A failing invariant is a finding about the *system*, not about the participant.

The managed graduation path is `services/agentcore_evals.py`, which submits
CloudWatch-log-driven batch evaluations to AgentCore Evaluations. It stays
optional and env-gated; this script exists so the demonstration works with no
provisioning at all.

Usage::

    python3 scripts/score_governance_evidence.py
    python3 scripts/score_governance_evidence.py --turn turn-forensic-allowed
    python3 scripts/score_governance_evidence.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Dict, List, Optional

_BACKEND = pathlib.Path(__file__).resolve().parents[1] / "pellier" / "backend"

# Decisions that mean the request was refused before it could change anything.
_BLOCKING_DECISIONS = {"DENY"}
# Decisions that mean the request continued despite an adverse policy opinion.
_MONITOR_DECISIONS = {"WOULD_DENY"}


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


_EVIDENCE_SQL = """
SELECT json_agg(row_to_json(t)) FROM (
  SELECT gtr.turn_id,
         gtr.principal_sub,
         gtr.principal_verified,
         gtr.rail,
         gtr.terminal_status,
         gtr.policy_events->0->>'decision' AS decision,
         gtr.policy_events->0->>'source'   AS decision_source,
         (SELECT count(*) FROM pellier.tool_audit ta
           WHERE ta.args->>'turn_id' = gtr.turn_id)          AS executions,
         (SELECT count(*) FROM pellier.governed_receipts gr
             JOIN pellier.tool_audit ta2 ON ta2.audit_id = gr.audit_id
           WHERE ta2.args->>'turn_id' = gtr.turn_id)         AS policy_receipts,
         (SELECT count(*) FROM pellier.tool_audit ta3
           WHERE ta3.args->>'turn_id' = gtr.turn_id
             AND ta3.result->>'status' = 'success')          AS successful_executions
    FROM pellier.governed_turn_receipts gtr
   {where}
   ORDER BY gtr.created_at
) t
"""


def read_turns(cfg: Dict[str, str], turn_id: Optional[str]) -> List[Dict[str, Any]]:
    """Read the correlated evidence for one turn, or all of them."""
    where = f"WHERE gtr.turn_id = '{turn_id}'" if turn_id else ""
    child = os.environ.copy()
    child["PGPASSWORD"] = cfg["DB_PASSWORD"]
    result = subprocess.run(
        [
            "psql", "-h", cfg["DB_HOST"], "-p", cfg.get("DB_PORT", "5432"),
            "-U", cfg["DB_USER"], "-d", cfg["DB_NAME"],
            "-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1",
            "-c", _EVIDENCE_SQL.format(where=where),
        ],
        env=child, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:300])
    payload = (result.stdout or "").strip()
    return json.loads(payload) if payload and payload != "" else []


def score_turn(turn: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return one finding per invariant, each pass or fail with a reason."""
    findings: List[Dict[str, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        findings.append(
            {"invariant": name, "result": "pass" if ok else "FAIL", "detail": detail}
        )

    decision = turn.get("decision")
    executions = int(turn.get("executions") or 0)
    successes = int(turn.get("successful_executions") or 0)

    record(
        "identity recorded",
        bool(turn.get("principal_sub")) or turn.get("principal_verified") is False,
        f"principal_sub={turn.get('principal_sub') or 'absent'}, "
        f"verified={turn.get('principal_verified')}",
    )

    record(
        "policy decision recorded",
        bool(decision),
        f"decision={decision or 'none'} (source={turn.get('decision_source') or 'none'})",
    )

    if decision in _BLOCKING_DECISIONS:
        record(
            "denial means non-execution",
            executions == 0,
            f"{executions} execution row(s) for a {decision}; the absence of a "
            "row is the proof the tool never ran",
        )
        record(
            "denial changed nothing",
            successes == 0,
            f"{successes} successful execution(s) on a denied turn",
        )
    elif decision in _MONITOR_DECISIONS:
        record(
            "monitor mode still executed",
            executions > 0,
            f"{executions} execution row(s); zero would mean the request was "
            "blocked after all, so monitor mode never took effect",
        )
        record(
            "monitor mode changed nothing",
            successes == 0,
            f"{successes} successful execution(s); a would-deny that succeeded "
            "means nothing refused it",
        )
    else:
        record(
            "allowed turn executed",
            executions > 0,
            f"{executions} execution row(s) for decision={decision}",
        )

    # A per-tool Cedar receipt can only exist where a tool ran, because the
    # receipt joins through audit_id. Its absence on a denied turn is correct.
    receipts = int(turn.get("policy_receipts") or 0)
    record(
        "correlation holds",
        receipts <= executions,
        f"{receipts} policy receipt(s) against {executions} execution row(s); a "
        "receipt without an execution row cannot be joined to anything",
    )

    record(
        "terminal status stated",
        bool(turn.get("terminal_status")),
        f"terminal_status={turn.get('terminal_status') or 'absent'}",
    )
    return findings


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--turn", help="Score one turn_id instead of all.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    cfg = _load_env()
    missing = [k for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not cfg.get(k)]
    if missing:
        print(f"Database not configured (missing {', '.join(missing)}).", file=sys.stderr)
        return 2

    try:
        turns = read_turns(cfg, args.turn)
    except RuntimeError as exc:
        print(f"could not read evidence: {exc}", file=sys.stderr)
        return 1

    if not turns:
        print("No turn receipts to score. Seed the forensic dataset first:")
        print("  python3 scripts/seed_forensic_dataset.py")
        return 2

    scored = [{"turn": turn, "findings": score_turn(turn)} for turn in turns]
    failures = [
        (entry["turn"]["turn_id"], finding)
        for entry in scored
        for finding in entry["findings"]
        if finding["result"] == "FAIL"
    ]

    if args.json:
        print(json.dumps({"turns": scored, "failures": len(failures)}, indent=2))
        return 1 if failures else 0

    print("Governance invariants, scored from evidence")
    print("=" * 84)
    for entry in scored:
        turn = entry["turn"]
        print(f"\n  {turn['turn_id']}  [{turn.get('decision') or 'no decision'}"
              f" / {turn.get('terminal_status')}]")
        for finding in entry["findings"]:
            mark = "✓" if finding["result"] == "pass" else "✗"
            print(f"    {mark} {finding['invariant']:<30} {finding['detail'][:70]}")

    print()
    print("  The same rows a participant reads by hand were scored here without a")
    print("  model, a managed evaluation service, or any knowledge of what was")
    print("  supposed to happen. That is the point: structured, correlated evidence")
    print("  supports human reconstruction and automated evaluation equally.")
    print()
    if failures:
        print(f"{len(failures)} invariant(s) failed:", file=sys.stderr)
        for turn_id, finding in failures:
            print(f"  {turn_id}: {finding['invariant']} — {finding['detail']}", file=sys.stderr)
        return 1
    print("✅ every invariant holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
