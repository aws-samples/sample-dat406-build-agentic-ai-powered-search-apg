/**
 * StorefrontThreadGuide — a compact, persona-specific three-turn path in
 * Ask Pellier. It advances only when the real conversation still matches the
 * shared canonical thread, so freeform shopping stays entirely freeform.
 */
import { ArrowRight, RotateCcw } from 'lucide-react'
import type { AgentChatMessage } from '../hooks/useAgentChat'
import {
  labThreadForPersona,
  type PersonaLabThread,
} from '../data/personaCurations'

type StorefrontThreadStatus = 'idle' | 'next' | 'complete' | 'waiting' | 'hidden'

export interface StorefrontThreadProgress {
  status: StorefrontThreadStatus
  nextIndex: number | null
}

export interface StorefrontThreadGuideProps {
  personaId: string | null | undefined
  messages: readonly AgentChatMessage[]
  isLoading: boolean
  onSend: (text: string) => void
  onRestart: () => void
}

function normalized(text: string): string {
  return text.trim().replace(/\s+/g, ' ').toLocaleLowerCase()
}

/**
 * Derive progression from actual shopper messages. There is deliberately no
 * separate "guided conversation" state to drift away from the chat history.
 */
export function storefrontThreadProgress(
  messages: readonly Pick<AgentChatMessage, 'role' | 'content'>[],
  thread: PersonaLabThread,
  isLoading: boolean,
): StorefrontThreadProgress {
  const shopperTurns = messages.filter((message) => message.role === 'user')

  if (shopperTurns.length === 0) {
    return { status: 'idle', nextIndex: 0 }
  }

  const followsThread = shopperTurns.every(
    (message, index) =>
      index < thread.turns.length &&
      normalized(message.content) === normalized(thread.turns[index]),
  )

  if (!followsThread) {
    return { status: 'hidden', nextIndex: null }
  }

  if (isLoading) {
    return { status: 'waiting', nextIndex: null }
  }

  if (shopperTurns.length === thread.turns.length) {
    return { status: 'complete', nextIndex: null }
  }

  return { status: 'next', nextIndex: shopperTurns.length }
}

export default function StorefrontThreadGuide({
  personaId,
  messages,
  isLoading,
  onSend,
  onRestart,
}: StorefrontThreadGuideProps) {
  if (!personaId || personaId === 'fresh') return null

  const thread = labThreadForPersona(personaId)
  const progress = storefrontThreadProgress(messages, thread, isLoading)

  if (progress.status === 'hidden' || progress.status === 'waiting') {
    return null
  }

  if (progress.status === 'complete') {
    return (
      <section
        className="cd-thread-guide cd-thread-guide-complete"
        data-testid="storefront-thread-guide"
        aria-label="Conversation trail complete"
      >
        <div className="cd-thread-guide-head">
          <span>Conversation trail</span>
          <span>03 / 03</span>
        </div>
        <p>That thread is complete.</p>
        <button
          type="button"
          className="cd-thread-guide-restart"
          onClick={onRestart}
        >
          <RotateCcw size={13} aria-hidden="true" />
          <span>Start again</span>
        </button>
      </section>
    )
  }

  const nextIndex = progress.nextIndex ?? 0
  const nextTurn = thread.turns[nextIndex]
  const heading =
    nextIndex === 0 ? 'Follow the conversation' : 'Continue the conversation'

  return (
    <section
      className="cd-thread-guide"
      data-testid="storefront-thread-guide"
      aria-label={`${heading}, step ${nextIndex + 1} of ${thread.turns.length}`}
    >
      <div className="cd-thread-guide-head">
        <span>{heading}</span>
        <span>
          {String(nextIndex + 1).padStart(2, '0')} /{' '}
          {String(thread.turns.length).padStart(2, '0')}
        </span>
      </div>
      <button
        type="button"
        className="cd-thread-guide-action"
        onClick={() => onSend(nextTurn)}
      >
        <span>{nextTurn}</span>
        <ArrowRight size={15} aria-hidden="true" />
      </button>
    </section>
  )
}
