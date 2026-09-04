"""One run id for one participant's workshop, and where it comes from.

Every evidence table a lab leaves rows in (``tool_audit``, ``retrieval_receipts``,
``governed_turn_receipts``, ``execution_receipts``, ``write_operations``,
``governed_receipts``, ``policy_decisions``) carries a ``run_id`` column whose
DEFAULT is ``current_setting('pellier.run_id', true)`` (migration 049). No writer
names the column; the database stamps it from the session setting that
``services.database._configure_connection`` binds on every pooled connection.
This module is the one place that decides what that setting is.

Resolution order, deliberately simple:

1. ``PELLIER_RUN_ID`` in the environment (the systemd unit reads it from
   ``/etc/pellier/run.env``, and a shell can override it for a one-off tool).
2. ``~/.pellier/run_id``, the file ``scripts/workshop-start.sh`` mints before
   Lab 1. The service runs as the participant's user, so its ``~`` is theirs.

Anything else means no run is in progress, and evidence rows carry NULL. That is
a true statement about the box, not a failure: the receipt and the doctor say
"no run id" rather than inventing one.

The shell entry points call the CLI below so the format lives here once::

    python3 pellier/backend/services/workshop_run.py current
    python3 pellier/backend/services/workshop_run.py mint --persona marco
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Optional, Sequence

RUN_ID_ENV = "PELLIER_RUN_ID"
RUN_ID_FILE = Path.home() / ".pellier" / "run_id"
RUN_PERSONA_FILE = Path.home() / ".pellier" / "run_persona"

# The same shape ``pellier.workshop_runs.run_id`` CHECKs. Kept in lockstep so a
# value the database would reject never reaches ``set_config``.
RUN_ID_PATTERN = re.compile(r"^run-[0-9a-f]{12}$")
PERSONA_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,31}$")


def is_valid_run_id(value: object) -> bool:
    """Return True when ``value`` is a string of the ``run-<12 hex>`` shape."""
    return isinstance(value, str) and RUN_ID_PATTERN.fullmatch(value) is not None


def current_run_id() -> Optional[str]:
    """Return the run id in effect, or None when no workshop run has started.

    The environment wins over the file so an operator can pin a tool invocation
    to a specific run without touching the participant's minted file.
    """
    from_env = os.environ.get(RUN_ID_ENV, "").strip()
    if from_env:
        return from_env
    return _read_token(RUN_ID_FILE)


def current_run_persona() -> Optional[str]:
    """Return the persona recorded when the current run was minted, if any."""
    return _read_token(RUN_PERSONA_FILE)


def mint_run_id(persona: Optional[str] = None) -> str:
    """Mint a fresh run id, write it to ``RUN_ID_FILE`` (0600), and return it.

    Args:
        persona: Optional workshop persona (``marco``, ``anna``, ``theo``,
            ``jessica``) recorded beside the id so later tooling can name the
            run without a database round trip. Validated before any write.

    Returns:
        The new id, matching :data:`RUN_ID_PATTERN`.

    Raises:
        ValueError: If ``persona`` is given and is not a short lowercase slug.
    """
    if persona is not None and PERSONA_PATTERN.fullmatch(persona) is None:
        raise ValueError(
            f"persona must match {PERSONA_PATTERN.pattern}, got {persona!r}"
        )
    run_id = "run-" + uuid.uuid4().hex[:12]
    _write_private(RUN_ID_FILE, run_id)
    if persona is not None:
        _write_private(RUN_PERSONA_FILE, persona)
    return run_id


def _read_token(path: Path) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def _write_private(path: Path, value: str) -> None:
    """Write ``value`` as the whole file, readable and writable by the owner only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, (value + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI used by ``scripts/workshop-start.sh``; prints the id on stdout."""
    parser = argparse.ArgumentParser(description="Read or mint the workshop run id.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("current", help="print the run id in effect; exit 1 if none")
    mint = commands.add_parser("mint", help="mint a new run id and write ~/.pellier/run_id")
    mint.add_argument("--persona", default=None, help="persona to record beside the id")
    args = parser.parse_args(argv)

    if args.command == "current":
        run_id = current_run_id()
        if run_id is None:
            return 1
        print(run_id)
        return 0

    try:
        print(mint_run_id(persona=args.persona))
    except ValueError as exc:
        print(f"workshop_run: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
