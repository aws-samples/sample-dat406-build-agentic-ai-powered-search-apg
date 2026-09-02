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

**Lab 1 - Ground the Answer.** Two marker regions to fill and two fallback
files to copy. A missing marker breaks the primary lane; a missing fallback breaks the
recovery lane, which is worse, because it only fails for the participant who is already
behind.

**Lab 2 - Build and Measure PostgreSQL Hybrid Retrieval.** A runnable psql
worksheet whose RRF expression starts degraded and a complete recovery twin.

**Lab 3 - Operate and Observe the AgentCore Managed Path.** A jq contract whose
OTEL predicates start false and a complete recovery twin.

**Lab 4 - Govern and Prove Actions.** A starter Cedar file that must NOT contain
the answer, a reference rule that must, and one proof script whose flags the guide passes
verbatim.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
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
# Labs 2 and 3, bounded build artifacts plus pacing fallbacks.
# ---------------------------------------------------------------------------

LAB2_STARTER = "workshop/lab-2-rrf.sql"
LAB2_REFERENCE = "solutions/the-quiet-search/sql/lab-2-rrf-solution.sql"
LAB2_MARKER = "WORKSHOP · PostgreSQL RRF · fusion expression"

LAB3_STARTER = "workshop/lab-3-otel-contract.jq"
LAB3_REFERENCE = "solutions/the-ledger/observability/lab-3-otel-contract-solution.jq"
LAB3_MARKER = "WORKSHOP · AgentCore OTEL · trace contract"

# ---------------------------------------------------------------------------
# Lab 4, "40-govern-actions-and-prove-outcomes", steps 1 through 4.
# ---------------------------------------------------------------------------

LAB4_STARTER = "policies/workshop_identity_match_forbid.cedar"
LAB4_REFERENCE = "solutions/the-concierge/policies/identity_match_forbid.cedar"
LAB4_PROOF_SCRIPT = "scripts/deploy/gateway_initiate_return.py"
LAB4_RLS_PROOF = "workshop/lab-4-rls.sql"

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
    ("jessica", "CUST-JESSICA"),
)

PARTICIPANT_EXERCISE_RESET = "scripts/reset_participant_exercises.py"
PARTICIPANT_STARTERS = {
    "lab-1-inventory-agent": (
        "workshop/starters/lab-1/inventory-agent-definition.pyfrag",
        "pellier/backend/agents/inventory_agent.py",
    ),
    "lab-1-inventory-tool": (
        "workshop/starters/lab-1/check-inventory-tool.pyfrag",
        "pellier/backend/services/agent_tools.py",
    ),
    "lab-2-rrf": (
        "workshop/starters/lab-2-rrf.sql",
        LAB2_STARTER,
    ),
    "lab-3-otel": (
        "workshop/starters/lab-3-otel-contract.jq",
        LAB3_STARTER,
    ),
    "lab-4-cedar": (
        "workshop/starters/workshop_identity_match_forbid.cedar",
        LAB4_STARTER,
    ),
}


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


@pytest.mark.parametrize(
    "starter,reference,label",
    (
        (LAB2_STARTER, LAB2_REFERENCE, LAB2_MARKER),
        (LAB3_STARTER, LAB3_REFERENCE, LAB3_MARKER),
    ),
)
def test_labs_2_and_3_have_matching_build_markers(
    starter: str,
    reference: str,
    label: str,
) -> None:
    for rel in (starter, reference):
        text = _read(rel)
        assert text.count(f"{label}: START ===") == 1
        assert text.count(f"{label}: END ===") == 1


def test_lab2_starter_fails_until_rrf_is_authored() -> None:
    starter = _read(LAB2_STARTER)
    reference = _read(LAB2_REFERENCE)
    assert "0::numeric AS recomputed_rrf" in starter
    assert "0::numeric AS recomputed_rrf" not in reference
    assert reference.count("1.0 / (60 +") == 2
    assert "\\if :fusion_matches" in starter
    assert "\\quit 1" in starter


