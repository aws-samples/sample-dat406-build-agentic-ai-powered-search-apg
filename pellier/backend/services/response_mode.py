"""Per-turn specialist model selection for Pellier Labs.

Routing remains on the configured Sonnet router. This module selects only the
specialist that composes the shopper-facing response.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Literal

from config import settings

ResponseMode = Literal["balanced", "editorial", "fast"]
ModelTier = Literal["opus", "sonnet"]

response_mode_var: ContextVar[ResponseMode] = ContextVar(
    "pellier_response_mode",
    default="balanced",
)


def normalize_response_mode(value: object) -> ResponseMode:
    """Return a supported mode, defaulting unknown values to balanced."""
    normalized = str(value or "balanced").strip().lower()
    if normalized in {"balanced", "editorial", "fast"}:
        return normalized  # type: ignore[return-value]
    return "balanced"


def set_response_mode(value: object) -> Token:
    """Bind one response mode to the current agent turn."""
    return response_mode_var.set(normalize_response_mode(value))


def reset_response_mode(token: Token) -> None:
    """Restore the response mode that preceded the current turn."""
    response_mode_var.reset(token)


def resolve_specialist_model(
    default_tier: ModelTier,
    response_mode: object | None = None,
    *,
    balanced_model_id: str | None = None,
    balanced_max_tokens: int | None = None,
) -> tuple[str, int, ModelTier]:
    """Resolve the model ID and output ceiling for one specialist."""
    mode = normalize_response_mode(
        response_mode if response_mode is not None else response_mode_var.get()
    )
    if mode == "balanced" and balanced_model_id:
        default_max_tokens = (
            settings.AGENT_MAX_TOKENS_OPUS
            if default_tier == "opus"
            else settings.AGENT_MAX_TOKENS_SONNET
        )
        return (
            balanced_model_id,
            balanced_max_tokens
            if balanced_max_tokens is not None
            else default_max_tokens,
            default_tier,
        )

    tier: ModelTier
    if mode == "editorial":
        tier = "opus"
    elif mode == "fast":
        tier = "sonnet"
    else:
        tier = default_tier

    if tier == "opus":
        return (
            settings.BEDROCK_OPUS_MODEL,
            settings.AGENT_MAX_TOKENS_OPUS,
            tier,
        )
    model_id = (
        settings.BEDROCK_REPORTING_MODEL
        if mode == "balanced"
        else settings.BEDROCK_SONNET_MODEL
    )
    return model_id, settings.AGENT_MAX_TOKENS_SONNET, tier


def response_model_for_intent(
    intent: str,
    response_mode: object | None = None,
) -> tuple[str, int, ModelTier]:
    """Resolve the responding specialist model for a routed intent."""
    normalized_intent = "support" if intent == "customer_support" else intent
    default_tier: ModelTier = (
        "sonnet" if normalized_intent in {"pricing", "inventory"} else "opus"
    )
    return resolve_specialist_model(default_tier, response_mode)


def build_intent_signal(intent: str, response_mode: object) -> dict:
    """Build the public SSE event describing the real routing decision."""
    normalized_intent = "support" if intent == "customer_support" else intent
    mode = normalize_response_mode(response_mode)
    model_id, _, tier = response_model_for_intent(normalized_intent, mode)
    model_id_lower = model_id.lower()
    actual_family: ModelTier = (
        "opus"
        if "opus" in model_id_lower
        else "sonnet"
        if "sonnet" in model_id_lower
        else tier
    )
    return {
        "type": "intent_signal",
        "intent": normalized_intent,
        "classifier": "deterministic",
        "response_mode": mode,
        "model_family": actual_family,
        "model_id": model_id,
    }
