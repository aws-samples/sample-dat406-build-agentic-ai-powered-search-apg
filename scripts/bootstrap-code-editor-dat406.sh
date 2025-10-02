#!/bin/bash
# DAT406 Workshop - Code Editor Bootstrap Script
# Sets up VS Code Server + React/Tailwind Frontend Environment
# Usage: ./bootstrap-code-editor-dat406.sh [PASSWORD]

set -euo pipefail

# Parameters
CODE_EDITOR_PASSWORD="${1:-defaultPassword}"
CODE_EDITOR_USER="participant"
HOME_FOLDER="/workshop"
REPO_URL="https://github.com/aws-samples/sample-dat406-build-agentic-ai-powered-search-apg.git"
REPO_NAME="sample-dat406-build-agentic-ai-powered-search-apg"

# Database configuration from environment (will be set by CloudFormation)
DB_SECRET_ARN="${DB_SECRET_ARN:-}"
DB_CLUSTER_ENDPOINT="${DB_CLUSTER_ENDPOINT:-}"
DB_CLUSTER_ARN="${DB_CLUSTER_ARN:-}"
DB_NAME="${DB_NAME:-postgres}"
AWS_REGION="${AWS_REGION:-us-west-2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

check_success() {
    if [ $? -eq 0 ]; then
        log "$1 - SUCCESS"
    else
        error "$1 - FAILED"
    fi
}

log "Starting DAT406 Code Editor Bootstrap"
log "Password: ${CODE_EDITOR_PASSWORD:0:4}****"

# ============================================================================
# SYSTEM PACKAGES
# ============================================================================

log "Installing base packages..."
dnf update -y
dnf install --skip-broken -y \
    curl gnupg whois argon2 unzip nginx openssl jq git wget \
    python3.13 python3.13-pip python3.13-devel python3.13-wheel \
    gcc gcc-c++ make postgresql16 postgresql16-devel
check_success "Base packages installation"

# Install Node.js 20.x (required for React/Vite)
log "Installing Node.js 20.x..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs
npm install -g npm@latest
check_success "Node.js installation"

node --version
npm --version

# ============================================================================
# AWS CLI v2
# ============================================================================

log "Installing AWS CLI v2..."
cd /tmp
if [ "$(uname -m)" = "aarch64" ]; then
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
else
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
fi
unzip -q awscliv2.zip
./aws/install --update
rm -rf awscliv2.zip aws/
cd -

if command -v aws &>/dev/null; then
    log "✅ AWS CLI installed: $(aws --version)"
else
    error "AWS CLI installation failed"
fi

# ============================================================================
# USER SETUP
# ============================================================================

log "Setting up user: $CODE_EDITOR_USER"
if ! id "$CODE_EDITOR_USER" &>/dev/null; then
    adduser -c '' "$CODE_EDITOR_USER"
    echo "$CODE_EDITOR_USER:$CODE_EDITOR_PASSWORD" | chpasswd
    usermod -aG wheel "$CODE_EDITOR_USER"
    sed -i 's/# %wheel/%wheel/g' /etc/sudoers
    check_success "User creation"
else
    log "User $CODE_EDITOR_USER already exists"
fi

# ============================================================================
# WORKSPACE SETUP
# ============================================================================

log "Setting up workspace directory..."
mkdir -p "$HOME_FOLDER"
cd "$HOME_FOLDER"

# Clone the repository
if [ ! -d "$HOME_FOLDER/$REPO_NAME" ]; then
    log "Cloning repository from GitHub..."
    git clone "$REPO_URL" || error "Failed to clone repository"
    check_success "Repository clone"
else
    log "Repository already exists"
fi

chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER"

# ============================================================================
# PYTHON SETUP
# ============================================================================

log "Setting up Python 3.13..."
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1
update-alternatives --set python3 /usr/bin/python3.13
ln -sf /usr/bin/python3.13 /usr/local/bin/python
ln -sf /usr/bin/python3.13 /usr/local/bin/python3

log "Installing Python packages..."
sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user --upgrade pip

# Backend dependencies
sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user \
    fastapi uvicorn "psycopg[binary,pool]" pgvector boto3 \
    pandas numpy python-dotenv pydantic pydantic-settings

