"""The participant contract has exactly one definition, and it is enforced.

Three artifacts describe what an attendee edits: ``solutions/README.md``
(the prose contract), ``scripts/builders_starter.py`` (which installs the
gaps), and the Workshop Studio guide (which asks attendees to close them).
They drifted: the README promised one code build and named the tool body as
"the only file participants change", while the starter installs two gaps and
the guide walks attendees through both. An attendee following the README
would have finished with an ungranted agent and a failing proof gate.

These tests pin the two gaps to the code that installs them, so the prose
cannot claim a different workshop than the one the machine provisions.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
README = REPO / "solutions/README.md"
STARTER = REPO / "scripts/builders_starter.py"


def _starter():
    spec = importlib.util.spec_from_file_location("builders_starter", STARTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract_section() -> str:
    text = README.read_text(encoding="utf-8")
    start = text.index("## Workshop required path")
    return text[start : text.index("### Optional fast-finisher A")]


def _granted_tools(block: str) -> list[str]:
    """Parse INVENTORY_AGENT_TOOLS out of one marked grant block."""
    body = "\n".join(
        line for line in block.splitlines() if not line.lstrip().startswith("#")
    )
    tree = ast.parse(body)
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
    return [element.id for element in assignment.value.elts]


def test_starter_installs_two_independent_gaps() -> None:
    """The tool body and the agent grant are separate gaps.

    The middle state — a working tool the agent still cannot select — is
    the lesson, so it must survive as its own position on the path.
    """
    starter = _starter()

    assert _granted_tools(starter.STARTER_AGENT_GRANT) == [
        "restock_shelf",
        "running_low",
    ]
    assert _granted_tools(starter.COMPLETE_AGENT_GRANT) == [
        "floor_check",
        "restock_shelf",
        "running_low",
    ]
    starter_tools = starter._paths(REPO)["starter_tools"]
    assert starter.TOOL_STUB_MARKER in starter_tools.read_text(encoding="utf-8")

    verify = inspect.getsource(starter.verify_state)
    for state in ("starter", "tool-wired", "complete"):
        assert f'"{state}"' in verify


def test_readme_names_both_files_the_participant_edits() -> None:
    """The prose contract must name both gaps, not just the tool body."""
    section = _contract_section()

    assert "pellier/backend/services/agent_tools.py" in section
    assert "pellier/backend/agents/stock_keeper.py" in section
    assert "INVENTORY_AGENT_TOOLS" in section
    assert "Two participant code edits" in section


def test_readme_does_not_claim_a_single_edited_file() -> None:
    """Guard the exact phrasing that caused the drift."""
    text = README.read_text(encoding="utf-8")

    assert "The only file participants change" not in text
    assert "One mandatory code build" not in text
    # The stale governed-branch exercise must not reappear here.
    assert "author three queries against" not in text


def test_readme_edited_paths_all_exist() -> None:
    """Every path the contract tells a participant to edit must be real."""
    section = _contract_section()

    for match in re.findall(r"`(pellier/[\w/]+\.py)`", section):
        assert (REPO / match).is_file(), f"contract names a missing file: {match}"
