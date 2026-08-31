"""Every deterministic tool has an owner, or a recorded reason for having none.

The finding this closes
-----------------------

The pre-handoff audit found `query_business_records`: a fully governed capability with a
read-only role, a READ ONLY transaction, a statement timeout, a schema allowlist, RLS, and
a receipt on every attempt including refusals - bound to no agent. Nothing could call it.
It was not broken; it was unreachable, and nothing in the repository said whether that was
a decision or an oversight. A lab author reading `agent_tools.py` would reasonably write a
step against it and find no path.

An unreachable tool is worse than a missing one: it reads as shipped, it carries a
security surface that still needs reviewing, and it costs the next team the same
investigation this test now answers in one place.

Writing the check surfaced a second one immediately: `issue_credit` is also bound to no
specialist. That one is correct and deliberate, and now says so.

What this asserts
-----------------

For every `@tool` in `services/agent_tools.py`, either a specialist imports it or it
appears in `UNBOUND_BY_DECISION` with a reason. That makes both directions fail loudly:

  * a new tool nobody binds fails until someone decides;
  * a tool listed as deliberately unbound fails the moment an agent binds it, so the
    decision has to be revisited rather than silently reversed.

The scan is import-based rather than runtime-based on purpose. `inventory_agent.py` binds
its three tools inside the Lab 1 marker region, which is empty until a participant fills
it, but the module-level import names them in either state. A runtime check would report
the Inventory Agent's tools as orphaned on every unstarted workshop box.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, Set

REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "pellier" / "backend"
AGENT_TOOLS = BACKEND / "services" / "agent_tools.py"
AGENTS_DIR = BACKEND / "agents"

# Tools deliberately reachable by no specialist. Each entry is a decision with a reason,
# not a waiver: removing the reason, or binding the tool, must break this test.
UNBOUND_BY_DECISION: Dict[str, str] = {
    "issue_credit": (
        "Operator-only, and deferred for this workshop iteration. Its caller is the "
        "confirmed-review execution path, not a specialist: "
        "Cedar forbids the action for shopper principals precisely so a shopper-facing "
        "agent cannot move money, and binding it to one would put the capability back "
        "inside the conversation it was removed from. It is also absent from the "
        "published Gateway set, so a fresh provision does not expose it at all."
    ),
    "query_business_records": (
        "Model-generated SQL behind the boundary in services/governed_query.py. It is "
        "unbound because a specialist that can reach it will sometimes prefer it to a "
        "curated tool that answers the same question deterministically, which trades an "
        "auditable tool call for a generated statement. Wiring it is a deliberate "
        "product decision: it needs an owning specialist, prompt language that makes it "
        "the last resort, and a governed-query receipt surface in the Observatory. Until "
        "then it ships governed and unreachable rather than reachable and ungoverned."
    ),
}

# `@tool` functions that are agent wrappers rather than deterministic business tools.
# Each wraps a whole specialist for the Agents-as-Tools orchestrator, so its owner is the
# orchestrator, not another specialist.
AGENT_WRAPPER_TOOLS: Set[str] = {
    "inventory", "search", "pricing", "recommendation", "support",
}


def _decorated_tools(path: Path) -> Set[str]:
    """Names of `@tool`-decorated functions, from the AST rather than a regex."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: Set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            name = getattr(target, "attr", None) or getattr(target, "id", None)
            if name == "tool":
                found.add(node.name)
    return found


