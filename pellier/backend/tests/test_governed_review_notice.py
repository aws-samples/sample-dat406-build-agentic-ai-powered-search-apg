"""The shopper must be told a person will confirm, whatever the prose says.

The measured defect
-------------------

On the shopper rail the governed boundary declines every mutation, opens an operator
review, and returns a machine envelope. ``agents/customer_service_agent.py`` instructs
the specialist to say two things in that case:

  1. that it found the order and prepared the request, naming the piece;
  2. that a Pellier operator will confirm it before anything is changed.

It even supplies the worked example. On 2026-08-27, against the live stack, the model
said the first and dropped the second:

    "I'm sorry to hear your Wabi-Sabi Bowl arrived chipped. I found your order and
     prepared the damaged-return request for the bowl."

A shopper reading that reasonably concludes the return is filed. The guarantee that
nothing changed until a person agrees is the entire claim of this rail, and it was
riding on model compliance.

So the refusal envelope now carries the sentence, and the surface renders it as its own
event. The prompt keeps its instruction — belt and braces — but the notice no longer
depends on it.
"""

from __future__ import annotations

import json

import pytest

from pellier_copy import GOVERNED_ACTION_NOT_PERFORMED, GOVERNED_REVIEW_PENDING
from services import chat as CHAT
from services.agent_tools import _managed_rail_required, _review_pending_envelope


@pytest.fixture
def governed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the flagship format for this module.

    `conftest.py` deliberately runs with no `WORKSHOP_FORMAT`, so
    `requires_managed_rail` returns False and there is no refusal to test. That default
    is right for a hermetic suite — it is also exactly the fail-open that let a shopper
    execute a governed write directly, which is why `app.py` now announces the format at
    startup and `test_managed_rail_readiness.py` asserts it.
    """
    from config import settings

    monkeypatch.setattr(settings, "WORKSHOP_FORMAT", "governed", raising=False)


def test_the_refusal_envelope_carries_the_non_promising_sentence(governed: None) -> None:
    """The DEFAULT message promises nothing, because no review exists yet.

    `_managed_rail_required` is called before any review is attempted, so it cannot claim
    one. The guarantee arrives through `_review_pending_envelope` and only with an id.
    """
    envelope = json.loads(_managed_rail_required("initiate_return") or "{}")
    assert envelope["message"] == GOVERNED_ACTION_NOT_PERFORMED
    assert "review_id" not in envelope


def test_the_guarantee_requires_a_real_review_id(governed: None) -> None:
    """P1-03. The sentence follows the row, not the intention."""
    base = _managed_rail_required("initiate_return") or "{}"
    upgraded = json.loads(_review_pending_envelope(base, 44))
    assert upgraded["message"] == GOVERNED_REVIEW_PENDING
    assert upgraded["review_id"] == 44
    # Machine fields survive the upgrade.
    assert upgraded["error"] == "managed_rail_required"
    assert upgraded["tool"] == "initiate_return"


def test_a_non_reviewable_mutation_never_claims_a_review(governed: None) -> None:
    """`restock_inventory` requires the managed rail and is NOT in REVIEWABLE_ACTIONS.

    It used to receive the guarantee anyway: a shopper asking to restock was told a
    specialist would confirm a review that was never created.
    """
    from services.operator_review import REVIEWABLE_ACTIONS

    assert "restock_inventory" not in REVIEWABLE_ACTIONS
    envelope = json.loads(_managed_rail_required("restock_inventory") or "{}")
    assert envelope["message"] == GOVERNED_ACTION_NOT_PERFORMED
    assert "waiting" not in envelope["message"].lower()
    assert "confirm it" not in envelope["message"]


def test_every_managed_tool_gets_the_same_honest_default(governed: None) -> None:
    from services.execution_rail import mutation_tools

    for tool in sorted(mutation_tools()):
        envelope = json.loads(_managed_rail_required(tool) or "{}")
        assert envelope["message"] == GOVERNED_ACTION_NOT_PERFORMED, tool


def test_a_non_governed_format_produces_no_refusal_at_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The builders lineage serves this tool in process, so there is nothing to refuse.

    `builders` is pinned explicitly. It used to be the default, and relying on that
    default was the release bug: a governed deployment that set nothing served governed
    writes on the in-process rail. The default on this branch is now `governed`, so a
    test about the OTHER lineage has to say so.
    """
    from config import settings

    monkeypatch.setattr(settings, "WORKSHOP_FORMAT", "builders", raising=False)
    assert _managed_rail_required("initiate_return") is None


