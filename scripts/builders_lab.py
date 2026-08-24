#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Participant-facing client for the two exercises and agent wiring step."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = os.environ.get("PELLIER_BASE_URL", "http://localhost:8000")
DEFAULT_QUERY = "A housewarming gift under $100 that is in stock"


def _url(base_url: str, path: str, query: dict[str, str] | None = None) -> str:
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    return url


def _request_json(
    base_url: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    timeout: int = 75,
) -> dict[str, Any]:
    request = urllib.request.Request(
        _url(base_url, path, query),
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"{path} failed: {exc}") from exc


def _stream_chat(
    base_url: str,
    payload: dict[str, Any],
    *,
    session_token: str,
    output_path: Path,
    timeout: int = 75,
) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        _url(base_url, "/api/chat/stream"),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "X-Pellier-Session-Token": session_token,
        },
    )
    events: list[dict[str, Any]] = []
    try:
        with (
            urllib.request.urlopen(request, timeout=timeout) as response,
            output_path.open("w", encoding="utf-8") as output,
        ):
            for raw_line in response:
                line = raw_line.decode("utf-8")
                output.write(line)
                if not line.startswith("data: "):
                    continue
                try:
                    events.append(json.loads(line.removeprefix("data: ")))
                except json.JSONDecodeError:
                    continue
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"/api/chat/stream failed: {exc}") from exc
    return events


