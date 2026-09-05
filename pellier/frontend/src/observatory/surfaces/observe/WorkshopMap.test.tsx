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

    expect(screen.getAllByText(/^Lab [1-4] ·/).map((node) => node.textContent)).toEqual([
      'Lab 1 · Build',
      'Lab 2 · Build & Measure',
      'Lab 3 · Deploy & Operate',
      'Lab 4 · Govern',
    ]);
    expect(
      screen.getByRole('heading', { name: 'Build a PostgreSQL-Grounded Agent' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        name: 'Build and Measure PostgreSQL Hybrid Retrieval',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        name: 'Deploy and Operate the Managed Agent Path',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Govern and Prove Agent Actions' }),
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
