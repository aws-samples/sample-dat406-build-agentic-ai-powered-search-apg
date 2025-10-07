#!/usr/bin/env python3
"""Generate MCP config dynamically from environment variables"""
import json
import os
import sys
from pathlib import Path

def generate_mcp_config():
    """Generate MCP server config from environment"""
    
    # Read from environment
    db_cluster_arn = os.environ.get('DB_CLUSTER_ARN', '')
    db_secret_arn = os.environ.get('DB_SECRET_ARN', '')
    db_name = os.environ.get('DB_NAME', 'postgres')
    aws_region = os.environ.get('AWS_REGION', 'us-west-2')
    
    if not db_cluster_arn or not db_secret_arn:
        print("❌ Missing required environment variables:")
        print(f"   DB_CLUSTER_ARN: {'✅' if db_cluster_arn else '❌ NOT SET'}")
        print(f"   DB_SECRET_ARN: {'✅' if db_secret_arn else '❌ NOT SET'}")
        sys.exit(1)
    
    config = {
        "mcpServers": {
            "awslabs.postgres-mcp-server": {
                "command": "uv",
                "args": [
                    "run",
                    "--with",
                    "awslabs.postgres-mcp-server",
                    "awslabs.postgres-mcp-server",
                    "--resource_arn",
                    db_cluster_arn,
                    "--secret_arn",
                    db_secret_arn,
                    "--database",
                    db_name,
                    "--region",
                    aws_region,
                    "--readonly",
                    "True"
                ],
                "env": {
                    "AWS_REGION": aws_region,
                    "FASTMCP_LOG_LEVEL": "ERROR"
                },
                "disabled": False,
                "autoApprove": []
            }
        }
    }
    
    # Write to config directory
    config_dir = Path(__file__).parent.parent / 'config'
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / 'mcp-server-config.json'
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ MCP config generated: {config_path}")
    print(f"   Cluster ARN: {db_cluster_arn}")
    print(f"   Secret ARN: {db_secret_arn}")
    print(f"   Region: {aws_region}")
    
    return config_path

if __name__ == '__main__':
    generate_mcp_config()
