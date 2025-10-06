#!/bin/bash
# DAT406 Workshop - Stage 1: Environment Bootstrap (AUTOMATIC INSTALLER VERSION - BACKUP)
# Purpose: Get Code Editor + VS Code ready FAST, then signal CloudFormation
# Duration: ~8 minutes
# NOTE: This version uses the AWS Code Editor installer script (has token issues)

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
# STEP 4: CODE EDITOR INSTALLATION - AUTOMATIC (~1 min)
# ============================================================================

log "Installing Code Editor (automatic installer)..."
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

# Rest of the script continues...
# (Truncated for brevity - this is just showing the key difference)
