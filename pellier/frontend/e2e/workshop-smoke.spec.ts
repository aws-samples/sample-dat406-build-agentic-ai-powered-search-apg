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
 *   5. Real query produces streaming tokens and a reply that is not a
 *      stub non-answer.
 *   6. ?reset=1 clears persisted state.
 *
 * Runs automatically on Ubuntu and as a manual macOS facilitator gate.
 *
 * NOTE: does not require Cognito or AWS creds. The real-query step
 * asserts a non-empty reply that is not a workshop stub non-answer, so
 * it exercises triage → orchestrator → specialist without depending on
 * external model availability.
 *
 * That is deliberately weaker than a room-readiness check: a reply can
 * be non-empty and still be degraded. Set E2E_REQUIRE_LIVE_MODEL=1 when
 * rehearsing against a real Bedrock-backed environment to additionally
 * require grounded product evidence, so a model outage fails the
 * rehearsal instead of passing it on a non-empty apology. CI leaves it
 * unset because it runs with PELLIER_SMOKE_MODE, which returns canned
 * text and no products by design.
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
  await page.keyboard.press('Escape');

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

  test('first visit offers a concise, session-gated tour', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearBrowserState(page);
    await page.reload({ waitUntil: 'networkidle' });

    const tour = page.getByRole('dialog');
    await expect(tour).toBeVisible();
    await expect(
      tour.getByRole('heading', { name: 'Begin with the edit.' }),
    ).toBeVisible();
    await expect(tour.getByRole('button', { name: /^Show / })).toHaveCount(4);

    await tour.getByRole('button', { name: 'Skip welcome tour' }).click();
    await expect(tour).toHaveCount(0);
    await page.reload({ waitUntil: 'networkidle' });
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });

  test('Pellier Labs has a direct storefront entry and an explicit return', async ({
    page,
  }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.keyboard.press('Escape');

    await page.getByTestId('pellier-labs-link').click();
    await expect(page).toHaveURL(/\/pellier-labs(?:\/|$)/);
    await expect(page.getByTestId('agent-trace-topbar')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Pellier Labs' })).toBeVisible();
    await expect(
      page.getByRole('button', {
        name: /^Inspect:/,
      }),
    ).toHaveCount(5);
    await expect(
      page.getByRole('heading', { name: 'Shopper turns' }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Evidence ledger' }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Grounded answer', exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole('link', { name: 'Live Workbench' }),
    ).toBeVisible();
    await expect(
      page.getByRole('link', { name: 'Optional Deep Dives' }),
    ).toBeVisible();
    await expect(page.getByText(/concierge online/i)).toHaveCount(0);

    await page.keyboard.press('Control+K');
    await expect(page.getByTestId('chat-drawer')).toHaveCount(0);
    await expect(page.getByTestId('concierge-modal')).toHaveCount(0);
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
      const hostname = new URL(url).hostname.toLowerCase();
      if (hostname === 'fonts.gstatic.com' || hostname === 'fonts.googleapis.com') {
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
    const heroPills = page.getByTestId('pellier-hero-pills');
    await expect(heroPills).toBeVisible();
    await expect(heroPills).toContainText('Browse linen for a Goa carry-on');
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
    await expect(body).toContainText(/Pellier concierge/i, { timeout: 3000 });
  });

  test('real query: streaming tokens land, reply is not a non-answer', async ({
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
      // A stub non-answer is a degraded reply, not a passing one.
      expect(text).not.toMatch(/outside what I can answer right now/i);
    }).toPass({ timeout: 45_000 });

    if (process.env.E2E_REQUIRE_LIVE_MODEL === '1') {
      // Room readiness: the turn must return grounded catalog evidence, so
      // a model outage fails the rehearsal rather than passing it.
      await expect(
        page.locator('[data-testid^="product-card-"]').first(),
      ).toBeVisible({ timeout: 45_000 });
    }
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
