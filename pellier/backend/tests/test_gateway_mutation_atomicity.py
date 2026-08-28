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
    """A Data API stand-in that records which statements shared a transaction.

    Statement order and ``transactionId`` presence are the whole point here: RLS
    is only real if the role and principal bindings precede the protected
    statement in the same server-side transaction, and the audit receipt only
    survives a rollback if it is issued outside one.
    """

    def __init__(
        self,
        result: dict[str, Any],
        *,
        fail_audit: bool = False,
        fail_protected: bool = False,
    ) -> None:
        self.result = result
        self.fail_audit = fail_audit
        self.fail_protected = fail_protected
        self.statements: list[dict[str, Any]] = []
        self.commits: list[dict[str, Any]] = []
        self.rollbacks: list[dict[str, Any]] = []

    def begin_transaction(self, **kwargs: Any) -> dict[str, str]:
        return {"transactionId": "tx-governed-1"}

    def execute_statement(self, **kwargs: Any) -> dict[str, Any]:
        self.statements.append(kwargs)
        sql = kwargs.get("sql", "")
        if "INSERT INTO pellier.tool_audit" in sql:
            if self.fail_audit:
                raise RuntimeError("audit insert failed")
            return {}
        if self.fail_protected and (
            "process_return_idempotent" in sql or "apply_store_credit" in sql
        ):
            # Stands in for an RLS refusal or a CHECK violation: the protected
            # statement is the one that fails, not the audit.
            raise RuntimeError("new row violates row-level security policy")
        if "SET LOCAL ROLE" in sql or "set_config(" in sql:
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
    """The ORIGINAL contract, still correct for `restock_inventory`.

    The audit-survival change is scoped to the two reviewable actions
    (`initiate_return`, `issue_credit`), which are the ones a human confirms and
    the ones whose Aurora denial has to stay provable. `restock_inventory` is an
    inventory action with no review path, so its boundary is deliberately
    unchanged rather than swept along.
    """
    assert len(client.statements) == 2
    assert {call["transactionId"] for call in client.statements} == {
        "tx-governed-1"
    }
    assert len(client.commits) == 1
    assert not client.rollbacks


def test_initiate_return_binds_the_runtime_role_and_customer_subject_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RLS is only real if the role and principal precede the protected statement.

    The Gateway rail used to reach Aurora over the Data API as the secret's user,
    which owns the tables and therefore bypassed Row-Level Security entirely. Two
    settings now run first, on the same transaction: a non-owner role, and the
    customer subject.
    """
    module = _load_server("pellier_experience_server.py", "experience_rls")
    client = _DataApi({"status": "success", "return_id": 42})
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    module.initiate_return(
        "CUST-MARCO", 21, "damaged", "return-rls-1",
        customer_subject="sub-marco",
    )

    statements = [
        call.get("sql", "") for call in client.statements
        if call.get("transactionId")
    ]
    assert statements, "no statement ran inside a transaction"
    assert "SET LOCAL ROLE pellier_agent" in statements[0], (
        f"the runtime role is not bound first; got {statements[0]!r}"
    )
    assert "set_config('pellier.principal_sub'" in statements[1], (
        f"the customer subject is not bound second; got {statements[1]!r}"
    )
    protected = next(
        i for i, sql in enumerate(statements) if "process_return_idempotent" in sql
    )
    assert protected > 1, "the protected statement ran before the bindings"


def test_the_customer_subject_is_bound_not_the_operator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The two principals must not be interchangeable.

    Cedar authorizes the operator at the Gateway; RLS scopes the customer here.
    Binding the operator's subject would scope the transaction to the operator's
    own rows, and the write would fail for every client they are not mapped to.
    """
    module = _load_server("pellier_experience_server.py", "experience_subject")
    client = _DataApi({"status": "success", "return_id": 42})
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    module.initiate_return(
        "CUST-THEO", 37, "damaged", "return-subject-1",
        customer_subject="sub-theo",
    )

    bound = [
        call for call in client.statements
        if "set_config('pellier.principal_sub'" in call.get("sql", "")
    ]
    assert len(bound) == 1
    values = [
        p["value"]["stringValue"] for p in bound[0].get("parameters", [])
    ]
    assert values == ["sub-theo"]


def test_a_missing_customer_subject_binds_empty_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unmapped client resolves no scope, which denies rather than widens."""
    module = _load_server("pellier_experience_server.py", "experience_nosubject")
    client = _DataApi({"status": "success", "return_id": 42})
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    module.initiate_return("CUST-JESSICA", 42, "damaged", "return-nosubject-1")

    bound = [
        call for call in client.statements
        if "set_config('pellier.principal_sub'" in call.get("sql", "")
    ]
    assert len(bound) == 1, "the principal must be bound explicitly, not skipped"
    values = [p["value"]["stringValue"] for p in bound[0].get("parameters", [])]
    assert values == [""], (
        "a missing subject must bind an empty principal so the policies resolve "
        "no scope; leaving it unset is a silently unbound principal"
    )


def test_the_audit_receipt_survives_a_rolled_back_business_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The load-bearing change of Prompt 4's audit boundary.

    The receipt used to be written inside the mutation's transaction, so a
    rollback took it with it. That made the most important governance outcome
    unprovable: an action Cedar allowed, that entered the tool, and that Aurora
    then refused would leave no trace, and "nothing happened" became
    indistinguishable from "nothing was attempted".
    """
    module = _load_server("pellier_experience_server.py", "experience_survive")
    client = _DataApi({"status": "success", "return_id": 42}, fail_protected=True)
    monkeypatch.setattr(_dataapi(), "rds_client", client)

    result = module.initiate_return("CUST-MARCO", 21, "damaged", "return-survive-1")

    assert result["status"] == "error"
    assert len(client.rollbacks) == 1, "the business transaction must roll back"
    assert not client.commits, "nothing may commit in the business transaction"

    receipts = [
        call for call in client.statements
        if "INSERT INTO pellier.tool_audit" in call.get("sql", "")
    ]
    assert len(receipts) == 1, (
        f"expected exactly one surviving attempt receipt, got {len(receipts)}"
    )
    assert not receipts[0].get("transactionId"), (
        "the receipt is still inside a transaction, so a rollback would destroy it"
    )


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

    result = module.restock_inventory(
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
        module.restock_inventory(21, 4, "restock-atomic-2")

    assert not client.commits
    assert len(client.rollbacks) == 1
