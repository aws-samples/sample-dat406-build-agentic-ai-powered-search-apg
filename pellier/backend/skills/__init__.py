"""
Skills — the third architectural layer alongside agents and tools.

Skills are folders of domain expertise loaded conditionally into an
agent's system prompt based on what the conversation needs. Agents
are *who*, tools are *what*, skills are *how*.

This package exposes:
  - ``Skill`` / ``RouterDecision``: Pydantic models
  - ``SkillRegistry``: in-memory store of skills loaded at boot
  - ``get_registry()``: FastAPI-friendly accessor
  - ``inject_skills()``: helper that composes a skill-augmented system prompt
  - ``SkillRouter``: one-call LLM router (Phase 2)

The package is agent-agnostic — it does not import from any specific
agent. Any agent can opt in by calling ``inject_skills(system_prompt)``
with the currently-loaded skills for the turn.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import Skill, RouterDecision
from .registry import SkillRegistry
from .loader import get_registry, load_registry
from .context import (
    loaded_skills_var,
    set_loaded_skills,
    get_loaded_skills,
    inject_skills,
)

if TYPE_CHECKING:
    from .router import SkillRouter


def __getattr__(name: str) -> Any:
    """Load the model-backed router only when a caller requests it."""
    if name == "SkillRouter":
        from .router import SkillRouter

        return SkillRouter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Skill",
    "RouterDecision",
    "SkillRegistry",
    "get_registry",
    "load_registry",
    "loaded_skills_var",
    "set_loaded_skills",
    "get_loaded_skills",
    "inject_skills",
    "SkillRouter",
]
