import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Session } from '../../types'

vi.mock('../../hooks/useObservatoryData', () => ({
  useObservatoryData: () => ({
    data: [
      {
        id: 'aurora-session-7',
        personaId: 'anna',
        openingQuery: 'Durable live Aurora session',
        elapsedMs: 4200,
        agentCount: 2,
        routingPattern: 'Storefront Dispatcher',
        timestamp: '2026-08-30T12:00:00.000Z',
        status: 'complete',
      },
      {
        id: 'aurora-session-8',
        personaId: 'marco',
        openingQuery: 'A different live Aurora session',
        elapsedMs: 1300,
        agentCount: 1,
        routingPattern: 'Managed Gateway',
        timestamp: '2026-08-30T13:00:00.000Z',
        status: 'complete',
      },
    ] satisfies Session[],
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('../../../contexts/PersonaContext', () => ({
  usePersona: () => ({
    persona: {
      id: 'anna',
      display_name: 'Anna',
    },
  }),
}))

import SessionsList from './SessionsList'

describe('SessionsList live data boundary', () => {
  it('shows the signed-in shopper only durable Aurora sessions, not canned turns', () => {
    render(
      <MemoryRouter>
        <SessionsList />
      </MemoryRouter>,
    )

    expect(screen.getByText('Durable live Aurora session')).toBeInTheDocument()
    expect(screen.queryByText('A different live Aurora session')).not.toBeInTheDocument()
    expect(
      screen.queryByText('What linen do you have for 10 days in Goa?'),
    ).not.toBeInTheDocument()
  })
})
