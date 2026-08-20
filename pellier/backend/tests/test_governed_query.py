"""Unit contract for the governed natural-language query boundary.

These cover the parts that are decidable without a database: the wrapping that
makes structure the gate, the plan-inspection rules, and the evidence shape.
The rejection list itself is exercised against a real planner in
`test_governed_query_live.py`, because "PostgreSQL refuses this" is a claim
only PostgreSQL can settle.

Two bugs found during implementation are pinned here, both of the same shape —
a control that appears to work because it refuses too much or checks too
little:

  1. `SET LOCAL statement_timeout = %s` fails (`SET` takes no parameters), and
     because that error aborts every query the module looked like a perfect
     boundary while refusing legitimate questions too. Only a control case
     exposed it.
  2. Plain `EXPLAIN (FORMAT JSON)` omits `Schema`, so every relation looked
     schema-less and the allowlist filtered itself into an empty check. A
     relation with no resolvable schema must now be a rejection.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from services import governed_query as gq


# ---------------------------------------------------------------------------
# The wrap is what makes structure the gate
# ---------------------------------------------------------------------------


def test_wrap_makes_the_statement_a_subquery():
    wrapped = gq.wrap_statement("SELECT 1")

    assert wrapped.startswith("SELECT * FROM (")
    assert "AS governed_query" in wrapped


def test_wrap_owns_the_row_limit():
    """The cap must not depend on the generated SQL's own LIMIT."""
    wrapped = gq.wrap_statement("SELECT name FROM product_catalog LIMIT 100000")

    # The generated limit survives inside the subquery, but ours is outer and
    # therefore decides.
    assert wrapped.rstrip().endswith(f"LIMIT {gq.MAX_ROWS}")


def test_wrap_respects_an_explicit_lower_cap():
    assert gq.wrap_statement("SELECT 1", max_rows=5).rstrip().endswith("LIMIT 5")


def test_wrap_puts_a_newline_before_the_closing_paren():
    """A trailing line comment would otherwise comment out the paren.

    `SELECT 1 --` followed immediately by `)` changes the statement's meaning;
    the newline keeps the wrap intact.
    """
    wrapped = gq.wrap_statement("SELECT 1 -- trailing comment")

    assert "\n) AS governed_query" in wrapped


def test_wrap_is_not_a_string_prefix_check():
    """Guard against regressing to `startswith('select')`.

    The module must not gain a naive textual gate; the planner is the gate.
    """
    source = (
        __import__("pathlib")
        .Path(gq.__file__)
        .read_text()
        .lower()
    )
    assert 'startswith("select")' not in source
    assert "startswith('select')" not in source


# ---------------------------------------------------------------------------
# Plan inspection
# ---------------------------------------------------------------------------


def _scan(schema: Any, relation: str) -> Dict[str, Any]:
    return {"Node Type": "Seq Scan", "Schema": schema, "Relation Name": relation}


def _plan(*nodes: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"Plan": {"Node Type": "Limit", "Plans": list(nodes)}}]


def test_allowed_schema_passes():
    reason, schemas = gq.check_plan(_plan(_scan("pellier", "product_catalog")))

    assert reason is None
    assert schemas == ["pellier"]


def test_schema_outside_the_allowlist_is_rejected():
    reason, _schemas = gq.check_plan(_plan(_scan("pg_catalog", "pg_authid")))

    assert reason is not None
    assert "outside the allowed schemas" in reason
    assert "pg_catalog.pg_authid" in reason


def test_relation_with_no_resolvable_schema_is_rejected():
    """Regression: unknown schema must deny, not permit.

    Without `VERBOSE` the plan omits `Schema`, and treating that as acceptable
    let `SELECT rolname FROM pg_roles` through during implementation.
    """
    reason, _schemas = gq.check_plan(_plan(_scan(None, "pg_authid")))

    assert reason is not None
    assert "could not determine the schema" in reason


def test_nested_plans_are_inspected():
    """A subplan can reach a relation the outer node never mentions."""
    nested = _plan(
        {
            "Node Type": "Nested Loop",
            "Plans": [
                _scan("pellier", "orders"),
                {"Node Type": "SubPlan", "Plans": [_scan("pg_catalog", "pg_authid")]},
            ],
        }
    )

    reason, _schemas = gq.check_plan(nested)

    assert reason is not None
    assert "pg_catalog.pg_authid" in reason


def test_write_node_is_rejected_even_though_the_wrap_should_prevent_it():
    """Belt and braces: a silent write is the one failure worth catching twice."""
    reason, _schemas = gq.check_plan(
        _plan({"Node Type": "ModifyTable", "Operation": "Delete"})
    )

    assert reason == "plan contains a data-modifying node"


