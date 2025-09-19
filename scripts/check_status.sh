#!/bin/bash
echo "==================================="
echo "   Blaize Bazaar Status Check"
echo "==================================="

echo -n "API Service: "
if systemctl is-active --quiet blaize-api 2>/dev/null; then
    echo "✅ Running"
else
    echo "⚠️  Not running or not configured"
fi

echo -n "Nginx: "
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo "✅ Running"
else
    echo "⚠️  Not running"
fi

echo ""
echo "Access your app at: https://YOUR_CLOUDFRONT_URL/app/"
echo "==================================="
