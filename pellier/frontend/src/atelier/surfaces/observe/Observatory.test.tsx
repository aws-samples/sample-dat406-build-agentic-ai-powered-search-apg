import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import Observatory from './Observatory';

describe('Atelier workshop map', () => {
  it('uses the exact governed lab sequence and destinations', () => {
    render(
      <MemoryRouter>
        <Observatory />
      </MemoryRouter>,
    );

    expect(screen.getAllByText(/^Lab [1-4]$/).map((node) => node.textContent)).toEqual([
      'Lab 1',
      'Lab 2',
      'Lab 3',
      'Lab 4',
    ]);
    expect(screen.getByRole('heading', { name: 'Build & Trace' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Retrieval Quality' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Managed Execution & Audit' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Govern Actions' })).toBeInTheDocument();
    expect(screen.queryByText(/^Act (I|II|III)$/)).not.toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Open retrieval comparison/i })).toHaveAttribute(
      'href',
      '/atelier/performance',
    );
    expect(screen.getByRole('link', { name: /Open Lab 3 proofs/i })).toHaveAttribute(
      'href',
      '/atelier/proof-board#managed-rail',
    );
    expect(screen.getByRole('link', { name: /Open Gateway & Policy/i })).toHaveAttribute(
      'href',
      '/atelier/write-path',
    );
  });
});
