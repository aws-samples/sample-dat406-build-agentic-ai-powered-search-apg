#!/usr/bin/env python3
"""Invoke any Gateway tool through the real MCP path and classify the outcome.

Why this exists separately from ``gateway_initiate_return.py``: that script proves
one specific governed write and hardcodes its argument shape. Verifying a quiesce
needs the opposite — call an arbitrary tool, including one no policy names, and
report exactly what the service said.

The classifier is imported from ``gateway_initiate_return`` rather than
reimplemented. It distinguishes a Cedar DENY from a transport, JWT, or tool-name
failure, and a second copy would eventually disagree with it and turn a broken
Gateway into a fake policy proof.

The tool name is an argument precisely so this file does not have to name whichever
vocabulary is currently live:

    PY=pellier/backend/.venv/bin/python
    $PY scripts/probe_gateway_tool.py --tool "$TOOL" \\
        --args '{"customer_id":"CUST-THEO","product_id":1,"reason":"changed_mind"}'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "deploy"))

import anyio  # noqa: E402
import httpx  # noqa: E402
from mcp import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402

from gateway_initiate_return import (  # noqa: E402
    _exception_summary,
    _is_authorization_denial,
    _jsonable,
    _load_env,
    _require,
    _token_from_cognito,
)


async def _call(gateway_url: str, token: str, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    timeout = httpx.Timeout(30.0, read=120.0)
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
        follow_redirects=True,
    ) as http_client:
        async with streamable_http_client(gateway_url, http_client=http_client) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                catalog = await session.list_tools()
                names = sorted(t.name for t in catalog.tools)
                result = await session.call_tool(tool, args)
                return {
                    "outcome": "allow",
                    "tool": tool,
                    "arguments": args,
                    "gatewayCatalog": names,
                    "result": _jsonable(result),
                }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--args", default="{}", help="JSON object of tool arguments")
    parser.add_argument("--gateway-url", default="")
    args = parser.parse_args()

    _load_env()
    gateway_url = args.gateway_url or _require("AGENTCORE_GATEWAY_URL")
    token = _token_from_cognito()
    tool_args = json.loads(args.args)

    try:
        payload = anyio.run(_call, gateway_url, token, args.tool, tool_args)
    except BaseException as exc:  # noqa: BLE001 - the outcome IS the result here
        summary = _exception_summary(exc)
        payload = {
            # A denial and a broken Gateway must never print the same word.
            "outcome": "policy_denied" if _is_authorization_denial(exc) else "error",
            "tool": args.tool,
            "arguments": tool_args,
            "serviceResponse": summary,
        }

    print(json.dumps(payload, indent=2, default=str))
    return 0 if payload["outcome"] in ("allow", "policy_denied") else 1


if __name__ == "__main__":
    sys.exit(main())
