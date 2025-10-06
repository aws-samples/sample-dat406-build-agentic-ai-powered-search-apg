#!/bin/bash
# Manual Stage 2 Bootstrap Fix
# Run this on the EC2 instance if Stage 2 didn't run automatically

set -euo pipefail

echo "=========================================="
echo "Manual Stage 2 Bootstrap Fix"
echo "=========================================="

# Download Stage 2 script
echo "Downloading Stage 2 bootstrap script..."
curl -fsSL "https://raw.githubusercontent.com/aws-samples/sample-dat406-build-agentic-ai-powered-search-apg/main/deployment/bootstrap-labs.sh" -o /tmp/bootstrap-labs.sh

if [ ! -f /tmp/bootstrap-labs.sh ]; then
    echo "ERROR: Failed to download bootstrap-labs.sh"
    exit 1
fi

chmod +x /tmp/bootstrap-labs.sh

# Run Stage 2 in background
echo "Starting Stage 2 bootstrap (background)..."
nohup /tmp/bootstrap-labs.sh > /var/log/bootstrap-labs.log 2>&1 &
STAGE2_PID=$!

echo "✅ Stage 2 started (PID: $STAGE2_PID)"
echo ""
echo "Monitor progress with:"
echo "  tail -f /var/log/bootstrap-labs.log"
echo ""
echo "Check completion status:"
echo "  cat /tmp/workshop-ready.json"
echo ""
echo "This will take ~20 minutes to complete."
