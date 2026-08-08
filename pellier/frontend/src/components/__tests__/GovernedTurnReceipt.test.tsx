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

function renderReceipt(
  props: Partial<React.ComponentProps<typeof GovernedTurnReceipt>> = {},
) {
  return render(
    <MemoryRouter>
      <GovernedTurnReceipt sessionId="sess-1" {...props} />
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
    renderReceipt({ sourceCount: 3, toolCount: 2 })

    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('labels an unreported source count instead of showing zero', () => {
    // "0 sources" would claim the answer was ungrounded.
    renderReceipt({ toolCount: 1 })

    expect(screen.getAllByText('not reported').length).toBeGreaterThan(0)
    expect(screen.queryByText('0')).toBeNull()
  })

  it('omits the policy badge entirely when no decision was made', () => {
    // Absence of a decision is not an ALLOW.
    renderReceipt({ sourceCount: 2, toolCount: 1 })

    expect(screen.queryByTestId('policy-decision-badge')).toBeNull()
  })

  it('renders an ALLOW decision when one exists', () => {
    renderReceipt({ sourceCount: 2, policyDecision: 'ALLOW' })

    const badge = screen.getByTestId('policy-decision-badge')
    expect(badge.getAttribute('data-decision')).toBe('ALLOW')
  })

  it('renders a DENY decision distinctly', () => {
    renderReceipt({
      policyDecision: 'DENY',
      policyReason: 'principal does not own the order',
    })

    const badge = screen.getByTestId('policy-decision-badge')
    expect(badge.getAttribute('data-decision')).toBe('DENY')
    expect(
      screen.getByText(/principal does not own the order/),
    ).toBeInTheDocument()
  })

  it('omits latency when the backend reported none', () => {
    renderReceipt({ sourceCount: 1 })

    expect(screen.queryByText(/ms$/)).toBeNull()
  })

  it('shows latency when measured', () => {
    renderReceipt({ sourceCount: 1, latencyMs: 1234.7 })

    expect(screen.getByText('1235ms')).toBeInTheDocument()
  })

  it('shows the governed seal only when a rail was reported', () => {
    const { unmount } = renderReceipt({ sourceCount: 1 })
    expect(screen.queryByTestId('governed-seal')).toBeNull()
    unmount()

    renderReceipt({ sourceCount: 1, railDecision: VERIFIED_RAIL })
    expect(screen.getByTestId('governed-seal')).toBeInTheDocument()
  })

  it('renders nothing at all when the turn emitted no evidence', () => {
    // A triage reply that ran no tools should not sprout an empty strip.
    const { container } = render(
      <MemoryRouter>
        <GovernedTurnReceipt />
      </MemoryRouter>,
    )

    expect(container.textContent).toBe('')
  })

  it('links to the exact turn when a turn id exists', () => {
    renderReceipt({ sourceCount: 1, turnId: 'turn-abc' })

    const link = screen.getByTestId('governed-receipt-link')
    expect(link.getAttribute('href')).toContain('/atelier/sessions/sess-1/telemetry')
    expect(link.getAttribute('href')).toContain('turn=turn-abc')
  })

  it('degrades to a session link when no turn id exists', () => {
    renderReceipt({ sourceCount: 1 })

    const link = screen.getByTestId('governed-receipt-link')
    expect(link.getAttribute('href')).toBe('/atelier/sessions/sess-1/telemetry')
    expect(link.getAttribute('href')).not.toContain('turn=')
  })

  it('falls back to the audit surface when no session is known', () => {
    render(
      <MemoryRouter>
        <GovernedTurnReceipt toolCount={1} />
      </MemoryRouter>,
    )

    expect(
      screen.getByTestId('governed-receipt-link').getAttribute('href'),
    ).toBe('/atelier/audit-proof')
  })

  it('offers one plain-language way into the full evidence', () => {
    renderReceipt({ sourceCount: 1 })

    expect(screen.getByText(/Why this answer\?/)).toBeInTheDocument()
  })
})
