/**
 * governed_tokens_import.test.ts
 *
 * `styles/governed-tokens.css` defines every `--gov-*` token and the
 * `.gov-visually-hidden` utility that PolicyDecisionBadge, GovernedSeal and
 * GovernedTurnReceipt depend on. It was once left unimported: the badge
 * rendered with no colour and its screen-reader sentence became visible,
 * overflowing the Proof Board's receipt panel on phones. Vitest runs with
 * CSS disabled, so a render test cannot see that; this file checks the
 * import contract directly.
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const indexCss = readFileSync(resolve(here, '../index.css'), 'utf8');
const tokensCss = readFileSync(
  resolve(here, '../styles/governed-tokens.css'),
  'utf8',
);

describe('governed token stylesheet', () => {
  it('is imported by index.css after the Daylight bridge', () => {
    const bridge = indexCss.indexOf("@import './styles/daylight-bridge.css';");
    const tokens = indexCss.indexOf("@import './styles/governed-tokens.css';");
    expect(bridge).toBeGreaterThan(-1);
    expect(tokens).toBeGreaterThan(bridge);
  });

  it('still defines the visually-hidden utility the badges rely on', () => {
    expect(tokensCss).toMatch(/\.gov-visually-hidden\s*\{/);
  });
});
