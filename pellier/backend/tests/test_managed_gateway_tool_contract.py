"""Guard the canonical 15-tool contract across every managed deployment copy."""

from __future__ import annotations

import ast
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DEPLOY = REPO / "scripts" / "deploy"

CANONICAL_TOOLS = {
    "preference_snapshot",
    "trace_receipt",
    "floor_check",
    "whats_trending",
    "price_intelligence",
    "restock_shelf",
    "process_return",
    "escalate_to_stylist",
    "find_pieces",
    "find_pieces_hybrid",
    "explore_collection",
    "running_low",
    "side_by_side",
    "returns_and_care",
    "style_match",
}

# Tools that exist on the in-process rail and are deliberately NOT published
# through the Gateway. Declared explicitly so an accidental divergence still
# fails: the assertion below is in-process == CANONICAL | IN_PROCESS_ONLY, so
# adding a tool without deciding which category it belongs to breaks the test.
#
# `query_business_records` runs model-generated SQL behind a security boundary
# (`services/governed_query.py`: read-only role, READ ONLY transaction,
# statement timeout, schema allowlist, RLS). Publishing it through a Gateway
# Lambda would mean copying that boundary into a separate deploy artifact,
# where it would drift from the reviewed version. The design's required
# execution rail for this capability is the in-process one.
IN_PROCESS_ONLY_TOOLS = {
    "query_business_records",
}

SURFACE_FILES = {
    "search": DEPLOY / "pellier_search_server.py",
    "pricing": DEPLOY / "pellier_pricing_server.py",
    "recommendation": DEPLOY / "pellier_recommend_server.py",
    "experience": DEPLOY / "pellier_experience_server.py",
}


def _assignment(path: Path, name: str) -> ast.expr:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return node.value
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return node.value
    raise AssertionError(f"{name} not found in {path}")


def _dict_items(node: ast.expr) -> dict[str, ast.expr]:
    assert isinstance(node, ast.Dict)
    return {
        key.value: value
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def _dict_keys(node: ast.expr) -> set[str]:
    return set(_dict_items(node))


def _gateway_schema_names() -> dict[str, set[str]]:
    surfaces = _dict_items(
        _assignment(DEPLOY / "gateway_tool_schemas.py", "TOOL_SCHEMAS")
    )
    result: dict[str, set[str]] = {}
    for surface, config_node in surfaces.items():
        tools_node = _dict_items(config_node)["tools"]
        assert isinstance(tools_node, ast.List)
        result[surface] = {
            _dict_items(tool_node)["name"].value
            for tool_node in tools_node.elts
        }
    return result


def _lambda_names() -> dict[str, set[str]]:
    return {
        surface: _dict_keys(_assignment(path, "TOOLS"))
        for surface, path in SURFACE_FILES.items()
    }


def test_managed_surfaces_publish_exactly_the_canonical_15_tools() -> None:
    lambda_names = _lambda_names()
    gateway_names = _gateway_schema_names()

    assert lambda_names == gateway_names
    published = set().union(*lambda_names.values())
    assert len(published) == 15
    assert published == CANONICAL_TOOLS

    provisioner = (
        REPO / "scripts" / "provision_agentcore_end_to_end.py"
    ).read_text(encoding="utf-8")
    renderer = (DEPLOY / "render_agentcore_project.py").read_text(encoding="utf-8")
    assert "from gateway_tool_schemas import TOOL_SCHEMAS, schema_for" in provisioner
    assert "from gateway_tool_schemas import TOOL_SCHEMAS, schema_for" in renderer


def test_in_process_and_recovery_files_match_the_managed_contract() -> None:
    paths = [
        REPO / "pellier" / "backend" / "services" / "agent_tools.py",
        REPO / "solutions" / "closing-marcos-gap" / "services"
        / "agent_tools_builders_preapply.py",
        REPO / "solutions" / "closing-marcos-gap" / "services"
        / "agent_tools_floor_check_solution.py",
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        decorated = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any(
                isinstance(decorator, ast.Name) and decorator.id == "tool"
                for decorator in node.decorator_list
            )
        }
        assert decorated == CANONICAL_TOOLS | IN_PROCESS_ONLY_TOOLS, path


def test_gateway_targets_are_owned_by_agentcore_cli_project() -> None:
    source = (DEPLOY / "render_agentcore_project.py").read_text(encoding="utf-8")
    assert '"targetType": "lambdaFunctionArn"' in source
    assert '"lambdaArn": lambda_arns[surface]' in source
    assert '"toolSchemaFile"' in source
    assert "deploy_gateway.py" not in source


def test_workshop_dependencies_are_immutable() -> None:
    backend_lock = REPO / "pellier" / "backend" / "requirements.lock"
    uv_lock = REPO / "pellier" / "backend" / "uv.lock"
    assert backend_lock.is_file()
    assert uv_lock.is_file()
    locked = backend_lock.read_text(encoding="utf-8")
    assert "--generate-hashes" in locked
    assert "--hash=sha256:" in locked
    for package in ("bedrock-agentcore", "boto3", "mcp", "strands-agents"):
        assert re_search_exact_pin(locked, package), package

    deploy_requirements = (
        DEPLOY / "requirements.txt"
    ).read_text(encoding="utf-8").splitlines()
    for line in deploy_requirements:
        clean = line.strip()
        if clean and not clean.startswith("#"):
            assert "==" in clean, clean
    deploy_lambda = (DEPLOY / "deploy_lambda.py").read_text(encoding="utf-8")
    assert "'mcp==1.28.1'" in deploy_lambda
    assert '"bedrock:Rerank"' in deploy_lambda


def re_search_exact_pin(requirements: str, package: str) -> bool:
    import re

    return re.search(
        rf"(?m)^{re.escape(package)}(?:\[[^]]+\])?==[^\s\\]+",
        requirements,
    ) is not None


def test_imperative_resources_receive_workshop_ownership_tags() -> None:
    paths = [
        DEPLOY / "render_agentcore_project.py",
        DEPLOY / "deploy_lambda.py",
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "PellierWorkshopId" in source, path


def test_in_process_only_tools_are_not_published_through_the_gateway() -> None:
    """The declared exception must stay an exception.

    If one of these ever appears in a Gateway schema or Lambda surface, the
    security boundary it depends on has been copied into a second place, and
    the two copies will drift.
    """
    published = set().union(*_lambda_names().values()) | set().union(
        *_gateway_schema_names().values()
    )
    overlap = published & IN_PROCESS_ONLY_TOOLS
    assert not overlap, (
        f"in-process-only tools appear on a managed surface: {sorted(overlap)}"
    )
