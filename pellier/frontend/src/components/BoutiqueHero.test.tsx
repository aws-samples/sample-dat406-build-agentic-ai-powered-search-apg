import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import BoutiqueHero from './BoutiqueHero'

const switchPersona = vi.fn()
const signOut = vi.fn()
let persona: { id: string; avatar_color: string } | null = null

vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona,
    switchPersona,
    signOut,
    switching: false,
  }),
}))

vi.mock('../contexts/UIContext', () => ({
  useUI: () => ({ openDrawerWithQuery: vi.fn() }),
}))

vi.mock('../hooks/useVoiceSearch', () => ({
  useVoiceSearch: () => ({
    isListening: false,
    startListening: vi.fn(),
    stopListening: vi.fn(),
  }),
}))

vi.mock('../shared', () => ({
  PresencePill: () => <span>Presence</span>,
}))

describe('BoutiqueHero edit selector', () => {
  beforeEach(() => {
    persona = null
    switchPersona.mockReset()
    signOut.mockReset()
  })

  it('offers four editorial edits without exposing customer names', () => {
    render(<BoutiqueHero />)

    expect(screen.getByTestId('boutique-edit-selector')).toBeInTheDocument()
    expect(screen.getByTestId('boutique-edit-fresh')).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByTestId('boutique-edit-fresh')).toHaveTextContent(
      'The Resort Edit',
    )
    expect(screen.getByTestId('boutique-edit-marco')).toHaveTextContent(
      'The Travel Edit',
    )
    expect(screen.getByTestId('boutique-edit-anna')).toHaveTextContent(
      'The Gift Edit',
    )
    expect(screen.getByTestId('boutique-edit-theo')).toHaveTextContent(
      'The Home Rituals Edit',
    )

    const trust = screen.getByTestId('boutique-hero-trust')
    const edits = screen.getByTestId('boutique-edit-selector')
    expect(trust.compareDocumentPosition(edits) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('uses the existing persona transitions for each edit', () => {
    persona = { id: 'marco', avatar_color: '#5a3528' }
    render(<BoutiqueHero />)

    fireEvent.click(screen.getByTestId('boutique-edit-anna'))
    expect(switchPersona).toHaveBeenCalledWith('anna')

    fireEvent.click(screen.getByTestId('boutique-edit-fresh'))
    expect(signOut).toHaveBeenCalledOnce()
  })
})
