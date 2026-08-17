#!/usr/bin/env python3
"""Provision Pellier's required AgentCore Memory through the AgentCore CLI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


DEPLOY_DIR = Path(__file__).resolve().parent / "deploy"
if str(DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(DEPLOY_DIR))

from render_agentcore_project import (  # noqa: E402
    AGENTCORE_CLI,
    MEMORY_NAME,
    MEMORY_NAMESPACE,
    MEMORY_STRATEGY_NAME,
    PROJECT_NAME,
    project_root,
)


AWS_CONFIG = Config(
    retries={"total_max_attempts": 5, "mode": "adaptive"},
    connect_timeout=10,
    read_timeout=60,
)


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        )
    return process


def _agentcore(
    root: Path,
    *arguments: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return _run(
        ["npx", "-y", AGENTCORE_CLI, *arguments],
        cwd=root,
        env=env,
    )


def _scaffold_project(
    *,
    repo: Path,
    env: dict[str, str],
) -> Path:
    root = project_root(repo)
    config_path = root / "agentcore" / "agentcore.json"
    if config_path.is_file():
        return root

    root.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "npx",
            "-y",
            AGENTCORE_CLI,
            "create",
            "--project-name",
            PROJECT_NAME,
            "--no-agent",
            "--skip-git",
            "--skip-python-setup",
            "--skip-install",
            "--output-dir",
            str(root.parent),
            "--json",
        ],
        cwd=root.parent,
        env=env,
    )
    if not config_path.is_file():
        raise RuntimeError(f"AgentCore CLI did not create {config_path}")
    return root


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read valid JSON from {path}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _configure_memory(
    *,
    root: Path,
    account_id: str,
    region: str,
    workshop_id: str,
    env: dict[str, str],
) -> None:
    config_path = root / "agentcore" / "agentcore.json"
    project = _read_json(config_path)
    memories = project.get("memories")
    if not isinstance(memories, list):
        raise RuntimeError("AgentCore project has no memories array")

    memory = next(
        (
            item
            for item in memories
            if isinstance(item, dict) and item.get("name") == MEMORY_NAME
        ),
        None,
    )
    if memory is None:
        _agentcore(
            root,
            "add",
            "memory",
            "--name",
            MEMORY_NAME,
            "--strategies",
            "USER_PREFERENCE",
            "--expiry",
            "30",
            "--json",
            env=env,
        )
        project = _read_json(config_path)
        memory = next(
            (
                item
                for item in project.get("memories", [])
                if isinstance(item, dict) and item.get("name") == MEMORY_NAME
            ),
            None,
        )
    if not isinstance(memory, dict):
        raise RuntimeError("AgentCore CLI did not add PellierMemory")

    memory["eventExpiryDuration"] = 30
    memory["strategies"] = [
        {
            "type": "USER_PREFERENCE",
            "name": MEMORY_STRATEGY_NAME,
            "description": "Extract durable shopper preferences",
            "namespaceTemplates": [MEMORY_NAMESPACE],
        }
    ]
    memory["tags"] = {
        "Project": "pellier",
        "PellierWorkshopId": workshop_id,
    }
    project["$schema"] = "https://schema.agentcore.aws.dev/v1/agentcore.json"
    project.setdefault("tags", {}).update(
        {
            "Project": "pellier",
            "PellierWorkshopId": workshop_id,
        }
    )
    _write_json(config_path, project)
    _write_json(
        root / "agentcore" / "aws-targets.json",
        [{"name": "default", "account": account_id, "region": region}],
    )


def _read_deployed_memory(root: Path) -> dict[str, Any]:
    state_path = root / "agentcore" / ".cli" / "deployed-state.json"
    state = _read_json(state_path)
    targets = state.get("targets", {})
    target = targets.get("default") if isinstance(targets, dict) else None
    resources = target.get("resources", {}) if isinstance(target, dict) else {}
    memories = resources.get("memories", {}) if isinstance(resources, dict) else {}
    memory = memories.get(MEMORY_NAME) if isinstance(memories, dict) else None
    if not isinstance(memory, dict) or not memory.get("memoryId"):
        raise RuntimeError(
            "AgentCore CLI deployed state is missing memories.PellierMemory"
        )
    return memory


def _seed_memory(
    *,
    repo: Path,
    memory_id: str,
    region: str,
    env: dict[str, str],
) -> dict[str, Any]:
    process = _run(
        [
            sys.executable,
            str(repo / "scripts" / "deploy" / "seed_agentcore_memory.py"),
            "--memory-id",
            memory_id,
            "--region",
            region,
        ],
        cwd=repo,
        env=env,
    )
    payload = json.loads(process.stdout)
    if (
        payload.get("status") != "ready"
        or payload.get("resource_status") != "ACTIVE"
    ):
        raise RuntimeError("AgentCore Memory seed did not verify ACTIVE")
    return payload


def provision(
    *,
    repo: Path,
    region: str,
    workshop_id: str,
    env: dict[str, str],
) -> dict[str, Any]:
    session = boto3.Session(region_name=region)
    sts = session.client("sts", config=AWS_CONFIG)
    account_id = str(sts.get_caller_identity()["Account"])

    root = _scaffold_project(repo=repo, env=env)
    _configure_memory(
        root=root,
        account_id=account_id,
        region=region,
        workshop_id=workshop_id,
        env=env,
    )
    _agentcore(root, "validate", "--json", env=env)
    _agentcore(root, "deploy", "--yes", "--json", env=env)

    deployed = _read_deployed_memory(root)
    memory_id = str(deployed["memoryId"])
    seed = _seed_memory(
        repo=repo,
        memory_id=memory_id,
        region=region,
        env=env,
    )
    return {
        "status": "ready",
        "region": region,
        "cli": {
            "package": AGENTCORE_CLI,
            "project_root": str(root),
        },
        "memory": {
            "memory_id": memory_id,
            "memory_arn": deployed.get("memoryArn"),
            "resource_status": seed["resource_status"],
            "strategy": seed["strategy"],
            "seed": seed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", default=os.environ.get("REPO_PATH", "."))
    parser.add_argument(
        "--output-json",
        default="/tmp/pellier-agentcore-memory.json",
    )
    arguments = parser.parse_args()

    repo = Path(arguments.repo_path).resolve()
    output_path = Path(arguments.output_json)
    region = os.environ.get("AWS_REGION", "").strip()
    workshop_id = os.environ.get("WORKSHOP_ID", "").strip() or "unknown"
    if not region:
        print("AWS_REGION is required", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env.update({"AWS_REGION": region, "AWS_DEFAULT_REGION": region})
    result: dict[str, Any]
    try:
        result = provision(
            repo=repo,
            region=region,
            workshop_id=workshop_id,
            env=env,
        )
        output_path.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        output_path.chmod(0o600)
        print(json.dumps({"status": "ready", "output_json": str(output_path)}))
        return 0
    except (ClientError, RuntimeError, OSError, ValueError) as exc:
        result = {
            "status": "failed",
            "region": region,
            "cli": {"package": AGENTCORE_CLI},
            "error": str(exc),
        }
        output_path.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        output_path.chmod(0o600)
        print(
            json.dumps({"status": "failed", "output_json": str(output_path)}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
