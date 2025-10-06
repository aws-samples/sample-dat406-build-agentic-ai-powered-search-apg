# Bootstrap Script Versions

## Files

### `bootstrap-environment.sh` (MAIN - Manual Installation)
**Current production version** - Uses manual Code Editor installation to avoid token conflicts.

**Method**: Downloads Code Editor tarball directly and extracts manually, then creates custom systemd service with our token.

**Advantages**:
- Full control over token from the start
- No race conditions with installer's default service
- Eliminates HTTP 403 token mismatch errors

**Use this for**: All deployments

---

### `bootstrap-environment-automatic.sh` (BACKUP - Automatic Installer)
**Backup version** - Uses AWS Code Editor installer script (original approach).

**Method**: Runs `install.sh` from AWS, stops the installer's default service, creates our own service.

**Issues**:
- Installer creates default service with random token
- Race condition: Code Editor may cache wrong token
- Requires stopping/disabling installer's service
- Can cause HTTP 403 errors

**Use this for**: Reference only, not recommended for production

---

## History

**Problem**: Code Editor installer automatically creates a systemd service with a random token. Even when we stop that service and create our own with the correct token, Code Editor sometimes caches the wrong token, causing HTTP 403 errors.

**Solution**: Skip the installer entirely. Download and extract Code Editor manually, then create our systemd service with the correct token from the start. This eliminates the race condition.

---

## Testing

To test the manual installation locally:
```bash
export CODE_EDITOR_PASSWORD="testPassword123"
export CODE_EDITOR_USER="participant"
export HOME_FOLDER="/workshop"
export CFN_WAIT_HANDLE=""
export STAGE2_SCRIPT_URL=""

sudo bash deployment/bootstrap-environment.sh
```

To verify Code Editor is working:
```bash
curl -I http://localhost:8080/
systemctl status code-editor@participant
```
