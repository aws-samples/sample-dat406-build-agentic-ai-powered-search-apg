"""The Cedar identity rule and the application must agree on who owns what.

Why a parity test rather than generated policy
----------------------------------------------

The username-to-customer pairs are written out longhand in the Lab 4 reference
policy on purpose: a participant authors that condition and has to reason about
it, so generating it from `USERNAME_TO_CUSTOMER_ID` at deploy time would turn the
exercise into plumbing they never read.

The cost of keeping it explicit is drift. If the application ever remaps a
username and the policy does not follow, the failure is silent and it fails
*open* in the direction that matters: Cedar would permit a principal to act on a
customer the application no longer scopes to them. So the mapping stays readable
and this test carries the duplication risk.

What is checked
---------------

* every application mapping appears in the reference policy;
* the reference policy invents no pair the application does not have;
* the participant starter stays unsolved;
* the claim compared is the access token's, not the ID token's.

Nothing here writes to either file. A validator that repaired the starter would
delete the exercise.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from services.turn_identity import USERNAME_TO_CUSTOMER_ID

_REPO = pathlib.Path(__file__).resolve().parents[3]
STARTER = _REPO / "policies" / "workshop_identity_match_forbid.cedar"
REFERENCE = _REPO / "solutions" / "the-concierge" / "policies" / "identity_match_forbid.cedar"

# `principal.getTag("username") == "marco" && context.input.customer_id == "CUST-MARCO"`
_PAIR = re.compile(
    r'getTag\(\s*"username"\s*\)\s*==\s*"(?P<user>[^"]+)"'
    r'.*?customer_id\s*==\s*"(?P<customer>[^"]+)"',
    re.DOTALL,
)


def _reference_pairs() -> dict[str, str]:
    return {m.group("user"): m.group("customer") for m in _PAIR.finditer(REFERENCE.read_text())}


def test_both_policy_files_exist():
    assert STARTER.is_file(), f"missing participant starter: {STARTER}"
    assert REFERENCE.is_file(), f"missing reference solution: {REFERENCE}"


def test_every_application_mapping_appears_in_the_reference_policy():
    """A mapping the application enforces but Cedar omits fails open."""
    pairs = _reference_pairs()
    missing = {
        user: customer
        for user, customer in USERNAME_TO_CUSTOMER_ID.items()
        if pairs.get(user) != customer
    }
    assert not missing, (
        "the reference Cedar policy does not bind "
        f"{missing}. Add the pair to "
        f"{REFERENCE.relative_to(_REPO)} so the policy and "
        "services/turn_identity.py agree."
    )


def test_the_reference_policy_invents_no_unknown_pair():
    """A pair Cedar permits but the application does not know is a hole."""
    pairs = _reference_pairs()
    unknown = {
        user: customer
        for user, customer in pairs.items()
        if USERNAME_TO_CUSTOMER_ID.get(user) != customer
    }
    assert not unknown, (
        f"the reference Cedar policy binds {unknown}, which "
        "services/turn_identity.py does not map. Remove it or add the mapping."
    )


def test_the_mapping_is_exactly_the_same_size():
    """Catches an extra principal added to only one side."""
    assert len(_reference_pairs()) == len(USERNAME_TO_CUSTOMER_ID)


def test_the_participant_starter_is_still_unsolved():
    """The `unless` block is the Lab 4 build. Shipping it solved removes the lab."""
    starter = STARTER.read_text()
    assert "unless {" in starter
    assert re.search(r"unless\s*\{\s*false\s*\}", starter), (
        "the participant starter must ship with `unless { false }`; it currently "
        "contains something else, so either the exercise was solved in place or "
        "the fail-closed shape was lost."
    )
    for user in USERNAME_TO_CUSTOMER_ID:
        assert f'"{user}"' not in starter, (
            f"the starter names {user!r}, which gives away the answer."
        )


def test_the_starter_and_the_reference_target_the_same_action():
    """A reference that guards a different action would never be reachable."""
    action = re.compile(r'action\s*==\s*AgentCore::Action::"([^"]+)"')
    starter_action = action.search(STARTER.read_text())
    reference_action = action.search(REFERENCE.read_text())
    assert starter_action and reference_action
    assert starter_action.group(1) == reference_action.group(1)


def test_the_reference_is_fail_closed_on_a_missing_claim():
    """A missing tag must deny, not skip the comparison."""
    reference = REFERENCE.read_text()
    assert 'hasTag("username")' in reference, (
        "without an explicit hasTag guard a token carrying no username claim "
        "would fall through the comparison instead of being denied."
    )
    assert "context.input has customer_id" in reference, (
        "a request with no customer_id must be denied rather than compared "
        "against an absent field."
    )


def test_the_claim_is_the_access_token_username_not_the_id_token_claim():
    """`cognito:username` is on the ID token; the Gateway validates the access token.

    Box-verified 2026-06-12. Comparing the wrong claim name yields a tag that is
    never present, which under a fail-closed rule denies everyone and reads like
    a broken policy engine.
    """
    for path in (STARTER, REFERENCE):
        text = path.read_text()
        assert "cognito:username" not in text, (
            f"{path.name} references the ID token claim; the access token the "
            "Gateway validates carries `username`."
        )


@pytest.mark.parametrize("path", [STARTER, REFERENCE], ids=["starter", "reference"])
def test_both_policies_forbid_rather_than_permit(path: pathlib.Path):
    """`forbid ... unless` keeps the default deny; a permit rule would widen access."""
    text = path.read_text()
    assert text.lstrip().count("permit(") == 0, (
        f"{path.name} uses permit; the identity rule must be a forbid so an "
        "unmatched principal stays denied."
    )
    assert "forbid(" in text
