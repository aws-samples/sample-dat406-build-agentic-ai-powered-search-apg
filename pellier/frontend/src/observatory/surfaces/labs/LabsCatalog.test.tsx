import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { LAB_EXERCISES } from '../../labs/labCatalog';
import LabsCatalog from './LabsCatalog';

describe('LabsCatalog', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the four evidence-first labs without claiming completion', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: 'attention',
            managedReceipt: { present: false },
            cards: [],
          }),
          { status: 200 },
        ),
      ),
    );

    render(
      <MemoryRouter>
        <LabsCatalog />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Four evidence-first labs')).toBeInTheDocument();
    expect(
      screen
        .getAllByRole('link')
        .filter((link) => link.classList.contains('labs-catalog-card')),
    ).toHaveLength(4);
    expect(screen.getByText('4 labs')).toBeInTheDocument();
    expect(screen.queryByText(/workshop complete/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        name: 'Telemetry from the running system',
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('What reached PostgreSQL?')).toBeInTheDocument();

    expect(
      document.querySelectorAll('.labs-catalog-contact-sheet figure'),
    ).toHaveLength(4);
    expect(
      document.querySelector('.labs-catalog-hero > picture'),
    ).not.toBeInTheDocument();
  });

  it('anchors each lab to its named persona and portrait', () => {
    expect(
      LAB_EXERCISES.map(({ anchorName, image }) => ({ anchorName, image })),
    ).toEqual([
      {
        anchorName: 'Marco',
        image: '/assets/personas/marco.png',
      },
      {
        anchorName: 'Anna',
        image: '/assets/personas/anna.png',
      },
      {
        anchorName: 'Theo',
        image: '/assets/personas/theo.png',
      },
      {
        anchorName: 'Jessica',
        image: '/assets/personas/jessica.png',
      },
    ]);

    const managed = LAB_EXERCISES.find(
      (exercise) => exercise.id === 'managed-agent-path',
    );
    const governed = LAB_EXERCISES.find(
      (exercise) => exercise.id === 'fail-closed-policy',
    );

    expect(managed?.objective).toContain('With Theo selected');
    expect(managed?.participantTodo).toContain('three-turn');
    expect(managed?.command).toContain(
      'Hand-thrown ceramics for a slower morning routine',
    );

    expect(governed).toMatchObject({
      image: '/assets/personas/jessica.png',
      imageWidth: 960,
      imageHeight: 1200,
    });
    expect(governed?.objective).toContain('Marco, Anna, and Jessica');
    expect(governed?.participantTodo).toContain('four-case identity matrix');
    expect(governed?.participantTodo).toContain('RLS read and write');
    expect(governed?.participantTodo).toContain('three-turn Operator investigation');
    expect(governed?.command).toContain('scripts/prove_identity_boundary.py');
    expect(governed?.evidenceAssertion).toContain('human checkpoint');
    expect(governed?.primaryAction).toEqual({
      label: 'Open Jessica in Operator',
      to: '/operator/clients/CUST-JESSICA?guided=service-recovery#operator-concierge-title',
    });
  });
});
