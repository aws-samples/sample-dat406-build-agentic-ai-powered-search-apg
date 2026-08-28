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

    expect(screen.getAllByText(/^Lab [1-4]$/).map((node) => node.textContent)).toEqual([
      'Lab 1',
      'Lab 2',
      'Lab 3',
      'Lab 4',
    ]);
    expect(screen.getByRole('heading', { name: 'Ground Answers in Live Data' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Measure Hybrid Retrieval Trade-offs' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Operate the Managed Agent Path' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Govern Actions and Prove Outcomes' }),
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
