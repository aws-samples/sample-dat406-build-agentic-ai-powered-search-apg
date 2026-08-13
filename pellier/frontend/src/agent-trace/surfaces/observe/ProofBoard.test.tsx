import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import ProofBoard from './ProofBoard';

const proofBoardPayload = {
  status: 'ready',
  readiness: {
    status: 'ready',
    checks: [
      {
        id: 'aurora',
        label: 'Aurora PostgreSQL',
        state: 'pass',
        detail: 'Catalog 40 products, warehouse 120 rows, audit ledger 7 rows.',
        required: true,
      },
      {
        id: 'gateway',
        label: 'AgentCore Gateway',
        state: 'pass',
        detail: 'Gateway URL configured.',
        required: true,
      },
    ],
  },
  managedReceipt: {
    present: true,
    traceKind: 'managed-runtime-receipt',
    runtime: 'agentcore-managed',
    rail: 'gateway-mcp',
    jwtPassthrough: true,
    gatewayPassthrough: true,
  },
  cards: [
    {
      id: 'marco-floor-check',
      group: 'Agent and tool evidence',
      title: 'Wire Marco to floor_check',
      status: 'complete',
      required: true,
      surface: 'Code Editor + Pellier',
      summary: "The Stock Keeper tool is wired and Marco's warehouse turn leaves a floor_check audit row.",
      evidence: ['Latest floor_check row: audit_id 101'],
      fallback: {
        label: 'Terminal fallback',
        command: 'curl -s http://localhost:8000/api/agent/chat',
      },
      links: [{ label: 'Tools', to: '/agent-trace/tools' }],
    },
    {
      id: 'managed-rail',
      group: 'Managed boundaries',
      title: 'Inspect the managed rail',
      status: 'available',
      required: false,
      surface: 'Runtime receipt',
      summary: 'After a managed Runtime turn, the receipt shows passthrough.',
      evidence: ['JWT passthrough: true'],
      fallback: {
        label: 'Terminal fallback',
        command: 'curl -N http://localhost:8000/api/agent/chat',
      },
      links: [{ label: 'Sessions', to: '/agent-trace/sessions' }],
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ProofBoard', () => {
  beforeAll(() => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
  });

  it('renders readiness checks, managed receipt, and proof card fallbacks', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify(proofBoardPayload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    render(
      <MemoryRouter>
        <ProofBoard />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Inspect evidence, then boundaries.')).toBeInTheDocument();
    expect(
      document.querySelector('.pellier-labs-flow[aria-hidden="true"] canvas'),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Aurora PostgreSQL')).toBeInTheDocument();
    });
    expect(screen.getByText('AgentCore Gateway')).toBeInTheDocument();
    expect(screen.getByText('gateway-mcp')).toBeInTheDocument();
    expect(screen.getByTestId('proof-card-marco-floor-check')).toHaveTextContent(
      'Wire Marco to floor_check',
    );
    expect(screen.getByText('curl -s http://localhost:8000/api/agent/chat')).toBeInTheDocument();
  });
});
