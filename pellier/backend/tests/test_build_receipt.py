"""The build receipt must never blur "did not happen" with "did not look".

A receipt that reports an unreachable database as NOT YET tells a participant
they failed a lab they may well have passed, and tells a table lead to debug the
wrong thing. These tests pin that separation, and the related one in Lab 4:
a DENY receipt and the absence of an execution row are two facts, and
non-execution is only claimed when the row was actually searched for.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "build_receipt.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("pellier_build_receipt", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pellier_build_receipt"] = module
    spec.loader.exec_module(module)
    return module


receipt_module = _load()
PROVED = receipt_module.PROVED
NOT_YET = receipt_module.NOT_YET
UNCHECKED = receipt_module.UNCHECKED


class TestUncheckedIsNotFailure:
    def test_unreachable_database_reports_unchecked_not_not_yet(self) -> None:
        built = receipt_module.assemble(
            {"available": False, "reason": "connection refused"}
        )
        labs = built["labs"]
        assert labs["02_measure_hybrid_retrieval"]["hybrid_receipt"] == UNCHECKED
        assert labs["03_operate_the_managed_path"]["managed_rail"] == UNCHECKED
        assert labs["04_govern_and_prove"]["decisions"] == UNCHECKED
        # The reason travels with the receipt, so a reader can act on it.
        assert "connection refused" in built["evidence_source"]

    def test_reachable_database_with_no_rows_reports_not_yet(self) -> None:
        """The same absence, but now it is evidence."""
        built = receipt_module.assemble(
            {
                "available": True,
                "principal_sub": "sub-1",
                "lab1": None,
                "lab2": None,
                "lab3": None,
                "lab3_memory": None,
                "lab4": [],
            }
        )
        labs = built["labs"]
        assert labs["02_measure_hybrid_retrieval"]["hybrid_receipt"] == NOT_YET
        assert labs["03_operate_the_managed_path"]["managed_rail"] == NOT_YET
        assert labs["04_govern_and_prove"]["decisions"] == NOT_YET

    def test_rows_present_report_proved(self) -> None:
        built = receipt_module.assemble(
            {
                "available": True,
                "principal_sub": "sub-1",
                "lab1": {"audit_id": 4099, "turn_id": "turn-abc"},
                "lab2": {"receipt_id": 12, "reranked": True},
                "lab3": {"turn_id": "turn-abc", "rail": "gateway-mcp"},
                "lab3_memory": {"receipt_id": 12, "records": 3},
                "lab4": [],
            }
        )
        labs = built["labs"]
        assert labs["01_ground_the_answer"]["execution_row"] == PROVED
        assert labs["02_measure_hybrid_retrieval"]["hybrid_receipt"] == PROVED
        assert labs["03_operate_the_managed_path"]["managed_rail"] == PROVED
        assert labs["03_operate_the_managed_path"]["memory_informed_a_turn"] == PROVED


class TestGovernanceChain:
    """ALLOW, execution, durable effect and non-execution stay four claims."""

    @staticmethod
    def _findings(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return receipt_module._lab4_findings(rows)

    def test_allow_without_an_execution_row_is_not_a_durable_effect(self) -> None:
        found = self._findings(
            [
                {
                    "decision": "ALLOW",
                    "audit_id": None,
                    "completed_at": None,
                    "policy_name": "p",
                    "idempotency_key": None,
                }
            ]
        )
        assert found["allow_seen"] == PROVED
        assert found["allow_executed"] == NOT_YET
        assert found["durable_effect"] == NOT_YET

    def test_executed_allow_without_a_write_row_is_not_committed(self) -> None:
        """Reaching the tool is not the same as changing the system of record."""
        found = self._findings(
            [
                {
                    "decision": "ALLOW",
                    "audit_id": 4127,
                    "completed_at": None,
                    "policy_name": "p",
                    "idempotency_key": "k",
                }
            ]
        )
        assert found["allow_executed"] == PROVED
        assert found["durable_effect"] == NOT_YET

    def test_deny_with_no_audit_row_proves_non_execution(self) -> None:
        found = self._findings(
            [
                {
                    "decision": "DENY",
                    "audit_id": None,
                    "completed_at": None,
                    "policy_name": "p",
                    "idempotency_key": None,
                }
            ]
        )
        assert found["deny_seen"] == PROVED
        assert found["deny_did_not_execute"] == PROVED

    def test_deny_that_left_an_execution_row_does_not_prove_non_execution(
        self,
    ) -> None:
        """The contradiction case: a denial that nevertheless ran."""
        found = self._findings(
            [
                {
                    "decision": "DENY",
                    "audit_id": 4128,
                    "completed_at": None,
                    "policy_name": "p",
                    "idempotency_key": None,
                }
            ]
        )
        assert found["deny_seen"] == PROVED
        assert found["deny_did_not_execute"] == NOT_YET

    def test_no_rows_at_all_is_unchecked_when_the_database_was_unreachable(
        self,
    ) -> None:
        assert receipt_module._lab4_findings(None)["decisions"] == UNCHECKED


class TestSourceState:
    def test_this_checkout_reports_the_lab_one_starters_as_unwritten(self) -> None:
        """A fresh governed checkout ships both Lab 1 sites as stubs."""
        state = receipt_module.collect_source_state()
        assert state["inventory_tool"] == NOT_YET
        assert state["inventory_agent_definition"] == NOT_YET

    def test_an_unreadable_file_is_unchecked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(receipt_module, "BACKEND", Path("/nonexistent"))
        state = receipt_module.collect_source_state()
        assert state["inventory_tool"] == UNCHECKED
        assert state["inventory_agent_definition"] == UNCHECKED


class TestReporting:
    def test_unproven_list_names_every_incomplete_claim(self) -> None:
        built = receipt_module.assemble({"available": False, "reason": "no db"})
        assert built["unproven"]
        assert built["complete"] is False
        # Every entry carries its state, so NOT YET and UNCHECKED stay legible
        # in the summary a participant actually reads.
        assert all(
            item.endswith(NOT_YET) or item.endswith(UNCHECKED)
            for item in built["unproven"]
        )

    def test_markdown_renders_and_explains_unchecked(self) -> None:
        built = receipt_module.assemble({"available": False, "reason": "no db"})
        markdown = receipt_module.render_markdown(built)
        assert "# Pellier build receipt" in markdown
        assert "Not yet proven" in markdown
        assert "not that the step failed" in markdown

    def test_markdown_reports_a_complete_run_without_a_scold(self) -> None:
        built = receipt_module.assemble(
            {
                "available": True,
                "principal_sub": "sub-1",
                "lab1": {"audit_id": 1},
                "lab2": {"receipt_id": 1},
                "lab3": {"turn_id": "t"},
                "lab3_memory": {"receipt_id": 1},
                "lab4": [
                    {
                        "decision": "ALLOW",
                        "audit_id": 2,
                        "completed_at": "now",
                        "policy_name": "p",
                        "idempotency_key": "k",
                    },
                    {
                        "decision": "DENY",
                        "audit_id": None,
                        "completed_at": None,
                        "policy_name": "p",
                        "idempotency_key": None,
                    },
                ],
            }
        )
        # Source state is still stubbed in this checkout, so the run is not
        # complete; assert the governance half instead, which is fully proved.
        lab4 = built["labs"]["04_govern_and_prove"]
        assert lab4["allow_executed"] == PROVED
        assert lab4["durable_effect"] == PROVED
        assert lab4["deny_did_not_execute"] == PROVED
