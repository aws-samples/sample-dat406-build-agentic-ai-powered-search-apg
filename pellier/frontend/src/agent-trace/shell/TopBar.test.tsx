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

  it('keeps supporting routes under Optional Deep Dives', () => {
    render(
      <MemoryRouter initialEntries={['/pellier-labs/proof-board']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('link', { name: 'Optional Deep Dives' }),
    ).toHaveAttribute('aria-current', 'page')
    expect(
      screen.getByRole('link', { name: 'Live Workbench' }),
    ).not.toHaveAttribute('aria-current')
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
    expect(screen.queryByRole('button', { name: /Pellier Labs view/i })).not.toBeInTheDocument()
    expect(
      screen.getAllByRole('link', {
        name: /Live Workbench|Optional Deep Dives/,
      }),
    ).toHaveLength(2)

    await user.click(screen.getByRole('link', { name: 'Optional Deep Dives' }))
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/pellier-labs/references',
    )
  })
})
