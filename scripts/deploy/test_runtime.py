#!/usr/bin/env python3
"""Invoke the deployed CUSTOM_JWT Runtime over its raw HTTPS data plane.

Usage:
    uv run test_runtime.py \
      --runtime-arn "$AGENT_RUNTIME_ARN" \
      --prompt "Find a linen shirt under $250." \
      --token "$TOKEN"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def invoke_runtime(
    *,
    runtime_arn: str,
    prompt: str,
    token: str,
    region: str,
    session_id: str,
) -> dict[str, Any]:
    """Return one authenticated Runtime response.

    CUSTOM_JWT Runtime calls use a bearer token on the raw data-plane request.
    The normal SDK call is SigV4-authenticated and cannot carry this caller JWT.
    """
    escaped_arn = urllib.parse.quote(runtime_arn, safe="")
    url = (
        f"https://bedrock-agentcore.{region}.amazonaws.com"
        f"/runtimes/{escaped_arn}/invocations?qualifier=DEFAULT"
    )
    runtime_session_id = (session_id or "pellier-runtime-smoke").ljust(33, "0")
    payload = json.dumps(
        {
            "prompt": prompt,
            "session_id": session_id,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": runtime_session_id,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read().decode("utf-8", errors="replace")

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = {"response": raw}
    if not isinstance(decoded, dict):
        raise RuntimeError("Runtime returned a non-object JSON response.")
    return decoded


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test the Pellier CUSTOM_JWT AgentCore Runtime"
    )
    parser.add_argument(
        "--runtime-arn",
        required=True,
        help="Full AgentCore Runtime ARN",
    )
    parser.add_argument("--prompt", required=True, help="Prompt to send")
    parser.add_argument("--token", required=True, help="Cognito access token")
    parser.add_argument(
        "--session-id",
        default="pellier-runtime-smoke",
        help="Stable application session id",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-east-1",
    )
    args = parser.parse_args()

    try:
        result = invoke_runtime(
            runtime_arn=args.runtime_arn,
            prompt=args.prompt,
            token=args.token,
            region=args.region,
            session_id=args.session_id,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"Runtime invoke failed with HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        print(f"Runtime invoke failed: {exc}", file=sys.stderr)
        return 1

    if result.get("rail") != "gateway-mcp":
        print(
            "Runtime invoke failed: expected rail=gateway-mcp, got "
            f"{result.get('rail') or 'missing'}",
            file=sys.stderr,
        )
        return 1
    if not str(result.get("response") or "").strip():
        print("Runtime invoke failed: response payload is empty", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
