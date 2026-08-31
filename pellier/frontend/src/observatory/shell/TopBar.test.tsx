import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../../contexts/PersonaContext', () => ({
  usePersona: () => ({ persona: null }),
}))

vi.mock('../../components/PersonaModal', () => ({
  default: () => null,
}))

vi.mock('../../shared', () => ({
  PresencePill: () => null,
}))

import TopBar from './TopBar'

function LocationProbe() {
  const { pathname } = useLocation()
  return <output data-testid="location">{pathname}</output>
}

describe('Pellier Observatory TopBar', () => {
  it('makes the Storefront the only top-bar exit', () => {
    render(
      <MemoryRouter initialEntries={['/observatory/proof-board']}>
        <TopBar />
      </MemoryRouter>,
    )

    const backLink = screen.getByRole('link', {
      name: 'Back to Pellier',
    })
    expect(backLink).toHaveAttribute('href', '/')
    expect(backLink).toHaveTextContent('Pellier')
    expect(backLink).not.toHaveTextContent('Storefront')
    expect(backLink).toHaveClass('pellier-home-link')
    expect(backLink.querySelector('.pellier-home-chip')).toHaveTextContent('P')
    expect(backLink.querySelector('.pellier-home-wordmark')).toHaveTextContent(
      'Pellier',
    )
    expect(screen.queryByRole('link', { name: /github/i })).not.toBeInTheDocument()
  })

  it('keeps supporting routes under Proof & References', () => {
    render(
      <MemoryRouter initialEntries={['/observatory/proof-board']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('link', { name: 'Proof & References' }),
    ).toHaveAttribute('aria-current', 'page')
    expect(
      screen.getByRole('link', { name: 'Live Workbench' }),
    ).not.toHaveAttribute('aria-current')
    expect(
      screen.getByRole('link', { name: 'Lab Collection' }),
    ).not.toHaveAttribute('aria-current')
  })

  it('offers the collection, workbench, and reference index as first-level views', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/observatory']}>
        <TopBar />
        <LocationProbe />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Pellier Observatory' })).toHaveAttribute(
      'href',
      '/observatory',
    )
    expect(screen.queryByRole('button', { name: /Pellier Observatory view/i })).not.toBeInTheDocument()
    expect(
      screen.getAllByRole('link', {
        name: /Lab Collection|Live Workbench|Proof & References/,
      }),
    ).toHaveLength(3)

    expect(
      screen.getByRole('link', { name: 'Lab Collection' }),
    ).toHaveAttribute('aria-current', 'page')

    await user.click(screen.getByRole('link', { name: 'Live Workbench' }))
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/observatory/workbench',
    )
  })

  it('keeps exercise details within the Lab Collection tab', () => {
    render(
      <MemoryRouter initialEntries={['/observatory/labs/fail-closed-policy']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('link', { name: 'Lab Collection' }),
    ).toHaveAttribute('aria-current', 'page')
  })
})
