"""A failed governed write must not consume its idempotency key.

Migration 023 exists because of a bug measured live on 2026-08-26:
`process_return_idempotent` claimed the key, then finalised the row
unconditionally, so a *failed* attempt cached its own failure and every later
retry returned it with `idempotent_replay: true` without re-attempting.

The amplification is what makes it serious. The function is not SECURITY DEFINER,
so its ownership probe runs under the caller's role and is subject to the
`orders_principal_scope` RLS policy. Bound to the wrong principal, a real order
becomes invisible and the function stores "Customer X did not order product Y" —
an authorization outcome persisted as a business fact, permanently.

These tests read the migration rather than the database, so they run in the
hermetic suite. The behavioural proof lives in the migration's own verification
block, which raises unless a failed attempt leaves no finalised row and a success
records once and replays once.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MIGRATION = REPO / "scripts" / "migrations" / "023_idempotency_claims_release_on_failure.sql"
ELEVEN = REPO / "scripts" / "migrations" / "011_governed_write_integrity.sql"


def _body() -> str:
    return MIGRATION.read_text()


def test_the_migration_exists_and_replaces_the_function() -> None:
    text = _body()
    assert "CREATE OR REPLACE FUNCTION pellier.process_return_idempotent" in text


def test_the_finalising_update_is_conditional_on_success() -> None:
    """The whole fix is that this UPDATE no longer runs for a failure."""
    text = _body()
    match = re.search(
        r"IF v_result->>'status' = 'success' THEN\s*"
        r"UPDATE pellier\.write_operations\s*"
        r"SET result = v_result,\s*completed_at = now\(\)",
        text,
    )
    assert match, "the finalising UPDATE is not gated on a success status"


def test_a_failure_is_never_written_as_a_completed_row() -> None:
    """Exactly one finalising UPDATE, and it is inside the success branch.

    Counted over the function body only: the header comment quotes the old,
    unconditional version to explain the defect, and that quotation must not be
    mistaken for live code.
    """
    text = _body()
    body = text[text.index("CREATE OR REPLACE FUNCTION"):text.index("-- Verification")]
    assert body.count("SET result = v_result") == 1
    assert body.count("completed_at = now()") == 1


def test_the_claim_is_released_without_deleting_anything() -> None:
    """Releasing by DELETE needed a grant the agent role must not have.

    016 grants `pellier_agent` SELECT, INSERT, UPDATE on write_operations. A
    DELETE-based release raised `permission denied for table write_operations`
    under that role and aborted the transaction, turning a clean business refusal
    into an error. Granting DELETE would let the runtime role remove write
    evidence, which defeats the table's purpose.
    """
    text = _body()
    assert "DELETE FROM pellier.write_operations" not in text.split(
        "-- Verification"
    )[0], "the function body deletes write evidence"
    assert "permission denied" in text, "the reason for not deleting is not recorded"


def test_the_agent_role_is_not_granted_delete_on_write_operations() -> None:
    grants = (REPO / "scripts" / "migrations" / "016_runtime_roles_rls.sql").read_text()
    line = next(
        l for l in grants.splitlines()
        if "write_operations TO pellier_agent" in l
    )
    assert "DELETE" not in line.upper(), (
        f"the runtime role can delete write evidence: {line.strip()}"
    )


def test_the_replay_guard_still_requires_a_stored_result() -> None:
    """Unfinalised claims must not short-circuit a retry."""
    text = _body()
    assert "IF NOT v_claimed AND v_existing.result IS NOT NULL THEN" in text


def test_a_vanished_claim_is_adopted_rather_than_used_as_null() -> None:
    """Otherwise the argument guard compares against NULL and silently passes."""
    text = _body()
    assert "IF NOT FOUND THEN" in text
    assert "v_claimed := TRUE;" in text


def test_the_idempotency_conflict_guard_is_preserved() -> None:
    text = _body()
    assert "idempotency_conflict" in text
    assert "v_existing.request_hash <> p_request_hash" in text


def test_the_success_result_shape_is_unchanged_from_011() -> None:
    """The fix must not alter what a successful return reports."""
    new, old = _body(), ELEVEN.read_text()
    for field in ("'status', 'success'", "'return_id', v_return_id",
                  "'idempotent_replay', false", "'new_quantity'"):
        assert field in new, field
        assert field in old, field


def test_the_migration_verifies_its_own_invariant() -> None:
    """A migration that only redefines a function proves nothing."""
    text = _body()
    assert "RAISE EXCEPTION" in text
    assert "the idempotency key is consumed" in text
    assert "did not report a replay" in text
    assert "applied the write more than once" in text


def test_the_rls_amplification_is_documented_not_just_the_bug() -> None:
    """The next reader must know why caching this outcome is unsafe."""
    text = _body()
    assert "RLS" in text
    assert "SECURITY DEFINER" in text
    assert "orders_principal_scope" in text
    body = text.split("-- Verification")[0]
    assert "RLS is hiding one that exists" in body, (
        "the ownership branch does not record that it cannot distinguish a "
        "missing order from a hidden one"
    )
