#!/usr/bin/env python3
"""Seed `pellier.principal_customers` from the Cognito user pool.

Without this, Row-Level Security denies every signed-in shopper.

Migration 016 keys its policies on a *mapping*: the database resolves a
verified Cognito subject to the customer scope that subject may touch. An
empty mapping table is therefore not a neutral starting state — it denies
everyone, including a participant who has just signed in as `marco` and asked
about their own order. That reads as a broken application, not as governance,
and the distinction is the whole point of the exercise.

Why the mapping cannot be a static SQL seed
-------------------------------------------

`principal_sub` is the Cognito `sub`, a UUID that Cognito assigns when the
user is created. It differs in every deployment, so no migration can contain
it. This script resolves username -> sub against the live pool and upserts the
rows. It is idempotent and safe to re-run.

One source of truth
-------------------

The username -> customer half comes from
`services.turn_identity.USERNAME_TO_CUSTOMER_ID`, the same table the
application uses to scope a turn. If the two ever disagreed the failure would
be maddening: the application would believe the turn is scoped to a customer
while the database refuses every row, with no error to explain why. Importing
the mapping rather than restating it makes that divergence impossible.

Who is deliberately left unmapped
---------------------------------

Guests and simulated personas. An anonymous turn has no verified subject, so
it maps to nothing and sees nothing. That is the intended denial, and
`turn_identity` already reports it as `persona_is_simulated` rather than as an
identity.

Usage::

    python3 scripts/seed_principal_mappings.py            # seed and report
    python3 scripts/seed_principal_mappings.py --check    # report only
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
from typing import Dict, List, Optional, Tuple

_BACKEND = pathlib.Path(__file__).resolve().parents[1] / "pellier" / "backend"

# Exit codes. `--check` uses 1 for "mapping incomplete" so a provisioning
# script can gate on it.
_EXIT_OK = 0
_EXIT_INCOMPLETE = 1
_EXIT_UNCONFIGURED = 2


def _load_env(path: pathlib.Path) -> Dict[str, str]:
    """Parse a dotenv file without shell interpolation.

    Sourcing `.env` through a shell word-splits any password containing shell
    metacharacters and can echo it into a log. Parsing it here keeps
    credentials out of any command line.
    """
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _username_to_customer() -> Dict[str, str]:
    """Return the application's own username -> customer mapping."""
    sys.path.insert(0, str(_BACKEND))
    from services.turn_identity import USERNAME_TO_CUSTOMER_ID

    return dict(USERNAME_TO_CUSTOMER_ID)


def resolve_subs(
    *, region: str, pool_id: str, usernames: List[str]
) -> Tuple[Dict[str, str], List[str]]:
    """Resolve each username to its Cognito subject.

    Returns:
        A ``(resolved, missing)`` pair. A username absent from the pool is
        reported rather than raising: a deployment may legitimately seed a
        subset of the personas, and the caller decides whether that matters.
    """
    import boto3

    cognito = boto3.client("cognito-idp", region_name=region)
    resolved: Dict[str, str] = {}
    missing: List[str] = []

    for username in usernames:
        try:
            user = cognito.admin_get_user(UserPoolId=pool_id, Username=username)
        except cognito.exceptions.UserNotFoundException:
            missing.append(username)
            continue
        sub = next(
            (
                attribute["Value"]
                for attribute in user.get("UserAttributes", [])
                if attribute.get("Name") == "sub"
            ),
            None,
        )
        if not sub:
            missing.append(username)
            continue
        resolved[username] = sub

    return resolved, missing


