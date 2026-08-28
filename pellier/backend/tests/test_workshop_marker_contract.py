"""The anchors the lab guide points at, asserted from the source side.

Why this file exists
--------------------

The Workshop Studio guide names exact paths, exact marker strings, and exact CLI flags.
A participant does not debug a drifted instruction; they read "edit between the markers",
find no markers, and stop. Every anchor below is quoted from the shipped guide, so a
rename in this repository fails here instead of in a room.

These tests cannot read the guide: the lab content lives in the sibling
``build-governed-agentic-ai-search-with-aurora-rds-bedrock-agentcore`` repository, which
CI does not clone. The anchors are therefore written out once, each with the page and
step it comes from, and this file is the source-side half of the contract. Changing an
anchor means changing both repositories, which is the point.

What each lab needs from the source tree
----------------------------------------

**Lab 1 - Ground answers in live data.** Two marker regions to fill and two fallback
files to copy. A missing marker breaks the primary lane; a missing fallback breaks the
recovery lane, which is worse, because it only fails for the participant who is already
behind.

**Lab 4 - Govern actions and prove outcomes.** A starter Cedar file that must NOT contain
the answer, a reference rule that must, and one proof script whose flags the guide passes
verbatim.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest

REPO = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Lab 1, "10-ground-answers-in-live-data", steps 1 and 2 plus the pacing fallback.
# ---------------------------------------------------------------------------

LAB1_REGIONS: Tuple[Tuple[str, str], ...] = (
    ("pellier/backend/agents/inventory_agent.py",
     "WORKSHOP · Inventory Agent · definition"),
    ("pellier/backend/services/agent_tools.py",
     "WORKSHOP · Inventory Agent · check_inventory"),
)

# The exact `cp` sources in the guide's pacing fallback. A participant runs these
# verbatim, so a renamed solution file is a dead recovery lane.
LAB1_FALLBACK_COPIES: Tuple[Tuple[str, str], ...] = (
    ("solutions/waking-the-stock-keeper/agents/inventory_agent_solution.py",
     "pellier/backend/agents/inventory_agent.py"),
    ("solutions/closing-marcos-gap/services/agent_tools_check_inventory_solution.py",
     "pellier/backend/services/agent_tools.py"),
)

# ---------------------------------------------------------------------------
# Lab 4, "40-govern-actions-and-prove-outcomes", steps 1 through 4.
# ---------------------------------------------------------------------------

LAB4_STARTER = "policies/workshop_identity_match_forbid.cedar"
LAB4_REFERENCE = "solutions/the-concierge/policies/identity_match_forbid.cedar"
LAB4_PROOF_SCRIPT = "scripts/deploy/gateway_initiate_return.py"

# The policy name passed to `agentcore add policy --name` and to the proof script's
# `--policy-name`. One string in three places.
LAB4_POLICY_NAME = "workshop_identity_match_forbid"

# The target-qualified action Gateway generates. The guide shows it inside the starter,
# and the rule is inert against any other action id.
LAB4_ACTION = "pellier-concierge-experience-target___initiate_return"

# Every flag the guide passes to the proof script, in both the DENY and ALLOW steps.
LAB4_PROOF_FLAGS = (
    "--customer-id", "--product-id", "--reason", "--expect",
    "--record-receipt", "--policy-name", "--session-id",
)

# The identity pairs the reference rule binds. Each pair joins a Cognito username to an
# Aurora customer id, which is the whole lesson of the lab.
LAB4_IDENTITY_PAIRS = (
    ("marco", "CUST-MARCO"),
    ("anna", "CUST-ANNA"),
    ("theo", "CUST-THEO"),
)


def _read(rel: str) -> str:
    path = REPO / rel
    assert path.is_file(), f"{rel} is named by the lab guide but is not in the repository"
    return path.read_text(encoding="utf-8")


def _marker_pair(text: str, label: str) -> Tuple[int, int]:
    start = text.find(f"{label}: START ===")
    end = text.find(f"{label}: END ===")
    return start, end


@pytest.mark.parametrize("rel,label", LAB1_REGIONS)
def test_lab1_region_has_exactly_one_marker_pair(rel: str, label: str) -> None:
    """Two pairs would make "edit between the markers" ambiguous; zero makes it false."""
    text = _read(rel)
    assert text.count(f"{label}: START ===") == 1, f"{rel}: expected one START for {label}"
    assert text.count(f"{label}: END ===") == 1, f"{rel}: expected one END for {label}"


@pytest.mark.parametrize("rel,label", LAB1_REGIONS)
def test_lab1_region_is_ordered_and_not_empty(rel: str, label: str) -> None:
    """An inverted or empty region reads as "nothing to do here"."""
    text = _read(rel)
    start, end = _marker_pair(text, label)
    assert start < end, f"{rel}: START must precede END for {label}"
    body = text[text.index("\n", start) + 1:end]
    assert body.strip(), f"{rel}: the {label} region is empty"


@pytest.mark.parametrize("rel,label", LAB1_REGIONS)
def test_lab1_marker_uses_the_middle_dot_the_guide_quotes(rel: str, label: str) -> None:
    """The guide quotes the marker with U+00B7.

    A participant searching the file for the string in the guide finds nothing if this
    ever becomes a hyphen or an ASCII dot, and "search for this text" is the only
    instruction that lane gives.
    """
    text = _read(rel)
    assert "·" in label
    assert label in text


@pytest.mark.parametrize("source,destination", LAB1_FALLBACK_COPIES)
def test_lab1_fallback_copy_exists_at_both_ends(source: str, destination: str) -> None:
    assert (REPO / source).is_file(), f"the guide copies {source}, which is absent"
    assert (REPO / destination).is_file(), f"the guide copies onto {destination}, which is absent"


@pytest.mark.parametrize("source,destination", LAB1_FALLBACK_COPIES)
def test_lab1_fallback_copy_keeps_the_markers(source: str, destination: str) -> None:
    """The recovery lane must not destroy the anchor.

    A participant who takes the fallback and then wants to read what changed needs the
    same marker region in the copied file. A solution written without markers turns one
    recovery into a dead end for the rest of the lab.
    """
    text = (REPO / source).read_text(encoding="utf-8")
    labels = [label for rel, label in LAB1_REGIONS if rel == destination]
    assert labels, f"{destination} is not a Lab 1 marker file"
    for label in labels:
        assert f"{label}: START ===" in text, f"{source} lost the {label} START marker"
        assert f"{label}: END ===" in text, f"{source} lost the {label} END marker"


def test_lab4_starter_does_not_ship_the_answer() -> None:
    """The starter must hold the placeholder, not the identity mapping.

    This is the same failure the fresh policy renderer had: a stack that pre-installs the
    participant's answer makes step 3's DENY fire before they have written anything, and
    the exercise silently becomes a copy-paste.
    """
    text = _read(LAB4_STARTER)
    assert re.search(r"unless\s*\{\s*false\s*\}", text), (
        f"{LAB4_STARTER} no longer holds the `unless {{ false }}` starter the guide "
        "tells the participant to replace"
    )
    for username, customer_id in LAB4_IDENTITY_PAIRS:
        assert f'"{customer_id}"' not in text, (
            f"{LAB4_STARTER} contains {customer_id}: the starter is shipping the answer"
        )
        assert f'getTag("username") == "{username}"' not in text


def test_lab4_starter_targets_the_generated_action() -> None:
    """A `forbid` on the wrong action id is inert, and an inert rule looks like an ALLOW."""
    text = _read(LAB4_STARTER)
    assert LAB4_ACTION in text, f"{LAB4_STARTER} must forbid {LAB4_ACTION}"
    assert "resource is AgentCore::Gateway" in text
    assert text.lstrip().startswith("//") or "forbid(" in text


def test_lab4_reference_rule_binds_every_identity_pair() -> None:
    """The fallback must be complete, or the participant who takes it still fails step 4."""
    text = _read(LAB4_REFERENCE)
    assert LAB4_ACTION in text
    assert 'principal.hasTag("username")' in text
    assert "context.input has customer_id" in text
    for username, customer_id in LAB4_IDENTITY_PAIRS:
        assert f'getTag("username") == "{username}"' in text, f"{LAB4_REFERENCE} lost {username}"
        assert f'context.input.customer_id == "{customer_id}"' in text


def test_lab4_reference_rule_is_the_starter_plus_the_condition() -> None:
    """Same head, different body.

    If the reference drifted to a different action or effect, the fallback would deploy a
    policy that cannot produce the DENY the guide's step 3 asserts.
    """
    starter = _read(LAB4_STARTER)
    reference = _read(LAB4_REFERENCE)
    for fragment in ("forbid(", "principal,", f'action == AgentCore::Action::"{LAB4_ACTION}"',
                     "resource is AgentCore::Gateway", "unless {"):
        assert fragment in starter, f"{LAB4_STARTER} lost {fragment!r}"
        assert fragment in reference, f"{LAB4_REFERENCE} lost {fragment!r}"


def test_lab4_proof_script_accepts_every_flag_the_guide_passes() -> None:
    """Parsed from the argparse calls, so a renamed flag fails here.

    The guide's step 3 and step 4 commands are identical apart from the bearer token, and
    both are pasted verbatim. A dropped flag is an immediate `unrecognized arguments`.
    """
    source = _read(LAB4_PROOF_SCRIPT)
    declared = set(re.findall(r'add_argument\(\s*"(--[a-z-]+)"', source))
    missing = sorted(flag for flag in LAB4_PROOF_FLAGS if flag not in declared)
    assert not missing, f"{LAB4_PROOF_SCRIPT} does not declare {missing}"


def test_lab4_policy_name_default_matches_the_cli_step() -> None:
    """One name in three places: the CLI `add policy`, the proof script, and the receipt."""
    source = _read(LAB4_PROOF_SCRIPT)
    assert f'"--policy-name", default="{LAB4_POLICY_NAME}"' in source, (
        f"{LAB4_PROOF_SCRIPT} must default --policy-name to {LAB4_POLICY_NAME}"
    )
    assert Path(LAB4_STARTER).stem == LAB4_POLICY_NAME, (
        "the starter filename is what the guide's --source points at; it must match "
        "the policy name"
    )


def test_lab4_proof_script_parses() -> None:
    """A syntax error in the one script the required proof runs is not a runtime problem."""
    ast.parse(_read(LAB4_PROOF_SCRIPT))


def test_no_lab_anchor_is_a_broken_path() -> None:
    """One list, so a future anchor cannot be added without an existence check."""
    anchors: List[str] = [rel for rel, _ in LAB1_REGIONS]
    anchors += [source for source, _ in LAB1_FALLBACK_COPIES]
    anchors += [destination for _, destination in LAB1_FALLBACK_COPIES]
    anchors += [LAB4_STARTER, LAB4_REFERENCE, LAB4_PROOF_SCRIPT]
    absent = sorted({rel for rel in anchors if not (REPO / rel).is_file()})
    assert not absent, f"lab anchors missing from the repository: {absent}"


# ---------------------------------------------------------------------------
# Lab titles, as the participant reads them in TWO products.
#
# The guide was renamed to a GROUND / RETRIEVE / OPERATE / GOVERN & PROVE spine and the
# shipped application was not, so the Observatory's Workshop Map and Proof Board went on
# naming "Design the Retrieval Strategy" while the guide beside them said "Measure Hybrid
# Retrieval Trade-offs". Nothing failed: the naming guards in this repository scan for
# retired SURFACE and TOOL names, and a lab title is neither.
#
# The same constraint as the rest of this file applies. CI does not clone the guide, so the
# canonical titles are written out once here and the source side is asserted against them.
# Changing a title means changing both repositories, which is the point.
# ---------------------------------------------------------------------------

CANONICAL_LAB_TITLES: Tuple[str, ...] = (
    "Ground Answers in Live Data",
    "Measure Hybrid Retrieval Trade-offs",
    "Operate the Managed Agent Path",
    "Govern Actions and Prove Outcomes",
)

# Titles the rename replaced. Present anywhere in the shipped product, they are drift.
RETIRED_LAB_TITLES: Tuple[str, ...] = (
    "Design the Retrieval Strategy",
    "Run Agents in a Managed Runtime",
    "Govern and Trace Agent Actions",
)

# Surfaces a participant actually reads a lab title on, plus the API that supplies one.
LAB_TITLE_SURFACES: Tuple[str, ...] = (
    "pellier/backend/routes/observatory.py",
    "pellier/frontend/src/observatory/surfaces/observe/WorkshopMap.tsx",
    "pellier/frontend/src/observatory/surfaces/observe/ProofBoard.tsx",
)


def test_no_shipped_surface_names_a_retired_lab_title() -> None:
    """The finding this closes, asserted where a participant would see it."""
    findings = []
    for rel in LAB_TITLE_SURFACES:
        text = _read(rel)
        for retired in RETIRED_LAB_TITLES:
            if retired in text:
                line = text[: text.index(retired)].count("\n") + 1
                findings.append(f"  {rel}:{line}  {retired}")
    assert not findings, (
        "shipped surfaces still name retired lab titles, so the application and the guide "
        "disagree in the same viewport:\n" + "\n".join(findings)
    )


def test_the_workshop_map_and_proof_board_use_the_canonical_titles() -> None:
    """Absence of the old name is not presence of the new one.

    A surface that dropped its lab labels entirely would satisfy the check above while
    telling a participant less than before.
    """
    workshop_map = _read(
        "pellier/frontend/src/observatory/surfaces/observe/WorkshopMap.tsx"
    )
    for title in CANONICAL_LAB_TITLES:
        assert title in workshop_map, f"the Workshop Map no longer names {title!r}"

    api = _read("pellier/backend/routes/observatory.py")
    for title in CANONICAL_LAB_TITLES[1:]:
        assert title in api, f"the Proof Board API no longer names {title!r}"


def test_the_retired_and_canonical_title_lists_do_not_overlap() -> None:
    """Guards the two lists above from being edited into agreement."""
    assert not set(CANONICAL_LAB_TITLES) & set(RETIRED_LAB_TITLES)
    assert len(CANONICAL_LAB_TITLES) == 4
