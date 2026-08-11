"""FastAPI routers for the Pellier backend.

Routers live here so ``app.py`` only wires them up with ``include_router``
rather than declaring every endpoint inline.

  * ``auth`` — ``/api/auth/*`` Cognito Hosted UI sign-in loop.
  * ``user`` — ``/api/user/preferences`` GET/POST protected by Cognito JWT.
  * ``agent`` — ``/api/agent/chat`` SSE stream + session history.
  * ``products`` — editorial and personalized product and inventory APIs.
  * ``search`` — boutique vector search.
  * ``workshop`` — Agent Trace query and resume telemetry APIs.
  * ``boutique`` — storefront briefing and pulse APIs.
"""

from __future__ import annotations

from .agent import router as agent_router
from .auth import router as auth_router
from .products import router as products_router
from .search import router as search_router
from .boutique import router as boutique_router
from .user import router as user_router
from .workshop import router as workshop_router
from .agent_trace import router as agent_trace_router

__all__ = [
    "agent_router",
    "agent_trace_router",
    "auth_router",
    "products_router",
    "search_router",
    "boutique_router",
    "user_router",
    "workshop_router",
]