# Data processing
sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user \
    jupyter jupyterlab matplotlib seaborn tqdm pandarallel

check_success "Python packages installation"

# ============================================================================
# FRONTEND SETUP
# ============================================================================

log "==================== Setting Up React Frontend ===================="

if [ -d "$HOME_FOLDER/$REPO_NAME/frontend" ]; then
    cd "$HOME_FOLDER/$REPO_NAME/frontend"
    
    log "Installing npm dependencies..."
    sudo -u "$CODE_EDITOR_USER" npm install
    check_success "Frontend npm packages installation"
    
    # Create environment file
    log "Creating frontend .env file..."
    cat > .env << ENV_FRONTEND
VITE_API_URL=http://localhost:8000
VITE_AWS_REGION=${AWS_REGION}
VITE_BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
VITE_BEDROCK_CHAT_MODEL=us.anthropic.claude-3-7-sonnet-20250219-v1:0
ENV_FRONTEND
    
    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" .env
    
    # Verify Vite config exists
    if [ ! -f "vite.config.ts" ] && [ ! -f "vite.config.js" ]; then
        log "Creating Vite configuration..."
        cat > vite.config.ts << 'VITE_CONFIG'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: false
  }
})
VITE_CONFIG
        chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" vite.config.ts
    fi
    
    log "✅ Frontend setup complete"
else
    warn "Frontend directory not found in repository"
fi

cd "$HOME_FOLDER"

# ============================================================================
# CODE EDITOR INSTALLATION
# ============================================================================

log "Installing Code Editor..."
export CodeEditorUser="$CODE_EDITOR_USER"
curl -fsSL https://code-editor.amazonaws.com/content/code-editor-server/dist/aws-workshop-studio/install.sh | bash -s --
check_success "Code Editor installation"

# Find Code Editor binary
if [ -f "/home/$CODE_EDITOR_USER/.local/bin/code-editor-server" ]; then
    CODE_EDITOR_CMD="/home/$CODE_EDITOR_USER/.local/bin/code-editor-server"
    log "Found Code Editor at: $CODE_EDITOR_CMD"
else
    error "Code Editor binary not found"
fi

# Configure authentication token
log "Configuring authentication token..."
sudo -u "$CODE_EDITOR_USER" mkdir -p "/home/$CODE_EDITOR_USER/.code-editor-server/data"
echo -n "$CODE_EDITOR_PASSWORD" > "/home/$CODE_EDITOR_USER/.code-editor-server/data/token"
chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "/home/$CODE_EDITOR_USER/.code-editor-server/data/token"

# ============================================================================
# NGINX CONFIGURATION
# ============================================================================

log "Configuring Nginx..."
mkdir -p /etc/nginx/conf.d

