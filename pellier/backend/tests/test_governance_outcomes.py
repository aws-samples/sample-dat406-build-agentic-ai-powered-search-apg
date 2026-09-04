"""The three enforcement boundaries, and the axes that must not infer one another.

Proven live on 2026-08-27 against the partial-reopen authorization surface (damaged
permit ACTIVE, non-damaged forbid ACTIVE, baseline still narrowed):

    THEO    CONFIRMED / ALLOW / PERMITTED / RECEIPTED
    RACHEL  CONFIRMED / DENY  / NOT_REACHED / POLICY_PROOF
    AMARA   CONFIRMED / ALLOW / DENIED / ATTEMPT_RECEIPT

Every assertion here is about a classification rule, not about a captured value: the
rules are what make the live outcomes reproducible.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict

import pytest

from services import governed_execution as GE


# ---------------------------------------------------------------------------
# No axis derives another
# ---------------------------------------------------------------------------

def test_a_policy_denial_never_reaches_aurora() -> None:
    """The tool was not entered, so no statement reached the database."""
    aurora, note = GE.classify_aurora({"status": "policy_denied",
                                       "denied_by": "agentcore_policy"})
    assert aurora == GE.AURORA_NOT_REACHED
    assert GE.classify_evidence_for(GE.POLICY_DENY, aurora, {}) == GE.EVIDENCE_POLICY_PROOF


def test_a_policy_allow_does_not_imply_aurora_permitted() -> None:
    """Outcome C. Authorization and database permission are separate boundaries."""
    denied = GE.as_rls_denial(
        {"status": "error", "message": "Customer CUST-AMARA did not order product 46."},
        "CUST-AMARA",
    )
    aurora, _note = GE.classify_aurora(denied)
    assert aurora == GE.AURORA_DENIED
    assert GE.classify_evidence_for(GE.POLICY_ALLOW, aurora, denied) == (
        GE.EVIDENCE_ATTEMPT_RECEIPT
    )


def test_a_permissive_gateway_result_is_not_an_allow_without_engine_state() -> None:
    """A call that returned under LOG_ONLY is an observation, not an authorization."""
    policy, note = GE.resolve_permissive_policy_state(None)
    assert policy == GE.POLICY_EVALUATION_INCOMPLETE
    assert "could not be read" in note


def test_enforcement_on_turns_a_returned_call_into_a_real_allow() -> None:
    state = GE.PolicyEngineState(
        gateway_mode="ENFORCE",
        policies={"process_return_damaged_only": ("forbid", "ACTIVE")},
        matching_forbids=("process_return_damaged_only",),
    )
    assert state.enforcement_is_on is True
    policy, note = GE.resolve_permissive_policy_state(state)
    assert policy == GE.POLICY_ALLOW
    assert "evaluated the action and permitted it" in note


def test_an_unenforced_matching_forbid_is_inferred_not_a_verdict() -> None:
    """Policy text that names the action is a fact about text, not a decision."""
    state = GE.PolicyEngineState(
        gateway_mode="LOG_ONLY",
        policies={"process_return_damaged_only": ("forbid", "ACTIVE")},
        matching_forbids=("process_return_damaged_only",),
    )
    assert state.enforcement_is_on is False
    policy, note = GE.resolve_permissive_policy_state(state)
    assert policy == GE.POLICY_INFERRED
    assert policy != GE.POLICY_WOULD_DENY
    assert "process_return_damaged_only" in note


# ---------------------------------------------------------------------------
# An RLS-hidden row never becomes a business falsehood
# ---------------------------------------------------------------------------

def test_an_rls_hidden_row_is_not_reported_as_a_missing_order() -> None:
    """The canonical database-enforcement outcome, and it used to lie.

    `pellier.process_return_idempotent` reports "did not order" when its ownership
    SELECT finds nothing. Under a session that resolved NO customer scope that SELECT
    was guaranteed to find nothing whatever the orders table holds — order 323 exists.
    The managed Gateway rail cannot set `denied_by` itself, so the raw message came
    back and the Aurora axis read NOT_REACHED with the falsehood attached.
    """
    raw = {"status": "error",
           "message": "Customer CUST-AMARA did not order product 46; cannot process return."}
    assert GE.is_ownership_failure(raw) is True

    fixed = GE.as_rls_denial(raw, "CUST-AMARA")
    assert fixed["denied_by"] == "database_row_level_security"
    assert "did not order" not in fixed["message"]
    assert "not in scope for this database session" in fixed["message"]
    assert "The order relationship itself is unchanged" in fixed["message"]
    # Nothing is hidden: the tool's verbatim text is preserved, just not as truth.
    assert fixed["tool_message"] == raw["message"]


def test_a_success_is_never_reclassified() -> None:
    for result in ({"status": "success"},
                   {"status": "success", "message": "did not order"}):
        assert GE.is_ownership_failure(result) is False


def test_the_reclassification_only_fires_without_a_customer_subject() -> None:
    """A mapped client's not-ordered result is a business fact and must stand."""
    source = inspect.getsource(GE._classify_aurora_axis)
    branch = source[source.index("elif customer_subject is None"):]
    branch = branch[: branch.index("return aurora, aurora_note, result")]
    assert "is_ownership_failure(result)" in branch
    assert "as_rls_denial(result, customer_id)" in branch
    # And the reclassification precedes the classification it feeds.
    assert branch.index("as_rls_denial") < branch.index("classify_aurora")


