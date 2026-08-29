"""Golden retail journeys: deterministic fixture and teaching-contract gates.

Version 2 keeps the original fixture regressions, then adds the stage contract
participants are meant to learn:

    intent -> identity -> grounding -> proposal -> human decision
      -> authorization -> data enforcement -> durable evidence -> outcome

The file does not claim a local fixture proves AgentCore. Managed verdicts stay
``deferred_live`` until a fresh AWS environment produces them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_FILE = Path(__file__).resolve().parent / "golden" / "journeys.json"


def _load_golden() -> Dict[str, Any]:
    return json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))


GOLDEN = _load_golden()
JOURNEYS = GOLDEN["journeys"]


def _fixture_checks() -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    for journey in JOURNEYS:
        for check in journey.get("fixtureChecks", []):
            yield journey, check


FIXTURE_CHECKS = list(_fixture_checks())


def _load_fixture(fixture_name: str) -> Dict[str, Any]:
    path = REPO_ROOT / GOLDEN["fixtureRoot"] / fixture_name
    return json.loads(path.read_text(encoding="utf-8"))


def _assistant_turn(fixture: Dict[str, Any], turn_index: int) -> Dict[str, Any]:
    """Return the Nth assistant message (1-indexed) from the chat array."""
    assistants = [m for m in fixture.get("chat", []) if m.get("role") == "assistant"]
    if turn_index < 1 or turn_index > len(assistants):
        raise AssertionError(
            f"Fixture has {len(assistants)} assistant turns; asked for turn {turn_index}"
        )
    return assistants[turn_index - 1]


@pytest.mark.parametrize(
    ("journey", "check"),
    FIXTURE_CHECKS,
    ids=[f"{j['id']}:{c['id']}" for j, c in FIXTURE_CHECKS],
)
def test_golden_fixture_check(
    journey: Dict[str, Any], check: Dict[str, Any]
) -> None:
    fixture = _load_fixture(check["fixture"])
    asserts = check["asserts"]
    check_id = f"{journey['id']}:{check['id']}"

    expected_pattern = asserts.get("routingPattern")
    if expected_pattern is not None:
        assert fixture.get("routingPattern") == expected_pattern, (
            f"{check_id}: routingPattern drift "
            f"(expected {expected_pattern!r}, got {fixture.get('routingPattern')!r})"
        )

    turn = _assistant_turn(fixture, asserts["turn"])
    tool_calls: List[Dict[str, Any]] = turn.get("toolCalls", [])
    tools_in_order = [tc["toolName"] for tc in tool_calls]
    tools_set = set(tools_in_order)

    for tool in asserts.get("expectedTools", []):
        assert tool in tools_set, (
            f"{check_id}: expected tool {tool!r} missing (saw {tools_in_order})"
        )

    expected_order = asserts.get("expectedToolsInOrder", [])
    index = -1
    for tool in expected_order:
        try:
            index = tools_in_order.index(tool, index + 1)
        except ValueError as exc:
            raise AssertionError(
                f"{check_id}: expected {expected_order} as a subsequence; "
                f"saw {tools_in_order}"
            ) from exc

    for tool in asserts.get("forbiddenTools", []):
        assert tool not in tools_set, (
            f"{check_id}: forbidden tool {tool!r} fired (saw {tools_in_order})"
        )

    products = [p["name"] for p in turn.get("products", [])]
    products_set = set(products)
    for name in asserts.get("expectedProductsAll", []):
        assert name in products_set, (
            f"{check_id}: required product {name!r} missing (surfaced {products})"
        )

    expected_any = asserts.get("expectedProductsAny", [])
    if expected_any:
        assert any(name in products_set for name in expected_any), (
            f"{check_id}: none of {expected_any} surfaced (surfaced {products})"
        )


def test_golden_set_names_the_complete_retail_cast() -> None:
    """The hero remains three people; guest and Jessica add boundary coverage."""
    personas = {journey["persona"] for journey in JOURNEYS}
    assert personas == {"guest", "marco", "anna", "theo", "jessica"}


@pytest.mark.parametrize("journey", JOURNEYS, ids=[j["id"] for j in JOURNEYS])
def test_every_journey_uses_the_same_teaching_order(journey: Dict[str, Any]) -> None:
    expected = GOLDEN["stageContract"]["order"]
    stages = journey["stages"]
    assert [stage["id"] for stage in stages] == expected

    allowed = set(GOLDEN["stageContract"]["proofStates"])
    assert all(stage["proof"] in allowed for stage in stages)
    assert all(stage["teaches"].strip() for stage in stages)


def test_closed_loop_keeps_actor_subject_and_confirmation_distinct() -> None:
    """The operator is authorized; the customer is the RLS subject."""
    journey = next(
        item for item in JOURNEYS if item["id"] == "theo-damaged-return-closed-loop"
    )
    actors = journey["actors"]
    contract = journey["closedLoop"]

    assert actors["executor"]["principal"] != actors["customerSubject"]
    assert actors["executor"]["requiredGroup"] == "pellier-operators"
    assert contract["humanConfirmationRequired"] is True
    assert contract["executionParametersSource"] == "persisted_review_only"
    assert contract["serverResolvedCustomerSubject"] is True


def test_closed_loop_requires_fingerprint_idempotency_rls_and_receipt() -> None:
    journey = next(
        item for item in JOURNEYS if item["id"] == "theo-damaged-return-closed-loop"
    )
    contract = journey["closedLoop"]

    assert contract["materialParameters"] == [
        "customer_id",
        "product_id",
        "reason",
    ]
    assert contract["actionFingerprint"] == "sha256_canonical_operation_arguments"
    assert contract["idempotencyRequired"] is True
    assert contract["rowLevelSecurityRequired"] is True
    assert contract["receiptRequired"] is True
    assert contract["correlationKey"] == "turn_id"


def test_local_golden_set_never_fabricates_a_managed_verdict() -> None:
    """Local PostgreSQL may prove workflow state, never Cedar ALLOW/DENY."""
    for journey in JOURNEYS:
        if journey["kind"] != "governed_write":
            continue
        by_id = {stage["id"]: stage for stage in journey["stages"]}
        assert by_id["authorization"]["proof"] == "deferred_live"
        assert by_id["customer_outcome"]["proof"] == "deferred_live"
        assert (
            journey["closedLoop"]["localExecutionBoundary"]
            == "managed_execution_deferred_live"
        )


def test_jessica_preserves_fact_context_and_inference() -> None:
    journey = next(
        item
        for item in JOURNEYS
        if item["id"] == "jessica-return-evidence-reconciliation"
    )
    contract = journey["epistemicContract"]

    assert set(contract) == {"fact", "context", "inference", "forbiddenClaim"}
    assert "returns" in contract["fact"].lower()
    assert "TKT-2026-3015" in contract["context"]
    assert journey["safeStop"]["consequentialActionPrepared"] is False
    assert contract["forbiddenClaim"] == "Jessica completed a return"
