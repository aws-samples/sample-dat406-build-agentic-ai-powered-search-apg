import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import ReferencesIndex from './ReferencesIndex';

describe('Pellier Labs optional deep dives', () => {
  it('groups every supporting view behind one optional index', () => {
    const { container } = render(
      <MemoryRouter>
        <ReferencesIndex />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('heading', { name: 'Optional Deep Dives', level: 1 }),
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

    const expectedIcons = [
      ['Persona journeys', 'lucide-footprints'],
      ['Sessions', 'lucide-rotate-ccw-clock'],
      ['Architecture', 'lucide-network'],
      ['Tools', 'lucide-wrench'],
      ['Write path', 'lucide-database-zap'],
    ] as const;

    for (const [linkName, iconClass] of expectedIcons) {
      const link = screen.getByRole('link', { name: new RegExp(linkName, 'i') });
      expect(link.querySelector(`.${iconClass}`)).not.toBeNull();
    }

    expect(
      container.querySelectorAll('.pellier-labs-reference-link-icon svg'),
    ).toHaveLength(13);
  });
});
