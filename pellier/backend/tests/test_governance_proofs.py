"""Contracts for the two governance-proof scripts.

`prove_governance_windows.py` compares the ENFORCE and LOG_ONLY windows against
a live Gateway. `score_governance_evidence.py` scores the same evidence a
participant reads by hand. Neither can run in the hermetic suite, so what is
pinned here is their *logic* and their safety properties.

Three safety properties carry real risk:

  1. **Mode is restored on every exit path.** A crashed run must not leave the
     account in monitor mode, where Cedar denies nothing.
  2. **A non-deployable project changes nothing.** `agentcore deploy` is a
     whole-project CDK deploy, so a template render cannot be deployed. The
     check has to happen *before* the declaration is edited, or a blocked run
     leaves the project declaring a mode that was never applied — which the
     next successful deploy would then apply by surprise.
  3. **The scorer must fail on a real violation.** A scorer that always passes
     is worse than none, because it certifies broken evidence.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _load(name: str, filename: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _windows():
    return _load("prove_governance_windows_t", "prove_governance_windows.py")


def _scorer():
    return _load("score_governance_evidence_t", "score_governance_evidence.py")


# ---------------------------------------------------------------------------
# The two windows are asserted differently, on purpose
# ---------------------------------------------------------------------------


def _result(window: str, executions: int, returns: int = 0, ledger: int = 0) -> Dict[str, Any]:
    return {
        "window": window,
        "call": {"outcome": "returned", "is_error": True, "text": ""},
        "executions": executions,
        "business_change": {"returns": returns, "ledger": ledger},
    }


def test_enforce_window_requires_no_execution():
    """Cedar denies before the target runs, so the absence is the proof."""
    windows = _windows()

    assert windows._report(_result("ENFORCE", executions=0)) == []
    failures = windows._report(_result("ENFORCE", executions=1))
    assert failures and "expected no execution row" in failures[0]


def test_log_only_window_requires_execution():
    """Zero executions here means Cedar still blocked it.

    That is the failure mode worth catching: the mode change silently not
    taking effect looks identical to enforcement working.
    """
    windows = _windows()

    assert windows._report(_result("LOG_ONLY", executions=1)) == []
    failures = windows._report(_result("LOG_ONLY", executions=0))
    assert failures and "Cedar may still be enforcing" in failures[0]


def test_both_windows_require_zero_business_change():
    windows = _windows()

    for window in ("ENFORCE", "LOG_ONLY"):
        executions = 0 if window == "ENFORCE" else 1
        failures = windows._report(_result(window, executions, returns=1))
        assert any("committed a return row" in f for f in failures), window
        failures = windows._report(_result(window, executions, ledger=1))
        assert any("moved inventory" in f for f in failures), window


def test_a_missing_tool_is_reported_rather_than_scored():
    windows = _windows()
    result = _result("ENFORCE", 0)
    result["call"] = {"outcome": "tool_absent"}

    failures = windows._report(result)

    assert failures and "not published on the Gateway" in failures[0]


def test_the_request_targets_a_reason_the_policy_forbids():
    """A permitted reason would make both windows behave identically."""
    windows = _windows()

    assert windows.FORBIDDEN_REASON != "damaged"
    assert windows.GATING_POLICY == "process_return_damaged_only"


def test_mode_is_restored_on_every_exit_path():
    """A crashed run must not leave the account in monitor mode."""
    source = (_SCRIPTS / "prove_governance_windows.py").read_text()

    assert "finally:" in source
    restore_index = source.index("_restore_shipped")
    finally_index = source.index("finally:")
    assert finally_index < restore_index, "the restore must sit in a finally block"


# ---------------------------------------------------------------------------
# A non-deployable project must change nothing
# ---------------------------------------------------------------------------


def test_deployability_rejects_a_template_render(tmp_path):
    tool = _load("policy_mode_proofs_t", "policy_mode.py")
    project = tmp_path / "p"
    (project / "agentcore").mkdir(parents=True)
    (project / "agentcore" / "agentcore.json").write_text(
        '{"agentCoreGateways": [{"roleArn": "arn:aws:iam::123456789012:role/x"}]}'
    )

    blocker = tool.deployability(project, "444455556666")

    assert blocker and "template render" in blocker


def test_deployability_rejects_a_cross_account_project(tmp_path):
    tool = _load("policy_mode_proofs_t", "policy_mode.py")
    project = tmp_path / "p"
    (project / "agentcore").mkdir(parents=True)
    (project / "agentcore" / "agentcore.json").write_text(
        '{"agentCoreGateways": [{"roleArn": "arn:aws:iam::111122223333:role/x"}]}'
    )

    blocker = tool.deployability(project, "444455556666")

    assert blocker and "111122223333" in blocker


def test_deployability_accepts_a_matching_project(tmp_path):
    tool = _load("policy_mode_proofs_t", "policy_mode.py")
    project = tmp_path / "p"
    (project / "agentcore").mkdir(parents=True)
    (project / "agentcore" / "agentcore.json").write_text(
        '{"agentCoreGateways": [{"roleArn": "arn:aws:iam::444455556666:role/x"}]}'
    )

    assert tool.deployability(project, "444455556666") is None


def test_a_blocked_change_is_checked_before_the_declaration_is_edited():
    """Editing first would leave a declared mode that was never applied."""
    source = (_SCRIPTS / "policy_mode.py").read_text()
    apply_body = source[source.index("def _apply("):source.index("def main(")]

    assert apply_body.index("deployability(") < apply_body.index("declare_modes(")


# ---------------------------------------------------------------------------
# The scorer must fail on a real violation
# ---------------------------------------------------------------------------


def _turn(**overrides: Any) -> Dict[str, Any]:
    turn = {
        "turn_id": "turn-x",
        "principal_sub": "sub-a",
        "principal_verified": True,
        "rail": "gateway-mcp",
        "terminal_status": "complete",
        "decision": "ALLOW",
        "decision_source": "governed_receipts",
        "executions": 1,
        "policy_receipts": 1,
        "successful_executions": 1,
    }
    turn.update(overrides)
    return turn


def _failed(findings: List[Dict[str, str]]) -> List[str]:
    return [f["invariant"] for f in findings if f["result"] == "FAIL"]


def test_a_clean_allowed_turn_passes():
    scorer = _scorer()

    assert _failed(scorer.score_turn(_turn())) == []


def test_a_denied_turn_with_an_execution_row_fails():
    """The tool ran after being refused, which the design forbids."""
    scorer = _scorer()

    failed = _failed(
        scorer.score_turn(
            _turn(decision="DENY", executions=1, successful_executions=1,
                  terminal_status="denied-before-execution", policy_receipts=0)
        )
    )

    assert "denial means non-execution" in failed
    assert "denial changed nothing" in failed


def test_a_clean_denied_turn_passes():
    scorer = _scorer()

    failed = _failed(
        scorer.score_turn(
            _turn(decision="DENY", executions=0, successful_executions=0,
                  policy_receipts=0, terminal_status="denied-before-execution")
        )
    )

    assert failed == []


def test_a_monitor_turn_that_never_executed_fails():
    """Zero executions means the mode change never took effect."""
    scorer = _scorer()

    failed = _failed(
        scorer.score_turn(
            _turn(decision="WOULD_DENY", executions=0, successful_executions=0,
                  policy_receipts=0)
        )
    )

    assert "monitor mode still executed" in failed


def test_a_monitor_turn_that_succeeded_fails():
    """A would-deny that changed state means nothing refused it."""
    scorer = _scorer()

    failed = _failed(
        scorer.score_turn(
            _turn(decision="WOULD_DENY", executions=1, successful_executions=1,
                  policy_receipts=0)
        )
    )

    assert "monitor mode changed nothing" in failed


def test_a_clean_monitor_turn_passes():
    scorer = _scorer()

    failed = _failed(
        scorer.score_turn(
            _turn(decision="WOULD_DENY", executions=1, successful_executions=0,
                  policy_receipts=0)
        )
    )

    assert failed == []


def test_a_turn_with_no_identity_fails():
    scorer = _scorer()

    failed = _failed(_scorer().score_turn(_turn(principal_sub=None, principal_verified=True)))

    assert "identity recorded" in failed


def test_an_anonymous_turn_is_not_an_identity_failure():
    """Anonymous is a legitimate state; unrecorded is not."""
    scorer = _scorer()

    failed = _failed(scorer.score_turn(_turn(principal_sub=None, principal_verified=False)))

    assert "identity recorded" not in failed


def test_more_policy_receipts_than_executions_fails_correlation():
    """A receipt joins through audit_id, so it cannot outnumber executions."""
    scorer = _scorer()

    failed = _failed(scorer.score_turn(_turn(executions=1, policy_receipts=2)))

    assert "correlation holds" in failed


def test_a_turn_with_no_decision_is_reported():
    scorer = _scorer()

    failed = _failed(scorer.score_turn(_turn(decision=None, decision_source=None)))

    assert "policy decision recorded" in failed


def test_the_scorer_needs_no_model_or_managed_service():
    """Section 19.7 keeps evaluations out of required lab completion."""
    source = (_SCRIPTS / "score_governance_evidence.py").read_text()

    for forbidden in ("bedrock", "converse(", "invoke_model", "StartBatchEvaluation"):
        assert forbidden not in source, forbidden
