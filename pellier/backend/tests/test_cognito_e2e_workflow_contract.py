"""Regression coverage for the optional Cognito browser workflow."""

from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/e2e.yml"


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
