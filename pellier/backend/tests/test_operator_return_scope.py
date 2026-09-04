"""The Operator human checkpoint must survive Lab 4 writing to the same table.

Lab 4's identity matrix (`scripts/prove_identity_boundary.py`) targets
CUST-JESSICA and, on its ALLOW case, writes a real `pellier.returns` row for
whichever product she ordered first. The Operator service-recovery walkthrough
is built on the opposite premise: her ticket asserts a return that the
authoritative table does not carry.

Those two shared one unscoped predicate, `asserts_return and not returns`. Any
return row for the customer -- including Lab 4's, on an unrelated product --
flipped it, and the human checkpoint stopped rendering. Not replayed: absent.
Nothing required the labs to run in a particular order, and only a full
governed reset restored it.

Scoping the conflict to the products the ticket names fixes the collision and
is independently more truthful: a return for the reed diffuser has never been
evidence about a disputed refund on the catchall.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from routes.operator import _ticket_named_product_ids  # noqa: E402

# The seeded Jessica case: migration 019 logs a return for the catchall and the
# robe; migration 018 gives her five orders.
JESSICA_TICKETS: List[Dict[str, Any]] = [
    {
        "ticketId": "TKT-2026-3015",
        "subject": "Return received, refund amount disputed",
        "lastNote": (
            "Return logged for the catchall and the robe. Client expected a "
            "full refund including original shipping."
        ),
        "status": "pending",
    }
]

JESSICA_ORDERS: List[Dict[str, Any]] = [
    {"productId": "P-001", "productName": "Leather Catchall Tray"},
    {"productId": "P-002", "productName": "Waffle Cotton Robe"},
    {"productId": "P-003", "productName": "Stoneware Pour-Over Set"},
    {"productId": "P-004", "productName": "Quilted Down Vest"},
    {"productId": "P-005", "productName": "Merino Crew Sweater"},
]


def _evidence(returns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Recompute the flag exactly as routes.operator does."""
    asserts_return = any(
        "return" in (t.get("subject", "") + " " + t.get("lastNote", "")).lower()
        for t in JESSICA_TICKETS
    )
    disputed = _ticket_named_product_ids(JESSICA_TICKETS, JESSICA_ORDERS)
    unresolved = [
        r for r in returns if not disputed or r.get("productId") in disputed
    ]
    return {
        "unconfirmedReturnAssertion": asserts_return and not unresolved,
        "disputedProductIds": sorted(disputed),
    }


class TestTicketScoping:
    def test_the_ticket_names_only_the_products_it_mentions(self) -> None:
        named = _ticket_named_product_ids(JESSICA_TICKETS, JESSICA_ORDERS)
        assert named == {"P-001", "P-002"}

    def test_resolved_tickets_do_not_name_products(self) -> None:
        """A closed ticket is history, not an open dispute."""
        closed = [dict(JESSICA_TICKETS[0], status="resolved")]
        assert _ticket_named_product_ids(closed, JESSICA_ORDERS) == set()

    def test_short_and_generic_tokens_do_not_match(self) -> None:
        """Matching on 'bath' or 'set' would pull in the whole catalog."""
        tickets = [
            {"subject": "Bath set query", "lastNote": "", "status": "open"}
        ]
        orders = [
            {"productId": "P-100", "productName": "Pellier Luxury Bath Set"},
            {"productId": "P-101", "productName": "Sage Bath Towel"},
        ]
        assert _ticket_named_product_ids(tickets, orders) == set()


class TestCollisionWithLabFour:
    def test_the_checkpoint_stands_at_baseline(self) -> None:
        assert _evidence([])["unconfirmedReturnAssertion"] is True

    def test_lab_four_return_on_an_unrelated_product_does_not_erase_it(self) -> None:
        """The regression this file exists for.

        Lab 4 writes a return for the lowest-id product Jessica owns. Under the
        old unscoped predicate this emptied the Operator checkpoint.
        """
        lab_four_row = {"productId": "P-003", "productName": "Stoneware Pour-Over Set"}
        assert _evidence([lab_four_row])["unconfirmedReturnAssertion"] is True

    def test_a_return_for_a_disputed_product_does_resolve_it(self) -> None:
        """The flag must still fall when the dispute is genuinely answered."""
        catchall_row = {"productId": "P-001", "productName": "Leather Catchall Tray"}
        assert _evidence([catchall_row])["unconfirmedReturnAssertion"] is False

    def test_several_unrelated_returns_still_do_not_resolve_it(self) -> None:
        rows = [
            {"productId": "P-003", "productName": "Stoneware Pour-Over Set"},
            {"productId": "P-004", "productName": "Quilted Down Vest"},
            {"productId": "P-005", "productName": "Merino Crew Sweater"},
        ]
        assert _evidence(rows)["unconfirmedReturnAssertion"] is True

    def test_the_surface_can_name_what_is_disputed(self) -> None:
        assert _evidence([])["disputedProductIds"] == ["P-001", "P-002"]


class TestFailureDirection:
    def test_an_unmatchable_ticket_falls_back_to_any_return(self) -> None:
        """Narrowing to an empty set must not auto-resolve every dispute.

        When the ticket names no recognisable product we cannot scope, so the
        conservative reading is the old one: any return answers it. The
        alternative -- treating "no named products" as "nothing is disputed" --
        would resolve disputes the desk has not looked at.
        """
        tickets = [
            {"subject": "Return question", "lastNote": "No item named.", "status": "open"}
        ]
        orders = JESSICA_ORDERS
        disputed = _ticket_named_product_ids(tickets, orders)
        assert disputed == set()

        returns = [{"productId": "P-003"}]
        unresolved = [
            r for r in returns if not disputed or r.get("productId") in disputed
        ]
        # With no scope available, the return counts, so the flag falls.
        assert unresolved
