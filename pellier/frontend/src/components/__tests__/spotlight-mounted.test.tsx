/**
 * First-visit orientation is actually mounted (audit finding D5).
 *
 * The repository shipped `BoutiqueSpotlight` and `AtelierSpotlight` as
 * complete, session-gated components that nothing rendered. Dead
 * onboarding code is worse than none: it reads as a delivered feature in
 * review while an attendee lands on four unexplained surfaces.
 *
 * These tests assert the components are referenced by the pages that own
 * them, and that the session gate still suppresses a repeat showing.
 */
import { describe, expect, it, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const SRC = resolve(__dirname, '../..');

function read(relativePath: string): string {
  return readFileSync(resolve(SRC, relativePath), 'utf8');
}

describe('first-visit orientation is mounted', () => {
  it('BoutiquePage renders BoutiqueSpotlight', () => {
    const page = read('pages/BoutiquePage.tsx');

    expect(page).toContain("import BoutiqueSpotlight from '../components/BoutiqueSpotlight'");
    expect(page).toContain('<BoutiqueSpotlight />');
  });

  it('AtelierFrame renders AtelierSpotlight', () => {
    const frame = read('atelier/shell/AtelierFrame.tsx');

    expect(frame).toContain('AtelierSpotlight');
    expect(frame).toContain('<AtelierSpotlight />');
  });

  it('both spotlights are session-gated so they show at most once', () => {
    // A tour that reappears on every route change is worse than no tour.
    for (const file of [
      'components/BoutiqueSpotlight.tsx',
      'components/AtelierSpotlight.tsx',
    ]) {
      expect(read(file)).toContain('sessionStorage');
    }
  });

  it('both spotlights are dismissible', () => {
    for (const file of [
      'components/BoutiqueSpotlight.tsx',
      'components/AtelierSpotlight.tsx',
    ]) {
      const source = read(file);
      // Escape key handling is the skip affordance.
      expect(source).toContain('Escape');
    }
  });
});

describe('spotlight session gate', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('a dismissed spotlight stays dismissed within the session', async () => {
    const { default: BoutiqueSpotlight } = await import('../BoutiqueSpotlight');
    const { render } = await import('@testing-library/react');

    // Seed the gate as already-seen, mirroring a prior dismissal.
    const source = read('components/BoutiqueSpotlight.tsx');
    const keyMatch = source.match(/SPOTLIGHT_SEEN_KEY\s*=\s*['"]([^'"]+)['"]/);
    expect(keyMatch).not.toBeNull();
    window.sessionStorage.setItem(keyMatch![1], 'true');

    const { container } = render(<BoutiqueSpotlight />);

    // Nothing rendered: the gate held.
    expect(container.textContent).toBe('');
  });
});
