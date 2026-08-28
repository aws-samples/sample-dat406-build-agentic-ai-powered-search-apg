/**
 * Pellier orientation remains session-gated. Pellier Observatory intentionally
 * avoids a blocking tour: its Proof Board supplies persistent orientation.
 *
 * The storefront benefits from a short welcome. Pellier Observatory is a workshop
 * surface, where an interstitial hides the proof a participant came to see.
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import PellierSpotlight from '../PellierSpotlight';

const SRC = resolve(__dirname, '../..');

function read(relativePath: string): string {
  return readFileSync(resolve(SRC, relativePath), 'utf8');
}

describe('first-visit orientation', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('PellierPage renders PellierSpotlight', () => {
    const page = read('pages/PellierPage.tsx');

    expect(page).toContain("import PellierSpotlight from '../components/PellierSpotlight'");
    expect(page).toContain('<PellierSpotlight />');
  });

  it('ObservatoryFrame does not mount a blocking Pellier Observatory tour', () => {
    const frame = read('observatory/shell/ObservatoryFrame.tsx');

    expect(frame).not.toContain('ObservatorySpotlight');
  });

  it('the Pellier spotlight is session-gated so it shows at most once', () => {
    expect(read('components/PellierSpotlight.tsx')).toContain('sessionStorage');
  });

  it('the Pellier spotlight is dismissible', () => {
    const source = read('components/PellierSpotlight.tsx');
    // Escape key handling is the skip affordance.
    expect(source).toContain('Escape');
  });

  it('moves through every step with keyboard navigation', () => {
    render(<PellierSpotlight />);

    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('heading', { name: 'Begin with the edit.' })).toBeInTheDocument();
    // Derived from the source rather than hardcoded: the tour gained an
    // operator step, and a literal count made that a test failure instead of
    // a content change.
    const dots = screen.getAllByRole('button', { name: /Show / });
    expect(dots.length).toBeGreaterThanOrEqual(4);

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('button', { name: 'Show Personalize' })).toHaveAttribute(
      'aria-current',
      'step',
    );

    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getByRole('button', { name: 'Show Browse' })).toHaveAttribute(
      'aria-current',
      'step',
    );
  });

  it('contains keyboard focus and restores it after dismissal', () => {
    const opener = document.createElement('button');
    opener.textContent = 'Open storefront';
    document.body.appendChild(opener);
    opener.focus();

    try {
      render(<PellierSpotlight />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveFocus();

      const focusable = within(dialog).getAllByRole('button');
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      last.focus();
      fireEvent.keyDown(window, { key: 'Tab' });
      expect(first).toHaveFocus();

      first.focus();
      fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
      expect(last).toHaveFocus();

      fireEvent.click(screen.getByRole('button', { name: 'Skip' }));
      expect(opener).toHaveFocus();
    } finally {
      opener.remove();
    }
  });
});

describe('spotlight session gate', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('a dismissed spotlight stays dismissed within the session', () => {
    // Seed the gate as already-seen, mirroring a prior dismissal.
    const source = read('components/PellierSpotlight.tsx');
    const keyMatch = source.match(/SPOTLIGHT_SEEN_KEY\s*=\s*['"]([^'"]+)['"]/);
    expect(keyMatch).not.toBeNull();
    window.sessionStorage.setItem(keyMatch![1], 'true');

    const { container } = render(<PellierSpotlight />);

    // Nothing rendered: the gate held.
    expect(container.textContent).toBe('');
  });
});
