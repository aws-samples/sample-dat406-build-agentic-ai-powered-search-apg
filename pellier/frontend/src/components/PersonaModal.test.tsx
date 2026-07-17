import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPersonaPhoto } from '../data/personaPhotos'
import { LOCAL_PERSONAS } from '../data/personas'
import PersonaModal from './PersonaModal'

vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona: null,
    switchPersona: vi.fn(),
    signOut: vi.fn(),
    switching: false,
  }),
}))

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('PersonaModal', () => {
  it('uses the shared Marco, Anna, and Theo headshots', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify(LOCAL_PERSONAS), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    render(<PersonaModal open onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByTestId('persona-card-marco')).toBeInTheDocument()
    })

    for (const persona of LOCAL_PERSONAS) {
      const image = screen
        .getByTestId(`persona-card-${persona.id}`)
        .querySelector<HTMLImageElement>('.pm-avatar-photo')

      expect(image).not.toBeNull()
      expect(image).toHaveAttribute('src', getPersonaPhoto(persona.id))
    }
  })
})
