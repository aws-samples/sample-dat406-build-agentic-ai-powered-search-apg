#!/bin/bash
# DAT406 Workshop - Stage 1: Environment Bootstrap
# Purpose: Get Code Editor + VS Code ready FAST, then signal CloudFormation
# Duration: ~8 minutes

set -euo pipefail

# ============================================================================
# PARAMETERS FROM ENVIRONMENT
# ============================================================================
CODE_EDITOR_PASSWORD="${CODE_EDITOR_PASSWORD:-defaultPassword}"
CODE_EDITOR_USER="${CODE_EDITOR_USER:-participant}"
HOME_FOLDER="${HOME_FOLDER:-/workshop}"
CFN_WAIT_HANDLE="${CFN_WAIT_HANDLE:-}"
STAGE2_SCRIPT_URL="${STAGE2_SCRIPT_URL:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"; exit 1; }

log "=========================================="
log "DAT406 Stage 1: Environment Bootstrap"
log "=========================================="

# ============================================================================
# STEP 1: ESSENTIAL SYSTEM PACKAGES (~2 min)
# ============================================================================

log "Installing essential system packages..."
dnf update -y -q
dnf install --skip-broken -y -q \
    curl \
    gnupg \
    whois \
    argon2 \
    unzip \
    nginx \
    openssl \
    jq \
    git \
    wget \
    python3.13 \
    python3.13-pip \
    python3.13-setuptools \
    python3.13-devel \
    python3.13-wheel \
    python3.13-tkinter \
    gcc \
    gcc-c++ \
    make \
    postgresql16 \
    nodejs

log "✅ System packages installed"

# ============================================================================
# STEP 2: AWS CLI V2 (~1 min)
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
cd - > /dev/null

log "✅ AWS CLI installed: $(aws --version)"

# ============================================================================
# STEP 3: USER SETUP (~10 sec)
# ============================================================================

log "Setting up user: $CODE_EDITOR_USER"
if ! id "$CODE_EDITOR_USER" &>/dev/null; then
    adduser -c '' "$CODE_EDITOR_USER"
    echo "$CODE_EDITOR_USER:$CODE_EDITOR_PASSWORD" | chpasswd
    usermod -aG wheel "$CODE_EDITOR_USER"
    sed -i 's/# %wheel/%wheel/g' /etc/sudoers
    log "✅ User created"
else
    log "✅ User already exists"
fi

# Create workspace
mkdir -p "$HOME_FOLDER"
chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER"

# ============================================================================
# STEP 4: CODE EDITOR INSTALLATION (~1 min)
# ============================================================================

log "Installing Code Editor..."
export CodeEditorUser="$CODE_EDITOR_USER"
curl -fsSL https://code-editor.amazonaws.com/content/code-editor-server/dist/aws-workshop-studio/install.sh | bash -s --

# Find binary
if [ -f "/home/$CODE_EDITOR_USER/.local/bin/code-editor-server" ]; then
    CODE_EDITOR_CMD="/home/$CODE_EDITOR_USER/.local/bin/code-editor-server"
    log "✅ Code Editor installed at: $CODE_EDITOR_CMD"
else
    error "Code Editor binary not found"
fi

# Configure token (will be set after service is created)
log "Token will be configured after service creation"

# ============================================================================
# STEP 5: NGINX CONFIGURATION (~10 sec)
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
        proxy_set_header Host $http_host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection upgrade;
        proxy_set_header Accept-Encoding gzip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
EOF

nginx -t
systemctl enable nginx
systemctl start nginx
log "✅ Nginx configured and running"

# ============================================================================
# STEP 6: CODE EDITOR SERVICE (~10 sec)
# ============================================================================

log "Creating Code Editor systemd service..."

# Stop and disable the installer's default service
if systemctl is-active --quiet "code-editor@$CODE_EDITOR_USER"; then
    log "Stopping installer's default Code Editor service..."
    systemctl stop "code-editor@$CODE_EDITOR_USER" || true
    systemctl disable "code-editor@$CODE_EDITOR_USER" || true
fi

# Get AWS region from environment or EC2 metadata
AWS_REGION="${AWS_REGION:-$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo 'us-west-2')}"
log "AWS Region: $AWS_REGION"

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
Environment=AWS_REGION=$AWS_REGION
Environment=AWS_DEFAULT_REGION=$AWS_REGION
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

# Create token file BEFORE starting service
log "Creating token file with correct password..."
sudo -u "$CODE_EDITOR_USER" mkdir -p "/home/$CODE_EDITOR_USER/.code-editor-server/data"
echo -n "$CODE_EDITOR_PASSWORD" > "/home/$CODE_EDITOR_USER/.code-editor-server/data/token"
chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "/home/$CODE_EDITOR_USER/.code-editor-server/data/token"
chmod 600 "/home/$CODE_EDITOR_USER/.code-editor-server/data/token"

systemctl start "code-editor@$CODE_EDITOR_USER"
log "✅ Code Editor service started"

