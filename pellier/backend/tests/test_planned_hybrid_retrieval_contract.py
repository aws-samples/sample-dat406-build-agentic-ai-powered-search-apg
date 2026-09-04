"""The Observatory comparison must expose its shared planned-hybrid path."""

from __future__ import annotations

import inspect

import app


def test_observatory_agentic_comparison_uses_shared_planned_hybrid_primitives() -> None:
    """The comparison's plan, hybrid candidate pool, and rerank stay coupled."""
    observatory = inspect.getsource(app.compare_search_strategies)

    assert "retrieve_planned_hybrid(" in observatory
    assert "rerank_hybrid_candidates(" in observatory
