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

  it('shows the current Labs view in the switcher', () => {
    render(
      <MemoryRouter initialEntries={['/pellier-labs/agents']}>
        <TopBar />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('button', { name: 'Pellier Labs view: Agents' }),
    ).toBeInTheDocument()
  })

  it('keeps the top bar focused on useful Labs views', async () => {
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

    const switcher = screen.getByRole('button', {
      name: 'Pellier Labs view: Live workbench',
    })
    expect(screen.queryByRole('menuitem', { name: /Proof Board/i })).not.toBeInTheDocument()
    await user.click(switcher)
    expect(screen.getByText('Guided demo')).toBeInTheDocument()
    expect(screen.getByText('Inspect')).toBeInTheDocument()
    expect(screen.getByText('Evaluate')).toBeInTheDocument()
    await user.click(screen.getByRole('menuitem', { name: /Architecture/i }))
    expect(screen.getByTestId('location')).toHaveTextContent('/pellier-labs/architecture')

    await user.click(
      screen.getByRole('button', { name: 'Pellier Labs view: Architecture' }),
    )
    await user.click(screen.getByRole('menuitem', { name: /Evaluations/i }))
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/pellier-labs/evaluations',
    )
  })
})