# ============================================================================
# STEP 7: WAIT FOR CODE EDITOR (~30 sec)
# ============================================================================

log "Waiting for Code Editor to initialize..."
sleep 10

MAX_RETRIES=20
RETRY_COUNT=0
CODE_EDITOR_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
        log "✅ Code Editor is responding (HTTP $HTTP_CODE)"
        CODE_EDITOR_READY=true
        sleep 3
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            error "Code Editor failed to start after $MAX_RETRIES attempts (HTTP: $HTTP_CODE)"
        fi
        log "Waiting for Code Editor... ($RETRY_COUNT/$MAX_RETRIES) [HTTP: $HTTP_CODE]"
        sleep 3
    fi
done

if [ "$CODE_EDITOR_READY" = "false" ]; then
    error "Code Editor did not become ready"
fi

# ============================================================================
# STEP 8: VS CODE EXTENSIONS (~3 min)
# ============================================================================

log "Installing VS Code extensions..."

install_extension() {
    local EXT_ID=$1
    local EXT_NAME=$2
    
    log "Installing extension: $EXT_NAME ($EXT_ID)..."
    
    if [ -f "$CODE_EDITOR_CMD" ]; then
        sudo -u "$CODE_EDITOR_USER" "$CODE_EDITOR_CMD" --install-extension "$EXT_ID" --force 2>&1 | tee -a /tmp/extension_install.log || true
        
        if grep -q "successfully installed" /tmp/extension_install.log 2>/dev/null; then
            log "  ✅ $EXT_NAME"
            return 0
        fi
    fi
    
    warn "  ⚠️  $EXT_NAME may require manual install"
    return 1
}

# Install essential extensions
install_extension "ms-python.python" "Python"
install_extension "ms-python.vscode-pylance" "Pylance"
install_extension "ms-toolsai.jupyter" "Jupyter"
install_extension "ms-toolsai.vscode-jupyter-cell-tags" "Jupyter Cell Tags"
install_extension "ms-toolsai.jupyter-keymap" "Jupyter Keymap"
install_extension "ms-toolsai.jupyter-renderers" "Jupyter Renderers"
install_extension "dbaeumer.vscode-eslint" "ESLint"
install_extension "esbenp.prettier-vscode" "Prettier"
install_extension "bradlc.vscode-tailwindcss" "Tailwind CSS"
install_extension "amazonwebservices.aws-toolkit-vscode" "AWS Toolkit"
install_extension "amazonwebservices.amazon-q-vscode" "Amazon Q"

log "✅ VS Code extensions installed"

# ============================================================================
# STEP 9: VS CODE SETTINGS (~5 sec)
# ============================================================================

log "Configuring VS Code settings..."
SETTINGS_DIR="/home/$CODE_EDITOR_USER/.code-editor-server/User"
sudo -u "$CODE_EDITOR_USER" mkdir -p "$SETTINGS_DIR"

cat > "$SETTINGS_DIR/settings.json" << 'VSCODE_SETTINGS'
{
    "python.defaultInterpreterPath": "/usr/bin/python3.13",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.globalModuleInstallation": true,
    "jupyter.jupyterServerType": "local",
    "jupyter.kernels.filter": [],
    "jupyter.notebookFileRoot": "/workshop",
    "jupyter.askForKernelRestart": false,
    "notebook.defaultKernel": "python3",
    "notebook.cellToolbarLocation": {
        "default": "right",
        "jupyter-notebook": "left"
    },
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.cwd": "/workshop",
    "files.autoSave": "afterDelay",
    "files.autoSaveDelay": 1000,
    "workbench.startupEditor": "none",
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "git.enabled": false,
    "git.autorefresh": false,
    "git.autofetch": false,
    "scm.defaultViewMode": "tree",
    "aws.telemetry": false,
    "amazonQ.telemetry": false,
    "telemetry.telemetryLevel": "off",
    "extensions.autoCheckUpdates": false,
    "extensions.autoUpdate": false,
    "extensions.ignoreRecommendations": true,
    "security.workspace.trust.enabled": false,
    "security.workspace.trust.startupPrompt": "never",
    "security.workspace.trust.banner": "never",
    "security.workspace.trust.emptyWindow": false
}
VSCODE_SETTINGS

chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$SETTINGS_DIR"

# Create Python environment file for workspace
log "Creating Python environment configuration..."
mkdir -p "$HOME_FOLDER/.vscode"
cat > "$HOME_FOLDER/.vscode/settings.json" << 'WORKSPACE_SETTINGS'
{
    "python.defaultInterpreterPath": "/usr/bin/python3.13",
    "jupyter.kernels.filter": [],
    "notebook.defaultKernel": "python3"
}
WORKSPACE_SETTINGS

chown -R "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "$HOME_FOLDER/.vscode"
log "✅ VS Code settings configured"

# ============================================================================
# STEP 10: PYTHON SETUP (~10 sec)
# ============================================================================

log "Setting up Python 3.13..."
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1
update-alternatives --set python3 /usr/bin/python3.13

