import { describe, expect, it } from 'vitest';
import { composeWelcomeGreeting } from './PellierWelcome';

describe('composeWelcomeGreeting', () => {
  it('does not double-punctuate a returning shopper greeting', () => {
    expect(
      composeWelcomeGreeting('Good morning', ', Marco. Welcome back.'),
    ).toBe('Good morning, Marco. Welcome back.');
  });
});
