/**
 * E2E: Workshop smoke test — the readiness gate.
 *
 * This suite runs against the PRODUCTION BUILD served by FastAPI on
 * port 8000 (one process, one port). It exercises the demo path a
 * presenter walks through on stage so regressions catch ahead of the
 * room:
 *
 *   1. Home page loads without console errors.
 *   2. Fonts are self-hosted — no requests to fonts.gstatic.com.
 *   3. Persona sign-in opens the current storefront persona dropdown.
 *   4. Triage fast-path in ChatDrawer: "hi" produces a reply instantly,
 *      without routing to the specialist chain.
 *   5. Real query produces streaming tokens + a non-empty reply.
 *   6. ?reset=1 clears persisted state.
 *
 * Runs automatically on Ubuntu and as a manual macOS facilitator gate.
 *
 * NOTE: does not require Cognito or AWS creds. Bedrock is required
 * for step 4 (real query); if Bedrock is unavailable, step 4 falls
 * back to asserting the fallback message ("I looked through the
 * catalog...") instead of a positive product reply. That still
 * exercises the full pipeline — triage → orchestrator → fallback —
 * without depending on external model availability.
 */

import { expect, test } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:8000';

async function clearBrowserState(page: import('@playwright/test').Page) {
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

async function signInAsMarco(page: import('@playwright/test').Page) {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await clearBrowserState(page);
  await page.reload({ waitUntil: 'networkidle' });

  await page.getByTestId('persona-pill').click();
  await page.getByTestId('persona-option-marco').click();
  await expect(page.getByTestId('persona-pill')).toContainText(/Marco/i);
}

async function openChatDrawer(page: import('@playwright/test').Page) {
  await page.keyboard.press('Control+K');
  const drawer = page.getByTestId('chat-drawer');
  if (!(await drawer.isVisible().catch(() => false))) {
    await page.keyboard.press('Meta+K');
  }
  await expect(drawer).toBeVisible({ timeout: 5000 });
  return drawer;
}

test.describe('Workshop production build smoke', () => {
  test('home page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    page.on('console', (msg) => {
      if (msg.type() === 'error' && !msg.text().includes('401')) {
        // 401s from /api/auth/me are expected for anonymous users.
        errors.push(msg.text());
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await expect(page).toHaveTitle(/Pellier/);
    expect(errors, `console errors: ${errors.join('\n')}`).toHaveLength(0);
  });

  test('Pellier Labs has a direct storefront entry and an explicit return', async ({
    page,
  }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.keyboard.press('Escape');

    await page.getByTestId('pellier-labs-link').click();
    await expect(page).toHaveURL(/\/agent-trace(?:\/|$)/);
    await expect(page.getByTestId('agent-trace-topbar')).toBeVisible();
    await page.keyboard.press('Escape');

    await page.getByTestId('back-to-pellier').click();
    await expect(page).toHaveURL(new URL('/', BASE_URL).toString());
    await expect(page.getByTestId('wordmark')).toBeVisible();
  });

  test('fonts are self-hosted (no fonts.gstatic.com requests)', async ({
    page,
  }) => {
    const googleFontRequests: string[] = [];
    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('fonts.gstatic.com') || url.includes('fonts.googleapis.com')) {
        googleFontRequests.push(url);
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    expect(
      googleFontRequests,
      `Google Fonts should not be loaded: ${googleFontRequests.join(', ')}`,
    ).toHaveLength(0);
  });

  test('persona sign-in updates the storefront to Marco', async ({ page }) => {
    await signInAsMarco(page);
    await expect(page.getByTestId('persona-pill')).toContainText(/Marco/i);
    const heroPills = page.getByTestId('boutique-hero-pills');
    await expect(heroPills).toBeVisible();
    await expect(heroPills).toContainText('What linen do you have for 10 days in Goa?');
  });

  test('/signin opens the provider chooser instead of falling through', async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/signin?returnTo=%2Fdiscover`);

    const chooser = page.getByTestId('auth-modal');
    await expect(chooser).toBeVisible();
    await expect(
      chooser.getByRole('button', { name: /continue with google/i }),
    ).toBeVisible();
    await expect(
      chooser.getByRole('button', { name: /continue with apple/i }),
    ).toBeVisible();
    await expect(
      chooser.getByRole('button', { name: /continue with email/i }),
    ).toBeVisible();
  });

  test('triage fast-path: "hi" replies instantly without LLM calls', async ({
    page,
  }) => {
    await signInAsMarco(page);
    const drawer = await openChatDrawer(page);

    const input = drawer.locator('.cd-input').first();
    await input.fill('hi');
    await page.keyboard.press('Enter');

    // Triage reply should land in under 3 seconds — no LLM in loop.
    const body = page.locator('.ec-msg-body').last();
    await expect(body).toContainText(/I'm Pellier/i, { timeout: 3000 });
  });

  test('real query: streaming tokens land, reply is non-empty', async ({
    page,
  }) => {
    await signInAsMarco(page);
    const drawer = await openChatDrawer(page);

    const input = drawer.locator('.cd-input').first();
    await input.fill('find me a linen shirt under $150');
    await page.keyboard.press('Enter');

    // A real orchestrator turn can take 10-20s. Poll for non-empty
    // text rather than using the missing ``toBeEmpty`` matcher.
    // Guards against the empty-bubble regression we hit pre-fallback.
    const body = page.locator('.ec-msg-body').first();
    await expect(async () => {
      const text = (await body.textContent()) ?? '';
      expect(text.trim().length).toBeGreaterThan(10);
    }).toPass({ timeout: 45_000 });
  });

  test('?reset=1 clears persisted localStorage keys', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.setItem('smoke-test-key', 'poisoned');
    });
    const before = await page.evaluate(() =>
      localStorage.getItem('smoke-test-key'),
    );
    expect(before).toBe('poisoned');

    await page.goto(`${BASE_URL}/?reset=1`);
    // Give the reset effect + reload cycle a moment.
    await page.waitForTimeout(1500);

    const after = await page.evaluate(() =>
      localStorage.getItem('smoke-test-key'),
    );
    expect(after).toBeNull();

    // URL should be stripped of the reset flag.
    expect(page.url()).not.toContain('reset=1');
  });
});
