"""
Pellier - Main FastAPI Application
FastAPI app for the Pellier workshop backend.
"""

import asyncio
import os
import re
import time
import logging
import json
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from pellier_copy import MEMORY_WRITE_WARNING
from models.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    HealthResponse,
    ChatRequest,
    ChatResponse,
    PerfCompareRequest,
    PerfIterativeScanRequest,
    PerfQuantizationRequest,
    RestockRequest,
)
from models.product import ProductWithScore
from services.database import DatabaseService
from services.auth import get_current_user, require_operator
from services.embeddings import EmbeddingService
from services.chat import ChatService
from services.chat_error_taxonomy import classify_chat_error
from datetime import datetime
from services.sql_query_logger import init_query_logger, get_query_logger, QueryLog
from services.index_performance import get_index_performance_service
from services.vector_search import VectorSearch
from services.cache import init_cache, get_cache
from routes import (
    agent_router,
    observatory_router,
    auth_router,
    products_router,
    search_router,
    storefront_router,
    commerce_router,
    user_router,
    workshop_router,
    operator_router,
)
from routes.transcribe import (
    TRANSCRIBE_REGION,
    router as transcribe_router,
    transcribe_runtime_status,
)

# Configure logging for Strands SDK
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

# Filter out malicious bot requests from logs
class SecurityScanFilter(logging.Filter):
    """Filter out automated security scanner requests"""
    MALICIOUS_PATTERNS = [
        'phpunit', '.env', 'eval-stdin', 'wp-admin', 'wp-login',
        '.git', 'config.php', 'shell', 'cmd', 'exec'
    ]
    
    def filter(self, record):
        message = record.getMessage().lower()
        return not any(pattern in message for pattern in self.MALICIOUS_PATTERNS)

# Apply filter to uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(SecurityScanFilter())

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.INFO)

# Configure app logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Global service instances
db_service: DatabaseService = None
embedding_service: EmbeddingService = None
chat_service: ChatService = None
query_logger = None
index_performance_service = None


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


SMOKE_THINKING_DELAY_SECONDS = max(
    0.0,
    _float_env("PELLIER_SMOKE_THINKING_DELAY_SECONDS", 0.35),
)
SMOKE_CHUNK_DELAY_SECONDS = max(
    0.0,
    _float_env("PELLIER_SMOKE_CHUNK_DELAY_SECONDS", 0.045),
)


def _editorial_stream_chunks(content: str, target_words: int = 3) -> List[str]:
    """Split controlled smoke copy into exact, readable streaming phrases."""
    words = re.findall(r"\S+\s*", content)
    chunks: List[str] = []
    phrase: List[str] = []

    for word in words:
        phrase.append(word)
        punctuation_break = word.rstrip().endswith((",", ".", ";", ":", "?", "!"))
        if len(phrase) >= target_words or (len(phrase) >= 2 and punctuation_break):
            chunks.append("".join(phrase))
            phrase = []

    if phrase:
        chunks.append("".join(phrase))

    return chunks


SEARCH_STRATEGY_COST_PER_1000_USD = {
    "vector": _float_env("PELLIER_COST_VECTOR_PER_1000_USD", 0.18),
    "hybrid": _float_env("PELLIER_COST_HYBRID_PER_1000_USD", 0.18),
    "rerank": _float_env("PELLIER_COST_RERANK_PER_1000_USD", 1.18),
    "agentic": _float_env("PELLIER_COST_AGENTIC_PER_1000_USD", 8.18),
}


