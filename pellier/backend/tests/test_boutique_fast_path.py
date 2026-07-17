from services.chat import _allows_human_handoff


def test_ordinary_catalog_query_cannot_trigger_stylist_handoff() -> None:
    assert not _allows_human_handoff(
        "What linen do you have for 10 days in Goa?"
    )


def test_explicit_stylist_capstone_keeps_handoff_available() -> None:
    assert _allows_human_handoff(
        "Connect me with a real Pellier stylist, not product cards."
    )


def test_sensitive_request_keeps_handoff_available() -> None:
    assert _allows_human_handoff(
        "I need advice about cultural dress for this wedding."
    )
