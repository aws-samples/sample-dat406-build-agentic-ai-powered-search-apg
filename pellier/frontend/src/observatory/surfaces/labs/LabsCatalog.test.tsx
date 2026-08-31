import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import LabsCatalog from './LabsCatalog';

describe('LabsCatalog', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the five evidence-first exercises without claiming completion', async () => {
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

    expect(await screen.findByText('Five evidence-first exercises')).toBeInTheDocument();
    expect(
      screen
        .getAllByRole('link')
        .filter((link) => link.getAttribute('href')?.startsWith('/observatory/labs/')),
    ).toHaveLength(5);
    expect(screen.getByText('5 exercises')).toBeInTheDocument();
    expect(screen.queryByText(/workshop complete/i)).not.toBeInTheDocument();
  });
});
