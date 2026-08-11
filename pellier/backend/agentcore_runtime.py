"""
AgentCore Runtime - deployment entrypoint for the managed execution path.

Wraps the dispatcher for execution in an AgentCore Runtime container. This
file is the BYO entrypoint deployed by the pinned @aws/agentcore Node CLI
(CDK-based — https://github.com/aws/agentcore-cli). Bootstrap renders one
declarative project containing Runtime, Memory, Gateway, targets, and Policy,
then runs ``agentcore validate`` and ``agentcore deploy`` before participants
arrive. In-room they inspect the project and invoke via
``POST /api/agent/chat`` with ``USE_AGENTCORE_RUNTIME=true``.

Inside the container the orchestrator's tools run over the managed AgentCore
GATEWAY (MCP over streamable HTTP, JWT passthrough) — NOT in-process. The
in-process specialists in ``agents/`` call ``services.agent_tools``, whose
database service is injected only by the FastAPI startup hook
(``app.py:set_db_service``); that hook never runs here, so every in-process
tool would fail with "Database service not initialized" (box-verified
2026-06-12 — the smoke's only symptom was the LLM apologizing about a
"temporary database issue"). The caller's Cognito access token reaches this
handler because provisioning allowlists the ``Authorization`` header on the
runtime (``requestHeaderAllowlist`` patch), so identity passes through:
shopper → Runtime → Gateway → Cedar → MCP Lambda, one JWT end to end.

Deploy (bootstrap / instructor):
    python3 scripts/provision_agentcore_end_to_end.py --repo-path "$PWD"

The provisioner renders ``.agentcore-project/pellier/agentcore/agentcore.json``
and invokes the pinned CLI. AgentCore CDK injects discovery variables for
project resources into this Runtime.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Bridge CLI-injected resource discovery names BEFORE the first `config`
# import. Settings are built once at import time.
_gateway_url = (
    os.environ.get("AGENTCORE_GATEWAY_PELLIER_GATEWAY_URL")
    or os.environ.get("MCP_GATEWAY_URL")
)
if _gateway_url and not os.environ.get("AGENTCORE_GATEWAY_URL"):
    os.environ["AGENTCORE_GATEWAY_URL"] = _gateway_url
if os.environ.get("MEMORY_PELLIERMEMORY_ID") and not os.environ.get(
    "AGENTCORE_MEMORY_ID"
):
    os.environ["AGENTCORE_MEMORY_ID"] = os.environ["MEMORY_PELLIERMEMORY_ID"]
if os.environ.get("AGENT_MODEL_ID") and not os.environ.get("BEDROCK_ROUTER_MODEL"):
    os.environ["BEDROCK_ROUTER_MODEL"] = os.environ["AGENT_MODEL_ID"]

try:
    from bedrock_agentcore.runtime import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()

    def _bearer_token_from(context: Any) -> Optional[str]:
        """Extract the caller's raw Cognito access token, if forwarded.

        The runtime data plane forwards only allowlisted headers; provisioning
        allowlists ``Authorization``, and the SDK surfaces it on the
        ``RequestContext`` passed as the handler's second argument (and in
        ``BedrockAgentCoreContext`` as a fallback for older call shapes).
        """
        headers: Dict[str, str] = {}
        if context is not None and getattr(context, "request_headers", None):
            headers = context.request_headers or {}
        if not headers:
            try:
                from bedrock_agentcore.runtime import BedrockAgentCoreContext

                headers = BedrockAgentCoreContext.get_request_headers() or {}
            except Exception:  # pragma: no cover - SDK surface drift
                headers = {}
        auth = headers.get("Authorization") or headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip() or None
        return None

    @app.entrypoint
    def invoke(payload: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """Handle the prompt, identity/session ids, and prior Memory history."""
        prompt = (payload or {}).get("prompt", "")
        session_id = (payload or {}).get("session_id", "runtime-session")
        user_id = (payload or {}).get("user_id", "anonymous")
        history = (payload or {}).get("history", [])

        # Tools execute only through Gateway MCP under the caller's identity.
        # A managed Runtime invocation must never degrade into local tools.
        rail = "runtime"
        access_token = _bearer_token_from(context)
        if not access_token:
            logger.warning(
                "Managed Runtime invocation rejected: Cognito bearer token missing"
            )
            return {
                "error": "authentication_required",
                "products": [],
                "rail": rail,
            }

        if not os.environ.get("AGENTCORE_GATEWAY_URL"):
            logger.error("Managed Runtime invocation rejected: Gateway URL missing")
            return {
                "error": "managed_gateway_unavailable",
                "products": [],
                "rail": rail,
            }

        from services.agentcore_gateway import create_gateway_dispatcher

        dispatcher = create_gateway_dispatcher(access_token=access_token)
        if dispatcher is None:
            return {
                "error": "managed_gateway_unavailable",
                "products": [],
                "rail": rail,
            }
        rail = "gateway-mcp"

        try:
            dispatcher.trace_attributes = {
                "session.id": session_id,
                "user.id": user_id or "anonymous",
                "runtime": "agentcore-managed",
                "workshop": "pellier",
            }
        except Exception:  # pragma: no cover
            pass

        from services.conversation_context import build_conversation_prompt

        response = dispatcher(build_conversation_prompt(prompt, history))
        return {
            "response": str(response),
            "products": [],
            "rail": rail,
            "intent": dispatcher.last_intent,
            "specialist": dispatcher.last_specialist,
            "gateway_tools": list(dispatcher.last_tool_names),
        }

except ImportError:
    logger.info("bedrock-agentcore not installed — Runtime entrypoint disabled")
    app = None  # type: ignore[misc, assignment]


if __name__ == "__main__":
    if app:
        app.run()
    else:
        print("Install bedrock-agentcore to run: pip install bedrock-agentcore")
