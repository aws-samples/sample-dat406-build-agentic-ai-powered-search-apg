#!/bin/bash
# DAT406 Workshop - Code Editor Bootstrap Script (Updated v2.1)
# Sets up VS Code Server + Lab 1 (Jupyter) + Lab 2 (Full Stack) Environment
# Usage: ./bootstrap-code-editor-dat406.sh [PASSWORD]

set -euo pipefail

# Parameters
CODE_EDITOR_PASSWORD="${1:-defaultPassword}"
CODE_EDITOR_USER="participant"
HOME_FOLDER="/workshop"
REPO_URL="${REPO_URL:-https://github.com/aws-samples/sample-dat406-build-agentic-ai-powered-search-apg.git}"
REPO_NAME="sample-dat406-build-agentic-ai-powered-search-apg"

# Database configuration from environment
DB_SECRET_ARN="${DB_SECRET_ARN:-}"
DB_CLUSTER_ENDPOINT="${DB_CLUSTER_ENDPOINT:-}"
DB_NAME="${DB_NAME:-postgres}"
AWS_REGION="${AWS_REGION:-us-west-2}"
BEDROCK_EMBEDDING_MODEL="${BEDROCK_EMBEDDING_MODEL:-amazon.titan-embed-text-v2:0}"
BEDROCK_CHAT_MODEL="${BEDROCK_CHAT_MODEL:-us.anthropic.claude-sonnet-4-20250514-v1:0}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"; exit 1; }

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
# STEP 1: SYSTEM PACKAGES (CRITICAL FIRST)
# ============================================================================

log "Installing base packages..."
dnf update -y
dnf install --skip-broken -y \
    gnupg whois argon2 unzip nginx openssl jq git wget \
    python3.13 python3.13-pip python3.13-devel python3.13-wheel \
    gcc gcc-c++ make postgresql16
check_success "Base packages installation"

# Note: curl is already installed as curl-minimal on AL2023

# Install Node.js 20.x
log "Installing Node.js 20.x..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs
npm install -g npm@latest
check_success "Node.js installation"

# ============================================================================
# STEP 2: AWS CLI v2
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
    log "AWS CLI installed: $(aws --version)"
else
    error "AWS CLI installation failed"
fi

# ============================================================================
# STEP 3: USER SETUP
# ============================================================================

log "Setting up user: $CODE_EDITOR_USER"
if ! id "$CODE_EDITOR_USER" &>/dev/null; then
    adduser -c '' "$CODE_EDITOR_USER"
    echo "$CODE_EDITOR_USER:$CODE_EDITOR_PASSWORD" | chpasswd
    usermod -aG wheel "$CODE_EDITOR_USER"
    sed -i 's/# %wheel/%wheel/g' /etc/sudoers
    check_success "User creation"
else
    log "User already exists"
fi

# ============================================================================
# STEP 4: WORKSPACE AND REPOSITORY
# ============================================================================

log "Setting up workspace directory..."
mkdir -p "$HOME_FOLDER"
chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER"

# Clone repository if URL provided (skip if private/unavailable)
if [ ! -z "$REPO_URL" ] && [ "$REPO_URL" != "none" ]; then
    if [ ! -d "$HOME_FOLDER/$REPO_NAME" ]; then
        log "Attempting to clone repository..."
        if sudo -u "$CODE_EDITOR_USER" git clone "$REPO_URL" "$HOME_FOLDER/$REPO_NAME" 2>/dev/null; then
            log "Repository cloned successfully"
        else
            warn "Repository clone failed (may be private) - creating directory structure"
            sudo -u "$CODE_EDITOR_USER" mkdir -p "$HOME_FOLDER/$REPO_NAME"/{lab1,lab2/{backend,frontend,config},data,deployment,docs}
        fi
    else
        log "Repository already exists"
    fi
fi

# ============================================================================
# STEP 5: CODE EDITOR INSTALLATION (BEFORE EVERYTHING ELSE)
# ============================================================================

