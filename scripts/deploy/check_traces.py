#!/usr/bin/env python3
"""Check recent AgentCore Runtime invocation events.

Usage:
    uv run check_traces.py --runtime-id "$AGENT_RUNTIME_ID" --last 5
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def check_traces(runtime_id: str, last_n: int, region: str) -> bool:
    """Query CloudWatch Logs for recent AgentCore Runtime invocations."""
    logs_client = boto3.client("logs", region_name=region)
    log_group = f"/aws/bedrock-agentcore/runtimes/{runtime_id}"

    print(f"Checking log group: {log_group}")
    print(f"Looking for last {last_n} invocations...\n")

    try:
        now = datetime.now(timezone.utc)
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=int((now - timedelta(hours=1)).timestamp() * 1000),
            endTime=int(now.timestamp() * 1000),
            limit=last_n * 10,
            interleaved=True,
        )
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"Log group not found: {log_group}")
        print("The Runtime may not have been invoked yet, or the ID is incorrect.")
        return False

    events = response.get("events", [])
    if not events:
        print("No recent Runtime events found.")
        print(
            "Invoke it first:\n"
            "  uv run test_runtime.py "
            '--runtime-arn "$AGENT_RUNTIME_ARN" '
            '--prompt "Find linen pieces" --token "$TOKEN"'
        )
        return False

    displayed = events[-last_n:]
    print(f"Recent Runtime events ({len(displayed)} shown):\n")
    for index, event in enumerate(displayed, 1):
        timestamp = datetime.fromtimestamp(
            event["timestamp"] / 1000,
            tz=timezone.utc,
        ).strftime("%H:%M:%S")
        message = " ".join(str(event.get("message", "")).split())
        if len(message) > 240:
            message = message[:237] + "..."
        print(f"  {index}. [{timestamp} UTC] {message}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AgentCore Runtime traces")
    parser.add_argument("--runtime-id", required=True, help="AgentCore Runtime ID")
    parser.add_argument("--last", type=int, default=5, help="Number of events to show")
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-east-1",
    )
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("AgentCore Runtime Events")
    print(f"  Runtime: {args.runtime_id}")
    print(f"{'=' * 60}\n")

    try:
        found = check_traces(args.runtime_id, args.last, args.region)
    except (BotoCoreError, ClientError) as exc:
        print(f"ERROR: Failed to query Runtime logs: {exc}", file=sys.stderr)
        return 1

    print(f"{'=' * 60}\n")
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
