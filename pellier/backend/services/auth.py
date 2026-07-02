"""AgentCore Identity — optional Cognito user extraction.

Route dependencies use ``get_current_user()``, which delegates to the
cookie-aware ``CognitoAuthService`` so code-flow httpOnly cookies and
legacy ``Authorization: Bearer`` headers share one validation path.
"""
import logging
from typing import Optional, Dict, Any

from fastapi import Request

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency: extract and verify the optional Cognito user.

    Returns None for anonymous users (demo mode).
    Returns {sub, email, given_name, access_token} for authenticated users.
    """
    try:
        from services.cognito_auth import get_cognito_auth_service

        user = await get_cognito_auth_service().extract_user(request)
    except Exception as exc:
        logger.debug("Optional Cognito user extraction failed: %s", exc)
        return None

    if user is None:
        return None

    # Include the raw token so chat can pass the caller's identity through to
    # AgentCore Gateway/Runtime. This dict remains server-side.
    return {
        "sub": user.user_id,
        "email": user.email or "anonymous",
        "given_name": user.given_name,
        "access_token": user.access_token,
    }