# Upgrade pip
sudo -u "$CODE_EDITOR_USER" python3.13 -m pip install --user --upgrade pip -q

# Set AWS region and workshop shortcuts for user environment
log "Configuring AWS region and workshop shortcuts..."
cat >> "/home/$CODE_EDITOR_USER/.bashrc" << 'EOF'

# AWS Configuration
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"

# Workshop shortcuts
alias workshop='cd /workshop'
alias lab1='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab1'
alias lab2='cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2'

# Load .env file if it exists
if [ -f /workshop/.env ]; then
    set -a
    source /workshop/.env
    set +a
fi

# Add local bin to PATH
export PATH="$HOME/.local/bin:$PATH"
EOF

chown "$CODE_EDITOR_USER:$CODE_EDITOR_USER" "/home/$CODE_EDITOR_USER/.bashrc"

log "✅ Python 3.13 configured"

# ============================================================================
# STEP 11: FINAL VERIFICATION (~5 sec)
# ============================================================================

log "Performing final verification..."

# Verify Code Editor service
if systemctl is-active --quiet "code-editor@$CODE_EDITOR_USER"; then
    log "✅ Code Editor service is active"
else
    error "Code Editor service is not running"
fi

# Verify Code Editor responding
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    log "✅ Code Editor verified running (HTTP $HTTP_CODE)"
else
    error "Code Editor not responding (HTTP $HTTP_CODE)"
fi

# Verify Nginx
if systemctl is-active --quiet nginx; then
    log "✅ Nginx verified running"
else
    error "Nginx is not running"
fi

# Verify Nginx proxy
NGINX_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/ 2>/dev/null || echo "000")
if [ "$NGINX_CODE" = "302" ] || [ "$NGINX_CODE" = "200" ]; then
    log "✅ Nginx proxy verified (HTTP $NGINX_CODE)"
else
    error "Nginx proxy failing (HTTP $NGINX_CODE)"
fi

# ============================================================================
# STEP 12: SIGNAL CLOUDFORMATION SUCCESS (~1 sec)
# ============================================================================

if [ ! -z "${CFN_WAIT_HANDLE}" ]; then
    log "Signaling CloudFormation WaitCondition..."
    
    SIGNAL_SUCCESS=false
    for attempt in {1..5}; do
        SIGNAL_RESPONSE=$(curl -X PUT -H 'Content-Type:' \
            --data-binary "{\"Status\":\"SUCCESS\",\"Reason\":\"Code Editor Ready\",\"UniqueId\":\"Stage1-$(date +%s)\",\"Data\":\"Environment Bootstrap Complete\"}" \
            -w "\nHTTP_CODE:%{http_code}" \
            --max-time 10 \
            "$CFN_WAIT_HANDLE" 2>&1)
        
        SIGNAL_HTTP_CODE=$(echo "$SIGNAL_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
        
        if [ "$SIGNAL_HTTP_CODE" = "200" ]; then
            log "✅ CloudFormation signaled successfully (HTTP 200)"
            echo "$SIGNAL_RESPONSE" > /tmp/cfn-signal-stage1.log
            SIGNAL_SUCCESS=true
            break
        else
            warn "Signal attempt $attempt failed (HTTP: ${SIGNAL_HTTP_CODE:-unknown})"
            sleep 2
        fi
    done
    
    if [ "$SIGNAL_SUCCESS" = "false" ]; then
        error "CRITICAL: Failed to signal CloudFormation after 5 attempts"
    fi
else
    log "ℹ️  CFN_WAIT_HANDLE not set - development mode"
fi

# ============================================================================
# STEP 13: TRIGGER STAGE 2 IN BACKGROUND (~1 sec)
# ============================================================================

if [ ! -z "${STAGE2_SCRIPT_URL}" ]; then
    log "Triggering Stage 2: Labs Bootstrap (background)..."
    
    # Download Stage 2 script
    curl -fsSL "$STAGE2_SCRIPT_URL" -o /tmp/bootstrap-labs.sh
    chmod +x /tmp/bootstrap-labs.sh
    
    # Run Stage 2 in background
    nohup /tmp/bootstrap-labs.sh > /var/log/bootstrap-labs.log 2>&1 &
    STAGE2_PID=$!
    
    log "✅ Stage 2 triggered (PID: $STAGE2_PID)"
    log "   Monitor: tail -f /var/log/bootstrap-labs.log"
else
    warn "STAGE2_SCRIPT_URL not set - Stage 2 will not run"
fi

# ============================================================================
# SUMMARY
# ============================================================================

log "=========================================="
log "Stage 1: Environment Bootstrap Complete!"
log "=========================================="
echo ""
echo "✅ Code Editor ready and accessible"
echo "✅ VS Code extensions installed"
echo "✅ Python 3.13 configured"
echo "✅ CloudFormation signaled (stack continues)"
echo "⏳ Stage 2 running in background (Labs setup)"
echo ""
echo "Access Code Editor at CloudFront URL"
echo "Password: $CODE_EDITOR_PASSWORD"
echo ""
log "=========================================="

exit 0