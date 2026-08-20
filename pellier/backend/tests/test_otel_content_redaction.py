"""Model prompts and completions must not ride out on exported spans.

Verified against the live `aws/spans` log group: before this was wired, a
`gen_ai.user.message` event carried the shopper's question verbatim into
CloudWatch. A turn is reconstructable from `turn_id`, identity, policy
verdict, and execution outcome, so the content is payload in broadly
readable telemetry rather than in the access-controlled ledger.

Two properties carry real risk of silent regression and are pinned here:

  1. **Append, never replace.** `OTEL_SEMCONV_STABILITY_OPT_IN` carries
     unrelated convention tokens. Clobbering it would quietly change
     behavior an operator chose.
  2. **Do not override an explicit allow-list.** If someone has already
     named which attributes stay readable, that is a deliberate decision.

The ordering requirement — this must run before `StrandsTelemetry()` because
`Tracer.__init__` reads the variable once — cannot be asserted from here; it
is enforced by placement in `app.py`'s lifespan and called out there.
"""

from __future__ import annotations

import importlib
import pathlib
import re

import pytest

from services.otel_content_redaction import (
    SEMCONV_ENV,
    apply_model_content_redaction,
    redaction_already_configured,
)


def test_enabling_sets_the_redact_all_token(monkeypatch):
    """An empty allow-list is how Strands expresses "redact everything"."""
    monkeypatch.delenv(SEMCONV_ENV, raising=False)

    result = apply_model_content_redaction(enabled=True)

    assert result == "gen_ai_unredacted_attributes="
    assert redaction_already_configured(result) is True


def test_existing_convention_tokens_are_preserved(monkeypatch):
    """Clobbering the variable would change conventions the operator chose."""
    monkeypatch.setenv(SEMCONV_ENV, "gen_ai_latest_experimental,gen_ai_span_attributes_only")

    result = apply_model_content_redaction(enabled=True)

    tokens = result.split(",")
    assert "gen_ai_latest_experimental" in tokens
    assert "gen_ai_span_attributes_only" in tokens
    assert "gen_ai_unredacted_attributes=" in tokens


def test_an_explicit_allow_list_is_left_alone(monkeypatch):
    """A named allow-list is a decision; redact-all would override it."""
    configured = "gen_ai_unredacted_attributes=gen_ai.output.*"
    monkeypatch.setenv(SEMCONV_ENV, configured)

    result = apply_model_content_redaction(enabled=True)

    assert result == configured


def test_disabled_leaves_the_environment_untouched(monkeypatch):
    monkeypatch.setenv(SEMCONV_ENV, "gen_ai_latest_experimental")

    result = apply_model_content_redaction(enabled=False)

    assert result == "gen_ai_latest_experimental"
    assert redaction_already_configured(result) is False


def test_disabled_on_a_clean_environment_adds_nothing(monkeypatch):
    monkeypatch.delenv(SEMCONV_ENV, raising=False)

    assert apply_model_content_redaction(enabled=False) == ""
    assert redaction_already_configured("") is False


def test_repeated_application_does_not_duplicate_the_token(monkeypatch):
    """Startup may run more than once in a process (tests, reload)."""
    monkeypatch.delenv(SEMCONV_ENV, raising=False)

    apply_model_content_redaction(enabled=True)
    result = apply_model_content_redaction(enabled=True)

    assert result.count("gen_ai_unredacted_attributes=") == 1


def test_whitespace_in_the_variable_is_tolerated(monkeypatch):
    """Strands strips tokens, so a hand-edited .env with spaces still works."""
    monkeypatch.setenv(SEMCONV_ENV, " gen_ai_latest_experimental , ")

    result = apply_model_content_redaction(enabled=True)

    assert result == "gen_ai_latest_experimental,gen_ai_unredacted_attributes="


# ---------------------------------------------------------------------------
# The switch actually redacts — asserted against Strands' own tracer
# ---------------------------------------------------------------------------


def _strands_supports_attribute_redaction() -> bool:
    """Return True when the installed Strands carries the redaction hook.

    A capability probe rather than a version comparison: what the assertions
    below need is `Tracer._redact`, and probing for it keeps the check honest
    if the feature moves.
    """
    try:
        tracer_module = importlib.import_module("strands.telemetry.tracer")
    except Exception:  # pragma: no cover - absent Strands is its own failure
        return False
    return hasattr(tracer_module, "REDACTED_VALUE") and hasattr(
        tracer_module.Tracer, "_redact"
    )


# A developer box whose site-packages predates the pinned version would fail
# these two rather than the tests being wrong, which sends the next reader
# hunting a bug in this module. Skip with the install that fixes it, and let
# `test_the_lock_pins_a_strands_version_that_can_redact` hold the invariant —
# that one cannot skip.
requires_redaction_support = pytest.mark.skipif(
    not _strands_supports_attribute_redaction(),
    reason=(
        "installed strands-agents has no Tracer._redact; the box installs "
        "requirements.lock, which pins a version that does"
    ),
)