log "Installing Code Editor..."
export CodeEditorUser="$CODE_EDITOR_USER"
curl -fsSL https://code-editor.amazonaws.com/content/code-editor-server/dist/aws-workshop-studio/install.sh | bash -s --
check_success "Code Editor installation"

# Find binary
if [ -f "/home/$CODE_EDITOR_USER/.local/bin/code-editor-server" ]; then
    CODE_EDITOR_CMD="/home/$CODE_EDITOR_USER/.local/bin/code-editor-server"
    log "Found Code Editor at: $CODE_EDITOR_CMD"
else
    error "Code Editor binary not found"
fi

# Configure token
log "Configuring authentication token..."
sudo -u "$CODE_EDITOR_USER" mkdir -p "/home/$CODE_EDITOR_USER/.code-editor-server/data"
echo -n "$CODE_EDITOR_PASSWORD" > "/home/$CODE_EDITOR_USER/.code-editor-server/data/token"
chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "/home/$CODE_EDITOR_USER/.code-editor-server/data/token"

# ============================================================================
# STEP 6: NGINX CONFIGURATION
# ============================================================================

log "Configuring Nginx..."
mkdir -p /etc/nginx/conf.d
cat > /etc/nginx/conf.d/code-editor.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection upgrade;
        proxy_set_header Accept-Encoding gzip;
        proxy_read_timeout 86400;
    }
}
EOF

nginx -t
systemctl enable nginx
systemctl start nginx
check_success "Nginx configuration"

# ============================================================================
# STEP 7: CODE EDITOR SERVICE
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
WorkingDirectory=$HOME_FOLDER
Environment=PATH=/usr/local/bin:/usr/bin:/bin:/home/$CODE_EDITOR_USER/.local/bin
Environment=HOME=/home/$CODE_EDITOR_USER
ExecStart=$CODE_EDITOR_CMD --accept-server-license-terms --host 127.0.0.1 --port 8080 --default-workspace $HOME_FOLDER --default-folder $HOME_FOLDER --connection-token $CODE_EDITOR_PASSWORD
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

# ============================================================================
# STEP 8: WAIT FOR CODE EDITOR (CRITICAL)
# ============================================================================

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
        log "Waiting for Code Editor... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    fi
done

# ============================================================================
# STEP 9: VS CODE EXTENSIONS (AFTER SERVICE IS UP)
# ============================================================================

log "Installing VS Code Extensions..."

install_extension() {
    local EXT_ID=$1
    local EXT_NAME=$2
    log "Installing: $EXT_NAME"
    sudo -u "$CODE_EDITOR_USER" "$CODE_EDITOR_CMD" --install-extension "$EXT_ID" 2>&1 || warn "$EXT_NAME may require manual install"
}

# Essential extensions for Lab 1 and Lab 2
install_extension "ms-python.python" "Python"
install_extension "ms-python.vscode-pylance" "Pylance"
install_extension "ms-toolsai.jupyter" "Jupyter"  # CRITICAL for Lab 1 notebooks in VS Code
install_extension "dbaeumer.vscode-eslint" "ESLint"
install_extension "esbenp.prettier-vscode" "Prettier"
install_extension "bradlc.vscode-tailwindcss" "Tailwind CSS"
install_extension "amazonwebservices.aws-toolkit-vscode" "AWS Toolkit"
install_extension "amazonwebservices.amazon-q-vscode" "Amazon Q"

# Configure settings
SETTINGS_DIR="/home/$CODE_EDITOR_USER/.code-editor-server/User"
sudo -u "$CODE_EDITOR_USER" mkdir -p "$SETTINGS_DIR"

