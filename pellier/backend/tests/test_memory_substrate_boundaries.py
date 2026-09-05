"""Who owns each memory substrate, asserted rather than described.

Pellier separates four memory categories by owner, and the separation is the
lesson: AgentCore Memory is not a store for all four. Two of these live in the
managed service, one lives in Aurora, and one lives in the repository.

    working    short-term  AgentCore Memory session events, 30-day expiry
    semantic   long-term   AgentCore Memory records from the USER_PREFERENCE
                           strategy, namespaced by actor
    episodic   long-term   Aurora: customers, orders, returns, seeded events
    procedural long-term   checked-in runtime skills and MCP tool schemas

`pellier.tool_audit` is deliberately outside that set. It records what
executed and how long it took; it does not teach the agent how to work.

This file exists because the boundary drifted once on a participant-visible
surface: the production-patterns fixture claimed durable taste lived in
"Aurora pgvector profile embeddings keyed by user", marked shipped, while the
README's table correctly attributed it to AgentCore. No such table, column, or
lookup has ever existed. A reader comparing the two surfaces would have to
guess which was true.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
OBSERVATORY_ROUTE = REPO / "pellier" / "backend" / "routes" / "observatory.py"
RENDERER = REPO / "scripts" / "deploy" / "render_agentcore_project.py"
PATTERNS = (
    REPO
    / "pellier"
    / "frontend"
    / "src"
    / "observatory"
    / "fixtures"
    / "production-patterns.json"
)


def _read(path: pathlib.Path) -> str:
    assert path.is_file(), f"{path.relative_to(REPO)} is missing"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# What the managed service is actually provisioned to hold
# ---------------------------------------------------------------------------


def test_agentcore_memory_declares_exactly_one_long_term_strategy() -> None:
    """One extraction strategy, so "semantic" names one thing.

    A second strategy would put two different long-term record shapes under the
    same participant-facing word without the surfaces distinguishing them.
    """
    source = _read(RENDERER)
    strategies = re.findall(r'"type":\s*"(USER_PREFERENCE|SEMANTIC|SUMMARIZATION|SUMMARY)"', source)
    assert strategies == ["USER_PREFERENCE"], (
        f"expected exactly one USER_PREFERENCE strategy, found {strategies}"
    )


def test_the_long_term_namespace_is_keyed_by_actor_not_session() -> None:
    """Long-term records must outlive the session that produced them."""
    source = _read(RENDERER)
    assert '"/pellier/preferences/{actorId}/"' in source
    assert "{sessionId}" not in source


def test_short_term_events_expire() -> None:
    """The session ledger is a recent record, not a permanent transcript."""
    assert '"eventExpiryDuration"' in _read(RENDERER)


# ---------------------------------------------------------------------------
# What the Observatory tells a participant each substrate is
# ---------------------------------------------------------------------------


SUBSTRATE_OWNERS = (
    ("working", "Working - AgentCore Memory"),
    ("semantic", "Semantic - AgentCore Memory"),
    ("episodic", "Episodic - Aurora"),
    ("procedural", "Procedural - source controlled"),
    ("operational", "Operational History - Aurora"),
)


@pytest.mark.parametrize(("substrate", "owner"), SUBSTRATE_OWNERS)
def test_the_read_model_attributes_each_substrate_to_its_owner(
    substrate: str, owner: str
) -> None:
    source = _read(OBSERVATORY_ROUTE)
    assert f'"{owner}"' in source, f"{substrate} lost its owner label {owner!r}"


def test_tool_audit_is_never_presented_as_a_memory_substrate() -> None:
    """It is execution history. Calling it procedural memory was an older model."""
    source = _read(OBSERVATORY_ROUTE)
    assert '"Operational History - Aurora"' in source
    assert "Procedural - Aurora" not in source
    assert '"Procedural - source controlled"' in source


def test_procedural_memory_points_at_reviewable_source() -> None:
    source = _read(OBSERVATORY_ROUTE)
    assert "skills/*/SKILL.md" in source
    assert "gateway_tool_schemas.py" in source


# ---------------------------------------------------------------------------
# No surface may relocate a substrate
# ---------------------------------------------------------------------------


def test_no_surface_claims_aurora_holds_a_preference_embedding_store() -> None:
    """Aurora owns episodic history. Durable preference is AgentCore's.

    Pellier has no profile-embedding table: the catalogue carries the only
    embeddings, and `get_customer_preferences` reads ordinary Aurora rows.
    """
    offenders = []
    for path in REPO.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".md", ".json"}:
            continue
        rel = path.relative_to(REPO).as_posix()
        if rel.startswith((".git/", "node_modules/")) or "/node_modules/" in rel:
            continue
        if rel == "pellier/backend/tests/test_memory_substrate_boundaries.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(pgvector|Aurora)[^.\n]{0,40}profile embedding", text, re.I):
            offenders.append(rel)
        if re.search(r"profile_embedding|customer_profile_vector", text):
            offenders.append(rel)
    assert not offenders, (
        "these surfaces claim a profile-embedding store Pellier does not have: "
        f"{sorted(set(offenders))}"
    )


def test_the_multitenancy_pattern_names_the_real_long_term_store() -> None:
    patterns = json.loads(_read(PATTERNS))

    def find(node):
        if isinstance(node, dict):
            if node.get("slug") == "multitenancy":
                return node
            for value in node.values():
                found = find(value)
                if found:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = find(value)
                if found:
                    return found
        return None

    entry = find(patterns)
    assert entry is not None, "the multi-tenancy production pattern is gone"
    blob = json.dumps(entry)
    assert "USER_PREFERENCE" in blob, (
        "the pattern must name the strategy that actually holds long-term records"
    )
    assert "pgvector profile" not in blob
