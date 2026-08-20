"""No shopper text on OpenTelemetry trace attributes.

This is a regression guard for a leak found live, not a hypothetical. Pellier
set `"user.query": message[:100]` on `Agent.trace_attributes`, so every
exported span carried the shopper's question — confirmed by finding a
distinctive test phrase verbatim in the `aws/spans` CloudWatch log group.

Redacting Strands' own `gen_ai.*` content does **not** cover this: trace
attributes are Pellier's own, set outside the framework's content path, so
they bypass redaction entirely. Two independent leaks, two independent fixes.

Why an AST guard rather than a behavior test: the leak is a one-line dict
entry that any future edit can reintroduce, in a code path that needs a live
agent to exercise. Scanning the construction sites catches it in CI at the
moment it is written. The invariant being defended:

    Spans locate and correlate a turn. Aurora artifacts prove what happened.
    Customer payloads belong in the access-controlled ledger, not in
    broadly readable telemetry.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

import pytest

BACKEND = Path(__file__).resolve().parents[1]

# Modules that build `trace_attributes`. Listed explicitly so a new one is a
# deliberate addition rather than something the glob quietly absorbs.
_SOURCES = [
    BACKEND / "services" / "chat.py",
    BACKEND / "agentcore_runtime.py",
    BACKEND / "services" / "agentcore_runtime.py",
]

# Local names that hold shopper- or model-authored text. A trace attribute
# whose value reads from one of these is a payload leak.
_PAYLOAD_NAMES = frozenset(
    {
        "message",
        "prompt",
        "user_message",
        "query",
        "routing_query",
        "response",
        "answer",
        "content",
        "conversation_history",
    }
)

# Attribute keys that name payload regardless of how the value is built.
_FORBIDDEN_KEYS = frozenset(
    {
        "user.query",
        "user.message",
        "user.prompt",
        "gen_ai.prompt",
        "gen_ai.completion",
        "agent.response",
    }
)


def _referenced_names(node: ast.AST) -> set:
    """Return every bare name read inside an expression."""
    return {
        child.id for child in ast.walk(node) if isinstance(child, ast.Name)
    }


def _trace_attribute_dicts(tree: ast.AST) -> List[ast.Dict]:
    """Find dict literals assigned to anything named `trace_attributes`."""
    found: List[ast.Dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Dict):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            name = (
                target.attr
                if isinstance(target, ast.Attribute)
                else target.id
                if isinstance(target, ast.Name)
                else ""
            )
            if name == "trace_attributes":
                found.append(value)
    return found


def _leaks(path: Path) -> List[Tuple[str, str]]:
    """Return (key, reason) for every payload-bearing trace attribute."""
    tree = ast.parse(path.read_text())
    problems: List[Tuple[str, str]] = []

    for dict_node in _trace_attribute_dicts(tree):
        for key_node, value_node in zip(dict_node.keys, dict_node.values):
            key = (
                key_node.value
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)
                else "<computed>"
            )
            if key in _FORBIDDEN_KEYS:
                problems.append((key, "key names shopper or model text"))
                continue
            leaked = _referenced_names(value_node) & _PAYLOAD_NAMES
            if leaked:
                problems.append(
                    (key, f"value reads {', '.join(sorted(leaked))}")
                )
    return problems


@pytest.mark.parametrize("source", [p for p in _SOURCES if p.exists()], ids=lambda p: p.name)
def test_trace_attributes_carry_no_shopper_text(source: Path) -> None:
    problems = _leaks(source)

    assert not problems, (
        f"{source.name} puts payload on trace attributes: "
        + "; ".join(f"{key} ({why})" for key, why in problems)
        + ". Spans locate a turn; the text belongs in the session record."
    )


def test_at_least_one_source_actually_builds_trace_attributes() -> None:
    """Guard the guard: a scanner that matches nothing proves nothing.

    If `trace_attributes` is renamed or moved, this fails rather than
    letting the parametrized test pass vacuously.
    """
    total = sum(
        len(_trace_attribute_dicts(ast.parse(path.read_text())))
        for path in _SOURCES
        if path.exists()
    )
    assert total >= 2, (
        "expected the streamed and non-streamed chat paths to build "
        f"trace_attributes; found {total} construction sites"
    )


def test_scanner_detects_a_known_bad_pattern() -> None:
    """Self-check on the exact leak that shipped."""
    bad = ast.parse(
        "agent.trace_attributes = {\n"
        '    "session.id": session_id,\n'
        '    "user.query": message[:100],\n'
        "}\n"
    )
    dicts = _trace_attribute_dicts(bad)
    assert len(dicts) == 1

    keys = [
        k.value for k in dicts[0].keys if isinstance(k, ast.Constant)
    ]
    assert "user.query" in keys
    assert "user.query" in _FORBIDDEN_KEYS


def test_scanner_detects_a_renamed_key_carrying_the_message() -> None:
    """Renaming the key must not defeat the guard — the value is the leak."""
    bad = ast.parse(
        'agent.trace_attributes = {"context.hint": message[:100]}\n'
    )
    dict_node = _trace_attribute_dicts(bad)[0]
    leaked = _referenced_names(dict_node.values[0]) & _PAYLOAD_NAMES

    assert leaked == {"message"}


def test_identity_and_correlation_attributes_are_allowed() -> None:
    """Identity is correlation, not payload; the guard must not flag it."""
    good = ast.parse(
        "agent.trace_attributes = {\n"
        '    "session.id": session_id or "anonymous",\n'
        '    "session.user": user.get("sub", "anonymous") if user else "anonymous",\n'
        '    "turn.id": turn_id,\n'
        '    "workshop": "pellier",\n'
        "}\n"
    )
    dict_node = _trace_attribute_dicts(good)[0]

    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        assert key_node.value not in _FORBIDDEN_KEYS
        assert not (_referenced_names(value_node) & _PAYLOAD_NAMES)
