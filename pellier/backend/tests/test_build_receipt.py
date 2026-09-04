"""The build receipt must never blur "did not happen" with "did not look".

A receipt that reports an unreachable database as NOT YET tells a participant
they failed a lab they may well have passed, and tells a table lead to debug the
wrong thing. These tests pin that separation, and the related one in Lab 4:
a DENY receipt and the absence of an execution row are two facts, and
non-execution is only claimed when the row was actually searched for.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
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


# ---------------------------------------------------------------------------
# Run scoping and the strict contract
# ---------------------------------------------------------------------------

RUN_ID = "run-0123456789ab"


class FakeCursor:
    def __init__(self, conn: "FakeConn") -> None:
        self.conn = conn
        self._rows: list = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self.conn.queries.append((sql, params))
        for fragment, rows in self.conn.rows.items():
            if fragment in sql:
                self._rows = list(rows)
                return
        self._rows = []

    def fetchone(self) -> Any:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> Any:
        return list(self._rows)


class FakeConn:
    def __init__(self, rows: dict[str, list]) -> None:
        self.rows = rows
        self.queries: list = []

    def __enter__(self) -> "FakeConn":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)


def _env_file(tmp_path: Path) -> Path:
    env = tmp_path / ".env"
    env.write_text(
        "DB_HOST=db\nDB_NAME=pellier\nDB_USER=u\nDB_PASSWORD=p\n", encoding="utf-8"
    )
    return env


class TestRunScope:
    def test_a_run_id_scopes_every_lab_query(self, tmp_path: Path) -> None:
        conn = FakeConn({"to_regclass": [{"installed": "pellier.workshop_runs"}]})
        evidence = receipt_module.read_evidence(
            _env_file(tmp_path), "sub-1", run_id=RUN_ID, connect=lambda dsn: conn
        )
        assert evidence["available"] is True
        assert evidence["run_id"] == RUN_ID
        assert evidence["run_scope"] == "run_id"
        lab_queries = [(sql, params) for sql, params in conn.queries if "%(sub)s" in sql]
        assert len(lab_queries) == 5, [q[0][:40] for q in conn.queries]
        for sql, params in lab_queries:
            assert "%(run)s" in sql, sql
            assert params["run"] == RUN_ID
        # Rows the Lambda writes through the Data API carry no run_id, so the
        # governance query also admits rows created after the run started.
        lab4 = [sql for sql, _ in lab_queries if "governed_receipts gr" in sql][0]
        assert "pellier.workshop_runs" in lab4
        assert "gr.run_id IS NULL" in lab4

    def test_the_default_connector_is_the_public_one(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Sibling scripts reach psycopg through a supported name, not a private one."""
        conn = FakeConn({})
        used: list = []

        def _connector() -> Any:
            used.append(True)
            return lambda dsn: conn

        monkeypatch.setattr(receipt_module, "psycopg_connector", _connector)
        evidence = receipt_module.read_evidence(_env_file(tmp_path), "sub-1")
        assert used == [True]
        assert evidence["available"] is True

    def test_without_a_run_id_nothing_is_scoped(self, tmp_path: Path) -> None:
        conn = FakeConn({})
        evidence = receipt_module.read_evidence(
            _env_file(tmp_path), "sub-1", connect=lambda dsn: conn
        )
        assert evidence["run_scope"] == "none"
        assert all("run_id" not in sql for sql, _ in conn.queries)

    def test_missing_migration_049_is_reported_and_left_unscoped(
        self, tmp_path: Path
    ) -> None:
        conn = FakeConn({"to_regclass": [{"installed": None}]})
        evidence = receipt_module.read_evidence(
            _env_file(tmp_path), "sub-1", run_id=RUN_ID, connect=lambda dsn: conn
        )
        assert evidence["run_id"] == RUN_ID
        assert evidence["run_scope"].startswith("unavailable")
        assert "049" in evidence["run_scope"]
        assert all("%(run)s" not in sql for sql, _ in conn.queries if "%(sub)s" in sql)

    def test_the_newest_principal_is_looked_up_inside_the_run(self, tmp_path: Path) -> None:
        conn = FakeConn(
            {
                "to_regclass": [{"installed": "pellier.workshop_runs"}],
                "MAX(created_at)": [{"principal_sub": "sub-9", "last_seen": "t"}],
            }
        )
        evidence = receipt_module.read_evidence(
            _env_file(tmp_path), None, run_id=RUN_ID, connect=lambda dsn: conn
        )
        assert evidence["principal_sub"] == "sub-9"
        principal_sql = [sql for sql, _ in conn.queries if "MAX(created_at)" in sql][0]
        assert "run_id = %(run)s" in principal_sql

    def test_the_receipt_carries_the_run(self) -> None:
        built = receipt_module.assemble(
            {"available": True, "run_id": RUN_ID, "run_scope": "run_id", "lab4": []}
        )
        assert built["run_id"] == RUN_ID
        assert built["run_scope"] == "run_id"
        assert f"`{RUN_ID}`" in receipt_module.render_markdown(built)


