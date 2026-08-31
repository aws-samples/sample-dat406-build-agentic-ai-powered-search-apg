"""Shell entrypoints must parse dotenv values rather than execute them."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOTENV_HELPER = ROOT / "scripts" / "lib" / "dotenv.sh"


def test_dotenv_helper_keeps_shell_metacharacters_literal(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    expected = "one(two)$HOME`literal`"
    dotenv.write_text(
        f"DB_PASSWORD={expected}\nexport RECOVERY_VALUE='managed value'\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "bash",
            "-c",
            'set -euo pipefail; source "$1"; pellier_load_dotenv "$2"; printf "%s|%s" "$DB_PASSWORD" "$RECOVERY_VALUE"',
            "--",
            str(DOTENV_HELPER),
            str(dotenv),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == f"{expected}|managed value"


def test_managed_shell_entrypoints_use_the_shared_dotenv_parser() -> None:
    for relative in ("scripts/health-gate.sh", "scripts/deploy/deploy_all.sh"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "pellier_load_dotenv" in source
        assert 'source "$env_file"' not in source


def test_bootstrap_resolves_the_confidential_hosted_ui_secret_server_side() -> None:
    """A confidential Cognito client requires Basic auth for code exchange."""
    source = (ROOT / "scripts" / "bootstrap-labs.sh").read_text(encoding="utf-8")

    assert 'COGNITO_CLIENT_SECRET_ARN' in source
    assert 'aws secretsmanager get-secret-value' in source
    assert 'COGNITO_CLIENT_SECRET=${COGNITO_CLIENT_SECRET@Q}' in source
    assert 'value.get("client_secret", "")' in source
