import { expect, test } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'
const OPERATOR_TOKEN = process.env.PELLIER_OPERATOR_TOKEN ?? ''

test.describe('Operator client storefront handoff', () => {
  test.skip(
    !OPERATOR_TOKEN,
    'PELLIER_OPERATOR_TOKEN is required for the operator-gated client reads',
  )

  test.use({
    extraHTTPHeaders: OPERATOR_TOKEN
      ? { Authorization: `Bearer ${OPERATOR_TOKEN}` }
      : {},
  })

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('pellier-storefront-spotlight-seen', 'true')
    })
  })

  test('the live client book stays balanced across all three membership rungs', async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/operator`, { waitUntil: 'networkidle' })
    await expect(page.getByTestId('operator-book')).toBeVisible()

    for (const rung of ['registered', 'circle', 'maison']) {
      await expect(
        page
          .getByTestId(`operator-ladder-${rung}`)
          .locator('.operator-ladder-count'),
      ).toHaveText('5')
    }
  })

  test('Jessica stays a read-only client preview and exposes the evidence conflict', async ({
    page,
  }) => {
    await page.goto(
      `${BASE_URL}/operator/clients/CUST-JESSICA`,
      { waitUntil: 'networkidle' },
    )
    await expect(page.getByTestId('operator-record')).toBeVisible()
    const request = page.getByTestId('operator-service-request')
    await expect(request).toContainText(
      'Return received, refund amount disputed',
    )
    await expect(request).toContainText('0 authoritative rows')
    await expect(request).toContainText(
      'Reconcile the assertion before promising an outcome.',
    )

    await page.getByTestId('operator-storefront-handoff').click()
    await expect(page).toHaveURL(/\/\?clientPreview=CUST-JESSICA$/)

    const preview = page.getByTestId('operator-client-preview')
    await expect(preview).toBeVisible()
    await expect(preview).toContainText('Jessica Nakamura')
    await expect(preview).toContainText('Read-only')
    await expect(
      page.getByTestId('operator-client-preview-evidence-conflict'),
    ).toContainText('returns ledger contains 0 record')
    await expect(page.getByTestId('persona-pill')).toContainText('Sign in')

    await page.getByTestId('operator-client-preview-record').click()
    await expect(page).toHaveURL(/\/operator\/clients\/CUST-JESSICA$/)
    await expect(page.getByTestId('operator-record')).toBeVisible()
  })

  test('a client preview clears an unrelated shopper persona', async ({
    page,
  }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.getByTestId('persona-pill').click()
    await page.getByTestId('persona-option-marco').click()
    await expect(page.getByTestId('persona-pill')).toContainText('Marco')

    await page.goto(
      `${BASE_URL}/?clientPreview=CUST-JESSICA`,
      { waitUntil: 'networkidle' },
    )
    await expect(page.getByTestId('operator-client-preview')).toBeVisible()
    await expect(page.getByTestId('persona-pill')).toContainText('Sign in')
    await expect(page.getByTestId('persona-pill')).not.toContainText('Marco')
  })

  test('a hero handoff performs the canonical persona switch', async ({
    page,
  }) => {
    await page.goto(
      `${BASE_URL}/operator/clients/CUST-MARCO`,
      { waitUntil: 'networkidle' },
    )
    await expect(page.getByTestId('operator-record')).toBeVisible()

    await page.getByTestId('operator-storefront-handoff').click()
    await expect(page).toHaveURL(new URL('/', BASE_URL).toString())
    await expect(page.getByTestId('persona-pill')).toContainText('Marco')
    await expect(page.getByTestId('operator-client-preview')).toHaveCount(0)
  })
})
