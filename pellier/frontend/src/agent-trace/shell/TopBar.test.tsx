import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

  it('groups the Labs picker by interaction while retaining governed proof routes', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={['/pellier-labs/proof-board']}>
        <TopBar />
      </MemoryRouter>,
    )

    await user.click(screen.getByTestId('pellier-labs-view-switcher'))

    expect(screen.getByText('Interactive')).toBeInTheDocument()
    expect(screen.getByText('Reference')).toBeInTheDocument()
    expect(
      screen.getByRole('menuitem', { name: /audit proof/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('menuitem', { name: /gateway & policy/i }),
    ).toBeInTheDocument()
  })
})
