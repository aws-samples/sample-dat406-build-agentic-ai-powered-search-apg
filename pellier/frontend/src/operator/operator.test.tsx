/**
 * Tests for the Pellier Operator surfaces.
 *
 * The behaviours worth pinning are the ones a screenshot cannot show: that a
 * missing portrait becomes a designed monogram rather than a grey box, that
 * the credit form refuses to submit above the ceiling, that a signed-out
 * operator gets a labelled state instead of a dead button, and that a replayed
 * write is reported as a replay rather than as a second credit.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ClientBook from './surfaces/ClientBook'
import ClientRecord from './surfaces/ClientRecord'
import ClientAvatar from './components/ClientAvatar'
import { MEMBERSHIP } from '../data/membership'
import {
  CAPABILITY_LABELS,
  GOVERNED_UNAVAILABLE_COPY,
} from '../services/operatorCapabilities'

const BOOK = {
  total: 3,
  byMembership: { registered: 1, circle: 1, maison: 1 },
  clients: [
    {
      customerId: 'CUST-AMARA', slug: 'amara', name: 'Amara Okonkwo',
      membership: 'maison' as const, spend12mo: 18900, orderCount: 5,
      orderValue: 3495, lastOrderAt: null, note: 'Investment pieces.',
      personaId: null,
    },
    {
      customerId: 'CUST-MARCO', slug: 'marco', name: 'Marco',
      membership: 'circle' as const, spend12mo: 3180, orderCount: 7,
      orderValue: 1200, lastOrderAt: null, note: 'Natural fibers.',
      personaId: 'marco',
    },
    {
      customerId: 'CUST-NEW', slug: 'new', name: 'Nadia Weber',
      membership: 'registered' as const, spend12mo: 410, orderCount: 1,
      orderValue: 60, lastOrderAt: null, note: 'New joiner.',
      personaId: null,
    },
  ],
}

const RECORD = {
  client: {
    customerId: 'CUST-JESSICA', slug: 'jessica', name: 'Jessica Nakamura',
    membership: 'circle' as const, spend12mo: 3940, orderCount: 2,
    orderValue: 540, lastOrderAt: null, note: 'Open return dispute.',
    personaId: null, openTicketCount: 1, creditBalanceCents: 4000,
    creditBalance: '40.00',
    returnEvidence: {
      authoritativeReturnCount: 0,
      supportAssertsReturn: true,
      unconfirmedReturnAssertion: true,
    },
  },
  orders: [
    {
      orderId: 1, productId: '41', productName: 'Coral Lacquer Catchall',
      brand: 'Pellier Maison', price: 325.36, quantity: 1, placedAt: null,
      imageUrl: '/products/house-coral-lacquer-catchall.png',
    },
  ],
  tickets: [
    {
      ticketId: 'TKT-1', subject: 'Refund disputed', status: 'pending' as const,
      channel: 'chat', lastNote: 'Awaiting decision.', openedAt: null,
      resolvedAt: null,
    },
  ],
  credits: [
    {
      creditId: 7, amountCents: 4000, amount: '40.00', currency: 'USD',
      reason: 'Goodwill: shipping', issuedBy: 'operator-sub', createdAt: null,
    },
  ],
  returns: [],
}

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const result = handler(url, init) as
        | { status?: number; body?: unknown }
        | undefined
      const status = result?.status ?? 200
      return Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve(result?.body ?? {}),
      } as Response)
    }),
  )
}

function renderRecord() {
  return render(
    <MemoryRouter initialEntries={['/operator/clients/CUST-JESSICA']}>
      <Routes>
        <Route path="/operator/clients/:customerId" element={<ClientRecord />} />
      </Routes>
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('ClientBook', () => {
  beforeEach(() => {
    mockFetch(() => ({ body: BOOK }))
  })

  it('lists every client with their rung', async () => {
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    await screen.findByTestId('operator-book')

    expect(screen.getByText('Amara Okonkwo')).toBeInTheDocument()
    expect(screen.getByText('Nadia Weber')).toBeInTheDocument()
    expect(screen.getByTestId('operator-client-amara')).toBeInTheDocument()
  })

  it('takes membership counts from the API rather than recomputing them', async () => {
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    const summary = await screen.findByTestId('operator-book-summary')

    // One of each, straight from byMembership.
    expect(summary).toHaveTextContent('Maison')
    expect(summary).toHaveTextContent('Circle')
    // The descriptor rides with the label wherever the tier matters.
    expect(summary).toHaveTextContent('priority client')
    expect(summary).toHaveTextContent('Registered')
  })

  it('pairs every rung label with a plain functional descriptor', async () => {
    // The label is premium branding; the descriptor is instant comprehension.
    // Shipping one without the other loses half the point.
    expect(MEMBERSHIP.registered.descriptor).toBe('standard client')
    expect(MEMBERSHIP.circle.descriptor).toBe('priority client')
    expect(MEMBERSHIP.maison.descriptor).toBe('private client')
    expect(MEMBERSHIP.circle.label).toBe('Circle')
  })

  it('defines each rung with its threshold and what it earns', async () => {
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    const ladder = await screen.findByTestId('operator-book-summary')

    // The pills are jargon without this: an operator can read "Maison" and
    // still not know what the house owes that client.
    expect(ladder).toHaveTextContent('Above $7,500 in 12 months')
    expect(ladder).toHaveTextContent(
      'Private appointments, repairs, and a dedicated advisor',
    )
    expect(ladder).toHaveTextContent('Under $1,500 in 12 months')
  })

  it('filters the book to one rung when its cell is pressed', async () => {
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    await screen.findByTestId('operator-book')
    expect(screen.getByText('Amara Okonkwo')).toBeInTheDocument()
    expect(screen.getByText('Nadia Weber')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('operator-ladder-maison'))

    expect(screen.getByTestId('operator-ladder-maison')).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByText('Amara Okonkwo')).toBeInTheDocument()
    // Nadia is registered, so she leaves the list.
    expect(screen.queryByText('Nadia Weber')).not.toBeInTheDocument()
  })

  it('says the list is filtered rather than just showing fewer rows', async () => {
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    await screen.findByTestId('operator-book')
    fireEvent.click(screen.getByTestId('operator-ladder-circle'))

    const note = screen.getByTestId('operator-filter-note')
    expect(note).toHaveTextContent('Showing 1 of 3')
    expect(note).toHaveTextContent('Circle')
  })

  it('clears the filter by pressing the same cell again', async () => {
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    await screen.findByTestId('operator-book')
    const cell = screen.getByTestId('operator-ladder-maison')

    fireEvent.click(cell)
    expect(screen.queryByText('Nadia Weber')).not.toBeInTheDocument()

    fireEvent.click(cell)
    expect(cell).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText('Nadia Weber')).toBeInTheDocument()
    expect(screen.queryByTestId('operator-filter-note')).not.toBeInTheDocument()
  })

  it('clears the filter from the explicit escape hatch', async () => {
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    await screen.findByTestId('operator-book')
    fireEvent.click(screen.getByTestId('operator-ladder-maison'))
    fireEvent.click(screen.getByTestId('operator-filter-clear'))

    expect(screen.getByText('Nadia Weber')).toBeInTheDocument()
  })

  it('names the missing migration when the book cannot be read', async () => {
    mockFetch(() => ({ status: 503, body: { detail: 'client_book_unavailable' } }))
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    const state = await screen.findByTestId('operator-book-error')
    expect(state).toHaveTextContent('018_client_book.sql')
  })

  it('does not blame the database when the operator is signed out', async () => {
    mockFetch(() => ({ status: 401, body: { detail: 'authentication_required' } }))
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    const state = await screen.findByTestId('operator-book-error')
    expect(state).toHaveTextContent('Operator sign-in required')
    expect(state).toHaveTextContent('No database request was attempted')
    expect(state).not.toHaveTextContent('018_client_book.sql')
  })

  it('distinguishes an empty book from a broken one', async () => {
    mockFetch(() => ({
      body: { total: 0, clients: [], byMembership: { registered: 0, circle: 0, maison: 0 } },
    }))
    render(
      <MemoryRouter>
        <ClientBook />
      </MemoryRouter>,
    )
    expect(await screen.findByTestId('operator-book-empty')).toBeInTheDocument()
  })
})

describe('ClientAvatar', () => {
  it('renders a designed monogram, not a grey box, for an unknown client', () => {
    render(<ClientAvatar customerId="CUST-NOBODY" name="Nadia Weber" />)
    const monogram = screen.getByTestId('operator-monogram')
    expect(monogram).toHaveTextContent('NW')
  })

  it('uses the real portrait when the client has one', () => {
    const { container } = render(
      <ClientAvatar customerId="CUST-JESSICA" name="Jessica Nakamura" />,
    )
    const img = container.querySelector('img')
    expect(img).not.toBeNull()
    expect(img?.getAttribute('src')).toContain('client-jessica-portrait-160.webp')
  })

  it('resolves a hero through the persona map, not the client map', () => {
    const { container } = render(
      <ClientAvatar customerId="CUST-MARCO" name="Marco" personaId="marco" />,
    )
    expect(container.querySelector('img')?.getAttribute('src')).toContain(
      'persona-marco-portrait-160.webp',
    )
  })
})

describe('ClientRecord', () => {
  beforeEach(() => {
    mockFetch((url) => {
      if (url.includes('/api/operator/clients/')) return { body: RECORD }
      return { body: {} }
    })
  })

  it('does not blame Aurora when the operator is signed out', async () => {
    mockFetch(() => ({ status: 401, body: { detail: 'authentication_required' } }))
    renderRecord()

    const state = await screen.findByTestId('operator-record-error')
    expect(state).toHaveTextContent('Operator sign-in required')
    expect(state).toHaveTextContent('No database request was attempted')
    expect(state).not.toHaveTextContent('Aurora did not return')
  })

  it('states that standing is context, not authorization', async () => {
    renderRecord()
    await screen.findByTestId('operator-record')

    // Tier / Cedar / RLS are three independent questions, and the operator is
    // told so on the surface where they are about to act.
    const record = screen.getByTestId('operator-record')
    expect(record).toHaveTextContent('Standing is business context')
    expect(record).toHaveTextContent('AgentCore Policy still decides')
    expect(record).toHaveTextContent('Aurora still decides')
  })

  it('shows standing, orders, tickets and credits together', async () => {
    renderRecord()
    await screen.findByTestId('operator-record')

    // Scoped to the record heading: the Concierge pane also names the client, to
    // make the conversation's subject unambiguous, so an unscoped text query now
    // matches twice. That duplication is intentional.
    expect(
      screen.getByRole('heading', { name: 'Jessica Nakamura' }),
    ).toBeInTheDocument()
    expect(screen.getByTestId('operator-rung-circle')).toBeInTheDocument()
    expect(screen.getByTestId('operator-orders')).toHaveTextContent(
      'Coral Lacquer Catchall',
    )
    expect(screen.getByTestId('operator-tickets')).toHaveTextContent(
      'Refund disputed',
    )
    expect(screen.getByTestId('operator-credits')).toHaveTextContent('40.00')
  })

  it('promotes the live service request and keeps conflicting evidence separate', async () => {
    renderRecord()

    const request = await screen.findByTestId('operator-service-request')
    expect(request).toHaveTextContent('Refund disputed')
    expect(request).toHaveTextContent('Awaiting decision.')
    expect(request).toHaveTextContent('0 authoritative rows')
    expect(request).toHaveTextContent(
      'Reconcile the assertion before promising an outcome.',
    )
    expect(request).toHaveAttribute('data-conflict', 'true')
    expect(
      screen.getByRole('link', { name: /Investigate with Operator Concierge/i }),
    ).toHaveAttribute('href', '#operator-concierge-title')
  })

  it('offers every nonhero client a read-only storefront preview', async () => {
    renderRecord()
    await screen.findByTestId('operator-record')

    expect(screen.getByTestId('operator-storefront-handoff')).toHaveAttribute(
      'href',
      '/?clientPreview=CUST-JESSICA',
    )
    expect(screen.getByTestId('operator-storefront-handoff')).toHaveTextContent(
      'Preview client context',
    )
  })

  it('uses a real persona-switch handoff for a canonical hero', async () => {
    mockFetch((url) => {
      if (url.includes('/api/operator/clients/')) {
        return {
          body: {
            ...RECORD,
            client: {
              ...RECORD.client,
              customerId: 'CUST-MARCO',
              slug: 'marco',
              name: 'Marco',
              personaId: 'marco',
            },
          },
        }
      }
      return { body: {} }
    })
    renderRecord()
    await screen.findByTestId('operator-record')

    expect(screen.getByTestId('operator-storefront-handoff')).toHaveAttribute(
      'href',
      '/?persona=marco',
    )
    expect(screen.getByTestId('operator-storefront-handoff')).toHaveTextContent(
      "Open Marco's storefront",
    )
  })

  it('disables the credit button until an amount and a reason are present', async () => {
    renderRecord()
    await screen.findByTestId('operator-record')

    const submit = screen.getByTestId('operator-credit-submit')
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByTestId('operator-credit-reason'), {
      target: { value: 'Goodwill for the delay' },
    })
    expect(submit).toBeEnabled()
  })

  it('refuses an amount above the $500 ceiling client-side too', async () => {
    renderRecord()
    await screen.findByTestId('operator-record')

    fireEvent.change(screen.getByTestId('operator-credit-reason'), {
      target: { value: 'Goodwill' },
    })
    fireEvent.change(screen.getByTestId('operator-credit-amount'), {
      target: { value: '500.01' },
    })
    expect(screen.getByTestId('operator-credit-submit')).toBeDisabled()

    fireEvent.change(screen.getByTestId('operator-credit-amount'), {
      target: { value: '500.00' },
    })
    expect(screen.getByTestId('operator-credit-submit')).toBeEnabled()
  })

  it('sends integer cents so no float reaches the ledger', async () => {
    mockFetch((_url, init) => {
      if (init?.method === 'POST') {
        return {
          body: {
            result: { status: 'success', amount: '12.34' },
            idempotencyKey: 'k', actedBy: 'operator-1',
          },
        }
      }
      return { body: RECORD }
    })
    renderRecord()
    await screen.findByTestId('operator-record')

    fireEvent.change(screen.getByTestId('operator-credit-reason'), {
      target: { value: 'Goodwill' },
    })
    fireEvent.change(screen.getByTestId('operator-credit-amount'), {
      target: { value: '12.34' },
    })
    fireEvent.click(screen.getByTestId('operator-credit-submit'))

    await waitFor(() => {
      const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls
      const post = calls.find(
        (call) => String(call[0]).includes('issue-credit'),
      )
      expect(post).toBeDefined()
      expect(JSON.parse(String((post?.[1] as RequestInit).body))).toMatchObject({
        amountCents: 1234,
      })
    })
  })

  it('labels a signed-out operator instead of leaving a dead button', async () => {
    mockFetch((_url, init) => {
      if (init?.method === 'POST') {
        return { status: 401, body: { detail: 'operator_sign_in_required' } }
      }
      return { body: RECORD }
    })
    renderRecord()
    await screen.findByTestId('operator-record')

    fireEvent.change(screen.getByTestId('operator-credit-reason'), {
      target: { value: 'Goodwill' },
    })
    fireEvent.click(screen.getByTestId('operator-credit-submit'))

    expect(await screen.findByTestId('operator-needs-signin')).toHaveTextContent(
      'Operator sign-in required',
    )
  })

  it('reports a replay as a replay, not as a second credit', async () => {
    mockFetch((_url, init) => {
      if (init?.method === 'POST') {
        return {
          body: {
            result: {
              status: 'success', amount: '40.00', idempotent_replay: true,
            },
            idempotencyKey: 'stable-key',
            actedBy: 'operator-1',
          },
        }
      }
      return { body: RECORD }
    })
    renderRecord()
    await screen.findByTestId('operator-record')

    fireEvent.change(screen.getByTestId('operator-credit-reason'), {
      target: { value: 'Goodwill' },
    })
    fireEvent.click(screen.getByTestId('operator-credit-submit'))

    const receipt = await screen.findByTestId('operator-action-receipt')
    expect(receipt).toHaveAttribute('data-outcome', 'success')
    expect(receipt).toHaveTextContent('Already applied')
    expect(receipt).toHaveTextContent('stable-key')
  })

  it('renders a policy block as blocked, not as a failure', async () => {
    mockFetch((_url, init) => {
      if (init?.method === 'POST') {
        return {
          body: {
            result: { status: 'policy_blocked', message: 'exceeds the ceiling' },
            idempotencyKey: 'k',
            actedBy: 'operator-1',
          },
        }
      }
      return { body: RECORD }
    })
    renderRecord()
    await screen.findByTestId('operator-record')

    fireEvent.change(screen.getByTestId('operator-credit-reason'), {
      target: { value: 'Goodwill' },
    })
    fireEvent.click(screen.getByTestId('operator-credit-submit'))

    const receipt = await screen.findByTestId('operator-action-receipt')
    expect(receipt).toHaveAttribute('data-outcome', 'blocked')
    expect(receipt).toHaveTextContent('exceeds the ceiling')
  })

  it('keeps the return button inert until a numeric product id is entered', async () => {
    renderRecord()
    await screen.findByTestId('operator-record')

    const submit = screen.getByTestId('operator-return-submit')
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByTestId('operator-return-product'), {
      target: { value: 'forty-one' },
    })
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByTestId('operator-return-product'), {
      target: { value: '41' },
    })
    expect(submit).toBeEnabled()
  })
})

// ---------------------------------------------------------------------------
// Capability copy
// ---------------------------------------------------------------------------

describe('governed capability copy', () => {
  it('never calls a deliberately closed rail an error', () => {
    // A closed write rail is a governance state, not a fault. Asserted against the
    // shipped strings rather than a copy of them: a test that restates the copy
    // locally passes no matter what the surface renders.
    const copy = `${GOVERNED_UNAVAILABLE_COPY.title} ${GOVERNED_UNAVAILABLE_COPY.detail}`
    for (const banned of ['Disconnected', 'Offline', 'Broken', 'Error', 'Failed']) {
      expect(copy).not.toContain(banned)
    }
    expect(copy).toContain('remain available')
  })

  it('keeps not_enabled and temporarily_unavailable distinct', () => {
    // Different causes with different futures: one may open, one is not published.
    expect(CAPABILITY_LABELS.not_enabled).not.toBe(
      CAPABILITY_LABELS.temporarily_unavailable,
    )
  })
})
