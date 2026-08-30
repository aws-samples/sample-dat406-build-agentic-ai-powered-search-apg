import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ProductArtifactCard from './ProductArtifactCard'
import type { ChatProduct } from '../services/chat'

const PRODUCT: ChatProduct = {
  id: 41,
  name: 'Coral Lacquer Catchall',
  price: 325.36,
  image: '',
  category: 'Home Decor',
}

describe('ProductArtifactCard shopping details', () => {
  it('labels missing stock evidence as not verified instead of checked', () => {
    render(<ProductArtifactCard product={PRODUCT} />)

    const details = screen.getByLabelText('Shopping details')
    expect(within(details).getByText('Stock')).toBeInTheDocument()
    expect(within(details).getByText('Not verified')).toBeInTheDocument()
    expect(within(details).queryByText('Checked')).not.toBeInTheDocument()
  })

  it('shows only product facts carried by the storefront contract', () => {
    render(<ProductArtifactCard product={PRODUCT} />)

    const details = screen.getByLabelText('Shopping details')
    expect(within(details).getByText('Category')).toBeInTheDocument()
    expect(within(details).getByText('Home Decor')).toBeInTheDocument()
    expect(within(details).queryByText('Material')).not.toBeInTheDocument()
    expect(within(details).queryByText('Service')).not.toBeInTheDocument()
  })

  it('renders measured inventory when the response carries it', () => {
    render(
      <ProductArtifactCard
        product={{ ...PRODUCT, quantity: 4, inStock: true }}
      />,
    )

    const details = screen.getByLabelText('Shopping details')
    expect(within(details).getByText('4 available')).toBeInTheDocument()
  })
})
