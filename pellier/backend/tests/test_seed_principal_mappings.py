"""Tests for `scripts/seed_principal_mappings.py`.

The mapping this script writes is what makes Row-Level Security usable rather
than merely strict. Migration 016 resolves a verified Cognito subject to a
customer scope through `pellier.principal_customers`; an empty table denies
every signed-in shopper, which a participant reads as a broken application
rather than as governance.

Two properties are pinned because both were wrong in the first version:

  1. **Completeness is a property of the table, not the pool.** The first
     `--check` compared *resolvable* subjects against the wanted personas and
     printed "Mapping complete" against an empty table — the precise failure
     the script exists to prevent.
  2. **A pool rebuild must not leave a stale subject authorized.** Cognito
     issues new subjects, and an old row would keep granting access to a
     subject that no longer exists.

The username -> customer half is imported from `turn_identity`, never
restated, so the application and the database cannot disagree about scope.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_seeder():
    module_name = "seed_principal_mappings_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]

    script_path = (
        Path(__file__).resolve().parents[3] / "scripts" / "seed_principal_mappings.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


# ---------------------------------------------------------------------------
# One source of truth for scope
# ---------------------------------------------------------------------------


def test_personas_come_from_the_application_mapping():
    """Restating the mapping would let the app and the database diverge.

    The app would believe a turn is scoped to a customer while the database
    refuses every row, with no error explaining why.
    """
    seeder = _load_seeder()
    from services.turn_identity import USERNAME_TO_CUSTOMER_ID

    assert seeder._username_to_customer() == USERNAME_TO_CUSTOMER_ID
    # A copy, so a caller cannot mutate the application's table.
    seeder._username_to_customer()["marco"] = "CUST-INTRUDER"
    assert USERNAME_TO_CUSTOMER_ID["marco"] == "CUST-MARCO"


def test_every_named_persona_is_covered():
    """The obvious question: does each signed-in user get a mapping?"""
    seeder = _load_seeder()

    wanted = seeder._username_to_customer()

    assert set(wanted) == {"marco", "anna", "theo"}
    assert set(wanted.values()) == {"CUST-MARCO", "CUST-ANNA", "CUST-THEO"}


# ---------------------------------------------------------------------------
# Upsert shape
# ---------------------------------------------------------------------------


def test_upsert_is_idempotent():
    seeder = _load_seeder()

    sql = seeder.upsert_sql({"marco": ("sub-1", "CUST-MARCO")})

    assert "ON CONFLICT (principal_sub, customer_id) DO NOTHING" in sql
    assert sql.startswith("BEGIN;") and sql.rstrip().endswith("COMMIT;")


def test_upsert_removes_stale_subjects_for_the_same_customer():
    """A rebuilt pool issues new subjects; the old row must stop authorizing."""
    seeder = _load_seeder()

    sql = seeder.upsert_sql({"marco": ("sub-new", "CUST-MARCO")})

    assert "DELETE FROM pellier.principal_customers" in sql
    assert "customer_id IN ('CUST-MARCO')" in sql
    assert "principal_sub NOT IN ('sub-new')" in sql


def test_upsert_of_nothing_is_empty_not_a_delete_everything():
    """An empty resolution must never emit a bare DELETE."""
    seeder = _load_seeder()

    assert seeder.upsert_sql({}) == ""


def test_upsert_covers_every_resolved_persona():
    seeder = _load_seeder()

    sql = seeder.upsert_sql(
        {
            "marco": ("sub-m", "CUST-MARCO"),
            "anna": ("sub-a", "CUST-ANNA"),
            "theo": ("sub-t", "CUST-THEO"),
        }
    )

    for sub, customer in (("sub-m", "CUST-MARCO"), ("sub-a", "CUST-ANNA"), ("sub-t", "CUST-THEO")):
        assert f"('{sub}', '{customer}')" in sql


# ---------------------------------------------------------------------------
# Subject resolution
# ---------------------------------------------------------------------------


class _FakeCognitoExceptions:
    class UserNotFoundException(Exception):
        pass


class _FakeCognito:
    def __init__(self, users):
        self._users = users
        self.exceptions = _FakeCognitoExceptions()

    def admin_get_user(self, UserPoolId, Username):  # noqa: N803 - boto3 casing
        if Username not in self._users:
            raise self.exceptions.UserNotFoundException(Username)
        return {
            "Username": Username,
            "UserAttributes": [
                {"Name": "email", "Value": f"{Username}@example.com"},
                {"Name": "sub", "Value": self._users[Username]},
            ],
        }


def test_resolves_subject_from_user_attributes(monkeypatch):
    seeder = _load_seeder()
    fake = _FakeCognito({"marco": "sub-m", "anna": "sub-a"})
    monkeypatch.setattr("boto3.client", lambda *_a, **_kw: fake)

    resolved, missing = seeder.resolve_subs(
        region="us-east-1", pool_id="pool", usernames=["marco", "anna", "theo"]
    )

    assert resolved == {"marco": "sub-m", "anna": "sub-a"}
    assert missing == ["theo"]


def test_a_user_absent_from_the_pool_is_reported_not_raised(monkeypatch):
    """A deployment may seed a subset; the caller decides if that matters."""
    seeder = _load_seeder()
    monkeypatch.setattr("boto3.client", lambda *_a, **_kw: _FakeCognito({}))

    resolved, missing = seeder.resolve_subs(
        region="us-east-1", pool_id="pool", usernames=["marco"]
    )

    assert resolved == {}
    assert missing == ["marco"]


def test_a_user_without_a_sub_attribute_is_treated_as_missing(monkeypatch):
    """No subject means nothing to key a policy on."""
    seeder = _load_seeder()

    class _NoSub(_FakeCognito):
        def admin_get_user(self, UserPoolId, Username):  # noqa: N803
            return {"Username": Username, "UserAttributes": [{"Name": "email", "Value": "x"}]}

    monkeypatch.setattr("boto3.client", lambda *_a, **_kw: _NoSub({"marco": "x"}))

    resolved, missing = seeder.resolve_subs(
        region="us-east-1", pool_id="pool", usernames=["marco"]
    )

    assert resolved == {}
    assert missing == ["marco"]


# ---------------------------------------------------------------------------
# Credential handling
# ---------------------------------------------------------------------------


def test_env_is_parsed_not_sourced(tmp_path):
    """A password with shell metacharacters must survive intact.

    Sourcing `.env` through a shell word-splits such a value and can echo a
    fragment into a log, which is how a live credential reached a session
    transcript once.
    """
    seeder = _load_seeder()
    env_file = tmp_path / ".env"
    hostile = "~koVh*cCz|sX5$4x8.VRrVs]"
    env_file.write_text(
        "# comment\n"
        "DB_HOST=cluster.example.com\n"
        f'DB_PASSWORD="{hostile}"\n'
        "\n"
        "COGNITO_POOL_ID=us-east-1_ABC\n"
    )

    cfg = seeder._load_env(env_file)

    assert cfg["DB_PASSWORD"] == hostile
    assert cfg["DB_HOST"] == "cluster.example.com"
    assert cfg["COGNITO_POOL_ID"] == "us-east-1_ABC"
    assert "# comment" not in cfg


def test_missing_env_file_is_not_fatal(tmp_path):
    seeder = _load_seeder()

    assert seeder._load_env(tmp_path / "absent.env") == {}


def test_password_is_never_placed_on_a_command_line(monkeypatch):
    """psql must receive credentials through the environment only."""
    seeder = _load_seeder()
    captured = {}

    def _fake_run(args, env=None, capture_output=None, text=None):
        captured["args"] = args
        captured["env"] = env

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr("subprocess.run", _fake_run)

    secret = "s3cr3t-value"
    seeder._psql(
        {
            "DB_HOST": "h",
            "DB_NAME": "d",
            "DB_USER": "u",
            "DB_PASSWORD": secret,
        },
        "SELECT 1",
    )

    assert secret not in " ".join(captured["args"])
    assert captured["env"]["PGPASSWORD"] == secret
    # `-X` keeps a developer's .psqlrc banners out of parsed output.
    assert "-X" in captured["args"]
