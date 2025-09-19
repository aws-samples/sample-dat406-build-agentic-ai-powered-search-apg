#!/bin/bash
# Workshop setup script for Blaize Bazaar
# This script is run automatically by CloudFormation during environment setup

set -euo pipefail

echo "=================================================="
echo "   Starting Blaize Bazaar Workshop Setup"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}➜${NC} $1"
}

# Set workshop directory
WORKSHOP_DIR="/workshop"
REPO_URL="https://github.com/aws-samples/sample-dat406-build-agentic-ai-powered-search-apg.git"

# Step 1: Clone the repository
print_info "Cloning repository from GitHub..."
cd $WORKSHOP_DIR
if [ -d "sample-dat406-build-agentic-ai-powered-search-apg" ]; then
    print_info "Repository already exists, pulling latest changes..."
    cd sample-dat406-build-agentic-ai-powered-search-apg
    git pull
else
    git clone $REPO_URL
    cd sample-dat406-build-agentic-ai-powered-search-apg
fi
print_status "Repository ready"

# Step 2: Setup Frontend
print_info "Setting up frontend application..."
cd frontend

# Install dependencies
print_info "Installing npm dependencies..."
npm install

# Build the production app
print_info "Building production app..."
npm run build

# Deploy to nginx
print_info "Deploying to web server..."
sudo mkdir -p /var/www/html/app
sudo rm -rf /var/www/html/app/*
sudo cp -r dist/* /var/www/html/app/
sudo chown -R nginx:nginx /var/www/html/app 2>/dev/null || sudo chown -R www-data:www-data /var/www/html/app

print_status "Frontend deployed"

# Step 3: Setup Backend
print_info "Setting up backend API..."
cd ../backend

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install -r requirements.txt

# Create systemd service for the API
print_info "Configuring API service..."
sudo tee /etc/systemd/system/blaize-api.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Blaize Bazaar API Service
After=network.target

[Service]
Type=simple
User=participant
WorkingDirectory=/workshop/sample-dat406-build-agentic-ai-powered-search-apg/backend
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/local/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --reload
Restart=always

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Start the API service
sudo systemctl daemon-reload
sudo systemctl enable blaize-api
sudo systemctl start blaize-api

print_status "Backend API running on port 8000"

# Step 4: Configure nginx
print_info "Configuring nginx proxy..."
sudo tee /etc/nginx/conf.d/blaize-bazaar.conf > /dev/null << 'EOFNGINX'
server {
    listen 80;
    listen [::]:80;
    server_name *.cloudfront.net localhost;
    
    # React app
    location /app/ {
        alias /var/www/html/app/;
        try_files $uri $uri/ /app/index.html;
        index index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type' always;
    }
}
EOFNGINX

sudo nginx -t && sudo systemctl reload nginx
print_status "Nginx configured"

# Step 5: Load sample data (if database is configured)
if [ -n "${DB_SECRET_ARN:-}" ]; then
    print_info "Loading product data into database..."
    cd ../scripts
    
    # Download sample data if not present
    if [ ! -f "../data/amazonproducts_sample.csv" ]; then
        print_info "Downloading sample data..."
        # You can upload your CSV to S3 and download it here
        # aws s3 cp s3://your-bucket/amazonproducts_sample.csv ../data/
    fi
    
    # Run data loader
    if [ -f "../data/amazonproducts_sample.csv" ]; then
        python load_products.py
        print_status "Product data loaded"
    else
        print_error "Sample data not found, skipping data load"
    fi
else
    print_info "Database not configured, skipping data load"
fi

# Step 6: Create helper scripts
print_info "Creating helper scripts..."
cd $WORKSHOP_DIR

# Create status check script
cat > check_status.sh << 'EOFSTATUS'
#!/bin/bash
echo "=================================="
echo "   Blaize Bazaar Status Check"
echo "=================================="

echo -n "Frontend: "
if [ -d "/var/www/html/app" ]; then
    echo "✓ Deployed"
else
    echo "✗ Not deployed"
fi

echo -n "API Service: "
if systemctl is-active --quiet blaize-api; then
    echo "✓ Running"
else
    echo "✗ Not running"
fi

echo -n "Nginx: "
if systemctl is-active --quiet nginx; then
    echo "✓ Running"
else
    echo "✗ Not running"
fi

echo ""
echo "Access your app at: /app/"
echo "API endpoint: /api/"
echo "=================================="
EOFSTATUS
chmod +x check_status.sh

# Create rebuild script
cat > rebuild_app.sh << 'EOFREBUILD'
#!/bin/bash
cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/frontend
npm run build
sudo rm -rf /var/www/html/app/*
sudo cp -r dist/* /var/www/html/app/
echo "✓ App rebuilt and deployed!"
EOFREBUILD
chmod +x rebuild_app.sh

print_status "Helper scripts created"

# Step 7: Final verification
print_info "Running final verification..."
sleep 2

# Check if services are running
if systemctl is-active --quiet blaize-api && systemctl is-active --quiet nginx; then
    print_status "All services running successfully!"
else
    print_error "Some services failed to start. Check logs for details."
fi

# Print summary
echo ""
echo "=================================================="
echo -e "${GREEN}   Workshop Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "Access Points:"
echo "  • Frontend: https://YOUR_CLOUDFRONT_URL/app/"
echo "  • API Docs: http://localhost:8000/docs"
echo ""
echo "Quick Commands:"
echo "  • Check status: ./check_status.sh"
echo "  • Rebuild app:  ./rebuild_app.sh"
echo "  • View API logs: sudo journalctl -u blaize-api -f"
echo ""
echo "Next Steps:"
echo "  1. Access the app at /app/"
echo "  2. Try searching for products"
echo "  3. Explore the workshop labs"
echo ""
echo "=================================================="