def _bound_tools() -> Dict[str, Set[str]]:
    """Specialist module -> the tool names it imports from `services.agent_tools`."""
    bound: Dict[str, Set[str]] = {}
    for path in sorted(AGENTS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in (
                "services.agent_tools", "agent_tools",
            ):
                names.update(alias.name for alias in node.names)
        if names:
            bound[path.name] = names
    return bound


def test_the_scan_finds_the_tools_and_the_agents() -> None:
    """Guards the assertions below from passing on an empty scan."""
    tools = _decorated_tools(AGENT_TOOLS)
    bound = _bound_tools()
    assert len(tools) >= 15, f"only {len(tools)} @tool functions found in agent_tools.py"
    assert len(bound) >= 5, f"only {len(bound)} specialists import tools"


def test_every_tool_is_bound_or_recorded_as_unbound() -> None:
    tools = _decorated_tools(AGENT_TOOLS) - AGENT_WRAPPER_TOOLS
    bound = set().union(*_bound_tools().values())
    orphans = sorted(tools - bound - set(UNBOUND_BY_DECISION))
    assert not orphans, (
        "these tools are reachable by no specialist and no decision is recorded:\n  "
        + "\n  ".join(orphans)
        + "\nEither bind one to an agent or add it to UNBOUND_BY_DECISION with the reason."
    )


def test_no_recorded_unbound_tool_has_quietly_been_bound() -> None:
    """Reversing the decision must be deliberate, not a side effect of an import."""
    bound = set().union(*_bound_tools().values())
    contradictions = sorted(set(UNBOUND_BY_DECISION) & bound)
    assert not contradictions, (
        f"{contradictions} are listed as deliberately unbound but a specialist imports "
        "them. Update UNBOUND_BY_DECISION, and the governance that entry describes."
    )


def test_every_recorded_reason_is_a_reason() -> None:
    """A one-word waiver is not a decision the next team can act on."""
    for name, reason in UNBOUND_BY_DECISION.items():
        assert len(reason) > 120, f"{name}: the recorded reason is too thin to act on"
        assert name not in reason.split()[0], name


def test_every_recorded_unbound_tool_still_exists() -> None:
    """A stale entry hides the fact that the capability is gone."""
    tools = _decorated_tools(AGENT_TOOLS)
    missing = sorted(set(UNBOUND_BY_DECISION) - tools)
    assert not missing, f"UNBOUND_BY_DECISION names tools that no longer exist: {missing}"


def test_agent_wrapper_tools_all_exist() -> None:
    """The wrapper allow-list must not outlive the wrappers it excuses."""
    wrappers: Set[str] = set()
    for path in sorted(AGENTS_DIR.glob("*.py")):
        wrappers |= _decorated_tools(path)
    missing = sorted(AGENT_WRAPPER_TOOLS - wrappers - _decorated_tools(AGENT_TOOLS))
    assert not missing, f"AGENT_WRAPPER_TOOLS names non-existent wrappers: {missing}"


# ---------------------------------------------------------------------------
# The classification itself, asserted from every place that states it.
#
# `query_business_records` is category INTERNAL / NON-PUBLISHED. That is not a new
# decision made here: the README says it, `LOCAL_MCP_TOOL_NAMES` omits it,
# `gateway_tool_schemas` never declares it, no surface Lambda serves it, and
# `test_managed_gateway_tool_contract` pins in-process == CANONICAL | IN_PROCESS_ONLY.
# What was missing was agreement between the documentation and the binding: the README
# said it "runs only on the in-process rail", and on that rail a tool runs because a
# specialist lists it in `tools=[...]`. It was in no such list, so it ran nowhere.
# ---------------------------------------------------------------------------

INTERNAL_ONLY_TOOL = "query_business_records"
README = REPO / "README.md"


def test_the_internal_tool_is_absent_from_every_publication_path() -> None:
    """Four independent gates must all exclude it, not just one."""
    import sys

    deploy = str(REPO / "scripts" / "deploy")
    if deploy not in sys.path:
        sys.path.insert(0, deploy)
    from gateway_tool_schemas import canonical_tool_names, workshop_published_tools

    assert INTERNAL_ONLY_TOOL not in canonical_tool_names()
    assert INTERNAL_ONLY_TOOL not in workshop_published_tools()

    backend = str(BACKEND)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from services.agentcore_gateway import LOCAL_MCP_TOOL_NAMES

    assert INTERNAL_ONLY_TOOL not in set(LOCAL_MCP_TOOL_NAMES)

    served = ""
    for surface in sorted((REPO / "scripts" / "deploy").glob("pellier_*_server.py")):
        served += surface.read_text(encoding="utf-8")
    assert INTERNAL_ONLY_TOOL not in served, (
        "a Gateway surface Lambda serves the internal-only tool, which would put a "
        "second copy of the governed-query boundary into a deploy artifact"
    )


def test_fresh_rendering_cannot_publish_the_internal_tool() -> None:
    """The renderer writes what it is given; assert what it is given.

    Checked against the rendered schema rather than the declaration, because the
    accident this guards against is a schema helper widening, not someone typing the
    name into `TOOL_SCHEMAS`.
    """
    import sys

    deploy = str(REPO / "scripts" / "deploy")
    if deploy not in sys.path:
        sys.path.insert(0, deploy)
    from gateway_tool_schemas import TOOL_SCHEMAS, schema_for

    for surface in TOOL_SCHEMAS:
        for workshop in (True, False):
            names = {tool["name"] for tool in schema_for(surface, workshop=workshop)}
            assert INTERNAL_ONLY_TOOL not in names, (
                f"{surface} would publish {INTERNAL_ONLY_TOOL} with workshop={workshop}"
            )


def test_the_readme_does_not_claim_the_internal_tool_runs() -> None:
    """The documentation must match the binding.

    "runs only on the in-process rail" was false: a tool runs on that rail because a
    specialist lists it, and it is in no specialist's list. A false claim about a
    security-sensitive capability is worse than no claim, because the next reader
    budgets review time for a code path that never executes.
    """
    text = README.read_text(encoding="utf-8")
    assert INTERNAL_ONLY_TOOL in text, "the README no longer classifies the tool at all"
    window_start = text.index(INTERNAL_ONLY_TOOL)
    window = text[window_start: window_start + 700]
    assert "bound to no specialist" in window, (
        "the README must state that nothing invokes the internal tool, or it implies "
        "a code path that does not execute"
    )
    assert "runs **only** on the in-process rail" not in text
