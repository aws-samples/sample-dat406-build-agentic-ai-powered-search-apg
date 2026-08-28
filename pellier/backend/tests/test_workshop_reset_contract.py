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
    # The code form, not the first textual match: the header documents this variable in
    # prose, and anchoring there would read the docstring instead of the branch.
    guard = '"${PELLIER_RESET_SKIP_AGENTCORE:-0}" == "1"'
    assert guard in body
    skip = body[body.index(guard):]
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


# ---------------------------------------------------------------------------
# The service-state contract.
#
# Audit finding P2-06: the reset had no defined service state, so it TRUNCATEd the
# evidence tables while the application was free to serve a turn. Postgres will not
# corrupt anything, but "not corrupt" is not the property a workshop needs. The
# dangerous interleavings are specific:
#
#   * a `write_operations` claim cleared after its domain write committed, so a replay
#     applies the effect twice;
#   * an `approvals` row cleared after the execution it authorized, so a receipt points
#     at a review that no longer exists;
#   * a conversation or Memory event written just after the truncate, so the clean
#     baseline opens with someone else's residue in it.
#
# One box, one systemd unit, one database. The fix is to own the service state, not to
# build a lock.
# ---------------------------------------------------------------------------


def test_the_reset_quiesces_before_it_truncates() -> None:
    """Order is the whole property. Quiescing after the truncate proves nothing."""
    body = _reset_body()
    for call in ("_quiesce_services\n", "_assert_no_active_execution\n"):
        assert call in body, f"the reset no longer calls {call.strip()}"
    quiesce = body.index("_quiesce_services\n")
    assert "_assert_no_active_execution\n" in body[quiesce:], (
        "_assert_no_active_execution does not run after _quiesce_services"
    )
    assert_no_active = body.index("_assert_no_active_execution\n", quiesce)
    truncate = body.index("TRUNCATE TABLE")
    assert quiesce < assert_no_active < truncate, (
        "the reset must stop the application and prove nothing is executing BEFORE it "
        "truncates"
    )


def test_the_reset_restarts_the_service_even_when_a_step_fails() -> None:
    """`set -e` plus a stopped service is a workshop box with no application.

    A failing psql must not be the reason a participant's backend is down with no
    message saying so, which is why resume is on a trap rather than at the end.
    """
    body = _reset_body()
    assert "trap _resume_services EXIT" in body
    assert "_resume_services() {" in body
    # The trap has to be armed before anything can fail after the stop.
    assert body.index("trap _resume_services EXIT") < body.index("_quiesce_services\n")


def test_the_reset_refuses_a_live_backend_it_cannot_stop() -> None:
    """Refusing is the safe default; racing must be an explicit opt-in."""
    body = _reset_body()
    assert "PELLIER_RESET_ALLOW_LIVE" in body
    assert "Reset refuses to race live writes." in body or "refuses" in body
    # The refusal must exit, not warn and continue.
    section = body[body.index("_quiesce_services() {"): body.index("_assert_no_active_execution() {")]
    assert "exit 1" in section, "the quiesce path warns instead of refusing"


def test_the_active_execution_check_uses_a_deterministic_marker() -> None:
    """An unfinished claim is `completed_at IS NULL`, not a timestamp heuristic.

    `write_operations` is the idempotency ledger: one row per key, `completed_at` set
    when the effect landed. That is an exact in-flight marker, so the check does not
    have to guess from ages or counts.
    """
    body = _reset_body()
    assert "pg_stat_activity" in body
    assert "pg_backend_pid()" in body, (
        "the active-session count must exclude the reset's own session or it always "
        "finds itself"
    )
    assert "FROM pellier.write_operations WHERE completed_at IS NULL" in body


def test_the_reset_cleans_agentcore_memory_runtime_state() -> None:
    """Aurora is not the whole workshop.

    Preference records are actor-scoped, so a new session id does not isolate them. This
    used to be a separate command an operator had to remember; it is a lifecycle step
    now, skippable only for a box with no AWS credentials.
    """
    body = _reset_body()
    assert "reset_memory_runtime.py" in body
    assert "--apply" in body
    assert "PELLIER_RESET_SKIP_MEMORY" in body
    # Before the control-plane leg, so the rows-only path gets it too. Compared against
    # the control-plane BRANCH, not the first mention of its name in the header prose.
    assert body.index("reset_memory_runtime.py") < body.index(
        '"${PELLIER_RESET_SKIP_AGENTCORE:-0}" == "1"'
    )


def test_the_reset_verifies_the_baseline_it_claims_to_have_restored() -> None:
    """Asserting each step is not the same claim as asserting the result."""
    body = _reset_body()
    assert "_verify_baseline() {" in body
    cleared = _truncate_list()
    verified = set(
        re.findall(r"SELECT count\(\*\) FROM pellier\.\$\{table\}", body)
    )
    assert verified, "the baseline check no longer counts anything"
    section = body[body.index("_verify_baseline() {"):]
    for table in ("approvals", "execution_receipts", "operator_episodes",
                  "write_operations", "conversations", "observatory_spans"):
        assert table in section, f"{table} is truncated but never verified empty"
        assert table in cleared, f"{table} is verified empty but never truncated"
    # The forensic incident is the one intentional row; zero is as wrong as two.
    for table in ("returns", "tool_audit", "governed_receipts"):
        assert table in section