cat > "$SETTINGS_DIR/settings.json" << 'VSCODE_SETTINGS'
{
    "python.defaultInterpreterPath": "/usr/bin/python3.13",
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.cwd": "/workshop",
    "files.autoSave": "afterDelay",
    "workbench.startupEditor": "none",
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "aws.telemetry": false,
    "telemetry.telemetryLevel": "off",
    "jupyter.askForKernelRestart": false,
    "notebook.cellToolbarLocation": {
        "default": "right",
        "jupyter-notebook": "left"
    }
}
VSCODE_SETTINGS

chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$SETTINGS_DIR"

# ============================================================================
# STEP 10: PYTHON SETUP
# ============================================================================

log "Setting up Python 3.13..."
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1
update-alternatives --set python3 /usr/bin/python3.13

log "Installing Python packages..."
sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user --upgrade pip

# ============================================================================
# STEP 11: LAB 1 - JUPYTER NOTEBOOK DEPENDENCIES
# ============================================================================

log "Installing Lab 1 (Jupyter) dependencies..."
if [ -f "$HOME_FOLDER/$REPO_NAME/lab1/requirements.txt" ]; then
    sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user -r "$HOME_FOLDER/$REPO_NAME/lab1/requirements.txt"
    check_success "Lab 1 dependencies installation"
else
    warn "Lab 1 requirements.txt not found, installing core packages..."
    sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user \
        httpx>=0.25.0 \
        "psycopg[binary,pool]>=3.1.0" \
        pgvector>=0.2.0 \
        sqlparse>=0.4.0 \
        "pandas>=2.0.0" \
        "numpy<2.0" \
        "pandarallel>=1.6.0" \
        "matplotlib>=3.7.0" \
        "seaborn>=0.12.0" \
        "boto3>=1.28.0" \
        "tqdm>=4.65.0" \
        "python-dotenv>=1.0.0" \
        "ipykernel>=6.25.0" \
        "jupyter>=1.0.0" \
        "jupyterlab>=4.0.0" \
        "ipywidgets>=8.0.0" \
        "fastapi>=0.100.0" \
        "uvicorn>=0.23.0" \
        "pydantic>=2.0.0" \
        "pydantic-settings>=2.0.0"
    check_success "Core Lab 1 packages installation"
fi

# Register Jupyter kernel for Python 3.13
log "Registering Jupyter kernel for Python 3.13..."
sudo -u "$CODE_EDITOR_USER" python3.13 -m ipykernel install --user --name python3 --display-name "Python 3.13"
check_success "Jupyter kernel registration"

# ============================================================================
# STEP 12: LAB 2 - BACKEND DEPENDENCIES
# ============================================================================

log "Installing Lab 2 (Backend) dependencies..."
if [ -f "$HOME_FOLDER/$REPO_NAME/lab2/backend/requirements.txt" ]; then
    sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user -r "$HOME_FOLDER/$REPO_NAME/lab2/backend/requirements.txt"
    check_success "Lab 2 Backend dependencies installation"
else
    warn "Lab 2 Backend requirements.txt not found, installing core packages..."
    sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.30.0" \
        "python-multipart>=0.0.9" \
        "psycopg[binary,pool]>=3.2.0" \
        "pgvector>=0.2.5" \
        "boto3>=1.35.0" \
        "botocore>=1.35.0" \
        "pydantic>=2.0.0" \
        "pydantic-settings>=2.0.0" \
        "python-dotenv>=1.0.0" \
        "numpy>=1.22.0,<2.0.0" \
        "tenacity>=8.0.0" \
        "rich>=13.0.0" \
        "python-json-logger>=3.0.0" \
        strands-agents \
        strands-agents-tools \
        strands-agents-builder
    check_success "Core Lab 2 Backend packages installation"
fi

# ============================================================================
# STEP 13: LAB 2 - FRONTEND SETUP
# ============================================================================

if [ -d "$HOME_FOLDER/$REPO_NAME/lab2/frontend" ]; then
    log "Setting up Lab 2 React frontend..."
    cd "$HOME_FOLDER/$REPO_NAME/lab2/frontend"
    
    # Install dependencies
    if sudo -u "$CODE_EDITOR_USER" npm install 2>/dev/null; then
        log "Lab 2 Frontend dependencies installed"
    else
        warn "Lab 2 Frontend npm install failed - may need manual setup"
    fi
    cd -