def _psql(cfg: Dict[str, str], sql: str) -> Tuple[int, str, str]:
    """Run one statement through psql, passing the password via the env only."""
    import subprocess

    child = os.environ.copy()
    child["PGPASSWORD"] = cfg["DB_PASSWORD"]
    result = subprocess.run(
        [
            "psql",
            "-h", cfg["DB_HOST"],
            "-p", cfg.get("DB_PORT", "5432"),
            "-U", cfg["DB_USER"],
            "-d", cfg["DB_NAME"],
            "-X",  # ignore ~/.psqlrc; its banners would pollute parsed output
            "-q",
            "-v", "ON_ERROR_STOP=1",
            "-t", "-A",
            "-c", sql,
        ],
        env=child,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def upsert_sql(mappings: Dict[str, Tuple[str, str]]) -> str:
    """Build the idempotent upsert for username -> (sub, customer_id).

    Also deletes stale rows for the same customer: a pool rebuild issues new
    subjects, and leaving the old ones mapped would keep authorizing subjects
    that no longer exist.
    """
    if not mappings:
        return ""
    values = ", ".join(
        f"('{sub}', '{customer}')" for sub, customer in mappings.values()
    )
    customers = ", ".join(f"'{customer}'" for _sub, customer in mappings.values())
    subs = ", ".join(f"'{sub}'" for sub, _customer in mappings.values())
    return (
        "BEGIN;\n"
        f"DELETE FROM pellier.principal_customers\n"
        f" WHERE customer_id IN ({customers}) AND principal_sub NOT IN ({subs});\n"
        "INSERT INTO pellier.principal_customers (principal_sub, customer_id)\n"
        f" VALUES {values}\n"
        " ON CONFLICT (principal_sub, customer_id) DO NOTHING;\n"
        "COMMIT;"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report the current mapping without writing.",
    )
    parser.add_argument(
        "--env",
        default=str(_BACKEND / ".env"),
        help="Path to the backend .env (default: pellier/backend/.env).",
    )
    args = parser.parse_args(argv)

    cfg = _load_env(pathlib.Path(args.env))
    cfg = {**cfg, **{k: v for k, v in os.environ.items() if k.startswith(("DB_", "COGNITO_", "AWS_"))}}

    pool_id = cfg.get("COGNITO_POOL_ID") or cfg.get("COGNITO_USER_POOL_ID") or ""
    region = cfg.get("COGNITO_REGION") or cfg.get("AWS_REGION") or "us-east-1"

    missing_db = [k for k in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not cfg.get(k)]
    if missing_db:
        print(f"Database not configured (missing {', '.join(missing_db)}); nothing to do.")
        return _EXIT_UNCONFIGURED

    code, out, err = _psql(
        cfg,
        "SELECT customer_id || '|' || principal_sub FROM pellier.principal_customers"
        " ORDER BY customer_id",
    )
    if code != 0:
        print(f"could not read pellier.principal_customers: {err}")
        return _EXIT_UNCONFIGURED

    seeded: Dict[str, str] = {}
    for line in out.splitlines():
        if "|" in line:
            customer, _, sub = line.strip().partition("|")
            seeded[customer] = sub

    print("Seeded mapping:")
    if seeded:
        for customer in sorted(seeded):
            print(f"  {customer:<12} <- {seeded[customer]}")
    else:
        print("  (empty — Row-Level Security denies every signed-in shopper)")

    if not pool_id:
        print(
            "\nCOGNITO_POOL_ID is not set, so subjects cannot be resolved.\n"
            "Run this after Cognito provisioning; until then RLS denies every\n"
            "authenticated read of orders and returns."
        )
        return _EXIT_UNCONFIGURED

    wanted = _username_to_customer()
    resolved, missing = resolve_subs(
        region=region, pool_id=pool_id, usernames=sorted(wanted)
    )

    print(f"\nResolved from pool {pool_id} ({region}):")
    for username in sorted(wanted):
        if username in resolved:
            print(f"  {username:<8} -> {wanted[username]:<12} sub={resolved[username]}")
        else:
            print(f"  {username:<8} -> {wanted[username]:<12} NOT IN POOL")

    mappings = {
        username: (resolved[username], wanted[username])
        for username in resolved
    }

    if args.check:
        # Completeness is a property of the TABLE, not of the pool. Comparing
        # resolvable subjects against the wanted set reported "complete"
        # against an empty table, which is the precise failure this script
        # exists to prevent: RLS denying every signed-in shopper while the
        # check says everything is fine.
        problems: List[str] = []
        for username, customer in sorted(wanted.items()):
            pool_sub = resolved.get(username)
            seeded_sub = seeded.get(customer)
            if seeded_sub is None:
                problems.append(f"{customer} has no seeded mapping")
            elif pool_sub and seeded_sub != pool_sub:
                problems.append(
                    f"{customer} maps to a stale subject "
                    f"(seeded {seeded_sub}, pool {pool_sub})"
                )
        if problems:
            print("\nMapping incomplete — RLS will deny the affected shoppers:")
            for problem in problems:
                print(f"  - {problem}")
            return _EXIT_INCOMPLETE
        print("\nMapping complete: every persona resolves to its current subject.")
        return _EXIT_OK

    if not mappings:
        print("\nNothing to seed.")
        return _EXIT_INCOMPLETE

    code, _out, err = _psql(cfg, upsert_sql(mappings))
    if code != 0:
        print(f"\nSeed failed: {err}")
        return _EXIT_INCOMPLETE

    print(f"\n✅ Seeded {len(mappings)} principal mapping(s).")
    if missing:
        print(
            f"⚠️  {', '.join(missing)} not in the pool, so those personas stay "
            "unmapped and RLS will deny them."
        )
    return _EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
