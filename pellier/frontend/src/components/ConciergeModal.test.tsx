import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import ConciergeModal from './ConciergeModal'

const retryMessage = vi.fn()
const setInputValue = vi.fn()
const openModal = vi.fn()

vi.mock('../contexts/UIContext', () => ({
  useUI: () => ({
    activeModal: 'concierge',
    closeModal: vi.fn(),
    openModal,
    openComparison: vi.fn(),
    consumePendingQuery: vi.fn(),
  }),
}))

vi.mock('../contexts/LayoutContext', () => ({
  useLayout: () => ({
    workshopMode: 'agentic',
    guardrailsEnabled: true,
  }),
}))

vi.mock('../contexts/CartContext', () => ({
  useCart: () => ({ addToCart: vi.fn() }),
}))

vi.mock('../contexts/PersonaContext', () => ({
  usePersona: () => ({ persona: null }),
}))

vi.mock('../hooks/useAgentChat', () => ({
  useAgentChat: () => ({
    messages: [
      {
        role: 'user',
        content: 'process this return',
        timestamp: new Date('2026-07-16T12:00:00Z'),
      },
      {
        role: 'assistant',
        content: '',
        timestamp: new Date('2026-07-16T12:00:01Z'),
        agentStatus: 'complete',
        failure: {
          code: 'policy_denied',
          retryable: false,
          query: 'process this return',
          referenceId: 'policy-deny-42',
        },
      },
    ],
    inputValue: '',
    setInputValue,
    isLoading: false,
    backendOnline: true,
    sendMessage: vi.fn(),
    retryMessage,
    clearChat: vi.fn(),
  }),
}))

describe('ConciergeModal', () => {
  it('renders a typed policy outcome instead of an empty assistant reply', () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/proof-board']}>
        <ConciergeModal />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('dialog', { name: 'Ask Pellier' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Protected action')
    expect(screen.getByRole('alert')).toHaveTextContent('policy-deny-42')
    expect(
      screen.queryByText('Unable to connect. Please check that the backend is running.'),
    ).not.toBeInTheDocument()
  })
})
