#!/bin/bash
# Fix current workshop environment
set -e

echo "🔧 Fixing Workshop Environment..."
echo ""

cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg

# 1. Update MCP config with correct account
echo "1️⃣  Generating MCP config with your account..."
cd lab2/backend
python3 generate_mcp_config.py

# 2. Verify AWS credentials work
echo ""
echo "2️⃣  Verifying AWS credentials..."
python3 verify_aws_creds.py

echo ""
echo "✅ Environment fixed!"
echo ""
echo "Now start the backend:"
echo "  cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2"
echo "  ./START_BACKEND.sh"
