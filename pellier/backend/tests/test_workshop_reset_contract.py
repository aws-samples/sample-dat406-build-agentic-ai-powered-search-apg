"""The deterministic workshop reset, and the fail-closed default it depends on.

Two release blockers this file locks down
----------------------------------------

1. `WORKSHOP_FORMAT` defaulted to `builders` in BOTH `Settings` and the bootstrap `.env`
   heredoc, on the `governed` branch. A governed deployment that set nothing served
   governed writes on the in-process rail: no human review, no Cedar verdict, no
   `tool_audit` receipt. It happened, and a shopper executed a return directly.

2. `reset-governed-workshop.sh` predates `execution_receipts`, `operator_episodes` and
   the Concierge conversation tables, so a reset cluster kept rows a freshly provisioned
   one has never had. Nothing seeds `conversations`; the fresh baseline is zero.

The reset plan and post-reset state are captured artifacts, so these are contract tests
over the script and the migration chain rather than a live reset.
"""

from __future__ import annotations

import pathlib
import re

RESET = pathlib.Path("../../scripts/reset-governed-workshop.sh")
BOOTSTRAP = pathlib.Path("../../scripts/bootstrap-labs.sh")
MIGRATIONS = pathlib.Path("../../scripts/migrations")
MEMORY_RESET = pathlib.Path("../../scripts/reset_memory_runtime.py")


def _reset_body() -> str:
    return RESET.read_text()


def _truncate_list() -> set[str]:
    """The tables the reset clears, parsed from the TRUNCATE statement itself."""
    body = _reset_body()
    start = body.index("TRUNCATE TABLE")
    block = body[start: body.index("RESTART IDENTITY", start)]
    return set(re.findall(r"pellier\.([a-z_]+)", block))


# ---------------------------------------------------------------------------
# The fail-closed default
# ---------------------------------------------------------------------------


def test_the_settings_default_is_governed_on_this_branch() -> None:
    """Fail closed. The default should be whatever the branch actually ships."""
    from config import Settings

    assert Settings.model_fields["WORKSHOP_FORMAT"].default == "governed"


def test_the_bootstrap_env_default_is_governed() -> None:
    """The systemd unit reads $REPO/.env, so this heredoc is the deployment default.

    A local `pellier/backend/.env` fix does not reach it.
    """
    body = BOOTSTRAP.read_text()
    assert "WORKSHOP_FORMAT='${WORKSHOP_FORMAT:-governed}'" in body
    assert "WORKSHOP_FORMAT='${WORKSHOP_FORMAT:-builders}'" not in body


def test_no_bootstrap_branch_defaults_to_builders() -> None:
    """The `.env` heredoc was not the only fail-open default.

    Fourteen in-script branches read ``${WORKSHOP_FORMAT:-builders}``, so an operator who
    ran bootstrap on this branch without exporting the variable took the builders path
    even though the heredoc it had just written said governed. The CloudFormation asset
    does export it, which is exactly why this went unnoticed: it only misfires for a
    manual or recovery run, which is when a wrong rail is hardest to spot.

    The script now sets the default once and every branch reads that one value.
    """
    body = BOOTSTRAP.read_text()
    assert "${WORKSHOP_FORMAT:-builders}" not in body, (
        "a bootstrap branch still defaults to builders on the governed branch"
    )
    assert 'WORKSHOP_FORMAT="${WORKSHOP_FORMAT:-governed}"' in body, (
        "bootstrap must establish the governed default once, near the other parameters"
    )
    # Established before the first branch that reads it, or the default is decoration.
    default_at = body.index('WORKSHOP_FORMAT="${WORKSHOP_FORMAT:-governed}"')
    first_read = body.index('"${WORKSHOP_FORMAT}"')
    assert default_at < first_read


def test_the_managed_rail_is_required_under_the_default() -> None:
    """With nothing configured, a governed mutation must refuse the in-process rail."""
    from services.execution_rail import requires_managed_rail

    assert requires_managed_rail("initiate_return") is True
    assert requires_managed_rail("issue_credit") is True
    # Reads still serve in process.
    assert requires_managed_rail("check_inventory") is False


# ---------------------------------------------------------------------------
# Reset coverage
# ---------------------------------------------------------------------------


def test_the_reset_clears_the_evidence_tables_added_since_it_was_written() -> None:
    cleared = _truncate_list()
    for table in ("execution_receipts", "operator_episodes"):
        assert table in cleared, table


