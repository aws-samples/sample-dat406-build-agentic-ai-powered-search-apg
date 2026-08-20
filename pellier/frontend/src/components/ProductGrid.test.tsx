/**
 * ProductGrid tests — render contract.
 *
 * The grid renders every showcase product synchronously. The earlier parallax
 * reveal was dropped (see ProductCard.tsx header comment) because the
 * pre-reveal `opacity: 0` left the grid invisible in real browsers whenever
 * IntersectionObserver didn't fire — the landmark can't hide itself.
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import { describe, expect, it, vi } from 'vitest'

import ProductGrid from './ProductGrid'
import { SHOWCASE_PRODUCTS } from '../data/showcaseProducts'

// Cards link to /product/:id, so the grid needs router context.
function renderGrid(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('ProductGrid — render contract', () => {
  it('renders all 9 showcase cards in declaration order', () => {
    renderGrid(<ProductGrid />)

    for (const [index, product] of SHOWCASE_PRODUCTS.entries()) {
      const card = screen.getByTestId(`product-card-${product.id}`)
      expect(card).toBeInTheDocument()
      expect(card).toHaveAttribute('data-index', String(index % 3))
    }
  })

  it('hides Add to bag when no action handler is provided', () => {
    renderGrid(<ProductGrid />)

    for (const product of SHOWCASE_PRODUCTS) {
      expect(
        screen.queryByTestId(`product-card-add-${product.id}`),
      ).not.toBeInTheDocument()
    }
    for (const product of SHOWCASE_PRODUCTS) {
      expect(
        screen.getByTestId(`product-card-details-${product.id}`),
      ).not.toHaveAttribute('open')
    }
  })

  it('calls the supplied Add to bag handler with the selected product', async () => {
    const user = userEvent.setup()
    const onAddToBag = vi.fn()
    renderGrid(
      <ProductGrid
        products={SHOWCASE_PRODUCTS.slice(0, 1)}
        onAddToBag={onAddToBag}
      />,
    )

    await user.click(
      screen.getByTestId(`product-card-add-${SHOWCASE_PRODUCTS[0].id}`),
    )
    expect(onAddToBag).toHaveBeenCalledWith(SHOWCASE_PRODUCTS[0])
  })

  it('respects the `products` prop when provided', () => {
    const subset = SHOWCASE_PRODUCTS.slice(0, 3)
    renderGrid(<ProductGrid products={subset} />)

    for (const product of subset) {
      expect(
        screen.getByTestId(`product-card-${product.id}`),
      ).toBeInTheDocument()
    }
    expect(
      screen.queryByTestId(`product-card-${SHOWCASE_PRODUCTS[4].id}`),
    ).toBeNull()
  })
})
