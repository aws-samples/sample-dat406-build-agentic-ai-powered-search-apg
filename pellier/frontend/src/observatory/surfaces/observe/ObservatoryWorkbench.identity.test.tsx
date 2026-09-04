/**
 * The workbench reads a persona identity, not a persona object.
 *
 * The effect that resets a run depends on the whole `selectedPersona` object,
 * but the only thing it and the run path use is `customer_id`. Any provider
 * that hands back a fresh object for the same shopper therefore re-runs the
 * reset, and the reset assigns new arrays and objects (`setSteps([])`,
 * `setTurnEntries([])`, `setReceiptOverrides({})`), so React can never bail
 * out on an unchanged value: every render schedules the next one.
 *
 * The loop is synchronous inside `act`, so it starves the event loop and no
 * test timeout can fire. The persona mock therefore carries a render budget
 * and throws when it is exceeded, which turns a hang into a failed assertion
 * with a count in the message.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  sendChatMessageStreaming: vi.fn(),
  usePersona: vi.fn(),
}));

vi.mock('../../../services/chat', () => ({
  sendChatMessageStreaming: mocks.sendChatMessageStreaming,
}));

vi.mock('../../../contexts/PersonaContext', () => ({
  usePersona: mocks.usePersona,
}));

import ObservatoryWorkbench from './ObservatoryWorkbench';

/**
 * Renders past this many times and the surface is not settling. Mount plus
 * the scenario fetch plus a few effect passes is well inside it.
 */
const RENDER_BUDGET = 40;

let renders = 0;

/** A new object every call, the same shopper every call. */
function unstableMarco() {
  renders += 1;
  if (renders > RENDER_BUDGET) {
    throw new Error(
      `ObservatoryWorkbench rendered more than ${RENDER_BUDGET} times for one ` +
        'persona: the reset effect is re-running on persona object identity.',
    );
  }
  return {
    persona: { id: 'marco', display_name: 'Marco', customer_id: 'CUST-MARCO' },
    switchPersona: vi.fn(),
    switching: false,
    switchError: null,
  };
}

function scenariosResponse(): Response {
  return new Response(
    JSON.stringify({
      persona: 'marco',
      scenarios: [
        {
          id: 1,
          ordinal: 1,
          prompt: 'First guided turn',
          productName: null,
          imageUrl: null,
        },
      ],
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
}

function workbench() {
  return (
    <MemoryRouter
      initialEntries={['/observatory/workbench?lab=grounded-inventory']}
    >
      <ObservatoryWorkbench />
    </MemoryRouter>
  );
}

describe('Observatory workbench persona identity', () => {
  beforeEach(() => {
    renders = 0;
    localStorage.clear();
    mocks.usePersona.mockReset();
    mocks.usePersona.mockImplementation(unstableMarco);
    mocks.sendChatMessageStreaming.mockReset();
    mocks.sendChatMessageStreaming.mockResolvedValue({
      response: 'A grounded answer.',
      products: [],
      suggestions: [],
    });
    vi.stubGlobal('fetch', vi.fn(async () => scenariosResponse()));
  });

  it('settles when the persona object identity changes on every render', () => {
    expect(() => render(workbench())).not.toThrow();
    expect(renders).toBeLessThan(RENDER_BUDGET);
  });

  it('keeps the current step when the persona re-resolves to the same shopper', () => {
    const { rerender } = render(workbench());

    fireEvent.click(screen.getByRole('button', { name: /Reconcile answer/ }));
    expect(
      screen.getByRole('button', { name: /Reconcile answer/ }),
    ).toHaveAttribute('aria-current', 'step');

    // A fresh object for the same shopper: what a provider re-render or a
    // persona re-fetch hands down. Nothing about the run has changed.
    rerender(workbench());

    expect(
      screen.getByRole('button', { name: /Reconcile answer/ }),
    ).toHaveAttribute('aria-current', 'step');
  });
});
