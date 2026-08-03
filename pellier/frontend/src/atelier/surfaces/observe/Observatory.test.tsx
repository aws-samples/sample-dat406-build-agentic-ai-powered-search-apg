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

    expect(screen.getAllByText(/^Lab [1-5]$/).map((node) => node.textContent)).toEqual([
      'Lab 1',
      'Lab 2',
      'Lab 3',
      'Lab 4',
      'Lab 5',
    ]);
    expect(screen.getByRole('heading', { name: 'Build a Specialist Agent' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Measure Hybrid Search' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Prove AgentCore Memory' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Audit Agent Actions' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Enforce Cedar Policy' })).toBeInTheDocument();
    expect(screen.queryByText(/^Act (I|II|III)$/)).not.toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Open retrieval comparison/i })).toHaveAttribute(
      'href',
      '/atelier/performance',
    );
    expect(screen.getByRole('link', { name: /Open audit proof/i })).toHaveAttribute(
      'href',
      '/atelier/audit-proof',
    );
    expect(screen.getByRole('link', { name: /Open Memory/i })).toHaveAttribute(
      'href',
      '/atelier/memory',
    );
    expect(screen.getByRole('link', { name: /Open Gateway & Policy/i })).toHaveAttribute(
      'href',
      '/atelier/write-path',
    );
  });
});