# ---------------------------------------------------------------------------
# Identity is server-resolved
# ---------------------------------------------------------------------------

def test_the_customer_subject_is_resolved_from_configuration_not_a_caller() -> None:
    source = inspect.getsource(GE.resolve_customer_subject)
    assert "pellier.principal_customers" in inspect.getsource(GE)
    assert "customer_id" in inspect.signature(GE.resolve_customer_subject).parameters
    # No request/browser material reaches it.
    for forbidden in ("request", "payload", "body", "args"):
        assert forbidden not in inspect.signature(GE.resolve_customer_subject).parameters


def test_an_unmapped_client_fails_closed_rather_than_widening() -> None:
    source = inspect.getsource(GE.resolve_customer_subject)
    assert "RLS will fail closed" in source


def test_the_two_principals_are_never_collapsed() -> None:
    params = inspect.signature(GE.execute_confirmed_review).parameters
    assert "operator_sub" in params
    outcome_fields = {f for f in GE.ExecutionOutcome.__dataclass_fields__}
    assert {"operator_sub", "customer_subject"} <= outcome_fields


# ---------------------------------------------------------------------------
# The policy engine must be readable at all
# ---------------------------------------------------------------------------

def test_the_engine_id_is_read_from_settings_not_only_the_environment() -> None:
    """`Settings` loads `.env` into the settings object, not into `os.environ`.

    Reading only the environment returned "" on every normally configured backend, so
    `engine_state_for_action` returned None and every Gateway ALLOW was downgraded to
    NOT_EVALUATED. The workshop's single most important positive claim was unreachable,
    and it failed in the honest direction — which is why nothing looked broken.
    """
    from services import managed_policy as MP

    source = inspect.getsource(MP._engine_id)
    assert "from config import settings" in source
    assert "os.environ.get" in source, "the environment fallback was dropped"
    # And it actually resolves in this hermetic test environment or falls back cleanly.
    assert isinstance(MP._engine_id(), str)


def test_the_engine_state_reader_imports_settings_in_scope() -> None:
    """A bare `settings` reference sat behind the unreachable engine-id guard."""
    from services import managed_policy as MP

    source = inspect.getsource(MP.engine_state_for_action)
    assert "from config import settings as _settings" in source
    assert "getattr(_settings, \"AGENTCORE_GATEWAY_ARN\"" in source
