import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AgentChatMessage } from '../hooks/useAgentChat'
import { PERSONA_LAB_THREADS } from '../data/personaCurations'
import StorefrontThreadGuide, {
  storefrontThreadProgress,
} from './StorefrontThreadGuide'

function message(
  role: AgentChatMessage['role'],
  content: string,
): AgentChatMessage {
  return { role, content, timestamp: new Date('2026-09-01T12:00:00Z') }
}

function renderedMessages(
  persona: keyof typeof PERSONA_LAB_THREADS,
  turns: number,
): AgentChatMessage[] {
  const thread = PERSONA_LAB_THREADS[persona]
  return Array.from({ length: turns }).flatMap((_, index) => [
    message('user', thread.turns[index]),
    message('assistant', `Grounded reply for ${index + 1}`),
  ])
}

describe('StorefrontThreadGuide', () => {
  it.each(['marco', 'anna', 'theo'] as const)(
    'starts the shared %s conversation with its canonical first prompt',
    (personaId) => {
      const onSend = vi.fn()
      const thread = PERSONA_LAB_THREADS[personaId]

      render(
        <StorefrontThreadGuide
          personaId={personaId}
          messages={[]}
          isLoading={false}
          onSend={onSend}
          onRestart={vi.fn()}
        />,
      )

      fireEvent.click(screen.getByRole('button', { name: thread.turns[0] }))
      expect(onSend).toHaveBeenCalledWith(thread.turns[0])
    },
  )

  it('waits for the real assistant reply before exposing the next prompt', () => {
    const thread = PERSONA_LAB_THREADS.anna
    const onSend = vi.fn()
    const firstTurn = [message('user', thread.turns[0])]

    const { rerender } = render(
      <StorefrontThreadGuide
        personaId="anna"
        messages={firstTurn}
        isLoading
        onSend={onSend}
        onRestart={vi.fn()}
      />,
    )

    expect(screen.queryByTestId('storefront-thread-guide')).not.toBeInTheDocument()

    rerender(
      <StorefrontThreadGuide
        personaId="anna"
        messages={[...firstTurn, message('assistant', 'Grounded reply')]}
        isLoading={false}
        onSend={onSend}
        onRestart={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: thread.turns[1] }))
    expect(onSend).toHaveBeenCalledWith(thread.turns[1])
  })

  it('offers the final recall prompt only after the first two turns', () => {
    const thread = PERSONA_LAB_THREADS.marco
    const onSend = vi.fn()

    render(
      <StorefrontThreadGuide
        personaId="marco"
        messages={renderedMessages('marco', 2)}
        isLoading={false}
        onSend={onSend}
        onRestart={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: thread.turns[2] }))
    expect(onSend).toHaveBeenCalledWith(thread.turns[2])
  })

  it('finishes cleanly and restarts from the same shared thread', () => {
    const onRestart = vi.fn()

    render(
      <StorefrontThreadGuide
        personaId="theo"
        messages={renderedMessages('theo', 3)}
        isLoading={false}
        onSend={vi.fn()}
        onRestart={onRestart}
      />,
    )

    expect(screen.getByText('That thread is complete.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Start again' }))
    expect(onRestart).toHaveBeenCalledOnce()
  })

  it('gets out of the way when the shopper takes a different path', () => {
    const thread = PERSONA_LAB_THREADS.marco
    const progress = storefrontThreadProgress(
      [message('user', thread.turns[0]), message('user', 'Hadley availability in Brooklyn')],
      thread,
      false,
    )

    expect(progress).toEqual({ status: 'hidden', nextIndex: null })
  })

  it('keeps Theo read-only: no guided prompt files a return', () => {
    expect(PERSONA_LAB_THREADS.theo.turns.join(' ')).not.toMatch(
      /file|process|submit.*return/i,
    )
  })
})