def test_a_relationless_plan_is_acceptable():
    """`SELECT 1` scans nothing and is harmless."""
    reason, schemas = gq.check_plan(_plan({"Node Type": "Result"}))

    assert reason is None
    assert schemas == []


# ---------------------------------------------------------------------------
# Precheck
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sql,expected",
    [
        ("", "empty statement"),
        ("   ", "empty statement"),
        ("SELECT 1" + "\x00", "statement contains a null byte"),
    ],
)
def test_precheck_rejections(sql, expected):
    assert gq.precheck(sql) == expected


def test_precheck_bounds_statement_length():
    reason = gq.precheck("SELECT " + "a" * gq.MAX_SQL_LENGTH)

    assert reason is not None and "exceeds" in reason


def test_precheck_passes_a_normal_statement():
    assert gq.precheck("SELECT name FROM product_catalog") is None


# ---------------------------------------------------------------------------
# Evidence shape
# ---------------------------------------------------------------------------


def test_evidence_carries_every_required_field():
    """The design's required evidence set for a governed query."""
    result = gq.GovernedQueryResult(
        accepted=True,
        turn_id="turn-1",
        principal_sub="sub-a",
        caller="agent",
        sql="SELECT 1",
        row_count=3,
        execution_outcome="success",
        latency_ms=12,
        schemas_read=["pellier"],
        receipt_id=9,
    )

    evidence = result.evidence()

    for field in (
        "turn_id",
        "principal_sub",
        "caller",
        "accepted",
        "validation",
        "role_used",
        "statement_timeout",
        "result_limit",
        "row_count",
        "execution_outcome",
        "receipt_id",
        "sql",
    ):
        assert field in evidence, field


def test_evidence_excludes_result_rows():
    """Rows are the answer, not evidence about how the query was governed."""
    result = gq.GovernedQueryResult(
        accepted=True, rows=[{"name": "Linen Shirt"}], row_count=1
    )

    evidence = result.evidence()

    assert "rows" not in evidence
    assert evidence["row_count"] == 1


def test_a_rejected_result_reports_no_execution():
    result = gq.GovernedQueryResult(accepted=False, rejection_reason="nope")

    assert result.execution_outcome == "not_executed"
    assert result.row_count is None


def test_role_and_limits_are_reported_not_assumed():
    """An operator reads the enforced values rather than trusting a default."""
    evidence = gq.GovernedQueryResult(accepted=False).evidence()

    assert evidence["role_used"] == "pellier_query"
    assert evidence["statement_timeout"] == gq.STATEMENT_TIMEOUT
    assert evidence["result_limit"] == gq.MAX_ROWS


# ---------------------------------------------------------------------------
# Session containment
# ---------------------------------------------------------------------------


def test_read_only_session_never_uses_a_set_statement_for_the_timeout():
    """Regression: `SET LOCAL statement_timeout = %s` is a syntax error.

    `SET` takes no parameters. The failure aborted every query, so the module
    looked like a boundary that refused everything — including legitimate
    questions. `set_config(..., true)` is the parameterizable form.
    """
    import pathlib

    source = pathlib.Path(
        __import__("services.database", fromlist=["x"]).__file__
    ).read_text()
    session = source.split("async def query_session", 1)[1].split("async def", 1)[0]

    assert "SET LOCAL statement_timeout = %s" not in session
    assert "set_config('statement_timeout'" in session


def test_read_only_session_sets_every_containment():
    """All four containments, in one transaction, on one connection."""
    import pathlib

    source = pathlib.Path(
        __import__("services.database", fromlist=["x"]).__file__
    ).read_text()
    session = source.split("async def query_session", 1)[1].split("async def", 1)[0]

    assert "SET TRANSACTION READ ONLY" in session
    assert "SET LOCAL ROLE pellier_query" in session
    assert "set_config('statement_timeout'" in session
    assert "set_config('search_path'" in session
    assert "set_config('pellier.principal_sub'" in session


def test_read_only_precedes_the_role_switch():
    """`SET TRANSACTION` must come before the first query in the transaction."""
    import pathlib

    source = pathlib.Path(
        __import__("services.database", fromlist=["x"]).__file__
    ).read_text()
    session = source.split("async def query_session", 1)[1].split("async def", 1)[0]

    assert session.index("SET TRANSACTION READ ONLY") < session.index(
        "SET LOCAL ROLE pellier_query"
    )
