"""Atomicity checks for governed Gateway mutations and their Aurora audit rows."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY = REPO_ROOT / "scripts" / "deploy"

if str(DEPLOY) not in sys.path:
    sys.path.insert(0, str(DEPLOY))


def _load_server(filename: str, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, DEPLOY / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def _dataapi() -> ModuleType:
    """Return the shared transport module, which owns the only Data API client.

    The seam moved here when the surface servers stopped each constructing a
    client of their own. Patching it in one place is the point: a mutation and
    its audit row must be issued through the same client, in the same
    transaction, or the atomicity these tests assert is not real.
    """
    import common.dataapi as dataapi

    return dataapi


class _DataApi:
    def __init__(self, result: dict[str, Any], *, fail_audit: bool = False) -> None:
        self.result = result
        self.fail_audit = fail_audit
        self.statements: list[dict[str, Any]] = []
        self.commits: list[dict[str, Any]] = []
        self.rollbacks: list[dict[str, Any]] = []

    def begin_transaction(self, **kwargs: Any) -> dict[str, str]:
        return {"transactionId": "tx-governed-1"}

    def execute_statement(self, **kwargs: Any) -> dict[str, Any]:
        self.statements.append(kwargs)
        if "INSERT INTO pellier.tool_audit" in kwargs["sql"]:
            if self.fail_audit:
                raise RuntimeError("audit insert failed")
            return {}
        return {
            "columnMetadata": [{"name": "result"}],
            "records": [[{"stringValue": __import__("json").dumps(self.result)}]],
        }

    def commit_transaction(self, **kwargs: Any) -> None:
        self.commits.append(kwargs)

    def rollback_transaction(self, **kwargs: Any) -> None:
        self.rollbacks.append(kwargs)


def _assert_shared_transaction(client: _DataApi) -> None:
    assert len(client.statements) == 2
    assert {call["transactionId"] for call in client.statements} == {
        "tx-governed-1"
    }
    assert len(client.commits) == 1
    assert not client.rollbacks


def test_process_return_commits_mutation_and_audit_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_server("pellier_experience_server.py", "experience_atomic")
    client = _DataApi({"status": "success", "return_id": 42})
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    result = module.process_return(
        "CUST-MARCO",
        21,
        "damaged",
        "return-atomic-1",
        audit_arguments={
            "customer_id": "CUST-MARCO",
            "product_id": 21,
            "reason": "damaged",
            "idempotency_key": "return-atomic-1",
            "turn_id": "turn-" + ("a" * 32),
        },
    )

    assert result["status"] == "success"
    _assert_shared_transaction(client)


def test_process_return_rolls_back_when_audit_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_server("pellier_experience_server.py", "experience_rollback")
    client = _DataApi(
        {"status": "success", "return_id": 42},
        fail_audit=True,
    )
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    result = module.process_return(
        "CUST-MARCO",
        21,
        "damaged",
        "return-atomic-2",
    )

    assert result == {"status": "error", "message": "audit insert failed"}
    assert not client.commits
    assert len(client.rollbacks) == 1


def test_restock_commits_mutation_and_audit_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_server("pellier_search_server.py", "restock_atomic")
    client = _DataApi(
        {
            "status": "success",
            "product_id": 21,
            "name": "Linen Shirt",
            "new_quantity": 12,
            "warehouse_id": "BK-01",
        }
    )
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    result = module.restock_shelf(
        21,
        4,
        "restock-atomic-1",
        audit_arguments={
            "product_id": 21,
            "quantity": 4,
            "idempotency_key": "restock-atomic-1",
            "turn_id": "turn-" + ("b" * 32),
        },
    )

    assert result["status"] == "success"
    _assert_shared_transaction(client)


def test_restock_rolls_back_when_audit_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_server("pellier_search_server.py", "restock_rollback")
    client = _DataApi(
        {
            "status": "success",
            "product_id": 21,
            "new_quantity": 12,
        },
        fail_audit=True,
    )
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        module.restock_shelf(21, 4, "restock-atomic-2")

    assert not client.commits
    assert len(client.rollbacks) == 1
