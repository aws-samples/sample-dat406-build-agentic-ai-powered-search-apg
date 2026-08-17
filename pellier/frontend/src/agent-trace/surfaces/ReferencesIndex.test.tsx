import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import ReferencesIndex from './ReferencesIndex';

describe('Pellier Labs optional references', () => {
  it('groups every supporting view behind one optional index', () => {
    render(
      <MemoryRouter>
        <ReferencesIndex />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('heading', { name: 'Optional References', level: 1 }),
    ).toBeInTheDocument();

    const groups = [
      ['Replay and compare', ['Persona journeys', 'Sessions']],
      [
        'Inspect the request path',
        ['Architecture', 'Agents', 'Tools', 'Skills', 'Search', 'Routing', 'Memory', 'Write path'],
      ],
      [
        'Evaluate and productionize',
        ['Performance', 'Evaluations', 'Production patterns'],
      ],
    ] as const;

    for (const [heading, links] of groups) {
      const section = screen.getByRole('heading', { name: heading }).closest('section');
      expect(section).not.toBeNull();
      for (const link of links) {
        expect(within(section as HTMLElement).getByRole('link', { name: new RegExp(link) })).toBeInTheDocument();
      }
    }

    expect(
      screen.getByRole('link', {
        name: /AgentCore session turns and preferences, separated from Aurora state and evidence/,
      }),
    ).toBeInTheDocument();
  });
});
