import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  sendChatMessageStreaming: vi.fn(),
  persona: null as null | {
    id: string;
    display_name: string;
    customer_id: string;
  },
}));

vi.mock('../../../services/chat', () => ({
  sendChatMessageStreaming: mocks.sendChatMessageStreaming,
}));

vi.mock('../../../contexts/PersonaContext', () => ({
  usePersona: () => ({ persona: mocks.persona }),
}));

import { PERSONA_HERO_PILLS } from '../../../data/personaCurations';
import ObservatoryWorkbench from './ObservatoryWorkbench';

/**
 * There is no free-text box any more: a run starts by inspecting one of the
 * curated turns, and the query the agent receives is the canonical string from
 * personaCurations. Tests drive the surface the same way a participant does.
 */
const FRESH_TURNS = PERSONA_HERO_PILLS.fresh;

async function inspectTurn(
  user: ReturnType<typeof userEvent.setup>,
  query: string,
) {
  await user.click(screen.getByRole('button', { name: `Inspect: ${query}` }));
}

/** Tool and skill names appear on the turn cards too, so trace-panel
 *  assertions must be scoped rather than matched globally. */
function tracePanel(container: HTMLElement): HTMLElement {
  const panel = container.querySelector<HTMLElement>(
    '.observatory-trace-panel',
  );
  if (!panel) throw new Error('trace panel not rendered');
  return panel;
}

