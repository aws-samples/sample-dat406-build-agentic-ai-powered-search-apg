import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import WorkshopMap from './WorkshopMap';

describe('Observatory workshop map', () => {
  it('uses the exact governed lab sequence and destinations', () => {
    render(
      <MemoryRouter>
        <WorkshopMap />
      </MemoryRouter>,
    );

    expect(screen.getAllByText(/^0[1-4] /).map((node) => node.textContent)).toEqual([
      '01 GROUND THE ANSWER',
      '02 MEASURE HYBRID RETRIEVAL',
      '03 OPERATE THE MANAGED AGENT PATH',
      '04 GOVERN AND PROVE ACTIONS',
    ]);
    expect(screen.getByRole('heading', { name: 'Live Data and Evidence' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Search, Filters, and Trade-offs' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Runtime, Gateway, Memory, and Trace' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Human Decision, Policy, Database, and Receipts' }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^Act (I|II|III)$/)).not.toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Open retrieval comparison/i })).toHaveAttribute(
      'href',
      '/observatory/performance',
    );
    expect(screen.getByRole('link', { name: /Open Lab 3 proofs/i })).toHaveAttribute(
      'href',
      '/observatory/proof-board#managed-rail',
    );
    expect(screen.getByRole('link', { name: /Open Gateway & Policy/i })).toHaveAttribute(
      'href',
      '/observatory/write-path',
    );
  });
});
