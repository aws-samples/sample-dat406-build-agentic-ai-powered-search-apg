import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import Observatory from './Observatory';

describe('Atelier workshop map', () => {
  it('uses the exact governed Core Lab sequence and destinations', () => {
    render(
      <MemoryRouter>
        <Observatory />
      </MemoryRouter>,
    );

    expect(screen.getAllByText(/^Core Lab [1-4]$/).map((node) => node.textContent)).toEqual([
      'Core Lab 1',
      'Core Lab 2',
      'Core Lab 3',
      'Core Lab 4',
    ]);
    expect(screen.getByRole('heading', { name: 'Build and Trace' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Measure Retrieval' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Query Evidence' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Enforce Policy' })).toBeInTheDocument();
    expect(screen.queryByText(/^Act (I|II|III)$/)).not.toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Open retrieval comparison/i })).toHaveAttribute(
      'href',
      '/atelier/performance',
    );
    expect(screen.getByRole('link', { name: /Open audit proof/i })).toHaveAttribute(
      'href',
      '/atelier/audit-proof',
    );
    expect(screen.getByRole('link', { name: /^Memory/i })).toHaveAttribute(
      'href',
      '/atelier/memory',
    );
    expect(screen.getByRole('link', { name: /Open Gateway & Policy/i })).toHaveAttribute(
      'href',
      '/atelier/write-path',
    );
  });
});
