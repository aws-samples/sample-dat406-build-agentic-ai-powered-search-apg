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
})

describe('PellierHero signature suggestions', () => {
  beforeEach(() => {
    switchPersona.mockReset()
    openDrawerWithQuery.mockReset()
  })

  /**
   * Each persona's journey turns on one distinctive tool. That turn sits at
   * index 3 for Marco and Theo, outside the default first-three window, so
   * without explicit handling their defining query never appears on sign-on.
   * These assert the query is reachable, and that clicking it sends the
   * canonical string verbatim rather than the shortened pill label.
   */
  it.each([
    ['marco', 'Is the Hadley shirt at the Brooklyn warehouse?', 'floor_check'],
    [
      'theo',
      "My Wabi-Sabi Bowl arrived chipped. Please file a damaged return – my customer id is 'theo'.",
      'process_return',
    ],
  ])(
    'surfaces %s’s signature %s turn on sign-on',
    (personaId, canonicalQuery, _tool) => {
      persona = { id: personaId, avatar_color: '#000' }
      render(<PellierHero />)

      const pills = screen.getByTestId('pellier-hero-pills')
      // The pill may render a short label, so match on the button whose click
      // submits the canonical query rather than on visible text.
      const buttons = Array.from(pills.querySelectorAll('button'))
      expect(buttons.length).toBeGreaterThan(0)

      fireEvent.click(buttons[0])
      expect(openDrawerWithQuery).toHaveBeenCalledWith(canonicalQuery)
    },
  )

  it('leaves a persona whose signature turn is already visible untouched', () => {
    // Anna's turns are all hybrid retrieval, so there is no signature turn to
    // promote and the default first-three ordering must stand.
    persona = { id: 'anna', avatar_color: '#000' }
    render(<PellierHero />)

    const pills = screen.getByTestId('pellier-hero-pills')
    const buttons = Array.from(pills.querySelectorAll('button'))
    fireEvent.click(buttons[0])

    expect(openDrawerWithQuery).toHaveBeenCalledWith(
      'A thoughtful gift for someone who loves morning rituals',
    )
  })
})
