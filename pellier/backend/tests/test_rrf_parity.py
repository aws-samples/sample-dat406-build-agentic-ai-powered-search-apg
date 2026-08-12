"""RRF parity: in-process fusion vs the Lambda single-CTE path.

Hybrid retrieval is implemented twice, deliberately:

- ``services/hybrid_search.py`` — the in-process path. Two SQL branches,
  then :meth:`HybridSearch._rrf_merge` fuses the ranked lists in Python.
- ``scripts/deploy/pellier_search_server.py`` — the Gateway Lambda path.
  Data API's single-statement constraint folds both branches and the
  fusion into one CTE: ``COALESCE(1.0/(60+vrank),0) +
  COALESCE(1.0/(60+frank),0)`` over a FULL OUTER JOIN.

The Lambda source promises "the same constant the in-process
implementation uses, so participants get a one-to-one comparison
between paths" — but nothing enforced that promise. These tests are the
drift alarm:

1. The k constant pinned in three places (in-process default, Settings
   default, every literal in the Lambda SQL) must agree.
2. The Lambda CTE's fusion shape (FULL OUTER JOIN + COALESCE-to-zero)
   must still be present.
3. A faithful Python transcription of the CTE math must produce the
   same scores and ordering as ``_rrf_merge`` on shared fixtures,
   including overlap, one-branch-only, and tie cases.

No live database is involved; both sides reduce to arithmetic over
ranked pid lists.
"""

import math
import re
from pathlib import Path
from typing import Any, Dict, List

from services.hybrid_search import _RRF_K_DEFAULT, HybridSearch
from config import Settings

# tests/test_rrf_parity.py → parents[0]=tests, [1]=backend,
# [2]=pellier, [3]=repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LAMBDA_PATH = _REPO_ROOT / "scripts" / "deploy" / "pellier_search_server.py"


def _lambda_source() -> str:
    return _LAMBDA_PATH.read_text(encoding="utf-8")


def _row(product_id: int) -> Dict[str, Any]:
    return {"product_id": product_id}


def _lambda_cte_scores(
    vector_pids: List[int], fts_pids: List[int], k: int
) -> Dict[int, float]:
    """Transcribe the Lambda ``rrf`` CTE into Python.

    ``row_number()`` ranks each branch starting at 1 in list order;
    the FULL OUTER JOIN is the union of pids; a missing rank COALESCEs
    to a zero contribution.
    """
    vrank = {pid: i + 1 for i, pid in enumerate(vector_pids)}
    frank = {pid: i + 1 for i, pid in enumerate(fts_pids)}
    scores: Dict[int, float] = {}
    for pid in set(vector_pids) | set(fts_pids):
        v_term = 1.0 / (k + vrank[pid]) if pid in vrank else 0.0
        f_term = 1.0 / (k + frank[pid]) if pid in frank else 0.0
        scores[pid] = v_term + f_term
    return scores


class TestRRFConstantParity:
    """One k across the in-process default, Settings, and the Lambda SQL."""

    def test_lambda_sql_uses_the_in_process_constant(self) -> None:
        source = _lambda_source()
        literals = re.findall(r"1\.0\s*/\s*\(\s*(\d+)\s*\+", source)
        assert literals, (
            "No RRF `1.0 / (k + rank)` literals found in "
            f"{_LAMBDA_PATH} — if the fusion moved or was reshaped, "
            "update this parity test alongside it."
        )
        assert set(literals) == {str(_RRF_K_DEFAULT)}, (
            f"Lambda RRF constants {sorted(set(literals))} drifted from "
            f"the in-process default {_RRF_K_DEFAULT}. The two hybrid "
            "paths must fuse with the same k for a one-to-one comparison."
        )

    def test_settings_default_matches_in_process_default(self) -> None:
        assert Settings.model_fields["HYBRID_RRF_K"].default == _RRF_K_DEFAULT


class TestLambdaCTEShape:
    """Pin the fusion shape the transcription below depends on."""

    def test_full_outer_join_coalesce_fusion_is_present(self) -> None:
        source = _lambda_source()
        for fragment in (
            "FULL OUTER JOIN",
            "COALESCE(v.pid, f.pid)",
            "COALESCE(1.0 / (60 + v.vrank), 0)",
            "COALESCE(1.0 / (60 + f.frank), 0)",
        ):
            assert fragment in source, (
                f"Expected `{fragment}` in the Lambda hybrid CTE. If the "
                "fusion SQL changed, update _lambda_cte_scores() in this "
                "test to match and re-verify parity with _rrf_merge."
            )


class TestFusionMathParity:
    """Same fixtures through both formulas → same scores, same ordering."""

    FIXTURES = [
        # (label, vector pids, fts pids)
        ("overlap-at-head", [1, 2, 3], [1, 4, 5]),
        ("disjoint", [10, 11], [20, 21]),
        ("fts-empty", [1, 2, 3], []),
        ("vector-empty", [], [7, 8]),
        # Symmetric ranks → pid 1 and pid 2 tie exactly.
        ("exact-tie", [1, 2], [2, 1]),
        ("full-depth", list(range(1, 21)), list(range(15, 35))),
    ]

    def test_scores_match_lambda_transcription(self) -> None:
        for label, v_pids, f_pids in self.FIXTURES:
            merged = HybridSearch._rrf_merge(
                [_row(p) for p in v_pids],
                [_row(p) for p in f_pids],
                rrf_k=_RRF_K_DEFAULT,
            )
            in_process = {r["product_id"]: r["rrf_score"] for r in merged}
            lambda_side = _lambda_cte_scores(v_pids, f_pids, _RRF_K_DEFAULT)
            assert in_process.keys() == lambda_side.keys(), label
            for pid in lambda_side:
                assert math.isclose(
                    in_process[pid], lambda_side[pid], rel_tol=0, abs_tol=1e-12
                ), f"{label}: pid {pid} scored differently across paths"

    def test_ordering_matches_up_to_ties(self) -> None:
        # Exact sequences can differ within a tie group (Python's sort is
        # stable on insertion order; ORDER BY ... DESC leaves tie order
        # unspecified), so compare the score-descending grouping instead.
        for label, v_pids, f_pids in self.FIXTURES:
            merged = HybridSearch._rrf_merge(
                [_row(p) for p in v_pids],
                [_row(p) for p in f_pids],
                rrf_k=_RRF_K_DEFAULT,
            )
            scores = [r["rrf_score"] for r in merged]
            assert scores == sorted(scores, reverse=True), label
            lambda_side = _lambda_cte_scores(v_pids, f_pids, _RRF_K_DEFAULT)
            expected_order = sorted(lambda_side.values(), reverse=True)
            for got, expected in zip(scores, expected_order):
                assert math.isclose(
                    got, expected, rel_tol=0, abs_tol=1e-12
                ), f"{label}: fused ranking diverged between paths"
