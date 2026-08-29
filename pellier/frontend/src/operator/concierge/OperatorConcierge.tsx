/**
 * The advisor's workbench beside the client record.
 *
 * Not a chat widget. Operator requests are compact editorial blocks, not bubbles;
 * assistant output will be native structured artifacts, not one assistant balloon.
 * The visual weight sits in typography and whitespace rather than nested cards,
 * which is what keeps a pane full of governance machinery feeling calm.
 *
 * Nothing here fabricates. When orchestration is absent the surface says so; when a
 * governed action is closed it says which and why. A composer that visibly accepts a
 * question it cannot answer is worse than no composer, so it is gated.
 */

import React, { useEffect, useMemo, useRef } from 'react'

import type { OperatorClientRecord } from '../../services/operator'

import ConciergeCapabilityState from './ConciergeCapabilityState'
import ConciergePendingTurn from './ConciergePendingTurn'
import ConciergeSuggestions from './ConciergeSuggestions'
import { buildTemplateContext } from './templates'
import ConciergeComposer from './ConciergeComposer'
import ConciergeConversation from './ConciergeConversation'
import ConciergeEmptyState from './ConciergeEmptyState'
import { useOperatorConcierge } from './useOperatorConcierge'

interface Props {
  clientId: string
  clientName: string
  membershipLabel: string
  spendLabel: string
  /** Loaded record state, so suggestions derive from real context. */
  record: OperatorClientRecord | null
}

const OperatorConcierge: React.FC<Props> = ({
  clientId,
  clientName,
  membershipLabel,
  spendLabel,
  record,
}) => {
  const concierge = useOperatorConcierge(clientId)
  const hasConversation = concierge.messages.length > 0
  const inFlight = concierge.pendingRequest !== null
  // Deterministic, from loaded state. No model decides what to suggest.
  const templateContext = useMemo(() => buildTemplateContext(record), [record])

  // The pane is a viewport-height scroller, so a thread with history opened at its
  // OLDEST turn and the answer an operator just waited for sat below the fold.
  //
  // Align the newest turn's TOP, not the container's end. Scrolling fully to the
  // bottom lands on that turn's evidence table, which is the tail of the answer
  // rather than the answer. Instant rather than smooth: this is a position, not a
  // transition, and animating it on every step event would be motion for its own sake.
  const body = useRef<HTMLDivElement | null>(null)
  const growth = concierge.messages.length + concierge.liveSteps.length
  useEffect(() => {
    const el = body.current
    if (!el) return
    // The newest REQUEST, not the newest turn. A request and its answer are two
    // sibling turns, so aligning the last one shows an answer with the question that
    // produced it scrolled out of view.
    const requests = el.querySelectorAll(
      '.operator-concierge-turn:has(.operator-concierge-request)',
    )
    const newest = requests[requests.length - 1]
    if (!newest) return
    // Measured against the live boxes, so it holds regardless of which ancestor
    // happens to be positioned.
    el.scrollTop +=
      newest.getBoundingClientRect().top - el.getBoundingClientRect().top
  }, [growth, concierge.pendingRequest])

  return (
    <section
      className="operator-concierge"
      aria-labelledby="operator-concierge-title"
      data-testid="operator-concierge"
    >
      <header className="operator-concierge-head">
        <h2 className="operator-concierge-title" id="operator-concierge-title">
          Operator Concierge
        </h2>
        <p className="operator-concierge-sub">
          Grounded in this client&rsquo;s orders, preferences, inventory, returns, and
          governed actions from {concierge.config?.dataSource ?? 'the live database'}.
        </p>
        {/* Scope, not a second profile: enough to make the conversation's subject
            unambiguous without repeating the record on the left. */}
        <p className="operator-concierge-scope" data-testid="operator-concierge-scope">
          <span className="operator-concierge-scope-name">{clientName}</span>
          <span className="operator-concierge-scope-meta">
            {membershipLabel} &middot; {spendLabel}
          </span>
        </p>
      </header>

      <ConciergeCapabilityState
        status={concierge.status}
        capabilities={concierge.capabilities}
        config={concierge.config}
      />

      <div
        className="operator-concierge-body"
        data-testid="operator-concierge-body"
        ref={body}
      >
        {hasConversation || inFlight ? (
          <>
            <ConciergeConversation messages={concierge.messages} />
            {inFlight ? (
              <ol className="operator-concierge-thread">
                <ConciergePendingTurn
                  request={concierge.pendingRequest ?? ''}
                  steps={concierge.liveSteps}
                  answer={concierge.liveAnswer}
                />
              </ol>
            ) : null}
          </>
        ) : (
          <>
            <ConciergeEmptyState loading={concierge.status === 'loading'} />
            {/* Not while loading. A stored thread has not arrived yet, so offering
                actions here would flash four rows and then replace them with the
                conversation they were never relevant to. */}
            {concierge.composerEnabled && concierge.status !== 'loading' ? (
              <ConciergeSuggestions
                context={templateContext}
                supportedWorkflows={concierge.config?.supportedWorkflowKinds}
                disabled={inFlight}
                onSelect={(template) => {
                  if (!templateContext) return
                  // A template is a shortcut into the SAME orchestrator: it builds a
                  // request and submits it. No separate endpoint, no canned answer.
                  void concierge.submit(template.buildRequest(templateContext))
                }}
              />
            ) : null}
          </>
        )}
      </div>

      <ConciergeComposer
        loading={concierge.status === 'loading'}
        enabled={concierge.composerEnabled}
        submitting={concierge.status === 'submitting'}
        note={concierge.config?.note ?? ''}
        error={concierge.error}
        onSubmit={concierge.submit}
      />
    </section>
  )
}

export default OperatorConcierge
