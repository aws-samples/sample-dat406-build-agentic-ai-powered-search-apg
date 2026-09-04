"""An unauthenticated caller may only act as a seeded demo persona.

``customer_id`` arrives on the request body and is unauthenticated by
design, so persona selection works without a login. It then scopes memory
reads and reaches the support specialist's ``process_return`` write. The
ownership check inside that write compares the *claimed* customer against
their orders, which answers "did this customer order this product" and
never "is the caller this customer" — so without an allow-list, any
well-formed ``CUST-*`` value is an accepted identity assertion.
"""

from __future__ import annotations

import pytest

from services import persona_identity


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    persona_identity.reset_cache()
    yield
    persona_identity.reset_cache()


def test_seeded_personas_are_claimable() -> None:
    claimable = persona_identity.claimable_customer_ids()

    assert claimable, "personas-config.json should ship seeded customers"
    assert {"CUST-MARCO", "CUST-ANNA", "CUST-THEO"} <= claimable
    for customer_id in sorted(claimable):
        assert (
            persona_identity.assert_claimable_customer_id(customer_id)
            == customer_id
        )


def test_arbitrary_customer_id_is_rejected() -> None:
    # Matches the ChatRequest pattern ^CUST-[A-Z0-9-]{1,40}$, so schema
    # validation alone lets this through.
    with pytest.raises(persona_identity.CustomerIdNotClaimable):
        persona_identity.assert_claimable_customer_id("CUST-VICTIM-9001")


def test_missing_persona_config_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No persona config must mean no claim, never an unchecked claim."""
    monkeypatch.setattr(persona_identity, "load_personas", lambda: [])

    with pytest.raises(persona_identity.PersonasUnavailable):
        persona_identity.assert_claimable_customer_id("CUST-MARCO")


def test_chat_stream_rejects_an_unclaimable_customer_before_streaming() -> None:
    """The rejection must be an HTTP error, not a broken SSE stream."""
    from fastapi.testclient import TestClient

    import app as app_module

    client = TestClient(app_module.app)
    response = client.post(
        "/api/chat/stream",
        json={
            "message": "Please refund my order",
            "customer_id": "CUST-VICTIM-9001",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "customer_id_not_claimable"
