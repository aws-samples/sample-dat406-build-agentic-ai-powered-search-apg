/**
 * E2E: Persona modal portal regression gate.
 *
 * Guards against the containing-block bug where a parent with a
 * stacking/paint boundary traps the modal's ``position: fixed``
 * descendant. The fix was ``createPortal`` onto ``document.body``;
 * this test catches regressions if any future ancestor introduces
 * another containing-block creator (transform, filter, contain, etc.)
 * that re-traps the modal.
 *
 * The assertion is cheap: the modal backdrop's bounding rect must
 * equal the viewport's bounding rect. If that holds, the portal is
 * working and the CSS is being interpreted in the correct stacking
 * context.
 *
 * Runs against the production build on port 8000. PersonaModal now
 * lives on Agent Trace surfaces; the storefront header uses a direct
 * persona dropdown instead.
 */

import { expect, test } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:8000';

async function openLabsAsReturningVisitor(
  page: import('@playwright/test').Page,
) {
  // The portal check targets the persistent Labs control, not the
  // first-visit onboarding overlay that intentionally blocks the page.
  await page.addInitScript(() => {
    sessionStorage.setItem('pellier-labs-spotlight-seen', 'true');
  });
  await page.goto(`${BASE_URL}/agent-trace`);
  await page.waitForLoadState('networkidle');
}

test.describe('Persona modal - portal + viewport coverage', () => {
  test('backdrop fills the viewport when opened from the Agent Trace top bar', async ({
    page,
  }) => {
    await openLabsAsReturningVisitor(page);

    // The storefront uses the persona dropdown now. PersonaModal is the
    // Agent Trace persona switcher, where the portal regression still matters.
    await page.getByTestId('agent-trace-persona-switcher').click();

    const backdrop = page.getByTestId('persona-modal-backdrop');
    await expect(backdrop).toBeVisible();

    // Assert the backdrop's bounding rect matches the viewport. If
    // any ancestor creates a containing block, the rect will be
    // smaller — this is the bug we're guarding against.
    const viewport = page.viewportSize();
    expect(viewport).not.toBeNull();

    const box = await backdrop.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBe(0);
    expect(box!.y).toBe(0);
    expect(box!.width).toBe(viewport!.width);
    expect(box!.height).toBe(viewport!.height);

    // The backdrop's DOM parent must be <body> — the portal target.
    // If a future change rendered the modal inline, this would fail.
    const parentTag = await backdrop.evaluate(
      (el) => el.parentElement?.tagName ?? '',
    );
    expect(parentTag).toBe('BODY');

    // All three persona cards should be reachable (not clipped).
    await expect(page.getByTestId('persona-card-marco')).toBeVisible();
    await expect(page.getByTestId('persona-card-anna')).toBeVisible();
    await expect(page.getByTestId('persona-card-theo')).toBeVisible();
  });

  test('backdrop click dismisses the modal', async ({ page }) => {
    await openLabsAsReturningVisitor(page);

    await page.getByTestId('agent-trace-persona-switcher').click();
    const backdrop = page.getByTestId('persona-modal-backdrop');
    await expect(backdrop).toBeVisible();

    // Click the backdrop corner (not the card).
    await backdrop.click({ position: { x: 10, y: 10 } });
    await expect(backdrop).toBeHidden();
  });
});