cat > /etc/nginx/conf.d/code-editor.conf << 'NGINX_CONFIG'
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # VS Code Server proxy
    location / {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection upgrade;
        proxy_set_header Accept-Encoding gzip;
        proxy_read_timeout 86400;
    }
    
    # React development server proxy (if needed)
    location /app/ {
        proxy_pass http://127.0.0.1:5173/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINX_CONFIG

nginx -t
systemctl enable nginx
systemctl restart nginx
check_success "Nginx configuration"

# ============================================================================
# CODE EDITOR SERVICE
# ============================================================================

log "Creating Code Editor systemd service..."
cat > /etc/systemd/system/code-editor@.service << EOF
[Unit]
Description=AWS Code Editor Server
After=network.target

[Service]
Type=simple
User=%i
Group=%i
WorkingDirectory=$HOME_FOLDER/$REPO_NAME
Environment=PATH=/usr/local/bin:/usr/bin:/bin:/home/$CODE_EDITOR_USER/.local/bin
Environment=HOME=/home/$CODE_EDITOR_USER
ExecStart=$CODE_EDITOR_CMD --accept-server-license-terms --host 127.0.0.1 --port 8080 --default-workspace $HOME_FOLDER/$REPO_NAME --default-folder $HOME_FOLDER/$REPO_NAME --connection-token $CODE_EDITOR_PASSWORD
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "code-editor@$CODE_EDITOR_USER"
systemctl start "code-editor@$CODE_EDITOR_USER"
check_success "Code Editor service creation"

# Wait for Code Editor
log "Waiting for Code Editor to initialize..."
sleep 20

MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ | grep -q "200\|302\|401\|403"; then
        log "Code Editor is responding"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            error "Code Editor failed to start"
        fi
        log "Waiting for Code Editor... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    fi
done

# ============================================================================
# VS CODE EXTENSIONS
# ============================================================================

log "==================== Installing VS Code Extensions ===================="

install_extension() {
    local EXT_ID=$1
    local EXT_NAME=$2
    log "Installing: $EXT_NAME ($EXT_ID)..."
    sudo -u "$CODE_EDITOR_USER" "$CODE_EDITOR_CMD" --install-extension "$EXT_ID" 2>&1 || warn "Extension $EXT_NAME installation failed"
}

install_extension "ms-python.python" "Python"
install_extension "ms-python.vscode-pylance" "Pylance"
install_extension "ms-toolsai.jupyter" "Jupyter"
install_extension "dbaeumer.vscode-eslint" "ESLint"
install_extension "esbenp.prettier-vscode" "Prettier"
install_extension "bradlc.vscode-tailwindcss" "Tailwind CSS IntelliSense"
install_extension "amazonwebservices.aws-toolkit-vscode" "AWS Toolkit"
install_extension "amazonwebservices.amazon-q-vscode" "Amazon Q"

# VS Code settings
SETTINGS_DIR="/home/$CODE_EDITOR_USER/.code-editor-server/User"
sudo -u "$CODE_EDITOR_USER" mkdir -p "$SETTINGS_DIR"

cat > "$SETTINGS_DIR/settings.json" << 'SETTINGS_JSON'
{
    "python.defaultInterpreterPath": "/usr/bin/python3.13",
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.cwd": "/workshop/sample-dat406-build-agentic-ai-powered-search-apg",
    "files.autoSave": "afterDelay",
    "workbench.startupEditor": "none",
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "[typescript]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode"
    },
    "[typescriptreact]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode"
    },
    "tailwindCSS.experimental.classRegex": [
        ["className\\s*=\\s*['\"`]([^'\"`]*)['\"`]"]
    ],
    "aws.telemetry": false,
    "extensions.autoUpdate": false,
    "telemetry.telemetryLevel": "off"
}
SETTINGS_JSON

chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$SETTINGS_DIR"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

log "==================== Database Configuration ===================="

export DB_HOST=""
export DB_PORT="5432"
export DB_USER=""
export DB_PASSWORD=""

if [ ! -z "$DB_SECRET_ARN" ] && [ "$DB_SECRET_ARN" != "none" ]; then
    log "Retrieving database credentials..."
    
    DB_SECRET=$(aws secretsmanager get-secret-value \
        --secret-id "$DB_SECRET_ARN" \
        --region "$AWS_REGION" \
        --query SecretString \
        --output text 2>/dev/null || echo "")
    
    if [ ! -z "$DB_SECRET" ]; then
        export DB_HOST=$(echo "$DB_SECRET" | jq -r '.host // empty')
        export DB_PORT=$(echo "$DB_SECRET" | jq -r '.port // "5432"')
        export DB_NAME=$(echo "$DB_SECRET" | jq -r '.dbname // .database // "postgres"')
        export DB_USER=$(echo "$DB_SECRET" | jq -r '.username // empty')
        export DB_PASSWORD=$(echo "$DB_SECRET" | jq -r '.password // empty')
        
        log "✅ Database credentials retrieved"
    fi
fi

# Create .env file
if [ ! -z "$DB_HOST" ] && [ ! -z "$DB_USER" ]; then
    cat > "$HOME_FOLDER/$REPO_NAME/.env" << ENV_FILE
# Database Configuration
DB_HOST='$DB_HOST'
DB_PORT='$DB_PORT'
DB_NAME='$DB_NAME'
DB_USER='$DB_USER'
DB_PASSWORD='$DB_PASSWORD'
DATABASE_URL='postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME'

# PostgreSQL Standard Variables
PGHOST='$DB_HOST'
PGPORT='$DB_PORT'
PGUSER='$DB_USER'
PGPASSWORD='$DB_PASSWORD'
PGDATABASE='$DB_NAME'

