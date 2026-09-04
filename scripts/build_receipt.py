#!/usr/bin/env python3
"""Assemble one portable build receipt for a participant's workshop run.

What this is
------------

Four labs each end in durable evidence, but that evidence is spread across
seven Aurora tables, a source-state check, and a managed-runtime receipt. A
participant who finishes the workshop has proved a great deal and has nothing
to take home that says so. This assembles exactly one artifact from evidence
that already exists -- it creates no tables, writes no rows, and invents no
state.

It is also the fastest table-lead diagnostic in the room: one command that says
which boundary a stuck participant has not crossed yet, and names the row that
would prove it.

The honesty rule
----------------

Every line reports one of three states, never two:

    PROVED       a durable row exists and satisfies the claim
    NOT YET      the lab has not left its evidence
    UNCHECKED    the query could not run (no database, no credentials)

UNCHECKED is not a soft NOT YET. "This did not happen" and "I could not look"
are different findings, and a receipt that blurs them is worse than no receipt,
because it invites a participant to conclude they failed at something the tool
simply never examined. The same rule governs the DENY case: the absence of an
execution row is only evidence when the row was actually searched for.

The run
-------

Migration 049 stamps every evidence row with the ``run_id`` bound on the
connection that wrote it (see ``services/workshop_run.py``). When a run id is
known, from ``--run-id``, ``PELLIER_RUN_ID``, or ``~/.pellier/run_id``, every
query below is scoped to it, so a seeded incident or a facilitator's rehearsal
cannot stand in for the participant's own evidence. Rows written outside the
application's pool (the Lambda's Data API path, a direct script) carry no
run_id; the governance query admits those only when they were created after the
run started, and says so.

Usage
-----

    python3 scripts/build_receipt.py                     # newest participant
    python3 scripts/build_receipt.py --principal <sub>   # one participant
    python3 scripts/build_receipt.py --run-id run-0123456789ab
    python3 scripts/build_receipt.py --strict            # exit 1 unless complete
    python3 scripts/build_receipt.py --json receipt.json --markdown receipt.md
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence
from urllib.parse import quote_plus

REPO = pathlib.Path(__file__).resolve().parents[1]
BACKEND = REPO / "pellier" / "backend"
DEFAULT_ENV = BACKEND / ".env"

PROVED = "PROVED"
NOT_YET = "NOT YET"
UNCHECKED = "UNCHECKED"

RUN_ID_PATTERN = re.compile(r"^run-[0-9a-f]{12}$")
RUN_SCOPE_UNAVAILABLE = "unavailable (migration 049 not applied)"


# ---------------------------------------------------------------------------
# Source state -- read as text, deliberately
# ---------------------------------------------------------------------------
# The backend decides shipped-vs-exercise by importing the modules and
# inspecting their source. Importing them here would drag in FastAPI, settings,
# and a database handle, so a receipt could not be produced on a box whose
# backend does not start -- which is precisely when a table lead needs one. The
# marker strings below are the same ones routes/observatory.py looks for.


def _reads_as_stub(path: pathlib.Path, markers: tuple[str, ...]) -> Optional[bool]:
    """True when the file still reads as the shipped starter, None if unreadable."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return any(marker in source for marker in markers)


def collect_source_state() -> Dict[str, Any]:
    tool_stub = _reads_as_stub(
        BACKEND / "services" / "agent_tools.py",
        ("check_inventory is in stub state", "received_product_query"),
    )
    agent_stub = _reads_as_stub(
        BACKEND / "agents" / "inventory_agent.py",
        ("_INVENTORY_AGENT_STUBBED = True",),
    )

    def _state(is_stub: Optional[bool]) -> str:
        if is_stub is None:
            return UNCHECKED
        return NOT_YET if is_stub else PROVED

    return {
        "inventory_tool": _state(tool_stub),
        "inventory_agent_definition": _state(agent_stub),
    }


