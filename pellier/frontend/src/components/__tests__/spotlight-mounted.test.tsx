/**
 * Boutique orientation remains session-gated. Pellier Labs intentionally
 * avoids a blocking tour: its Proof Board supplies persistent orientation.
 *
 * The storefront benefits from a short welcome. Pellier Labs is a workshop
 * surface, where an interstitial hides the proof a participant came to see.
 */
import { render } from '@testing-library/react';
import { describe, expect, it, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import BoutiqueSpotlight from '../BoutiqueSpotlight';

const SRC = resolve(__dirname, '../..');

function read(relativePath: string): string {
  return readFileSync(resolve(SRC, relativePath), 'utf8');
}

describe('first-visit orientation', () => {
  it('BoutiquePage renders BoutiqueSpotlight', () => {
    const page = read('pages/BoutiquePage.tsx');

    expect(page).toContain("import BoutiqueSpotlight from '../components/BoutiqueSpotlight'");
    expect(page).toContain('<BoutiqueSpotlight />');
  });

  it('AgentTraceFrame does not mount a blocking Pellier Labs tour', () => {
    const frame = read('agent-trace/shell/AgentTraceFrame.tsx');

    expect(frame).not.toContain('AgentTraceSpotlight');
  });

  it('the Boutique spotlight is session-gated so it shows at most once', () => {
    expect(read('components/BoutiqueSpotlight.tsx')).toContain('sessionStorage');
  });

  it('the Boutique spotlight is dismissible', () => {
    const source = read('components/BoutiqueSpotlight.tsx');
    // Escape key handling is the skip affordance.
    expect(source).toContain('Escape');
  });
});

describe('spotlight session gate', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('a dismissed spotlight stays dismissed within the session', () => {
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
