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
        'agents_as_tools',
        'balanced',
      );
    });

    expect(await screen.findByText('Pellier Linen Shirt')).toBeInTheDocument();
    expect(
      screen.getByText('I found a light linen option for the trip.'),
    ).toBeInTheDocument();
    expect(screen.getByText('find_pieces')).toBeInTheDocument();
    expect(screen.getByText('Recommendation')).toBeInTheDocument();
    expect(screen.getByText('Claude Opus 5')).toBeInTheDocument();
    expect(screen.getByText('In process')).toBeInTheDocument();
    expect(screen.getByText('SELECT · product_catalog')).toBeInTheDocument();
    expect(screen.getByLabelText('Captured SQL')).toHaveTextContent(
      'SELECT name, price FROM pellier.product_catalog LIMIT 12',
    );
    expect(screen.getAllByText('Completed')).toHaveLength(2);

    const metrics = screen.getByText('Journey steps').closest('dl');
    expect(metrics).not.toBeNull();
    expect(within(metrics!).getByText('Captured SQL')).toBeInTheDocument();
    expect(within(metrics!).getAllByText('1')).toHaveLength(2);
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

    await user.click(screen.getByRole('button', { name: 'Graph' }));
    await user.click(screen.getByRole('button', { name: 'Editorial' }));
    await user.click(
      screen.getByRole('switch', { name: /Guardrail input check/i }),
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
        'graph',
        'editorial',
      );
    });
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
    'runs the %s persona pill immediately with live memory',
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
          'agents_as_tools',
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
    expect(screen.getAllByText('Error')).toHaveLength(2);
    expect(screen.queryByText('Live run complete')).not.toBeInTheDocument();
  });
});
