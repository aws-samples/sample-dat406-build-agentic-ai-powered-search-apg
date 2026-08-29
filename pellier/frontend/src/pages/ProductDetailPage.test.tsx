/**
 * ProductDetailPage tests — `/product/:productId`.
 *
 * The contract under test is the two-layer read and, above all, its
 * honesty rules:
 *
 *   - The committed showcase row paints immediately, so the page is useful
 *     with no backend and never flashes empty.
 *   - Aurora contributes exactly `description` and `availability`.
 *   - A failed or null availability read renders as an explicit "not read"
 *     and NEVER as zero stock. This is the assertion that matters most:
 *     a fabricated out-of-stock claim about the authoritative system is
 *     the specific failure this surface must not have.
 *   - Siblings come from the piece's own edit, not the active profile's,
 *     so "More from this edit" stays true on a deep link.
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// --- Mocks --------------------------------------------------------------

const addToCart = vi.fn()
const openDrawerWithQuery = vi.fn()
const openModal = vi.fn()

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    accessToken: null,
    login: vi.fn(),
    logout: vi.fn(),
    loading: false,
    preferences: null,
    prefsVersion: 0,
  }),
}))

vi.mock('../contexts/CartContext', () => ({
  useCart: () => ({ items: [], addToCart, setCartOpen: vi.fn() }),
}))

// Anna is the active profile on purpose: the pieces under test belong to
// other edits, which is what proves siblings resolve from the piece.
vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona: {
      id: 'anna',
      display_name: 'Anna',
      avatar_initial: 'A',
      avatar_color: '#1f1410',
      customer_id: 'C-ANNA',
      role_tag: 'shopper',
      stats: { visits: 0, orders: 0, last_seen_days: null },
    },
    switchPersona: vi.fn(),
    signOut: vi.fn(),
    switching: false,
  }),
}))

vi.mock('../contexts/UIContext', () => ({
  useUI: () => ({
    activeModal: null,
    openModal,
    closeModal: vi.fn(),
    chatSurface: 'drawer',
    setChatSurface: vi.fn(),
    toggleDrawer: vi.fn(),
    openDrawerWithQuery,
    pendingConciergeQuery: null,
    consumePendingQuery: vi.fn(),
    comparisonProducts: [],
    openComparison: vi.fn(),
    openChat: vi.fn(),
    announcementDismissed: {
      legacy: false,
      search: false,
      agentic: false,
      production: false,
    },
    dismissAnnouncement: vi.fn(),
  }),
}))

import ProductDetailPage from './ProductDetailPage'
import { PRODUCT_DETAIL } from '../copy'
import { MARCO_PRODUCTS, SHOWCASE_PRODUCTS } from '../data/showcaseProducts'

// ProductCard's reveal observer needs the global in jsdom.
class NoopIntersectionObserver {
  readonly root: Element | null = null
  readonly rootMargin: string = ''
  readonly thresholds: ReadonlyArray<number> = [0]
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}

/** The Italian Linen Camp Shirt — Marco's edit, id 11. */
const SUBJECT = MARCO_PRODUCTS[0]

interface DetailPayload {
  description?: string | null
  availability?: {
    onHand: number
    warehouses: Array<{
      warehouseId: string
      name: string
      city: string
      quantity: number
      shipWindowMin?: number | null
      shipWindowMax?: number | null
    }>
  } | null
  [key: string]: unknown
}

/**
 * Route `/api/products/:id` to a supplied payload and answer every other
 * request benignly, so unrelated chrome fetches cannot fail a test.
 */
function stubFetch(handler: (id: string) => Response | Promise<Response>) {
  const impl = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : String(input)
    const match = /\/api\/products\/(\w+)/.exec(url)
    if (match) return handler(match[1])
    return new Response('[]', { status: 200 })
  })
  vi.stubGlobal('fetch', impl)
  return impl
}