def test_the_envelope_keeps_its_machine_fields(governed: None) -> None:
    """`is_boundary_refusal` matches on `error`; the rail name makes it diagnosable."""
    envelope = json.loads(_managed_rail_required("initiate_return") or "{}")
    assert envelope["error"] == "managed_rail_required"
    assert envelope["tool"] == "initiate_return"
    assert envelope["required_rail"] == "gateway-mcp"

    from services import operator_review as rv

    assert rv.is_boundary_refusal(envelope) is True


def test_a_permitted_tool_gets_no_envelope(governed: None) -> None:
    assert _managed_rail_required("check_inventory") is None


def test_both_sentences_say_what_did_and_did_not_happen() -> None:
    """The refusal taxonomy in VOICE.md: what happened, what did not, who acts next."""
    for text in (GOVERNED_REVIEW_PENDING, GOVERNED_ACTION_NOT_PERFORMED):
        assert "nothing about your order has" in text.lower()
        assert "pellier specialist" in text.lower()
    assert "waiting" in GOVERNED_REVIEW_PENDING.lower()
    # The default must not imply a queued decision.
    assert "waiting" not in GOVERNED_ACTION_NOT_PERFORMED.lower()
    assert "prepared" not in GOVERNED_ACTION_NOT_PERFORMED.lower()
    # No em dash, no internal vocabulary. A shopper never sees the rail or the tool.
    assert "—" not in text
    for internal in ("managed_rail", "gateway", "Cedar", "policy", "rail", "tool"):
        assert internal.lower() not in text.lower(), internal


def test_the_scanner_finds_a_bare_envelope() -> None:
    found = CHAT._scan_for_review_pending(
        json.dumps({"error": "managed_rail_required", "tool": "initiate_return"})
    )
    assert found is not None and found["tool"] == "initiate_return"


def test_the_scanner_finds_an_embedded_envelope() -> None:
    """A specialist wrapper appends the payload after its prose."""
    body = (
        "I found your order and prepared the request.\n\n```json\n"
        + json.dumps({"error": "managed_rail_required", "tool": "initiate_return"})
        + "\n```"
    )
    found = CHAT._scan_for_review_pending(body)
    assert found is not None and found["tool"] == "initiate_return"


def test_the_scanner_ignores_everything_else() -> None:
    for other in (
        "",
        "plain prose with no envelope",
        json.dumps({"status": "success", "return_id": 37}),
        json.dumps({"error": "something_else"}),
        json.dumps({"type": "escalation", "contact": "x"}),
    ):
        assert CHAT._scan_for_review_pending(other) is None


def test_the_emission_falls_back_to_the_canonical_sentence() -> None:
    """An envelope from an older code path has no `message`; the notice still holds."""
    source = CHAT.__dict__["_scan_for_review_pending"].__doc__ or ""
    assert "dropped the second" in source
    import inspect

    stream = inspect.getsource(CHAT)
    assert '"type": "review_pending"' in stream
    assert "or GOVERNED_REVIEW_PENDING" in stream


def test_products_are_not_suppressed_for_a_pending_review() -> None:
    """Unlike an escalation, the answer is not the handoff.

    The shopper asked about a piece they own; a replacement shelf beside the notice is
    useful. Suppressing it would be borrowing the escalation rule for a different case.
    """
    import inspect

    stream = inspect.getsource(CHAT)
    emission = stream[stream.index('"type": "review_pending"'):]
    emission = emission[: emission.index("# Now send buffered products")]
    assert "products_buffered = []" not in emission


def test_the_specialist_prompt_still_asks_for_the_sentence() -> None:
    """Belt and braces. The notice does not license removing the instruction.

    Prose that says it naturally reads better than prose plus a bolted-on notice, so the
    prompt keeps asking; the notice is what makes it guaranteed rather than likely.
    """
    from agents import customer_service_agent as cs

    prompt = cs.__dict__.get("_SUPPORT_AGENT_PROMPT") or ""
    if not prompt:
        prompt = "\n".join(
            str(v) for v in vars(cs).values() if isinstance(v, str) and len(v) > 400
        )
    assert "operator will confirm it before anything is" in prompt
    assert "managed_rail_required" in prompt
