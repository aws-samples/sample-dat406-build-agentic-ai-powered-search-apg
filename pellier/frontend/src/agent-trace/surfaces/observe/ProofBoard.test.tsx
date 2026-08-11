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
    governedVerifiedSubject: 'cognito-sub-marco',
    governedVerifiedUsername: 'marco@example.com',
    governedIdentitySource: 'cognito_access_token',
    governedTokenFingerprint: 'abc123def456abc123def456abc123def456abc123def456abc123def456abcd',
    governedDecision: 'ALLOW',
    governedTool: 'process_return',
    governedArgs: { customer_id: 'theo', product_id: '37', reason: 'damaged' },
    gatewayAuditPresent: true,
    latestGatewayAuditId: 303,
  },
  cards: [
    {
      id: 'marco-floor-check',
      lab: 'Lab 1: Ground Answers in Live Data',
      group: 'Agent and tool evidence',
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
      links: [{ label: 'Tools', to: '/agent-trace/tools' }],
    },
    {
      id: 'audit-ledger',
      lab: 'Lab 3: Run Agents in a Managed Runtime',
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
      links: [{ label: 'Sessions', to: '/agent-trace/sessions' }],
    },
    {
      id: 'managed-rail',
      lab: 'Lab 3: Run Agents in a Managed Runtime',
      group: 'Managed boundaries',
      title: 'Prove the managed Runtime and Gateway rail',
      status: 'complete',
      required: true,
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
    expect(
      screen.getAllByText('marco@example.com via cognito_access_token').length,
    ).toBeGreaterThan(0);
    expect(screen.getByText(/sha256 abc123def456\.\.\. · subject cognito-sub-marco/)).toBeInTheDocument();
    expect(screen.getAllByText('ALLOW').length).toBeGreaterThan(0);
    expect(screen.getByTestId('governance-receipt-policy')).toHaveTextContent(
      'Was the action permitted?',
    );
    expect(screen.getByTestId('governance-receipt-execution')).toHaveTextContent(
      'What actually ran?',
    );
    expect(screen.getByTestId('governance-receipt-data')).toHaveTextContent(
      'What reached the system of record?',
    );
    expect(screen.getByTestId('proof-card-marco-floor-check')).toHaveTextContent(
      'Wire Marco to floor_check',
    );
    expect(screen.getAllByText('Lab 1: Ground Answers in Live Data')).toHaveLength(2);
    expect(screen.getAllByText('Lab 3: Run Agents in a Managed Runtime').length).toBeGreaterThan(0);
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
            governedPolicyName: 'workshop_identity_match_forbid',
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

    expect(
      (await screen.findAllByText(/DENY via workshop_identity_match_forbid/)).length,
    ).toBeGreaterThan(0);
    expect(screen.getByTestId('governance-receipt-policy')).toHaveTextContent('DENY');
    expect(screen.getByTestId('governance-receipt-execution')).toHaveTextContent(
      'stopped before target execution',
    );
    expect(screen.getByTestId('governance-receipt-data')).toHaveTextContent(
      'no linked tool_audit row',
    );
    expect(screen.getByText('Cedar DENY: tool target did not execute')).toBeInTheDocument();
    expect(screen.getByText('Gateway/Cedar DENY left no tool_audit row')).toBeInTheDocument();
    expect(screen.getByText(/No-row DENY is scoped to the Gateway\/Cedar rail/)).toBeInTheDocument();
  });

  it('maps card ids to labs while an older local backend is still running', async () => {
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

    // Four-lab spine: managed execution and audit share Lab 3.
    expect(await screen.findAllByText('Lab 1: Ground Answers in Live Data')).toHaveLength(2);
    expect(screen.getAllByText('Lab 3: Run Agents in a Managed Runtime').length).toBeGreaterThan(0);
  });

  it('renders Audit Proof as a focused Lab 3 evidence view', async () => {
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
      <MemoryRouter initialEntries={['/agent-trace/audit-proof']}>
        <ProofBoard focusCardId="audit-ledger" />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Audit proof, row by row.')).toBeInTheDocument();
    expect(await screen.findByTestId('proof-card-audit-ledger')).toHaveTextContent(
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
    expect(screen.queryByText('Lab checkpoints')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'All checkpoints' })).toHaveAttribute(
      'href',
      '/agent-trace/proof-board',
    );
  });
});
