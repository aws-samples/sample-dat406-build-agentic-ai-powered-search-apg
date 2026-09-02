import { render, screen } from '@testing-library/react'
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

  it('keeps supporting routes inside the one Observatory workspace', () => {
    render(
      <MemoryRouter initialEntries={['/observatory/proof-board']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('link', { name: 'Labs & Workbench' }),
    ).toHaveAttribute('aria-current', 'page')
    expect(
      screen.queryByRole('link', { name: 'Proof & References' }),
    ).not.toBeInTheDocument()
  })

  it('offers one first-level Labs and Workbench view', () => {
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
      screen.getByRole('link', { name: 'Labs & Workbench' }),
    ).toHaveAttribute('aria-current', 'page')
    expect(
      screen.queryByRole('link', { name: 'Proof & References' }),
    ).not.toBeInTheDocument()
  })

  it('keeps collection, detail, and live routes in one workbench tab', () => {
    render(
      <MemoryRouter
        initialEntries={['/observatory/workbench?lab=fail-closed-policy']}
      >
        <TopBar />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('link', { name: 'Labs & Workbench' }),
    ).toHaveAttribute('aria-current', 'page')
  })
})
