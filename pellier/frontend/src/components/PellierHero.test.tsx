import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PellierHero from './PellierHero'

const switchPersona = vi.fn()
const openDrawerWithQuery = vi.fn()

const PROFILES = [
  {
    id: 'fresh',
    display_name: 'Pellier guest',
    role_tag: 'New visitor',
    blurb: 'Live guest profile.',
    avatar_color: '#000',
    avatar_initial: 'P',
    membership: 'registered',
    hero_image: '/products/landing-hero-weekender.webp',
    hero_alt: 'Guest profile',
    hero_subheadline: 'Live guest profile.',
    stats: { visits: 0, orders: 0, last_seen_days: null },
  },
  {
    id: 'anna',
    display_name: 'Anna',
    role_tag: 'Gift-giver',
    blurb: 'Live Anna profile.',
    avatar_color: '#000',
    avatar_initial: 'A',
    membership: 'circle',
    hero_image: '/products/hero-anna.webp',
    hero_alt: 'Anna profile',
    hero_subheadline: 'Live Anna profile.',
    stats: { visits: 1, orders: 1, last_seen_days: 1 },
  },
  {
    id: 'marco',
    display_name: 'Marco',
    role_tag: 'Returning',
    blurb: 'Live Marco profile.',
    avatar_color: '#000',
    avatar_initial: 'M',
    membership: 'maison',
    hero_image: '/products/hero-marco.webp',
    hero_alt: 'Marco profile',
    hero_subheadline: 'Live Marco profile.',
    stats: { visits: 1, orders: 1, last_seen_days: 1 },
  },
  {
    id: 'theo',
    display_name: 'Theo',
    role_tag: 'Home + slow craft',
    blurb: 'Live Theo profile.',
    avatar_color: '#000',
    avatar_initial: 'T',
    membership: 'registered',
    hero_image: '/products/hero-theo.webp',
    hero_alt: 'Theo profile',
    hero_subheadline: 'Live Theo profile.',
    stats: { visits: 1, orders: 1, last_seen_days: 1 },
  },
]

let persona: (typeof PROFILES)[number] | null = null

vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona,
    switchPersona,
    switching: false,
    switchError: null,
  }),
}))

vi.mock('../contexts/UIContext', () => ({
  useUI: () => ({ openDrawerWithQuery }),
}))

function liveFetch(input: RequestInfo | URL): Promise<Response> {
  const url = String(input)
  if (url.startsWith('/api/observatory/personas')) {
    return Promise.resolve(new Response(JSON.stringify(PROFILES), { status: 200 }))
  }
  if (url.startsWith('/api/observatory/scenarios')) {
    return Promise.resolve(
      new Response(
        JSON.stringify({
          scenarios: [
            { id: 1, ordinal: 1, prompt: 'A live Aurora scenario' },
            { id: 2, ordinal: 2, prompt: 'A second live scenario' },
          ],
        }),
        { status: 200 },
      ),
    )
  }
  return Promise.reject(new Error(`Unexpected request: ${url}`))
}

describe('PellierHero', () => {
  beforeEach(() => {
    persona = null
    switchPersona.mockReset()
    openDrawerWithQuery.mockReset()
    vi.stubGlobal('fetch', vi.fn(liveFetch))
  })

  it('keeps profile selection in the hero without a duplicate edit rail', async () => {
    render(<PellierHero />)

    expect(await screen.findByTestId('hero-profile-marco')).toBeInTheDocument()
    expect(screen.getByTestId('hero-profile-anna')).toBeInTheDocument()
    expect(screen.getByTestId('hero-profile-theo')).toBeInTheDocument()
    expect(screen.queryByTestId('pellier-edit-selector')).not.toBeInTheDocument()
    expect(screen.queryByTestId('pellier-hero-trust')).not.toBeInTheDocument()
  })

  it('uses the existing persona transition from the hero', async () => {
    render(<PellierHero />)

    fireEvent.click(await screen.findByTestId('hero-profile-anna'))
    expect(switchPersona).toHaveBeenCalledWith('anna')
  })

  it('submits an Aurora-backed guided request for a selected persona', async () => {
    persona = PROFILES[1]
    render(<PellierHero />)

    fireEvent.click(await screen.findByRole('button', { name: 'A live Aurora scenario' }))
    expect(openDrawerWithQuery).toHaveBeenCalledWith('A live Aurora scenario')
  })

  it('re-reads hero metadata from Aurora instead of trusting a stale profile snapshot', async () => {
    persona = {
      ...PROFILES[2],
      hero_image: '',
      hero_alt: '',
      hero_subheadline: '',
    }
    render(<PellierHero />)

    expect(
      await screen.findByAltText(
        'Marco profile',
      ),
    ).toHaveAttribute('src', '/products/hero-marco-960.webp')
  })
})
