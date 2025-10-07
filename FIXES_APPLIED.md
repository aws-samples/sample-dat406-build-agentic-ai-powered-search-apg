# Fixes Applied - Search & Autocomplete Issues

## Problem
- Search returned 0 results
- Autocomplete returned 422 errors through CloudFront
- Frontend had wrong API URL (localhost instead of CloudFront)

## Root Cause
**min_similarity threshold was too high (0.5)** - embeddings weren't matching with that threshold.

## Fixes Applied

### 1. Backend - Lower Default Similarity Threshold
**File**: `lab2/backend/models/search.py`
- Changed `min_similarity` default from `0.5` to `0.0`
- This allows all results to be returned, sorted by similarity

### 2. Frontend - Explicit Similarity Parameter
**File**: `lab2/frontend/src/components/SearchOverlay.tsx`
- Added `min_similarity: 0.0` to search requests
- Ensures frontend explicitly requests lower threshold

**File**: `lab2/frontend/src/services/types.ts`
- Added `min_similarity?: number` to `SearchQuery` interface

### 3. CloudFront URL Detection
**File**: `lab2/frontend/fix-cloudfront.sh`
- Removed hardcoded CloudFront URL
- Now fails with clear error if CloudFront URL not found
- Detects from EC2 tags or .env file

**File**: `lab2/UPDATE_FRONTEND.sh` (NEW)
- Simpler script for participants to update frontend
- Detects CloudFront URL from EC2 tags
- Rebuilds and restarts frontend automatically

### 4. Bootstrap Script
**File**: `deployment/bootstrap-labs.sh`
- Already properly detects CloudFront URL from EC2 tags
- Sets correct API URL in frontend .env during deployment
- No changes needed

## Testing

### Verify the fix works:
```bash
# Test with min_similarity=0.0 (should return results)
curl -s -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"headphones","limit":5,"min_similarity":0.0}' | jq '.total_results'
# Expected: 5

# Test autocomplete
curl -s "http://localhost:8000/api/autocomplete?q=headp" | jq '.suggestions | length'
# Expected: 5
```

## Participant Instructions

### For Current Deployment (EC2 instance):
```bash
# 1. Restart backend (picks up new default)
cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2/backend
pkill -f uvicorn
start-backend

# 2. Update and rebuild frontend
cd /workshop/sample-dat406-build-agentic-ai-powered-search-apg/lab2
./UPDATE_FRONTEND.sh

# 3. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)
```

### For Future Deployments:
No action needed - bootstrap script will set correct values automatically.

## Files Changed

1. `lab2/backend/models/search.py` - Default min_similarity: 0.5 → 0.0
2. `lab2/frontend/src/components/SearchOverlay.tsx` - Added min_similarity: 0.0
3. `lab2/frontend/src/services/types.ts` - Added min_similarity to interface
4. `lab2/frontend/fix-cloudfront.sh` - Removed hardcoded URL
5. `lab2/UPDATE_FRONTEND.sh` - NEW: Simple update script for participants

## Why This Works

The Titan v2 embeddings generate similarity scores that are typically lower than 0.5 for general product searches. By setting min_similarity to 0.0:
- All results are returned (sorted by similarity)
- Users see the most relevant products first
- No artificial filtering that removes valid results

The similarity scores are still displayed in the UI (as percentage badges), so users can see relevance.
