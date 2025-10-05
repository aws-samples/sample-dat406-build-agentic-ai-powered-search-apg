#!/usr/bin/env python3
"""
Generate mcp-server-config.json from environment variables
Run this from anywhere - loads from .env or environment
"""
import json
import os
import sys
from pathlib import Path

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env in backend or root
    backend_env = Path(__file__).parent.parent / 'lab2' / 'backend' / '.env'
    root_env = Path(__file__).parent.parent / '.env'
    
    if backend_env.exists():
        load_dotenv(backend_env)
    elif root_env.exists():
        load_dotenv(root_env)
except ImportError:
    pass  # python-dotenv not installed, use environment variables

# Load from environment variables
db_cluster_arn = os.getenv('DB_CLUSTER_ARN', '')
db_secret_arn = os.getenv('DB_SECRET_ARN', '')
db_name = os.getenv('DB_NAME', 'postgres')
aws_region = os.getenv('AWS_REGION', 'us-west-2')

if not db_cluster_arn or not db_secret_arn:
    print("❌ Error: Missing required environment variables")
    print("\nRequired:")
    print("  DB_CLUSTER_ARN")
    print("  DB_SECRET_ARN")
    print("\nOptional:")
    print("  DB_NAME (default: postgres)")
    print("  AWS_REGION (default: us-west-2)")
    print("  AWS_PROFILE (default: default)")
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
print(f"  Cluster ARN: {db_cluster_arn[:50] if len(db_cluster_arn) > 50 else db_cluster_arn}...")
print(f"  Secret ARN: {db_secret_arn[:50] if len(db_secret_arn) > 50 else db_secret_arn}...")
print(f"  AWS Profile: {aws_profile}")
print(f"\n💡 Tip: Set environment variables or create .env file with DB credentials")