# AWS Configuration
AWS_REGION='$AWS_REGION'
AWS_DEFAULT_REGION='$AWS_REGION'

# Bedrock Models
BEDROCK_EMBEDDING_MODEL='amazon.titan-embed-text-v2:0'
BEDROCK_CHAT_MODEL='us.anthropic.claude-3-7-sonnet-20250219-v1:0'
ENV_FILE

    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER/$REPO_NAME/.env"
    chmod 600 "$HOME_FOLDER/$REPO_NAME/.env"
    
    # Create .pgpass
    cat > "/home/$CODE_EDITOR_USER/.pgpass" << PGPASS
$DB_HOST:$DB_PORT:$DB_NAME:$DB_USER:$DB_PASSWORD
PGPASS
    chmod 600 "/home/$CODE_EDITOR_USER/.pgpass"
    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "/home/$CODE_EDITOR_USER/.pgpass"
    
    log "✅ Database configuration complete"
fi

# Update bashrc
cat >> "/home/$CODE_EDITOR_USER/.bashrc" << 'BASHRC'

# DAT406 Workshop Environment
if [ -f /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.env ]; then
    set -a
    source /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.env
    set +a
fi

# Shortcuts
alias workshop='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg'
alias frontend='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/frontend && npm run dev'
alias backend='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/backend && uvicorn app:app --reload'
BASHRC

# ============================================================================
# HELPER SCRIPTS
# ============================================================================

log "Creating helper scripts..."

# Frontend start script
cat > "$HOME_FOLDER/$REPO_NAME/start-frontend.sh" << 'SCRIPT_FRONTEND'
#!/bin/bash
cd "$(dirname "$0")/frontend"
echo "🚀 Starting React development server..."
npm run dev
SCRIPT_FRONTEND

# Backend start script
cat > "$HOME_FOLDER/$REPO_NAME/start-backend.sh" << 'SCRIPT_BACKEND'
#!/bin/bash
cd "$(dirname "$0")/backend"
echo "🚀 Starting FastAPI backend..."
source ../.env
uvicorn app:app --reload --host 0.0.0.0 --port 8000
SCRIPT_BACKEND

chmod +x "$HOME_FOLDER/$REPO_NAME/start-frontend.sh"
chmod +x "$HOME_FOLDER/$REPO_NAME/start-backend.sh"
chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER/$REPO_NAME"/*.sh

# Create README
cat > "$HOME_FOLDER/$REPO_NAME/WORKSHOP_GUIDE.md" << 'README_MD'
# DAT406 Workshop - Quick Start Guide

## 🚀 Getting Started

### Start Frontend (React + Tailwind)
```bash
cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/frontend
npm run dev
```
Access at: http://localhost:5173

### Start Backend (FastAPI)
```bash
cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/backend
uvicorn app:app --reload
```
API docs at: http://localhost:8000/docs

### Database Setup
Run the database setup script (provided separately):
```bash
cd /workshop
./setup-database-dat406.sh
```

## 📁 Project Structure
- `frontend/` - React + TypeScript + Tailwind CSS
- `backend/` - FastAPI + PostgreSQL + Bedrock
- `data/` - Product catalog CSV
- `scripts/` - Utility scripts

## 🧪 Testing
```bash
# Test database
psql -c "SELECT version();"

# Test backend
curl http://localhost:8000/api/health

# Test Bedrock
aws bedrock-runtime list-foundation-models --region us-west-2
```
README_MD

chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER/$REPO_NAME/WORKSHOP_GUIDE.md"

# ============================================================================
# SUMMARY
# ============================================================================

log "==================== Bootstrap Summary ===================="
echo "✅ CODE EDITOR SETUP COMPLETE"
echo ""
echo "Services:"
echo "  Nginx: $(systemctl is-active nginx)"
echo "  Code Editor: $(systemctl is-active code-editor@$CODE_EDITOR_USER)"
echo ""
echo "Frontend:"
echo "  Location: /workshop/$REPO_NAME/frontend"
echo "  Start: ./start-frontend.sh"
echo ""
echo "Backend:"
echo "  Location: /workshop/$REPO_NAME/backend"
echo "  Start: ./start-backend.sh"
echo ""
echo "Next: Run ./setup-database-dat406.sh to load data"
log "============================================================"