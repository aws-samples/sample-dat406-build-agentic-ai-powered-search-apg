import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  persona: null as null | { id: string },
}))

vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({ persona: mocks.persona }),
}))

import BecauseYouAsked from './BecauseYouAsked'

describe('BecauseYouAsked', () => {
  beforeEach(() => {
    mocks.persona = null
  })

  it('pairs the four canonical stories with quiet catalog imagery', () => {
    render(<BecauseYouAsked />)

    expect(
      screen.getByRole('heading', { name: 'Stories worth exploring.' }),
    ).toBeInTheDocument()
    expect(
      screen.getAllByRole('img', { name: /./ }),
    ).toHaveLength(4)
    expect(
      screen.getByRole('img', {
        name: 'Stoneware pour-over set for a morning ritual',
      }),
    ).toHaveAttribute('src', '/products/theo-stoneware-pour-over.png')
  })

  it('switches the images with the active editorial profile', () => {
    mocks.persona = { id: 'marco' }
    render(<BecauseYouAsked />)

    expect(
      screen.getByRole('heading', { name: 'Stories for the road.' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: 'Leather weekend holdall ready for travel' }),
    ).toBeInTheDocument()
  })
})
