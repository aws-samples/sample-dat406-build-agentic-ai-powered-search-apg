#!/usr/bin/env python3
"""
Test AgentCore Gateway authentication with Cognito JWT.

Usage:
    uv run test_gateway_auth.py \
      --gateway-url $GATEWAY_URL \
      --cognito-pool-id $COGNITO_POOL \
      --cognito-client-id $COGNITO_CLIENT
"""
import argparse
import boto3
import json
import os
import sys


def get_cognito_token(pool_id: str, client_id: str, region: str) -> str:
    """Obtain a JWT token from Cognito using the workshop test user."""
    client = boto3.client("cognito-idp", region_name=region)

    # Workshop default credentials (set during CloudFormation bootstrap)
    username = os.getenv("COGNITO_USERNAME", "workshop-user")
    password = os.getenv("COGNITO_PASSWORD", "Workshop2026!")

    try:
        response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )
        token = response["AuthenticationResult"]["IdToken"]
        return token
    except client.exceptions.NotAuthorizedException:
        print("ERROR: Invalid credentials. Check COGNITO_USERNAME and COGNITO_PASSWORD env vars.")
        sys.exit(1)
    except client.exceptions.UserNotFoundException:
        print(f"ERROR: User '{username}' not found in pool {pool_id}.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to obtain Cognito token: {e}")
        sys.exit(1)


def test_gateway_auth(gateway_url: str, token: str):
    """Test that the Gateway accepts the JWT token by listing tools."""
    import urllib.request
    import urllib.error

    url = gateway_url.rstrip("/") + "/tools/list"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="POST", data=b"{}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = json.loads(resp.read())
            tool_count = len(body.get("tools", []))
            print(f"JWT token obtained successfully")
            print(f"Gateway authentication: PASSED")
            print(f"  Status: {status}")
            print(f"  Tools discovered: {tool_count}")
    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 403:
            print(f"Gateway authentication: FAILED ({e.code})")
            print(f"  The JWT token was rejected by the Gateway.")
        else:
            print(f"Gateway authentication: FAILED ({e.code})")
            print(f"  {e.read().decode()[:200]}")
        sys.exit(1)
    except Exception as e:
        print(f"Gateway authentication: FAILED")
        print(f"  Connection error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Test AgentCore Gateway authentication")
    parser.add_argument("--gateway-url", required=True, help="AgentCore Gateway URL")
    parser.add_argument("--cognito-pool-id", required=True, help="Cognito User Pool ID")
    parser.add_argument("--cognito-client-id", required=True, help="Cognito App Client ID")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Testing Gateway Authentication")
    print(f"  Gateway: {args.gateway_url}")
    print(f"  Cognito Pool: {args.cognito_pool_id}")
    print(f"{'='*60}\n")

    token = get_cognito_token(args.cognito_pool_id, args.cognito_client_id, args.region)
    test_gateway_auth(args.gateway_url, token)

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
