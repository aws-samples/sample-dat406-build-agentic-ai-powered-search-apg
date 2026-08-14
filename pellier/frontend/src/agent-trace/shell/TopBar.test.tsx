import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
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

describe('Pellier Labs TopBar', () => {
  it('provides one explicit route back to Pellier', () => {
    render(
      <MemoryRouter initialEntries={['/pellier-labs/proof-board']}>
        <TopBar />
      </MemoryRouter>,
    )

    const backLink = screen.getByRole('link', { name: 'Back to Pellier' })
    expect(backLink).toHaveAttribute('href', '/')
  })

  it('keeps the current Labs route in the breadcrumb', () => {
    render(
      <MemoryRouter initialEntries={['/pellier-labs/proof-board']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent(
      'Proof Board',
    )
    expect(
      screen.getByRole('navigation', { name: 'Breadcrumb' }),
    ).not.toHaveTextContent('Pellier Labs')
  })

  it('does not expose a secondary Labs navigation drawer', () => {
    render(
      <MemoryRouter initialEntries={['/pellier-labs']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(
      screen.queryByRole('button', { name: /lab navigation/i }),
    ).not.toBeInTheDocument()
  })
})
