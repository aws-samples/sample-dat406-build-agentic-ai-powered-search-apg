import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import OperatorLineage from './OperatorLineage'

const HANDOFF = {
  schemaVersion: '1',
  trust: 'UNTRUSTED_SHOPPER_CONTEXT',
  checkpoint: 'WAITING_FOR_HUMAN',
  customerId: 'CUST-THEO',
  source: { sessionId: 'shopper-session', turnId: 'turn-shopper' },
  shopperRequest: 'My Wabi-Sabi Bowl arrived chipped.',
  routing: {
    specialist: 'customer_service',
    tools: ['get_return_policy', 'initiate_return'],
  },
  proposal: {
    reviewId: 8,
    action: 'initiate_return',
    actionHash: 'a'.repeat(64),
  },
}

const PENDING = {
  customerId: 'CUST-THEO',
  customerName: 'Theo',
  dataSource: 'Local PostgreSQL',
  handoff: HANDOFF,
  review: {
    reviewId: 8,
    customerId: 'CUST-THEO',
    customerName: 'Theo',
    action: 'initiate_return',
    status: 'pending',
    sourceTurnId: 'turn-shopper',
    executionTurnId: null,
    actionHash: 'a'.repeat(64),
  },
  orchestration: {
    graphId: 'operator-concierge-v1',
    pattern: 'strands-graph',
    execution: 'application-orchestrated',
    deploymentTarget: 'AgentCore Runtime',
    agents: ['case-investigator', 'resolution-planner'],
    executedNodes: [
      {
        nodeId: 'case-investigator',
        status: 'completed',
        durationMs: 8,
      },
      {
        nodeId: 'resolution-planner',
        status: 'completed',
        durationMs: 13,
      },
    ],
    checkpoint: {
      state: 'WAITING_FOR_HUMAN',
      reviewId: 8,
      actionHash: 'a'.repeat(64),
    },
  },
  execution: null,
}

function mockResponse(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve(body),
      } as Response),
    ),
  )
}

function renderPage() {
  return render(
    <MemoryRouter>
      <OperatorLineage />
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('OperatorLineage', () => {
  it('renders the handoff, two graph agents, and later human checkpoint', async () => {
    mockResponse(PENDING)
    renderPage()

    expect(await screen.findByText('My Wabi-Sabi Bowl arrived chipped.'))
      .toBeInTheDocument()
    expect(screen.getByText('Local PostgreSQL')).toBeInTheDocument()
    expect(screen.getByTestId('operator-lineage-checkpoint'))
      .toHaveAttribute('data-stage-state', 'complete')
    expect(screen.getByTestId('operator-lineage-case-investigator'))
      .toHaveTextContent('completed in 8ms')
    expect(screen.getByTestId('operator-lineage-resolution-planner'))
      .toHaveTextContent('completed in 13ms')
    expect(screen.getByTestId('operator-lineage-human-decision'))
      .toHaveAttribute('data-stage-state', 'waiting')
    expect(screen.getByTestId('operator-lineage-execution'))
      .toHaveAttribute('data-stage-state', 'waiting')
    expect(screen.getByText(/strands-graph · AgentCore Runtime target/i))
      .toBeInTheDocument()

    expect(fetch).toHaveBeenCalledWith(
      '/api/observatory/operator-lineage/CUST-THEO',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('shows a live-data empty state rather than fixture lineage', async () => {
    mockResponse({
      customerId: 'CUST-THEO',
      dataSource: 'Local PostgreSQL',
      handoff: null,
      review: null,
      orchestration: null,
      execution: null,
    })
    renderPage()

    expect(await screen.findByText(/No durable Theo handoff is present yet/i))
      .toBeInTheDocument()
    expect(screen.getByText(/does not substitute fixture data/i))
      .toBeInTheDocument()
    expect(screen.queryByTestId('operator-lineage-case-investigator'))
      .not.toBeInTheDocument()
  })

  it('does not mistake an authentication failure for a missing handoff', async () => {
    mockResponse({ detail: 'authentication_required' }, 401)
    renderPage()

    expect(await screen.findByText('Operator sign-in required'))
      .toBeInTheDocument()
    expect(screen.getByText(/principal-scoped lineage/i)).toBeInTheDocument()
    expect(screen.queryByText(/No durable Theo handoff/i)).not.toBeInTheDocument()
  })

  it('keeps human, policy, database, and evidence outcomes distinct', async () => {
    mockResponse({
      ...PENDING,
      review: { ...PENDING.review, status: 'approved' },
      execution: {
        latestReceipt: {
          policy_outcome: 'ALLOW',
          aurora_outcome: 'APPLIED',
          evidence_outcome: 'COMPLETE',
          rail: 'gateway-mcp',
        },
      },
    })
    renderPage()

    await waitFor(() => {
      expect(screen.getByTestId('operator-lineage-human-decision'))
        .toHaveAttribute('data-stage-state', 'complete')
    })
    const execution = screen.getByTestId('operator-lineage-execution')
    expect(execution).toHaveAttribute('data-stage-state', 'complete')
    expect(execution).toHaveTextContent('Policy ALLOW')
    expect(execution).toHaveTextContent('PostgreSQL APPLIED')
    expect(execution).toHaveTextContent('evidence COMPLETE')
  })
})
