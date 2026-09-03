import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

  it('keeps the workbench index out of the initial evidence viewport until requested', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <WorkbenchResources collapsible defaultExpanded={false} />
      </MemoryRouter>,
    );

    const disclosure = screen.getByRole('button', {
      name: /Explore reference views/i,
    });
    expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    expect(
      screen.queryByRole('heading', {
        name: 'Telemetry from the running system',
      }),
    ).not.toBeInTheDocument();

    await user.click(disclosure);

    expect(disclosure).toHaveAttribute('aria-expanded', 'true');
    expect(
      screen.getByRole('heading', {
        name: 'Telemetry from the running system',
      }),
    ).toBeVisible();
    expect(screen.getByText('What reached PostgreSQL?')).toBeVisible();
  });
});
