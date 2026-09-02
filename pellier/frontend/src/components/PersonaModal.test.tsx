import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPersonaModalPortrait } from '../data/personaPhotos'
import PersonaModal from './PersonaModal'

const LIVE_PERSONAS = [
  {
    id: 'marco',
    display_name: 'Marco',
    role_tag: 'Returning',
    blurb: 'Live Aurora profile.',
    avatar_color: '#5a3528',
    avatar_initial: 'M',
    membership: 'maison',
    stats: { visits: 11, orders: 7, last_seen_days: 21 },
  },
  {
    id: 'anna',
    display_name: 'Anna',
    role_tag: 'Gift-giver',
    blurb: 'Live Aurora profile.',
    avatar_color: '#6b3d2a',
    avatar_initial: 'A',
    membership: 'circle',
    stats: { visits: 6, orders: 5, last_seen_days: 9 },
  },
  {
    id: 'theo',
    display_name: 'Theo',
    role_tag: 'Home + slow craft',
    blurb: 'Live Aurora profile.',
    avatar_color: '#5a4535',
    avatar_initial: 'T',
    membership: 'registered',
    stats: { visits: 8, orders: 4, last_seen_days: 14 },
  },
]

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
        new Response(JSON.stringify(LIVE_PERSONAS), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    render(<PersonaModal open onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByTestId('persona-card-marco')).toBeInTheDocument()
    })

    for (const persona of LIVE_PERSONAS) {
      const image = screen
        .getByTestId(`persona-card-${persona.id}`)
        .querySelector<HTMLImageElement>('.pm-avatar-photo')

      expect(image).not.toBeNull()
      expect(image).toHaveAttribute('src', getPersonaModalPortrait(persona.id))
      expect(image).toHaveAttribute('width', '1200')
      expect(image).toHaveAttribute('height', '1800')
    }
    expect(screen.queryByText('v1.0')).not.toBeInTheDocument()
  })
})
