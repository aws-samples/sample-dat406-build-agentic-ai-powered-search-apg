#!/bin/bash
set -e

echo "🔧 Fixing CloudFront configuration..."

# Detect CloudFront URL from EC2 tags
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "us-west-2")
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null)

if [ -n "$INSTANCE_ID" ]; then
    CLOUDFRONT_URL=$(aws ec2 describe-tags \
        --region "$REGION" \
        --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=CloudFrontURL" \
        --query 'Tags[0].Value' \
        --output text 2>/dev/null || echo "")
fi

# Fallback to .env if available
if [ -z "$CLOUDFRONT_URL" ] || [ "$CLOUDFRONT_URL" = "None" ]; then
    CLOUDFRONT_URL=$(grep CLOUDFRONT_URL .env 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'" || echo "")
fi

# Error if CloudFront URL not found
if [ -z "$CLOUDFRONT_URL" ] || [ "$CLOUDFRONT_URL" = "None" ]; then
    echo "❌ CloudFront URL not found in EC2 tags or .env"
    echo "Please set CLOUDFRONT_URL in .env file"
    exit 1
fi

echo "✅ CloudFront URL: $CLOUDFRONT_URL"

# Update .env with CloudFront backend URL
cat > .env << EOF
VITE_API_URL=${CLOUDFRONT_URL}/ports/8000
VITE_AWS_REGION=us-west-2
EOF

echo "✅ Updated .env file"
cat .env

# Clean and rebuild
echo "🧹 Cleaning old build..."
rm -rf dist

echo "🔨 Building production bundle..."
NODE_ENV=production npm run build

# Kill old server
echo "🛑 Stopping old server..."
pkill -f "http-server" || true

# Start new server
echo "🚀 Starting production server..."
npx http-server dist -p 5173 --cors &

echo ""
echo "✅ Frontend rebuilt and deployed!"
echo "📍 Frontend: ${CLOUDFRONT_URL}/ports/5173/"
echo "📍 Backend:  ${CLOUDFRONT_URL}/ports/8000/"
echo ""
echo "⚠️  IMPORTANT: Hard refresh your browser (Cmd+Shift+R or Ctrl+Shift+R)"
