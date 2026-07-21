#!/usr/bin/env python3
"""
Test AgentCore Gateway tool discovery — lists all MCP tools registered with the Gateway.

Usage:
    uv run test_gateway_tools.py \
      --gateway-url $GATEWAY_URL \
      --token "$TOKEN"
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error


EXPECTED_TOOLS = {
    "preference_snapshot",
    "trace_receipt",
    "floor_check",
    "whats_trending",
    "price_intelligence",
    "restock_shelf",
    "process_return",
    "escalate_to_stylist",
    "find_pieces",
    "find_pieces_hybrid",
    "explore_collection",
    "running_low",
    "side_by_side",
    "returns_and_care",
    "style_match",
}


def _canonical_name(name: str) -> str:
    """Strip AgentCore's target prefix from a discovered tool name."""
    return name.rsplit("__", 1)[-1]


def list_gateway_tools(gateway_url: str, token: str):
    """Call the Gateway's tools/list endpoint and display discovered tools."""
    url = gateway_url.rstrip("/") + "/tools/list"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="POST", data=b"{}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: Gateway returned {e.code}")
        print(f"  {e.read().decode()[:200]}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not reach Gateway: {e}")
        sys.exit(1)

    tools = body.get("tools", [])
    if not tools:
        print("WARNING: No tools discovered. Check that Lambda targets are registered.")
        return

    # Group tools by server (inferred from tool naming conventions)
    print("Discovered tools:\n")
    for tool in sorted(tools, key=lambda t: t.get("name", "")):
        name = tool.get("name", "unknown")
        desc = tool.get("description", "")
        # Truncate long descriptions for display
        if len(desc) > 80:
            desc = desc[:77] + "..."
        print(f"  - {name}")
        print(f"    {desc}")

    observed = {_canonical_name(tool.get("name", "")) for tool in tools}
    missing = sorted(EXPECTED_TOOLS - observed)
    unexpected = sorted(observed - EXPECTED_TOOLS)
    print(f"\nTotal: {len(tools)} tools")
    if len(tools) != 15 or missing or unexpected:
        print(f"ERROR: Expected the canonical 15 tools.")
        if missing:
            print(f"  Missing: {', '.join(missing)}")
        if unexpected:
            print(f"  Unexpected: {', '.join(unexpected)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Test AgentCore Gateway tool discovery")
    parser.add_argument("--gateway-url", required=True, help="AgentCore Gateway URL")
    parser.add_argument("--token", required=True, help="JWT token for authentication")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Gateway Tool Discovery")
    print(f"  Gateway: {args.gateway_url}")
    print(f"{'='*60}\n")

    list_gateway_tools(args.gateway_url, args.token)

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
