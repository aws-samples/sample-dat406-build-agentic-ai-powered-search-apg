"""One execution contract shared by the storefront and the managed route.

Before this module existed, ``USE_AGENTCORE_RUNTIME`` only affected
``/api/agent/chat``. The Boutique posts to ``/api/chat/stream``, so the
storefront kept working entirely in-process even when the workshop had
just finished provisioning Runtime, Gateway, and Policy — an attendee
could watch the shopper experience succeed without any of it touching the
governed chain they were being asked to reason about.

This module is the single place that answers two questions for both
endpoints:

  1. **Which rail should execute this turn?** — :func:`resolve_rail`
  2. **Which rail actually executed it?** — the ``rail`` field that every
     completed turn now carries.

Rails
-----

``in-process``
    Strands specialists in this process, tools calling ``agent_tools``
    against Aurora directly. The builders path and the default.

``runtime``
    The managed AgentCore Runtime was selected. Inside the container the
    orchestrator's tools run over the Gateway, so a successful managed
    turn reports ``gateway-mcp`` (the entrypoint sets that itself);
    ``runtime`` alone means selected-but-not-yet-confirmed.

``gateway-mcp``
    Confirmed: the managed Runtime executed and reported that its tools
    ran over Gateway MCP under the caller's identity.

Fail-closed posture
-------------------

:func:`resolve_rail` returns a :class:`RailDecision` that can be
*unavailable*. When the managed rail is requested but the request cannot
satisfy it — no verified caller token, no configured Runtime endpoint —
the decision says so with a reason instead of quietly falling back to
in-process execution. A governed write must never be served by a rail the
operator believes was bypassed, and a governed read that silently
downgrades teaches the wrong lesson about what was proven.

The caller decides what to do with an unavailable decision: the managed
route fails the turn, while the storefront may degrade to a clearly
labelled read-only in-process turn (``degraded=True``) so a demo does not
hard-stop mid-sentence. Either way the turn reports what happened.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)

RAIL_IN_PROCESS = "in-process"
RAIL_RUNTIME = "runtime"
RAIL_GATEWAY_MCP = "gateway-mcp"

# Reasons a requested managed rail cannot serve a turn. These are distinct
# from a Cedar DENY: nothing was authorized or refused here, the rail
# simply is not usable for this request.
REASON_NO_TOKEN = "authentication_required"
REASON_NOT_CONFIGURED = "runtime_not_configured"


@dataclass(frozen=True)
class RailDecision:
    """The rail selected for one turn, and why.

    Attributes:
        rail: The rail to execute on — one of ``in-process`` or
            ``runtime``. A confirmed ``gateway-mcp`` is reported by the
            managed entrypoint after execution, not predicted here.
        managed_requested: True when ``USE_AGENTCORE_RUNTIME`` asked for
            the managed rail, regardless of whether it is usable.
        available: False when the managed rail was requested but cannot
            serve this request.
        reason: Machine code explaining an unavailable decision.
    """

    rail: str
    managed_requested: bool
    available: bool = True
    reason: Optional[str] = None

    @property
    def is_managed(self) -> bool:
        """True when this decision routes to the managed Runtime."""
        return self.rail == RAIL_RUNTIME

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for the turn's completion payload."""
        return {
            "rail": self.rail,
            "managedRequested": self.managed_requested,
            "available": self.available,
            "reason": self.reason,
        }


def resolve_rail(*, auth_token: Optional[str] = None) -> RailDecision:
    """Decide which rail should execute this turn.

    Args:
        auth_token: The caller's raw Cognito access token, when present.
            The managed Runtime authorizer rejects anonymous requests, so
            a turn without one cannot reach the managed rail.

    Returns:
        A :class:`RailDecision`. When ``USE_AGENTCORE_RUNTIME`` is false
        the decision is plain ``in-process`` and ``available``. When it is
        true but the request cannot satisfy the managed rail, the decision
        is ``in-process`` with ``available=False`` and a ``reason`` — the
        caller must decide whether to fail or to degrade visibly.
    """
    if not settings.USE_AGENTCORE_RUNTIME:
        return RailDecision(rail=RAIL_IN_PROCESS, managed_requested=False)

    if not settings.AGENTCORE_RUNTIME_ENDPOINT:
        logger.error(
            "USE_AGENTCORE_RUNTIME=true but AGENTCORE_RUNTIME_ENDPOINT is unset"
        )
        return RailDecision(
            rail=RAIL_IN_PROCESS,
            managed_requested=True,
            available=False,
            reason=REASON_NOT_CONFIGURED,
        )

    if not auth_token:
        logger.warning(
            "Managed rail requested without a Cognito access token; "
            "the Runtime authorizer would reject this turn"
        )
        return RailDecision(
            rail=RAIL_IN_PROCESS,
            managed_requested=True,
            available=False,
            reason=REASON_NO_TOKEN,
        )

    return RailDecision(rail=RAIL_RUNTIME, managed_requested=True)


def requires_managed_rail(tool_name: str) -> bool:
    """True when ``tool_name`` may only run on the managed rail.

    Mutation-capable tools are governed: in the flagship format they must
    travel through Gateway and managed Policy so the Cedar decision and
    the ``tool_audit`` row line up. Read tools may serve in-process.

    Args:
        tool_name: The logical tool name, e.g. ``process_return``.
    """
    if str(getattr(settings, "WORKSHOP_FORMAT", "")).lower() != "governed":
        return False
    return tool_name in _MUTATION_TOOLS


# Mutation-capable tools. Kept in one place so the fail-closed rule and
# the Gateway capability tiers cannot drift apart.
_MUTATION_TOOLS = frozenset(
    {
        "process_return",
        "restock_shelf",
        "escalate_to_stylist",
    }
)


def degraded_notice(decision: RailDecision) -> Dict[str, Any]:
    """Describe a degraded turn for the completion payload.

    A degraded turn is one the operator asked to run on the managed rail
    that ran in-process instead. It reports which capabilities were
    removed so the response is never mistaken for a governed turn.
    """
    return {
        "degraded": True,
        "reason": decision.reason,
        "rail": decision.rail,
        "capabilitiesRemoved": sorted(_MUTATION_TOOLS),
        "explanation": (
            "The managed AgentCore rail was requested but is unavailable "
            "for this request, so mutation-capable tools were withheld and "
            "this turn ran read-only in-process. This is not a Cedar DENY."
        ),
    }
