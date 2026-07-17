import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
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
        detail: 'Catalog 1,000 products, warehouse 120 rows, audit ledger 7 rows.',
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
    governedReceiptPresent: true,
    latestGovernedReceiptId: 505,
    governedPrincipalId: 'CUST-MARCO',
    governedPrincipalLabel: 'Marco (Cognito JWT)',
    governedDecision: 'ALLOW',
    governedTool: 'process_return',
    governedArgs: { customer_id: 'theo', product_id: '37', reason: 'damaged' },
    gatewayAuditPresent: true,
    latestGatewayAuditId: 303,
  },
  cards: [
    {
      id: 'marco-floor-check',
      lab: 'Core Lab 1: Build and Trace',
      title: 'Wire Marco to floor_check',
      status: 'complete',
      required: true,
      surface: 'Code Editor + Boutique',
      summary: "The Stock Keeper tool is wired and Marco's warehouse turn leaves a floor_check audit row.",
      evidence: ['Latest floor_check row: audit_id 101'],
      fallback: {
        label: 'Terminal fallback',
        command: 'curl -s http://localhost:8000/api/agent/chat',
      },
      links: [{ label: 'Tools', to: '/atelier/tools' }],
    },
    {
      id: 'audit-ledger',
      lab: 'Core Lab 3: Query Evidence',
      title: 'Prove the audit trail in Aurora',
      status: 'complete',
      required: true,
      surface: 'Aurora PostgreSQL',
      summary: 'The live tool_audit ledger contains the expected identity, tool, and outcome.',
      evidence: ['Latest audit row: audit_id 303'],
      fallback: {
        label: 'SQL fallback',
        command: 'SELECT audit_id, caller, tool_name FROM pellier.tool_audit ORDER BY audit_id DESC;',
      },
      links: [{ label: 'Sessions', to: '/atelier/sessions' }],
    },
    {
      id: 'managed-rail',
      lab: 'Core Lab 4: Enforce Policy',
      title: 'Fast-finisher managed rail',
      status: 'available',
      required: false,
      surface: 'Runtime receipt',
      summary: 'After a managed Runtime turn, the receipt shows passthrough.',
      evidence: ['JWT passthrough: true'],
      fallback: {
        label: 'Terminal fallback',
        command: 'curl -N http://localhost:8000/api/agent/chat',
      },
      links: [{ label: 'Sessions', to: '/atelier/sessions' }],
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ProofBoard', () => {
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

    expect(await screen.findByText('Evidence checkpoints, in lab order.')).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Aurora PostgreSQL' }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText('AgentCore Gateway')).toBeInTheDocument();
    expect(screen.getByText('gateway-mcp')).toBeInTheDocument();
    expect(screen.getByText('Marco (Cognito JWT)')).toBeInTheDocument();
    expect(screen.getByText('ALLOW')).toBeInTheDocument();
    expect(screen.getByTestId('proof-card-marco-floor-check')).toHaveTextContent(
      'Wire Marco to floor_check',
    );
    expect(screen.getAllByText('Core Lab 1: Build and Trace')).toHaveLength(2);
    expect(screen.getAllByText('Core Lab 4: Enforce Policy')).toHaveLength(2);
    expect(screen.queryByText(/^Act (I|II|III)$/)).not.toBeInTheDocument();
    expect(screen.getByText('curl -s http://localhost:8000/api/agent/chat')).toBeInTheDocument();
  });

  it('renders Gateway/Cedar DENY as a verified no-row proof', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({
          ...proofBoardPayload,
          managedReceipt: {
            ...proofBoardPayload.managedReceipt,
            governedDecision: 'DENY',
            governedPolicyName: 'workshop_final_sale_forbid',
            gatewayAuditPresent: false,
            gatewayAuditAbsenceVerified: true,
            latestGatewayAuditId: null,
            absenceCheckDetail: 'Gateway/Cedar DENY: governed receipt has no audit_id and no tool_audit row was written.',
          },
        }), {
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

    expect(await screen.findByText(/DENY via workshop_final_sale_forbid/)).toBeInTheDocument();
    expect(screen.getByText('Cedar DENY: tool target did not execute')).toBeInTheDocument();
    expect(screen.getByText('Gateway/Cedar DENY left no tool_audit row')).toBeInTheDocument();
    expect(screen.getByText(/No-row DENY is scoped to the Gateway\/Cedar rail/)).toBeInTheDocument();
  });

  it('maps card ids to Core Labs while an older local backend is still running', async () => {
    const cards = proofBoardPayload.cards.map(({ lab: _lab, ...card }) => card);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ ...proofBoardPayload, cards }), {
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

    expect(await screen.findAllByText('Core Lab 1: Build and Trace')).toHaveLength(2);
    expect(screen.getAllByText('Core Lab 4: Enforce Policy')).toHaveLength(2);
  });

  it('renders Audit Proof as a focused Core Lab 3 evidence view', async () => {
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
      <MemoryRouter initialEntries={['/atelier/audit-proof']}>
        <ProofBoard focusCardId="audit-ledger" />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Audit proof, row by row.')).toBeInTheDocument();
    expect(screen.getByTestId('proof-card-audit-ledger')).toHaveTextContent(
      'Prove the audit trail in Aurora',
    );
    expect(screen.getByText('SQL fallback')).toBeInTheDocument();
    expect(
      screen.getByText(
        'SELECT audit_id, caller, tool_name FROM pellier.tool_audit ORDER BY audit_id DESC;',
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'Workshop readiness' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('proof-card-marco-floor-check')).not.toBeInTheDocument();
    expect(screen.queryByTestId('proof-card-managed-rail')).not.toBeInTheDocument();
    expect(screen.queryByText('Core Lab checkpoints')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'All checkpoints' })).toHaveAttribute(
      'href',
      '/atelier/proof-board',
    );
  });
});
