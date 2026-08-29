import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import ObservatoryContextBanner from './ObservatoryContextBanner';

describe('ObservatoryContextBanner', () => {
  it('offers an unambiguous return to the Storefront from a shopper trace', () => {
    render(
      <MemoryRouter
        initialEntries={[
          '/observatory/proof-board?from=pellier&trace=tool.transparency',
        ]}
      >
        <ObservatoryContextBanner />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('link', { name: 'Return to Storefront' }),
    ).toHaveAttribute('href', '/');
  });
});
