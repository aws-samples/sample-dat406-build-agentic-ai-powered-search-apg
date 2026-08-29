import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import PellierChatBody from './PellierChatBody'
import type { AgentChatMessage } from '../hooks/useAgentChat'

function message(over: Partial<AgentChatMessage> = {}): AgentChatMessage {
  return {
    role: 'assistant',
    content: 'The linen edit is ready.',
    timestamp: new Date('2026-08-28T14:00:00Z'),
    agentStatus: 'complete',
    ...over,
  }
}

function renderBody(chatMessage: AgentChatMessage) {
  return render(
    <PellierChatBody
      messages={[chatMessage]}
      sendMessage={vi.fn()}
      retryMessage={vi.fn()}
      onEditRequest={vi.fn()}
      onAuthenticate={vi.fn()}
      addToCart={vi.fn()}
      persona={null}
    />,
  )
}

describe('storefront source disclosure', () => {
  it('keeps completed source details collapsed until the shopper asks', async () => {
    const user = userEvent.setup()
    renderBody(message({
      sourceActivity: [
        {
          source: 'Local PostgreSQL',
          details: [
            '4 profile facts, 2 recent orders',
            '3 live queries · customer_facts, orders',
          ],
          status: 'complete',
        },
        {
          source: 'Amazon Bedrock',
          details: ['Dispatcher routed recommendation'],
          status: 'complete',
        },
      ],
    }))

    const disclosure = screen.getByRole('button', { name: /match details/i })
    expect(disclosure).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Local PostgreSQL')).toBeNull()

    await user.click(disclosure)

    expect(disclosure).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Local PostgreSQL')).toBeInTheDocument()
    expect(screen.getByText('Amazon Bedrock')).toBeInTheDocument()
    expect(screen.getByText('4 profile facts, 2 recent orders')).toBeInTheDocument()
    expect(screen.getByText(/3 live queries/)).toBeInTheDocument()
    expect(screen.getAllByText('Used')).toHaveLength(2)
  })

  it('opens live source work and labels it as active', () => {
    renderBody(message({
      content: '',
      agentStatus: 'streaming',
      sourceActivity: [
        {
          source: 'Amazon Bedrock',
          details: ['Searching the catalog'],
          status: 'in_progress',
        },
      ],
    }))

    const disclosure = screen.getByRole('button', {
      name: /working with live sources/i,
    })
    expect(disclosure).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Amazon Bedrock')).toBeInTheDocument()
    expect(screen.getByText('Searching the catalog')).toBeInTheDocument()
    expect(screen.getByText('Working')).toBeInTheDocument()
  })

  it('labels an unavailable source without presenting it as successful', async () => {
    const user = userEvent.setup()
    renderBody(message({
      sourceActivity: [
        {
          source: 'AgentCore Memory',
          details: ['2 prior turns loaded, write unavailable'],
          status: 'unavailable',
        },
      ],
    }))

    await user.click(screen.getByRole('button', { name: /match details/i }))

    expect(screen.getByText('AgentCore Memory')).toBeInTheDocument()
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
    expect(screen.queryByText('Used')).toBeNull()
  })

  it('renders the backend completed status as finished tool work', async () => {
    const user = userEvent.setup()
    const { container } = renderBody(message({
      agentExecution: {
        agent_steps: [],
        tool_calls: [{
          tool: 'search_products_hybrid',
          timestamp: Date.now(),
          duration_ms: 184,
          status: 'completed',
        }],
        reasoning_steps: [],
        total_duration_ms: 184,
        success_rate: 1,
      },
    }))

    await user.click(screen.getByRole('button', { name: /match details/i }))

    expect(container.querySelector('.ec-toolcall-complete')).not.toBeNull()
    expect(container.querySelector('.ec-toolcall-active')).toBeNull()
    expect(screen.getByText('184ms')).toBeInTheDocument()
  })
})
