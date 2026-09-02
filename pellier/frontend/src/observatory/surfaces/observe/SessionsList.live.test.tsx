import { fireEvent, render, screen } from '@testing-library/react'
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
      ...Array.from({ length: 9 }, (_, index) => ({
        id: `aurora-session-anna-${index + 1}`,
        personaId: 'anna',
        openingQuery: `Anna durable session ${index + 1}`,
        elapsedMs: 1800 + index,
        agentCount: 2,
        routingPattern: 'Storefront Dispatcher',
        timestamp: new Date(
          Date.parse('2026-08-30T12:01:00.000Z') + index * 60_000,
        ).toISOString(),
        status: 'complete' as const,
      })),
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

  it('bounds the initial session history and reveals the next page on request', () => {
    render(
      <MemoryRouter>
        <SessionsList />
      </MemoryRouter>,
    )

    expect(screen.getByText('Showing 8 of 10 recorded sessions')).toBeInTheDocument()
    expect(screen.queryByText('Anna durable session 9')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('sessions-load-more'))

    expect(screen.getByText('Showing 10 of 10 recorded sessions')).toBeInTheDocument()
    expect(screen.getByText('Anna durable session 9')).toBeInTheDocument()
    expect(screen.queryByTestId('sessions-load-more')).not.toBeInTheDocument()
  })
})