def test_lab3_starter_fails_until_otel_contract_is_authored() -> None:
    starter = _read(LAB3_STARTER)
    reference = _read(LAB3_REFERENCE)
    for field in ("agentSpan", "modelSpan", "toolSpan", "sessionCorrelated"):
        assert f"{field}: false" in starter
        assert f"{field}: false" not in reference
    for required in (
        "invoke_agent",
        "gen_ai.request.model",
        "execute_tool",
        "gen_ai.tool.name",
        'attributes["session.id"]',
    ):
        assert required in reference


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


def test_lab4_rls_proof_covers_read_write_and_rolls_everything_back() -> None:
    """The required psql proof must exercise both RLS clauses without durable writes."""
    text = _read(LAB4_RLS_PROOF)
    for fragment in (
        r"\set ON_ERROR_STOP on",
        "SET LOCAL ROLE pellier_query",
        "SET LOCAL ROLE pellier_agent",
        "current_setting('pellier.principal_sub', true)",
        "CUST-MARCO",
        "CUST-JESSICA",
        "RLS_READ_MARCO_JESSICA_ROWS:",
        "RLS_READ_JESSICA_JESSICA_ROWS:",
        "RLS_PROBE_ROLE_OK",
        "RLS_PROBE_MARCO_SQLSTATE:42501",
        "RLS_PROBE_JESSICA_SQLSTATE:00000",
        "ROLLBACK",
    ):
        assert fragment in text, f"{LAB4_RLS_PROOF} lost {fragment!r}"

    assert "COMMIT" not in text
    assert text.count("ROLLBACK") >= 3


def test_lab4_rls_proof_fails_when_the_positive_controls_do_not_hold() -> None:
    """A deny-everyone database must not look like a successful RLS proof."""
    text = _read(LAB4_RLS_PROOF)
    for condition in (
        "mapped_shoppers <> 4",
        ":'marco_jessica_rows'::INTEGER <> 0",
        ":'jessica_jessica_rows'::INTEGER = 0",
        "RLS_PROBE_MARCO_SQLSTATE:00000",
    ):
        assert condition in text, (
            f"{LAB4_RLS_PROOF} must fail closed when {condition!r} is observed"
        )


def test_no_lab_anchor_is_a_broken_path() -> None:
    """One list, so a future anchor cannot be added without an existence check."""
    anchors: List[str] = [rel for rel, _ in LAB1_REGIONS]
    anchors += [source for source, _ in LAB1_FALLBACK_COPIES]
    anchors += [destination for _, destination in LAB1_FALLBACK_COPIES]
    anchors += [
        LAB4_STARTER,
        LAB4_REFERENCE,
        LAB4_PROOF_SCRIPT,
        LAB4_RLS_PROOF,
    ]
    absent = sorted({rel for rel in anchors if not (REPO / rel).is_file()})
    assert not absent, f"lab anchors missing from the repository: {absent}"


def test_participant_exercise_reset_declares_every_incomplete_artifact() -> None:
    source = _read(PARTICIPANT_EXERCISE_RESET)
    for exercise_id, (starter, destination) in PARTICIPANT_STARTERS.items():
        assert exercise_id in source
        assert starter in source
        assert destination in source


def test_participant_starter_copies_are_incomplete_not_solutions() -> None:
    inventory_agent = _read(PARTICIPANT_STARTERS["lab-1-inventory-agent"][0])
    inventory_tool = _read(PARTICIPANT_STARTERS["lab-1-inventory-tool"][0])
    lab2 = _read(PARTICIPANT_STARTERS["lab-2-rrf"][0])
    lab3 = _read(PARTICIPANT_STARTERS["lab-3-otel"][0])
    lab4 = _read(PARTICIPANT_STARTERS["lab-4-cedar"][0])

    assert "_INVENTORY_AGENT_STUBBED = True" in inventory_agent
    assert "_INVENTORY_SYSTEM_PROMPT_FOR_AGENT = \"\"" in inventory_agent
    assert '"error": "check_inventory is in stub state"' in inventory_tool
    assert "result = _run_async(logic.check_inventory" not in inventory_tool
    assert "0::numeric AS recomputed_rrf" in lab2
    for field in ("agentSpan", "modelSpan", "toolSpan", "sessionCorrelated"):
        assert f"{field}: false" in lab3
    assert re.search(r"unless\s*\{\s*false\s*\}", lab4)
    assert "CUST-JESSICA" not in lab4


