"""Bounds on the customer identity a caller may assert.

Persona selection in Pellier is unauthenticated by design: an attendee
picks Marco, Anna, or Theo without signing in, and the chosen persona's
``customer_id`` scopes memory reads and the support specialist's
ownership-checked ``process_return`` write.

That affordance is safe only while it stays bounded to the seeded demo
customers. An unbounded ``customer_id`` is an unauthenticated identity
assertion: any well-formed ``CUST-*`` value would let an anonymous caller
act as a customer they never proved a relationship to. The ownership check
inside ``BusinessLogic.process_return`` does not close this, because it
validates the *claimed* customer against their orders — it answers "did
this customer order this product", never "is the caller this customer".

The allow-list here is the missing half of that pair.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

PERSONAS_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "personas-config.json"
)

_personas_cache: Optional[List[Any]] = None


class CustomerIdNotClaimable(ValueError):
    """The caller asserted a customer id that is not a seeded persona."""


class PersonasUnavailable(RuntimeError):
    """Persona configuration could not be read, so no claim can be checked."""


def load_personas() -> List[Any]:
    """Return the persona definitions, cached after the first read.

    Returns:
        The list under ``personas`` in ``personas-config.json``, or an
        empty list when the file is missing or unreadable.
    """
    global _personas_cache
    if _personas_cache is not None:
        return _personas_cache
    try:
        raw = json.loads(PERSONAS_CONFIG_PATH.read_text())
        _personas_cache = raw.get("personas", [])
    except Exception as exc:
        logger.warning("Failed to load personas config: %s", exc)
        _personas_cache = []
    return _personas_cache


def reset_cache() -> None:
    """Drop the cached personas so the next read hits disk."""
    global _personas_cache
    _personas_cache = None


def claimable_customer_ids() -> set[str]:
    """Return the customer ids a caller is permitted to act as."""
    return {
        str(persona["customer_id"])
        for persona in load_personas()
        if persona.get("customer_id")
    }


def assert_claimable_customer_id(customer_id: str) -> str:
    """Return ``customer_id`` when it names a seeded demo persona.

    Args:
        customer_id: The customer id asserted by the caller.

    Returns:
        The same id, unchanged, when the claim is allowed.

    Raises:
        PersonasUnavailable: Persona config is empty, so no claim can be
            validated. Callers must fail closed rather than accept anything.
        CustomerIdNotClaimable: The id is well-formed but is not one of the
            seeded personas.
    """
    claimable = claimable_customer_ids()
    if not claimable:
        raise PersonasUnavailable(
            "persona configuration is empty; cannot validate a customer claim"
        )
    if customer_id not in claimable:
        logger.warning(
            "Rejected unclaimable customer_id %r (allowed: %s)",
            customer_id,
            sorted(claimable),
        )
        raise CustomerIdNotClaimable(customer_id)
    return customer_id