else
    warn "Lab 2 Frontend directory not found - skipping frontend setup"
fi

# ============================================================================
# STEP 14: DATABASE CONFIGURATION & ENVIRONMENT FILES
# ============================================================================

log "Configuring database credentials..."

export DB_HOST=""
export DB_PORT="5432"
export DB_USER=""
export DB_PASSWORD=""

if [ ! -z "$DB_SECRET_ARN" ] && [ "$DB_SECRET_ARN" != "none" ]; then
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
        
        log "Database credentials retrieved"
    fi
fi

# Create .env files if we have DB credentials
if [ ! -z "$DB_HOST" ] && [ ! -z "$DB_USER" ]; then
    
    # ========== LAB 2 BACKEND .env ==========
    log "Creating Lab 2 Backend .env file..."
    cat > "$HOME_FOLDER/$REPO_NAME/lab2/backend/.env" << ENV_BACKEND
# Database Configuration
DB_HOST='$DB_HOST'
DB_PORT='$DB_PORT'
DB_NAME='$DB_NAME'
DB_USER='$DB_USER'
DB_PASSWORD='$DB_PASSWORD'
DATABASE_URL='postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME'

# PostgreSQL Connection
PGHOST='$DB_HOST'
PGPORT='$DB_PORT'
PGUSER='$DB_USER'
PGPASSWORD='$DB_PASSWORD'
PGDATABASE='$DB_NAME'

# AWS Configuration
AWS_REGION='$AWS_REGION'

# Bedrock Models (Updated for DAT406)
BEDROCK_EMBEDDING_MODEL='$BEDROCK_EMBEDDING_MODEL'
BEDROCK_CHAT_MODEL='$BEDROCK_CHAT_MODEL'
ENV_BACKEND

    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER/$REPO_NAME/lab2/backend/.env"
    chmod 600 "$HOME_FOLDER/$REPO_NAME/lab2/backend/.env"
    log "Lab 2 Backend .env created"
    
    # ========== LAB 2 FRONTEND .env ==========
    log "Creating Lab 2 Frontend .env file..."
    cat > "$HOME_FOLDER/$REPO_NAME/lab2/frontend/.env" << ENV_FRONTEND
# API Configuration
VITE_API_URL=http://localhost:8000

# AWS Configuration
VITE_AWS_REGION=$AWS_REGION

# Feature Flags
VITE_ENABLE_LAB2=true
ENV_FRONTEND

    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER/$REPO_NAME/lab2/frontend/.env"
    chmod 644 "$HOME_FOLDER/$REPO_NAME/lab2/frontend/.env"
    log "Lab 2 Frontend .env created"
    
    # ========== ROOT .env (for compatibility) ==========
    log "Creating root .env file..."
    cat > "$HOME_FOLDER/$REPO_NAME/.env" << ENV_ROOT
DB_HOST='$DB_HOST'
DB_PORT='$DB_PORT'
DB_NAME='$DB_NAME'
DB_USER='$DB_USER'
DB_PASSWORD='$DB_PASSWORD'
DATABASE_URL='postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME'
PGHOST='$DB_HOST'
PGPORT='$DB_PORT'
PGUSER='$DB_USER'
PGPASSWORD='$DB_PASSWORD'
PGDATABASE='$DB_NAME'
AWS_REGION='$AWS_REGION'
BEDROCK_EMBEDDING_MODEL='$BEDROCK_EMBEDDING_MODEL'
BEDROCK_CHAT_MODEL='$BEDROCK_CHAT_MODEL'
ENV_ROOT

    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER/$REPO_NAME/.env"
    chmod 600 "$HOME_FOLDER/$REPO_NAME/.env"
    
    # ========== .pgpass for psql CLI ==========
    cat > "/home/$CODE_EDITOR_USER/.pgpass" << PGPASS
