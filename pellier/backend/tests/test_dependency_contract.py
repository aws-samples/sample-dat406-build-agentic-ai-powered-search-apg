"""The documented Python setup must install the SDK model this workshop proves."""

from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def test_readme_installs_the_hashed_backend_lock() -> None:
    readme = (REPO / "README.md").read_text()

    assert "python3 -m venv .venv" in readme
    assert "pip install --require-hashes -r requirements.lock" in readme
    assert "./.venv/bin/python -m pytest -q" in readme


def test_unlocked_requirements_reject_the_old_agentcore_service_model() -> None:
    requirements = (REPO / "pellier/backend/requirements.txt").read_text()

    assert "boto3>=1.43.51" in requirements
    assert "botocore>=1.43.51" in requirements


def test_active_botocore_model_understands_policy_enforcement_mode() -> None:
    """The release interpreter must preserve this field when it calls AgentCore."""
    import botocore.session

    model = botocore.session.get_session().get_service_model(
        "bedrock-agentcore-control"
    )

    assert "enforcementMode" in model.operation_model(
        "UpdatePolicy"
    ).input_shape.members
    assert "enforcementMode" in model.operation_model(
        "GetPolicy"
    ).output_shape.members
