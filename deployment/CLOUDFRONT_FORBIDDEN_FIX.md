# CloudFront "Forbidden" Error - Root Cause & Fix

## 🔴 Problem

CloudFront shows **"Forbidden"** error after CloudFormation deployment in Workshop Studio.

## 🔍 Root Cause

**Race condition between CloudFront creation and Code Editor readiness:**

1. CloudFormation creates EC2 instance
2. SSM document starts bootstrap script (takes 5-10 minutes)
3. CloudFront distribution is created with `DependsOn: RunCodeEditorSSMDoc`
4. **ISSUE**: `DependsOn` only waits for SSM command to be **sent**, not **completed**
5. CloudFront tries to fetch from origin (nginx → Code Editor on port 8080)
6. Code Editor isn't ready yet → nginx returns 502/403
7. CloudFront caches the error response → **"Forbidden"**

## ✅ Solutions Implemented

### 1. **CloudFormation: Wait Condition Lambda** (`dat406-code-editor.yml`)

Added `WaitForCodeEditorLambda` that:
- Polls `http://EC2_PUBLIC_DNS/` every 15 seconds
- Waits for HTTP 200 or 302 (Code Editor ready signal)
- Times out after 15 minutes (60 attempts × 15s)
- Blocks CloudFront creation until Code Editor is verified ready

**Key Changes:**
```yaml
WaitForCodeEditor:
  Type: Custom::WaitForCodeEditorLambda
  DependsOn: RunCodeEditorSSMDoc
  Properties:
    ServiceToken: !GetAtt WaitForCodeEditorLambda.Arn
    OriginUrl: !Sub 'http://${CodeEditorInstance.PublicDnsName}/'

CloudFrontDistribution:
  Type: AWS::CloudFront::Distribution
  DependsOn: WaitForCodeEditor  # Changed from RunCodeEditorSSMDoc
```

### 2. **Bootstrap Script: Enhanced Verification** (`bootstrap-code-editor-dat406.sh`)

Improved final verification to **fail fast** if services aren't ready:

```bash
# Verify Code Editor service status
if systemctl is-active --quiet "code-editor@$CODE_EDITOR_USER"; then
    log "✅ Code Editor service is active"
else
    error "Code Editor service is not running"
fi

# Verify nginx proxy chain (port 80 → 8080)
NGINX_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/)
if [ "$NGINX_CODE" = "302" ] || [ "$NGINX_CODE" = "200" ]; then
    log "✅ Nginx proxy verified"
else
    error "Nginx proxy failing - Code Editor not accessible via CloudFront"
fi
```

### 3. **Health Check Script** (`verify-code-editor-health.sh`)

New diagnostic script for troubleshooting (available system-wide):

```bash
# Run from anywhere (installed to /usr/local/bin/)
verify-code-editor-health.sh

# Or from the repository
/workshop/sample-dat406-build-agentic-ai-powered-search-apg/deployment/verify-code-editor-health.sh
```

Checks:
- ✅ Code Editor systemd service status
- ✅ Nginx service status
- ✅ Code Editor direct access (port 8080)
- ✅ Nginx proxy (port 80)
- ✅ Token file existence
- ✅ Listening ports

## 📊 Deployment Flow (Fixed)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CloudFormation creates EC2 instance                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SSM Document sends bootstrap command                     │
│    (RunCodeEditorSSMDoc completes immediately)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Bootstrap script runs (5-10 minutes)                     │
│    - Install Python 3.13, Node.js, PostgreSQL client        │
│    - Install Code Editor + VS Code extensions               │
│    - Configure nginx proxy                                  │
│    - Start services                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. WaitForCodeEditor Lambda polls origin                    │
│    - Attempts: 60 × 15s = 15 minutes max                    │
│    - Waits for HTTP 200/302 from nginx                      │
│    - Adds 10s stability buffer                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (ONLY AFTER VERIFIED READY)
┌─────────────────────────────────────────────────────────────┐
│ 5. CloudFront distribution created                          │
│    - Origin: EC2 public DNS                                 │
│    - First request succeeds (no "Forbidden")                │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Troubleshooting

### If CloudFront still shows "Forbidden":

1. **Check CloudFormation Events:**
   ```
   Look for "WaitForCodeEditor" resource status
   ```

2. **SSH to EC2 and run health check:**
   ```bash
   verify-code-editor-health.sh
   ```

3. **Check bootstrap logs:**
   ```bash
   # SSM execution logs
   sudo journalctl -u amazon-ssm-agent -n 100
   
   # Code Editor service logs
   sudo journalctl -u code-editor@participant -n 100
   
   # Nginx logs
   sudo tail -f /var/log/nginx/error.log
   ```

4. **Test locally before CloudFront:**
   ```bash
   curl -I http://localhost:80/
   # Should return: HTTP/1.1 302 Found
   ```

5. **Restart services if needed:**
   ```bash
   sudo systemctl restart code-editor@participant
   sudo systemctl restart nginx
   ```

6. **Invalidate CloudFront cache:**
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id <DISTRIBUTION_ID> \
     --paths "/*"
   ```

## 📝 Files Modified

1. ✅ `deployment/cfn/dat406-code-editor.yml` - Added WaitForCodeEditor Lambda
2. ✅ `deployment/bootstrap-code-editor-dat406.sh` - Enhanced verification
3. ✅ `deployment/verify-code-editor-health.sh` - New health check script

## 🎯 Expected Behavior After Fix

- CloudFormation stack creation takes **15-20 minutes** (includes wait time)
- CloudFront URL works **immediately** after stack completes
- No "Forbidden" errors on first access
- Bootstrap failures cause CloudFormation to fail (not silent failures)

## 📊 Timing Breakdown

| Phase | Duration | Status Check |
|-------|----------|--------------|
| EC2 Launch | 2-3 min | Instance running |
| Bootstrap Script | 5-10 min | Services installing |
| Wait Lambda | 0-15 min | Polling origin |
| CloudFront Creation | 5-10 min | Distribution deploying |
| **Total** | **12-28 min** | Stack complete |

The wait lambda typically completes in **5-8 minutes** (not the full 15 min timeout).