def collect_provenance() -> Dict[str, Any]:
    """Which content this box is running, and which revision it would deploy."""
    provenance: Dict[str, Any] = {}

    ref_file = REPO / ".workshop-ref.json"
    if ref_file.exists():
        try:
            provenance["source"] = json.loads(ref_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            provenance["source"] = {"error": "unreadable .workshop-ref.json"}
    else:
        # The env var is exported by CloudFormation UserData and dies with the
        # bootstrap shell, so it is a fallback, not the primary record.
        revision = os.environ.get("WORKSHOP_SOURCE_REVISION", "")
        provenance["source"] = {"repo_ref": revision} if revision else {}

    # The digest the renderer would stamp on a deploy from this tree. Comparing
    # it against what Runtime echoes is what proves the managed path executed
    # the participant's revision rather than a previous deployment.
    try:
        sys.path.insert(0, str(BACKEND))
        from services.build_fingerprint import compute_fingerprint

        provenance["runtime_build_fingerprint"] = compute_fingerprint(BACKEND)
    except Exception as exc:  # noqa: BLE001 - provenance is never load-bearing
        provenance["runtime_build_fingerprint"] = ""
        provenance["runtime_build_fingerprint_error"] = (
            f"{type(exc).__name__}: {str(exc)[:120]}"
        )
    return provenance


# ---------------------------------------------------------------------------
# Aurora evidence
# ---------------------------------------------------------------------------
# Each query carries a `{run_scope}` slot. It is filled with the run clause when
# a run id is in effect and migration 049 is installed, and left empty otherwise,
# so one query text serves both cases without a second copy to keep in sync.

_RUN_SCOPE_PROBE = "SELECT to_regclass('pellier.workshop_runs') AS installed;"

_LATEST_PRINCIPAL = """
SELECT principal_sub, MAX(created_at) AS last_seen
  FROM pellier.governed_turn_receipts
 WHERE principal_sub IS NOT NULL AND principal_sub <> ''
   {run_scope}
 GROUP BY principal_sub
 ORDER BY last_seen DESC
 LIMIT 1;
"""

# Lab 1 -- the tool ran and left an execution row.
_LAB1 = """
SELECT ta.audit_id, ta.session_id, ta.args->>'turn_id' AS turn_id,
       ta.caller, ta.latency_ms, ta.created_at
  FROM pellier.tool_audit ta
  LEFT JOIN pellier.governed_turn_receipts gtr
         ON gtr.turn_id = ta.args->>'turn_id'
 WHERE ta.tool = 'check_inventory'
   AND ta.result IS NOT NULL
   AND (%(sub)s IS NULL OR gtr.principal_sub = %(sub)s)
   {run_scope}
 ORDER BY ta.audit_id DESC
 LIMIT 1;
"""

# Lab 2 -- a receipt carrying BOTH retrieval ranks and their fusion. Vector or
# lexical alone is not hybrid retrieval, so all three must be populated.
_LAB2 = """
SELECT receipt_id, turn_id, query_preview, embedding_model, rerank_model,
       retrieval_config, latency_breakdown, modeled_cost_usd,
       jsonb_array_length(COALESCE(citation_ids, '[]'::jsonb)) AS citations,
       (rerank_scores IS NOT NULL AND rerank_scores <> '{}'::jsonb) AS reranked
  FROM pellier.retrieval_receipts
 WHERE (%(sub)s IS NULL OR principal_sub = %(sub)s)
   AND rrf_scores <> '{}'::jsonb
   AND vector_ranks <> '{}'::jsonb
   AND lexical_ranks <> '{}'::jsonb
   {run_scope}
 ORDER BY receipt_id DESC
 LIMIT 1;
"""

# Lab 3 -- the managed rail, proved durably rather than from the in-memory
# runtime receipt, which does not survive a backend restart.
#
# The proof is the turn receipt's own `rail`. `governed_turn_receipts` is
# written through the application pool
# (services/governed_turn_receipt.py::persist_turn_receipt), so migration 049's
# DEFAULT stamps this run on it, and the row records the rail that actually
# served the turn. That is exactly what Lab 3 sets out to establish.
#
# The gateway `tool_audit` row is reported, never required. Only the three
# mutation tools leave one -- the MCP Lambda audits them in
# scripts/deploy/common/dataapi.py -- and Gateway reads leave no tool_audit row
# at all. Lab 3's Theo journey ends at a pending review
# (tests/golden/journeys.json: `endsAt: proposal`) and performs no mutation, so
# demanding that row would make Lab 3 unprovable by completing Lab 3. The
# mutation chain is Lab 4's contract, on Jessica's return.
_LAB3 = """
SELECT gtr.turn_id, gtr.rail, gtr.terminal_status, gtr.created_at,
       ta.audit_id AS gateway_mutation_audit_id
  FROM pellier.governed_turn_receipts gtr
  LEFT JOIN pellier.tool_audit ta
         ON ta.args->>'turn_id' = gtr.turn_id
        AND ta.caller = 'gateway'
 WHERE (%(sub)s IS NULL OR gtr.principal_sub = %(sub)s)
   AND gtr.rail = 'gateway-mcp'
   {run_scope}
 ORDER BY gtr.created_at DESC, ta.audit_id DESC NULLS LAST
 LIMIT 1;
"""

# Lab 3 -- memory actually informed a turn, rather than merely being configured.
_LAB3_MEMORY = """
SELECT receipt_id, turn_id,
       jsonb_array_length(COALESCE(memory_record_ids_used, '[]'::jsonb)) AS records
  FROM pellier.retrieval_receipts
 WHERE (%(sub)s IS NULL OR principal_sub = %(sub)s)
   AND COALESCE(memory_record_ids_used, '[]'::jsonb) <> '[]'::jsonb
   {run_scope}
 ORDER BY receipt_id DESC
 LIMIT 1;
"""

# Lab 4 -- the decision chain. `audit_id IS NULL` on a DENY is the absence
# proof; the LEFT JOIN to write_operations is the durable-effect check.
_LAB4 = """
SELECT gr.receipt_id, gr.decision, gr.policy_name, gr.policy_engine_id,
       gr.verified_subject, gr.identity_source, gr.audit_id, gr.created_at,
       wo.idempotency_key, wo.operation, wo.completed_at
  FROM pellier.governed_receipts gr
  LEFT JOIN pellier.tool_audit ta ON ta.audit_id = gr.audit_id
  LEFT JOIN pellier.write_operations wo
         ON wo.idempotency_key = COALESCE(
              ta.args->>'idempotency_key', gr.args->>'idempotency_key')
 WHERE (%(sub)s IS NULL OR gr.principal_id = %(sub)s)
   AND gr.caller = 'gateway'
   {run_scope}
 ORDER BY gr.receipt_id DESC
 LIMIT 8;
"""

# The run clause per query. governed_receipts rows written by the Gateway
# helper through its own connection carry no run_id, so that query also admits
# unattributed rows created after the run started; every other table is written
# through the application pool and is scoped by run_id alone.
_RUN_CLAUSES = {
    "principal": "AND run_id = %(run)s",
    "lab1": "AND ta.run_id = %(run)s",
    "lab2": "AND run_id = %(run)s",
    "lab3": "AND gtr.run_id = %(run)s",
    "lab3_memory": "AND run_id = %(run)s",
    "lab4": (
        "AND (gr.run_id = %(run)s OR (gr.run_id IS NULL AND gr.created_at >= ("
        "SELECT wr.started_at FROM pellier.workshop_runs wr WHERE wr.run_id = %(run)s)))"
    ),
}


def _scoped(sql: str, label: str, scoped: bool) -> str:
    return sql.replace("{run_scope}", _RUN_CLAUSES[label] if scoped else "")


def parse_dotenv(env_path: pathlib.Path) -> Dict[str, str]:
    """Read KEY=value lines from a dotenv file without shell interpolation."""
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            if key.startswith("export "):
                key = key[len("export "):].strip()
            values[key] = value.strip().strip('"').strip("'")
    return values


def db_config(env_path: pathlib.Path) -> Optional[Dict[str, str]]:
    """Database settings from the backend .env, with the environment overriding."""
    cfg = parse_dotenv(env_path)
    for key in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_PORT"):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
    if not all(cfg.get(k) for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")):
        return None
    return cfg


def connection_dsn(cfg: Dict[str, str]) -> str:
    return (
        f"postgresql://{cfg['DB_USER']}:{quote_plus(cfg['DB_PASSWORD'])}"
        f"@{cfg['DB_HOST']}:{cfg.get('DB_PORT', '5432')}/{cfg['DB_NAME']}"
    )


def psycopg_connector() -> Optional[Callable[[str], Any]]:
    """Return a factory that opens one dict-row connection from a DSN.

    Sibling scripts (``workshop_doctor.py``) read the same Aurora with the same
    driver settings, so the factory is public rather than reimplemented there.

    Returns:
        A callable taking a DSN and returning a connection, or None when
        psycopg is not installed on this box.
    """
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return None
    return lambda dsn: psycopg.connect(dsn, row_factory=dict_row, connect_timeout=15)


def _run_scope_installed(conn: Any) -> bool:
    with conn.cursor() as cur:
        cur.execute(_RUN_SCOPE_PROBE)
        row = cur.fetchone()
    return bool(row and row.get("installed"))


def read_evidence(
    env_path: pathlib.Path,
    principal: Optional[str],
    run_id: Optional[str] = None,
    connect: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """Read every lab's evidence rows, scoped to ``run_id`` when one is known.

    Args:
        env_path: Backend ``.env`` to take database settings from.
        principal: Cognito subject to scope to; None selects the newest one.
        run_id: Workshop run to scope to; None leaves every query unscoped.
        connect: Connection factory taking a DSN; defaults to psycopg. Tests
            inject a fake here so the SQL contract runs offline.

    Returns:
        A dict with ``available`` and, when True, one entry per lab plus the
        run scope that was applied (``run_id``, ``none``, or the reason it
        could not be applied).
    """
    cfg = db_config(env_path)
    if cfg is None:
        return {
            "available": False,
            "reason": f"no database settings in {env_path} or the environment",
        }
    connect = connect or psycopg_connector()
    if connect is None:
        return {"available": False, "reason": "psycopg is not installed"}

    out: Dict[str, Any] = {"available": True, "run_id": run_id or ""}
    try:
        with connect(connection_dsn(cfg)) as conn:
            scoped = bool(run_id) and _run_scope_installed(conn)
            if scoped:
                out["run_scope"] = "run_id"
            else:
                out["run_scope"] = RUN_SCOPE_UNAVAILABLE if run_id else "none"
            params = {"sub": principal, "run": run_id if scoped else None}
            if principal is None:
                with conn.cursor() as cur:
                    cur.execute(_scoped(_LATEST_PRINCIPAL, "principal", scoped), params)
                    row = cur.fetchone()
                    principal = row["principal_sub"] if row else None
                params["sub"] = principal
            out["principal_sub"] = principal
            for label, sql in (
                ("lab1", _LAB1),
                ("lab2", _LAB2),
                ("lab3", _LAB3),
                ("lab3_memory", _LAB3_MEMORY),
            ):
                with conn.cursor() as cur:
                    cur.execute(_scoped(sql, label, scoped), params)
                    out[label] = cur.fetchone()
            with conn.cursor() as cur:
                cur.execute(_scoped(_LAB4, "lab4", scoped), params)
                out["lab4"] = cur.fetchall()
    except Exception as exc:  # noqa: BLE001 - report, never raise, to the room
        return {
            "available": False,
            "reason": f"{type(exc).__name__}: {str(exc)[:160]}",
        }
    return out


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _lab4_findings(rows: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Classify the Cedar chain without collapsing its distinct evidence.

    A DENY receipt and the absence of an execution row are two facts. This keeps
    them separate, and only claims non-execution when a DENY receipt carries no
    audit_id -- which is the row the Gateway would have written had it executed.
    """
    if rows is None:
        return {"decisions": UNCHECKED}
    allow = [r for r in rows if r["decision"] == "ALLOW"]
    deny = [r for r in rows if r["decision"] == "DENY"]
    executed = [r for r in allow if r["audit_id"] is not None]
    committed = [r for r in executed if r.get("completed_at") is not None]
    deny_without_execution = [r for r in deny if r["audit_id"] is None]

    return {
        "decisions": PROVED if rows else NOT_YET,
        "allow_seen": PROVED if allow else NOT_YET,
        "deny_seen": PROVED if deny else NOT_YET,
        "allow_executed": PROVED if executed else NOT_YET,
        "durable_effect": PROVED if committed else NOT_YET,
        "deny_did_not_execute": PROVED if deny_without_execution else NOT_YET,
        "policy_name": rows[0]["policy_name"] if rows else "",
        "latest_allow_audit_id": executed[0]["audit_id"] if executed else None,
        "latest_write_key": committed[0]["idempotency_key"] if committed else None,
    }


def assemble(evidence: Dict[str, Any]) -> Dict[str, Any]:
    source = collect_source_state()
    available = bool(evidence.get("available"))

    def row_state(key: str) -> str:
        if not available:
            return UNCHECKED
        return PROVED if evidence.get(key) else NOT_YET

    lab4 = _lab4_findings(evidence.get("lab4") if available else None)

    receipt: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "principal_sub": evidence.get("principal_sub") or "",
        "run_id": evidence.get("run_id") or "",
        "run_scope": evidence.get("run_scope") or "none",
        "evidence_source": (
            "aurora" if available else f"unavailable ({evidence.get('reason', '')})"
        ),
        "provenance": collect_provenance(),
        "labs": {
            "01_ground_the_answer": {
                "inventory_tool_written": source["inventory_tool"],
                "inventory_agent_defined": source["inventory_agent_definition"],
                "execution_row": row_state("lab1"),
                "detail": evidence.get("lab1") if available else None,
            },
            "02_measure_hybrid_retrieval": {
                "hybrid_receipt": row_state("lab2"),
                "detail": evidence.get("lab2") if available else None,
            },
            "03_operate_the_managed_path": {
                "managed_rail": row_state("lab3"),
                "memory_informed_a_turn": row_state("lab3_memory"),
                "detail": evidence.get("lab3") if available else None,
            },
            "04_govern_and_prove": lab4,
        },
    }

    # An explicit list of what this run has NOT established. A receipt that only
    # lists successes reads as a certificate; the unproven column is the half a
    # participant can act on, and the half a table lead needs.
    unproven: List[str] = []
    for lab, claims in receipt["labs"].items():
        for claim, state in claims.items():
            if claim == "detail" or not isinstance(state, str):
                continue
            if state in (NOT_YET, UNCHECKED):
                unproven.append(f"{lab}.{claim}: {state}")
    receipt["unproven"] = unproven
    receipt["complete"] = not unproven
    return receipt


def _fmt(state: Any) -> str:
    return str(state) if isinstance(state, str) else str(state)


def render_markdown(receipt: Dict[str, Any]) -> str:
    lines: List[str] = []
    add = lines.append
    add("# Pellier build receipt")
    add("")
    add(f"- Generated: `{receipt['generated_at']}`")
    add(f"- Participant: `{receipt['principal_sub'] or 'unidentified'}`")
    if receipt.get("run_id"):
        add(f"- Run: `{receipt['run_id']}` (scope: {receipt.get('run_scope', 'none')})")
    else:
        add("- Run: `none` (no run id; evidence is not scoped to one participant run)")
    add(f"- Evidence source: `{receipt['evidence_source']}`")
    prov = receipt.get("provenance", {})
    src = prov.get("source") or {}
    if src.get("repo_ref") or src.get("resolved_sha"):
        add(
            f"- Source: `{src.get('repo_ref', '?')}` @ "
            f"`{str(src.get('resolved_sha', '?'))[:12]}`"
        )
    if prov.get("runtime_build_fingerprint"):
        add(f"- Runtime build: `{prov['runtime_build_fingerprint'][:12]}`")
    add("")

    titles = {
        "01_ground_the_answer": "01 Ground the answer",
        "02_measure_hybrid_retrieval": "02 Measure hybrid retrieval",
        "03_operate_the_managed_path": "03 Operate the managed path",
        "04_govern_and_prove": "04 Govern and prove actions",
    }
    for key, claims in receipt["labs"].items():
        add(f"## {titles.get(key, key)}")
        add("")
        for claim, state in claims.items():
            if claim == "detail" or not isinstance(state, str):
                continue
            add(f"- {claim.replace('_', ' ')}: **{_fmt(state)}**")
        detail = claims.get("detail")
        if isinstance(detail, dict):
            # `gateway_mutation_audit_id` is named in full so a reader can tell
            # the rail proof from the optional mutation evidence beside it.
            keys = [
                k
                for k in (
                    "audit_id",
                    "receipt_id",
                    "turn_id",
                    "rail",
                    "gateway_mutation_audit_id",
                )
                if detail.get(k)
            ]
            if keys:
                add("")
                add("  " + " · ".join(f"`{k}={detail[k]}`" for k in keys))
        add("")

    add("## Not yet proven")
    add("")
    if receipt["unproven"]:
        for item in receipt["unproven"]:
            add(f"- {item}")
        add("")
        add(
            "> `UNCHECKED` means the query could not run, not that the step "
            "failed. Those are different findings."
        )
    else:
        add("- Nothing. Every boundary above is backed by a durable row.")
    add("")
    return "\n".join(lines)


def _resolve_run_id(explicit: Optional[str]) -> Optional[str]:
    """``--run-id`` wins; otherwise the run the service module considers current."""
    if explicit:
        return explicit
    try:
        sys.path.insert(0, str(BACKEND))
        from services.workshop_run import current_run_id
    except Exception:  # noqa: BLE001 - a receipt must build without the backend
        return None
    return current_run_id()


def _write_outputs(args: argparse.Namespace, receipt: Dict[str, Any], markdown: str) -> None:
    if args.json_out:
        pathlib.Path(args.json_out).write_text(
            json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8"
        )
    if args.md_out:
        pathlib.Path(args.md_out).write_text(markdown, encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(markdown)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--principal",
        default=None,
        help="Cognito sub to scope the receipt to (default: most recent turn)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="workshop run to scope to (default: PELLIER_RUN_ID or ~/.pellier/run_id)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 unless every lab's evidence contract is proved for the run",
    )
    parser.add_argument("--env", default=str(DEFAULT_ENV), help="backend .env path")
    parser.add_argument("--json", dest="json_out", default="", help="write JSON here")
    parser.add_argument(
        "--markdown", dest="md_out", default="", help="write Markdown here"
    )
    args = parser.parse_args(argv)

    run_id = _resolve_run_id(args.run_id)
    if run_id and not RUN_ID_PATTERN.fullmatch(run_id):
        print(f"build_receipt: run id {run_id!r} must match run-<12 hex>", file=sys.stderr)
        return 2
    if args.strict and not run_id:
        print(
            "build_receipt: --strict needs a run id; pass --run-id or run "
            "scripts/workshop-start.sh before Lab 1",
            file=sys.stderr,
        )
        return 1

    evidence = read_evidence(pathlib.Path(args.env), args.principal, run_id=run_id)
    receipt = assemble(evidence)
    _write_outputs(args, receipt, render_markdown(receipt))

    if not evidence.get("available"):
        # Only an unreadable evidence source is an error, because then the
        # receipt cannot speak to the run at all.
        return 1
    if args.strict and receipt["run_scope"] != "run_id":
        # Every query ran unscoped, so a seeded forensic row or a facilitator's
        # rehearsal would grade as this participant's proof. A strict receipt
        # that cannot tell those apart is worse than no receipt.
        print(
            f"STRICT: evidence could not be scoped to run {run_id} "
            f"(run_scope={receipt['run_scope']}). Apply "
            "scripts/migrations/049_workshop_runs.sql, rerun the labs, then "
            "rebuild the receipt.",
            file=sys.stderr,
        )
        return 1
    if args.strict and not receipt["complete"]:
        print(
            f"STRICT: {len(receipt['unproven'])} claim(s) not proved for run {run_id}:",
            file=sys.stderr,
        )
        for item in receipt["unproven"]:
            print(f"  {item}", file=sys.stderr)
        return 1
    # Default mode exits 0 even when boundaries are unproven: an incomplete run
    # is a true report, not a tool failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