def _last_complete(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("type") == "complete":
            response = event.get("response")
            if isinstance(response, dict):
                return response
    raise RuntimeError("The chat stream ended without a complete event")


def readiness(args: argparse.Namespace) -> int:
    health = _request_json(args.base_url, "/api/health", timeout=10)
    build_state = _request_json(
        args.base_url,
        "/api/agent-trace/build-state",
        timeout=10,
    )
    version = subprocess.run(
        ["claude", "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    result = {
        "application": {
            "status": health.get("status"),
            "database": health.get("database"),
        },
        "claudeCode": {
            "version": version.stdout.strip() if version.returncode == 0 else None,
            "bedrockMode": os.environ.get("CLAUDE_CODE_USE_BEDROCK"),
            "model": os.environ.get("ANTHROPIC_MODEL"),
        },
        "exercise": {
            "Stock Keeper": (build_state.get("agents") or {}).get("Stock Keeper"),
            "floor_check": (build_state.get("tools") or {}).get("floor_check"),
        },
    }
    print(json.dumps(result, indent=2))
    ready = (
        result["application"]["status"] == "healthy"
        and result["application"]["database"] == "connected"
        and bool(result["claudeCode"]["version"])
        and result["claudeCode"]["bedrockMode"] == "1"
        # Pinned global profile — Workshop Studio does not expose Sonnet 5,
        # so the floating `sonnet` alias would resolve to a denied model.
        and result["claudeCode"]["model"] == "global.anthropic.claude-sonnet-4-6"
        and set(result["exercise"].values()) == {"exercise"}
    )
    if not ready:
        print("Readiness did not match the expected starter state.", file=sys.stderr)
        return 1
    return 0


def build_state(args: argparse.Namespace) -> int:
    payload = _request_json(
        args.base_url,
        "/api/agent-trace/build-state",
        timeout=10,
    )
    result = {
        "Stock Keeper": (payload.get("agents") or {}).get("Stock Keeper"),
        "floor_check": (payload.get("tools") or {}).get("floor_check"),
    }
    print(json.dumps(result, indent=2))
    expected_agent = args.expect_agent or args.expect
    expected_tool = args.expect_tool or args.expect
    if expected_agent is None or expected_tool is None:
        print(
            "Set --expect for both states or set both "
            "--expect-tool and --expect-agent.",
            file=sys.stderr,
        )
        return 2
    if (
        result["Stock Keeper"] != expected_agent
        or result["floor_check"] != expected_tool
    ):
        print(
            "Expected "
            f"Stock Keeper={expected_agent!r}, floor_check={expected_tool!r}.",
            file=sys.stderr,
        )
        return 1
    return 0


def tool_check(args: argparse.Namespace) -> int:
    payload = _request_json(
        args.base_url,
        "/api/agent-trace/tools/floor-check/run",
        query={"product_query": args.query},
        timeout=30,
    )
    print(json.dumps(payload, indent=2))
    brooklyn = next(
        (
            warehouse
            for warehouse in payload.get("warehouses", [])
            if warehouse.get("city") == "Brooklyn"
            or warehouse.get("warehouse_id") == "BK-01"
        ),
        None,
    )
    valid = (
        payload.get("status") == "success"
        and isinstance(brooklyn, dict)
        and isinstance(brooklyn.get("quantity"), int)
        and isinstance(brooklyn.get("ship_window_min"), int)
        and isinstance(brooklyn.get("ship_window_max"), int)
    )
    if not valid:
        print(
            "floor_check did not return the Brooklyn quantity and ship window.",
            file=sys.stderr,
        )
        return 1
    return 0


def compare(args: argparse.Namespace) -> int:
    payload = _request_json(
        args.base_url,
        "/api/agent-trace/search-strategies/compare",
        query={"query": args.query},
    )
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        f"Shared query embedding: "
        f"{payload.get('sharedQueryEmbeddingObservedMs')} ms"
    )
    for strategy in payload.get("strategies", []):
        products = ", ".join(
            product.get("name", "")
            for product in strategy.get("products", [])[:3]
        )
        components = ", ".join(strategy.get("costComponents", []))
        print(
            f"\n{strategy.get('strategy')}\n"
            f"  observed once: {strategy.get('observedMs')} ms\n"
            f"  modeled cost/1K: "
            f"${strategy.get('modeledCostPerThousandUsd')}\n"
            f"  components: {components}\n"
            f"  top 3: {products}"
        )

    cost_model = payload.get("costModel") or {}
    filters = ((payload.get("strategies") or [{}])[-1]).get(
        "extractedFilters",
        {},
    )
    print("\nCost model:")
    print(
        json.dumps(
            {
                "pricingReviewedOn": cost_model.get("pricingReviewedOn"),
                "pricingSource": cost_model.get("pricingSource"),
                "components": cost_model.get("components"),
            },
            indent=2,
        )
    )
    print("\nAgentic filters:")
    print(json.dumps(filters, indent=2))
    print(f"\nFull response: {args.output}")

    valid = (
        len(payload.get("strategies", [])) == 4
        and filters.get("priceMaxUsd") == 100
        and filters.get("inStockOnly") is True
        and bool(cost_model.get("components"))
    )
    if not valid:
        print("Comparison did not satisfy the Lab 2 evidence contract.", file=sys.stderr)
        return 1
    return 0


def receipt(args: argparse.Namespace) -> int:
    payload = _request_json(
        args.base_url,
        "/api/agent-trace/tool-audit/recent",
        query={"tool": "floor_check", "limit": "1"},
        timeout=10,
    )
    rows = payload.get("rows") or []
    row = rows[0] if rows and isinstance(rows[0], dict) else {}
    result = row.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            result = {}
    if not isinstance(result, dict):
        result = {}

    brooklyn = next(
        (
            warehouse
            for warehouse in result.get("warehouses", [])
            if isinstance(warehouse, dict)
            and (
                warehouse.get("city") == "Brooklyn"
                or warehouse.get("warehouse_id") == "BK-01"
            )
        ),
        None,
    )
    proof = {
        "source": payload.get("source"),
        "auditId": row.get("audit_id"),
        "sessionId": row.get("session_id"),
        "tool": row.get("tool"),
        "caller": row.get("caller"),
        "args": row.get("args"),
        "result": result,
        "latencyMs": row.get("latency_ms"),
        "createdAt": row.get("created_at"),
    }
    print(json.dumps(proof, indent=2))

    valid = (
        proof["source"] == "pellier.tool_audit"
        and isinstance(proof["auditId"], int)
        and bool(proof["sessionId"])
        and proof["tool"] == "floor_check"
        and proof["caller"] == "agent"
        and isinstance(proof["latencyMs"], int)
        and result.get("status") == "success"
        and isinstance(brooklyn, dict)
        and isinstance(brooklyn.get("quantity"), int)
        and isinstance(brooklyn.get("ship_window_min"), int)
        and isinstance(brooklyn.get("ship_window_max"), int)
    )
    if not valid:
        print(
            "No complete agent floor_check receipt was found in "
            "pellier.tool_audit.",
            file=sys.stderr,
        )
        return 1
    return 0


def ledger(args: argparse.Namespace) -> int:
    session_id = args.session or (
        f"builders-ledger-{int(time.time())}-{secrets.token_hex(4)}"
    )
    session_token = args.token or secrets.token_hex(32)

    turn_one = {
        "message": (
            "My Wabi-Sabi Bowl arrived chipped. Please file a damaged "
            "return (my customer id is 'theo')."
        ),
        "session_id": session_id,
        "pattern": "dispatcher",
    }
    turn_two = {
        "message": (
            "Without calling a tool, what customer id and damage did I "
            "just report?"
        ),
        "session_id": session_id,
        "pattern": "dispatcher",
    }
    _stream_chat(
        args.base_url,
        turn_one,
        session_token=session_token,
        output_path=args.ledger_output,
    )
    memory_events = _stream_chat(
        args.base_url,
        turn_two,
        session_token=session_token,
        output_path=args.memory_output,
    )
    memory = _last_complete(memory_events).get("memory") or {}

    print(f"Session: {session_id}")
    print("Memory receipt:")
    print(json.dumps(memory, indent=2))
    print(f"Session file: {args.session_file}")
    valid = (
        memory.get("source") == "agentcore-memory"
        and memory.get("loaded_messages") == 2
        and memory.get("persisted") is True
    )
    if not valid:
        print(
            "The recall check did not prove AgentCore session memory.",
            file=sys.stderr,
        )
        return 1
    args.session_file.write_text(session_id + "\n", encoding="utf-8")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--base-url", default=DEFAULT_BASE_URL)
    commands = root.add_subparsers(dest="command", required=True)

    readiness_parser = commands.add_parser("readiness")
    readiness_parser.set_defaults(handler=readiness)

    build_parser = commands.add_parser("build-state")
    build_parser.add_argument("--expect", choices=("exercise", "shipped"))
    build_parser.add_argument(
        "--expect-tool",
        choices=("exercise", "shipped"),
    )
    build_parser.add_argument(
        "--expect-agent",
        choices=("exercise", "shipped"),
    )
    build_parser.set_defaults(handler=build_state)

    tool_parser = commands.add_parser("tool-check")
    tool_parser.add_argument("--query", default="Hadley shirt")
    tool_parser.set_defaults(handler=tool_check)

    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("--query", default=DEFAULT_QUERY)
    compare_parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/retrieval-comparison.json"),
    )
    compare_parser.set_defaults(handler=compare)

    receipt_parser = commands.add_parser("receipt")
    receipt_parser.set_defaults(handler=receipt)

    ledger_parser = commands.add_parser("ledger")
    ledger_parser.add_argument("--session")
    ledger_parser.add_argument("--token")
    ledger_parser.add_argument(
        "--session-file",
        type=Path,
        default=Path("/tmp/pellier-ledger-session.txt"),
    )
    ledger_parser.add_argument(
        "--ledger-output",
        type=Path,
        default=Path("/tmp/pellier-ledger-turn.sse"),
    )
    ledger_parser.add_argument(
        "--memory-output",
        type=Path,
        default=Path("/tmp/pellier-memory-turn.sse"),
    )
    ledger_parser.set_defaults(handler=ledger)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.handler(args))
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
