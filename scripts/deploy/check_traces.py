#!/usr/bin/env python3
"""
Check recent AgentCore Runtime invocation traces for observability verification.

Usage:
    uv run check_traces.py --runtime-id $AGENT_RUNTIME_ID --last 5
"""
import argparse
import boto3
import json
import os
import sys
from datetime import datetime, timedelta


def check_traces(runtime_id: str, last_n: int, region: str):
    """Query CloudWatch Logs for recent AgentCore Runtime invocations."""
    logs_client = boto3.client("logs", region_name=region)

    # AgentCore Runtime logs to a predictable log group
    log_group = f"/aws/bedrock/agentcore/runtime/{runtime_id}"

    print(f"Checking log group: {log_group}")
    print(f"Looking for last {last_n} invocations...\n")

    # Check if the log group exists
    try:
        logs_client.describe_log_groups(logGroupNamePrefix=log_group, limit=1)
    except Exception:
        pass

    # Query recent log events
    try:
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)

        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            limit=last_n * 10,  # Over-fetch to account for multi-line events
            interleaved=True,
        )

        events = response.get("events", [])
        if not events:
            print("No recent traces found.")
            print("\nPossible reasons:")
            print("  - No invocations have been made yet")
            print("  - The Runtime is still provisioning")
            print(f"  - Log group '{log_group}' does not exist yet")
            print("\nTry sending a test request first:")
            print(f"  uv run test_runtime.py --runtime-id {runtime_id} "
                  f'--prompt "Find running shoes" --token "$TOKEN"')
            return

        # Parse and display invocation traces
        invocations = []
        current_invocation = None

        for event in events:
            message = event.get("message", "")
            timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)

            # Look for invocation start markers
            if "prompt" in message.lower() or "invoke" in message.lower():
                if current_invocation:
                    invocations.append(current_invocation)
                current_invocation = {
                    "timestamp": timestamp,
                    "events": [message.strip()],
                }
            elif current_invocation:
                current_invocation["events"].append(message.strip())

        if current_invocation:
            invocations.append(current_invocation)

        # Display the most recent N invocations
        displayed = invocations[-last_n:] if len(invocations) > last_n else invocations

        print(f"Recent traces ({len(displayed)} of {len(invocations)} found):\n")
        for i, inv in enumerate(displayed, 1):
            ts = inv["timestamp"].strftime("%H:%M:%S")
            print(f"  {i}. [{ts}]")
            for line in inv["events"][:5]:  # Show first 5 lines per invocation
                # Truncate very long lines
                if len(line) > 120:
                    line = line[:117] + "..."
                print(f"     {line}")
            if len(inv["events"]) > 5:
                print(f"     ... ({len(inv['events']) - 5} more lines)")
            print()

    except logs_client.exceptions.ResourceNotFoundException:
        print(f"Log group not found: {log_group}")
        print("\nThe AgentCore Runtime may not have been invoked yet,")
        print("or the Runtime ID may be incorrect.")
        print(f"\nTry sending a test request first:")
        print(f"  uv run test_runtime.py --runtime-id {runtime_id} "
              f'--prompt "Find running shoes" --token "$TOKEN"')
    except Exception as e:
        print(f"ERROR: Failed to query traces: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Check AgentCore Runtime traces")
    parser.add_argument("--runtime-id", required=True, help="AgentCore Runtime ID")
    parser.add_argument("--last", type=int, default=5, help="Number of recent traces to show")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"AgentCore Runtime Traces")
    print(f"  Runtime: {args.runtime_id}")
    print(f"{'='*60}\n")

    check_traces(args.runtime_id, args.last, args.region)

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
