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

echo "🛠️  Building frontend for production..."
NODE_ENV=production npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build complete!"
echo ""
echo "🚀 Starting frontend server on port 5173..."
if [ -n "$CLOUDFRONT_URL" ]; then
    echo "🌐 Access at: ${CLOUDFRONT_URL}/ports/5173/"
else
    echo "🌐 Access at: http://localhost:5173"
fi
echo ""

# Serve with cache control headers:
# - index.html: no-cache (always check for updates)
# - assets/*: max-age=31536000 (1 year, safe because filenames have hashes)
npx http-server dist -p 5173 --cors -c-1