function jsonResponse(body: DetailPayload): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function detailPayload(overrides: DetailPayload = {}): DetailPayload {
  return {
    id: SUBJECT.id,
    brand: SUBJECT.brand,
    name: SUBJECT.name,
    color: SUBJECT.color,
    price: SUBJECT.price,
    rating: SUBJECT.rating,
    reviewCount: SUBJECT.reviewCount,
    category: 'Tops',
    imageUrl: SUBJECT.imageUrl,
    badge: SUBJECT.badge ?? null,
    tags: SUBJECT.tags,
    description: 'Cut from Italian linen with a relaxed camp collar.',
    availability: {
      onHand: 42,
      warehouses: [
        {
          warehouseId: 'BK-01',
          name: 'Brooklyn',
          city: 'Brooklyn, NY',
          quantity: 20,
          shipWindowMin: 1,
          shipWindowMax: 2,
        },
        {
          warehouseId: 'ATX-02',
          name: 'Austin',
          city: 'Austin, TX',
          quantity: 22,
          shipWindowMin: 2,
          shipWindowMax: 4,
        },
      ],
    },
    ...overrides,
  }
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/product/:productId" element={<ProductDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.stubGlobal('IntersectionObserver', NoopIntersectionObserver)
  addToCart.mockReset()
  openDrawerWithQuery.mockReset()
  openModal.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// --- Committed layer ----------------------------------------------------

describe('ProductDetailPage — committed showcase layer', () => {
  it('paints the piece before the Aurora read resolves', () => {
    // A promise that never settles: nothing below can come from the fetch.
    stubFetch(() => new Promise<Response>(() => {}))

    renderAt(`/product/${SUBJECT.id}`)

    expect(screen.getByTestId('product-detail-name')).toHaveTextContent(
      SUBJECT.name,
    )
    // Scoped to the detail column — sibling cards print brands and prices too.
    const summary = within(screen.getByTestId('product-detail-summary'))
    expect(summary.getByText(SUBJECT.brand)).toBeInTheDocument()
    expect(summary.getByText(`$${SUBJECT.price}`)).toBeInTheDocument()
    expect(screen.getByTestId('product-availability')).toHaveAttribute(
      'data-state',
      'reading',
    )
  })

  it('lists siblings from the piece own edit, not the active profile edit', async () => {
    stubFetch(() => jsonResponse(detailPayload()))

    renderAt(`/product/${SUBJECT.id}`)

    const siblings = await screen.findByTestId('product-detail-siblings')
    // Anna is the active profile; every sibling must still be Marco's.
    const marcoIds = new Set(MARCO_PRODUCTS.map(p => p.id))
    const rendered = Array.from(
      siblings.querySelectorAll('[data-testid^="product-card-"]'),
    )
      .map(node => node.getAttribute('data-testid'))
      .filter((id): id is string => /^product-card-\d+$/.test(id ?? ''))
      .map(id => Number(id.replace('product-card-', '')))

    expect(rendered.length).toBeGreaterThan(0)
    for (const id of rendered) {
      expect(marcoIds.has(id)).toBe(true)
      expect(id).not.toBe(SUBJECT.id)
    }
  })
})

// --- Aurora layer -------------------------------------------------------

describe('ProductDetailPage — Aurora layer', () => {
  it('renders catalog copy and per-warehouse stock once the read lands', async () => {
    stubFetch(() => jsonResponse(detailPayload()))

    renderAt(`/product/${SUBJECT.id}`)

    expect(await screen.findByTestId('product-description')).toHaveTextContent(
      'Cut from Italian linen with a relaxed camp collar.',
    )
    expect(screen.getByTestId('product-on-hand')).toHaveTextContent('42')
    expect(screen.getByTestId('product-availability')).toHaveAttribute(
      'data-state',
      'read',
    )
    expect(screen.getByTestId('product-availability-source')).toHaveTextContent(
      PRODUCT_DETAIL.AVAILABILITY_SOURCE,
    )

    const brooklyn = screen.getByTestId('product-warehouse-BK-01')
    expect(brooklyn).toHaveTextContent('Brooklyn')
    expect(brooklyn).toHaveTextContent('20')
    expect(brooklyn).toHaveTextContent(PRODUCT_DETAIL.shipWindow(1, 2))
  })

  it('prints each catalog signal distinctly', async () => {
    stubFetch(() => jsonResponse(detailPayload()))

    renderAt(`/product/${SUBJECT.id}`)

    const signals = await screen.findByTestId('product-detail-signals')
    const labels = Array.from(signals.children).map(node =>
      node.textContent?.trim(),
    )
    // The friendly label mode collapses every `tag.match` entry onto one
    // vocabulary label, which rendered four identical chips.
    expect(new Set(labels).size).toBe(labels.length)
    expect(labels[0]).toContain(SUBJECT.tags[0])
  })

  it('requests the piece by its catalog id', async () => {
    const impl = stubFetch(() => jsonResponse(detailPayload()))

    renderAt(`/product/${SUBJECT.id}`)

    await screen.findByTestId('product-description')
    const urls = impl.mock.calls.map(call => String(call[0]))
    expect(urls).toContain(`/api/products/${SUBJECT.id}`)
  })
})

// --- Degraded reads -----------------------------------------------------

describe('ProductDetailPage — a failed read is never zero stock', () => {
  it('declares inventory unread when the request fails', async () => {
    stubFetch(() => Promise.reject(new Error('network down')))

    renderAt(`/product/${SUBJECT.id}`)

    const panel = await screen.findByTestId('product-availability-degraded')
    expect(panel).toHaveTextContent(PRODUCT_DETAIL.AVAILABILITY_UNAVAILABLE)
    expect(screen.getByTestId('product-availability')).toHaveAttribute(
      'data-state',
      'not-read',
    )
    // The specific fabrication this guards against.
    expect(screen.queryByTestId('product-on-hand')).toBeNull()
    expect(
      screen.queryByTestId('product-availability-source'),
    ).toBeNull()
    // The committed piece is still fully rendered.
    expect(screen.getByTestId('product-detail-name')).toHaveTextContent(
      SUBJECT.name,
    )
  })

  it('declares inventory unread when availability comes back null', async () => {
    stubFetch(() => jsonResponse(detailPayload({ availability: null })))

    renderAt(`/product/${SUBJECT.id}`)

    await screen.findByTestId('product-availability-degraded')
    expect(screen.queryByTestId('product-on-hand')).toBeNull()
  })

  it('states that catalog copy was not read rather than omitting it', async () => {
    stubFetch(() => jsonResponse(detailPayload({ description: null })))

    renderAt(`/product/${SUBJECT.id}`)

    await waitFor(() =>
      expect(
        screen.getByTestId('product-description-degraded'),
      ).toHaveTextContent(PRODUCT_DETAIL.DESCRIPTION_UNAVAILABLE),
    )
  })
})

// --- Ids outside the committed set --------------------------------------

describe('ProductDetailPage — ids the showcase set does not carry', () => {
  it('renders wholly from the live row', async () => {
    // 10 is one of the four ids Aurora carries and the showcase set omits.
    expect(SHOWCASE_PRODUCTS.some(p => p.id === 10)).toBe(false)
    stubFetch(() =>
      jsonResponse({
        id: 10,
        brand: 'Pellier Home',
        name: 'Aurora Only Piece',
        color: 'Ivory',
        price: 120,
        rating: 4.5,
        reviewCount: 12,
        category: 'Home',
        imageUrl: '/products/fresh-olive-branch-vessel.png',
        badge: null,
        tags: ['ceramic', 'home'],
        description: 'Served entirely from the catalog row.',
        availability: { onHand: 7, warehouses: [] },
      }),
    )

    renderAt('/product/10')

    expect(await screen.findByTestId('product-detail-name')).toHaveTextContent(
      'Aurora Only Piece',
    )
    expect(screen.getByTestId('product-on-hand')).toHaveTextContent('7')
    expect(screen.getByText(PRODUCT_DETAIL.WAREHOUSE_EMPTY)).toBeInTheDocument()
  })

  it('states plainly that an unknown id is not in the edit', async () => {
    stubFetch(() => new Response('null', { status: 404 }))

    renderAt('/product/99999')

    expect(
      await screen.findByTestId('product-detail-not-found'),
    ).toBeInTheDocument()
    expect(screen.getByText(PRODUCT_DETAIL.NOT_FOUND_TITLE)).toBeInTheDocument()
  })

  it('does not attempt a read for a non-numeric id', async () => {
    const impl = stubFetch(() => jsonResponse(detailPayload()))

    renderAt('/product/not-a-number')

    expect(
      await screen.findByTestId('product-detail-not-found'),
    ).toBeInTheDocument()
    const productReads = impl.mock.calls
      .map(call => String(call[0]))
      .filter(url => url.includes('/api/products/'))
    expect(productReads).toEqual([])
  })
})

// --- Actions ------------------------------------------------------------

describe('ProductDetailPage — actions', () => {
  it('adds the piece to the bag with its catalog identity', async () => {
    const user = userEvent.setup()
    stubFetch(() => jsonResponse(detailPayload()))

    renderAt(`/product/${SUBJECT.id}`)
    await user.click(screen.getByTestId('product-detail-add'))

    expect(addToCart).toHaveBeenCalledWith({
      productId: SUBJECT.id,
      name: SUBJECT.name,
      price: SUBJECT.price,
      image: SUBJECT.imageUrl,
      origin: 'manual',
    })
  })

  it('seeds the shopper drawer with questions that name the piece', async () => {
    const user = userEvent.setup()
    stubFetch(() => jsonResponse(detailPayload()))

    renderAt(`/product/${SUBJECT.id}`)

    await user.click(screen.getByTestId('product-detail-ask'))
    expect(openDrawerWithQuery).toHaveBeenCalledWith(
      PRODUCT_DETAIL.askQuestion(SUBJECT.name),
    )

    await user.click(screen.getByTestId('product-check-stock'))
    expect(openDrawerWithQuery).toHaveBeenCalledWith(
      PRODUCT_DETAIL.stockQuestion(SUBJECT.name),
    )
  })
})
