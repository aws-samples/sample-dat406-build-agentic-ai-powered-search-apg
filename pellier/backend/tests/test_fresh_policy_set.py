"""What a FRESH workshop provision would publish and authorize.

The audit gap this closes
-------------------------

Nothing asserted the fresh renderer's output, so it drifted a long way from the
validated live contract without a single test going red:

  * 18 policies instead of 3;
  * a `permit_<tool>` per read tool instead of one exact allow-list;
  * the actor/customer OWNERSHIP condition pre-installed on `initiate_return` — which is
    the Lab 4 challenge, so a fresh stack shipped the participant's answer and step 3's
    DENY fired before they wrote anything;
  * `issue_credit` and `get_ticket_history` published while both are deferred.

These tests parse the GENERATED Cedar. They do not re-implement a second policy model,
and they never assert a count alone: a count passes while the names are wrong.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys
from typing import Dict, List, Set

import pytest

sys.path.insert(0, os.path.abspath("../../scripts/deploy"))

from gateway_tool_schemas import (  # noqa: E402
    TOOL_SCHEMAS,
    WORKSHOP_DEFERRED_TOOLS,
    canonical_tool_names,
    schema_for,
    workshop_published_tools,
    workshop_target_tools,
)
from render_agentcore_project import baseline_policies  # noqa: E402

EXPERIENCE = "pellier-concierge-experience-target"
RETURN_ACTION = f"{EXPERIENCE}___initiate_return"
RECOMMENDATION = "pellier-curation-recommendation-target"
CUSTOMER_READ_POLICIES = {
    "get_customer_preferences_identity_scope": (
        f"{RECOMMENDATION}___get_customer_preferences"
    ),
    "get_audit_trail_identity_scope": f"{RECOMMENDATION}___get_audit_trail",
}

# The exact 15 this workshop iteration publishes. Written out ONCE, here, so a change to
# the derived contract has to be acknowledged in a test rather than absorbed silently.
EXPECTED_PUBLISHED: Set[str] = {
    "search_products", "search_products_hybrid", "browse_category", "check_inventory",
    "get_low_stock", "restock_inventory",
    "get_price_analysis", "compare_products",
    "get_customer_preferences", "get_audit_trail", "get_trending_products",
    "get_return_policy", "get_related_products",
    "initiate_return", "escalate_to_human",
}

EXPECTED_TARGETS: Dict[str, Set[str]] = {
    "pellier-discovery-search-target": {
        "search_products", "search_products_hybrid", "browse_category",
        "check_inventory", "get_low_stock", "restock_inventory",
    },
    "pellier-value-pricing-target": {"get_price_analysis", "compare_products"},
    "pellier-curation-recommendation-target": {
        "get_customer_preferences", "get_audit_trail", "get_trending_products",
        "get_return_policy", "get_related_products",
    },
    "pellier-concierge-experience-target": {"initiate_return", "escalate_to_human"},
}

RETIRED = {
    "floor_check", "running_low", "restock_shelf", "process_return", "find_pieces",
    "find_pieces_hybrid", "whats_trending", "price_intelligence", "explore_collection",
    "side_by_side", "returns_and_care", "style_match", "preference_snapshot",
    "trace_receipt", "escalate_to_stylist",
}


def _policies() -> List[dict]:
    return baseline_policies()


def _by_name() -> Dict[str, dict]:
    return {p["name"]: p for p in _policies()}


def _actions(statement: str) -> List[str]:
    return re.findall(r'AgentCore::Action::"([^"]+)"', statement)


def _norm(statement: str) -> str:
    return " ".join(statement.split())


# ---------------------------------------------------------------------------
# Publication: the exact set, not the count
# ---------------------------------------------------------------------------


def test_the_workshop_publishes_exactly_the_expected_fifteen() -> None:
    assert workshop_published_tools() == EXPECTED_PUBLISHED


def test_the_deferred_pair_is_exactly_issue_credit_and_ticket_history() -> None:
    assert WORKSHOP_DEFERRED_TOOLS == {"issue_credit", "get_ticket_history"}


def test_the_published_set_is_derived_not_hand_copied() -> None:
    """Catalogue minus deferred. A second literal list would drift on the next tool."""
    assert workshop_published_tools() == canonical_tool_names() - WORKSHOP_DEFERRED_TOOLS
    assert len(canonical_tool_names()) == 17
    assert len(workshop_published_tools()) == 15


def test_every_published_name_is_unique() -> None:
    names = [t["name"] for c in TOOL_SCHEMAS.values() for t in c["tools"]]
    assert len(names) == len(set(names)), "a tool name is declared twice"


def test_target_assignment_is_exact() -> None:
    assert {k: set(v) for k, v in workshop_target_tools().items()} == EXPECTED_TARGETS


def test_no_retired_name_is_published() -> None:
    assert workshop_published_tools() & RETIRED == set()


def test_no_deferred_name_is_published() -> None:
    assert workshop_published_tools() & WORKSHOP_DEFERRED_TOOLS == set()


def test_the_experience_target_publishes_only_the_two_governed_actions() -> None:
    """`issue_credit` and `get_ticket_history` live on this target and must not ship."""
    served = [t["name"] for t in schema_for("experience", workshop=True)]
    assert served == ["initiate_return", "escalate_to_human"]
    full = [t["name"] for t in schema_for("experience", workshop=False)]
    assert set(full) - set(served) == {"issue_credit", "get_ticket_history"}


# ---------------------------------------------------------------------------
# The policy set: exact names, effects, actions, conditions
# ---------------------------------------------------------------------------


def test_the_fresh_policy_set_is_exactly_the_named_baseline_and_scoped_reads() -> None:
    """Exact set, never a count: a count passes while the names are wrong."""
    assert set(_by_name()) == {
        "baseline_permit_workshop_tools",
        *CUSTOMER_READ_POLICIES,
        "initiate_return_damaged_only",
        "initiate_return_deny_other_reasons",
    }


def test_every_policy_action_exists_in_the_published_schema() -> None:
    """A policy naming an unpublished action does not deploy at all.

    Measured against the live engine and recorded in
    `scripts/migrate_gateway_vocabulary.py`: `FAIL_ON_ANY_FINDINGS` rejects
    `unrecognized action AgentCore::Action::"..."` for any id absent from the live Gateway
    schema, and `UPDATE_FAILED` does not roll the stored definition back.

    Nothing compared policy actions against the published set until a policy was written
    naming the deferred `issue_credit`, on the reasoning that gating a deferred tool
    "closes the publication window in advance". It would have failed the whole policy on a
    fresh provision.
    """
    published = {
        f"{target}___{tool}"
        for target, tools in workshop_target_tools().items()
        for tool in tools
    }
    for policy in _policies():
        for action in _actions(policy["statement"]):
            assert action in published, (
                f"{policy['name']} names {action}, which a fresh Gateway does not "
                f"publish. Deferred tools: {sorted(WORKSHOP_DEFERRED_TOOLS)}"
            )


def test_every_conditional_policy_pins_one_action() -> None:
    """A conditional policy must use `action ==`, never `action in [...]`.

    The second measured failure. Widening the action set widens the scope the validator
    type-checks the condition against, and the condition is not valid for sibling action
    types such as `Mcp`, `CallTool` and `InvokeLLM`.

    Unconditional policies may use `action in [...]` freely: there is no condition to
    type-check, which is why the baseline allow-list may list thirteen.
    """
    for policy in _policies():
        statement = policy["statement"]
        if not (("when {" in statement) or ("unless {" in statement)):
            continue
        assert "action in [" not in statement, (
            f"{policy['name']} is conditional and uses `action in [...]`; pin it to a "
            "single `action ==` id or split it into one policy per action"
        )
        assert len(_actions(statement)) == 1, (
            f"{policy['name']} is conditional and names "
            f"{len(_actions(statement))} actions"
        )


def test_no_baseline_policy_claims_operator_enforcement() -> None:
    """Operator authorization is an API-only boundary, and must not be faked here.

    A policy gating `restock_inventory` on the operator Cognito group was added and then
    removed, because it enforced nothing: `restock_inventory` is an Inventory Agent tool
    with no operator route, and it has no matching permit, so an operator and a shopper are
    both denied either way. It changed the recorded reason and no outcome, while risking
    the whole provision on an unproven `getTag(...).contains(...)` under
    FAIL_ON_ANY_FINDINGS.

    This guard exists so that cannot come back as reassurance. Gateway-side operator
    enforcement is only meaningful once a genuinely operator-only action is published;
    until then, a policy mentioning the group is decorative at best and a deploy risk at
    worst. When such a tool IS published, add a single-action policy for it, live-validate
    it, and update this test to expect it by name rather than deleting the guard.
    """
    from services.auth import OPERATOR_GROUP

    for policy in _policies():
        statement = policy["statement"]
        assert OPERATOR_GROUP not in statement, (
            f"{policy['name']} names the operator group. Which published, operator-only "
            "action does it gate? If the answer is none, it enforces nothing."
        )
        assert "cognito:groups" not in statement, (
            f"{policy['name']} reads cognito:groups, whose tag representation is not "
            "validated against this engine. See the renderer docstring."
        )


def test_the_operator_only_limitation_is_recorded_where_it_would_be_changed() -> None:
    """A gap someone can act on, not one they have to rediscover.

    Three places a reader would land: the renderer that would carry such a policy, the
    dependency that is the actual boundary, and the route module that describes the
    asymmetry with the shopper rail.
    """
    renderer = pathlib.Path(
        os.path.abspath("../../scripts/deploy/render_agentcore_project.py")
    ).read_text(encoding="utf-8")
    assert "WHY THERE IS NO OPERATOR-AUTHORIZATION POLICY HERE" in renderer
    assert "WHEN AN OPERATOR-ONLY TOOL IS INTENTIONALLY PUBLISHED" in renderer

    auth = pathlib.Path(
        os.path.abspath("../../pellier/backend/services/auth.py")
    ).read_text(encoding="utf-8")
    assert "THE ONLY PLACE operator authorization is enforced" in auth

    routes = pathlib.Path(
        os.path.abspath("../../pellier/backend/routes/operator.py")
    ).read_text(encoding="utf-8")
    assert "there is no Gateway-side" in routes


def test_issue_credit_is_absent_from_the_gateway_rather_than_forbidden() -> None:
    """Absent is a stronger guarantee than forbidden, and a different one.

    A fresh Gateway publishes no `issue_credit` action id, so a shopper cannot reach it
    there at all. Saying Cedar "forbids" it, as an earlier docstring did, names the wrong
    layer as the one denying, which is how each layer ends up believing the other is
    enforcing.
    """
    assert "issue_credit" in WORKSHOP_DEFERRED_TOOLS
    published = {
        tool for tools in workshop_target_tools().values() for tool in tools
    }
    assert "issue_credit" not in published
    for policy in _policies():
        assert "issue_credit" not in policy["statement"], policy["name"]


def test_every_policy_is_active_and_validated_strictly() -> None:
    for policy in _policies():
        assert policy["enforcementMode"] == "ACTIVE", policy["name"]
        assert policy["validationMode"] == "FAIL_ON_ANY_FINDINGS", policy["name"]


def test_the_baseline_is_an_exact_allow_list_not_a_wildcard() -> None:
    """A wildcard hands every future published tool a permit the moment it appears."""
    statement = _by_name()["baseline_permit_workshop_tools"]["statement"]
    assert "action in [" in statement
    assert not re.search(r"permit\s*\(\s*principal,\s*action\s*,", _norm(statement))
    # And no target Action Group, whose membership compiles at policy-save time.
    assert 'action in AgentCore::Action::"pellier-' not in statement


def test_the_baseline_permits_exactly_the_thirteen_safe_actions() -> None:
    expected = {
        f"{target}___{tool}"
        for target, tools in EXPECTED_TARGETS.items()
        for tool in tools
        if tool not in {"initiate_return", "restock_inventory"}
    }
    actual = set(_actions(_by_name()["baseline_permit_workshop_tools"]["statement"]))
    assert actual == expected
    assert len(actual) == 13


def test_the_baseline_is_unconditional() -> None:
    statement = _by_name()["baseline_permit_workshop_tools"]["statement"]
    assert "when {" not in statement
    assert "unless {" not in statement


def test_the_return_pair_names_the_canonical_action_only() -> None:
    for name in ("initiate_return_damaged_only", "initiate_return_deny_other_reasons"):
        actions = _actions(_by_name()[name]["statement"])
        assert actions == [RETURN_ACTION], name
        assert "process_return" not in _by_name()[name]["statement"], name


def test_the_return_permit_is_damaged_only_and_the_forbid_is_its_complement() -> None:
    permit = _norm(_by_name()["initiate_return_damaged_only"]["statement"])
    forbid = _norm(_by_name()["initiate_return_deny_other_reasons"]["statement"])
    assert permit.startswith("permit (")
    assert 'context.input has reason && context.input.reason == "damaged"' in permit
    assert forbid.startswith("forbid (")
    assert '!(context.input has reason) || context.input.reason != "damaged"' in forbid


def test_sensitive_gateway_reads_are_fail_closed_to_the_verified_customer() -> None:
    """Direct Gateway invocation must not turn a customer_id into authority."""
    for name, action in CUSTOMER_READ_POLICIES.items():
        statement = _norm(_by_name()[name]["statement"])
        assert statement.startswith("forbid ("), name
        assert f'AgentCore::Action::"{action}"' in statement, name
        assert 'principal.hasTag("username")' in statement, name
        assert "context.input has customer_id" in statement, name
        for username, customer_id in (
            ("marco", "CUST-MARCO"),
            ("anna", "CUST-ANNA"),
            ("theo", "CUST-THEO"),
            ("jessica", "CUST-JESSICA"),
        ):
            assert (
                f'principal.getTag("username") == "{username}"' in statement
            ), name
            assert f'context.input.customer_id == "{customer_id}"' in statement, name


# ---------------------------------------------------------------------------
# The Lab 4 challenge must NOT be pre-installed
# ---------------------------------------------------------------------------


def test_no_fresh_policy_contains_the_lab_four_ownership_condition() -> None:
    """The load-bearing assertion of this file.

    Binding `principal.getTag("username")` to `context.input.customer_id` is the Lab 4
    exercise. A baseline that already contains it makes the exercise semantically false:
    the cross-customer DENY the participant is meant to create already happens.

    The assertion is the BINDING, not the mere presence of a tag read. It used to be
    "`getTag` appears nowhere", which was a proxy that broke the moment the baseline needed
    a legitimate, unrelated tag check: the operator-group forbid reads
    `cognito:groups`, which has nothing to do with the participant's exercise. A proxy that
    forbids a whole Cedar feature blocks correct policies as readily as incorrect ones.
    """
    for policy in _policies():
        statement = policy["statement"]
        name = policy["name"]
        if RETURN_ACTION not in _actions(statement):
            continue
        assert 'getTag("username")' not in statement, name
        assert 'hasTag("username")' not in statement, name
        assert "context.input.customer_id" not in statement, name
        assert "context.input has customer_id" not in statement, name


def test_no_fresh_policy_names_a_persona_customer() -> None:
    for policy in _policies():
        if RETURN_ACTION not in _actions(policy["statement"]):
            continue
        for persona in (
            "CUST-MARCO",
            "CUST-ANNA",
            "CUST-THEO",
            "CUST-JESSICA",
            '"marco"',
            '"anna"',
            '"theo"',
            '"jessica"',
        ):
            assert persona not in policy["statement"], f"{policy['name']} / {persona}"


def test_the_renderer_documents_the_omission_as_deliberate() -> None:
    """So a later 'hardening' pass cannot re-add the challenge as an oversight."""
    doc = baseline_policies.__doc__ or ""
    assert "absent on purpose" in doc
    assert "Lab 4" in doc
    assert "teaching baseline" in doc


# ---------------------------------------------------------------------------
# Evaluated authorization outcomes
# ---------------------------------------------------------------------------


def _decide(action: str, reason: str | None) -> str:
    """Evaluate the generated statements. Cedar is default-deny and forbid wins."""
    permits, forbids = [], []
    for policy in _policies():
        statement = policy["statement"]
        actions = _actions(statement)
        scoped_in_list = "action in [" in statement
        matches = action in actions if (actions and not scoped_in_list) else action in actions
        if not matches:
            continue
        if "reason" in statement:
            damaged = reason == "damaged"
            wants_damaged = 'reason == "damaged"' in statement
            applies = damaged if wants_damaged else not damaged
        else:
            applies = True
        if not applies:
            continue
        (forbids if statement.lstrip().startswith("forbid") else permits).append(policy["name"])
    if forbids:
        return "DENY"
    return "ALLOW" if permits else "DENY"


@pytest.mark.parametrize(("action", "reason", "expected"), [
    (RETURN_ACTION, "damaged", "ALLOW"),
    (RETURN_ACTION, "not_as_described", "DENY"),
    (RETURN_ACTION, "changed_mind", "DENY"),
    (RETURN_ACTION, None, "DENY"),
    ("pellier-discovery-search-target___restock_inventory", None, "DENY"),
    ("pellier-discovery-search-target___check_inventory", None, "ALLOW"),
    (f"{EXPERIENCE}___escalate_to_human", None, "ALLOW"),
    (f"{EXPERIENCE}___issue_credit", None, "DENY"),
    (f"{EXPERIENCE}___get_ticket_history", None, "DENY"),
    (f"{EXPERIENCE}___some_future_tool", None, "DENY"),
])
def test_the_fresh_authorization_matrix(action: str, reason, expected: str) -> None:
    assert _decide(action, reason) == expected


def test_restock_inventory_has_zero_matching_permits() -> None:
    """P1-04. Publishing the schema must not make a mutation callable.

    Cedar is default-deny, so omission from the allow-list IS the control. No redundant
    permit-plus-forbid pair: that would be a second thing to keep in sync.
    """
    action = "pellier-discovery-search-target___restock_inventory"
    matching = [
        p["name"] for p in _policies()
        if action in _actions(p["statement"])
        and not p["statement"].lstrip().startswith("forbid")
    ]
    assert matching == []
    # It IS published — the tool exists; it simply cannot be authorized.
    assert "restock_inventory" in workshop_published_tools()


def test_a_future_published_tool_is_denied_by_default() -> None:
    for future in ("get_ticket_history", "issue_credit", "anything_at_all"):
        action = f"{EXPERIENCE}___{future}"
        assert _decide(action, None) == "DENY", future
        assert _decide(action, "damaged") == "DENY", future


# ---------------------------------------------------------------------------
# Lab 4: before and after the participant's own Policy work
# ---------------------------------------------------------------------------

CHALLENGE = pathlib.Path("../../policies/workshop_identity_match_forbid.cedar")
SOLUTION = pathlib.Path(
    "../../solutions/the-concierge/policies/identity_match_forbid.cedar")


def _ownership_holds(username: str, customer_id: str) -> bool:
    """The solution rule's `unless` clause, read from the shipped Cedar.

    Parsed from the file rather than reimplemented, so the test cannot pass against a
    solution that no longer says this.
    """
    body = SOLUTION.read_text()
    pairs = re.findall(
        r'getTag\("username"\)\s*==\s*"([a-z]+)"\s*&&\s*'
        r'context\.input\.customer_id\s*==\s*"([A-Z\-]+)"',
        body,
    )
    assert pairs, "the solution no longer binds usernames to customer ids"
    return (username, customer_id) in pairs


def test_the_challenge_file_ships_unsolved() -> None:
    """`unless { false }` denies everything, which is the honest starting state.

    A challenge file containing the answer is the other half of the P1-01 defect.
    """
    body = CHALLENGE.read_text()
    assert re.search(r"unless\s*\{\s*false\s*\}", body)
    assert 'getTag("username")' not in body
    assert "CUST-MARCO" not in body


def test_the_solution_file_contains_the_ownership_binding() -> None:
    body = SOLUTION.read_text()
    assert 'principal.hasTag("username")' in body
    assert "context.input has customer_id" in body
    for username, customer in (
        ("marco", "CUST-MARCO"),
        ("anna", "CUST-ANNA"),
        ("theo", "CUST-THEO"),
        ("jessica", "CUST-JESSICA"),
    ):
        assert _ownership_holds(username, customer), f"{username}/{customer}"


def test_before_the_solution_a_cross_customer_return_is_permitted() -> None:
    """Case F. Marco's token, Theo's damaged return.

    This must ALLOW on the fresh baseline, or the participant has nothing to discover.
    """
    assert _decide(RETURN_ACTION, "damaged") == "ALLOW"
    for policy in _policies():
        if RETURN_ACTION not in _actions(policy["statement"]):
            continue
        assert 'getTag("username")' not in policy["statement"]


def test_after_the_solution_the_cross_customer_return_is_denied() -> None:
    """Case G. The same call, with the participant's rule added.

    The forbid's `unless` fails for marco/CUST-THEO, so the forbid applies and Cedar
    denies — while the owner's own damaged return still passes.
    """
    assert _ownership_holds("marco", "CUST-JESSICA") is False
    assert _ownership_holds("jessica", "CUST-JESSICA") is True
    # And the baseline the solution lands on still permits the damaged case, so the
    # DENY is attributable to the participant's rule and nothing else.
    assert _decide(RETURN_ACTION, "damaged") == "ALLOW"


def test_the_solution_names_the_canonical_action() -> None:
    for path in (CHALLENGE, SOLUTION):
        body = path.read_text()
        assert "___initiate_return" in body, path.name
        assert "___process_return" not in body, path.name


# ---------------------------------------------------------------------------
# One contract, three declarations: they must reconcile
# ---------------------------------------------------------------------------


def test_the_application_catalogue_reconciles_with_the_workshop_contract() -> None:
    """The local MCP catalog and managed workshop subset have distinct roles.

    Three places name the tool set and each has a different job:

        agent_tools.py @tool          what the process can execute (18, incl. in-process only)
        LOCAL_MCP_TOOL_NAMES          local in-process / MCP catalog (17)
        workshop_published_tools()    what a fresh workshop provision publishes (15)

    Asserted as a DERIVED relationship rather than a fourth literal list, so adding a
    tool has to be classified once and cannot drift here.
    """
    import os as _os
    import sys as _sys

    backend = _os.path.abspath(".")
    if backend not in _sys.path:
        _sys.path.insert(0, backend)
    from services.agentcore_gateway import LOCAL_MCP_TOOL_NAMES

    catalogue = set(LOCAL_MCP_TOOL_NAMES)
    assert catalogue == canonical_tool_names(), (
        "the application catalogue and the Gateway schemas disagree: "
        f"{sorted(catalogue ^ canonical_tool_names())}"
    )
    assert catalogue - WORKSHOP_DEFERRED_TOOLS == workshop_published_tools()
    assert len(LOCAL_MCP_TOOL_NAMES) == len(catalogue), "a name is listed twice"


def test_the_in_process_only_tool_is_not_published_anywhere() -> None:
    """`query_business_records` runs model-generated SQL behind a security boundary.

    Classified `IN_PROCESS_ONLY` in `test_managed_gateway_tool_contract.py`: publishing it
    would mean copying that boundary (read-only role, READ ONLY transaction, statement
    timeout, schema allowlist, RLS) into a separate deploy artifact where it would drift.
    It must appear in neither the canonical catalogue nor the workshop set.
    """
    assert "query_business_records" not in canonical_tool_names()
    assert "query_business_records" not in workshop_published_tools()