def test_the_reset_still_truncates_rather_than_deletes() -> None:
    """The trigger-safe semantics must survive every change above.

    A DELETE here fires `record_inventory_movement` and the receipt-immutability
    trigger, writing fresh history while trying to clear history.
    """
    body = _reset_body()
    assert "TRUNCATE TABLE" in body
    assert "RESTART IDENTITY" in body
    assert not re.search(r"\bDELETE FROM pellier\.", body), (
        "a DELETE reappeared in the reset; that fires the row-level triggers TRUNCATE "
        "deliberately bypasses"
    )


# ---------------------------------------------------------------------------
# Which interpreter, and how the shell decides.
#
# A workshop box has NO `pellier/backend/.venv`. `bootstrap-environment.sh` installs
# `requirements.lock` into the participant's `~/.local` with `pip install --user`, and the
# systemd unit runs the ambient interpreter. So `python3` there IS the validated
# interpreter, carrying the same pinned botocore. On a developer box the opposite holds:
# the venv is validated and ambient `python3` is whatever the machine has (measured:
# botocore 1.43.28, which cannot see `UpdatePolicy.enforcementMode`).
#
# Both entry points must therefore RESOLVE rather than assume, and the resolution has one
# trap worth a test of its own: `[[ -x name ]]` is a file test relative to the working
# directory and performs no PATH lookup, so testing the bare string "python3" is always
# false. A step guarded that way is silently skipped on exactly the boxes that need it.
# ---------------------------------------------------------------------------

DEPLOY_ALL = pathlib.Path("../../scripts/deploy/deploy_all.sh")


def test_the_reset_falls_back_to_python3_when_there_is_no_venv() -> None:
    body = _reset_body()
    assert 'PYTHON="python3"' in body, (
        "the reset assumes a venv. A workshop box has none, so its first step would fail "
        "with 'No such file or directory' before touching the database."
    )
    # Resolution must happen before the first use, or the fallback is decoration.
    assert body.index('PYTHON="python3"') < body.index('"$PYTHON" "$REPO/scripts/')


def test_both_entry_points_resolve_the_interpreter_the_same_way() -> None:
    """`deploy_all.sh` already had this right; the reset must not disagree with it."""
    for path in (RESET, DEPLOY_ALL):
        body = path.read_text()
        # Quoted or not: `deploy_all.sh` writes `PYTHON=python3`, the reset quotes it.
        # The property is the fallback, not the quoting style.
        assert re.search(r'PYTHON="?python3"?', body), (
            f"{path.name} does not fall back to python3, so it assumes a venv a "
            "workshop box does not have"
        )


def test_no_step_is_guarded_by_a_dash_x_test_on_a_bare_command_name() -> None:
    """The trap that silently disabled the Memory leg.

    After the fallback, `$PYTHON` may be the bare string "python3". `[[ ! -x "$PYTHON" ]]`
    is then always true, so anything guarded by it never runs. `command -v` is the test
    that answers the question actually being asked.
    """
    body = _reset_body()
    assert "command -v \"$PYTHON\"" in body, (
        "the reset must check the interpreter with `command -v`, which honours PATH"
    )
    guarded = re.findall(r"^\s*(?:el)?if \[\[ ! -x \"\$PYTHON\" \]\]", body, re.MULTILINE)
    # One occurrence is legitimate: the venv-path probe that CHOOSES the fallback. Any
    # further one is a step that will be skipped whenever the fallback is in effect.
    assert len(guarded) <= 1, (
        f"{len(guarded)} steps are gated on `[[ ! -x $PYTHON ]]`; after the fallback that "
        "test is always true and the step never runs"
    )


def test_every_psql_invocation_ignores_a_developer_psqlrc() -> None:
    """`-X`, because a ~/.psqlrc broke the in-flight check in a way no box would show.

    A developer's psqlrc printed "Null display is (null). Timing is on." into the scalar
    reads, so a count of 0 parsed as noise and the reset refused a database with nothing
    running. A workshop box has no psqlrc, which is exactly why this only appears
    off-box, and off-box is where the reset gets tested.
    """
    body = _reset_body()
    invocations = len(re.findall(r"^\s*PGPASSWORD=.* psql \\\\?$", body, re.MULTILINE))
    hardened = body.count("-X -v ON_ERROR_STOP=1")
    assert hardened >= 3, f"only {hardened} psql invocations pass -X"
    assert "-v ON_ERROR_STOP=1" in body
    assert not re.search(r"psql \\\n(?!.*-X)", body) or hardened >= 3
