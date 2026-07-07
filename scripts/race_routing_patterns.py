#!/usr/bin/env python3
"""Race Pellier's three routing patterns against one shopper turn.

The script is intentionally read-only except for the chat turns it fires.
Each turn uses a unique session id so the optional workshop rail can compare
SSE telemetry with the matching ``pellier.tool_audit`` rows.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


PATTERNS = ("dispatcher", "agents_as_tools", "graph")
DEFAULT_MESSAGE = "Is the Hadley shirt available in the Brooklyn warehouse?"


def _post_stream(base_url: str, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base_url.rstrip('/')}/api/chat/stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    complete: dict[str, Any] = {}
    try:
        with urlopen(req, timeout=90) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "complete":
                    complete = event.get("response") or {}
    except URLError as exc:
        raise RuntimeError(f"backend request failed: {exc}") from exc
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return complete, elapsed_ms


def _tool_rows(session_id: str) -> list[dict[str, str]]:
    escaped_session = session_id.replace("'", "''")
    sql = (
        "SELECT tool, caller, latency_ms::text "
        "FROM pellier.tool_audit "
        f"WHERE session_id = '{escaped_session}' "
        "ORDER BY created_at;"
    )
    try:
        result = subprocess.run(
            ["psql", "-t", "-A", "-F", "\t", "-c", sql],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        tool, caller, latency = (line.split("\t") + ["", "", ""])[:3]
        rows.append({"tool": tool, "caller": caller, "latency_ms": latency})
    return rows


def _agent_metric(response: dict[str, Any], elapsed_ms: int) -> dict[str, Any]:
    execution = response.get("agent_execution") or {}
    spans = execution.get("spans") or []
    llm_spans = [
        span for span in spans
        if str(span.get("name") or "").startswith("invoke_agent")
    ]
    usage = execution.get("usage") or {}
    return {
        "elapsed_ms": elapsed_ms,
        "llm_spans": len(llm_spans),
        "specialist": execution.get("specialistRoute") or "",
        "tokens": int(response.get("token_count") or 0),
        "token_source": (response.get("cost_breakdown") or {}).get("token_source") or usage.get("source") or "",
        "cost_usd": float(response.get("estimated_cost_usd") or 0.0),
        "trace_id": (execution.get("trace_id") or "")[:12],
    }


def _print_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        "pattern",
        "elapsed_ms",
        "llm_spans",
        "specialist",
        "tokens",
        "token_source",
        "est_cost_usd",
        "audit_rows",
        "trace_id",
    ]
    print("\t".join(headers))
    for row in rows:
        print(
            "\t".join(
                [
                    str(row["pattern"]),
                    str(row["elapsed_ms"]),
                    str(row["llm_spans"]),
                    str(row["specialist"] or "-"),
                    str(row["tokens"]),
                    str(row["token_source"] or "-"),
                    f"{row['cost_usd']:.6f}",
                    str(row["audit_rows"] or "-"),
                    str(row["trace_id"] or "-"),
                ]
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare dispatcher, agents-as-tools, and graph routing."
    )
    parser.add_argument("--base-url", default=os.getenv("PELLIER_API_URL", "http://localhost:8000"))
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--customer-id", default="CUST-MARCO")
    parser.add_argument("--session-prefix", default=f"routing-race-{int(time.time())}")
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for pattern in PATTERNS:
        session_id = f"{args.session_prefix}-{pattern}"
        payload = {
            "message": args.message,
            "session_id": session_id,
            "customer_id": args.customer_id,
            "pattern": pattern,
        }
        print(f"Running {pattern}...", file=sys.stderr)
        response, elapsed_ms = _post_stream(args.base_url, payload)
        metric = _agent_metric(response, elapsed_ms)
        tool_rows = _tool_rows(session_id)
        metric.update(
            {
                "pattern": pattern,
                "audit_rows": ", ".join(
                    f"{r['tool']}:{r['caller']}:{r['latency_ms']}ms"
                    for r in tool_rows
                ),
            }
        )
        rows.append(metric)

    _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
