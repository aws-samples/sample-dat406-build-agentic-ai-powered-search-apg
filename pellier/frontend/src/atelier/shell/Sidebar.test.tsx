import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Sidebar from './Sidebar';

vi.mock('../../contexts/PersonaContext', () => ({
  usePersona: () => ({ persona: null }),
}));

vi.mock('../hooks/useBuildState', () => ({
  useBuildState: () => ({
    toolShipped: 14,
    toolTotal: 15,
  }),
}));

describe('Atelier Sidebar', () => {
  it('mirrors the five required labs and keeps extension surfaces separate', () => {
    render(
      <MemoryRouter initialEntries={['/atelier/performance']}>
        <Sidebar />
      </MemoryRouter>,
    );

    const nav = screen.getByRole('navigation');
    expect(within(nav).getByText('LAB 1 · BUILD A SPECIALIST AGENT')).toBeInTheDocument();
    expect(within(nav).getByText('LAB 2 · MEASURE HYBRID SEARCH')).toBeInTheDocument();
    expect(within(nav).getByText('LAB 3 · PROVE AGENTCORE MEMORY')).toBeInTheDocument();
    expect(within(nav).getByText('LAB 4 · AUDIT AGENT ACTIONS')).toBeInTheDocument();
    expect(within(nav).getByText('LAB 5 · ENFORCE CEDAR POLICY')).toBeInTheDocument();
    expect(within(nav).getByText('EXTENSION')).toBeInTheDocument();
    expect(within(nav).queryByText(/ACT (I|II|III)/)).not.toBeInTheDocument();

    expect(screen.getByRole('link', { name: 'Retrieval Comparison' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'Tool Registry 14/15' })).toHaveAttribute(
      'href',
      '/atelier/tools',
    );
    expect(screen.getByRole('link', { name: 'Audit Proof' })).toHaveAttribute(
      'href',
      '/atelier/audit-proof',
    );
    const lab3Section = within(nav)
      .getByText('LAB 3 · PROVE AGENTCORE MEMORY')
      .parentElement;
    expect(lab3Section).not.toBeNull();
    expect(
      within(lab3Section as HTMLElement).getByRole('link', { name: 'Memory' }),
    ).toHaveAttribute('href', '/atelier/memory');
    expect(screen.getAllByRole('link', { name: 'Memory' })).toHaveLength(1);
  });

  it('marks only the Audit Proof route as current', () => {
    render(
      <MemoryRouter initialEntries={['/atelier/audit-proof']}>
        <Sidebar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Audit Proof' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: /Proof Board/ })).not.toHaveAttribute(
      'aria-current',
    );
  });
});
