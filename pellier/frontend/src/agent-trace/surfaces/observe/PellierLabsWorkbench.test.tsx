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

import PellierLabsWorkbench from './PellierLabsWorkbench';

describe('Pellier Labs live agent workbench', () => {
  beforeEach(() => {
    mocks.sendChatMessageStreaming.mockReset();
    mocks.persona = null;
  });

  it('starts as an empty live runner without replay or fixture content', () => {
    render(
      <MemoryRouter>
        <PellierLabsWorkbench />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('heading', { name: 'Pellier Labs' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Shopper request')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Run agent' })).toBeDisabled();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.queryByText(/recorded/i)).not.toBeInTheDocument();
    expect(screen.getAllByRole('switch')).toHaveLength(3);
    expect(
      screen.getByRole('button', {
        name: 'Find a resort-ready linen shirt under $200',
      }),
    ).toBeEnabled();
    expect(screen.getByText('Agent configuration')).toBeInTheDocument();
    expect(screen.getByText('Awaiting catalog results')).toBeInTheDocument();
    expect(screen.queryByLabelText('Captured SQL')).not.toBeInTheDocument();
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
          model_id: 'global.anthropic.claude-opus-5',
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
          tool: 'find_pieces',
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
              router: 'model',
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
    render(
      <MemoryRouter>
        <PellierLabsWorkbench />
      </MemoryRouter>,
    );

    const input = screen.getByLabelText('Shopper request');
    await user.type(input, 'What works for a winter resort trip?');
    await user.click(screen.getByRole('button', { name: 'Run agent' }));

    await waitFor(() => {
      expect(mocks.sendChatMessageStreaming).toHaveBeenCalledWith(
        'What works for a winter resort trip?',
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
    expect(screen.getByText('Top pick')).toBeInTheDocument();
    expect(screen.getByText('Live catalog edit')).toBeInTheDocument();
    expect(screen.getByText('1 piece')).toBeInTheDocument();
    expect(
      screen.getByText('I found a light linen option for the trip.'),
    ).toBeInTheDocument();
    expect(screen.getByText('find_pieces')).toBeInTheDocument();
    expect(screen.getByText('Recommendation')).toBeInTheDocument();
    expect(screen.getByText('Claude Opus 5')).toBeInTheDocument();
    expect(screen.getByText('In process')).toBeInTheDocument();
    expect(
      screen.getByText('Dispatcher · Recommendation'),
    ).toBeInTheDocument();
    expect(screen.getByText('SELECT · product_catalog')).toBeInTheDocument();
    expect(screen.getByLabelText('Captured SQL')).toHaveTextContent(
      'SELECT name, price FROM pellier.product_catalog LIMIT 12',
    );
    expect(screen.getAllByText('Completed')).toHaveLength(1);

    const metrics = screen.getByText('Journey steps').closest('dl');
    expect(metrics).not.toBeNull();
    expect(within(metrics!).getByText('Captured SQL')).toBeInTheDocument();
    expect(within(metrics!).getAllByText('1')).toHaveLength(2);
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
        <PellierLabsWorkbench />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('Shopper request'), 'Build a linen edit');
    await user.click(screen.getByRole('button', { name: 'Run agent' }));

    expect(await screen.findByText(streamed)).toBeInTheDocument();
    expect(screen.queryByText(fallback)).not.toBeInTheDocument();
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
        <PellierLabsWorkbench />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: 'Editorial' }));
    await user.click(
      screen.getByRole('switch', { name: /Input safety inspection/i }),
    );
    await user.type(screen.getByLabelText('Shopper request'), 'Find a gift');
    await user.click(screen.getByRole('button', { name: 'Run agent' }));

    await waitFor(() => {
      expect(mocks.sendChatMessageStreaming).toHaveBeenCalledWith(
        'Find a gift',
        [],
        expect.any(Function),
        undefined,
        true,
        null,
        'dispatcher',
        'editorial',
      );
    });
  });

  it('renders live memory and guardrail receipts in the journey', async () => {
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
    render(
      <MemoryRouter>
        <PellierLabsWorkbench />
      </MemoryRouter>,
    );

    await user.click(
      screen.getByRole('switch', { name: /Input safety inspection/i }),
    );
    await user.type(screen.getByLabelText('Shopper request'), 'Build an edit');
    await user.click(screen.getByRole('button', { name: 'Run agent' }));

    expect(
      await screen.findByText('3 profile facts and 1 past order available'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('2 prior turns read; 2 new turns persisted'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Request evaluated before agent execution'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('pass-through · NONE · inspect only'),
    ).toBeInTheDocument();
    expect(screen.getByText('Dispatcher · Recommendation')).toBeInTheDocument();
  });

  it('features products in the order named by the live response', async () => {
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
          type: 'complete',
          response: {
            response:
              'Lead with the Italian Linen Camp Shirt, then add the Merino Travel Socks for the flight.',
            products: [],
            rail: 'in-process',
          },
        });
        return {
          response:
            'Lead with the Italian Linen Camp Shirt, then add the Merino Travel Socks for the flight.',
          products: [],
          suggestions: [],
        };
      },
    );

    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <PellierLabsWorkbench />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('Shopper request'), 'Build an edit');
    await user.click(screen.getByRole('button', { name: 'Run agent' }));
    await screen.findByText('Italian Linen Camp Shirt');

    const productNames = Array.from(
      container.querySelectorAll('.pellier-labs-product-copy h3'),
    ).map((heading) => heading.textContent);
    expect(productNames).toEqual([
      'Italian Linen Camp Shirt',
      'Merino Travel Socks',
    ]);
  });

  it.each([
    [
      'Marco',
      'marco',
      'CUST-MARCO',
      'Build a resort edit around the linen pieces I already own',
    ],
    [
      'Anna',
      'anna',
      'CUST-ANNA',
      'Find a housewarming gift under $100 that feels special',
    ],
    [
      'Theo',
      'theo',
      'CUST-THEO',
      'How should I care for the stoneware I bought?',
    ],
  ])(
    'runs the %s persona pill immediately with live profile context',
    async (displayName, id, customerId, prompt) => {
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
          <PellierLabsWorkbench />
        </MemoryRouter>,
      );

      await user.click(screen.getByRole('button', { name: prompt }));

      await waitFor(() => {
        expect(mocks.sendChatMessageStreaming).toHaveBeenCalledWith(
          prompt,
          [],
          expect.any(Function),
          undefined,
          false,
          customerId,
          'dispatcher',
          'balanced',
        );
      });
      expect(screen.getByLabelText('Shopper request')).toHaveValue(prompt);
    },
  );

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
        <PellierLabsWorkbench />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('Shopper request'), 'Find a gift');
    await user.click(screen.getByRole('button', { name: 'Run agent' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Agent run did not complete');
    expect(alert).toHaveTextContent('Agent execution timed out');
    expect(screen.getAllByText('Error')).toHaveLength(1);
    expect(screen.queryByText('Live run complete')).not.toBeInTheDocument();
  });
});
