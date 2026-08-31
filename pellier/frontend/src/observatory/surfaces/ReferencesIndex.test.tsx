import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import ReferencesIndex from './ReferencesIndex';

const buildState = { toolShipped: 14, toolTotal: 15 };

vi.mock('../hooks/useBuildState', () => ({
  useBuildState: () => buildState,
}));

/**
 * This page is the Observatory's navigation.
 *
 * There is no sidebar: `ObservatoryFrame` renders the top bar and an outlet, so
 * the two tabs plus this directory are the whole nav. A `Sidebar` component did
 * exist, with its own group names and its own labels for the same destinations,
 * and it rendered nowhere for six days while its tests passed against a
 * directly-mounted copy. It has been deleted. If a rail ever returns, these
 * labels are the ones it must use.
 */
describe('Observatory navigation index', () => {
  const GROUPS = [
    ['Proof views', ['Proof Board', 'Audit Proof']],
    ['Replay live evidence', ['Sessions']],
    [
      'Inspect the build',
      [
        'Architecture',
        'Tool Registry',
        'Skills',
        'Search Pipeline',
        'Routing',
        'Memory Types',
        'Gateway & Policy',
      ],
    ],
    ['Measure', ['Retrieval Comparison', 'Evaluations', 'Production Patterns']],
  ] as const;

  function renderPage() {
    return render(
      <MemoryRouter>
        <ReferencesIndex />
      </MemoryRouter>,
    );
  }

  it('titles the page and leads with the proof views', () => {
    const { container } = renderPage();

    expect(
      screen.getByRole('heading', { name: 'Proof & References', level: 1 }),
    ).toBeInTheDocument();

    const sections = container.querySelectorAll('.observatory-reference-group');
    expect(sections[0]).toHaveTextContent('Proof views');
    expect(sections[0]).toHaveTextContent('Proof Board');
    expect(sections[0]).toHaveTextContent('Audit Proof');
    expect(sections[0]).not.toHaveTextContent('Persona Journeys');
  });

  it('never tells a participant they owe work on an optional surface', () => {
    const { container } = renderPage();
    const text = container.textContent ?? '';

    // The surface is badged Optional in the top bar and on the storefront. A
    // "Required proof" heading here contradicted that badge in the same
    // viewport, which is the exact confusion the rename set out to end.
    expect(text).not.toMatch(/required/i);
    expect(text).not.toMatch(/complete the workshop path/i);
    // Self-paced workshop: no facilitator sends anyone anywhere.
    expect(text).not.toMatch(/facilitator/i);
  });

  it('names the canonical proof rather than implying these views are it', () => {
    renderPage();

    // Architecture invariant: Code Editor plus SQL/curl remain canonical proof,
    // and the Observatory is an assisted read of the same rows.
    expect(
      screen.getByText(/For workshop verification, curl and SQL in the Code Editor remain canonical/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/organize the same API and Aurora evidence/i))
      .toBeInTheDocument();
    expect(screen.queryByText(/Every view the Observatory offers/i))
      .not.toBeInTheDocument();
  });

  it('keeps the workshop source with references instead of the primary navigation', () => {
    renderPage();

    const source = screen.getByRole('link', {
      name: 'View workshop source on GitHub',
    });
    expect(source).toHaveAttribute(
      'href',
      'https://github.com/aws-samples/sample-pellier-agentic-search-apg',
    );
    expect(source).toHaveAttribute('target', '_blank');
    expect(source).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it.each(GROUPS)('groups %s with its destinations', (heading, links) => {
    renderPage();

    const section = screen.getByRole('heading', { name: heading }).closest('section');
    expect(section).not.toBeNull();
    for (const link of links) {
      expect(
        within(section as HTMLElement).getByRole('link', {
          name: new RegExp(link.replace('&', '&'), 'i'),
        }),
      ).toBeInTheDocument();
    }
  });

  it('uses one name per destination, in title case', () => {
    renderPage();

    // Six labels drifted from the deleted sidebar's names for the same routes
    // (Tools/Tool Registry, Search/Search Pipeline, Memory/Memory Types,
    // Performance/Retrieval Comparison, and two sentence-case strays).
    const labels = Array.from(
      document.querySelectorAll('.observatory-reference-link-copy strong'),
    ).map((node) => node.textContent ?? '');

    expect(labels).toHaveLength(14);
    for (const label of labels) {
      // Strip the appended live count before checking the label itself.
      const name = label.replace(/\d+\/\d+$|—$/, '').trim();
      expect(name).not.toMatch(/^[a-z]/);
      // Every multi-word label is title case: no "Gateway and policy".
      for (const word of name.split(/[\s&]+/).filter(Boolean)) {
        expect(word[0]).toBe(word[0].toUpperCase());
      }
    }
  });

  it('shows the live shipped-tool count on the Tool Registry only', () => {
    renderPage();

    const counts = screen.getAllByTestId('reference-tool-count');
    expect(counts).toHaveLength(1);
    expect(counts[0]).toHaveTextContent('14/15');
    expect(counts[0].closest('a')).toHaveAttribute('href', '/observatory/tools');
  });

  it('says unknown rather than guessing when build state is unavailable', () => {
    buildState.toolTotal = 0;
    buildState.toolShipped = 0;
    try {
      renderPage();
      expect(screen.getByTestId('reference-tool-count')).toHaveTextContent('—');
    } finally {
      buildState.toolTotal = 15;
      buildState.toolShipped = 14;
    }
  });

  it('renders one icon per destination', () => {
    const { container } = renderPage();

    expect(
      container.querySelectorAll('.observatory-reference-link-icon svg'),
    ).toHaveLength(14);
  });

  it.each([
    ['Sessions', 'lucide-rotate-ccw-clock'],
    ['Architecture', 'lucide-network'],
    ['Tool Registry', 'lucide-wrench'],
  ])('gives %s its own icon', (linkName, iconClass) => {
    renderPage();

    const link = screen.getByRole('link', { name: new RegExp(linkName, 'i') });
    expect(link.querySelector(`.${iconClass}`)).not.toBeNull();
  });

  it('keeps the memory description that distinguishes the two stores', () => {
    renderPage();

    expect(
      screen.getByRole('link', {
        name: /AgentCore turns and preferences, separated from Aurora state and audit evidence/,
      }),
    ).toBeInTheDocument();
  });
});
