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
  it('mirrors the four Core Labs and keeps optional surfaces separate', () => {
    render(
      <MemoryRouter initialEntries={['/atelier/performance']}>
        <Sidebar />
      </MemoryRouter>,
    );

    const nav = screen.getByRole('navigation');
    expect(within(nav).getByText('CORE LAB 1 · BUILD AND TRACE')).toBeInTheDocument();
    expect(within(nav).getByText('CORE LAB 2 · MEASURE RETRIEVAL')).toBeInTheDocument();
    expect(within(nav).getByText('CORE LAB 3 · QUERY EVIDENCE')).toBeInTheDocument();
    expect(within(nav).getByText('CORE LAB 4 · ENFORCE POLICY')).toBeInTheDocument();
    expect(within(nav).getByText('OPTIONAL LABS')).toBeInTheDocument();
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
    const coreLab3Section = within(nav)
      .getByText('CORE LAB 3 · QUERY EVIDENCE')
      .parentElement;
    expect(coreLab3Section).not.toBeNull();
    expect(
      within(coreLab3Section as HTMLElement).getByRole('link', { name: 'Memory opt' }),
    ).toHaveAttribute('href', '/atelier/memory');
    expect(screen.getAllByRole('link', { name: 'Memory opt' })).toHaveLength(1);
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
