import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import architecture from '../../../fixtures/architecture.json'

vi.mock('../../../hooks/useObservatoryData', () => ({
  useObservatoryData: () => ({
    data: architecture,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

import RuntimeDetail from './RuntimeDetail'
import StateDetail from './StateDetail'

describe('architecture orchestration truth', () => {
  it('names both shipped paths and the two operator agents', () => {
    render(
      <MemoryRouter>
        <StateDetail />
      </MemoryRouter>,
    )

    expect(screen.getByText(/Storefront uses deterministic Dispatcher/i))
      .toBeInTheDocument()
    expect(screen.getAllByText(/Case Investigator/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Resolution Planner/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/graph invocation never waits for a person/i))
      .toBeInTheDocument()
  })

  it('keeps the PostgreSQL checkpoint outside bounded Runtime invocations', () => {
    render(
      <MemoryRouter>
        <RuntimeDetail />
      </MemoryRouter>,
    )

    expect(screen.getByText(/PostgreSQL, not a suspended Runtime process/i))
      .toBeInTheDocument()
    expect(screen.getByText(/No worker, graph node, or model call stays open/i))
      .toBeInTheDocument()
    expect(screen.getByText(/Human confirmation and governed execution are separate/i))
      .toBeInTheDocument()
  })
})
