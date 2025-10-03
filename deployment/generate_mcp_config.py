#!/usr/bin/env python3
"""
Generate mcp-server-config.json from environment variables
Run this from your backend directory after activating venv
"""
import json
import os
import sys

# Load from config.settings
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import settings
    
    db_cluster_arn = getattr(settings, 'DB_CLUSTER_ARN', '')
    db_secret_arn = getattr(settings, 'DB_SECRET_ARN', '')
    db_name = settings.DB_NAME
    aws_region = settings.AWS_REGION
    
except Exception as e:
    print(f"Error loading settings: {e}")
    print("Make sure you're running this from the backend directory with venv activated")
    sys.exit(1)

# Get AWS profile from environment or use default
aws_profile = os.getenv('AWS_PROFILE', 'default')

config = {
    "mcpServers": {
        "awslabs.postgres-mcp-server": {
            "command": "uvx",
            "args": [
                "awslabs.postgres-mcp-server@latest",
                "--resource_arn", db_cluster_arn,
                "--secret_arn", db_secret_arn,
                "--database", db_name,
                "--region", aws_region,
                "--readonly", "True"
            ],
            "env": {
                "AWS_PROFILE": aws_profile,
                "AWS_REGION": aws_region,
                "FASTMCP_LOG_LEVEL": "ERROR"
            },
            "disabled": False,
            "autoApprove": []
        }
    }
}

# Write to parent directory (project root)
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server-config.json')

with open(output_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✅ MCP config written to: {output_path}")
print(f"\nConfiguration:")
print(f"  Database: {db_name}")
print(f"  Region: {aws_region}")
print(f"  Cluster ARN: {db_cluster_arn[:50]}...")
print(f"  Secret ARN: {db_secret_arn[:50]}...")
print(f"  AWS Profile: {aws_profile}")