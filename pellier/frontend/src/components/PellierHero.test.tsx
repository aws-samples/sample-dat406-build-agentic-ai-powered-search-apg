import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PellierHero from './PellierHero'

const switchPersona = vi.fn()
const openDrawerWithQuery = vi.fn()
let persona: { id: string; avatar_color: string } | null = null

vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona,
    switchPersona,
    switching: false,
  }),
}))

vi.mock('../contexts/UIContext', () => ({
  useUI: () => ({ openDrawerWithQuery }),
}))

vi.mock('../hooks/useVoiceSearch', () => ({
  useVoiceSearch: () => ({
    isListening: false,
    startListening: vi.fn(),
    stopListening: vi.fn(),
  }),
}))

describe('PellierHero primary action', () => {
  beforeEach(() => {
    persona = null
    switchPersona.mockReset()
    openDrawerWithQuery.mockReset()
  })

  it('keeps profile selection in the hero without a duplicate edit rail', () => {
    render(<PellierHero />)

    expect(screen.getByTestId('hero-profile-marco')).toBeInTheDocument()
    expect(screen.getByTestId('hero-profile-anna')).toBeInTheDocument()
    expect(screen.getByTestId('hero-profile-theo')).toBeInTheDocument()
    expect(screen.queryByTestId('pellier-edit-selector')).not.toBeInTheDocument()
    expect(screen.queryByTestId('pellier-hero-trust')).not.toBeInTheDocument()
  })

  it('uses the existing persona transition from the hero', () => {
    render(<PellierHero />)

    fireEvent.click(screen.getByTestId('hero-profile-anna'))
    expect(switchPersona).toHaveBeenCalledWith('anna')
  })

  it('keeps Marco floor-check proof visible without changing its query', () => {
    persona = { id: 'marco', avatar_color: '#7a263a' }
    render(<PellierHero />)

    const floorCheck = screen.getByRole('button', {
      name: 'Check Hadley stock in Brooklyn',
    })
    expect(screen.getByLabelText('Suggested queries').children).toHaveLength(3)

    fireEvent.click(floorCheck)
    expect(openDrawerWithQuery).toHaveBeenCalledWith(
      'Hadley availability in Brooklyn',
    )
  })
})