def test_participant_exercise_reset_check_accepts_the_checked_in_starters() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / PARTICIPANT_EXERCISE_RESET),
            "--repo",
            str(REPO),
            "--check",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    for exercise_id in PARTICIPANT_STARTERS:
        assert exercise_id in completed.stdout


def test_participant_exercise_reset_restores_only_the_named_marker_region() -> None:
    reset_script = REPO / PARTICIPANT_EXERCISE_RESET
    with tempfile.TemporaryDirectory() as tempdir:
        repo = Path(tempdir)
        for _exercise_id, (starter, destination) in PARTICIPANT_STARTERS.items():
            source_path = repo / starter
            destination_path = repo / destination
            source_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text((REPO / starter).read_text(encoding="utf-8"))
            destination_path.write_text(
                (REPO / destination).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

        inventory_destination = (
            repo / PARTICIPANT_STARTERS["lab-1-inventory-agent"][1]
        )
        inventory_destination.write_text(
            inventory_destination.read_text(encoding="utf-8").replace(
                "_INVENTORY_AGENT_STUBBED = True",
                "_INVENTORY_AGENT_STUBBED = False",
            )
            + "\n# PARTICIPANT_UNRELATED_EDIT\n",
            encoding="utf-8",
        )

        completed = subprocess.run(
            [sys.executable, str(reset_script), "--repo", str(repo)],
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        restored = inventory_destination.read_text(encoding="utf-8")
        assert "_INVENTORY_AGENT_STUBBED = True" in restored
        assert "# PARTICIPANT_UNRELATED_EDIT" in restored


# ---------------------------------------------------------------------------
# Lab titles, as the participant reads them in TWO products.
#
# The guide was renamed to a BUILD / BUILD & MEASURE / OPERATE & OBSERVE /
# GOVERN spine and the
# shipped application was not, so the Observatory's Workshop Map and Proof Board went on
# naming "Design the Retrieval Strategy" while the guide beside them said "Measure Hybrid
# Retrieval Trade-offs". Nothing failed: the naming guards in this repository scan for
# retired SURFACE and TOOL names, and a lab title is neither.
#
# The same constraint as the rest of this file applies. CI does not clone the guide, so the
# canonical titles are written out once here and the source side is asserted against them.
# Changing a title means changing both repositories, which is the point.
# ---------------------------------------------------------------------------

CANONICAL_LAB_TITLE_PARTS: Tuple[Tuple[str, str], ...] = (
    ("Lab 1 · Build", "Build a PostgreSQL-Grounded Agent"),
    ("Lab 2 · Build & Measure", "Build and Measure PostgreSQL Hybrid Retrieval"),
    ("Lab 3 · Operate & Observe", "Operate and Observe the AgentCore Managed Path"),
    ("Lab 4 · Govern", "Enforce Identity and Prove Non-Execution"),
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
    for primary, subtitle in CANONICAL_LAB_TITLE_PARTS:
        assert primary in workshop_map, (
            f"the Workshop Map no longer names {primary!r}"
        )
        assert subtitle in workshop_map, (
            f"the Workshop Map no longer names {subtitle!r}"
        )

    api = _read("pellier/backend/routes/observatory.py")
    for primary, subtitle in CANONICAL_LAB_TITLE_PARTS[1:]:
        assert primary in api, f"the Proof Board API no longer names {primary!r}"
        assert subtitle in api, f"the Proof Board API no longer names {subtitle!r}"


def test_the_retired_and_canonical_title_lists_do_not_overlap() -> None:
    """Guards the two lists above from being edited into agreement."""
    title_parts = {part for title in CANONICAL_LAB_TITLE_PARTS for part in title}
    assert not title_parts & set(RETIRED_LAB_TITLES)
    assert len(CANONICAL_LAB_TITLE_PARTS) == 4
