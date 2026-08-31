import { describe, expect, it } from 'vitest'

import { SHOWCASE_PRODUCTS } from '../data/showcaseProducts'
import { selectStorefrontGridProducts } from './PellierPage'

const NINE_PIECE_EDIT = SHOWCASE_PRODUCTS.slice(0, 9)
const TEN_PIECE_EDIT = SHOWCASE_PRODUCTS.slice(0, 10)

describe('selectStorefrontGridProducts', () => {
  it('keeps the featured product in the unsigned nine-piece discovery edit', () => {
    expect(
      selectStorefrontGridProducts(NINE_PIECE_EDIT, null).map(product => product.id),
    ).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9])
  })

  it('keeps named persona edits at one feature plus nine discovery cards', () => {
    expect(
      selectStorefrontGridProducts(TEN_PIECE_EDIT, 'marco').map(product => product.id),
    ).toHaveLength(9)
    expect(
      selectStorefrontGridProducts(TEN_PIECE_EDIT, 'marco')[0]?.id,
    ).not.toBe(TEN_PIECE_EDIT[0]?.id)
  })
})
