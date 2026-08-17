"""Regression tests for SQL query instrumentation."""

import pytest

from services.sql_query_logger import SQLQueryLogger


def test_disabled_logger_does_not_swallow_query_exception() -> None:
    logger = SQLQueryLogger()
    logger.enabled = False

    with pytest.raises(RuntimeError, match="query failed"):
        with logger.log_query("search", "SELECT 1", [], object()):
            raise RuntimeError("query failed")

    assert logger.queries == []
