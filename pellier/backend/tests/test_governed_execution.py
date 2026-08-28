"""PROMPT 4 Phase A — governed execution of a confirmed review.

The whole point of this stage is that four controls stay independent:

    Human      did a person decide?
    Cedar      may this principal attempt this action?
    RLS        may this session touch these rows?
    CHECK      is this mutation valid regardless of who asked?

Most of the assertions below are therefore negative. A policy verdict must never
appear on a rail where no policy engine was consulted; an ALLOW must never be
inferred from a call that merely returned under LOG_ONLY; and the operator's own
identity must never become the Row-Level Security subject.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

REPO = BACKEND.parents[1]
DEPLOY = REPO / "scripts" / "deploy"

from services import governed_execution as ge  # noqa: E402
from services.business_logic import write_request_hash  # noqa: E402

THEO_ARGS = {"customer_id": "CUST-THEO", "product_id": 37, "reason": "damaged"}
THEO_HASH = write_request_hash("initiate_return", **THEO_ARGS)
THEO_SUBJECT = "sub-theo-cognito"
OPERATOR_SUBJECT = "sub-operator-cognito"


def approved_review(**overrides: Any) -> Dict[str, Any]:
    row = {
        "review_id": 12,
        "customer_id": "CUST-THEO",
        "action": "initiate_return",
        "args": dict(THEO_ARGS),
        "status": "approved",
        "action_hash": THEO_HASH,
        "source_turn_id": "turn-" + ("a" * 32),
        "order_id": 305,
        "execution_turn_id": None,
        "decided_by": "operator-1",
    }
    row.update(overrides)
    return row


class FakeDb:
    """Records statements so the tests can assert what did NOT run."""

    def __init__(
        self,
        *,
        customer_subject: Optional[str] = THEO_SUBJECT,
        existing_execution_turn: Optional[str] = None,
    ) -> None:
        self.customer_subject = customer_subject
        self.existing_execution_turn = existing_execution_turn
        self.statements: List[str] = []
        self.claimed_turns: List[str] = []

    async def fetch_one(self, query: str, *params: Any) -> Optional[Dict[str, Any]]:
        self.statements.append(query)
        if "FROM pellier.principal_customers" in query:
            return (
                {"principal_sub": self.customer_subject}
                if self.customer_subject
                else None
            )
        if query.strip().startswith("UPDATE pellier.approvals"):
            if self.existing_execution_turn:
                return None  # the WHERE ... IS NULL guard refuses a second claim
            self.existing_execution_turn = params[0]
            self.claimed_turns.append(params[0])
            return {"execution_turn_id": params[0]}
        if "SELECT execution_turn_id" in query:
            return {"execution_turn_id": self.existing_execution_turn}
        return None

    async def fetch_all(self, query: str, *params: Any) -> List[Dict[str, Any]]:
        self.statements.append(query)
        return []


class FakeLogic:
    """Captures what the governed write was actually called with."""

    calls: List[Dict[str, Any]] = []
    envelope: Dict[str, Any] = {"status": "success", "return_id": 9}

    def __init__(self, db: Any) -> None:
        pass

    async def initiate_return(self, **kwargs: Any) -> Dict[str, Any]:
        type(self).calls.append({"tool": "initiate_return", **kwargs})
        return dict(type(self).envelope)

    async def issue_credit(self, **kwargs: Any) -> Dict[str, Any]:
        type(self).calls.append({"tool": "issue_credit", **kwargs})
        return dict(type(self).envelope)


@pytest.fixture(autouse=True)
def _reset_logic(monkeypatch: pytest.MonkeyPatch):
    FakeLogic.calls = []
    FakeLogic.envelope = {"status": "success", "return_id": 9}
    import services.business_logic as bl

    monkeypatch.setattr(bl, "BusinessLogic", FakeLogic)
    # Default to the in-process rail unless a test opts into the Gateway.
    from config import settings

    monkeypatch.setattr(settings, "AGENTCORE_GATEWAY_URL", "", raising=False)
    yield
    FakeLogic.calls = []


# ---------------------------------------------------------------------------
# Gateway vocabulary: source is authoritative
# ---------------------------------------------------------------------------

def test_the_runtime_target_map_matches_the_provisioning_schemas() -> None:
    """One vocabulary, asserted rather than duplicated on trust.

    Cedar action ids embed the target name, so a runtime map that drifts from the
    provisioning schemas would point policies at a target that no longer
    publishes the tool. The backend cannot import the deploy module at runtime,
    so the copy is pinned here instead.
    """
    if str(DEPLOY) not in sys.path:
        sys.path.insert(0, str(DEPLOY))
    from gateway_tool_schemas import TOOL_SCHEMAS

    from services.agentcore_gateway import GATEWAY_TARGET_FOR_TOOL

    expected = {
        tool["name"]: config["target_name"]
        for config in TOOL_SCHEMAS.values()
        for tool in config["tools"]
    }
    assert GATEWAY_TARGET_FOR_TOOL == expected


def test_every_published_tool_has_a_target() -> None:
    from services.agentcore_gateway import (
        GATEWAY_TARGET_FOR_TOOL,
        GATEWAY_TOOL_NAMES,
    )

    missing = sorted(set(GATEWAY_TOOL_NAMES) - set(GATEWAY_TARGET_FOR_TOOL))
    assert not missing, f"published tools with no Gateway target: {missing}"


def test_no_retired_tool_name_appears_in_the_desired_gateway_vocabulary() -> None:
    """The live Gateway is on the pre-rename names; the source must not be.

    Discovered during the Prompt 4 audit: the deployed targets still publish
    `process_return`, `floor_check`, `find_pieces` and friends. The migration
    moves live to the source vocabulary, so the source must be clean first.
    """
    if str(DEPLOY) not in sys.path:
        sys.path.insert(0, str(DEPLOY))
    from gateway_tool_schemas import TOOL_SCHEMAS

    published = {
        tool["name"]
        for config in TOOL_SCHEMAS.values()
        for tool in config["tools"]
    }
    retired = {
        "process_return", "floor_check", "find_pieces", "find_pieces_hybrid",
        "explore_collection", "running_low", "restock_shelf", "whats_trending",
        "price_intelligence", "side_by_side", "returns_and_care", "style_match",
        "preference_snapshot", "trace_receipt", "escalate_to_stylist",
    }
    assert not (published & retired), (
        f"retired names in the desired Gateway schema: {sorted(published & retired)}"
    )
    assert len(published) == 17


def test_the_cedar_action_id_is_target_qualified() -> None:
    assert (
        ge.gateway_action_id("initiate_return")
        == "pellier-concierge-experience-target___initiate_return"
    )
    with pytest.raises(ge.ExecutionError):
        ge.gateway_action_id("not_a_tool")


# ---------------------------------------------------------------------------
# Confirmation integrity
# ---------------------------------------------------------------------------

def test_a_pending_review_cannot_be_executed() -> None:
    with pytest.raises(ge.ExecutionError) as exc:
        ge.verify_confirmation(approved_review(status="pending"))
    assert exc.value.code == "review_not_confirmed"


def test_a_declined_review_cannot_be_executed() -> None:
    with pytest.raises(ge.ExecutionError) as exc:
        ge.verify_confirmation(approved_review(status="rejected"))
    assert exc.value.code == "review_declined"


def test_parameters_edited_after_confirmation_are_refused() -> None:
    """The fingerprint is what makes "the operator approved this" checkable."""
    tampered = approved_review()
    tampered["args"] = {**THEO_ARGS, "reason": "changed_mind"}
    with pytest.raises(ge.ExecutionError) as exc:
        ge.verify_confirmation(tampered)
    assert exc.value.code == "confirmation_invalid"


def test_verification_returns_the_persisted_parameters() -> None:
    """Execution parameters come from the row, never from a caller."""
    assert ge.verify_confirmation(approved_review()) == THEO_ARGS


@pytest.mark.asyncio
async def test_a_tampered_review_never_reaches_the_database() -> None:
    tampered = approved_review()
    tampered["args"] = {**THEO_ARGS, "product_id": 31}
    db = FakeDb()
    with pytest.raises(ge.ExecutionError):
        await ge.execute_confirmed_review(
            db, tampered, operator_sub=OPERATOR_SUBJECT
        )
    assert FakeLogic.calls == [], "a write ran despite an invalid confirmation"
    assert db.statements == [], "the database was touched before verification"


# ---------------------------------------------------------------------------
# The two principals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rls_is_scoped_to_the_customer_not_the_operator() -> None:
    """The load-bearing assertion of the two-principal model.

    Passing the operator's own subject as the RLS principal — which the legacy
    endpoints did — scopes the transaction to the operator's rows, and the write
    then fails for every client they are not mapped to.
    """
    db = FakeDb(customer_subject=THEO_SUBJECT)
    outcome = await ge.execute_confirmed_review(
        db, approved_review(), operator_sub=OPERATOR_SUBJECT
    )

    assert len(FakeLogic.calls) == 1
    call = FakeLogic.calls[0]
    assert call["principal_sub"] == THEO_SUBJECT
    assert call["principal_sub"] != OPERATOR_SUBJECT
    # And the actor is still reported, because attribution is a separate fact.
    assert outcome.operator_sub == OPERATOR_SUBJECT
    assert outcome.customer_subject == THEO_SUBJECT


@pytest.mark.asyncio
async def test_the_customer_subject_is_resolved_server_side() -> None:
    """A caller that could name its own RLS principal could read any client."""
    db = FakeDb(customer_subject=THEO_SUBJECT)
    await ge.execute_confirmed_review(
        db, approved_review(), operator_sub=OPERATOR_SUBJECT
    )
    assert any("FROM pellier.principal_customers" in s for s in db.statements), (
        "the subject was not resolved from the authorization mapping table"
    )


@pytest.mark.asyncio
async def test_an_unmapped_client_fails_closed_and_says_why() -> None:
    """No identity mapping means no scope, which denies rather than widens."""
    db = FakeDb(customer_subject=None)
    FakeLogic.envelope = {
        "status": "error",
        "message": "customer CUST-JESSICA did not order product 42",
    }
    outcome = await ge.execute_confirmed_review(
        db,
        approved_review(customer_id="CUST-JESSICA"),
        operator_sub=OPERATOR_SUBJECT,
    )
    assert outcome.customer_subject is None
    assert FakeLogic.calls[0]["principal_sub"] is None
    # The axis now says DENIED, not NOT_REACHED. The earlier version prefixed an honest
    # sentence onto the tool's "did not order" message and left the axis unchanged, so
    # the canonical database-enforcement outcome reported that no statement had reached
    # the database when one had, and been refused.
    assert outcome.aurora == ge.AURORA_DENIED
    assert outcome.evidence == ge.EVIDENCE_ATTEMPT_RECEIPT
    assert "Row-Level Security refused" in outcome.notes["aurora"]
    # And the falsehood is gone from what a surface would render.
    assert "did not order" not in outcome.result["message"]
    assert outcome.result["denied_by"] == "database_row_level_security"
    assert "did not order" in outcome.result["tool_message"]


@pytest.mark.asyncio
async def test_a_credit_attributes_the_operator_as_the_actor() -> None:
    """Attribution and scope are different fields with different subjects."""
    credit_args = {
        "customer_id": "CUST-THEO", "amount_cents": 2500, "reason": "courtesy",
    }
    review = approved_review(
        action="issue_credit",
        args=credit_args,
        action_hash=write_request_hash("issue_credit", **credit_args),
    )
    await ge.execute_confirmed_review(
        FakeDb(), review, operator_sub=OPERATOR_SUBJECT
    )
    assert FakeLogic.calls[0]["issued_by"] == OPERATOR_SUBJECT


# ---------------------------------------------------------------------------
# execution_turn_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_execution_turn_is_a_second_turn_not_the_shopper_turn() -> None:
    """Two logical turns, one lineage. Reusing one id would collapse it."""
    review = approved_review()
    outcome = await ge.execute_confirmed_review(
        FakeDb(), review, operator_sub=OPERATOR_SUBJECT
    )
    assert outcome.execution_turn_id != review["source_turn_id"]
    assert outcome.execution_turn_id.startswith("turn-")
    assert len(outcome.execution_turn_id) == 37


@pytest.mark.asyncio
async def test_a_retry_reuses_the_same_execution_turn() -> None:
    """One confirmed action is one attempt, however many times HTTP repeats."""
    db = FakeDb()
    first = await ge.execute_confirmed_review(
        db, approved_review(), operator_sub=OPERATOR_SUBJECT
    )
    second = await ge.execute_confirmed_review(
        db, approved_review(), operator_sub=OPERATOR_SUBJECT
    )
    assert first.execution_turn_id == second.execution_turn_id
    assert len(db.claimed_turns) == 1, "a second execution turn was minted"


def test_the_database_refuses_an_execution_turn_on_an_unconfirmed_review() -> None:
    """Assign-once and confirmation-first are storage guarantees, not habits."""
    sql = (REPO / "scripts" / "migrations" / "021_governed_execution.sql").read_text()
    assert "approvals_execution_requires_confirmation_check" in sql
    assert "execution_turn_id IS NULL OR status = 'approved'" in sql
    assert "approvals_execution_turn_unique_idx" in sql
    assert "^turn-[0-9a-f]{32}$" in sql


def test_the_approval_status_was_not_widened_with_execution_outcomes() -> None:
    """The human axis stays the human axis.

    Adding `executed`, `policy_denied`, or `rls_denied` here would fold three
    independent controls into one column, which is the conflation this entire arc
    exists to dismantle.
    """
    for name in ("020_operator_review.sql", "021_governed_execution.sql"):
        sql = (REPO / "scripts" / "migrations" / name).read_text()
        for forbidden in ("'executed'", "'policy_denied'", "'rls_denied'", "'failed'"):
            assert forbidden not in sql, f"{name} widened approvals.status with {forbidden}"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_the_write_key_is_derived_from_the_confirmed_action() -> None:
    key = ge.execution_idempotency_key(12, THEO_HASH)
    assert key == ge.execution_idempotency_key(12, THEO_HASH)
    assert key.startswith("operator-review:12:")
    assert len(key) <= 128


def test_a_different_confirmed_action_gets_a_different_key() -> None:
    other = write_request_hash(
        "initiate_return", customer_id="CUST-THEO", product_id=31, reason="damaged"
    )
    assert ge.execution_idempotency_key(12, THEO_HASH) != ge.execution_idempotency_key(
        12, other
    )
    assert ge.execution_idempotency_key(12, THEO_HASH) != ge.execution_idempotency_key(
        13, THEO_HASH
    )


@pytest.mark.asyncio
async def test_two_executions_of_one_review_claim_the_same_write_key() -> None:
    db = FakeDb()
    await ge.execute_confirmed_review(
        db, approved_review(), operator_sub=OPERATOR_SUBJECT
    )
    await ge.execute_confirmed_review(
        db, approved_review(), operator_sub=OPERATOR_SUBJECT
    )
    keys = {call["idempotency_key"] for call in FakeLogic.calls}
    assert len(keys) == 1, f"a retry used a different write key: {keys}"


# ---------------------------------------------------------------------------
# Policy axis honesty
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_in_process_rail_never_claims_a_policy_verdict() -> None:
    """No engine was asked, so no verdict may be reported."""
    outcome = await ge.execute_confirmed_review(
        FakeDb(), approved_review(), operator_sub=OPERATOR_SUBJECT
    )
    assert outcome.rail == ge.RAIL_IN_PROCESS
    assert outcome.policy == ge.POLICY_NOT_EVALUATED
    assert "not consulted" in outcome.notes["policy"]


def test_a_returned_gateway_call_under_log_only_is_not_an_allow() -> None:
    """The dual-verdict classification, and the easiest thing to get wrong.

    A call that returned proves the tool was reached. Whether that was an
    authorization or an unenforced observation depends on the engine's mode, not
    on the response.
    """
    log_only = ge.PolicyEngineState(
        gateway_mode="LOG_ONLY",
        policies={"process_return_damaged_only": ("forbid", "ACTIVE")},
        matching_forbids=("process_return_damaged_only",),
    )
    policy, note = ge.resolve_permissive_policy_state(log_only)
    assert policy == ge.POLICY_WOULD_DENY
    assert "observed, not enforced" in note


def test_enforcement_on_makes_a_returned_call_a_real_allow() -> None:
    enforced = ge.PolicyEngineState(
        gateway_mode="ENFORCE",
        policies={"process_return_damaged_only": ("forbid", "ACTIVE")},
        matching_forbids=("process_return_damaged_only",),
    )
    policy, _ = ge.resolve_permissive_policy_state(enforced)
    assert policy == ge.POLICY_ALLOW


def test_a_forbid_in_log_only_is_off_not_observed() -> None:
    """Only an ACTIVE forbid under a LOG_ONLY gateway produces a would-deny."""
    both_off = ge.PolicyEngineState(
        gateway_mode="LOG_ONLY",
        policies={"process_return_damaged_only": ("forbid", "LOG_ONLY")},
        matching_forbids=("process_return_damaged_only",),
    )
    policy, _ = ge.resolve_permissive_policy_state(both_off)
    assert policy == ge.POLICY_ALLOW


def test_an_unreadable_engine_yields_no_verdict_rather_than_a_guess() -> None:
    policy, note = ge.resolve_permissive_policy_state(None)
    assert policy == ge.POLICY_NOT_EVALUATED
    assert "no verdict is claimed" in note


def test_only_real_policy_denials_are_classified_as_denials() -> None:
    """A broken Gateway must never look like a governance proof."""
    assert ge.is_policy_denial("AuthorizeActionException: denied") is True
    assert ge.is_policy_denial("Tool call not allowed due to policy enforcement") is True
    assert ge.is_policy_denial("Policy evaluation denied due to forbid-1") is True
    for benign in (
        "AccessDeniedException: not authorized to invoke",
        "Unauthorized",
        "403 Forbidden",
        "ConnectTimeout",
        "Unknown tool",
    ):
        assert ge.is_policy_denial(benign) is False, benign


# ---------------------------------------------------------------------------
# Aurora and evidence axes
# ---------------------------------------------------------------------------

def test_only_an_rls_marker_counts_as_an_aurora_denial() -> None:
    denied, note = ge.classify_aurora(
        {"status": "policy_blocked", "denied_by": "database_row_level_security"}
    )
    assert denied == ge.AURORA_DENIED
    assert "Row-Level Security" in note

    # A business-rule refusal from the tool is not a database authorization fact.
    other, _ = ge.classify_aurora(
        {"status": "policy_blocked", "message": "reason not allowed"}
    )
    assert other == ge.AURORA_NOT_REACHED


def test_a_replay_is_permitted_but_says_so() -> None:
    state, note = ge.classify_aurora(
        {"status": "success", "idempotent_replay": True}
    )
    assert state == ge.AURORA_PERMITTED
    assert "replayed" in note


def test_the_evidence_axis_names_the_artifact_that_exists() -> None:
    assert ge.classify_evidence_for(
        ge.POLICY_DENY, ge.AURORA_NOT_REACHED, {}
    ) == ge.EVIDENCE_POLICY_PROOF
    assert ge.classify_evidence_for(
        ge.POLICY_WOULD_DENY, ge.AURORA_DENIED, {}
    ) == ge.EVIDENCE_ATTEMPT_RECEIPT
    assert ge.classify_evidence_for(
        ge.POLICY_ALLOW, ge.AURORA_PERMITTED, {"status": "success"}
    ) == ge.EVIDENCE_RECEIPTED


def test_no_axis_is_derived_from_another() -> None:
    """Each combination the architecture allows must be representable.

    A confirmed human decision with an unevaluated policy and an untouched
    database is a legitimate state, and so is an allowed policy with a denied
    database. If any pair were coupled, one of these would be unreachable.
    """
    combinations = [
        (ge.POLICY_NOT_EVALUATED, ge.AURORA_PERMITTED),
        (ge.POLICY_NOT_EVALUATED, ge.AURORA_DENIED),
        (ge.POLICY_ALLOW, ge.AURORA_DENIED),
        (ge.POLICY_ALLOW, ge.AURORA_PERMITTED),
        (ge.POLICY_WOULD_DENY, ge.AURORA_DENIED),
        (ge.POLICY_DENY, ge.AURORA_NOT_REACHED),
    ]
    seen = {
        ge.classify_evidence_for(policy, aurora, {"status": "success"})
        for policy, aurora in combinations
    }
    assert len(seen) >= 3, f"the evidence axis collapsed too far: {seen}"


@pytest.mark.asyncio
async def test_an_rls_denied_execution_reports_denied_and_an_attempt_receipt() -> None:
    FakeLogic.envelope = {
        "status": "policy_blocked",
        "message": "not authorized to act on CUST-THEO's orders",
        "denied_by": "database_row_level_security",
    }
    outcome = await ge.execute_confirmed_review(
        FakeDb(), approved_review(), operator_sub=OPERATOR_SUBJECT
    )
    assert outcome.aurora == ge.AURORA_DENIED
    assert outcome.evidence == ge.EVIDENCE_ATTEMPT_RECEIPT
    # And the human axis is untouched by a database outcome.
    assert outcome.as_payload()["assurance"]["human"] == "CONFIRMED"


# ---------------------------------------------------------------------------
# Runtime role and RLS binding, on the Gateway rail
# ---------------------------------------------------------------------------

def test_the_lambda_binds_a_non_owner_role_and_the_customer_principal() -> None:
    source = (DEPLOY / "common" / "dataapi.py").read_text()
    assert "def bind_runtime_principal(" in source
    assert "SET LOCAL ROLE" in source
    assert "set_config('pellier.principal_sub'" in source
    assert ", true)" in source, "the principal must be transaction-local"
    assert "_RUNTIME_ROLES" in source, "the role must be whitelisted, not interpolated"


def test_the_runtime_roles_are_non_owner_and_do_not_bypass_rls() -> None:
    sql = (REPO / "scripts" / "migrations" / "016_runtime_roles_rls.sql").read_text()
    assert "CREATE ROLE pellier_agent NOLOGIN NOINHERIT NOBYPASSRLS" in sql
    assert "CREATE ROLE pellier_query NOLOGIN NOINHERIT NOBYPASSRLS" in sql
    assert "ALTER TABLE pellier.orders  ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE pellier.returns ENABLE ROW LEVEL SECURITY" in sql


def test_the_lambda_never_accepts_a_customer_subject_from_the_wire() -> None:
    """The hole this closes: a caller naming its own RLS principal."""
    source = (DEPLOY / "pellier_experience_server.py").read_text()
    assert 'if key not in ("turn_id", "customer_subject")' in source
    assert "def _resolve_customer_subject(" in source
    assert "FROM {SCHEMA}.principal_customers" in source


def test_the_protected_db_function_keeps_its_name() -> None:
    """`initiate_return` is the public tool; the function stays
    `process_return_idempotent` because migration 016 grants EXECUTE on that
    exact identifier."""
    grants = (REPO / "scripts" / "migrations" / "016_runtime_roles_rls.sql").read_text()
    assert "process_return_idempotent" in grants
    lambda_src = (DEPLOY / "pellier_experience_server.py").read_text()
    assert "process_return_idempotent" in lambda_src


# ---------------------------------------------------------------------------
# Bypass closure
# ---------------------------------------------------------------------------

def test_both_legacy_action_endpoints_require_a_confirmed_review() -> None:
    source = (BACKEND / "routes" / "operator.py").read_text()
    for handler in ("async def resolve_return(", "async def issue_credit("):
        block = source.split(handler, 1)[1].split("\n@router", 1)[0]
        assert "_require_confirmed_review(" in block, (
            f"{handler} can still mutate without a confirmed review"
        )


def test_the_bypass_guard_matches_on_the_action_fingerprint() -> None:
    """Any approved review is not enough; it must be for these parameters."""
    source = (BACKEND / "routes" / "operator.py").read_text()
    guard = source.split("async def _require_confirmed_review(", 1)[1].split(
        "\n@router", 1
    )[0]
    assert "action_fingerprint(" in guard
    assert "a.action_hash = %s" in guard
    assert "a.status = 'approved'" in guard


def test_the_execute_route_accepts_no_action_parameters() -> None:
    """The browser supplies review identity only.

    Asserted on the model's declared fields. An earlier version scanned the class
    source and tripped on its own docstring, which names the parameters precisely
    in order to say they are not accepted.
    """
    from routes.operator import ReviewExecuteRequest

    fields = set(ReviewExecuteRequest.model_fields)
    assert fields == {"expectedActionHash"}, (
        f"the execute request accepts {sorted(fields)}; anything beyond a "
        "stale-view fingerprint would let a browser execute a different mutation "
        "than the one confirmed"
    )


def test_policy_mode_is_never_client_input() -> None:
    """Enforcement is control-plane state, not a request parameter."""
    source = (BACKEND / "routes" / "operator.py").read_text()
    for forbidden in ("LOG_ONLY", "ENFORCE", "policy_mode", "policyMode"):
        assert forbidden not in source, (
            f"{forbidden} appears in the operator routes; policy mode must come "
            "from the engine, never from a caller"
        )


# ---------------------------------------------------------------------------
# Migration-only compatibility alias (Phase B1)
# ---------------------------------------------------------------------------

def test_the_alias_maps_every_retired_name_to_a_real_implementation() -> None:
    """The live Gateway still invokes retired names; the new Lambda must serve them.

    Temporary. The alias exists only for the window between deploying the
    RLS-aware Lambda and migrating the Gateway/Cedar vocabulary, because the
    deployed targets publish `process_return` while the source implements
    `initiate_return`.
    """
    if str(DEPLOY) not in sys.path:
        sys.path.insert(0, str(DEPLOY))
    from common.types import canonical_tool_name
    from gateway_tool_schemas import TOOL_SCHEMAS

    current = {
        tool["name"]
        for config in TOOL_SCHEMAS.values()
        for tool in config["tools"]
    }
    for retired in (
        "process_return", "escalate_to_stylist", "floor_check", "find_pieces",
        "find_pieces_hybrid", "explore_collection", "running_low", "restock_shelf",
        "whats_trending", "price_intelligence", "side_by_side", "returns_and_care",
        "style_match", "preference_snapshot", "trace_receipt",
    ):
        mapped = canonical_tool_name(retired)
        assert mapped != retired, f"{retired} has no alias"
        assert mapped in current, f"{retired} aliases to {mapped}, which is not published"


def test_the_alias_is_a_no_op_for_current_names() -> None:
    """So it can be applied unconditionally and deleted without a behaviour change."""
    if str(DEPLOY) not in sys.path:
        sys.path.insert(0, str(DEPLOY))
    from common.types import canonical_tool_name
    from gateway_tool_schemas import TOOL_SCHEMAS

    for config in TOOL_SCHEMAS.values():
        for tool in config["tools"]:
            assert canonical_tool_name(tool["name"]) == tool["name"]
    assert canonical_tool_name("list_tools") == "list_tools"


def test_the_alias_never_reaches_discovery() -> None:
    """Retired names must not be advertised to Gateway discovery or a participant.

    `list_tools` builds its response from each surface's own TOOLS mapping, which
    holds current names exclusively. The alias lives in dispatch resolution only.
    """
    source = (DEPLOY / "pellier_experience_server.py").read_text()
    tools_block = source.split("TOOLS = {", 1)[1].split("\n}", 1)[0]
    for retired in ("process_return", "escalate_to_stylist"):
        assert f'"{retired}"' not in tools_block, (
            f"{retired} is a TOOLS key, so list_tools would advertise it"
        )


def test_one_operation_writes_one_audit_identity() -> None:
    """The receipt records the CANONICAL name, whichever alias was invoked.

    Decided deliberately: a legacy invocation and a current invocation of the
    same operation must not produce two different `tool_audit` identities, or
    every evidence query would have to know the migration history.
    """
    import re

    source = (DEPLOY / "pellier_experience_server.py").read_text()
    literals = re.findall(
        r'_write_tool_audit_independently\(\s*\n\s*tool="([^"]+)"', source
    )
    assert literals, "no receipt writer found"
    assert set(literals) == {"initiate_return", "issue_credit"}, (
        f"receipt tool literals drifted: {literals}"
    )
    # And the invoked name is never used as the audit identity.
    assert 'tool=tool_name' not in source
    assert 'tool=prefixed' not in source
