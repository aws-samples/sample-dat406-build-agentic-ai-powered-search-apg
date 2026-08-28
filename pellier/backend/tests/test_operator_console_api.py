"""Tests for ``/api/operator`` — the Pellier Operator clienteling desk.

Two behaviours matter most here, and both are about failing in the right
direction:

* **Reads are open, writes are gated.** A blank 401 on the whole console makes
  the desk useless on a box with no Cognito wired, so the GETs must work
  unauthenticated. The writes must NOT: an optional-auth write handler is an
  unauthenticated write path wearing an authenticated signature.
* **A policy decision is an answer, not an error.** ``policy_blocked`` comes
  back as 200 with the envelope intact. Only an unexpected failure is a 5xx.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from routes import operator as operator_module  # noqa: E402


CLIENT_ROWS = [
    {
        "customer_id": "CUST-AMARA", "name": "Amara Okonkwo",
        "membership": "maison", "spend_12mo": 18900.00,
        "preferences_summary": "Investment pieces.",
        "order_count": 5, "order_value": 3495.00, "last_order_at": None,
    },
    {
        "customer_id": "CUST-JESSICA", "name": "Jessica Nakamura",
        "membership": "circle", "spend_12mo": 3940.00,
        "preferences_summary": "Open return dispute.",
        "order_count": 5, "order_value": 958.79, "last_order_at": None,
    },
    {
        "customer_id": "CUST-MARCO", "name": "Marco",
        "membership": "maison", "spend_12mo": 9240.00,
        "preferences_summary": "Natural fibers.",
        "order_count": 7, "order_value": 1200.00, "last_order_at": None,
    },
]

ORDER_ROWS = [
    {
        "order_id": 1, "product_id": "41", "quantity": 1, "placed_at": None,
        "product_name": "Coral Lacquer Catchall", "brand": "Pellier Maison",
        "price": 325.36, "image_url": "/products/house-coral-lacquer-catchall.png",
    },
    {
        "order_id": 2, "product_id": "42", "quantity": 2, "placed_at": None,
        "product_name": "Luxury Bath Robe, Sage", "brand": "NestWell",
        "price": 107.30, "image_url": "/products/house-sage-bath-robe.png",
    },
]

TICKET_ROWS = [
    {
        "ticket_id": "TKT-2026-3015", "subject": "Refund amount disputed",
        "status": "pending", "channel": "chat", "last_note": "Awaiting decision.",
        "opened_at": None, "resolved_at": None,
    },
    {
        "ticket_id": "TKT-2025-9001", "subject": "Delivery rescheduled",
        "status": "resolved", "channel": "phone", "last_note": "Confirmed.",
        "opened_at": None, "resolved_at": None,
    },
]

def approved_credit_review(
    customer_id: str = "CUST-JESSICA",
    amount_cents: int = 4000,
    reason: str = "Goodwill: shipping",
) -> Dict[str, Any]:
    """An approved review matching a credit request, as the fake would store it.

    The legacy `/actions/issue-credit` endpoint is no longer a way around the
    review: it requires an approved review whose fingerprint matches these exact
    parameters. Building one here keeps the older behavioural tests meaningful
    instead of deleting them.
    """
    import sys as _sys
    from pathlib import Path as _Path

    _backend = _Path(__file__).resolve().parents[1]
    if str(_backend) not in _sys.path:
        _sys.path.insert(0, str(_backend))
    from services.business_logic import write_request_hash

    return {
        "review_id": 77,
        "customer_id": customer_id,
        "action": "issue_credit",
        "args": {
            "customer_id": customer_id,
            "amount_cents": amount_cents,
            "reason": reason,
        },
        "status": "approved",
        "action_hash": write_request_hash(
            "issue_credit",
            customer_id=customer_id,
            amount_cents=amount_cents,
            reason=reason,
        ),
        "source_turn_id": "turn-" + ("a" * 32),
        "order_id": None,
        "execution_turn_id": None,
        "decided_by": "operator-verified-sub",
    }


CREDIT_ROWS = [
    {
        "credit_id": 7, "amount_cents": 4000, "currency": "USD",
        "reason": "Goodwill: shipping", "issued_by": "operator-sub",
        "created_at": None,
    },
]


class FakeDb:
    """Routes queries by a distinctive fragment of each SELECT."""

    def __init__(
        self,
        *,
        fail: str | None = None,
        approved_review: Dict[str, Any] | None = None,
        customer_subject: str | None = "sub-customer",
    ) -> None:
        self.fail = fail
        self.calls: List[str] = []
        self.approved_review = approved_review
        self.customer_subject = customer_subject

    async def fetch_all(self, query: str, *params: Any) -> List[Dict[str, Any]]:
        self.calls.append(query)
        if self.fail and self.fail in query:
            raise RuntimeError(f"induced failure for {self.fail}")
        if "support_tickets" in query:
            return list(TICKET_ROWS)
        if "store_credits" in query:
            return list(CREDIT_ROWS)
        if "FROM pellier.orders o" in query:
            return list(ORDER_ROWS)
        return list(CLIENT_ROWS)

    async def fetch_one(self, query: str, *params: Any) -> Dict[str, Any] | None:
        self.calls.append(query)
        if self.fail and self.fail in query:
            raise RuntimeError(f"induced failure for {self.fail}")
        # The legacy /actions/* endpoints now require an approved review whose
        # fingerprint matches the request, so the fake serves one on demand.
        if "FROM pellier.approvals a" in query and "a.action_hash = %s" in query:
            if not self.approved_review:
                return None
            return {**self.approved_review, "action_hash": params[0]}
        if "FROM pellier.principal_customers" in query:
            return {"principal_sub": self.customer_subject} if self.customer_subject else None
        if query.strip().startswith("UPDATE pellier.approvals"):
            return {"execution_turn_id": params[0]}
        if "SELECT execution_turn_id" in query:
            return {"execution_turn_id": "turn-" + ("c" * 32)}
        wanted = params[0] if params else None
        for row in CLIENT_ROWS:
            if row["customer_id"] == wanted:
                return dict(row)
        return None


def build_client(db: FakeDb, *, operator: Dict[str, Any] | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(operator_module.router)
    app.dependency_overrides[operator_module.get_db_service] = lambda: db
    if operator is not None:
        app.dependency_overrides[operator_module.require_operator] = lambda: operator
    return TestClient(app)


# ---------------------------------------------------------------------------
# Reads are open
# ---------------------------------------------------------------------------

def test_the_book_lists_clients_without_a_token() -> None:
    client = build_client(FakeDb())
    response = client.get("/api/operator/clients")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["byMembership"] == {"registered": 0, "circle": 1, "maison": 2}
    assert [c["name"] for c in body["clients"]] == [
        "Amara Okonkwo", "Jessica Nakamura", "Marco",
    ]


def test_the_book_exposes_a_portrait_slug_and_flags_only_real_heroes() -> None:
    """`personaId` drives a storefront handoff; promising one that does not
    exist would be a dead button."""
    body = build_client(FakeDb()).get("/api/operator/clients").json()
    by_id = {c["customerId"]: c for c in body["clients"]}

    assert by_id["CUST-JESSICA"]["slug"] == "jessica"
    assert by_id["CUST-JESSICA"]["personaId"] is None
    assert by_id["CUST-MARCO"]["personaId"] == "marco"


def test_client_record_carries_orders_tickets_and_credits() -> None:
    client = build_client(FakeDb())
    body = client.get("/api/operator/clients/CUST-JESSICA").json()

    assert body["client"]["name"] == "Jessica Nakamura"
    assert body["client"]["membership"] == "circle"
    assert len(body["orders"]) == 2
    assert len(body["tickets"]) == 2
    assert len(body["credits"]) == 1

    # Derived from the rows actually returned, not a second aggregate query.
    assert body["client"]["orderCount"] == 2
    assert body["client"]["orderValue"] == pytest.approx(325.36 + 107.30 * 2)
    assert body["client"]["openTicketCount"] == 1
    assert body["client"]["creditBalanceCents"] == 4000
    assert body["client"]["creditBalance"] == "40.00"


def test_credit_amount_is_formatted_once_in_the_api() -> None:
    """No surface should re-derive currency from cents."""
    body = build_client(FakeDb()).get("/api/operator/clients/CUST-JESSICA").json()
    assert body["credits"][0]["amount"] == "40.00"
    assert body["credits"][0]["amountCents"] == 4000


def test_unknown_client_is_404_not_an_empty_record() -> None:
    response = build_client(FakeDb()).get("/api/operator/clients/CUST-NOBODY")
    assert response.status_code == 404


def test_an_unrecognised_membership_never_reaches_the_console() -> None:
    assert operator_module._normalise_membership("platinum") == "registered"
    assert operator_module._normalise_membership(None) == "registered"
    assert operator_module._normalise_membership("MAISON") == "maison"


def test_a_broken_tickets_query_empties_that_section_not_the_record() -> None:
    """An operator cannot act on a 500. Losing one section beats losing all."""
    client = build_client(FakeDb(fail="support_tickets"))
    response = client.get("/api/operator/clients/CUST-JESSICA")

    assert response.status_code == 200
    body = response.json()
    assert body["tickets"] == []
    assert len(body["orders"]) == 2       # unaffected
    assert body["client"]["openTicketCount"] == 0


def test_an_unreadable_book_is_503_naming_the_missing_migration() -> None:
    client = build_client(FakeDb(fail="FROM pellier.customers c"))
    response = client.get("/api/operator/clients")

    assert response.status_code == 503
    assert "018_client_book" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Writes are gated
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path, payload",
    [
        (
            "/api/operator/actions/issue-credit",
            {"customerId": "CUST-JESSICA", "amountCents": 4000, "reason": "Goodwill"},
        ),
        (
            "/api/operator/actions/resolve-return",
            {"customerId": "CUST-JESSICA", "productId": 41, "reason": "damaged"},
        ),
    ],
)
def test_writes_reject_an_unauthenticated_caller(path: str, payload: dict) -> None:
    """No operator override installed, so the real require_operator runs."""
    response = build_client(FakeDb()).post(path, json=payload)
    assert response.status_code in (401, 403), response.status_code


def test_credit_above_the_ceiling_is_rejected_before_any_database_work() -> None:
    db = FakeDb()
    client = build_client(db, operator={"sub": "operator-1"})
    response = client.post(
        "/api/operator/actions/issue-credit",
        json={"customerId": "CUST-JESSICA", "amountCents": 50_001, "reason": "too much"},
    )
    assert response.status_code == 422
    assert db.calls == []


def test_credit_requires_a_reason() -> None:
    client = build_client(FakeDb(), operator={"sub": "operator-1"})
    response = client.post(
        "/api/operator/actions/issue-credit",
        json={"customerId": "CUST-JESSICA", "amountCents": 4000, "reason": ""},
    )
    assert response.status_code == 422


def test_resolve_return_rejects_a_reason_outside_the_canonical_set() -> None:
    client = build_client(FakeDb(), operator={"sub": "operator-1"})
    response = client.post(
        "/api/operator/actions/resolve-return",
        json={"customerId": "CUST-JESSICA", "productId": 41, "reason": "vibes"},
    )
    assert response.status_code == 422
    assert "damaged" in response.json()["detail"]


def test_the_allowed_reason_set_matches_business_logic() -> None:
    """Mirrored constants drift. Compare them instead of trusting the copy."""
    source = (BACKEND / "services" / "business_logic.py").read_text()
    for reason in operator_module.ALLOWED_RETURN_REASONS:
        assert f'"{reason}"' in source, reason


def test_a_credit_is_attributed_to_the_verified_operator(monkeypatch) -> None:
    """The operator is the ACTOR on a credit, and that is what gets recorded.

    Attribution and data scope are different questions. `issued_by` names the
    person who authorised the money movement; Row-Level Security scopes the
    customer's rows. Recording the operator here is correct precisely because it
    is not the RLS subject.
    """
    captured: Dict[str, Any] = {}

    class FakeLogic:
        def __init__(self, db: Any) -> None:
            self.db = db

        async def issue_credit(self, **kwargs: Any) -> Dict[str, Any]:
            captured.update(kwargs)
            return {"status": "success", "credit_id": 9, "idempotent_replay": False}

    import services.business_logic as bl

    monkeypatch.setattr(bl, "BusinessLogic", FakeLogic)
    client = build_client(
        FakeDb(approved_review=approved_credit_review()),
        operator={"sub": "operator-verified-sub"},
    )
    response = client.post(
        "/api/operator/actions/issue-credit",
        json={
            "customerId": "CUST-JESSICA", "amountCents": 4000,
            "reason": "Goodwill: shipping",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["actedBy"] == "operator-verified-sub"
    assert captured["issued_by"] == "operator-verified-sub"
    assert body["reviewId"] == 77


def test_the_write_key_is_derived_so_a_retry_cannot_pay_twice(monkeypatch) -> None:
    """The reverse of the old contract, and deliberately so.

    This endpoint used to mint a fresh `operator-credit-<uuid4>` per request, so
    a double-click or an HTTP retry issued a *second* credit. Now the key is
    derived from the confirmed review and its fingerprint, so every retry of the
    same approved action claims the same key and collapses through the existing
    `write_operations` claim / replay / conflict machinery.

    Two genuinely different credits still get different keys, because a different
    amount or reason is a different fingerprint.
    """
    keys: List[str] = []

    class FakeLogic:
        def __init__(self, db: Any) -> None:
            pass

        async def issue_credit(self, **kwargs: Any) -> Dict[str, Any]:
            keys.append(kwargs["idempotency_key"])
            return {"status": "success"}

    import services.business_logic as bl

    monkeypatch.setattr(bl, "BusinessLogic", FakeLogic)
    client = build_client(
        FakeDb(approved_review=approved_credit_review()), operator={"sub": "operator-1"}
    )
    payload = {
        "customerId": "CUST-JESSICA", "amountCents": 4000,
        "reason": "Goodwill: shipping",
    }
    client.post("/api/operator/actions/issue-credit", json=payload)
    client.post("/api/operator/actions/issue-credit", json=payload)

    assert len(keys) == 2
    assert keys[0] == keys[1], (
        "a retry produced a different write key, so the same confirmed credit "
        "could be paid twice"
    )
    assert keys[0].startswith("operator-review:77:")


def test_a_privileged_mutation_without_a_confirmed_review_is_refused() -> None:
    """The bypass closure.

    A second HTTP route that performs the same mutation without a review is not a
    convenience; it is the control undone. An operator token alone is no longer
    enough.
    """
    client = build_client(FakeDb(approved_review=None), operator={"sub": "operator-1"})
    response = client.post(
        "/api/operator/actions/issue-credit",
        json={"customerId": "CUST-JESSICA", "amountCents": 4000, "reason": "x"},
    )
    assert response.status_code == 409
    assert "no_confirmed_review" in response.json()["detail"]


def test_a_confirmed_review_for_different_parameters_does_not_authorise_this_one() -> None:
    """Any approved review is not enough — it must match these parameters.

    The lookup is by action fingerprint, so a review confirmed for $40 cannot be
    used to execute $400.
    """
    client = build_client(
        FakeDb(approved_review=approved_credit_review(amount_cents=4000)),
        operator={"sub": "operator-1"},
    )
    response = client.post(
        "/api/operator/actions/issue-credit",
        json={"customerId": "CUST-JESSICA", "amountCents": 40000, "reason": "Goodwill: shipping"},
    )
    # The fake echoes back whatever hash was queried, so the guard's own
    # fingerprint comparison inside execute_confirmed_review is what refuses it.
    assert response.status_code == 409


def test_policy_blocked_is_an_answer_not_an_http_error(monkeypatch) -> None:
    class FakeLogic:
        def __init__(self, db: Any) -> None:
            pass

        async def issue_credit(self, **kwargs: Any) -> Dict[str, Any]:
            return {"status": "policy_blocked", "message": "exceeds the ceiling"}

    import services.business_logic as bl

    monkeypatch.setattr(bl, "BusinessLogic", FakeLogic)
    client = build_client(
        FakeDb(approved_review=approved_credit_review()), operator={"sub": "operator-1"}
    )
    response = client.post(
        "/api/operator/actions/issue-credit",
        json={
            "customerId": "CUST-JESSICA", "amountCents": 4000,
            "reason": "Goodwill: shipping",
        },
    )

    assert response.status_code == 200
    assert response.json()["result"]["status"] == "policy_blocked"


# ---------------------------------------------------------------------------
# SQL that a fake DB cannot validate
# ---------------------------------------------------------------------------

def test_no_query_carries_a_bare_percent_literal() -> None:
    """psycopg parses `%` as a placeholder even with no parameters bound.

    `WHERE c.id LIKE 'CUST-%'` therefore raised before the statement ever
    reached Postgres, and the fake DB in this file could not catch it because
    it never parses SQL. This guard does what the fake cannot.
    """
    constants = {
        name: value
        for name, value in vars(operator_module).items()
        if name.isupper() and name.endswith("_SELECT") and isinstance(value, str)
    }
    assert constants, "no _SELECT constants found — the naming moved"

    for name, sql in constants.items():
        # Only the legal placeholders are removed. Comments are deliberately
        # NOT stripped: psycopg does not skip them either, so a percent sign
        # inside a SQL comment breaks the query just as surely. An earlier
        # version of this test stripped comments and passed while the live
        # query still raised.
        stripped = sql.replace("%s", "").replace("%b", "").replace("%t", "")
        assert "%" not in stripped, (
            f"{name} contains a bare % literal, which psycopg rejects as a "
            "malformed placeholder. Use left()/strpos() instead of LIKE, or "
            "escape it as %%."
        )


def test_the_book_query_still_excludes_the_alias_and_fresh_rows() -> None:
    """Dropping LIKE must not quietly widen who appears in the book."""
    sql = operator_module._BOOK_SELECT
    assert "left(c.id, 5) = 'CUST-'" in sql
    assert "c.id <> 'CUST-FRESH'" in sql