def _log_agent_and_tool_inventory() -> None:
    """Log the live specialist roster and tool catalogue at boot.

    Mirrors the ``✅ Loaded N skills...`` line emitted by ``skills.loader``
    so the operator can confirm at a glance:

      * which specialists the Dispatcher (Pattern III) and Orchestrator
        (Pattern I) can route to, and
      * which @tool functions those specialists are allowed to call.

    Runs once per process at lifespan startup. The lists are short and
    lookup-only, so importing the modules here is cheap.
    """
    # Specialists. Each file exports a build_<role>_agent() factory; the
    # public role is the @tool wrapper name the orchestrator sees.
    specialists = [
        ("search_agent", "search"),
        ("personalization_agent", "recommendation"),
        ("pricing_agent", "pricing"),
        ("inventory_agent", "inventory"),
        ("customer_service_agent", "support"),
    ]
    specialist_summary = ", ".join(f"{role}→{name}" for name, role in specialists)
    logger.info(
        "✅ Loaded %d specialist agents: %s",
        len(specialists),
        specialist_summary,
    )

    # Tools. Walk services.agent_tools and collect every Strands @tool
    # so the count stays honest if a tool is added or removed.
    try:
        import services.agent_tools as agent_tools

        tool_names = sorted(
            name
            for name in dir(agent_tools)
            if getattr(agent_tools, name).__class__.__name__ == "DecoratedFunctionTool"
        )
        logger.info(
            "✅ Loaded %d agent tools: %s",
            len(tool_names),
            ", ".join(tool_names),
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Could not enumerate agent tools: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Pellier API...")

    # The governed lineage's write boundary is a CONFIG switch, and it fails open.
    # `services.execution_rail.requires_managed_rail` returns False for any format
    # other than `governed`, so with the flag unset every mutation-capable tool
    # becomes servable in process: no review, no Cedar verdict, no `tool_audit` row.
    #
    # `bootstrap-labs.sh` writes this into `.env` from the environment and defaults to
    # `builders`, which is right for the shorter lineage and silently wrong here. A
    # local `.env` created without the export left this box serving governed writes
    # straight from the shopper rail, and nothing said so until a return appeared in
    # Aurora. Say it loudly at startup instead.
    _format = str(getattr(settings, "WORKSHOP_FORMAT", "") or "").lower()
    if _format == "governed":
        logger.info("✅ WORKSHOP_FORMAT=governed — governed writes are managed-rail only")
    else:
        logger.warning(
            "⚠️ WORKSHOP_FORMAT=%r, not 'governed'. The managed-rail boundary is OFF: "
            "initiate_return, issue_credit and restock_inventory will execute "
            "in process with no human review, no AgentCore Policy verdict and no "
            "tool_audit receipt. Set WORKSHOP_FORMAT=governed for this lineage.",
            _format or "<unset>",
        )
    
    global db_service, embedding_service, chat_service, query_logger, index_performance_service

    if settings.PELLIER_SMOKE_MODE:
        logger.info(
            "PELLIER_SMOKE_MODE enabled — skipping Aurora, Bedrock, "
            "Strands, and AgentCore service initialization"
        )
        yield
        logger.info("Shutting down Pellier API smoke process...")
        logger.info("👋 Goodbye!")
        return
    
    try:
        # Initialize Strands OpenTelemetry tracing
        try:
            from strands.telemetry import StrandsTelemetry
            import sys

            # MUST run before StrandsTelemetry(): strands.telemetry.Tracer
            # reads OTEL_SEMCONV_STABILITY_OPT_IN once, in __init__. Setting
            # it afterwards leaves the tracer built with redaction off and
            # the setting silently does nothing.
            from services.otel_content_redaction import apply_model_content_redaction

            apply_model_content_redaction(
                enabled=settings.OTEL_REDACT_MODEL_CONTENT
            )

            strands_telemetry = StrandsTelemetry()
            
            # Custom formatter for cleaner trace output
            def format_trace(span):
                attrs = span.attributes or {}
                name = span.name
                duration_ms = (span.end_time - span.start_time) / 1_000_000  # ns to ms
                
                # Extract key metrics
                agent_name = attrs.get('gen_ai.agent.name', '')
                total_tokens = attrs.get('gen_ai.usage.total_tokens', 0)
                prompt_tokens = attrs.get('gen_ai.usage.prompt_tokens', 0)
                completion_tokens = attrs.get('gen_ai.usage.completion_tokens', 0)
                
                # Format based on span type
                if 'invoke_agent' in name:
                    return f"✨ Agent: {agent_name} | {duration_ms:.0f}ms | Tokens: {total_tokens} ({prompt_tokens} in + {completion_tokens} out)\n"
                elif 'chat' in name and total_tokens > 0:
                    return f"  🤖 LLM Call | {duration_ms:.0f}ms | Tokens: {total_tokens}\n"
                elif 'execute_event_loop_cycle' in name:
                    cycle_id = attrs.get('event_loop.cycle_id', '')[:8]
                    return f"  🔄 Cycle {cycle_id} | {duration_ms:.0f}ms\n"
                else:
                    return f"  • {name} | {duration_ms:.0f}ms\n"
            
            strands_telemetry.setup_console_exporter(
                out=sys.stdout,
                formatter=format_trace
            )

            logger.info("✅ Strands OpenTelemetry tracing enabled (compact format)")

            # Export traces to CloudWatch X-Ray via OTLP (requires OTEL_EXPORTER_OTLP_ENDPOINT)
            try:
                import os
                if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
                    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", settings.OTEL_EXPORTER_OTLP_ENDPOINT)
                    os.environ.setdefault("OTEL_SERVICE_NAME", "pellier")
                    os.environ.setdefault("OTEL_RESOURCE_ATTRIBUTES", "service.namespace=pellier,deployment.environment=workshop")
                    strands_telemetry.setup_otlp_exporter()
                    logger.info("✅ OTLP exporter enabled — traces → CloudWatch X-Ray")
                else:
                    logger.info("ℹ️  OTLP exporter skipped (set OTEL_EXPORTER_OTLP_ENDPOINT to enable)")
            except Exception as e:
                logger.warning(f"⚠️ OTLP exporter not available: {e}")

            # Collectorless span export to the CloudWatch X-Ray OTLP
            # endpoint. Separate from setup_otlp_exporter() above: that one
            # posts unsigned OTLP, and the X-Ray endpoint accepts SigV4 only.
            # Attached after StrandsTelemetry so there is an SDK provider to
            # add a processor to.
            try:
                from services.otel_cloudwatch_export import init_cloudwatch_span_export

                span_export = init_cloudwatch_span_export(
                    enabled=settings.OTEL_CLOUDWATCH_TRACES_ENABLED,
                    region=settings.AWS_REGION,
                    endpoint=settings.OTEL_CLOUDWATCH_TRACES_ENDPOINT,
                )
                if not span_export.attached:
                    logger.info(
                        "ℹ️  CloudWatch span export unavailable — %s",
                        span_export.reason,
                    )
            except Exception as e:
                logger.warning(f"⚠️ CloudWatch span export not initialized: {e}")

            # Attach in-memory span capture for trace extraction
            try:
                from services.otel_trace_extractor import init_span_capture
                init_span_capture()
            except Exception as e:
                logger.warning(f"⚠️ Failed to init span capture: {e}")

        except ImportError:
            logger.warning("⚠️ Strands OpenTelemetry not available - install with: pip install 'strands-agents[otel]'")
        except Exception as e:
            logger.warning(f"⚠️ Failed to setup OpenTelemetry: {e}")
        
        # Initialize core services
        db_service = DatabaseService()
        await db_service.connect()
        logger.info("✅ Database service initialized")
        
        embedding_service = EmbeddingService()
        logger.info("✅ Embedding service initialized (Cohere Embed v4)")

        # Initialize Valkey cache (graceful fallback to in-memory)
        cache_svc = init_cache(
            valkey_url=settings.VALKEY_URL,
            default_ttl=settings.CACHE_TTL,
        )
        logger.info(f"✅ Cache service initialized (mode={cache_svc.mode})")
        
        chat_service = ChatService(db_service=db_service)
        logger.info("✅ Chat service initialized")

        # Initialize SQL query logger
        query_logger = init_query_logger(max_logs=100)
        logger.info("✅ SQL query logger initialized")

        # Initialize index performance service
        conn_string = f"host={settings.DB_HOST} port={settings.DB_PORT} dbname={settings.DB_NAME} user={settings.DB_USER} password={settings.DB_PASSWORD}"
        index_performance_service = get_index_performance_service(conn_string)
        logger.info("✅ Index performance service initialized")

        # Set chat service logger to INFO
        logging.getLogger('services.chat').setLevel(logging.INFO)

        # Initialize agent tools. Retrieval tools cover vector, hybrid,
        # rerank-backed reads, and the governed write-path tools.
        from services.agent_tools import set_db_service, set_main_loop
        set_db_service(db_service)
        # Capture the running lifespan loop (get_running_loop is the correct,
        # non-deprecated call here — we are inside the async startup hook).
        set_main_loop(asyncio.get_running_loop())
        logger.info("✅ Agent tools initialized for retrieval, inventory, and write-path actions")

        # Wire the tool_audit writer the same way. Theo's anchor
        # capability persists every mutation to Aurora's pellier.tool_audit
        # table; the writer is fire-and-forget but needs the same
        # DB pool + main event loop reference to bridge sync→async.
        from services import tool_audit_writer
        tool_audit_writer.set_db_service(db_service)
        tool_audit_writer.set_main_loop(asyncio.get_running_loop())
        logger.info("✅ tool_audit writer initialized for ALLOW-path mutation logging")

        # The operator review writer needs the same bridge. When a governed
        # mutation declines to run on the shopper rail, the after-tool hook turns
        # that refusal into a durable review row, and it fires on a Strands
        # worker thread rather than the request loop.
        from services import operator_review
        operator_review.set_db_service(db_service)
        operator_review.set_main_loop(asyncio.get_running_loop())
        logger.info("✅ operator review writer initialized for the action boundary")

        # Load the skill registry once at boot. Per-request cost is zero —
        # skills are served from memory. See backend/skills/ for the
        # registry, models, and one-call router.
        from skills import load_registry
        load_registry()

        # Inventory the specialists + tools so the operator can confirm at
        # a glance what the process can actually route to. Keeps parity
        # with the skills loader's "✅ Loaded N skills..." line.
        _log_agent_and_tool_inventory()

        voice_status = transcribe_runtime_status()
        if voice_status["sdk_available"]:
            logger.info(
                "✅ Voice WebSocket mounted at /ws/transcribe (Amazon Transcribe Streaming, region=%s, python=%s)",
                TRANSCRIBE_REGION,
                voice_status["python"],
            )
        else:
            logger.warning(
                "⚠️ Voice WebSocket mounted at /ws/transcribe but amazon-transcribe is not installed for python=%s",
                voice_status["python"],
            )

        logger.info("🚀 Pellier API is ready!")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Pellier API...")
    
    if db_service:
        await db_service.disconnect()
    
    logger.info("👋 Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="Pellier API",
    description="Governed agentic AI search with Aurora and Bedrock AgentCore",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Storefront auth routes (Task 3.3) — Cognito sign-in loop + session
# cookie management. Mounted at /api/auth/* by the router's own prefix.
app.include_router(auth_router)

# Storefront user routes (Task 3.4) — preference persistence via
# AgentCore Memory. Mounted at /api/user/* by the router's own prefix.
app.include_router(user_router)

# Storefront agent routes (Task 3.5) — SSE chat stream + session
# history. Mounted at /api/agent/* by the router's own prefix. JWT is
# validated exactly once at stream start; mid-stream token expiry does
# not abort the response (Design Error Handling row + Sequence #2).
app.include_router(agent_router)

# Storefront product + inventory routes (Task 3.6) — editorial and
# personalized product listings, single-product lookup, and the live
# inventory signal for the status strip. The routers are AUTHORITATIVE
# for /api/products, /api/products/{id}, /api/inventory, and /api/search —
# the legacy @app.get/@app.post handlers for those paths were removed and
# should NOT be re-added here, not even for "safety." Add new endpoints to
# routes/products.py and routes/search.py instead.
app.include_router(products_router)
app.include_router(search_router)

# Workshop telemetry surface — returns flat
# {session_id, events: list[dict]} payloads for the panel renderer.
# Intentionally separate from /api/agent/chat so the Pellier SSE
# stream isn't reshaped for the workshop's replay needs.
app.include_router(workshop_router)

# Pellier Observatory read-only API endpoints — sessions, agents, tools,
# routing, memory, performance, evaluations, observatory dashboard.
# Additive to workshop_router (same /api/observatory/ prefix, no path conflicts).
app.include_router(observatory_router)

# Pellier ambient chrome — briefing (concierge empty state) + pulse
# (4 live metrics above the hero). Both endpoints are contract-typed
# via Pydantic and degrade gracefully; they are never allowed to 5xx
# the homepage.
app.include_router(storefront_router)
app.include_router(operator_router)
app.include_router(commerce_router)
app.include_router(transcribe_router)


# Dependency injection
async def get_db_service() -> DatabaseService:
    """Get database service instance"""
    if not db_service:
        raise HTTPException(
            status_code=503, 
            detail="Database unavailable - check network connectivity to Aurora cluster"
        )
    return db_service


async def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    if not embedding_service:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    return embedding_service


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

# Root + SPA serving ------------------------------------------------------
# The workshop runs in "production build" mode: FastAPI owns port 8000
# and serves the built React SPA from ``../frontend/dist``. No separate
# Vite dev server on attendee laptops — kills the "npm run dev on
# Windows" failure modes (port 5173 conflicts, file watcher limits,
# node_modules install issues behind corporate proxies).
#
# Resolution order for ``FRONTEND_DIST``:
#   1. If ``FRONTEND_DIST_PATH`` env var is set, use that.
#   2. Otherwise look for ``../frontend/dist`` relative to backend/.
#   3. If neither exists (pure API mode / tests), fall back to the
#      JSON status blob from the root handler.
#
# ``SPA_MOUNT_PATH`` controls the URL prefix the SPA is served from.
# Default ``/`` matches the historical behavior — nginx in this repo
# rewrites ``/app/`` → ``/`` before forwarding (see
# scripts/bootstrap-environment.sh:173-182), so root mount works behind
# both ``/ports/8000/*`` and ``/app/*`` proxies. Set to ``/app`` if a
# downstream proxy ever forwards the prefix verbatim instead of
# stripping it.
FRONTEND_DIST = Path(
    os.environ.get("FRONTEND_DIST_PATH")
    or (Path(__file__).resolve().parent.parent / "frontend" / "dist")
).resolve()

SPA_MOUNT_PATH = (os.environ.get("SPA_MOUNT_PATH", "/").rstrip("/") or "/")
SPA_STATIC_FILES = {
    path.relative_to(FRONTEND_DIST).as_posix(): path
    for path in FRONTEND_DIST.rglob("*")
    if path.is_file() and path.name != "index.html"
}


async def _serve_spa_root():
    """Serve the SPA's ``index.html`` if built, else return API status."""
    index_html = FRONTEND_DIST / "index.html"
    if index_html.is_file():
        return FileResponse(
            index_html,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return JSONResponse(
        {
            "message": "Pellier API",
            "version": "1.0.0",
            "note": (
                "Frontend bundle not found at "
                f"{FRONTEND_DIST}. Run `npm run build` in pellier/frontend/ "
                "to produce the SPA, or set FRONTEND_DIST_PATH."
            ),
        }
    )


# Mount path semantics:
#   - SPA_MOUNT_PATH = "/"   → serve SPA at ``/`` (legacy default).
#   - SPA_MOUNT_PATH = "/app" → serve SPA at ``/app/`` and 307-redirect
#     bare ``/app`` to ``/app/``. Trailing slash matters because the
#     bundle uses relative asset URLs ("assets/foo.js"); without the
#     slash, the browser resolves them against ``/`` and 404s.
if SPA_MOUNT_PATH == "/":
    app.add_api_route(
        "/",
        _serve_spa_root,
        methods=["GET"],
        include_in_schema=False,
    )
else:
    _slash_target = SPA_MOUNT_PATH + "/"

    async def _spa_redirect_to_slash():
        return RedirectResponse(url=_slash_target, status_code=307)

    app.add_api_route(
        SPA_MOUNT_PATH,
        _spa_redirect_to_slash,
        methods=["GET"],
        include_in_schema=False,
    )
    app.add_api_route(
        _slash_target,
        _serve_spa_root,
        methods=["GET"],
        include_in_schema=False,
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns status of all services
    """
    if settings.PELLIER_SMOKE_MODE:
        return HealthResponse(
            status="healthy",
            database="smoke",
            bedrock="smoke",
            custom_tools="available",
            version="1.0.0",
        )

    if not db_service:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable - check network connectivity to Aurora cluster",
        )

    health_status = {
        "status": "healthy",
        "database": "unknown",
        "bedrock": "unknown",
        "custom_tools": "available",
        "version": "1.0.0",
    }

    # Check database connection
    try:
        await db_service.execute_query("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Check Bedrock access
    try:
        embedding_service.generate_embedding("test")
        health_status["bedrock"] = "accessible"
    except Exception as e:
        logger.error(f"Bedrock health check failed: {e}")
        health_status["bedrock"] = "inaccessible"
        health_status["status"] = "degraded"

    return HealthResponse(**health_status)


# ============================================================================
# LAB 1: SEMANTIC SEARCH ENDPOINTS
# ============================================================================
#
# POST /api/search is authoritative on routes/search.py (StorefrontSearchResponse
# wire shape). The legacy semantic_search handler that used to live here has
# been removed — don't re-add it; the router owns that path.


_LIKE_METACHARACTERS = re.compile(r"([\\%_])")


def _prepare_like_pattern(term: str) -> str:
    """Neutralize shopper text for use inside an ILIKE pattern.

    Escapes the LIKE metacharacters (``\\``, ``%``, ``_``) so the input
    matches literally, then adds the surrounding wildcards. The value is
    still sent to PostgreSQL as a bound parameter — escaping here only
    stops a stray ``%`` or ``_`` from acting as a wildcard.
    """
    escaped = _LIKE_METACHARACTERS.sub(r"\\\1", term)
    return f"%{escaped}%"


@app.get("/api/products/category/{category_query}")
async def browse_category(
    category_query: str,
    limit: int = Query(default=5, ge=1, le=50),
    db: DatabaseService = Depends(get_db_service),
):
    """Fast category browsing without embeddings"""
    try:
        logger.info(f"📂 Category browse: '{category_query}' (limit={limit})")
        
        query = """
            SELECT
                "productId",
                name,
                brand,
                color,
                description,
                "imgUrl" as imgurl,
                rating,
                reviews,
                price,
                category,
                badge,
                tags,
                1.0 as similarity_score
            FROM pellier.product_catalog
            WHERE (category ILIKE %s OR name ILIKE %s OR description ILIKE %s)
              AND "imgUrl" IS NOT NULL
              AND NOT (tags ? 'archive')
            ORDER BY rating DESC, reviews::int DESC
            LIMIT %s
        """

        pattern = _prepare_like_pattern(category_query)
        results = await db.fetch_all(query, pattern, pattern, pattern, limit)
        logger.info(f"📦 Found {len(results)} products in category")
        
        return {
            "results": [
                {
                    "product": dict(row),
                    "similarity_score": 1.0
                }
                for row in results
            ],
            "total_results": len(results),
            "search_type": "category"
        }
    except Exception as e:
        logger.error(f"❌ Category browse failed: {e}")
        raise HTTPException(status_code=500, detail="internal_error")



# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/api/tools")
async def list_custom_tools():
    """List all custom business logic tools available"""
    return [
        {"name": "search_products", "description": "Search for products by natural language query with optional filters"},
        {"name": "get_trending_products", "description": "Get trending products by reviews and ratings"},
        {"name": "browse_category", "description": "Browse products filtered by category, rating, and price"},
        {"name": "check_inventory", "description": "Check stock levels and inventory alerts"},
        {"name": "get_price_analysis", "description": "Price analytics by category"},
        {"name": "restock_inventory", "description": "Update product stock quantities"},
        {"name": "compare_products", "description": "Side-by-side product comparison"},
        {"name": "get_low_stock", "description": "Find products running low on inventory"},
    ]


@app.get("/api/tools/trending")
async def get_trending(
    limit: int = Query(default=5, ge=1, le=50),
    category: str = Query(default=None),
    db: DatabaseService = Depends(get_db_service)
):
    """Get trending products using business logic"""
    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(db)
        return await logic.get_trending_products(limit, category)
    except Exception as e:
        logger.error(f"Failed to get trending products: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


@app.get("/api/tools/inventory-health")
async def check_inventory_endpoint(
    db: DatabaseService = Depends(get_db_service)
):
    """Get inventory health using business logic"""
    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(db)
        return await logic.check_inventory()
    except Exception as e:
        logger.error(f"Failed to get inventory health: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


@app.get("/api/tools/price-stats")
async def get_price_stats(
    category: str = Query(default=None),
    db: DatabaseService = Depends(get_db_service)
):
    """Get price statistics using business logic"""
    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(db)
        return await logic.get_price_analysis(category)
    except Exception as e:
        logger.error(f"Failed to get price statistics: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


@app.post("/api/tools/restock")
async def restock_inventory_endpoint(
    request: RestockRequest,
    operator: Dict[str, Any] = Depends(require_operator),
    db: DatabaseService = Depends(get_db_service),
):
    """Restock a product using business logic.

    This is an operator mutation, so it depends on ``require_operator``
    rather than the optional ``get_current_user``. The optional dependency
    returns ``None`` for an anonymous caller, and a handler that accepts
    ``None`` is an unauthenticated write path wearing an authenticated
    signature. ``require_operator`` guarantees a verified, non-empty
    ``sub`` this handler can attribute the mutation to.

    The body is a typed ``RestockRequest``: FastAPI rejects a malformed or
    out-of-range request with 422 before any database work starts.
    """
    if str(settings.WORKSHOP_FORMAT).lower() == "governed":
        raise HTTPException(status_code=409, detail="managed_rail_required")
    try:
        from services.business_logic import BusinessLogic
        logic = BusinessLogic(db)
        result = await logic.restock_inventory(
            product_id=request.product_id,
            quantity=request.quantity,
            idempotency_key=request.idempotency_key,
            warehouse_id=request.warehouse_id,
        )
    except Exception as e:
        logger.error(f"Failed to restock product: {e}")
        raise HTTPException(status_code=500, detail="restock_failed")

    # Record who performed the mutation. An inventory write with no
    # attributable principal is not auditable evidence.
    try:
        from services.tool_audit_writer import record_operator_mutation

        record_operator_mutation(
            tool_name="restock_inventory",
            caller="rest",
            principal_sub=operator["sub"],
            args={
                "product_id": request.product_id,
                "quantity": request.quantity,
                "warehouse_id": request.warehouse_id,
                "idempotency_key": request.idempotency_key,
            },
            result=result,
        )
    except Exception as exc:  # pragma: no cover - audit is best-effort
        logger.warning("restock audit write failed: %s", exc)

    if isinstance(result, dict):
        result = {**result, "performed_by": operator["sub"]}
    return result


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user=Depends(get_current_user)):
    """
    Chat endpoint with Aurora AI using Strands SDK and Custom Tools
    """
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")

    try:
        # Convert conversation history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]

        # Get chat response with session persistence
        response = await chat_service.chat(
            message=request.message,
            conversation_history=history,
            session_id=request.session_id,
            workshop_mode=request.workshop_mode,
            guardrails_enabled=request.guardrails_enabled,
            user=user
        )
        
        return ChatResponse(**response)
        
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail="chat_failed")


# Re-exported from services.turn_identity so `app.new_turn_id` keeps working for
# the routes and the turn-id contract test, while the format has one home.
from services.turn_identity import new_turn_id  # noqa: E402


def _annotate_rail(
    event: Dict[str, Any],
    decision,
    degraded_notice,
    turn_id: Optional[str] = None,
    session_id: Optional[str] = None,
    actual_rail: Optional[str] = None,
) -> Dict[str, Any]:
    """Stamp turn identity and the execution rail onto a ``complete`` event.

    Applied at the single point every storefront event funnels through, so
    a turn cannot report its outcome without also reporting which rail
    produced it and which turn it was. When the managed rail was requested
    but unavailable, the turn is additionally marked ``degraded`` with the
    capabilities that were withheld — a read-only in-process answer must
    never be mistaken for a governed one.
    """
    response = event.get("response")
    if not isinstance(response, dict):
        return event
    annotated = {
        **response,
        "rail": actual_rail or decision.rail,
        "railDecision": decision.to_dict(),
    }
    if turn_id:
        annotated["turn_id"] = turn_id
    if session_id:
        annotated["session_id"] = session_id
    if decision.managed_requested and not decision.available:
        annotated["degradation"] = degraded_notice(decision)
    return {**event, "response": annotated}


async def _persist_terminal_turn_receipt(
    *,
    turn_id: str,
    session_id: Optional[str],
    user: Optional[Dict[str, Any]],
    rail: str,
    terminal_status: str,
    started_at: float,
    trace: Optional[Dict[str, Any]] = None,
    terminal_error_code: Optional[str] = None,
    shopper_request: str = "",
    customer_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    assistant_response: str = "",
    specialist_route: str = "",
    tool_calls: Optional[List[Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Write one immutable receipt after a shopper turn has terminated.

    The receipt is not a prerequisite for serving an answer or an error. A
    failed evidence write returns ``None`` so callers never claim that an
    unpersisted receipt exists.
    """
    try:
        from services.governed_turn_receipt import persist_turn_receipt
        from services.shopper_handoff import build_handoff_context

        handoff_context = await build_handoff_context(
            db_service,
            turn_id=turn_id,
            session_id=session_id,
            customer_id=customer_id,
            shopper_request=shopper_request,
            conversation_history=conversation_history or [],
            assistant_response=assistant_response,
            specialist_route=specialist_route,
            tool_calls=tool_calls or [],
        )

        return await persist_turn_receipt(
            db_service,
            turn_id=turn_id,
            session_id=session_id,
            principal_sub=(user or {}).get("sub"),
            rail=rail,
            terminal_status=terminal_status,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            trace=trace,
            terminal_error_code=terminal_error_code,
            handoff_context=handoff_context,
        )
    except Exception as exc:  # pragma: no cover - persistence service is defensive
        logger.warning("governed turn receipt write skipped: %s", exc)
        return None


async def _aurora_profile_receipt(customer_id: Optional[str]) -> Dict[str, Any]:
    """Return bounded evidence that the verified profile exists in Aurora."""
    from services.data_source import database_source_label

    if not customer_id:
        return {
            "source": database_source_label(),
            "customer_id": None,
            "facts_available": 0,
            "orders_available": 0,
            "available": False,
        }
    if db_service is None:
        return {
            "source": "unavailable",
            "customer_id": customer_id,
            "facts_available": 0,
            "orders_available": 0,
            "available": False,
        }
    try:
        row = await db_service.fetch_one(
            """
            SELECT
              EXISTS (
                SELECT 1 FROM pellier.customers WHERE id = %s
              ) AS customer_exists,
              (
                SELECT count(*) FROM pellier.customer_episodic_seed
                 WHERE customer_id = %s
              ) AS facts_available,
              (
                SELECT count(*) FROM pellier.orders WHERE customer_id = %s
              ) AS orders_available
            """,
            customer_id,
            customer_id,
            customer_id,
        )
        return {
            "source": database_source_label(),
            "customer_id": customer_id,
            "facts_available": int((row or {}).get("facts_available") or 0),
            "orders_available": int((row or {}).get("orders_available") or 0),
            "available": bool((row or {}).get("customer_exists")),
        }
    except Exception as exc:
        logger.warning(
            "Aurora profile receipt unavailable for %s: %s",
            customer_id,
            exc.__class__.__name__,
        )
        return {
            "source": "error",
            "customer_id": customer_id,
            "facts_available": 0,
            "orders_available": 0,
            "available": False,
        }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, user=Depends(get_current_user)):
    """
    Streaming chat endpoint with real-time agent events via SSE.

    Uses chat_service.chat_stream() which runs the orchestrator in a background
    thread and yields events (tool calls, products, text) the moment they happen
    via an asyncio.Queue bridge, instead of waiting for the full chain to finish.
    """
    from fastapi.responses import StreamingResponse

    if settings.PELLIER_SMOKE_MODE:
        async def smoke_event_generator():
            content = (
                "I'm Pellier. For ten days in Goa, I would start with the "
                "Italian Linen Camp Shirt, Linen Drawstring Trousers, Linen "
                "Overshirt, and a cotton-linen tee, then rotate the lighter "
                "layers around dinners, travel days, and the beach."
            )
            if request.message.strip().lower() in {"hi", "hello", "hey"}:
                content = (
                    "I'm Pellier, your boutique concierge. I can help you "
                    "search linen, compare pieces, and keep the edit grounded."
                )

            routing = {
                "type": "skill_routing",
                "routing": {
                    "loaded_skills": ["the-packing-list"],
                    "considered": [
                        {
                            "name": "the-packing-list",
                            "reason": "Smoke-mode wardrobe query routing.",
                        }
                    ],
                    "elapsed_ms": 1,
                    "user_message": request.message,
                },
            }
            complete = {
                "type": "complete",
                "response": {
                    "response": content,
                    "products": [],
                    "suggestions": [
                        "Compare the linen layers",
                        "Show lighter travel pieces",
                        "Build a 10-day packing list",
                    ],
                    "agent_execution": {
                        "agent_steps": [],
                        "tool_calls": [],
                        "reasoning_steps": [],
                        "total_duration_ms": 1,
                        "success_rate": 1.0,
                    },
                    "token_count": 0,
                    "estimated_cost_usd": 0,
                },
            }

            # Smoke mode still mints a turn id: it is the mode that runs on
            # stage, and a receipt link that works everywhere except the demo
            # is not a working receipt link.
            smoke_turn_id = new_turn_id()
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "turn_start",
                        "turn_id": smoke_turn_id,
                        "session_id": request.session_id,
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            complete["response"]["turn_id"] = smoke_turn_id
            if request.session_id:
                complete["response"]["session_id"] = request.session_id
            yield f"data: {json.dumps(routing, ensure_ascii=False)}\n\n"
            await asyncio.sleep(SMOKE_THINKING_DELAY_SECONDS)
            for chunk in _editorial_stream_chunks(content):
                yield (
                    "data: "
                    f"{json.dumps({'type': 'content_delta', 'delta': chunk}, ensure_ascii=False)}"
                    "\n\n"
                )
                await asyncio.sleep(SMOKE_CHUNK_DELAY_SECONDS)
            yield f"data: {json.dumps(complete, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            smoke_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")

    async def event_generator():
        turn_id: Optional[str] = None
        receipt_attempted = False
        effective_user: Dict[str, Any] = {}
        history: List[Dict[str, Any]] = []
        shopper_customer_id: Optional[str] = None
        turn_started = time.perf_counter()

        async def persist_terminal(
            *,
            rail: str,
            terminal_status: str,
            trace: Optional[Dict[str, Any]] = None,
            terminal_error_code: Optional[str] = None,
            assistant_response: str = "",
            specialist_route: str = "",
            tool_calls: Optional[List[Any]] = None,
        ) -> Optional[Dict[str, Any]]:
            """Persist exactly once, even if a stream then raises."""
            nonlocal receipt_attempted
            if receipt_attempted or not turn_id:
                return None
            receipt_attempted = True
            return await _persist_terminal_turn_receipt(
                turn_id=turn_id,
                session_id=request.session_id,
                user=effective_user or None,
                rail=rail,
                terminal_status=terminal_status,
                started_at=turn_started,
                trace=trace,
                terminal_error_code=terminal_error_code,
                shopper_request=request.message,
                customer_id=shopper_customer_id,
                conversation_history=history,
                assistant_response=assistant_response,
                specialist_route=specialist_route,
                tool_calls=tool_calls,
            )

        try:
            history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
            effective_user = dict(user) if user else {}
            from services.turn_identity import resolve_turn_identity

            turn_identity = resolve_turn_identity(
                user=effective_user,
                requested_customer_id=request.customer_id,
            )
            shopper_customer_id = turn_identity.shopper_customer_id

            # Per-turn guardrail INPUT check — records a decision in
            # services/guardrails_log so the Observatory Grounding page's
            # Guardrails lane shows live audit rows. Only runs when
            # the user enabled guardrails in their request; otherwise
            # the log captures no entry (accurate — nothing happened).
            # Failures are swallowed: guardrail eval is observational,
            # not a hard turn gate in this demo surface.
            guardrail_event = None
            if request.guardrails_enabled:
                try:
                    import time as _time
                    from services.guardrails import GuardrailsService
                    from services.guardrails_log import record_guardrail
                    _g = GuardrailsService()
                    _t0 = _time.perf_counter()
                    _res = _g.check_input(request.message)
                    _latency = int((_time.perf_counter() - _t0) * 1000)
                    record_guardrail(
                        session_id=request.session_id,
                        source="INPUT",
                        action=_res.get("action", "NONE"),
                        allowed=_res.get("allowed", True),
                        violations=_res.get("violations", []),
                        latency_ms=_latency,
                        text_preview=request.message,
                        mode=_res.get("mode"),
                    )
                    guardrail_event = {
                        "type": "guardrail_decision",
                        "guardrail": {
                            "allowed": bool(_res.get("allowed", True)),
                            "action": str(_res.get("action", "NONE")),
                            "violations": len(_res.get("violations", [])),
                            "mode": str(_res.get("mode") or "configured"),
                            "enforced": False,
                        },
                    }
                except Exception as _exc:
                    logger.debug("Input guardrail observational check failed: %s", _exc)
                    guardrail_event = {
                        "type": "guardrail_decision",
                        "guardrail": {
                            "allowed": True,
                            "action": "ERROR",
                            "violations": 0,
                            "mode": "error",
                            "enforced": False,
                        },
                    }

            if guardrail_event is not None:
                yield f"data: {json.dumps(guardrail_event, ensure_ascii=False)}\n\n"

            # Resolve the execution rail through the same service the
            # managed ``/api/agent/chat`` route uses, so the storefront can
            # never quietly run ungoverned while the operator believes the
            # managed rail is live. Every completed turn reports the rail
            # that actually served it.
            from services.execution_rail import (
                degraded_notice,
                resolve_rail,
            )

            rail_decision = resolve_rail(
                auth_token=(effective_user or {}).get("access_token")
            )
            if rail_decision.managed_requested and not rail_decision.available:
                logger.warning(
                    "Storefront turn degraded: managed rail requested but "
                    "unavailable (%s)",
                    rail_decision.reason,
                )

            # Mint the turn identity before streaming so the id is stable
            # for the whole turn and can be emitted on the first event.
            # The client persists it and uses it to deep-link the exact
            # turn's evidence in Observatory.
            turn_id = new_turn_id()
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "turn_start",
                        "turn_id": turn_id,
                        "session_id": request.session_id,
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            # Pellier is the governed workshop's participant path. Once
            # the managed rail is selected, it must execute through Runtime
            # rather than run the local chat service and attach a managed
            # label afterward. A Runtime response is currently one complete
            # payload, so this branch emits a single content event followed by
            # the normal completion envelope.
            if rail_decision.managed_requested:
                if not rail_decision.available:
                    error = classify_chat_error(rail_decision.reason)
                    await persist_terminal(
                        rail=rail_decision.rail,
                        terminal_status="failed",
                        terminal_error_code=error["code"],
                    )
                    yield (
                        "data: "
                        + json.dumps(error, ensure_ascii=False)
                        + "\n\n"
                    )
                    return

                if not turn_identity.shopper_customer_id:
                    error = classify_chat_error("customer_identity_unmapped")
                    await persist_terminal(
                        rail=rail_decision.rail,
                        terminal_status="failed",
                        terminal_error_code=error["code"],
                    )
                    yield (
                        "data: "
                        + json.dumps(error, ensure_ascii=False)
                        + "\n\n"
                    )
                    return

                from services.intent_router import classify_intent
                from services.response_mode import build_intent_signal

                yield (
                    "data: "
                    + json.dumps(
                        build_intent_signal(
                            classify_intent(request.message),
                            request.response_mode,
                        ),
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )

                from services.agentcore_runtime import (
                    ManagedRuntimeError,
                    get_latest_trace,
                    run_agent_on_runtime_result,
                )
                from services.agentcore_identity import AgentCoreIdentityService
                from services.agentcore_memory import (
                    AgentCoreMemory,
                    ManagedMemoryError,
                )

                managed_started = time.perf_counter()
                managed_session_id = request.session_id or turn_id
                memory_namespace = AgentCoreIdentityService.build_namespace(
                    turn_identity.principal_sub,
                    managed_session_id,
                )
                managed_memory = AgentCoreMemory(strict=True)
                try:
                    managed_history = await managed_memory.get_session_history(
                        memory_namespace
                    )
                except ManagedMemoryError as exc:
                    error = classify_chat_error(exc.code)
                    await persist_terminal(
                        rail=rail_decision.rail,
                        terminal_status="failed",
                        terminal_error_code=error["code"],
                    )
                    yield f"data: {json.dumps(error, ensure_ascii=False)}\n\n"
                    return

                profile_customer_id = turn_identity.shopper_customer_id
                profile_receipt = await _aurora_profile_receipt(profile_customer_id)
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "aurora_profile_context",
                            "profile": profile_receipt,
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
                try:
                    managed_result = await run_agent_on_runtime_result(
                        message=request.message,
                        session_id=managed_session_id,
                        user_id=turn_identity.principal_sub,
                        auth_token=(effective_user or {}).get("access_token"),
                        history=managed_history,
                        turn_id=turn_id,
                        response_mode=request.response_mode,
                        customer_id=profile_customer_id,
                    )
                except ManagedRuntimeError as exc:
                    error = classify_chat_error(exc.code)
                    await persist_terminal(
                        rail=rail_decision.rail,
                        terminal_status=(
                            "denied-before-execution"
                            if error["code"] == "policy_denied"
                            else "failed"
                        ),
                        terminal_error_code=error["code"],
                    )
                    yield (
                        "data: "
                        + json.dumps(error, ensure_ascii=False)
                        + "\n\n"
                    )
                    return

                memory_receipt = {
                    "source": "agentcore-memory",
                    "turns_loaded": len(managed_history),
                    "turns_persisted": 0,
                    "namespace_scope": "verified-principal",
                    "read_status": "succeeded",
                    "write_status": "pending",
                    "action_status": "completed",
                    "retry_recommended": False,
                }
                try:
                    await managed_memory.append_session_turns(
                        memory_namespace,
                        [
                            {"role": "user", "content": request.message},
                            {
                                "role": "assistant",
                                "content": managed_result.response,
                            },
                        ],
                    )
                    memory_receipt["turns_persisted"] = 2
                    memory_receipt["write_status"] = "succeeded"
                except ManagedMemoryError as exc:
                    logger.warning(
                        "Managed Memory did not persist completed Runtime turn %s",
                        turn_id,
                    )
                    memory_receipt["write_status"] = "failed"
                    memory_receipt["error_code"] = exc.code
                except Exception as exc:
                    logger.warning(
                        "Managed Memory write failed after completed Runtime "
                        "turn %s: %s",
                        turn_id,
                        exc.__class__.__name__,
                    )
                    memory_receipt["source"] = "unavailable"
                    memory_receipt["write_status"] = "failed"
                    memory_receipt["error_code"] = "memory_write_failed"

                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "agentcore_memory",
                            "memory": memory_receipt,
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
                if managed_result.specialist:
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "agent_step",
                                "agent": managed_result.specialist,
                                "action": (
                                    f"Dispatcher routed {managed_result.intent or 'request'}"
                                ),
                                "status": "completed",
                                "source": "Amazon Bedrock",
                            },
                            ensure_ascii=False,
                        )
                        + "\n\n"
                    )
                for tool_call in managed_result.tool_calls:
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "tool_call",
                                **tool_call,
                            },
                            ensure_ascii=False,
                            default=str,
                        )
                        + "\n\n"
                    )
                for product in managed_result.products:
                    yield (
                        "data: "
                        + json.dumps(
                            {"type": "product", "product": product},
                            ensure_ascii=False,
                            default=str,
                        )
                        + "\n\n"
                    )

                managed_trace = get_latest_trace(
                    managed_session_id,
                    principal_sub=turn_identity.principal_sub,
                )
                actual_rail = str(managed_trace.get("rail") or "")
                event = {
                    "type": "complete",
                    "response": {
                        "response": managed_result.response,
                        "products": managed_result.products,
                        "suggestions": [],
                        "success": True,
                        "model": managed_result.model,
                        "memory": memory_receipt,
                        "warnings": (
                            [
                                {
                                    "code": memory_receipt.get("error_code"),
                                    "message": MEMORY_WRITE_WARNING,
                                    "retry_recommended": False,
                                }
                            ]
                            if memory_receipt["write_status"] == "failed"
                            else []
                        ),
                        "orchestration": {
                            "pattern": managed_result.orchestration,
                            "route": managed_result.intent,
                            "router": "deterministic",
                        },
                        "agent_execution": {
                            "agent_steps": (
                                [
                                    {
                                        "agent": managed_result.specialist,
                                        "action": (
                                            "Dispatcher selected specialist"
                                        ),
                                        "status": "completed",
                                    }
                                ]
                                if managed_result.specialist
                                else []
                            ),
                            "tool_calls": managed_result.tool_calls,
                            "reasoning_steps": [],
                            "total_duration_ms": int(
                                (time.perf_counter() - managed_started) * 1000
                            ),
                            "managed_trace": managed_trace,
                        },
                    },
                }
                receipt = await persist_terminal(
                    rail=actual_rail or rail_decision.rail,
                    terminal_status="complete",
                    trace=managed_trace,
                    assistant_response=managed_result.response,
                    specialist_route=managed_result.specialist,
                    tool_calls=managed_result.tool_calls,
                )
                if receipt:
                    event["response"]["governed_receipt"] = receipt
                event = _annotate_rail(
                    event,
                    rail_decision,
                    degraded_notice,
                    turn_id=turn_id,
                    session_id=request.session_id,
                    actual_rail=actual_rail or None,
                )
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "content",
                            "content": managed_result.response,
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
                return

            # Local retrieval tools run in a Strands worker thread. Bind only
            # server-minted route context before that worker starts so a model
            # can never choose another principal, rail, or turn id for its
            # retrieval receipt.
            from services.retrieval_receipt import (
                reset_turn_context,
                set_turn_context,
            )

            local_user = dict(effective_user)
            if turn_identity.shopper_customer_id:
                local_user["customer_id"] = turn_identity.shopper_customer_id

            receipt_context = set_turn_context(
                turn_id=turn_id,
                session_id=request.session_id,
                principal_sub=turn_identity.principal_sub,
                rail=rail_decision.rail,
            )
            try:
                async for event in chat_service.chat_stream(
                    message=request.message,
                    conversation_history=history,
                    session_id=request.session_id,
                    workshop_mode=request.workshop_mode,
                    guardrails_enabled=request.guardrails_enabled,
                    user=local_user or None,
                    pattern=request.pattern,
                    turn_id=turn_id,
                    response_mode=request.response_mode,
                ):
                    if event.get("type") == "error":
                        event = classify_chat_error(
                            event.get("error") or event.get("message") or event.get("code")
                        )
                        await persist_terminal(
                            rail=rail_decision.rail,
                            terminal_status=(
                                "denied-before-execution"
                                if event["code"] == "policy_denied"
                                else "failed"
                            ),
                            terminal_error_code=event["code"],
                        )
                    elif event.get("type") == "complete":
                        response = event.get("response")
                        execution = (
                            response.get("agent_execution")
                            if isinstance(response, dict)
                            else None
                        )
                        trace = (
                            execution.get("managed_trace")
                            if isinstance(execution, dict)
                            and isinstance(execution.get("managed_trace"), dict)
                            else None
                        )
                        receipt = await persist_terminal(
                            rail=rail_decision.rail,
                            terminal_status="complete",
                            trace=trace,
                            assistant_response=(
                                str(response.get("response") or "")
                                if isinstance(response, dict)
                                else ""
                            ),
                            specialist_route=(
                                str(
                                    ((response.get("orchestration") or {}).get("route"))
                                    or execution.get("specialistRoute")
                                    or ""
                                )
                                if isinstance(response, dict)
                                and isinstance(execution, dict)
                                else ""
                            ),
                            tool_calls=(
                                list(execution.get("tool_calls") or [])
                                if isinstance(execution, dict)
                                else []
                            ),
                        )
                        if receipt and isinstance(response, dict):
                            response["governed_receipt"] = receipt
                        event = _annotate_rail(
                            event,
                            rail_decision,
                            degraded_notice,
                            turn_id=turn_id,
                            session_id=request.session_id,
                        )
                    yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
            finally:
                reset_turn_context(receipt_context)
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}")
            error = classify_chat_error(e)
            await persist_terminal(
                rail=(
                    rail_decision.rail
                    if "rail_decision" in locals()
                    else "in-process"
                ),
                terminal_status=(
                    "denied-before-execution"
                    if error["code"] == "policy_denied"
                    else "failed"
                ),
                terminal_error_code=error["code"],
            )
            yield (
                "data: "
                f"{json.dumps(error, ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=5, ge=1, le=10),
    db: DatabaseService = Depends(get_db_service)
):
    """Product search autocomplete"""
    try:
        query = """
            SELECT name, category
            FROM pellier.product_catalog
            WHERE name ILIKE %s
              AND NOT (tags ? 'archive')
            ORDER BY reviews DESC
            LIMIT %s
        """
        results = await db.fetch_all(query, _prepare_like_pattern(q), limit)
        return {"suggestions": [{
            "text": r["name"][:60],
            "category": r["category"]
        } for r in results]}
    except Exception as e:
        logger.error(f"❌ Autocomplete failed: {e}")
        return {"suggestions": []}


