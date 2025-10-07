#!/bin/bash
# Start Frontend Server for DAT406 Workshop

cd "$(dirname "$0")/frontend"

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Get CloudFront URL from environment or .env file
if [ -z "$CLOUDFRONT_URL" ]; then
    if [ -f .env ]; then
        export $(grep -v '^#' .env | grep CLOUDFRONT_URL | xargs)
    fi
fi

echo "🚀 Starting frontend server on port 5173..."
if [ -n "$CLOUDFRONT_URL" ]; then
    echo "🌐 Access at: ${CLOUDFRONT_URL}/ports/5173/"
else
    echo "🌐 Access at: http://localhost:5173"
fi
echo ""

npx http-server dist -p 5173 --cors
