"""Three identities per turn, kept deliberately distinct.

A workshop needs persona switching: an attendee clicks "Marco" and the
storefront tunes its copy, recommendations, and memory. That affordance is
useful and should stay. What must not happen is the demo persona becoming
the *authorization* principal, because then a UI dropdown decides what a
request is allowed to do.

Three fields, three jobs:

``principal_sub``
    The verified security identity — the Cognito ``sub`` from a validated
    token. This is the only field policy and ownership checks may use. It
    is ``None`` for an anonymous shopper, and ``None`` means "no verified
    identity", never "trust the persona instead".

``shopper_customer_id``
    The authorized domain identity — which customer's orders, returns, and
    preferences this turn may touch. Derived from the verified principal
    when one exists; only a demo persona in demo mode.

``demo_persona_id``
    Pure UI simulation context. Drives copy, curation, and which fixture
    story renders. Never an input to an authorization decision.

The distinction has a concrete failure mode behind it. AgentCore Memory
namespaces durable records by actor; if the namespace is keyed on the
persona while the token says someone else, one attendee's persona switch
reads another's memory, and the audit row names a principal that never
made the request.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

USERNAME_TO_CUSTOMER_ID = {
    "marco": "CUST-MARCO",
    "anna": "CUST-ANNA",
    "theo": "CUST-THEO",
}


def customer_id_for_verified_username(username: Optional[str]) -> Optional[str]:
    """Map a verified Cognito username to its seeded Aurora customer."""
    normalized = str(username or "").strip().casefold()
    return USERNAME_TO_CUSTOMER_ID.get(normalized)


@dataclass(frozen=True)
class TurnIdentity:
    """The resolved identities for one turn.

    Attributes:
        principal_sub: Verified Cognito ``sub``, or ``None`` when
            anonymous. The only field valid for policy decisions.
        shopper_customer_id: Customer whose domain data this turn may
            read, or ``None``.
        demo_persona_id: UI persona label, or ``None``. Never
            authoritative.
        authenticated: True when a verified principal is present.
        persona_is_simulated: True when a persona is active without a
            verified principal backing it — i.e. the customer scope comes
            from a UI selection, not from a token.
    """

    principal_sub: Optional[str] = None
    shopper_customer_id: Optional[str] = None
    demo_persona_id: Optional[str] = None
    authenticated: bool = False
    persona_is_simulated: bool = False

    def memory_actor(self) -> str:
        """Return the actor id AgentCore Memory should namespace under.

        Prefers the verified principal. A demo persona never overrides a
        real identity: doing so would let a UI dropdown read another
        attendee's durable records. Falls back to the persona only when
        there is no verified principal at all — which is the demo case,
        and is reported as ``persona_is_simulated``.
        """
        if self.principal_sub:
            return self.principal_sub
        if self.demo_persona_id:
            return f"persona-{self.demo_persona_id}"
        return "anonymous"

    def authorization_principal(self) -> Optional[str]:
        """Return the only identity a policy check may use.

        ``None`` means unauthenticated. Callers must treat that as "deny
        or require login", never as "fall back to the persona".
        """
        return self.principal_sub

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for the turn payload and evidence surfaces."""
        return {
            "principalSub": self.principal_sub,
            "shopperCustomerId": self.shopper_customer_id,
            "demoPersonaId": self.demo_persona_id,
            "authenticated": self.authenticated,
            "personaIsSimulated": self.persona_is_simulated,
            "memoryActor": self.memory_actor(),
        }


def resolve_turn_identity(
    *,
    user: Optional[Dict[str, Any]] = None,
    requested_customer_id: Optional[str] = None,
) -> TurnIdentity:
    """Split one request's identities into their three distinct roles.

    Args:
        user: The verified-user dict from ``services.auth``
            (``{sub, email, given_name, access_token}``), or ``None`` for
            an anonymous caller. May also carry a ``customer_id`` that the
            storefront merged in from the active persona.
        requested_customer_id: A customer id supplied by the request body.
            Treated as a *demo persona* selection, not as an identity
            claim — the caller does not get to assert who they are.

    Returns:
        A :class:`TurnIdentity`. When a verified principal exists it always
        wins for authorization and memory namespacing; the persona only
        colours the experience.
    """
    user = user or {}
    principal_sub = (user.get("sub") or "").strip() or None
    persona_id = str(requested_customer_id or "").strip() or None

    # The customer scope follows the verified principal when we have one.
    # Without a principal, a persona selection is the only scope available
    # and the turn is explicitly marked as simulated.
    if principal_sub:
        shopper_customer_id = customer_id_for_verified_username(
            user.get("username")
        )
        persona_is_simulated = False
    else:
        shopper_customer_id = persona_id
        persona_is_simulated = persona_id is not None

    if persona_is_simulated and persona_id:
        logger.debug(
            "Turn scoped to simulated persona %s (no verified principal); "
            "this scope is not valid for authorization",
            persona_id,
        )

    return TurnIdentity(
        principal_sub=principal_sub,
        shopper_customer_id=shopper_customer_id,
        demo_persona_id=persona_id,
        authenticated=principal_sub is not None,
        persona_is_simulated=persona_is_simulated,
    )
