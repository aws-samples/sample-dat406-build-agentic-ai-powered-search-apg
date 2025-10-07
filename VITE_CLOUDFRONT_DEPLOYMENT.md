# Vite Frontend Deployment Guide for AWS Workshop Studio

## Problem Summary
When deploying Vite applications through AWS Workshop Studio with CloudFront + VSCode Server proxy, the default Vite configuration doesn't work because:
1. CloudFront serves at `/ports/5173/` path
2. VSCode Server proxies requests and strips the path prefix
3. Vite's default config uses absolute paths starting with `/`

## Solution: Production Build Configuration

### Configuration Applied

**File:** `lab2/frontend/vite.config.ts`

The configuration now uses:
```typescript
base: process.env.NODE_ENV === 'production' ? '/ports/5173/' : '/'
```

This ensures:
- **Production builds** prefix all assets with `/ports/5173/`
- **Dev mode** uses `/` for local development

### Deployment Process

```bash
cd lab2/frontend

# Build for production
npm run build

# Serve the build
npx http-server dist -p 5173 --cors
```

### Access URLs

- **CloudFront URL:** `https://{cloudfront-domain}/ports/5173/`
- **Direct (for testing):** `http://localhost:5173/`

## Asset Import Best Practices

### ❌ WRONG - Absolute paths don't work:
```typescript
<img src="/logo.png" alt="Logo" />
<img src="/images/header.jpg" alt="Header" />
```

### ✅ CORRECT - Use relative imports:
```typescript
import logo from './logo.png'
import headerImg from '../assets/header.jpg'

<img src={logo} alt="Logo" />
<img src={headerImg} alt="Header" />
```

## Troubleshooting

### Issue: Assets return 404
**Cause:** Using absolute paths instead of imports  
**Fix:** Change to relative imports

### Issue: Blank page after deployment
**Cause:** Incorrect base path  
**Fix:** Verify `base` in vite.config.ts matches CloudFront path

### Issue: API calls fail
**Cause:** Incorrect API base URL  
**Fix:** Update API base URL to include CloudFront domain and port

## Summary

**Key Changes Made:**
1. ✅ `vite.config.ts` - Added conditional `base` path for production
2. ✅ Removed `allowedHosts` (doesn't exist in Vite 5)
3. ✅ Simplified server config for reliability

**Deployment Checklist:**
- Build with `npm run build`
- Serve with `npx http-server dist -p 5173 --cors`
- Access via CloudFront `/ports/5173/` path
