"""Regression coverage for the optional Cognito browser workflow."""

from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/e2e.yml"
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
COGNITO_E2E = FRONTEND / "e2e" / "cognito"


def test_optional_cognito_job_wires_the_dev_pool_into_both_app_surfaces() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    expected_fragments = (
        "E2E_COGNITO_DOMAIN: ${{ secrets.E2E_COGNITO_DOMAIN }}",
        "COGNITO_POOL_ID: ${{ secrets.E2E_COGNITO_POOL_ID }}",
        "COGNITO_CLIENT_ID: ${{ secrets.E2E_COGNITO_CLIENT_ID }}",
        "COGNITO_REGION: ${{ secrets.E2E_AWS_REGION }}",
        "COGNITO_DOMAIN: ${{ secrets.E2E_COGNITO_DOMAIN }}",
        "APP_BASE_URL: http://localhost:5173",
        "VITE_COGNITO_DOMAIN: ${{ secrets.E2E_COGNITO_DOMAIN }}",
        "VITE_COGNITO_CLIENT_ID: ${{ secrets.E2E_COGNITO_CLIENT_ID }}",
        "E2E_COGNITO_POOL_ID E2E_COGNITO_CLIENT_ID E2E_COGNITO_DOMAIN "
        "E2E_TEST_USER_EMAIL E2E_TEST_USER_PASSWORD E2E_AWS_REGION "
        "E2E_AWS_ROLE_ARN",
    )

    for fragment in expected_fragments:
        assert fragment in source


def test_optional_cognito_job_runs_the_frontend_cognito_suite() -> None:
    """The auth specs must live under the frontend Playwright package.

    Passing root-level paths to the frontend runner fails in two ways: the
    smoke config excludes them, and Node resolves their ``@playwright/test``
    import relative to the root test directory instead of the frontend's
    dependency tree. Keep the runnable auth suite in the package that owns its
    runner and dependencies.
    """
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "npx playwright test e2e/cognito" in source
    assert "tests/e2e/auth-happy-path.spec.ts" not in source
    assert "tests/e2e/auth-refresh.spec.ts" not in source
    assert "tests/e2e/auth-refresh-fail.spec.ts" not in source
    assert "tests/e2e/anon-to-auth.spec.ts" not in source


def test_frontend_package_contains_each_cognito_auth_spec() -> None:
    expected = {
        "auth-happy-path.spec.ts",
        "auth-refresh.spec.ts",
        "auth-refresh-fail.spec.ts",
        "anon-to-auth.spec.ts",
    }
    assert {path.name for path in COGNITO_E2E.glob("*.spec.ts")} == expected