def test_the_lock_pins_a_strands_version_that_can_redact():
    """The capability probe can skip. This is what makes the skip safe.

    Redaction is only as real as the version the box installs. A lock
    regeneration that resolved Strands backwards would disable it silently:
    `apply_model_content_redaction` would still set the token, still log
    success, and content would export anyway. So the floor is asserted against
    the lock, where a regression is a diff rather than a runtime surprise.

    1.48.0 is the version verified to carry the hook, not necessarily the
    first — raise the floor only against a version actually checked.
    """
    lock = (pathlib.Path(__file__).resolve().parents[1] / "requirements.lock").read_text()
    pinned = re.search(r"^strands-agents==(\d+)\.(\d+)\.(\d+)", lock, re.MULTILINE)

    assert pinned, "requirements.lock does not pin strands-agents"
    assert (int(pinned.group(1)), int(pinned.group(2))) >= (1, 48), (
        f"lock pins strands-agents {pinned.group(0).split('==')[1]}, which "
        "predates the attribute-redaction hook — model content would export"
    )


@requires_redaction_support
def test_strands_tracer_redacts_content_when_the_token_is_present(monkeypatch):
    """End of the contract: the token makes Strands withhold model content.

    This asserts against the real `strands.telemetry.Tracer`, so an upstream
    change to the token name or semantics fails here rather than silently
    exporting shopper text again.
    """
    tracer_module = __import__(
        "strands.telemetry.tracer", fromlist=["Tracer", "REDACTED_VALUE"]
    )

    monkeypatch.delenv(SEMCONV_ENV, raising=False)
    apply_model_content_redaction(enabled=True)

    tracer = tracer_module.Tracer()

    assert tracer._redaction_enabled is True
    assert (
        tracer._redact("gen_ai.input.messages", "Is the linen shirt in Brooklyn?")
        == tracer_module.REDACTED_VALUE
    )
    # Note the allow-list is NOT scoped to `gen_ai.*` — an unlisted name of
    # any shape redacts. Pellier's evidence attributes survive because
    # Strands only applies redaction at its own content call sites; they are
    # never routed through it. `test_evidence_attributes_survive_redaction`
    # below asserts that end-state rather than this internal helper.
    assert tracer._redact("pellier.turn_id", "turn-abc") == tracer_module.REDACTED_VALUE


def test_evidence_attributes_survive_redaction(monkeypatch):
    """Redaction must not touch the attributes reconstruction depends on.

    Pellier sets `pellier.*` directly on spans, so they never pass through
    Strands' content redaction. This asserts the end-state a CloudWatch query
    sees: content withheld, correlation and identity intact.
    """
    sdk_trace = __import__("opentelemetry.sdk.trace", fromlist=["TracerProvider"])
    export = __import__(
        "opentelemetry.sdk.trace.export", fromlist=["SimpleSpanProcessor"]
    )
    in_memory = __import__(
        "opentelemetry.sdk.trace.export.in_memory_span_exporter",
        fromlist=["InMemorySpanExporter"],
    )
    from services import evidence_spans as ev

    monkeypatch.delenv(SEMCONV_ENV, raising=False)
    apply_model_content_redaction(enabled=True)

    provider = sdk_trace.TracerProvider()
    exporter = in_memory.InMemorySpanExporter()
    provider.add_span_processor(export.SimpleSpanProcessor(exporter))
    monkeypatch.setattr(ev, "_tracer", lambda: provider.get_tracer("test"))

    with ev.routing_span(
        turn_id="turn-abc",
        principal_sub="sub-marco",
        authenticated=True,
        persona_is_simulated=False,
    ):
        pass

    recorded = exporter.get_finished_spans()[0]
    assert recorded.attributes[ev.ATTR_TURN_ID] == "turn-abc"
    assert recorded.attributes[ev.ATTR_PRINCIPAL_SUB] == "sub-marco"
    assert recorded.attributes[ev.ATTR_AUTHENTICATED] is True


@requires_redaction_support
def test_strands_tracer_keeps_content_when_disabled(monkeypatch):
    """Without the token Strands exports content — the behavior we opt out of."""
    tracer_module = __import__(
        "strands.telemetry.tracer", fromlist=["Tracer", "REDACTED_VALUE"]
    )

    monkeypatch.delenv(SEMCONV_ENV, raising=False)
    apply_model_content_redaction(enabled=False)

    tracer = tracer_module.Tracer()

    assert tracer._redaction_enabled is False
    assert (
        tracer._redact("gen_ai.input.messages", "Is the linen shirt in Brooklyn?")
        == "Is the linen shirt in Brooklyn?"
    )
