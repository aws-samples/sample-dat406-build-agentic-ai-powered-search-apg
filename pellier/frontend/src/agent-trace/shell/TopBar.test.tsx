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

import TopBar from './TopBar'

function LocationProbe() {
  const { pathname } = useLocation()
  return <output data-testid="location">{pathname}</output>
}

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

  it('links to the public Pellier repository in a new tab', () => {
    render(
      <MemoryRouter initialEntries={['/pellier-labs']}>
        <TopBar />
      </MemoryRouter>,
    )

    const repositoryLink = screen.getByRole('link', {
      name: 'View Pellier repository on GitHub',
    })
    expect(repositoryLink).toHaveAttribute(
      'href',
      'https://github.com/aws-samples/sample-pellier-agentic-search-apg',
    )
    expect(repositoryLink).toHaveAttribute('target', '_blank')
    expect(repositoryLink).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('keeps supporting routes under Optional References', () => {
    render(
      <MemoryRouter initialEntries={['/pellier-labs/agents']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Live Workbench' })).not.toHaveAttribute(
      'aria-current',
    )
    expect(
      screen.getByRole('link', { name: 'Optional References' }),
    ).toHaveAttribute('aria-current', 'page')
  })

  it('offers only the workbench and reference index as first-level views', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/pellier-labs']}>
        <TopBar />
        <LocationProbe />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Pellier Labs' })).toHaveAttribute(
      'href',
      '/pellier-labs',
    )
    expect(screen.queryByText(/concierge online/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Pellier Labs view/i })).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Live Workbench|Optional References/ })).toHaveLength(2)

    await user.click(screen.getByRole('link', { name: 'Optional References' }))
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/pellier-labs/references',
    )
  })
})