$DB_HOST:$DB_PORT:$DB_NAME:$DB_USER:$DB_PASSWORD
PGPASS
    chmod 600 "/home/$CODE_EDITOR_USER/.pgpass"
    chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "/home/$CODE_EDITOR_USER/.pgpass"
    
    log "All environment files created successfully"
fi

# Update bashrc
cat >> "/home/$CODE_EDITOR_USER/.bashrc" << 'BASHRC'

# DAT406 Workshop Environment
if [ -f /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.env ]; then
    set -a
    source /workshop/sample-dat406-build-agentic-ai-powered-search-apg/.env
    set +a
fi

# Workshop aliases
alias workshop='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg'
alias lab1='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab1'
alias lab2='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2'
alias backend='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/backend'
alias frontend='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/frontend'

# Start Lab 2 services
start-backend() {
    cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/backend
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
}

start-frontend() {
    cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/frontend
    npm run dev
}

# Jupyter for Lab 1 (can run in VS Code or browser)
start-jupyter() {
    cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab1
    jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
}
BASHRC

# ============================================================================
# SUMMARY
# ============================================================================

log "==================== Bootstrap Complete ===================="
echo ""
echo "Environment Setup:"
echo "  ✅ Python 3.13 with Lab 1 & Lab 2 dependencies"
echo "  ✅ Node.js 20.x"
echo "  ✅ PostgreSQL 16 client"
echo "  ✅ Jupyter Lab & notebooks (with VS Code integration)"
echo "  ✅ VS Code Server with Jupyter extension"
echo ""
echo "Lab 1 - Jupyter Notebooks:"
echo "  📁 Location: $HOME_FOLDER/$REPO_NAME/lab1"
echo "  📓 Run notebooks directly in VS Code (Jupyter extension installed)"
echo "  🚀 Or use: start-jupyter (for browser-based Jupyter Lab)"
echo ""
echo "Lab 2 - Full Stack Application:"
echo "  📁 Backend: $HOME_FOLDER/$REPO_NAME/lab2/backend"
echo "  📁 Frontend: $HOME_FOLDER/$REPO_NAME/lab2/frontend"
echo ""
echo "Services:"
echo "  🌐 Nginx: $(systemctl is-active nginx)"
echo "  💻 Code Editor: $(systemctl is-active code-editor@$CODE_EDITOR_USER)"
echo ""
echo "Database:"
echo "  🗄️ Host: $DB_HOST"
echo "  🗄️ Database: $DB_NAME"
echo "  🗄️ Environment files created in lab2/backend and lab2/frontend"
echo ""
echo "Bedrock Models:"
echo "  🤖 Chat: $BEDROCK_CHAT_MODEL"
echo "  🔢 Embeddings: $BEDROCK_EMBEDDING_MODEL"
echo ""
echo "Quick Start Commands (in VS Code terminal):"
echo "  • workshop   - Go to workshop root"
echo "  • lab1       - Go to Lab 1 (open .ipynb files in VS Code)"
echo "  • lab2       - Go to Lab 2"
echo "  • backend    - Go to Lab 2 backend"
echo "  • frontend   - Go to Lab 2 frontend"
echo "  • start-jupyter    - Start Jupyter Lab in browser (optional)"
echo "  • start-backend    - Start FastAPI server (Lab 2)"
echo "  • start-frontend   - Start React dev server (Lab 2)"
echo ""
echo "Lab 1 Instructions:"
echo "  1. In VS Code, navigate to lab1/ folder"
echo "  2. Open the .ipynb notebook file"
echo "  3. VS Code will use the Jupyter extension to run it"
echo "  4. Select 'Python 3.13' kernel when prompted"
echo ""
echo "Access via CloudFront URL with token: $CODE_EDITOR_PASSWORD"
log "============================================================"