/**
 * Compact governed receipt — partial-evidence honesty.
 *
 * The receipt sits under a shopper-facing answer, so it must be quiet. What
 * it must never do is fill in a number nobody measured: "0 sources" reads
 * as "the answer was ungrounded", and a missing policy decision rendered as
 * ALLOW would erase the distinction this whole workshop teaches.
 *
 * These tests pin the partial-evidence contract from prompt 02:
 * render only known sections, label unavailable ones honestly, and never
 * infer source count, policy outcome, tool result, memory use, or latency.
 */
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import GovernedTurnReceipt from '../GovernedTurnReceipt'
import type { RailDecision } from '../../shared/governedTypes'
import type { PersistedGovernedTurnReceipt } from '../GovernedTurnReceipt'

const PERSISTED_RECEIPT: PersistedGovernedTurnReceipt = {
  turn_id: 'turn-abc',
  rail: 'gateway-mcp',
  citations: [
    {
      evidence_id: 'retrieval-1-catalog-1',
      source_uri: 'aurora://pellier/product_catalog/1',
      revision: '2026-08-12T00:00:00+00:00',
      quote: 'Linen Camp Shirt: Lightweight resort layer',
      entity_id: '1',
    },
    {
      evidence_id: 'retrieval-1-catalog-2',
      source_uri: 'aurora://pellier/product_catalog/2',
      revision: null,
      quote: 'Linen Trouser: Travel-ready layer',
      entity_id: '2',
    },
  ],
  tool_audit_ids: [
    {
      audit_id: 2,
      tool: 'find_pieces_hybrid',
      caller: 'gateway',
      latency_ms: 18,
      created_at: '2026-08-12T00:00:00+00:00',
    },
  ],
  policy_events: [{ decision: 'NOT_EVALUATED' }],
  terminal_status: 'complete',
  latency_ms: 1234.7,
}

function renderReceipt(
  props: Partial<React.ComponentProps<typeof GovernedTurnReceipt>> = {},
) {
  return render(
    <MemoryRouter>
      <GovernedTurnReceipt
        sessionId="sess-1"
        receipt={PERSISTED_RECEIPT}
        {...props}
      />
    </MemoryRouter>,
  )
}

const VERIFIED_RAIL: RailDecision = {
  rail: 'gateway-mcp',
  managedRequested: true,
  available: true,
  reason: null,
}

describe('GovernedTurnReceipt', () => {
  it('renders known counts', () => {
    renderReceipt()

    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('renders a measured zero when the persisted receipt has no citations', () => {
    renderReceipt({
      receipt: { ...PERSISTED_RECEIPT, citations: [] },
    })

    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('shows the explicit not-evaluated policy state', () => {
    renderReceipt()

    expect(screen.getByTestId('policy-decision-badge')).toHaveAttribute(
      'data-decision',
      'NOT_EVALUATED',
    )
  })

  it('renders an ALLOW decision when one exists', () => {
    renderReceipt({
      receipt: {
        ...PERSISTED_RECEIPT,
        policy_events: [{ decision: 'ALLOW' }],
      },
    })

    const badge = screen.getByTestId('policy-decision-badge')
    expect(badge.getAttribute('data-decision')).toBe('ALLOW')
  })

  it('renders a DENY decision distinctly', () => {
    renderReceipt({
      receipt: {
        ...PERSISTED_RECEIPT,
        policy_events: [
          { decision: 'DENY', reason: 'principal does not own the order' },
        ],
      },
    })

    const badge = screen.getByTestId('policy-decision-badge')
    expect(badge.getAttribute('data-decision')).toBe('DENY')
    expect(
      screen.getByText(/principal does not own the order/),
    ).toBeInTheDocument()
  })

  it('omits latency when the backend reported none', () => {
    renderReceipt({ receipt: { ...PERSISTED_RECEIPT, latency_ms: null } })

    expect(screen.queryByText(/ms$/)).toBeNull()
  })

  it('shows latency when measured', () => {
    renderReceipt()

    expect(screen.getByText('1235ms')).toBeInTheDocument()
  })

  it('shows the governed seal only when a rail was reported', () => {
    const { unmount } = renderReceipt()
    expect(screen.queryByTestId('governed-seal')).toBeNull()
    unmount()

    renderReceipt({ railDecision: VERIFIED_RAIL })
    expect(screen.getByTestId('governed-seal')).toBeInTheDocument()
  })

  it('renders nothing at all when the turn emitted no evidence', () => {
    // A triage reply that ran no tools should not sprout an empty strip.
    const { container } = render(
      <MemoryRouter>
        <GovernedTurnReceipt receipt={null} />
      </MemoryRouter>,
    )

    expect(container.textContent).toBe('')
  })

  it('links to the exact turn when a turn id exists', () => {
    renderReceipt({ turnId: 'turn-abc' })

    const link = screen.getByTestId('governed-receipt-link')
    expect(link.getAttribute('href')).toContain('/agent-trace/proof-board')
    expect(link.getAttribute('href')).toContain('turn=turn-abc')
  })

  it('degrades to a session link when no turn id exists', () => {
    renderReceipt()

    const link = screen.getByTestId('governed-receipt-link')
    expect(link.getAttribute('href')).toBe('/agent-trace/sessions/sess-1/telemetry')
    expect(link.getAttribute('href')).not.toContain('turn=')
  })

  it('falls back to the audit surface when no session is known', () => {
    render(
      <MemoryRouter>
        <GovernedTurnReceipt receipt={PERSISTED_RECEIPT} />
      </MemoryRouter>,
    )

    expect(
      screen.getByTestId('governed-receipt-link').getAttribute('href'),
    ).toBe('/agent-trace/audit-proof')
  })

  it('offers one plain-language way into the full evidence', () => {
    renderReceipt()

    expect(screen.getByText(/Why this answer\?/)).toBeInTheDocument()
  })
})
