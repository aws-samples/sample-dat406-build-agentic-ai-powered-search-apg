/**
 * Turn badges tell two different truths.
 *
 * "Response complete" means the stream finished. "Evidence recorded" means the
 * durable evidence ledger for that turn_id reports every required sufficiency
 * check satisfied. The second is fetched, never inferred from the first, and
 * while the fetch is in flight the receipt says nothing about evidence.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { EvidenceLedger } from '../shared/evidenceLedger'

const mocks = vi.hoisted(() => ({
  auth: { isAuthenticated: true } as { isAuthenticated: boolean } | null,
}))

vi.mock('../contexts/AuthContext', () => ({
  useOptionalAuth: () => mocks.auth,
}))

import TurnReceipt from './TurnReceipt'

function ledger(statuses: string[]): EvidenceLedger {
  return {
    version: '1.0',
    authority: 'canonical-receipt-projection',
    principalScoped: true,
    turnId: 'turn-1',
    events: [],
    evidenceSufficiency: statuses.map((status, index) => ({
      id: `check-${index}`,
      label: `Check ${index}`,
      status: status as EvidenceLedger['evidenceSufficiency'][number]['status'],
      detail: '',
    })),
  }
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('TurnReceipt', () => {
  beforeEach(() => {
    mocks.auth = { isAuthenticated: true }
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows Response complete once the stream has finished', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})))
    render(<TurnReceipt reference="trace-abc" turnId="turn-1" complete />)

    expect(screen.getByText('Response complete')).toBeInTheDocument()
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument()
  })

  it('says nothing about completion while the stream is still open', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})))
    render(<TurnReceipt reference="trace-abc" turnId="turn-1" complete={false} />)

    expect(screen.queryByText('Response complete')).not.toBeInTheDocument()
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument()
  })

  // "We read the ledger and it came back short" and "we have not looked" are
  // different findings. They rendered identically until the receipt carried a
  // third state, which made a contradicted turn indistinguishable from an
  // unexamined one on the surface an operator reads first.
  it('marks a read-but-unsatisfied ledger incomplete on the inspection surface', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(ledger(['satisfied', 'contradicted']))),
    )
    render(
      <TurnReceipt
        reference="trace-abc"
        turnId="turn-1"
        complete
        surface="observatory"
      />,
    )

    expect(await screen.findByText('Evidence incomplete')).toBeInTheDocument()
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument()
    expect(screen.getByTestId('turn-receipt')).toHaveAttribute(
      'data-evidence',
      'incomplete',
    )
  })

  it('separates an unsatisfied ledger from one that was never read', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 404 })))
    render(
      <TurnReceipt
        reference="trace-abc"
        turnId="turn-1"
        complete
        surface="observatory"
      />,
    )

    await waitFor(() =>
      expect(screen.getByTestId('turn-receipt')).toHaveAttribute(
        'data-evidence',
        'unknown',
      ),
    )
    expect(screen.queryByText('Evidence incomplete')).not.toBeInTheDocument()
  })

  it('leaves the storefront receipt free of a governance verdict', async () => {
    // The shopper is owed the answer. The absent "Evidence recorded" badge is
    // already the honest signal there, so the finding stays on the Observatory.
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(ledger(['satisfied', 'contradicted']))),
    )
    render(<TurnReceipt reference="trace-abc" turnId="turn-1" complete />)

    await waitFor(() =>
      expect(screen.getByTestId('turn-receipt')).toHaveAttribute(
        'data-evidence',
        'incomplete',
      ),
    )
    expect(screen.queryByText('Evidence incomplete')).not.toBeInTheDocument()
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument()
  })

  it('shows Evidence recorded only when every required check is satisfied', async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(ledger(['satisfied', 'satisfied', 'not_applicable'])),
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<TurnReceipt reference="trace-abc" turnId="turn-1" complete />)

    await waitFor(() => {
      expect(screen.getByText('Evidence recorded')).toBeInTheDocument()
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/observatory/turns/turn-1/ledger',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('withholds Evidence recorded when a required check is missing', async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(ledger(['satisfied', 'missing', 'satisfied'])),
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<TurnReceipt reference="trace-abc" turnId="turn-1" complete />)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    // Give any state update a chance to land before asserting absence.
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(screen.getByText('Response complete')).toBeInTheDocument()
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument()
  })

  it('does not fetch a principal-scoped ledger for an anonymous shopper', () => {
    mocks.auth = { isAuthenticated: false }
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    render(<TurnReceipt reference="trace-abc" turnId="turn-1" complete />)

    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.queryByText('Evidence recorded')).not.toBeInTheDocument()
  })
})
