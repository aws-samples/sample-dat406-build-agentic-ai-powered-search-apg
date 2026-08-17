import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  CommerceApiError,
  confirmCommerceQuote,
  createCommerceQuote,
  executeCommerceOrder,
  type CommerceQuote,
} from './commerce'

const quote: CommerceQuote = {
  quoteId: '0ca0d9d5-2229-43a8-8fe0-0d00a0321abb',
  quoteHash: 'a'.repeat(64),
  status: 'open',
  currency: 'USD',
  lines: [],
  amounts: {
    subtotal: '80.00',
    shipping: '12.00',
    tax: '6.60',
    total: '98.60',
  },
  rules: {
    policy: 'pellier-commerce-v1',
    taxRate: '0.0825',
    freeShippingThreshold: '150.00',
    standardShipping: '12.00',
    paymentProvider: 'pellier-sandbox',
    paymentMode: 'sandbox',
  },
  expiresAt: '2026-08-16T20:10:00+00:00',
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('commerce API', () => {
  it('sends only product identity and quantity for authoritative pricing', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(quote), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await createCommerceQuote([{ productId: 7, quantity: 2 }], 'session-1')

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({
      lines: [{ productId: 7, quantity: 2 }],
      sessionId: 'session-1',
    })
    expect(init.credentials).toBe('include')
  })

  it('binds explicit confirmation to the quote hash', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ confirmationGrantId: 'grant-1' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await confirmCommerceQuote(quote)

    const [path, init] = fetchMock.mock.calls[0]
    expect(path).toContain(`${quote.quoteId}/confirm`)
    expect(JSON.parse(init.body)).toEqual({
      quoteHash: quote.quoteHash,
      acknowledged: true,
    })
  })

  it('threads one idempotency key into order execution', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ orderId: 'order-1' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await executeCommerceOrder('grant-1', 'checkout-fixed-key')

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({
      confirmationGrantId: 'grant-1',
      idempotencyKey: 'checkout-fixed-key',
    })
  })

  it('preserves backend failure taxonomy', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'inventory_unavailable' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(createCommerceQuote([{ productId: 7, quantity: 2 }]))
      .rejects.toEqual(new CommerceApiError('inventory_unavailable', 409))
  })
})