def _complete_evidence() -> dict[str, Any]:
    return {
        "available": True,
        "principal_sub": "sub-1",
        "run_id": RUN_ID,
        "run_scope": "run_id",
        "lab1": {"audit_id": 1},
        "lab2": {"receipt_id": 1},
        "lab3": {"turn_id": "t", "rail": "gateway-mcp"},
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


class TestStrict:
    @pytest.fixture(autouse=True)
    def _wired_source(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            receipt_module,
            "collect_source_state",
            lambda: {"inventory_tool": PROVED, "inventory_agent_definition": PROVED},
        )
        monkeypatch.setattr(receipt_module, "collect_provenance", lambda: {})

    def test_strict_exits_zero_only_when_every_claim_is_proved(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            receipt_module, "read_evidence", lambda env, sub, run_id=None: _complete_evidence()
        )
        assert receipt_module.main(["--strict", "--run-id", RUN_ID]) == 0
        assert "STRICT" not in capsys.readouterr().err

    def test_strict_prints_the_missing_keys_and_exits_one(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        evidence = _complete_evidence()
        evidence["lab3"] = None
        evidence["lab4"] = []
        monkeypatch.setattr(
            receipt_module, "read_evidence", lambda env, sub, run_id=None: evidence
        )
        assert receipt_module.main(["--strict", "--run-id", RUN_ID]) == 1
        err = capsys.readouterr().err
        assert RUN_ID in err
        assert "03_operate_the_managed_path.managed_rail: NOT YET" in err
        assert "04_govern_and_prove.deny_did_not_execute: NOT YET" in err

    def test_strict_refuses_a_receipt_that_could_not_be_scoped_to_the_run(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Every claim is PROVED, but off rows nobody can attribute to this run."""
        evidence = _complete_evidence()
        evidence["run_scope"] = receipt_module.RUN_SCOPE_UNAVAILABLE
        monkeypatch.setattr(
            receipt_module, "read_evidence", lambda env, sub, run_id=None: evidence
        )
        assert receipt_module.main(["--strict", "--run-id", RUN_ID]) == 1
        err = capsys.readouterr().err
        assert "049" in err
        assert RUN_ID in err

    def test_default_mode_still_exits_zero_when_the_run_scope_is_unavailable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        evidence = _complete_evidence()
        evidence["run_scope"] = receipt_module.RUN_SCOPE_UNAVAILABLE
        monkeypatch.setattr(
            receipt_module, "read_evidence", lambda env, sub, run_id=None: evidence
        )
        assert receipt_module.main(["--run-id", RUN_ID]) == 0
        assert "# Pellier build receipt" in capsys.readouterr().out

    def test_strict_without_a_run_id_refuses(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(receipt_module, "_resolve_run_id", lambda explicit: None)
        monkeypatch.setattr(
            receipt_module, "read_evidence", lambda env, sub, run_id=None: _complete_evidence()
        )
        assert receipt_module.main(["--strict"]) == 1
        assert "workshop-start" in capsys.readouterr().err

    def test_default_mode_still_exits_zero_on_an_incomplete_run(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        evidence = _complete_evidence()
        evidence["lab3"] = None
        monkeypatch.setattr(
            receipt_module, "read_evidence", lambda env, sub, run_id=None: evidence
        )
        assert receipt_module.main(["--run-id", RUN_ID]) == 0
        assert "# Pellier build receipt" in capsys.readouterr().out

    def test_a_malformed_run_id_is_refused_before_any_query(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert receipt_module.main(["--run-id", "run-nope"]) == 2
        assert "run-<12 hex>" in capsys.readouterr().err

    def test_the_current_run_is_the_default_scope(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def _read(env: Any, sub: Any, run_id: Any = None) -> dict[str, Any]:
            seen["run_id"] = run_id
            return _complete_evidence()

        monkeypatch.setattr(receipt_module, "read_evidence", _read)
        monkeypatch.setenv("PELLIER_RUN_ID", RUN_ID)
        assert receipt_module.main(["--json", "/dev/null"]) == 0
        assert seen["run_id"] == RUN_ID


# ---------------------------------------------------------------------------
# Lab 3: what the managed rail actually leaves behind
# ---------------------------------------------------------------------------

_NAMED_PARAM = re.compile(r"%\((\w+)\)s")
SUB = "sub-theo"


class SqliteLab3:
    """Runs the receipt's real Lab 3 SQL over fixture rows, in SQLite.

    ``FakeConn`` answers by SQL fragment, so it cannot catch a predicate that no
    row a real writer produces can satisfy. The Lab 3 query is ordinary SQL plus
    the JSON ``->>`` operator, and SQLite understands both once the ``pellier``
    schema is attached as a database and psycopg's ``%(name)s`` is rewritten to
    ``:name``. The columns are the ones the real writers populate
    (``services/governed_turn_receipt.py``, ``scripts/deploy/common/dataapi.py``)
    plus migration 049's ``run_id``.
    """

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("ATTACH DATABASE ':memory:' AS pellier")
        self._conn.execute(
            "CREATE TABLE pellier.tool_audit ("
            "audit_id INTEGER PRIMARY KEY, session_id TEXT, tool TEXT, caller TEXT, "
            "args TEXT, result TEXT, latency_ms INTEGER, run_id TEXT)"
        )
        self._conn.execute(
            "CREATE TABLE pellier.governed_turn_receipts ("
            "turn_id TEXT PRIMARY KEY, session_id TEXT, principal_sub TEXT, rail TEXT, "
            "terminal_status TEXT, created_at TEXT, run_id TEXT)"
        )

    def turn(
        self,
        *,
        turn_id: str,
        run_id: str | None,
        rail: str = "gateway-mcp",
        created_at: str = "2026-09-04T10:00:00Z",
    ) -> None:
        """Record the turn receipt the application pool writes for one turn."""
        self._conn.execute(
            "INSERT INTO pellier.governed_turn_receipts "
            "(turn_id, session_id, principal_sub, rail, terminal_status, created_at, "
            "run_id) VALUES (?, 'lab3-start-1', ?, ?, 'complete', ?, ?)",
            (turn_id, SUB, rail, created_at, run_id),
        )

    def gateway_mutation(self, *, audit_id: int, turn_id: str) -> None:
        """Record the row the MCP Lambda writes for a mutation. ``run_id`` is NULL."""
        self._conn.execute(
            "INSERT INTO pellier.tool_audit "
            "(audit_id, session_id, tool, caller, args, result, latency_ms, run_id) "
            "VALUES (?, 'gateway-CUST-THEO', 'initiate_return', 'gateway', ?, '{}', "
            "412, NULL)",
            (audit_id, json.dumps({"turn_id": turn_id})),
        )

    def lab3(self) -> Any:
        sql = receipt_module._scoped(receipt_module._LAB3, "lab3", True)
        cursor = self._conn.execute(
            _NAMED_PARAM.sub(r":\1", sql), {"sub": SUB, "run": RUN_ID}
        )
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SqliteLab3":
        return self

    def __exit__(self, *exc: Any) -> bool:
        self.close()
        return False


class TestLab3ManagedRailProof:
    """Lab 3 must be provable by completing Lab 3.

    Theo's journey ends at a pending review (``tests/golden/journeys.json``:
    ``endsAt: proposal``), so a correct Lab 3 run performs no mutation. Only the
    three mutation tools leave a ``caller = 'gateway'`` row, and Gateway reads
    leave no ``tool_audit`` row at all, so the rail proof has to be the turn
    receipt: written through the application pool, run-stamped by migration 049,
    and carrying the rail that served the turn.
    """

    def test_lab3_as_designed_yields_a_row_with_no_gateway_mutation(self) -> None:
        with SqliteLab3() as db:
            db.turn(turn_id="turn-theo-ceramics", run_id=RUN_ID)
            row = db.lab3()
        assert row is not None, "a managed turn with no mutation must still prove Lab 3"
        assert row["rail"] == "gateway-mcp"
        assert row["turn_id"] == "turn-theo-ceramics"
        assert row["gateway_mutation_audit_id"] is None

    def test_that_row_proves_the_managed_rail_in_the_receipt(self) -> None:
        with SqliteLab3() as db:
            db.turn(turn_id="turn-theo-ceramics", run_id=RUN_ID)
            row = db.lab3()
        built = receipt_module.assemble(
            {"available": True, "lab3": row, "lab3_memory": {"receipt_id": 1}, "lab4": []}
        )
        assert built["labs"]["03_operate_the_managed_path"]["managed_rail"] == PROVED

    def test_an_in_process_only_run_leaves_lab3_unproved(self) -> None:
        """The check cannot pass vacuously: an unswitched run still fails."""
        with SqliteLab3() as db:
            db.turn(turn_id="turn-in-process", run_id=RUN_ID, rail="in-process")
            row = db.lab3()
        assert row is None
        built = receipt_module.assemble(
            {"available": True, "lab3": row, "lab3_memory": None, "lab4": []}
        )
        assert built["labs"]["03_operate_the_managed_path"]["managed_rail"] == NOT_YET

    def test_another_runs_managed_turn_does_not_count(self) -> None:
        with SqliteLab3() as db:
            db.turn(turn_id="turn-someone-else", run_id="run-ffffffffffff")
            assert db.lab3() is None

    def test_a_gateway_mutation_is_reported_as_labelled_detail(self) -> None:
        """Present it as the optional mutation evidence it is, not as the proof."""
        with SqliteLab3() as db:
            db.turn(turn_id="turn-theo-return", run_id=RUN_ID)
            db.gateway_mutation(audit_id=4127, turn_id="turn-theo-return")
            row = db.lab3()
        assert row["gateway_mutation_audit_id"] == 4127
        built = receipt_module.assemble(
            {"available": True, "lab3": row, "lab3_memory": {"receipt_id": 1}, "lab4": []}
        )
        markdown = receipt_module.render_markdown(built)
        assert "gateway_mutation_audit_id=4127" in markdown

    def test_strict_counts_lab3_satisfied_without_any_gateway_row(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with SqliteLab3() as db:
            db.turn(turn_id="turn-theo-ceramics", run_id=RUN_ID)
            row = db.lab3()
        evidence = _complete_evidence()
        evidence["lab3"] = row
        monkeypatch.setattr(
            receipt_module,
            "collect_source_state",
            lambda: {"inventory_tool": PROVED, "inventory_agent_definition": PROVED},
        )
        monkeypatch.setattr(receipt_module, "collect_provenance", lambda: {})
        monkeypatch.setattr(
            receipt_module, "read_evidence", lambda env, sub, run_id=None: evidence
        )
        assert receipt_module.main(["--strict", "--run-id", RUN_ID]) == 0
        assert "STRICT" not in capsys.readouterr().err
