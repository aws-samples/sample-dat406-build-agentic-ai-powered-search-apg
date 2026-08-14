import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
    traceId: '4bf92f3577b34da6a3ce929d0e0e4736',
    runtimeRequestId: 'request-123',
    sessionId: 'managed-proof',
    evidenceProvenance: 'agentcore-service-telemetry',
    managedTrace: {
      traceId: '4bf92f3577b34da6a3ce929d0e0e4736',
      runtimeRequestId: 'request-123',
      sessionId: 'managed-proof',
      xrayConsoleUrl: 'https://console.example/xray',
      logsConsoleUrl: 'https://console.example/logs',
    },
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
      links: [{ label: 'Tools', to: '/pellier-labs/tools' }],
    },
    {
      id: 'retrieval-comparison',
      lab: 'Lab 2: Design the Retrieval Strategy',
      group: 'Retrieval evidence',
      title: 'Compare retrieval strategies',
      status: 'available',
      required: true,
      surface: 'Pellier Labs',
      summary: 'The retrieval comparison keeps source and ranking evidence visible.',
      evidenceSource: 'Aurora search strategy comparison',
      evidence: ['Hybrid retrieval preserves candidate provenance.'],
      fallback: {
        label: 'Terminal fallback',
        command: 'curl -s http://localhost:8000/api/agent/search-strategies/compare',
      },
      links: [{ label: 'Retrieval comparison', to: '/pellier-labs/performance' }],
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
      links: [{ label: 'Sessions', to: '/pellier-labs/sessions' }],
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
      evidence: [
        'AgentCore Memory configured for authenticated session history',
        'JWT passthrough: true',
      ],
      fallback: {
        label: 'Terminal fallback',
        command: 'curl -N http://localhost:8000/api/agent/chat',
      },
      links: [{ label: 'Sessions', to: '/pellier-labs/sessions' }],
    },
    {
      id: 'runtime-gateway-policy',
      lab: 'Lab 4: Govern and Trace Agent Actions',
      group: 'Governance evidence',
      title: 'Verify Gateway, Cedar, and the governed receipt',
      status: 'complete',
      required: true,
      surface: 'Gateway policy receipt',
      summary: 'The Gateway decision and the corresponding audit row are correlated.',
      evidence: ['ALLOW receipt linked to tool_audit 303.'],
      fallback: {
        label: 'Terminal fallback',
        command: 'curl -s http://localhost:8000/api/agent-trace/proof-board',
      },
      links: [{ label: 'Gateway & Policy', to: '/pellier-labs/write-path' }],
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ProofBoard', () => {
  it('renders readiness checks, managed receipt, and proof card fallbacks', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify(proofBoardPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <ProofBoard />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Proof Board')).toBeInTheDocument();
    expect(screen.getByTestId('governed-proof-rail')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/agent-trace/proof-board', {
      credentials: 'include',
    });
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
    expect(screen.getByTestId('managed-trace-correlation')).toHaveTextContent(
      '4bf92f3577b34da6a3ce929d0e0e4736',
    );
    expect(screen.getByTestId('managed-trace-correlation')).toHaveTextContent(
      'request-123',
    );
    expect(screen.getByRole('link', { name: 'Trace in CloudWatch' })).toHaveAttribute(
      'href',
      'https://console.example/xray',
    );
    expect(screen.getByRole('link', { name: 'Runtime logs' })).toHaveAttribute(
      'href',
      'https://console.example/logs',
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

  it('keeps the governed path compact until a participant selects a stage', async () => {
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

    expect(await screen.findByRole('tab', { name: /Ground answers/i })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    fireEvent.click(screen.getByRole('tab', { name: /Runtime & memory/i }));
    expect(screen.getByRole('tabpanel')).toHaveTextContent(
      'AgentCore Memory configured for authenticated session history',
    );
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Memory and managed receipt');

    fireEvent.click(screen.getByRole('tab', { name: /Policy & receipt/i }));

    expect(screen.getByRole('tab', { name: /Policy & receipt/i })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getByRole('tabpanel')).toHaveTextContent(
      'Was the action allowed, stopped, or recorded with evidence?',
    );
    expect(screen.getByRole('tabpanel')).toHaveTextContent('ALLOW · tool_audit 303');
    expect(screen.getByRole('link', { name: 'Open checkpoint' }))
      .toHaveAttribute('href', '#runtime-gateway-policy');
  });

  it('fails closed when a proof-board response is missing a required checkpoint', async () => {
    const cards = proofBoardPayload.cards.filter((card) => card.id !== 'retrieval-comparison');
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

    await screen.findByTestId('governed-proof-rail');
    fireEvent.click(screen.getByRole('tab', { name: /Retrieval/i }));

    const panel = screen.getByRole('tabpanel');
    expect(panel).toHaveTextContent('Evidence unavailable');
    expect(panel).toHaveTextContent(
      'This Proof Board response does not include the checkpoint required for this stage.',
    );
    expect(panel.querySelector('a')).toBeNull();
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

  it('renders an authenticated persisted turn record instead of session fixtures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/receipts/turn-live')) {
          return new Response(
            JSON.stringify({
              turn_id: 'turn-live',
              rail: 'gateway-mcp',
              citations: [
                {
                  evidence_id: 'retrieval-1-catalog-12',
                  source_uri: 'aurora://pellier/product_catalog/12',
                  revision: null,
                  quote: 'Linen Camp Shirt: Breathable resort layer',
                  entity_id: '12',
                },
              ],
              tool_audit_ids: [],
              policy_events: [{ decision: 'NOT_EVALUATED' }],
              terminal_status: 'complete',
              latency_ms: 24,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(JSON.stringify(proofBoardPayload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    render(
      <MemoryRouter initialEntries={['/pellier-labs/proof-board?turn=turn-live']}>
        <ProofBoard />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId('persisted-turn-receipt')).toHaveTextContent(
      'turn-live',
    );
    expect(screen.getByTestId('persisted-turn-receipt')).toHaveTextContent(
      'Linen Camp Shirt: Breathable resort layer',
    );
    expect(screen.getByTestId('persisted-turn-receipt')).toHaveTextContent(
      'NOT EVALUATED',
    );
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
      <MemoryRouter initialEntries={['/pellier-labs/audit-proof']}>
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
      '/pellier-labs/proof-board',
    );
  });
});
