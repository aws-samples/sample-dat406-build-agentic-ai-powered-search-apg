import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { TEST_ROUTER_FUTURE_FLAGS } from '../../test-utils';

vi.mock('../../contexts/PersonaContext', () => ({
  usePersona: () => ({ persona: null }),
}));

vi.mock('../../components/PersonaModal', () => ({
  default: () => null,
}));

vi.mock('../../shared', () => ({
  PresencePill: () => null,
}));

import TopBar from './TopBar';

describe('Pellier Labs TopBar', () => {
  it('provides one explicit route back to Pellier', () => {
    render(
      <MemoryRouter
        initialEntries={['/agent-trace/proof-board']}
        future={TEST_ROUTER_FUTURE_FLAGS}
      >
        <TopBar />
      </MemoryRouter>,
    );

    const backLink = screen.getByRole('link', { name: 'Back to Pellier' });
    expect(backLink).toHaveAttribute('href', '/');
    expect(screen.queryByRole('group', { name: 'Switch surface' })).not.toBeInTheDocument();
  });

  it('keeps the current Labs route in the breadcrumb', () => {
    render(
      <MemoryRouter
        initialEntries={['/agent-trace/proof-board']}
        future={TEST_ROUTER_FUTURE_FLAGS}
      >
        <TopBar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent(
      'Pellier LabsProof Board',
    );
  });
});