describe('Pellier Observatory live agent workbench', () => {
  beforeEach(() => {
    mocks.sendChatMessageStreaming.mockReset();
    mocks.persona = null;
  });

  it('opens as an inspectable doorway with no request to compose', () => {
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('heading', {
        name: 'Live Workbench',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Run a governed shopper request and inspect identity, policy decisions, transaction state, and durable evidence.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText('Live governed surface')).toBeInTheDocument();
    expect(
      tracePanel(document.body).querySelector('canvas.labs-hero-field'),
    ).not.toBeInTheDocument();
    const proofSummary = screen.getByRole('status', {
      name: 'Run proof summary',
    });
    expect(proofSummary).toHaveTextContent('Ready to inspect');
    expect(proofSummary).toHaveTextContent(
      'Choose one of five canonical shopper turns.',
    );

    // The free-text box is gone: nothing here asks a participant to build.
    expect(screen.queryByLabelText('Shopper request')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Run agent' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.queryByText(/recorded/i)).not.toBeInTheDocument();

    // Five curated turns, straight from the shared storefront source.
    expect(FRESH_TURNS).toHaveLength(5);
    for (const query of FRESH_TURNS) {
      expect(
        screen.getByRole('button', { name: `Inspect: ${query}` }),
      ).toBeEnabled();
    }

    // The controls read out while collapsed and only the editing is behind
    // the disclosure, so the turns above stay the loudest thing in the rail.
    expect(
      screen.getByText('Edit controls').closest('details'),
    ).not.toHaveAttribute('open');
    expect(screen.getByText('Response mode')).not.toBeVisible();
    const readout = screen.getByText('Orchestration').closest('dl');
    expect(readout).not.toBeNull();
    expect(within(readout!).getByText('Dispatcher')).toBeInTheDocument();
    expect(within(readout!).getByText('Balanced')).toBeInTheDocument();
    // No persona is selected in this case, so the profile row says so rather
    // than reading "Off" as though it were a choice.
    expect(within(readout!).getByText('Select a persona')).toBeInTheDocument();
    // Readout dd + collapsed toggle label + collapsed session facts.
    expect(screen.getAllByText('Dispatcher')).toHaveLength(3);
    expect(screen.getByTestId('shopper-answer-sparkle')).toHaveClass(
      'observatory-agent-sparkle',
    );
    expect(
      screen.queryByRole('button', { name: 'Graph' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText('Grounded products from this turn will appear here.'),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText('Captured SQL')).not.toBeInTheDocument();
  });

  it('keeps the idle ledger and metrics honest before a run', () => {
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    expect(
      screen.queryByRole('heading', { name: 'Execution summary' }),
    ).not.toBeInTheDocument();
    expect(
      within(tracePanel(container)).getByText(
        'Select a guided request to populate the live trace.',
      ),
    ).toBeInTheDocument();
    expect(
      container.querySelectorAll('.observatory-trace-node'),
    ).toHaveLength(6);

    // Every metric reads "-" rather than 0, so an untouched page claims nothing.
    const metrics = screen.getByText('Elapsed').closest('dl');
    expect(metrics).not.toBeNull();
    expect(tracePanel(container)).toContainElement(metrics);
    expect(within(metrics!).getAllByText('-')).toHaveLength(4);
  });

  it('runs the real chat stream and renders only emitted evidence', async () => {
    mocks.sendChatMessageStreaming.mockImplementation(
      async (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) => {
        onUpdate({
          type: 'intent_signal',
          intent: 'recommendation',
          classifier: 'deterministic',
          response_mode: 'balanced',
          model_family: 'opus',
          model_id: 'global.anthropic.claude-opus-4-6-v1',
        });
        onUpdate({
          type: 'skill_routing',
          routing: {
            loaded_skills: ['resort-styling'],
            considered: [{ name: 'resort-styling' }],
            elapsed_ms: 42,
          },
        });
        onUpdate({
          type: 'agent_step',
          agent: 'Orchestrator',
          action: 'Analyzing query',
          status: 'in_progress',
        });
        onUpdate({
          type: 'tool_call',
          tool: 'search_products',
          status: 'executing',
        });
        onUpdate({
          type: 'content_delta',
          delta: 'I found a light linen option for the trip.',
        });
        onUpdate({
          type: 'product',
          product: {
            productId: 7,
            name: 'Pellier Linen Shirt',
            price: 128,
            category: 'Linen',
            imgurl: '/products/fresh-pellier-linen-shirt.png',
          },
        });
        onUpdate({
          type: 'db_queries',
          queries: [
            {
              op: 'select',
              table: 'product_catalog',
              sql: 'SELECT name, price FROM pellier.product_catalog LIMIT 12',
              duration_ms: 18,
            },
          ],
        });
        onUpdate({
          type: 'agent_step',
          agent: 'Orchestrator',
          action: 'Done',
          status: 'completed',
        });
        onUpdate({
          type: 'complete',
          response: {
            response: 'I found a light linen option for the trip.',
            products: [],
            rail: 'in-process',
            orchestration: {
              pattern: 'dispatcher',
              route: 'recommendation',
              router: 'deterministic',
            },
          },
        });
        return {
          response: 'I found a light linen option for the trip.',
          products: [],
          suggestions: [],
        };
      },
    );

    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);

    await waitFor(() => {
      expect(mocks.sendChatMessageStreaming).toHaveBeenCalledWith(
        FRESH_TURNS[0],
        [],
        expect.any(Function),
        undefined,
        false,
        null,
        'dispatcher',
        'balanced',
      );
    });

    expect(await screen.findByText('Pellier Linen Shirt')).toBeInTheDocument();
    expect(screen.getByText('Recommended result')).toBeInTheDocument();
    expect(screen.getByText('Best match')).toBeInTheDocument();
    expect(
      screen.getByText('First recommendation from this turn'),
    ).toBeInTheDocument();
    expect(screen.queryByText('Curated pairings')).not.toBeInTheDocument();
    expect(
      screen.getByText('I found a light linen option for the trip.'),
    ).toBeInTheDocument();
    expect(
      within(tracePanel(container)).getByText('search_products'),
    ).toBeInTheDocument();
    expect(screen.getByText('Recommendation')).toBeInTheDocument();
    expect(screen.getByText('Claude Opus 4.6')).toBeInTheDocument();
    expect(screen.getByText('Routing decision')).toBeInTheDocument();
    expect(screen.getByText('Deterministic')).toBeInTheDocument();
    expect(
      screen.getByText('global.anthropic.claude-opus-4-6-v1'),
    ).toBeInTheDocument();
    expect(screen.getByText('In process')).toBeInTheDocument();
    expect(
      screen.getByText('Dispatcher / Recommendation'),
    ).toBeInTheDocument();
    expect(
      within(tracePanel(container)).getByRole('heading', {
        name: 'SELECT / product_catalog',
      }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Captured SQL')).toHaveTextContent(
      /SELECT name, price\s+FROM pellier\.product_catalog\s+LIMIT 12/,
    );
    const sqlReceipt = screen
      .getByText('Aurora SQL receipt')
      .closest('.observatory-proof-block');
    expect(sqlReceipt).not.toBeNull();
    const sqlReceiptElement = sqlReceipt as HTMLElement;
    expect(within(sqlReceiptElement).getByText('db_queries')).toBeInTheDocument();
    expect(within(sqlReceiptElement).getByText('None')).toBeInTheDocument();
    expect(within(sqlReceiptElement).getByText('Completed')).toBeInTheDocument();
    expect(
      within(sqlReceiptElement).getByRole('button', {
        name: 'Copy captured SQL',
      }),
    ).toBeInTheDocument();
    const proofSummary = screen.getByRole('status', {
      name: 'Run proof summary',
    });
    expect(within(proofSummary).getByText('Completed')).toBeInTheDocument();
    expect(proofSummary).toHaveTextContent('Evidence captured');
    expect(proofSummary).toHaveTextContent(
      '4 events. 1 agent. 1 SQL query. 1 product.',
    );

    const metrics = screen.getByText('Elapsed').closest('dl');
    expect(metrics).not.toBeNull();
    expect(within(metrics!).getByText('SQL')).toBeInTheDocument();
    expect(within(metrics!).getAllByText('1')).toHaveLength(2);
    expect(
      tracePanel(container).querySelector('[data-current="true"]'),
    ).not.toBeInTheDocument();
  });

  it('lights and follows only the latest evidence row while a run is active', async () => {
    let finishRun = () => {};
    mocks.sendChatMessageStreaming.mockImplementation(
      (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) =>
        new Promise((resolve) => {
          onUpdate({
            type: 'skill_routing',
            routing: {
              loaded_skills: ['resort-styling'],
              considered: [{ name: 'resort-styling' }],
              elapsed_ms: 21,
            },
          });
          finishRun = () =>
            resolve({
              response: 'Finished response',
              products: [],
              suggestions: [],
            });
        }),
    );

    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);

    await waitFor(() => {
      const current = tracePanel(container).querySelector(
        '.observatory-trace-step[data-current="true"]',
      );
      expect(current).toBeInTheDocument();
      expect(current).toHaveTextContent('Skill routing');
      expect(
        tracePanel(container).querySelector(
          '.observatory-trace-progress',
        ),
      ).toBeInTheDocument();
    });

    finishRun();

    await waitFor(() => {
      expect(
        tracePanel(container).querySelector('[data-current="true"]'),
      ).not.toBeInTheDocument();
    });
  });

  it('keeps rich streamed prose when completion text is materially shorter', async () => {
    const streamed =
      'I found three linen layers that work together: a camp shirt for warm afternoons, an overshirt for evenings, and drawstring trousers for travel days.';
    const fallback = 'Here are some great options!';
    mocks.sendChatMessageStreaming.mockImplementation(
      async (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) => {
        onUpdate({ type: 'content_delta', delta: streamed });
        onUpdate({
          type: 'complete',
          response: { response: fallback, products: [] },
        });
        return { response: fallback, products: [], suggestions: [] };
      },
    );

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);

    expect(await screen.findByText(streamed)).toBeInTheDocument();
    expect(screen.queryByText(fallback)).not.toBeInTheDocument();
  });

  it('offers a retry after a failed turn and reruns the same request', async () => {
    mocks.sendChatMessageStreaming
      .mockRejectedValueOnce(new Error('Temporary stream failure'))
      .mockResolvedValueOnce({
        response: 'Recovered response',
        products: [],
        suggestions: [],
      });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);

    expect(
      await screen.findByText('Temporary stream failure'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('status', { name: 'Run proof summary' }),
    ).toHaveTextContent(
      'Turn 1 needs attention',
    );

    await user.click(screen.getByRole('button', { name: 'Retry turn' }));

    await waitFor(() => {
      expect(mocks.sendChatMessageStreaming).toHaveBeenCalledTimes(2);
    });
    expect(mocks.sendChatMessageStreaming.mock.calls[1][0]).toBe(FRESH_TURNS[0]);
    expect(await screen.findByText('Recovered response')).toBeInTheDocument();
  });

  it('applies the selected live configuration to the request', async () => {
    mocks.sendChatMessageStreaming.mockResolvedValue({
      response: 'Configured response',
      products: [],
      suggestions: [],
    });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await user.click(screen.getByText('Edit controls'));
    await user.click(screen.getByRole('radio', { name: 'Graph' }));
    await user.click(screen.getByRole('radio', { name: 'Editorial' }));
    await user.click(
      screen.getByRole('switch', { name: /Input safety inspection/i }),
    );
    await inspectTurn(user, FRESH_TURNS[0]);

    await waitFor(() => {
      expect(mocks.sendChatMessageStreaming).toHaveBeenCalledWith(
        FRESH_TURNS[0],
        [],
        expect.any(Function),
        undefined,
        true,
        null,
        'graph',
        'editorial',
      );
    });
  });

  it('keeps shopper and operator writes on Dispatcher', async () => {
    mocks.persona = {
      id: 'theo',
      display_name: 'Theo',
      customer_id: 'CUST-THEO',
    };
    mocks.sendChatMessageStreaming.mockResolvedValue({
      response: 'Operator response',
      products: [],
      suggestions: [],
    });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await user.click(screen.getByText('Edit controls'));
    await user.click(
      screen.getByRole('radio', { name: 'Agents-as-Tools' }),
    );

    expect(
      screen.getByRole('button', {
        name: `Inspect: ${PERSONA_HERO_PILLS.theo[3]}`,
      }),
    ).toBeDisabled();
    // A write op off Dispatcher is marked unavailable with `aria-disabled`
    // rather than `disabled`, so it stays focusable and the reason below it is
    // reachable. `disabled` plus a `title` was unreachable to a keyboard or
    // screen-reader user, who got a dead control and no explanation.
    const blockedWrite = screen.getByRole('button', {
      name: /Restock product 37/i,
    });
    expect(blockedWrite).toHaveAttribute('aria-disabled', 'true');
    const reasonId = blockedWrite.getAttribute('aria-describedby');
    expect(reasonId).toBeTruthy();
    expect(document.getElementById(reasonId as string)).toHaveTextContent(
      /Writes run only through Dispatcher/i,
    );

    // Marked unavailable must also mean it does nothing when clicked.
    const callsBefore = mocks.sendChatMessageStreaming.mock.calls.length;
    await user.click(blockedWrite);
    expect(mocks.sendChatMessageStreaming.mock.calls).toHaveLength(callsBefore);

    await user.click(
      screen.getByRole('button', { name: /Review low stock/i }),
    );
    await waitFor(() => {
      expect(mocks.sendChatMessageStreaming).toHaveBeenLastCalledWith(
        'Which pieces are running low?',
        [],
        expect.any(Function),
        undefined,
        false,
        null,
        'agents_as_tools',
        'balanced',
      );
    });

    await user.click(screen.getByRole('radio', { name: 'Dispatcher' }));
    await user.click(
      screen.getByRole('button', { name: /Restock product 37/i }),
    );
    await waitFor(() => {
      expect(mocks.sendChatMessageStreaming).toHaveBeenLastCalledWith(
        'Restock product 37 by 12 units.',
        [],
        expect.any(Function),
        undefined,
        false,
        null,
        'dispatcher',
        'balanced',
      );
    });
  });

  it('renders live memory and guardrail receipts in the journey', async () => {
    // Persona set below, so this run uses Marco's curated turns, not fresh's.
    mocks.persona = {
      id: 'marco',
      display_name: 'Marco',
      customer_id: 'CUST-MARCO',
    };
    mocks.sendChatMessageStreaming.mockImplementation(
      async (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) => {
        onUpdate({
          type: 'guardrail_decision',
          guardrail: {
            allowed: true,
            action: 'NONE',
            violations: 0,
            mode: 'pass-through',
            enforced: false,
          },
        });
        onUpdate({
          type: 'aurora_profile_context',
          profile: {
            source: 'aurora',
            customer_id: 'CUST-MARCO',
            facts_available: 3,
            orders_available: 1,
            available: true,
          },
        });
        onUpdate({
          type: 'agentcore_memory',
          memory: {
            source: 'agentcore-memory',
            turns_loaded: 2,
            turns_persisted: 2,
            namespace_scope: 'verified-principal',
          },
        });
        onUpdate({
          type: 'complete',
          response: {
            response: 'A grounded response.',
            products: [],
            rail: 'in-process',
            orchestration: {
              pattern: 'dispatcher',
              route: 'recommendation',
              router: 'deterministic',
            },
          },
        });
        return {
          response: 'A grounded response.',
          products: [],
          suggestions: [],
        };
      },
    );

    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await user.click(screen.getByText('Edit controls'));
    await user.click(
      screen.getByRole('switch', { name: /Input safety inspection/i }),
    );
    // Marco is the active persona here, so the card offers Marco's turns.
    await inspectTurn(user, PERSONA_HERO_PILLS.marco[0]);

    const trace = () => within(tracePanel(container));
    await waitFor(() =>
      expect(
        trace().getByText('3 profile facts and 1 past order available'),
      ).toBeInTheDocument(),
    );
    expect(
      trace().getByText('2 prior turns read; 2 new turns persisted'),
    ).toBeInTheDocument();
    expect(
      trace().getByText('Request evaluated before agent execution'),
    ).toBeInTheDocument();
    expect(
      trace().getByText('pass-through / NONE / inspect only'),
    ).toBeInTheDocument();
    expect(screen.getByText('Dispatcher / Recommendation')).toBeInTheDocument();
  });

  it('promotes the first named product above its curated pairings', async () => {
    mocks.sendChatMessageStreaming.mockImplementation(
      async (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) => {
        onUpdate({
          type: 'product',
          product: {
            productId: 20,
            name: 'Merino Travel Socks',
            price: 38,
          },
        });
        onUpdate({
          type: 'product',
          product: {
            productId: 11,
            name: 'Italian Linen Camp Shirt',
            price: 228,
          },
        });
        onUpdate({
          type: 'product',
          product: {
            productId: 34,
            name: 'Soft Leather Travel Pouch',
            price: 96,
          },
        });
        onUpdate({
          type: 'complete',
          response: {
            response:
              'Lead with the Italian Linen Camp Shirt, then add the Merino Travel Socks and Soft Leather Travel Pouch for the flight.',
            products: [],
            rail: 'in-process',
          },
        });
        return {
          response:
            'Lead with the Italian Linen Camp Shirt, then add the Merino Travel Socks and Soft Leather Travel Pouch for the flight.',
          products: [],
          suggestions: [],
        };
      },
    );

    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);
    await screen.findByText('Italian Linen Camp Shirt');

    expect(screen.getByText('Best match')).toBeInTheDocument();
    expect(screen.getByText('Curated pairings')).toBeInTheDocument();
    expect(screen.getByText('2 supporting pieces')).toBeInTheDocument();
    expect(
      container.querySelector('[data-product-role="best-match"] h4'),
    ).toHaveTextContent('Italian Linen Camp Shirt');
    const pairingNames = Array.from(
      container.querySelectorAll('[data-product-role="pairing"] h4'),
    ).map((heading) => heading.textContent);
    expect(pairingNames).toEqual([
      'Merino Travel Socks',
      'Soft Leather Travel Pouch',
    ]);

    const productNames = Array.from(
      container.querySelectorAll('.observatory-product-copy h4'),
    ).map((heading) => heading.textContent);
    expect(productNames).toEqual([
      'Italian Linen Camp Shirt',
      'Merino Travel Socks',
      'Soft Leather Travel Pouch',
    ]);
  });

  // A representative turn from each persona must stay byte-for-byte aligned.
  it.each([
    ['Marco', 'marco', 'CUST-MARCO'],
    ['Anna', 'anna', 'CUST-ANNA'],
    ['Theo', 'theo', 'CUST-THEO'],
  ] as const)(
    'sends %s their canonical curated turn verbatim, with live memory',
    async (displayName, id, customerId) => {
      mocks.persona = {
        id,
        display_name: displayName,
        customer_id: customerId,
      };
      mocks.sendChatMessageStreaming.mockResolvedValue({
        response: 'Live response',
        products: [],
        suggestions: [],
      });

      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <ObservatoryWorkbench />
        </MemoryRouter>,
      );

      const turn4 = PERSONA_HERO_PILLS[id][3];
      expect(mocks.sendChatMessageStreaming).not.toHaveBeenCalled();
      await inspectTurn(user, turn4);

      await waitFor(() => {
        expect(mocks.sendChatMessageStreaming).toHaveBeenCalledWith(
          turn4,
          [],
          expect.any(Function),
          undefined,
          false,
          customerId,
          'dispatcher',
          'balanced',
        );
      });
    },
  );

  it("keeps Marco's warehouse turn aligned with workshop content", () => {
    mocks.persona = {
      id: 'marco',
      display_name: 'Marco',
      customer_id: 'CUST-MARCO',
    };
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('button', {
        name: `Inspect: ${PERSONA_HERO_PILLS.marco[3]}`,
      }),
    ).toBeInTheDocument();
  });

  /**
   * A run that emits two Aurora receipts, so per-receipt disclosure, the bulk
   * control, and the claim-to-event link all have something real to act on.
   */
  function mockTwoReceiptRun() {
    mocks.sendChatMessageStreaming.mockImplementation(
      async (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) => {
        onUpdate({
          type: 'intent_signal',
          intent: 'recommendation',
          classifier: 'deterministic',
          response_mode: 'balanced',
          model_family: 'opus',
          model_id: 'global.anthropic.claude-opus-4-6-v1',
        });
        onUpdate({
          type: 'skill_routing',
          routing: { loaded_skills: ['resort-styling'], elapsed_ms: 30 },
        });
        onUpdate({ type: 'tool_call', tool: 'search_products', status: 'executing' });
        onUpdate({
          type: 'product',
          product: {
            productId: 7,
            name: 'Pellier Linen Shirt',
            price: 128,
            category: 'Linen',
          },
        });
        onUpdate({
          type: 'db_queries',
          queries: [
            {
              op: 'select',
              table: 'product_catalog',
              sql: 'SELECT name FROM pellier.product_catalog WHERE name ILIKE %s',
              duration_ms: 21,
            },
            {
              op: 'insert',
              table: 'tool_audit',
              sql: 'INSERT INTO pellier.tool_audit (tool) VALUES (%s)',
              duration_ms: 9,
            },
          ],
        });
        onUpdate({
          type: 'complete',
          response: {
            response: 'A grounded linen answer.',
            products: [],
            rail: 'in-process',
            orchestration: {
              pattern: 'dispatcher',
              route: 'recommendation',
              router: 'deterministic',
            },
          },
        });
        return {
          response: 'A grounded linen answer.',
          products: [],
          suggestions: [],
        };
      },
    );
  }

  it('discloses each Aurora receipt independently and in bulk', async () => {
    mockTwoReceiptRun();
    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);

    // The newest receipt opens itself so a finished run shows proof without a
    // click; the earlier one stays closed.
    await waitFor(() =>
      expect(
        screen.getByRole('button', {
          name: 'Hide the Aurora receipt for INSERT / tool_audit',
        }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole('button', {
        name: 'Show the Aurora receipt for SELECT / product_catalog',
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByLabelText('Captured SQL')).toHaveLength(1);

    // Bulk disclosure exists only because there is more than one receipt, and
    // it offers to expand while any row is still closed.
    await user.click(screen.getByRole('button', { name: /Expand all/ }));
    expect(screen.getAllByLabelText('Captured SQL')).toHaveLength(2);

    // Collapse all closes every row, including the one the default opened.
    await user.click(screen.getByRole('button', { name: /Collapse all/ }));
    expect(screen.queryByLabelText('Captured SQL')).not.toBeInTheDocument();

    // A single row still discloses on its own afterwards.
    await user.click(
      screen.getByRole('button', {
        name: 'Show the Aurora receipt for SELECT / product_catalog',
      }),
    );
    expect(screen.getAllByLabelText('Captured SQL')).toHaveLength(1);

    // The footer counts what state holds, not a hardcoded total: routing,
    // one tool call, and the two Aurora receipts.
    expect(
      tracePanel(container).querySelector('.observatory-append-only')
        ?.textContent,
    ).toBe('Append only. 4 events, 2 SQL receipts.');
  });

  it('opens the ledger event a verified claim rests on', async () => {
    mockTwoReceiptRun();
    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);
    await screen.findByText('Pellier Linen Shirt');

    // Three claims, and every one resolves to an emitted event.
    expect(
      screen.getByText('3 of 3 linked to a ledger event'),
    ).toBeInTheDocument();
    const claimLinks = screen.getAllByRole('button', { name: /Open event/ });
    expect(claimLinks).toHaveLength(3);

    // The route claim points at the routing event, so opening it marks that
    // row rather than any other.
    const routeClaim = screen
      .getByText('Dispatcher route')
      .closest('li') as HTMLElement;
    await user.click(
      within(routeClaim).getByRole('button', { name: /Open event/ }),
    );
    const linked = tracePanel(container).querySelector(
      '.observatory-trace-step[data-linked="true"]',
    );
    expect(linked).toHaveTextContent('Skill routing');
  });

  it('builds the rationale only from signals the turn emitted', async () => {
    mockTwoReceiptRun();
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    // Nothing has run, so there is no rationale to show.
    expect(
      screen.queryByRole('heading', { name: 'Why this answer' }),
    ).not.toBeInTheDocument();

    await inspectTurn(user, FRESH_TURNS[0]);

    expect(
      await screen.findByRole('heading', { name: 'Why this answer' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Classified as a Recommendation request by the deterministic router, then composed by Claude Opus 4.6.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Dispatched through the Dispatcher pattern to Recommendation.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Grounded by the tool search_products.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Aurora returned 2 query receipts on the In process rail.'),
    ).toBeInTheDocument();
    // The provenance line keeps this from reading as the model's own account.
    expect(
      screen.getByText("Assembled from this turn's emitted events."),
    ).toBeInTheDocument();
  });

  it('offers no bulk disclosure when a run captured a single receipt', async () => {
    mocks.sendChatMessageStreaming.mockImplementation(
      async (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) => {
        onUpdate({
          type: 'db_queries',
          queries: [
            {
              op: 'select',
              table: 'product_catalog',
              sql: 'SELECT 1',
              duration_ms: 4,
            },
          ],
        });
        return { response: 'One receipt.', products: [], suggestions: [] };
      },
    );

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);
    await screen.findByLabelText('Captured SQL');

    expect(
      screen.queryByRole('button', { name: /Expand all/ }),
    ).not.toBeInTheDocument();
  });

  it('keeps an SSE failure in the error state', async () => {
    mocks.sendChatMessageStreaming.mockImplementation(
      async (
        _query: string,
        _history: unknown[],
        onUpdate: (event: unknown) => void,
      ) => {
        onUpdate({
          type: 'error',
          error: 'Agent execution timed out',
        });
        throw new Error('Agent execution timed out');
      },
    );

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    await inspectTurn(user, FRESH_TURNS[0]);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Agent run did not complete');
    expect(alert).toHaveTextContent('Agent execution timed out');
    expect(screen.getAllByText('Error')).toHaveLength(1);
    expect(screen.queryByText('Live run complete')).not.toBeInTheDocument();
  });

  it('stops restating the controls once you open the editor', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    // Collapsed, the readout IS the summary of what a run will use.
    expect(screen.getByText('Orchestration')).toBeInTheDocument();

    await user.click(screen.getByText('Edit controls'));

    // Open, it was five facts repeated directly above the five controls that
    // set them. The controls are the readout now.
    expect(screen.queryByText('Orchestration')).toBeNull();
    expect(screen.getByText('Orchestration pattern')).toBeVisible();
  });

  it('states one setting once per section', async () => {
    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    const controls = container.querySelector('.observatory-run-controls');
    expect(controls).not.toBeNull();

    // Visible occurrences, not DOM occurrences: a closed `details` keeps its
    // controls in the document. Response mode used to be stated three times in
    // this one section — a header badge, a readout row, and the control — and
    // two of those were visible at once.
    // jsdom's checkVisibility does not model `details`, so ask directly.
    const visibleBalanced = () =>
      within(controls as HTMLElement)
        .getAllByText(/^Balanced$/)
        .filter((node) => node.closest('details:not([open])') === null);

    expect(visibleBalanced()).toHaveLength(1);

    await user.click(screen.getByText('Edit controls'));
    expect(visibleBalanced()).toHaveLength(1);
  });

  it('keeps operator runs out of the edit disclosure', () => {
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    const operators = container.querySelector('.observatory-operator-runs');
    expect(operators).not.toBeNull();

    // Operator runs has its own disclosure, named for what it does. What must
    // never come back is it being nested inside "Edit controls", where running
    // a turn hid behind a word that promises settings.
    expect(operators?.tagName).toBe('DETAILS');
    expect(operators?.closest('.observatory-edit-controls')).toBeNull();
    expect(operators?.closest('[hidden]')).toBeNull();
    expect(
      within(operators as HTMLElement).getByText('Operator runs'),
    ).toBeInTheDocument();
    // Not `toBeVisible`: the enclosing panel is a framer-motion element with
    // `initial={{ opacity: 0 }}`, which jsdom reports as invisible regardless
    // of the animation. Reachable and operable is the real claim.
    expect(
      within(operators as HTMLElement).getByRole('button', {
        name: /Review low stock/i,
      }),
    ).toBeEnabled();
  });

  it('rests as five facts and two closed pills, nothing more', () => {
    const { container } = render(
      <MemoryRouter>
        <ObservatoryWorkbench />
      </MemoryRouter>,
    );

    const controls = container.querySelector('.observatory-run-controls');
    expect(controls).not.toBeNull();
    const panel = controls as HTMLElement;

    // The readout is the resting state: the five settings a run will use.
    const readout = panel.querySelector('.observatory-run-readout');
    expect(readout).not.toBeNull();
    const facts = Array.from(readout!.querySelectorAll('dt')).map(
      (node) => node.textContent,
    );
    expect(facts).toEqual([
      'Response',
      'Orchestration',
      'Aurora profile',
      'Input safety inspection',
      'Live trace',
    ]);

    // Everything else is behind a closed disclosure. Both start closed, so the
    // panel opens as a readout and two pills rather than a wall of controls.
    const disclosures = Array.from(panel.querySelectorAll('details'));
    expect(disclosures).toHaveLength(2);
    for (const disclosure of disclosures) {
      expect(disclosure.open).toBe(false);
    }
    expect(
      disclosures.map((d) => d.querySelector('summary strong')?.textContent),
    ).toEqual(['Edit controls', 'Operator runs']);

    // No third heading or paragraph competing with the readout.
    expect(panel.querySelectorAll('h3')).toHaveLength(0);
  });
});
