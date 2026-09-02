"""Truth contracts for durable Observatory session summaries."""

from pathlib import Path


def test_opening_query_uses_the_first_audit_row_not_lexical_maximum() -> None:
    """A receipt must not call the alphabetically largest trace the opening turn."""
    source = (
        Path(__file__).resolve().parents[1] / "routes" / "observatory.py"
    ).read_text()

    # Both list and detail use the same chronologically deterministic subquery.
    assert source.count("ORDER BY first_audit.created_at ASC, first_audit.audit_id ASC") == 2
    assert 'max(COALESCE(\n                    NULLIF(ta.args->>\'query\'' not in source


def test_authenticated_session_replay_rejects_mixed_principals() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "routes" / "observatory.py"
    ).read_text()

    assert "foreign_turn.principal_sub IS DISTINCT FROM %s" in source
    assert "raise_on_error=True" in source