def test_the_reset_clears_the_conversation_substrate() -> None:
    """Nothing seeds these, so a fresh cluster has zero and a reset one must too."""
    cleared = _truncate_list()
    for table in ("conversations", "messages", "session_metadata", "tool_uses"):
        assert table in cleared, table


def test_the_reset_clears_spans_and_never_recreates_the_retired_table() -> None:
    """The retired name is spelled from parts, so this file does not carry it.

    `tests/test_surface_naming.py` scans the repository for it and is right to: a test
    that hardcodes the token is indistinguishable from code that reintroduces it.
    """
    assert "observatory_spans" in _truncate_list()
    retired = "agent_" + "trace_spans"
    assert retired not in _reset_body()
    assert retired.rsplit("_", 1)[0] not in _reset_body()


def test_the_reset_preserves_the_authorization_mapping() -> None:
    """`principal_customers` is authorization config, not turn evidence.

    Clearing it denies every signed-in shopper their own orders, which presents as a
    broken application rather than as governance.
    """
    assert "principal_customers" not in _truncate_list()


def test_the_reset_reapplies_every_migration_through_027() -> None:
    body = _reset_body()
    for n in range(23, 28):
        prefix = f"0{n}_"
        assert any(prefix in line for line in body.splitlines()), prefix


def test_every_migration_in_the_chain_is_reachable_from_bootstrap() -> None:
    """A migration that exists but is never applied is a table nobody has."""
    on_disk = {p.name for p in MIGRATIONS.glob("0*.sql")}
    registered = BOOTSTRAP.read_text()
    missing = sorted(name for name in on_disk if name not in registered)
    assert not missing, f"migrations not registered in bootstrap: {missing}"


def test_the_reset_uses_truncate_rather_than_delete() -> None:
    """TRUNCATE fires no row-level triggers.

    A DELETE would run `record_inventory_movement` on warehouse_inventory, writing new
    ledger history while trying to clear history, and would be refused outright by
    `reject_governed_turn_receipt_mutation` on governed_turn_receipts.
    """
    body = _reset_body()
    assert "TRUNCATE TABLE" in body
    assert not re.search(r"^\s*DELETE FROM pellier\.", body, re.MULTILINE)


def test_the_reset_does_not_require_control_plane_authority() -> None:
    """A data reset must not need `agentcore deploy`.

    On a deployment whose canonical policies were applied outside the CLI project, a
    deploy would push the project's declarations over them.
    """
    body = _reset_body()
    assert "PELLIER_RESET_SKIP_AGENTCORE" in body
    skip = body[body.index("PELLIER_RESET_SKIP_AGENTCORE"):]
    assert "exit 0" in skip[:900]


def test_the_reset_parses_a_dotenv_rather_than_sourcing_it() -> None:
    """A dotenv file is not a shell script.

    A password containing "(" makes `source` fail with a syntax error, and a value
    containing "$" would be expanded.
    """
    body = _reset_body()
    assert "_load_dotenv" in body
    assert 'export "$key=$value"' in body


# ---------------------------------------------------------------------------
# Memory runtime cleanup
# ---------------------------------------------------------------------------


def test_the_memory_cleanup_preserves_the_seeded_persona_actors() -> None:
    """`seed-sample-preferences.sh` posts their bundles, so a fresh box has them too."""
    body = MEMORY_RESET.read_text()
    assert 'PRESERVE_ACTORS = frozenset({"CUST-MARCO", "CUST-ANNA", "CUST-THEO"})' in body


def test_the_memory_cleanup_never_touches_the_resource() -> None:
    body = MEMORY_RESET.read_text()
    for control_plane in ("delete_memory(", "create_memory(", "update_memory("):
        assert control_plane not in body, control_plane


def test_the_memory_cleanup_is_dry_run_by_default() -> None:
    body = MEMORY_RESET.read_text()
    assert '"--apply", action="store_true"' in body
    assert "if not apply:" in body


def test_the_memory_cleanup_deletes_per_item_not_in_bulk() -> None:
    """Narrowest operations the SDK exposes, so a mistake costs one row."""
    body = MEMORY_RESET.read_text()
    assert "delete_event(" in body
    assert "delete_memory_record(" in body


def test_the_memory_cleanup_covers_long_term_not_only_events() -> None:
    """USER_PREFERENCE is ACTOR-scoped, so a new session id isolates nothing.

    The operator subject held 4 extracted preference records derived from engineering
    Concierge runs. Clearing short-term events alone would have left them.
    """
    body = MEMORY_RESET.read_text()
    assert "/pellier/preferences/{actor}/" in body
    assert "actor-scoped" in body.lower() or "ACTOR-scoped" in body
