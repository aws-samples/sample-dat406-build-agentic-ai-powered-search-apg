import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Sidebar from './Sidebar';

vi.mock('../../contexts/PersonaContext', () => ({
  usePersona: () => ({ persona: null }),
}));

const buildState = { toolShipped: 14, toolTotal: 15 };

vi.mock('../hooks/useBuildState', () => ({
  useBuildState: () => buildState,
}));

/**
 * Navigation spine tests.
 *
 * The Agent Trace previously showed seven groups and twelve near-equal
 * destinations, which made it read as a second application to learn. The
 * spine is now Cockpit + four numbered labs + collapsed Deep Dives.
 *
 * The invariant that matters most: consolidation must not make any surface
 * unreachable. Every route that used to be in the rail is still routable —
 * Deep Dives holds the rest.
 */
describe('Agent Trace Sidebar', () => {
  it('presents a cockpit, four numbered labs, and deep dives', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/performance']}>
        <Sidebar />
      </MemoryRouter>,
    );

    const nav = screen.getByRole('navigation');
    expect(within(nav).getByText('COCKPIT')).toBeInTheDocument();
    expect(within(nav).getByText(/LAB 1 · GROUND ANSWERS IN LIVE DATA/)).toBeInTheDocument();
    expect(
      within(nav).getByText(/LAB 2 · DESIGN THE RETRIEVAL STRATEGY/),
    ).toBeInTheDocument();
    expect(
      within(nav).getByText(/LAB 3 · RUN AGENTS IN A MANAGED RUNTIME/),
    ).toBeInTheDocument();
    expect(
      within(nav).getByText(/LAB 4 · GOVERN AND TRACE AGENT ACTIONS/),
    ).toBeInTheDocument();
    expect(within(nav).getByText('DEEP DIVES')).toBeInTheDocument();
    // The old Act taxonomy must never return.
    expect(within(nav).queryByText(/ACT (I|II|III)/)).not.toBeInTheDocument();
    // And there is no fifth lab in the visible spine.
    expect(within(nav).queryByText(/LAB 5/)).not.toBeInTheDocument();
  });

  it('expands only the active lab', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/performance']}>
        <Sidebar />
      </MemoryRouter>,
    );

    // Lab 2 is active, so its items render.
    expect(
      screen.getByRole('link', { name: 'Retrieval Comparison' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Search Pipeline' })).toBeInTheDocument();

    // Lab 4's items are collapsed away, keeping one step obvious.
    expect(screen.queryByRole('link', { name: 'Gateway & Policy' })).toBeNull();
  });

  it('keeps the cockpit always expanded', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/performance']}>
        <Sidebar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: /Proof Board/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Workshop Map' })).toBeInTheDocument();
  });

  it('reports lab status as text, not colour alone', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/performance']}>
        <Sidebar />
      </MemoryRouter>,
    );

    const nav = screen.getByRole('navigation');
    // Lab 2 is the active one.
    expect(within(nav).getAllByText('In progress').length).toBeGreaterThan(0);
    // Lab 1 is not complete at 14/15, and says so.
    expect(within(nav).getAllByText('Not started').length).toBeGreaterThan(0);
  });

  it('marks Lab 1 complete only when the build state proves it', () => {
    buildState.toolShipped = 15;
    try {
      render(
        <MemoryRouter initialEntries={['/agent-trace/tools']}>
          <Sidebar />
        </MemoryRouter>,
      );

      const nav = screen.getByRole('navigation');
      expect(within(nav).getAllByText('Complete').length).toBeGreaterThan(0);
    } finally {
      buildState.toolShipped = 14;
    }
  });

  it('gives every nav link an accessible name for the compact rail', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/tools']}>
        <Sidebar />
      </MemoryRouter>,
    );

    // The compact icon rail hides visible labels; the links must still be
    // named or an icon-only rail is unusable with a screen reader.
    for (const link of screen.getAllByRole('link')) {
      expect(link.getAttribute('aria-label')).toBeTruthy();
    }
  });

  it('routes Lab 1 to the tool registry with its shipped badge', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/tools']}>
        <Sidebar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Tool Registry' })).toHaveAttribute(
      'href',
      '/agent-trace/tools',
    );
  });

  it('marks only the Audit Proof route as current', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/audit-proof']}>
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

  it('keeps previously-visible surfaces reachable under Deep Dives', () => {
    // Consolidation must not orphan a route. Routing/Architecture/etc moved
    // rather than disappeared.
    render(
      <MemoryRouter initialEntries={['/agent-trace/routing']}>
        <Sidebar />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('link', { name: 'Agent Behavior & Routing' }),
    ).toHaveAttribute('href', '/agent-trace/routing');
    expect(screen.getByRole('link', { name: 'Architecture' })).toHaveAttribute(
      'href',
      '/agent-trace/architecture',
    );
  });
});
