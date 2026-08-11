import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import Observatory from './Observatory';

describe('Agent Trace workshop map', () => {
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
    expect(screen.getByRole('heading', { name: 'Ground Answers in Live Data' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Choose a Search Strategy You Can Defend' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Run the Agent as a Managed Service' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Stop the Wrong Action Before It Runs' }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^Act (I|II|III)$/)).not.toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Open retrieval comparison/i })).toHaveAttribute(
      'href',
      '/agent-trace/performance',
    );
    expect(screen.getByRole('link', { name: /Open Lab 3 proofs/i })).toHaveAttribute(
      'href',
      '/agent-trace/proof-board#managed-rail',
    );
    expect(screen.getByRole('link', { name: /Open Gateway & Policy/i })).toHaveAttribute(
      'href',
      '/agent-trace/write-path',
    );
  });
});
