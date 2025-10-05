#!/bin/bash
# Health check script for Code Editor - Use this to verify CloudFront access
# Usage: ./verify-code-editor-health.sh

set -euo pipefail

CODE_EDITOR_USER="participant"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Code Editor Health Check"
echo "=========================================="

# 1. Check systemd service
echo -n "Code Editor Service: "
if systemctl is-active --quiet "code-editor@$CODE_EDITOR_USER"; then
    echo -e "${GREEN}RUNNING${NC}"
else
    echo -e "${RED}STOPPED${NC}"
    echo "Run: journalctl -u code-editor@$CODE_EDITOR_USER -n 50"
    exit 1
fi

# 2. Check nginx service
echo -n "Nginx Service: "
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}RUNNING${NC}"
else
    echo -e "${RED}STOPPED${NC}"
    exit 1
fi

# 3. Check Code Editor direct access
echo -n "Code Editor (port 8080): "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}HTTP $HTTP_CODE${NC}"
else
    echo -e "${RED}HTTP $HTTP_CODE (FAILED)${NC}"
    exit 1
fi

# 4. Check nginx proxy
echo -n "Nginx Proxy (port 80): "
NGINX_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/ 2>/dev/null || echo "000")
if [ "$NGINX_CODE" = "302" ] || [ "$NGINX_CODE" = "200" ]; then
    echo -e "${GREEN}HTTP $NGINX_CODE${NC}"
else
    echo -e "${RED}HTTP $NGINX_CODE (FAILED)${NC}"
    exit 1
fi

# 5. Check token file
echo -n "Token File: "
if [ -f "/home/$CODE_EDITOR_USER/.code-editor-server/data/token" ]; then
    echo -e "${GREEN}EXISTS${NC}"
else
    echo -e "${RED}MISSING${NC}"
    exit 1
fi

# 6. Check listening ports
echo ""
echo "Listening Ports:"
ss -tlnp | grep -E ':(80|8080)\s' || echo "No listeners found"

echo ""
echo -e "${GREEN}✅ All health checks passed${NC}"
echo "Code Editor should be accessible via CloudFront"
