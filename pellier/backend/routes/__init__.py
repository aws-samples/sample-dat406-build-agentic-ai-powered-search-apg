"""FastAPI routers for the Pellier backend.

Routers live here so ``app.py`` only wires them up with ``include_router``
rather than declaring every endpoint inline.

  * ``auth``     (Task 3.3) — ``/api/auth/*`` Cognito Hosted UI sign-in loop.
  * ``user``     (Task 3.4) — ``/api/user/preferences`` GET/POST protected by
                              the Cognito JWT middleware.
  * ``agent``    (Task 3.5) — ``/api/agent/chat`` SSE stream + session history.
  * ``products`` (Task 3.6) — ``/api/products`` editorial + personalized list,
                              ``/api/products/{id}``, ``/api/inventory``.
  * ``search``   (Task 3.7) — ``POST /api/search`` pellier vector search
                              wrapping the vector-search ``vector_search`` method.
  * ``workshop``  (Week 1)   — ``POST /api/agent-trace/query`` + ``/api/agent-trace/resume``
                               flat replay payloads for Pellier Labs telemetry surface.
  * ``pellier`` (pre-W3)    — ``GET /api/storefront/briefing`` + ``/pulse``
                               for the homepage ambient agent chrome.
"""

from __future__ import annotations

from .agent import router as agent_router
from .auth import router as auth_router
from .products import router as products_router
from .search import router as search_router
from .pellier import router as pellier_router
from .user import router as user_router
from .workshop import router as workshop_router
from .agent_trace import router as agent_trace_router

__all__ = [
    "agent_router",
    "agent_trace_router",
    "auth_router",
    "products_router",
    "search_router",
    "pellier_router",
    "user_router",
    "workshop_router",
]
