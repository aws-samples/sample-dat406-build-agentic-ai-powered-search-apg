"""One run id for one participant's workshop, resolved the same way everywhere.

``services.workshop_run`` is the single source of the id that migration 049
stamps onto every evidence row through the ``pellier.run_id`` session setting.
These tests pin the resolution order (environment first, then the minted file),
the file contract (one stripped token, owner-only permissions), and the CLI the
shell entry points call.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from services import workshop_run


@pytest.fixture()
def run_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the module at a scratch home and clear the environment override."""
    run_dir = tmp_path / ".pellier"
    monkeypatch.setattr(workshop_run, "RUN_ID_FILE", run_dir / "run_id")
    monkeypatch.setattr(workshop_run, "RUN_PERSONA_FILE", run_dir / "run_persona")
    monkeypatch.delenv(workshop_run.RUN_ID_ENV, raising=False)
    return run_dir


class TestCurrentRunId:
    def test_nothing_set_returns_none(self, run_files: Path) -> None:
        assert workshop_run.current_run_id() is None

    def test_environment_wins_over_the_file(
        self, run_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_files.mkdir()
        (run_files / "run_id").write_text("run-aaaaaaaaaaaa\n", encoding="utf-8")
        monkeypatch.setenv(workshop_run.RUN_ID_ENV, "run-bbbbbbbbbbbb")
        assert workshop_run.current_run_id() == "run-bbbbbbbbbbbb"

    def test_file_is_read_stripped(self, run_files: Path) -> None:
        run_files.mkdir()
        (run_files / "run_id").write_text("  run-cccccccccccc \n\n", encoding="utf-8")
        assert workshop_run.current_run_id() == "run-cccccccccccc"

    def test_blank_environment_falls_through_to_the_file(
        self, run_files: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_files.mkdir()
        (run_files / "run_id").write_text("run-dddddddddddd", encoding="utf-8")
        monkeypatch.setenv(workshop_run.RUN_ID_ENV, "   ")
        assert workshop_run.current_run_id() == "run-dddddddddddd"

    def test_empty_file_is_none(self, run_files: Path) -> None:
        run_files.mkdir()
        (run_files / "run_id").write_text("\n", encoding="utf-8")
        assert workshop_run.current_run_id() is None


class TestMintRunId:
    def test_mint_matches_the_database_check_and_writes_the_file(
        self, run_files: Path
    ) -> None:
        run_id = workshop_run.mint_run_id()
        assert workshop_run.RUN_ID_PATTERN.fullmatch(run_id), run_id
        assert (run_files / "run_id").read_text(encoding="utf-8").strip() == run_id
        assert workshop_run.current_run_id() == run_id

    def test_minted_file_is_owner_only(self, run_files: Path) -> None:
        workshop_run.mint_run_id()
        mode = stat.S_IMODE(os.stat(run_files / "run_id").st_mode)
        assert mode == 0o600, oct(mode)

    def test_two_mints_differ(self, run_files: Path) -> None:
        assert workshop_run.mint_run_id() != workshop_run.mint_run_id()

    def test_persona_is_recorded_beside_the_id(self, run_files: Path) -> None:
        workshop_run.mint_run_id(persona="marco")
        assert workshop_run.current_run_persona() == "marco"

    def test_no_persona_leaves_no_persona_file(self, run_files: Path) -> None:
        workshop_run.mint_run_id()
        assert workshop_run.current_run_persona() is None
        assert not (run_files / "run_persona").exists()

    @pytest.mark.parametrize("persona", ["Marco", "a b", "x" * 33, "../etc"])
    def test_malformed_persona_is_rejected_before_anything_is_written(
        self, run_files: Path, persona: str
    ) -> None:
        with pytest.raises(ValueError):
            workshop_run.mint_run_id(persona=persona)
        assert not (run_files / "run_id").exists()


class TestValidity:
    @pytest.mark.parametrize(
        "value",
        ["run-0123456789ab", "run-ffffffffffff"],
    )
    def test_accepts_the_database_shape(self, value: str) -> None:
        assert workshop_run.is_valid_run_id(value)

    @pytest.mark.parametrize(
        "value",
        [None, "", "run-", "run-0123456789", "run-0123456789abc", "RUN-0123456789ab",
         "run-0123456789ag", "run-0123456789ab; DROP TABLE x"],
    )
    def test_rejects_everything_else(self, value: object) -> None:
        assert not workshop_run.is_valid_run_id(value)


class TestCli:
    def test_current_prints_the_id(
        self, run_files: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        run_files.mkdir()
        (run_files / "run_id").write_text("run-eeeeeeeeeeee\n", encoding="utf-8")
        assert workshop_run.main(["current"]) == 0
        assert capsys.readouterr().out.strip() == "run-eeeeeeeeeeee"

    def test_current_without_a_run_exits_one(
        self, run_files: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert workshop_run.main(["current"]) == 1
        assert capsys.readouterr().out.strip() == ""

    def test_mint_prints_a_fresh_id_and_records_persona(
        self, run_files: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert workshop_run.main(["mint", "--persona", "anna"]) == 0
        printed = capsys.readouterr().out.strip()
        assert workshop_run.is_valid_run_id(printed)
        assert workshop_run.current_run_id() == printed
        assert workshop_run.current_run_persona() == "anna"

    def test_mint_with_a_bad_persona_exits_two(
        self, run_files: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert workshop_run.main(["mint", "--persona", "Not Valid"]) == 2
        assert "persona" in capsys.readouterr().err
