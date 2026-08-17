import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  switchPersona: vi.fn(),
  signOut: vi.fn(),
}))

vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona: null,
    switchPersona: mocks.switchPersona,
    signOut: mocks.signOut,
    switching: false,
  }),
}))

import { getPersonaPhoto } from '../data/personaPhotos'
import { LOCAL_PERSONAS } from '../data/personas'
import PersonaModal from './PersonaModal'

describe('PersonaModal', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        json: async () => LOCAL_PERSONAS,
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the shared portrait for every seeded persona', async () => {
    render(<PersonaModal open onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByTestId('persona-card-marco')).toBeInTheDocument()
    })
    expect(
      screen.getByRole('dialog', { name: 'Choose a workshop profile.' }),
    ).toHaveAttribute('aria-modal', 'true')

    for (const persona of LOCAL_PERSONAS) {
      const photo = screen
        .getByTestId(`persona-card-${persona.id}`)
        .querySelector<HTMLImageElement>('.pm-avatar-photo')

      expect(photo).not.toBeNull()
      expect(photo).toHaveAttribute('src', getPersonaPhoto(persona.id))
    }
  })

  it('keeps the overlay mounted through the close exit', async () => {
    const onClose = vi.fn()
    const { rerender } = render(<PersonaModal open onClose={onClose} />)

    await screen.findByRole('dialog', { name: 'Choose a workshop profile.' })
    fireEvent.click(screen.getByTestId('persona-modal-close'))
    expect(onClose).toHaveBeenCalledTimes(1)

    rerender(<PersonaModal open={false} onClose={onClose} />)
    expect(
      screen.getByRole('dialog', { name: 'Choose a workshop profile.' }),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(
        screen.queryByRole('dialog', { name: 'Choose a workshop profile.' }),
      ).not.toBeInTheDocument()
    })
  })
})
