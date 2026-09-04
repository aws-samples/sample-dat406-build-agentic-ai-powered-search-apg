#!/usr/bin/env python3
"""Install and verify the two intentional builders-session starter gaps."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import sys
from pathlib import Path


AGENT_GRANT_START = "# === WORKSHOP: Stock Keeper agent grant: START ==="
AGENT_GRANT_END = "# === WORKSHOP: Stock Keeper agent grant: END ==="
TOOL_BODY_START = "# === WORKSHOP · Stock Keeper · floor_check: START ==="
TOOL_BODY_END = "# === WORKSHOP · Stock Keeper · floor_check: END ==="
TOOL_STUB_MARKER = "WORKSHOP_EXERCISE_STUB"
TOOL_STUB_RESPONSE = "floor_check is in stub state"

STARTER_AGENT_GRANT = """# === WORKSHOP: Stock Keeper agent grant: START ===
# WORKSHOP_AGENT_GRANT_STUB
# Add floor_check to this list after its implementation passes step 1.
INVENTORY_AGENT_TOOLS = [restock_shelf, running_low]
# === WORKSHOP: Stock Keeper agent grant: END ==="""

COMPLETE_AGENT_GRANT = """# === WORKSHOP: Stock Keeper agent grant: START ===
INVENTORY_AGENT_TOOLS = [floor_check, restock_shelf, running_low]
# === WORKSHOP: Stock Keeper agent grant: END ==="""


def _paths(repo: Path) -> dict[str, Path]:
    return {
        "live_tools": repo / "pellier/backend/services/agent_tools.py",
        "starter_tools": (
            repo
            / "solutions/closing-marcos-gap/services/"
            "agent_tools_builders_preapply.py"
        ),
        "solution_body": (
            repo
            / "solutions/closing-marcos-gap/services/"
            "floor_check_tool_body.py"
        ),
        "stock_keeper": repo / "pellier/backend/agents/stock_keeper.py",
    }


def _replace_marked_block(path: Path, replacement: str) -> None:
    source = path.read_text(encoding="utf-8")
    if source.count(AGENT_GRANT_START) != 1 or source.count(AGENT_GRANT_END) != 1:
        raise RuntimeError(
            f"{path} must contain exactly one Stock Keeper agent-grant block"
        )
    before, remainder = source.split(AGENT_GRANT_START, 1)
    _current, after = remainder.split(AGENT_GRANT_END, 1)
    path.write_text(
        f"{before}{replacement}{after}",
        encoding="utf-8",
    )


def _inventory_tool_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name)
            and target.id == "INVENTORY_AGENT_TOOLS"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            raise RuntimeError("INVENTORY_AGENT_TOOLS must be a literal list")
        names = {
            item.id
            for item in node.value.elts
            if isinstance(item, ast.Name)
        }
        if len(names) != len(node.value.elts):
            raise RuntimeError(
                "INVENTORY_AGENT_TOOLS may contain only imported tool names"
            )
        return names
    raise RuntimeError("INVENTORY_AGENT_TOOLS assignment was not found")


def inspect_state(repo: Path) -> dict[str, object]:
    paths = _paths(repo)
    for label, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"Missing {label}: {path}")

    tool_source = paths["live_tools"].read_text(encoding="utf-8")
    tool_is_stub = (
        TOOL_STUB_MARKER in tool_source
        and TOOL_STUB_RESPONSE in tool_source
    )
    inventory_tools = _inventory_tool_names(paths["stock_keeper"])
    return {
        "floor_check": "exercise" if tool_is_stub else "shipped",
        "Stock Keeper": (
            "shipped"
            if not tool_is_stub and "floor_check" in inventory_tools
            else "exercise"
        ),
        "inventoryTools": sorted(inventory_tools),
    }


def apply_starter(repo: Path) -> dict[str, object]:
    paths = _paths(repo)
    for label in ("starter_tools", "stock_keeper"):
        if not paths[label].is_file():
            raise RuntimeError(f"Missing {label}: {paths[label]}")

    shutil.copyfile(paths["starter_tools"], paths["live_tools"])
    _replace_marked_block(paths["stock_keeper"], STARTER_AGENT_GRANT)
    return verify_state(repo, "starter")


def complete_tool(repo: Path) -> dict[str, object]:
    paths = _paths(repo)
    for label in ("live_tools", "solution_body"):
        if not paths[label].is_file():
            raise RuntimeError(f"Missing {label}: {paths[label]}")

    source = paths["live_tools"].read_text(encoding="utf-8")
    if source.count(TOOL_BODY_START) != 1 or source.count(TOOL_BODY_END) != 1:
        raise RuntimeError(
            f"{paths['live_tools']} must contain exactly one floor_check block"
        )

    body_lines = paths["solution_body"].read_text(encoding="utf-8").splitlines()
    while body_lines and (
        not body_lines[0].strip()
        or body_lines[0].lstrip().startswith("#")
    ):
        body_lines.pop(0)
    body = "\n".join(body_lines).rstrip()
    if not body:
        raise RuntimeError(f"Solution body is empty: {paths['solution_body']}")
    before, remainder = source.split(TOOL_BODY_START, 1)
    _current, after = remainder.split(TOOL_BODY_END, 1)
    paths["live_tools"].write_text(
        f"{before}{TOOL_BODY_START}\n{body}\n    {TOOL_BODY_END}{after}",
        encoding="utf-8",
    )
    return verify_state(repo, "tool-wired")


def complete_agent(repo: Path) -> dict[str, object]:
    _replace_marked_block(_paths(repo)["stock_keeper"], COMPLETE_AGENT_GRANT)
    return verify_state(repo, "complete")


def verify_state(repo: Path, expected: str) -> dict[str, object]:
    state = inspect_state(repo)
    expected_states = {
        "starter": ("exercise", "exercise"),
        "tool-wired": ("shipped", "exercise"),
        "complete": ("shipped", "shipped"),
    }
    expected_tool, expected_agent = expected_states[expected]
    actual = (state["floor_check"], state["Stock Keeper"])
    wanted = (expected_tool, expected_agent)
    if actual != wanted:
        raise RuntimeError(
            f"Expected builders state {expected!r} {wanted}, found {actual}"
        )
    return state


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("apply")
    commands.add_parser("complete-tool")

    verify = commands.add_parser("verify")
    verify.add_argument(
        "--expect",
        choices=("starter", "tool-wired", "complete"),
        required=True,
    )

    commands.add_parser("complete-agent")
    return root


def main() -> int:
    args = parser().parse_args()
    repo = args.repo.resolve()
    try:
        if args.command == "apply":
            state = apply_starter(repo)
        elif args.command == "complete-tool":
            state = complete_tool(repo)
        elif args.command == "complete-agent":
            state = complete_agent(repo)
        else:
            state = verify_state(repo, args.expect)
    except (OSError, RuntimeError, SyntaxError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