# NOTE: the old ``POST /api/agents/query`` legacy endpoint (which
# dispatched to individual specialist agents by ``agent_type``) has
# been removed. No frontend caller remained — the orchestrator path
# is ``POST /api/agent/chat`` (see routes/agent.py) which the
# concierge already uses.


# ============================================================================
# SQL QUERY INSPECTOR ENDPOINTS
# ============================================================================

@app.get("/api/queries/recent")
async def get_recent_queries(limit: int = Query(default=10, ge=1, le=50)):
    """
    Get recent SQL queries with performance metrics
    
    Returns query logs for the SQL Inspector UI
    """
    try:
        query_logger_instance = get_query_logger()
        queries = query_logger_instance.get_recent_queries(limit=limit)
        stats = query_logger_instance.get_summary_stats()
        
        return {
            "queries": queries,
            "stats": stats,
            "total": len(queries)
        }
    except Exception as e:
        logger.error(f"Failed to get recent queries: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


@app.post("/api/queries/clear")
async def clear_query_logs():
    """Clear all query logs"""
    try:
        query_logger_instance = get_query_logger()
        query_logger_instance.clear_logs()
        return {"status": "success", "message": "Query logs cleared"}
    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


# ============================================================================
# INDEX PERFORMANCE ENDPOINTS
# ============================================================================

@app.post("/api/performance/compare")
async def compare_index_performance(
    request: PerfCompareRequest,
    embeddings: EmbeddingService = Depends(get_embedding_service)
):
    """
    Compare HNSW index performance vs sequential scan

    Request body is validated by PerfCompareRequest: ef_search reaches a
    Postgres SET statement that cannot bind parameters, so it must be a
    bounded int before it is interpolated.
    """
    try:
        query = request.query
        ef_search = request.ef_search
        limit = request.limit

        logger.info(f"🔬 Index performance comparison: '{query}' (ef_search={ef_search})")
        
        # Generate embedding
        embedding = embeddings.generate_embedding(query)
        
        # Run comparison
        results = await index_performance_service.compare_index_performance(
            query=query,
            embedding=embedding,
            ef_search=ef_search,
            limit=limit
        )
        
        logger.info(f"✅ Comparison complete: HNSW={results['hnsw']['execution_time_ms']}ms, Sequential={results['sequential']['execution_time_ms']}ms")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Performance comparison failed: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


@app.get("/api/performance/runtime")
async def performance_runtime(include_recent: bool = False):
    """Return rolling aggregates of chat turn latency breakdowns.

    Feeds the Observatory Performance tab — layer p50/p95 replace the
    hardcoded 3779ms/4ms numbers, cold-start histogram replaces the
    stub bars, tool p50 fuels the per-tool legend. Empty buffer is
    reported honestly so the UI can show a placeholder instead of
    faking data.
    """
    try:
        from services.performance_log import get_aggregates, get_recent_turns
        agg = get_aggregates()
        if include_recent:
            agg = {**agg, "recent": get_recent_turns(limit=30)}
        return agg
    except Exception as e:
        logger.warning(f"Performance runtime stats failed: {e}")
        return {
            "turn_count": 0,
            "empty": True,
            "error": "runtime_metrics_unavailable",
        }


@app.get("/api/performance/stats")
async def get_index_stats():
    """Get pgvector index statistics"""
    try:
        stats = await index_performance_service.get_index_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get index stats: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


# ============================================================================
# CONTEXT MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/context/stats")
async def get_context_stats(session_id: Optional[str] = Query(default=None)):
    """
    Get context statistics for monitoring
    
    Returns comprehensive metrics for token usage, efficiency, and costs.
    Demonstrates context-window management for the configured Bedrock model.
    
    Args:
        session_id: Optional session ID for session-specific stats
    """
    try:
        from services.context_manager import get_context_manager
        
        context_manager = get_context_manager()
        stats = context_manager.get_context_stats()
        
        logger.info(f"📊 Context stats requested: {stats['current_tokens']:,} tokens, {stats['efficiency_score']:.1f}% efficiency")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get context stats: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


@app.post("/api/context/clear")
async def clear_context(session_id: str = Query(...)):
    """
    Clear context for a session
    
    Useful for starting fresh conversations or freeing memory.
    System prompts are preserved.
    
    Args:
        session_id: Session ID to clear context for
    """
    try:
        from services.context_manager import get_context_manager
        
        context_manager = get_context_manager()
        context_manager.clear_context()
        
        logger.info(f"🗑️ Context cleared for session: {session_id}")
        
        return {
            "status": "success",
            "message": f"Context cleared for session {session_id}",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Failed to clear context: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


@app.get("/api/context/prompts")
async def list_prompts():
    """
    List all available prompt templates with versions and performance metrics
    
    Demonstrates enterprise-grade prompt engineering patterns:
    - Versioned prompts for A/B testing
    - Performance tracking per prompt
    - Agent-specific prompt templates
    """
    try:
        from services.context_manager import PromptRegistry
        
        prompts = PromptRegistry.list_available_prompts()
        
        logger.info(f"📋 Listed {len(prompts)} prompt templates")
        
        return {
            "prompts": prompts,
            "total": len(prompts)
        }
        
    except Exception as e:
        logger.error(f"Failed to list prompts: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


# ============================================================================
# QUANTIZATION COMPARISON ENDPOINT
# ============================================================================

@app.get("/api/performance/quantization")
async def get_quantization_comparison():
    """Compare full-precision vs quantized (SQ/BQ) index sizes"""
    if not index_performance_service:
        raise HTTPException(status_code=503, detail="Index performance service not initialized")
    return await index_performance_service.get_quantization_comparison()


@app.get("/api/performance/categories")
async def get_filter_categories():
    """Get distinct categories for iterative scan demo dropdown"""
    if not index_performance_service:
        raise HTTPException(status_code=503, detail="Index performance service not initialized")
    categories = await index_performance_service.get_distinct_categories()
    return {"categories": categories}


@app.post("/api/performance/iterative-scan")
async def compare_iterative_scan(request: PerfIterativeScanRequest):
    """Compare filtered HNSW with and without iterative scan (pgvector 0.8.0+)"""
    if not index_performance_service:
        raise HTTPException(status_code=503, detail="Index performance service not initialized")
    embedding = embedding_service.generate_embedding(request.query)
    return await index_performance_service.compare_filtered_search(
        query=request.query, embedding=embedding,
        category_filter=request.category, ef_search=request.ef_search,
        limit=request.limit,
    )


@app.post("/api/performance/quantization-benchmark")
async def quantization_benchmark(request: PerfQuantizationRequest):
    """Benchmark float32 vs halfvec vs binary quantization with live queries"""
    if not index_performance_service:
        raise HTTPException(status_code=503, detail="Index performance service not initialized")
    embedding = embedding_service.generate_embedding(request.query)
    return await index_performance_service.compare_quantization_benchmark(
        query=request.query, embedding=embedding, limit=request.limit,
    )


# ============================================================================
# PERSONALIZED SEARCH ENDPOINT
# ============================================================================

@app.post("/api/personalization/search")
async def personalized_search(
    request: Request,
    db: DatabaseService = Depends(get_db_service),
):
    """Search with preference-based re-ranking"""
    from services.business_logic import BusinessLogic
    logic = BusinessLogic(db)
    body = await request.json()
    query = body.get("query", "")
    preferences = body.get("preferences", {})
    limit = body.get("limit", 5)
    return await logic.personalized_search(query, preferences, limit)


# ============================================================================
# WORKSHOP MODULE STATUS ENDPOINT
# ============================================================================

@app.get("/api/observatory/skills")
async def list_skills():
    """
    List all skills in the registry for the Observatory surfaces.

    Returns a bare JSON array, matching the sibling list endpoints
    (``/api/observatory/agents``, ``/api/observatory/tools/list``) and the
    ``skills.json`` fixture shape. ``useObservatoryData`` stores the response
    verbatim, so a bare array keeps ``data ?? []`` an array even if a
    surface is ever switched from fixture mode to ``source: 'api'`` for the
    ``skills`` key — a wrapper object would break the downstream ``.map``.

    Each item carries name, description, version, display_name,
    token_estimate, and the full markdown body so the "Open SKILL.md →"
    link can render it inline without a second request. (Curated UI-only
    fields — persona, loadedBy, signals, status — live in the fixture; the
    registry does not own them.)
    """
    from skills import get_registry
    registry = get_registry()
    return [
        {
            "name": s.name,
            "display_name": s.display_name_resolved,
            "description": s.description,
            "version": s.version,
            "token_estimate": s.token_estimate,
            "body": s.body,
            "path": s.path,
        }
        for s in registry.get_all()
    ]


@app.get("/api/observatory/search-strategies/compare")
async def compare_search_strategies(query: str):
    """Run the same query through four retrieval strategies, return
    one observed duration per strategy + top-5 product names + (when present) the
    structured filters Sonnet extracted.

    Surfaces Anna's anchor-capability comparison live to the
    Observatory Performance page so workshop participants can see the
    delta between vector-only / hybrid / hybrid+rerank / agentic
    against the real catalog rather than reading a static fixture.

    Strategies:
      1. **vector only** — pgvector cosine over product_catalog.
         Marco's foundation path.
      2. **hybrid (RRF)** — vector + Postgres FTS in parallel, RRF-merged.
         No reranker pass. Kept as a teaching foil — pure lexical
         loses on conversational queries with this corpus.
      3. **hybrid + rerank** — same as #2 plus Cohere Rerank v3.5.
      4. **agentic (Sonnet → filter → vector → rerank)** — Anna's
         shipped path. Sonnet 4.6 extracts {categories, tags,
         price_max, in_stock, soft_signal}; pgvector cosine
         runs over the filtered candidate set with
         ``hnsw.iterative_scan = 'relaxed_order'`` so filtered recall
         doesn't silently collapse; Cohere Rerank reorders the pool
         using the soft_signal phrase (not the raw query) so
         structured constraints don't pollute the rerank score.

    Returns:
      {
        "query": str,
        "strategies": [
          {"strategy", "observedMs", "modeledCostPerThousandUsd",
           "products": [{name, productId}],
           "extractedFilters": {...}  // strategy 4 only
          }
        ]
      }

    This endpoint runs each strategy once. Its durations are observations,
    not percentile statistics. Cost values are modeled incremental request
    costs sourced from ``SEARCH_STRATEGY_COST_PER_1000_USD`` so the live
    endpoint and operator copy have one backend source; they are not values
    read from a bill.
    """
    import asyncio
    import time
    from services.embeddings import EmbeddingService
    from services.vector_search import VectorSearch
    from services.hybrid_search import HybridSearch
    from services.rerank import get_rerank_service
    from services.search_plan import build_plan
    from services.structured_extract import get_structured_extractor

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="query parameter required")
    q = query.strip()

    embed = EmbeddingService()
    shared_embed_started = time.perf_counter()
    query_embedding = embed.embed_query(q)
    shared_embedding_ms = int(
        (time.perf_counter() - shared_embed_started) * 1000
    )

    if db_service is None:
        raise HTTPException(
            status_code=503,
            detail="DB not initialized — wait for backend startup to complete",
        )
    db = db_service

    # Strategy 1: pure pgvector cosine. Marco's path.
    t0 = time.perf_counter()
    vec = VectorSearch(db)
    vec_rows = await vec.vector_search(
        query_embedding,
        5,
        ef_search=settings.VECTOR_EF_SEARCH_DEFAULT,
    )
    vec_ms = int((time.perf_counter() - t0) * 1000)
    vec_products = [
        {"name": r.get("name", ""), "productId": r.get("product_id")}
        for r in vec_rows[:5]
    ]

    # Strategy 2: hybrid (RRF), no rerank.
    t0 = time.perf_counter()
    hybrid = HybridSearch(db)
    hybrid_rows = await hybrid.search(
        query=q,
        query_embedding=query_embedding,
        top_n=5,
    )
    hybrid_ms = int((time.perf_counter() - t0) * 1000)
    hybrid_products = [
        {"name": r.get("name", ""), "productId": r.get("product_id")}
        for r in hybrid_rows[:5]
    ]

    # Strategy 3: hybrid + rerank.
    t0 = time.perf_counter()
    rerank_pool = await hybrid.search(
        query=q,
        query_embedding=query_embedding,
        top_n=settings.HYBRID_TOP_N,
    )
    documents = [
        f"{r.get('name','')} — {(r.get('description','') or '')[:200]} ({r.get('category','')})"
        for r in rerank_pool
    ]
    rerank_service = get_rerank_service()
    rerank_results = rerank_service.rerank(query=q, documents=documents, top_n=5)
    rerank_ms = int((time.perf_counter() - t0) * 1000)
    if rerank_results:
        rerank_products = [
            {
                "name": rerank_pool[r["index"]].get("name", ""),
                "productId": rerank_pool[r["index"]].get("product_id"),
            }
            for r in rerank_results
        ]
    else:
        rerank_products = [
            {"name": r.get("name", ""), "productId": r.get("product_id")}
            for r in rerank_pool[:5]
        ]

    # Strategy 4: agentic — Sonnet-extracted filters → filtered vector
    # → rerank with soft_signal. The boto3 calls are synchronous, so
    # they run on a worker thread to keep the event loop responsive.
    t0 = time.perf_counter()
    extractor = get_structured_extractor()
    extracted = await asyncio.to_thread(extractor.extract, q)
    soft_signal = extracted.get("soft_signal") or q
    # Re-embed only when the soft_signal differs from the raw query —
    # a wasted embed on identical text would just inflate the cost
    # number without changing the ranking.
    if soft_signal != q:
        soft_embedding = embed.embed_query(soft_signal)
    else:
        soft_embedding = query_embedding

    # Compile the model's extraction into a typed plan, then walk that
    # plan's relaxation ladder. The ladder widens *preferences* only:
    # price ceilings, availability, explicit categories, and exclusions
    # are hard constraints that no rung may drop. A one-result return is
    # sometimes worse than a wider pool — but a $250 candle returned for
    # "in-stock gift under $100, no candles" is always worse than both,
    # so the widening stops at the correctness boundary.
    AGENTIC_MIN_POOL = 5
    plan = build_plan(q, extracted, top_k=5)
    agentic_pool: List[Dict[str, Any]] = []
    plan_used = plan
    for rung in plan.relaxation_ladder():
        clauses, clause_params = rung.compile_predicates()
        agentic_pool = await vec.vector_search_planned(
            embedding=soft_embedding,
            limit=settings.HYBRID_TOP_N,
            ef_search=settings.VECTOR_EF_SEARCH_DEFAULT,
            predicates=clauses,
            predicate_params=clause_params,
        )
        plan_used = rung
        if len(agentic_pool) >= AGENTIC_MIN_POOL:
            break
    filter_used = (
        plan_used.relaxations[-1].step if plan_used.relaxations else "strict"
    )
    agentic_docs = [
        f"{r.get('name','')} — {(r.get('description','') or '')[:200]} ({r.get('category','')})"
        for r in agentic_pool
    ]
    agentic_rerank = rerank_service.rerank(
        query=soft_signal, documents=agentic_docs, top_n=5,
    )
    agentic_ms = int((time.perf_counter() - t0) * 1000)
    if agentic_rerank:
        agentic_products = [
            {
                "name": agentic_pool[r["index"]].get("name", ""),
                "productId": agentic_pool[r["index"]].get("product_id"),
            }
            for r in agentic_rerank
        ]
    else:
        agentic_products = [
            {"name": r.get("name", ""), "productId": r.get("product_id")}
            for r in agentic_pool[:5]
        ]

    return {
        "query": q,
        "sharedQueryEmbeddingObservedMs": shared_embedding_ms,
        "measurementAssumptions": {
            "latency": (
                "One wall-clock observation per strategy for this request; "
                "not a percentile. Strategies run sequentially after a shared "
                "query embedding."
            ),
            "cost": (
                "Modeled incremental request cost per 1,000 queries; not a "
                "billing measurement and excluding provisioned Aurora compute."
            ),
            "quality": (
                "Product order is live. Recall requires labeled relevance "
                "judgments and is not calculated by this endpoint."
            ),
        },
        "strategies": [
            {
                "strategy": "vector only",
                "observedMs": vec_ms,
                "modeledCostPerThousandUsd": SEARCH_STRATEGY_COST_PER_1000_USD["vector"],
                "products": vec_products,
            },
            {
                "strategy": "hybrid (RRF)",
                "observedMs": hybrid_ms,
                "modeledCostPerThousandUsd": SEARCH_STRATEGY_COST_PER_1000_USD["hybrid"],
                "products": hybrid_products,
            },
            {
                "strategy": "hybrid + rerank",
                "observedMs": rerank_ms,
                "modeledCostPerThousandUsd": SEARCH_STRATEGY_COST_PER_1000_USD["rerank"],
                "products": rerank_products,
            },
            {
                "strategy": "agentic (Sonnet → filter → vector → rerank)",
                "observedMs": agentic_ms,
                "modeledCostPerThousandUsd": SEARCH_STRATEGY_COST_PER_1000_USD["agentic"],
                "products": agentic_products,
                "extractedFilters": {
                    "categories": extracted.get("categories", []),
                    "tags": extracted.get("tags", []),
                    "priceMaxUsd": extracted.get("price_max_usd"),
                    "inStockOnly": extracted.get("in_stock_only", False),
                    "softSignal": soft_signal,
                    "filterUsed": filter_used,
                },
                # The typed plan that actually ran, including any widening.
                # Hard constraints and exclusions are reported separately
                # from preferences so the surface can state plainly which
                # of the two the pipeline is allowed to relax.
                "searchPlan": plan_used.to_dict(),
                "hardConstraintsEnforced": plan_used.hard.describe(),
                "relaxations": [r.to_dict() for r in plan_used.relaxations],
            },
        ],
    }


@app.get("/api/observatory/search/explain")
async def explain_search(query: str):
    """Run one hybrid query and return every *intermediate* stage so the
    Observatory "Search" surface can show the mechanism, not just the outcome.

    This is the mechanism counterpart to ``/search-strategies/compare``
    (which shows the *outcome* — which products win, how fast, at what
    cost). Here the payload walks the pipeline a single query takes:

        EMBED → VECTOR → LEXICAL → FUSION → RERANK

    Every stage carries the real artifact a participant should read:
    the literal branch SQL for VECTOR/LEXICAL (the same string the live
    path executes — see ``hybrid_search._VECTOR_BRANCH_SQL`` /
    ``_FTS_BRANCH_SQL``), the per-branch ranks the FUSION stage merges,
    and the position delta the RERANK stage produces. The reordering
    between FUSION and RERANK *is* the teaching moment, and it is live
    data — nothing here is fabricated.

    The response is shaped as panel-shaped stages
    (``tag``/``title``/``sql``/``columns``/``rows``/``meta``/``tagClass``)
    so the frontend reuses the existing telemetry-panel renderer. Rows
    are pre-stringified.

    On a Bedrock rerank outage the RERANK stage degrades honestly: it
    reports the failure in ``meta`` and shows the RRF order unchanged
    (``rrf_pos == reranked_pos``) rather than inventing scores.
    """
    import time
    from services.embeddings import EmbeddingService
    from services.hybrid_search import HybridSearch
    from services.rerank import get_rerank_service

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="query parameter required")
    q = query.strip()

    if db_service is None:
        raise HTTPException(
            status_code=503,
            detail="DB not initialized — wait for backend startup to complete",
        )

    # ---- helpers -------------------------------------------------------
    def _label(row: Dict[str, Any]) -> str:
        name = row.get("name", "") or "(unnamed)"
        brand = row.get("brand", "")
        return f"{name} · {brand}" if brand else name

    def _num(v: Any, places: int = 4) -> str:
        try:
            return f"{float(v):.{places}f}"
        except (TypeError, ValueError):
            return "—"

    DISPLAY = 8  # rows shown per branch/fusion table

    # ---- EMBED ---------------------------------------------------------
    embed = EmbeddingService()
    t0 = time.time()
    query_embedding = embed.embed_query(q)
    embed_ms = int((time.time() - t0) * 1000)
    head = ", ".join(_num(x, 4) for x in query_embedding[:4])
    embed_stage = {
        "stage": "embed",
        "tag": "SEARCH · EMBED",
        "title": "Query → 1024-d vector · Cohere Embed v4",
        "sql": "",
        "columns": ["field", "value"],
        "rows": [
            ["model", settings.BEDROCK_EMBEDDING_MODEL],
            ["input_type", "search_query"],
            ["output_dimension", "1024"],
            ["normalized", "L2 (unit length)"],
            ["vector[:4]", f"[{head}, … (1024 dims)]"],
        ],
        "meta": "Asymmetric retrieval: the query is embedded as search_query, "
                "the catalog was embedded as search_document. L2-normalized so "
                "cosine distance is well-behaved.",
        "tagClass": "amber",
        "durationMs": embed_ms,
    }

    # ---- VECTOR + LEXICAL + FUSION (one live hybrid pass) --------------
    hybrid = HybridSearch(db_service)
    t0 = time.time()
    explained = await hybrid.search_explained(query=q, query_embedding=query_embedding)
    hybrid_ms = int((time.time() - t0) * 1000)
    vector_rows = explained["vector_rows"]
    fts_rows = explained["fts_rows"]
    merged = explained["merged"]
    params = explained["params"]

    vector_stage = {
        "stage": "vector",
        "tag": "SEARCH · VECTOR",
        "title": "HNSW cosine · pgvector",
        "sql": explained["vector_sql"].strip(),
        "columns": ["rank", "product", "similarity"],
        "rows": [
            [str(i + 1), _label(r), _num(r.get("similarity"))]
            for i, r in enumerate(vector_rows[:DISPLAY])
        ],
        "meta": f"Top {params['k_vector']} by cosine over the HNSW index "
                f"(<=> operator). similarity = 1 − distance; higher is closer.",
        "tagClass": "cyan",
    }

    lexical_stage = {
        "stage": "lexical",
        "tag": "SEARCH · LEXICAL",
        "title": "Full-text · ts_rank_cd",
        "sql": explained["fts_sql"].strip(),
        "columns": ["rank", "product", "ts_rank_cd"],
        "rows": [
            [str(i + 1), _label(r), _num(r.get("fts_rank_score"), 5)]
            for i, r in enumerate(fts_rows[:DISPLAY])
        ],
        "meta": "to_tsquery('english', …) with OR-joined stems over the "
                "description_tsv GIN index. ts_rank_cd is cover-density rank "
                "(matched terms close together rank higher). Empty here means "
                "the query had no lexical anchors — vector carries the recall.",
        "tagClass": "cyan",
    }

    fusion_stage = {
        "stage": "fusion",
        "tag": "SEARCH · FUSION",
        "title": f"Reciprocal Rank Fusion (k={params['rrf_k']})",
        "sql": "",
        "columns": ["product", "vec_rank", "fts_rank", "rrf_score"],
        "rows": [
            [
                _label(r),
                str(r.get("vec_rank")) if r.get("vec_rank") is not None else "—",
                str(r.get("fts_rank")) if r.get("fts_rank") is not None else "—",
                _num(r.get("rrf_score"), 5),
            ]
            for r in merged[:DISPLAY]
        ],
        "meta": f"score(d) = Σ 1 / (k + rank) over each branch d appears in, "
                f"k={params['rrf_k']}. A row ranked in BOTH branches outscores "
                f"a row ranked in only one — that consensus is the point. "
                f"'—' means the row never surfaced in that branch.",
        "tagClass": "cyan",
        "durationMs": hybrid_ms,
    }

    # ---- RERANK --------------------------------------------------------
    # Rerank the fused pool. The reordering between FUSION order (rrf_pos)
    # and RERANK order (reranked_pos) is the headline of the whole surface.
    documents = [
        f"{r.get('name','')} — {(r.get('description','') or '')[:200]} ({r.get('category','')})"
        for r in merged
    ]
    rerank_top = min(DISPLAY, len(merged))
    t0 = time.time()
    rerank_results = get_rerank_service().rerank(
        query=q, documents=documents, top_n=rerank_top,
    )
    rerank_ms = int((time.time() - t0) * 1000)

    if rerank_results:
        rerank_rows = []
        for new_pos, res in enumerate(rerank_results, start=1):
            idx = res.get("index")
            if idx is None or idx >= len(merged):
                continue
            prod = merged[idx]
            rrf_pos = idx + 1  # merged is in RRF order
            delta = rrf_pos - new_pos
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
            rerank_rows.append([
                _label(prod),
                str(rrf_pos),
                f"{new_pos} {arrow}",
                _num(res.get("relevance_score"), 4),
            ])
        rerank_meta = (
            "Cohere Rerank v3.5 reads the query + each candidate and assigns a "
            "calibrated relevance score in [0,1]. ▲/▼ shows how far a product "
            "moved from its RRF position — that movement is what the rerank "
            "spend buys you."
        )
    else:
        # Honest degrade — no fabricated scores; show RRF order unchanged.
        rerank_rows = [
            [_label(r), str(i + 1), f"{i + 1} —", "n/a"]
            for i, r in enumerate(merged[:rerank_top])
        ]
        rerank_meta = (
            "Rerank unavailable (Bedrock error) — falling back to RRF order, "
            "positions unchanged. This is the documented degrade path: a rerank "
            "outage drops Anna to plain hybrid, it does not take search down."
        )

    rerank_stage = {
        "stage": "rerank",
        "tag": "SEARCH · RERANK",
        "title": "Cohere Rerank v3.5",
        "sql": "",
        "columns": ["product", "rrf_pos", "reranked_pos", "relevance_score"],
        "rows": rerank_rows,
        "meta": rerank_meta,
        "tagClass": "amber",
        "durationMs": rerank_ms,
    }

    return {
        "query": q,
        "params": params,
        "stages": [
            embed_stage,
            vector_stage,
            lexical_stage,
            fusion_stage,
            rerank_stage,
        ],
    }


@app.get("/api/observatory/catalog")
async def observatory_catalog():
    """
    Tool catalog + agent grants for the Observatory Architecture pages.

    Powers three surfaces:
      - MCP page's tool card grid (Fired / Idle state + p50 latency)
      - Tool Registry bipartite graph (agent → tool edges with styles)
      - Tool Registry detail rows (grants per tool)

    The catalog is hardcoded here because Pellier's tools are declared
    in Python at import time — there isn't a runtime tool-metadata
    table. If this catalog moves to the ``tools`` table seeded by
    migration 001, swap this endpoint to read from it.

    ``recent_calls`` and ``last_12_turns`` would come from a real
    telemetry store. For now we report 0 / 0 — the live strip on each
    page surfaces the current turn's activity via SSE, which is what
    matters for a live demo.
    """
    # Agent definitions — matches imports in backend/agents/*.py
    agents = [
        {"name": "orchestrator", "model": "Sonnet", "role": "SONNET · ROUTES"},
        {"name": "search", "model": "Opus", "role": "OPUS · 3 GRANTS"},
        {"name": "recommendation", "model": "Opus", "role": "OPUS · 4 GRANTS"},
        {"name": "pricing", "model": "Sonnet", "role": "SONNET · 3 GRANTS"},
        {"name": "support", "model": "Opus", "role": "OPUS · 2 GRANTS"},
        {"name": "inventory", "model": "Sonnet", "role": "SONNET · 3 GRANTS"},
    ]

    # Tool catalog — headline + description + typical p50.
    # p50 values are approximate defaults; the live strip surfaces
    # actual per-call latencies via the existing tool-call SSE.
    tools = [
        {
            "name": "search_products",
            "version": "v2.1",
            "headline": "Semantic search across the catalog.",
            "description": "Natural-language query against pgvector; returns top-k matched products.",
            "p50_ms": 280,
        },
        {
            "name": "get_trending_products",
            "version": "v1.3",
            "headline": "Current bestsellers and just-ins.",
            "description": "Returns products tagged BESTSELLER / JUST_IN / EDITORS_PICK from the catalog.",
            "p50_ms": 120,
        },
        {
            "name": "browse_category",
            "version": "v1.2",
            "headline": "Browse by named category.",
            "description": "Filter-by-category read for shoppers who know what shelf they want.",
            "p50_ms": 80,
        },
        {
            "name": "compare_products",
            "version": "v1.0",
            "headline": "Side-by-side product comparison.",
            "description": "Takes two product IDs, returns attributes arranged for comparison.",
            "p50_ms": 180,
        },
        {
            "name": "get_price_analysis",
            "version": "v1.1",
            "headline": "Price trends, deals, and budget fit.",
            "description": "Analyzes pricing across a category or a specific product family.",
            "p50_ms": 220,
        },
        {
            "name": "check_inventory",
            "version": "v1.0",
            "headline": "Stock levels at a glance.",
            "description": "Inventory summary by category with low-stock flags.",
            "p50_ms": 95,
        },
        {
            "name": "get_low_stock",
            "version": "v1.0",
            "headline": "What's running low right now.",
            "description": "Reads products below the restock threshold, ordered by urgency.",
            "p50_ms": 110,
        },
        {
            "name": "restock_inventory",
            "version": "v1.0",
            "headline": "Place a restock signal.",
            "description": "Writes a restock request. Gated — requires explicit user confirmation.",
            "p50_ms": 145,
            "gated": True,
        },
        {
            "name": "get_return_policy",
            "version": "v1.0",
            "headline": "Return windows by category.",
            "description": "Policy lookup used by customer support for returns / refunds questions.",
            "p50_ms": 45,
        },
    ]

    # Agent → tool grants, derived from imports in backend/agents/*.py.
    # Style: 'solid' = everyday access, 'dashed' = read-only/rare,
    # 'gated' = requires user confirmation (espresso-dashed in the UI).
    grants = [
        # search agent imports
        {"agent": "search", "tool": "search_products", "style": "solid"},
        {"agent": "search", "tool": "browse_category", "style": "solid"},
        {"agent": "search", "tool": "compare_products", "style": "solid"},
        # recommendation agent imports
        {"agent": "recommendation", "tool": "search_products", "style": "solid"},
        {"agent": "recommendation", "tool": "get_trending_products", "style": "solid"},
        {"agent": "recommendation", "tool": "compare_products", "style": "solid"},
        {"agent": "recommendation", "tool": "browse_category", "style": "solid"},
        # pricing agent imports
        {"agent": "pricing", "tool": "get_price_analysis", "style": "solid"},
        {"agent": "pricing", "tool": "browse_category", "style": "solid"},
        {"agent": "pricing", "tool": "search_products", "style": "dashed"},
        # inventory agent imports
        {"agent": "inventory", "tool": "check_inventory", "style": "solid"},
        {"agent": "inventory", "tool": "get_low_stock", "style": "solid"},
        {"agent": "inventory", "tool": "restock_inventory", "style": "gated"},
        # support agent imports
        {"agent": "support", "tool": "get_return_policy", "style": "solid"},
        {"agent": "support", "tool": "search_products", "style": "dashed"},
    ]

    return {
        "agents": agents,
        "tools": tools,
        "grants": grants,
    }


# ---------------------------------------------------------------------------
# Persona endpoints — workshop affordance for switching curated identities.
# Reads from docs/personas-config.json; no database table for persona defs.
# ---------------------------------------------------------------------------

import pathlib as _pathlib

_PERSONAS_CONFIG_PATH = _pathlib.Path(__file__).resolve().parent / "personas-config.json"
_personas_cache: Optional[list] = None


def _load_personas() -> list:
    """Load persona definitions from docs/personas-config.json. Cached."""
    global _personas_cache
    if _personas_cache is not None:
        return _personas_cache
    try:
        raw = json.loads(_PERSONAS_CONFIG_PATH.read_text())
        _personas_cache = raw.get("personas", [])
    except Exception as e:
        logger.warning(f"Failed to load personas config: {e}")
        _personas_cache = []
    return _personas_cache


@app.get("/api/observatory/personas/reload")
async def reload_personas():
    """Dev helper — force re-read of personas-config.json."""
    global _personas_cache
    _personas_cache = None
    return {"reloaded": True, "count": len(_load_personas())}


# In-memory session → persona mapping. Lightweight — no DB table.
# Keyed by session_id; value is the persona id string.
_session_persona: dict[str, str] = {}


@app.get("/api/observatory/personas")
async def list_personas():
    """Return the three persona definitions (without internal customer_ids)."""
    personas = _load_personas()
    return [
        {
            "id": p["id"],
            "display_name": p["display_name"],
            "role_tag": p["role_tag"],
            "blurb": p["blurb"],
            "avatar_color": p["avatar_color"],
            "avatar_initial": p["avatar_initial"],
            "membership": p.get("membership", "registered"),
            "stats": p["stats"],
        }
        for p in personas
    ]


from pydantic import BaseModel as _BaseModel


class PersonaSwitchRequest(_BaseModel):
    persona_id: str
    current_session_id: Optional[str] = None


@app.post("/api/persona/switch")
async def switch_persona(req: PersonaSwitchRequest):
    """End the current session and start a new one under the given persona."""
    personas = _load_personas()
    persona = next((p for p in personas if p["id"] == req.persona_id), None)
    if not persona:
        raise HTTPException(status_code=404, detail=f"Unknown persona: {req.persona_id}")

    import uuid
    # AgentCore Memory requires session IDs ≥33 chars. Use the full
    # uuid4 hex (32 chars) plus the prefix to guarantee compliance.
    new_session_id = f"persona-{req.persona_id}-{uuid.uuid4().hex}"

    # Track the mapping so /api/persona/current can resolve it.
    _session_persona[new_session_id] = req.persona_id

    return {
        "session_id": new_session_id,
        "persona": {
            "id": persona["id"],
            "display_name": persona["display_name"],
            "role_tag": persona["role_tag"],
            "avatar_color": persona["avatar_color"],
            "avatar_initial": persona["avatar_initial"],
            "customer_id": persona["customer_id"],
            "membership": persona.get("membership", "registered"),
            "stats": persona["stats"],
        },
    }


@app.get("/api/persona/current")
async def get_current_persona(session_id: Optional[str] = Query(default=None)):
    """Return the active persona for a session, or null."""
    if not session_id or session_id not in _session_persona:
        return {"persona": None}
    persona_id = _session_persona[session_id]
    personas = _load_personas()
    persona = next((p for p in personas if p["id"] == persona_id), None)
    if not persona:
        return {"persona": None}
    return {
        "persona": {
            "id": persona["id"],
            "display_name": persona["display_name"],
            "role_tag": persona["role_tag"],
            "avatar_color": persona["avatar_color"],
            "avatar_initial": persona["avatar_initial"],
            "customer_id": persona["customer_id"],
            "membership": persona.get("membership", "registered"),
            "stats": persona["stats"],
        },
    }


# NOTE: the legacy /api/observatory/status endpoint (multi-module stub detection
# for an older workshop draft) was removed from the current required path.
# The Observatory progress strip reads GET /api/observatory/build-state instead,
# which tracks the Inventory Agent definition and check_inventory body independently.
# See routes/observatory.py::get_build_state.


# ============================================================================
# AGENT STATS ENDPOINT
# ============================================================================

@app.get("/api/agent/stats")
async def get_agent_stats():
    """Get session-level agent activity stats"""
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")
    return chat_service.get_agent_stats()


# ============================================================================
# CACHE & COST ENDPOINTS
# ============================================================================

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics — Valkey/in-memory + embedding cost data."""
    from services.embeddings import get_cache_stats as get_embedding_stats
    cache = get_cache()
    result = cache.stats() if cache else {"mode": "unavailable"}
    result["embedding"] = get_embedding_stats()
    return result


# ============================================================================
# OPENTELEMETRY TRACING ENDPOINTS
# ============================================================================

@app.get("/api/traces/status")
async def get_tracing_status():
    """Report only the in-process span capture this API can verify."""
    try:
        from opentelemetry import trace
        from services import otel_trace_extractor

        tracer_provider = trace.get_tracer_provider()
        enabled = bool(otel_trace_extractor.OTEL_WORKING)
        return {
            "enabled": enabled,
            "provider_type": type(tracer_provider).__name__,
            "exporters": ["in-memory"] if enabled else [],
            "scope": "in-process Strands execution",
            "reason": (
                None
                if enabled
                else otel_trace_extractor.OTEL_FAILURE_REASON
            ),
            "managed_runtime": (
                "AgentCore unified telemetry is verified separately by the "
                "managed provisioning receipt."
            ),
        }
    except Exception as e:
        logger.warning("Tracing status fetch failed: %s", e)
        return {"enabled": False, "error": "tracing_status_unavailable"}


@app.get("/api/traces/waterfall")
async def get_trace_waterfall(session_id: Optional[str] = Query(None)):
    """Get waterfall timing data from captured OTEL spans.

    Always returns HTTP 200 with a structured payload. When OTEL is not
    wired correctly the payload carries ``otel_enabled: False`` plus a
    ``reason`` string — the frontend renders a banner instead of the
    waterfall. See docs/troubleshooting-otel.md.
    """
    try:
        from services.otel_trace_extractor import get_waterfall_data
        return get_waterfall_data(session_id=session_id)
    except Exception as e:
        logger.error(f"get_waterfall_data raised: {e}")
        return {
            "spans": [],
            "totalMs": 0,
            "specialistRoute": "",
            "waterfall": [],
            "span_count": 0,
            "otel_enabled": False,
            "reason": (
                f"Telemetry unavailable: extractor raised {type(e).__name__}. "
                f"See docs/troubleshooting-otel.md."
            ),
        }


@app.get("/api/traces/info")
async def get_tracing_info():
    """Describe the verified local trace path without inferring managed state."""
    from services import otel_trace_extractor

    enabled = bool(otel_trace_extractor.OTEL_WORKING)
    return {
        "tracing_enabled": enabled,
        "sdk": "Strands OpenTelemetry",
        "exporters": {
            "in_memory": {
                "enabled": enabled,
                "description": "Local spans used by the Pellier waterfall",
            },
            "agentcore_unified": {
                "enabled": None,
                "description": (
                    "Managed Runtime telemetry is proved by the deployment "
                    "receipt, not inferred by this process."
                ),
            },
        },
        "captured_data": (
            [
                "Agent invocations and routing",
                "LLM calls with token usage",
                "Tool executions with results",
                "End-to-end latency",
            ]
            if enabled
            else []
        ),
        "reason": None if enabled else otel_trace_extractor.OTEL_FAILURE_REASON,
    }


# ============================================================================
# GUARDRAILS ENDPOINT
# ============================================================================

@app.post("/api/guardrails/check")
async def check_guardrails(request: Request):
    """Demo endpoint to test Bedrock Guardrails on input/output text.

    Also records the decision in ``services/guardrails_log`` so the
    Observatory Grounding page's Guardrails lane can surface a live audit
    trail alongside the Cedar policy decisions.
    """
    import time as _time
    from services.guardrails import GuardrailsService
    from services.guardrails_log import record_guardrail

    body = await request.json()
    text = body.get("text", "")
    source = body.get("source", "INPUT")
    session_id = body.get("session_id", "") or ""

    svc = GuardrailsService()
    t0 = _time.perf_counter()
    if source == "OUTPUT":
        result = svc.check_output(text)
    else:
        result = svc.check_input(text)
    latency_ms = int((_time.perf_counter() - t0) * 1000)

    record_guardrail(
        session_id=session_id or None,
        source=source,
        action=result.get("action", "NONE"),
        allowed=result.get("allowed", True),
        violations=result.get("violations", []),
        latency_ms=latency_ms,
        text_preview=text,
        mode=result.get("mode"),
    )

    pii = svc.detect_pii(text)
    return {
        **result,
        "pii_detection": pii,
        "source": source,
        "configured": svc.is_configured,
        "latency_ms": latency_ms,
    }


@app.get("/api/guardrails/decisions")
async def guardrails_decisions(session_id: str = "", limit: int = 50):
    """Return recent guardrail outcomes for a session.

    Feeds the Observatory Grounding page's Guardrails lane. Distinct from
    ``/api/agentcore/policy/decisions`` (Cedar tool-call enforcement);
    these are Bedrock content filter outcomes on the prose side.
    """
    try:
        from services.guardrails_log import get_guardrails
        decisions = get_guardrails(session_id or None, limit=max(1, min(500, int(limit))))
        return {"session_id": session_id or "_anonymous", "decisions": decisions, "count": len(decisions)}
    except Exception as e:
        logger.warning(f"Guardrails decisions fetch failed: {e}")
        return {
            "session_id": session_id,
            "decisions": [],
            "count": 0,
            "error": "guardrail_history_unavailable",
        }


# ============================================================================
# CHAOS MODE (Error Handling & Resilience Demo)
# ============================================================================

_chaos_mode = False
_chaos_fail_rate = 0.3  # 30% failure rate when chaos mode active

@app.post("/api/dev/chaos")
async def toggle_chaos_mode(request: Request):
    """Toggle chaos mode for resilience testing"""
    global _chaos_mode
    body = await request.json()
    _chaos_mode = body.get("enabled", not _chaos_mode)
    return {"chaos_mode": _chaos_mode, "fail_rate": _chaos_fail_rate}

@app.get("/api/dev/chaos")
async def get_chaos_status():
    """Get current chaos mode status"""
    return {"chaos_mode": _chaos_mode, "fail_rate": _chaos_fail_rate}


# ============================================================================
# AGENTCORE POLICY ENDPOINTS (Cedar)
# ============================================================================

@app.get("/api/agentcore/policy/list")
async def list_policies(operator: Dict[str, Any] = Depends(require_operator)):
    """List the Cedar policies attached to the managed AgentCore Policy
    engine (Gateway-enforced, ENFORCE mode).

    Reads the managed engine via boto3 ``bedrock-agentcore-control``
    ``list_policies`` keyed on ``AGENTCORE_POLICY_ENGINE_ID``. The old
    local fake-Cedar ``PolicyService`` was removed — enforcement is now
    entirely at the Gateway, so this is a pure read of the managed
    engine's Cedar statements.
    """
    try:
        from services.managed_policy import list_managed_policies
        result = list_managed_policies()
        return {"policies": result.get("policies", []), "source": result.get("source")}
    except Exception as e:
        logger.warning(f"Failed to list policies: {e}")
        return {"policies": [], "error": "managed_policy_unavailable"}


# NOTE: the former POST /api/agentcore/policy/check route was removed.
# It evaluated actions against the local fake-Cedar engine (also removed).
# The managed AgentCore Policy engine evaluates Cedar at the Gateway at
# tool-call time and exposes no client-side "evaluate this action" API,
# so there is nothing for a runtime check endpoint to call.


@app.get("/api/agentcore/memory/ltm")
async def memory_ltm(customer_id: str = ""):
    """Return LTM facts for a persona, ranked by recency.

    Reads the ``pellier.customer_episodic_seed`` fixture table via
    ``services/episodic_memory.fetch_episodic_seed`` — the same source
    chat.py consults when building the persona preamble. The
    MemoryArchPage uses this to replace its hard-coded STUB_LTM_FACTS
    so attendees see persona-tailored history (Marco's linen notes,
    Anna's gift cues, Theo's slow-craft signals) the moment they pick
    a persona.

    Returns ``{customer_id, facts: [{text, ts_offset_days, relative}]}``.
    Anonymous or unknown customers return an empty facts list — the
    frontend falls back to the stub in that case so the page stays
    populated for fresh visitors.
    """
    if not customer_id or customer_id == "anonymous":
        return {"customer_id": customer_id or "", "facts": [], "source": "anonymous"}
    try:
        from services.episodic_memory import fetch_episodic_seed, _format_relative
        if db_service is None:
            return {"customer_id": customer_id, "facts": [], "source": "db-unavailable"}
        rows = await fetch_episodic_seed(db_service, customer_id, limit=10)
        facts = [
            {
                "text": r["summary_text"],
                "ts_offset_days": r["ts_offset_days"],
                "relative": _format_relative(r["ts_offset_days"]),
            }
            for r in rows
        ]
        return {"customer_id": customer_id, "facts": facts, "source": "aurora"}
    except Exception as e:
        logger.warning(f"Memory LTM fetch failed for {customer_id}: {e}")
        return {
            "customer_id": customer_id,
            "facts": [],
            "source": "error",
            "error": "memory_unavailable",
        }


@app.get("/api/agentcore/memory/status")
async def memory_status():
    """Return whether an ACTIVE AgentCore Memory is backing the SDK path.

    The MemoryArchPage in the Observatory reads this to show an honest
    banner — either 'Live: AgentCore Memory (id=...)' or 'Fallback:
    in-process dict; set AGENTCORE_MEMORY_ID to enable LIVE'. An ID and
    importable SDK are not sufficient: the control-plane resource must
    exist and report ACTIVE.
    """
    try:
        from services.agentcore_memory import probe_memory_backend_status

        return await asyncio.to_thread(probe_memory_backend_status)
    except Exception as e:
        logger.warning(f"Memory status fetch failed: {e}")
        return {
            "live": False,
            "source": "in-process-dict",
            "error": "memory_status_unavailable",
        }


@app.get("/api/agentcore/gateway/status")
async def gateway_status():
    """Return the effective Gateway wiring for the current backend.

    The Observatory MCP / Tool Registry tabs use this to show whether tools
    are being discovered via MCP (Gateway configured) or loaded via
    direct @tool imports (fallback). The ``source`` field is the
    human-readable label shown next to the tool list.
    """
    try:
        from config import settings
        gateway_url = getattr(settings, "AGENTCORE_GATEWAY_URL", None) or ""
        if gateway_url:
            return {
                "configured": True,
                "source": "mcp-discovery",
                "gateway_url": gateway_url,
                "fallback_reason": None,
            }
        return {
            "configured": False,
            "source": "in-process-imports",
            "gateway_url": "",
            "fallback_reason": "AGENTCORE_GATEWAY_URL env var not set",
        }
    except Exception as e:
        logger.warning(f"Gateway status fetch failed: {e}")
        return {
            "configured": False,
            "source": "in-process-imports",
            "error": "gateway_status_unavailable",
        }


@app.get("/api/agentcore/policy/decisions")
async def policy_decisions(
    session_id: str = "",
    limit: int = 50,
    operator: Dict[str, Any] = Depends(require_operator),
):
    """Return recent managed-rail policy decisions for a session.

    The gate is now the managed AgentCore Policy engine at the Gateway,
    which emits ALLOW/DENY decisions to CloudWatch rather than a
    queryable API. Instead of fabricating a decisions store, we surface
    immutable ``pellier.governed_receipts`` rows. Unlike execution audits,
    those receipts contain both explicit ALLOW and DENY outcomes and are
    scoped to the verified caller. See ``services/managed_policy.recent_decisions``."""
    try:
        from services.managed_policy import recent_decisions
        return await recent_decisions(
            db_service,
            principal_sub=operator["sub"],
            session_id=session_id or None,
            limit=limit,
        )
    except Exception as e:
        logger.warning(f"Policy decisions fetch failed: {e}")
        return {
            "session_id": session_id,
            "decisions": [],
            "count": 0,
            "error": "policy_history_unavailable",
        }


@app.get("/api/observatory/receipts/{turn_id}")
async def governed_turn_receipt(
    turn_id: str,
    operator: Dict[str, Any] = Depends(require_operator),
):
    """Read one durable turn receipt only when it belongs to the caller."""
    from services.governed_turn_receipt import get_turn_receipt

    receipt = await get_turn_receipt(
        db_service, turn_id=turn_id, principal_sub=operator["sub"]
    )
    if receipt is None:
        raise HTTPException(status_code=404, detail="receipt_not_found")
    return receipt


# ============================================================================
# AGENTCORE ENDPOINTS
# ============================================================================

@app.get("/api/agentcore/memories")
async def agentcore_memories(user=Depends(get_current_user)):
    """Get stored memories for authenticated user"""
    if not user:
        return {"memories": [], "message": "Sign in to view memories"}
    try:
        from services.agentcore_memory import get_user_memories
        memories = get_user_memories(user["sub"])
        return {"memories": memories, "user": user["email"]}
    except Exception as e:
        logger.warning(f"Failed to fetch memories: {e}")
        return {"memories": [], "error": "managed_memory_unavailable"}


@app.get("/api/agentcore/gateway/tools")
async def agentcore_gateway_tools(user=Depends(get_current_user)):
    """List tools registered in the AgentCore Gateway MCP server.

    JWT passthrough: forwards the caller's Cognito token so the live tool
    list is fetched under their identity. Anonymous callers get [] from a
    JWT-protected Gateway (the "skipped" state), which is intentional.
    """
    try:
        from services.agentcore_gateway import list_gateway_tools
        _token = (user or {}).get("access_token") if isinstance(user, dict) else None
        tools = list_gateway_tools(access_token=_token)
        return {"tools": tools, "gateway_url": settings.AGENTCORE_GATEWAY_URL or "not configured"}
    except Exception as e:
        logger.warning(f"Failed to list gateway tools: {e}")
        return {"tools": [], "error": "managed_gateway_unavailable"}


@app.get("/api/agentcore/runtime/status")
async def agentcore_runtime_status():
    """Get AgentCore Runtime execution status"""
    runtime_endpoint = settings.AGENTCORE_RUNTIME_ENDPOINT
    if runtime_endpoint:
        if runtime_endpoint.startswith("arn:"):
            runtime_id = runtime_endpoint.rsplit("/", 1)[-1]
            return {
                "mode": "agentcore",
                "endpoint": runtime_endpoint,
                "runtime_id": runtime_id,
                "healthy": True,
                "status": "configured",
            }

        # Check health of remote runtime
        try:
            import requests as req
            resp = await asyncio.to_thread(req.get, f"{runtime_endpoint}/health", timeout=3)
            return {
                "mode": "agentcore",
                "endpoint": runtime_endpoint,
                "healthy": resp.status_code == 200,
                "latency_ms": int(resp.elapsed.total_seconds() * 1000),
            }
        except Exception:
            return {
                "mode": "agentcore",
                "endpoint": runtime_endpoint,
                "healthy": False,
            }
    return {
        "mode": "local",
        "endpoint": f"http://localhost:{settings.PORT}",
        "healthy": True,
    }


# ============================================================================
# AGENTCORE GOING FURTHER ENDPOINTS
# ============================================================================

@app.get("/api/agentcore/memories/episodes")
async def get_episodic_memories(query: str, user=Depends(get_current_user)):
    """Search episodic memories for relevant past experiences"""
    if not user:
        return {"episodes": [], "message": "Sign in to search episodic memories"}
    try:
        from services.agentcore_memory import search_episodic_memories
        episodes = search_episodic_memories(user["sub"], query)
        return {"episodes": episodes, "query": query, "user": user["email"]}
    except Exception as e:
        logger.warning(f"Failed to search episodic memories: {e}")
        return {"episodes": [], "error": "episodic_memory_unavailable"}


# NOTE: the former POST /api/agentcore/policy/create route was removed.
# Cedar policy creation is now owned by the declarative AgentCore CLI project,
# not a runtime endpoint.


@app.post("/api/agentcore/analytics")
async def analytics_query(request: Request):
    """Run a data analytics query using Code Interpreter agent"""
    try:
        from services.code_interpreter import create_analytics_agent
        body = await request.json()
        prompt = body.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
        agent = create_analytics_agent()
        if agent is None:
            return {
                "response": "Code Interpreter is not available. Ensure AGENTCORE_RUNTIME_ENDPOINT is configured and strands-agents-tools is installed.",
                "available": False,
            }
        result = str(agent(prompt))
        return {"response": result, "available": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics query failed: {e}")
        raise HTTPException(status_code=500, detail="internal_error")


# ============================================================================
# SPA STATIC MOUNT + CLIENT-ROUTE CATCH-ALL
# ============================================================================
# Mounted LAST so every @app.get/@app.post above wins on path conflict.
# The SPA owns ``/`` and every client-side route (``/workshop``,
# ``/storyboard``, ``/discover``, etc.); ``/api/*`` routes remain
# API-side.
#
# The ``/assets`` mount serves Vite's hashed bundle output with a
# browser-friendly cache header — hashed filenames make long cache
# lifetimes safe. ``/fonts`` serves the self-hosted font files we ship
# from ``public/fonts/`` (no Google Fonts runtime dependency — corporate
# networks that block fonts.gstatic.com don't break the workshop).
#
# The catch-all handler falls back to ``index.html`` for anything that
# doesn't map to an /api/* path or a real file in dist/. React Router
# picks up from there.

if FRONTEND_DIST.is_dir():
    _assets_url = (
        "/assets" if SPA_MOUNT_PATH == "/" else f"{SPA_MOUNT_PATH}/assets"
    )
    _fonts_url = (
        "/fonts" if SPA_MOUNT_PATH == "/" else f"{SPA_MOUNT_PATH}/fonts"
    )
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount(_assets_url, StaticFiles(directory=assets_dir), name="assets")
    fonts_dir = FRONTEND_DIST / "fonts"
    if fonts_dir.is_dir():
        app.mount(_fonts_url, StaticFiles(directory=fonts_dir), name="fonts")

    # Client-route catch-all. Explicitly does NOT match /api/* or /ws/*
    # — those already resolve against the routers above and a 404 from
    # here would mask a real routing bug. We also refuse to serve files
    # that escape dist/ via .. segments.
    #
    # IMPORTANT: do not register any routes after this catch-all — its
    # ``{full_path:path}`` pattern matches everything under SPA_MOUNT_PATH
    # and would shadow them. The dynamic mount path makes ordering
    # invisible from a quick read; if you need a new route under the
    # SPA prefix, add it ABOVE this block.
    _catchall_url = (
        "/{full_path:path}"
        if SPA_MOUNT_PATH == "/"
        else f"{SPA_MOUNT_PATH}/{{full_path:path}}"
    )

    @app.get(_catchall_url, include_in_schema=False)
    async def spa_fallback(full_path: str):
        # When SPA_MOUNT_PATH = "/", /api/foo arrives here as "api/foo"
        # and we must reject it so the real router 404s aren't masked.
        # When SPA_MOUNT_PATH = "/app", /app/api/foo arrives as
        # "api/foo" too — but in that case the real API lives at
        # /api/foo (no /app prefix), so the SPA correctly owns
        # /app/api/* and we let it fall through to index.html.
        if SPA_MOUNT_PATH == "/" and (
            full_path.startswith("api/") or full_path.startswith("ws/")
        ):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = SPA_STATIC_FILES.get(full_path)
        if candidate is not None:
            return FileResponse(candidate)
        # Anything else → SPA entry. React Router handles the rest.
        return FileResponse(
            FRONTEND_DIST / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    logger.info(
        "SPA mounted at %s (FRONTEND_DIST=%s)", SPA_MOUNT_PATH, FRONTEND_DIST
    )
else:
    logger.warning(
        "⚠️  Frontend dist not found at %s — API will run, SPA will 404. "
        "Run `cd pellier/frontend && npm run build` to produce it.",
        FRONTEND_DIST,
    )


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
