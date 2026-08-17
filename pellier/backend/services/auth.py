"""AgentCore Identity — Cognito user extraction, optional and required.

Route dependencies use ``get_current_user()``, which delegates to the
cookie-aware ``CognitoAuthService`` so code-flow httpOnly cookies and
legacy ``Authorization: Bearer`` headers share one validation path.

Two dependencies, and the difference is a security boundary:

  * :func:`get_current_user` is **optional**. It returns ``None`` for an
    anonymous shopper so read paths and the demo storefront work without
    a login. Read paths only.
  * :func:`require_operator` is **required**. Every mutation and operator
    route must depend on it. It rejects anonymous callers, rejects a
    presented-but-invalid token with a *different* status than a missing
    one, and guarantees a non-empty ``sub`` claim so the audit row can
    name a real principal.

Why the split matters: the optional dependency returns ``None`` both when
no credentials were supplied and when supplied credentials failed to
verify. A mutation handler that accepts the optional dependency and does
not reject ``None`` is therefore an unauthenticated write path that reads
as an authenticated one.
"""
import logging
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency: extract and verify the optional Cognito user.

    Returns None for anonymous users (demo mode).
    Returns {sub, username, email, given_name, access_token} for authenticated users.
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
    payload = {
        "sub": user.user_id,
        "email": user.email or "anonymous",
        "given_name": user.given_name,
        "access_token": user.access_token,
    }
    username = getattr(user, "username", None)
    if username:
        payload["username"] = username
    return payload


async def require_operator(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: require a verified operator identity.

    Use this on every mutation and operator route. Unlike
    :func:`get_current_user`, it never returns ``None`` — the handler is
    guaranteed a principal it can write into the audit record.

    Args:
        request: The inbound request, carrying either an
            ``Authorization: Bearer`` header or an ``access_token`` cookie.

    Returns:
        ``{sub, username, email, given_name, access_token}`` for the verified caller.
        ``sub`` is guaranteed non-empty.

    Raises:
        HTTPException: ``401 authentication_required`` when no credentials
            were supplied at all; ``401 invalid_credentials`` when a token
            was presented but did not verify. The two are deliberately
            distinct: the first is an unauthenticated client, the second is
            a rejected one, and collapsing them hides token expiry and
            misconfiguration behind "please log in". Neither is a Cedar
            DENY — that distinction is load-bearing in this workshop.
    """
    from services.cognito_auth import get_cognito_auth_service

    service = get_cognito_auth_service()
    if not _has_presented_credentials(request):
        raise HTTPException(status_code=401, detail="authentication_required")

    try:
        user = await service.extract_user(request)
    except Exception as exc:
        logger.warning("Operator token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="invalid_credentials") from exc

    if user is None:
        # Credentials were presented (checked above) but did not verify.
        raise HTTPException(status_code=401, detail="invalid_credentials")

    subject = (user.user_id or "").strip()
    if not subject:
        # A token that verifies but carries no subject cannot be audited.
        raise HTTPException(status_code=401, detail="invalid_credentials")

    payload = {
        "sub": subject,
        "email": user.email or "anonymous",
        "given_name": user.given_name,
        "access_token": user.access_token,
    }
    username = getattr(user, "username", None)
    if username:
        payload["username"] = username
    return payload


def _has_presented_credentials(request: Request) -> bool:
    """Return True when the caller supplied a bearer token or auth cookie."""
    from services.cognito_auth import ACCESS_TOKEN_COOKIE

    authorization = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if authorization and authorization.lower().startswith("bearer "):
        return bool(authorization.split(" ", 1)[1].strip())
    return bool(request.cookies.get(ACCESS_TOKEN_COOKIE))
