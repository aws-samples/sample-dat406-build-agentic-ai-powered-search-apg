"""
Keep model prompts and completions out of exported telemetry.

Once spans leave the process (see `services/otel_cloudwatch_export.py`), what
they carry becomes a governance decision rather than a debugging convenience.
Strands records the shopper's message, the model's completion, the system
instructions, and tool results as span content by default — verified in the
live `aws/spans` log group, where a `gen_ai.user.message` event carried the
shopper's question verbatim.

That collides with the evidence-span contract: spans locate and correlate a
turn, Aurora artifacts prove what happened. A turn is reconstructable from
`turn_id`, identity, policy verdict, and execution outcome; it never needs the
prompt text. Anything beyond that is payload sitting in broadly readable
telemetry instead of in the access-controlled ledger.

How the switch works
--------------------

Strands exposes a first-class allow-list rather than an on/off flag. The
`OTEL_SEMCONV_STABILITY_OPT_IN` variable carries comma-separated tokens; the
token `gen_ai_unredacted_attributes=<semicolon-list>` turns redaction ON for
everything *except* the listed attributes. Its mere presence enables
redaction, so an empty list means "redact all model content" — that is the
posture this module installs.

Two constraints follow from Strands' implementation, both load-bearing:

* **Ordering.** `strands.telemetry.Tracer.__init__` reads the variable once,
  at construction. This must run *before* `StrandsTelemetry()`, or the tracer
  is already built with redaction off and the setting silently does nothing.
* **Append, never replace.** The same variable carries unrelated tokens
  (`gen_ai_latest_experimental`, `gen_ai_span_attributes_only`, ...).
  Overwriting it would quietly change convention behavior an operator chose.

Redaction replaces values with Strands' `[REDACTED]` marker; the attributes
still exist, so a reader can tell content was withheld rather than absent.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SEMCONV_ENV = "OTEL_SEMCONV_STABILITY_OPT_IN"

# Presence of this token enables redaction. The value after `=` is the
# allow-list; empty means nothing is exempt.
_REDACTION_TOKEN_PREFIX = "gen_ai_unredacted_attributes="

# Redact everything.
#
# The allow-list is not scoped to `gen_ai.*` — an unlisted attribute of any
# shape is redacted. Pellier's `pellier.*` evidence attributes survive
# because Strands applies redaction only at its own content call sites, and
# Pellier sets its attributes directly on spans. So withholding all model
# content costs the reconstruction path nothing.
_REDACT_ALL_TOKEN = f"{_REDACTION_TOKEN_PREFIX}"


def _tokens(value: str) -> list[str]:
    """Split the opt-in variable the way Strands does, preserving order."""
    return [token.strip() for token in value.split(",") if token.strip()]


def redaction_already_configured(value: Optional[str] = None) -> bool:
    """Return True when the operator has already set a redaction allow-list.

    An explicit allow-list is a deliberate choice — someone decided which
    attributes stay readable. Replacing it with "redact everything" would
    override that decision, so this module leaves it alone.
    """
    raw = os.environ.get(SEMCONV_ENV, "") if value is None else value
    return any(token.startswith(_REDACTION_TOKEN_PREFIX) for token in _tokens(raw))


def apply_model_content_redaction(*, enabled: bool) -> str:
    """Install the redact-all token, returning the resulting variable value.

    Must be called before `StrandsTelemetry()` constructs the tracer.

    Args:
        enabled: False leaves the environment untouched, which is Strands'
            default: full prompt and completion content on every span.

    Returns:
        The value of `OTEL_SEMCONV_STABILITY_OPT_IN` after this call, for
        logging and for the readiness surface.
    """
    current = os.environ.get(SEMCONV_ENV, "")

    if not enabled:
        logger.info(
            "Model content redaction disabled — prompts, completions, and tool "
            "results will be exported on spans. Appropriate for agent "
            "debugging, not for a deployment handling real shopper data."
        )
        return current

    if redaction_already_configured(current):
        logger.info(
            "%s already carries a redaction allow-list; leaving it as the "
            "operator set it.",
            SEMCONV_ENV,
        )
        return current

    tokens = _tokens(current)
    tokens.append(_REDACT_ALL_TOKEN)
    updated = ",".join(tokens)
    os.environ[SEMCONV_ENV] = updated
    logger.info(
        "✅ Model content redaction on — prompts, completions, and tool "
        "results export as [REDACTED]. Pellier's own pellier.* evidence "
        "attributes are set outside Strands' content path and are unaffected."
    )
    return updated
