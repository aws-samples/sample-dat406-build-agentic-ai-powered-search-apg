"""Ownership checks for anonymous and authenticated storefront sessions."""

from __future__ import annotations

import hashlib
from typing import Any, Dict


def session_actor_id(
    user: Dict[str, Any] | None,
    session_token: str | None,
) -> str:
    """Return the owner key after validating an anonymous session token."""
    if user and user.get("sub"):
        return str(user["sub"])
    token = (session_token or "").strip()
    if len(token) < 32 or len(token) > 256:
        raise ValueError("A valid session ownership token is required")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"anonymous:{digest}"
