import { render, screen, waitFor } from '@testing-library/react'
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

    for (const persona of LOCAL_PERSONAS) {
      const photo = screen
        .getByTestId(`persona-card-${persona.id}`)
        .querySelector<HTMLImageElement>('.pm-avatar-photo')

      expect(photo).not.toBeNull()
      expect(photo).toHaveAttribute('src', getPersonaPhoto(persona.id))
    }
  })
})
