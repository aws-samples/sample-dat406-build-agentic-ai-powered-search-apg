"""Safety and parity checks for the local golden-journey helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "seed_local_golden_journeys.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("seed_local_golden_journeys", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


seed = _load_script()


def test_hash_matches_the_business_write_path() -> None:
    from services.business_logic import write_request_hash

    assert seed.write_request_hash("initiate_return", seed.THEO_ARGS) == (
        write_request_hash("initiate_return", **seed.THEO_ARGS)
    )


@pytest.mark.parametrize("host", ["db.example.com", "10.0.1.25", "aurora.cluster"])
def test_remote_database_hosts_are_refused(host: str) -> None:
    with pytest.raises(SystemExit, match="non-loopback"):
        seed.require_local_target(host, "pellier_dev")


@pytest.mark.parametrize("database", ["pellier", "production", "postgres"])
def test_non_development_database_names_are_refused(database: str) -> None:
    with pytest.raises(SystemExit, match="must end in _dev"):
        seed.require_local_target("127.0.0.1", database)


def test_seed_writes_workflow_state_only() -> None:
    sql = seed.seed_sql().lower()
    assert "insert into pellier.approvals" in sql
    assert "insert into pellier.governed_turn_receipts" in sql
    assert "on conflict (customer_id, tool, action_hash)" in sql
    assert "do nothing" in sql
    assert "update pellier.approvals" not in sql
    assert "delete from pellier.approvals" not in sql
    for forbidden in (
        "insert into pellier.returns",
        "insert into pellier.store_credits",
        "insert into pellier.tool_audit",
        "insert into pellier.execution_receipts",
        "insert into pellier.governed_receipts",
    ):
        assert forbidden not in sql


def test_handoff_is_bound_to_the_review_and_explicitly_local() -> None:
    sql = seed.seed_sql()
    assert "UNTRUSTED_SHOPPER_CONTEXT" in sql
    assert "WAITING_FOR_HUMAN" in sql
    assert "'reviewId', v_review.id" in sql
    assert "'actionHash', v_review.action_hash" in sql
    assert '"managed":false' in sql
    assert "Existing immutable turn receipt has no handoff" in sql
