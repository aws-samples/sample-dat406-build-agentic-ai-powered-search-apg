import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import WorkbenchResources from './WorkbenchResources';

describe('WorkbenchResources', () => {
  it('organizes optional depth by participant question', () => {
    render(
      <MemoryRouter>
        <WorkbenchResources />
      </MemoryRouter>,
    );

    for (const question of [
      'What ran?',
      'Why was it allowed?',
      'What reached PostgreSQL?',
      'How does this operate?',
    ]) {
      expect(
        screen.getByRole('region', { name: question }),
      ).toBeInTheDocument();
    }

    expect(screen.getByText(/psql/)).toBeInTheDocument();
    expect(screen.getByText(/AgentCore CLI/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Sessions & traces/ }))
      .toHaveAttribute('href', '/observatory/sessions');
    expect(screen.getByRole('link', { name: /Gateway & policy/ }))
      .toHaveAttribute('href', '/observatory/write-path');
  });
});
