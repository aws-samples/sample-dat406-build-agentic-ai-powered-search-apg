/**
 * Session replay. No chat bubbles.
 *
 * An operator request is a compact request block with an uppercase eyebrow; an
 * assistant turn will render native structured artifacts. Nothing is wrapped in a
 * coloured rounded balloon, because this is a case file rather than a messaging app.
 */

import React from 'react'

import ConciergeInvestigation from './ConciergeInvestigation'
import ConciergeEvidence from './ConciergeEvidence'
import ConciergeRecommendations from './ConciergeRecommendations'
import ConciergePriorResolutions from './ConciergePriorResolutions'
import ConciergeProposedActions from './ConciergeProposedAction'
import type { ConciergeMessage } from '../../services/operatorConcierge'

const TURN_STATE_COPY: Record<string, { label: string; detail: string }> = {
  incomplete: {
    label: 'Incomplete',
    detail: 'Request saved. Investigation has not started.',
  },
  failed: {
    label: 'Failed',
    detail: 'Investigation could not be completed.',
  },
}

interface Props {
  messages: ConciergeMessage[]
}

const ConciergeConversation: React.FC<Props> = ({ messages }) => {
  // Which turns received an answer. The operator message's own `turnState` is
  // written once as `incomplete` and never updated, because history is append-only
  // and editing what was said would be rewriting the transcript. So completion is
  // DERIVED from the paired assistant message rather than read from a stale field —
  // otherwise a finished turn still reads "Investigation has not started."
  const answered = new Set(
    messages.filter((m) => m.role === 'assistant').map((m) => m.turnId),
  )

  return (
  <ol className="operator-concierge-thread" data-testid="operator-concierge-thread">
    {messages.map((message) => {
      if (message.role === 'user') {
        const state = answered.has(message.turnId)
          ? undefined
          : TURN_STATE_COPY[message.turnState]
        return (
          <li className="operator-concierge-turn" key={message.messageId}>
            <div className="operator-concierge-request"
                 data-testid="operator-concierge-request">
              <span className="operator-concierge-eyebrow">Operator request</span>
              <p className="operator-concierge-request-body">{message.content}</p>
            </div>
            {state ? (
              <div
                className="operator-concierge-turnstate"
                data-turn-state={message.turnState}
                data-testid="operator-concierge-turnstate"
              >
                <span className="operator-concierge-eyebrow">{state.label}</span>
                <p className="operator-concierge-turnstate-copy">{state.detail}</p>
              </div>
            ) : null}
          </li>
        )
      }

      const artifact = message.artifact ?? {}
      return (
        <li className="operator-concierge-turn" key={message.messageId}>
          {message.content ? (
            <div className="operator-concierge-primary"
                 data-workflow={artifact.workflow || 'client_summary'}>
              {/* A draft is labelled; a summary is not. The label is what stops
                  customer-facing copy from reading as something already sent. */}
              {artifact.primaryLabel ? (
                <span className="operator-concierge-eyebrow"
                      data-testid="operator-concierge-primary-label">
                  {artifact.primaryLabel}
                </span>
              ) : null}
              <p className="operator-concierge-conclusion">{message.content}</p>
              {artifact.primaryNote ? (
                <p className="operator-concierge-primary-note">
                  {artifact.primaryNote}
                </p>
              ) : null}
            </div>
          ) : null}
          {/* Products come before the sections: an operator asked for options, so
              the options lead and the comparison prose follows them. */}
          {artifact.replacement ? (
            <ConciergeRecommendations replacement={artifact.replacement} />
          ) : null}
          {artifact.sections?.length
            ? artifact.sections.map((section) => (
                <section
                  className="operator-concierge-section"
                  key={section.id}
                  data-tone={section.tone}
                  data-testid={`operator-concierge-section-${section.id}`}
                >
                  <span className="operator-concierge-eyebrow">{section.label}</span>
                  <p className="operator-concierge-section-body">{section.body}</p>
                </section>
              ))
            : null}
          {/* Before the evidence list and after the prose: the operator asked what
              happened before, so the answer to that question sits with the answer to
              the one they typed, not buried under the raw evidence rows. */}
          {artifact.priorResolutions ? (
            <ConciergePriorResolutions prior={artifact.priorResolutions} />
          ) : null}
          {artifact.investigation?.length ? (
            <ConciergeInvestigation steps={artifact.investigation} />
          ) : null}
          {artifact.evidence?.length ? (
            <ConciergeEvidence items={artifact.evidence} />
          ) : null}
          {/* After the prose and the evidence: an operator reads what was found,
              then what is being asked of them. */}
          {artifact.proposedActions?.length ? (
            <ConciergeProposedActions actions={artifact.proposedActions} />
          ) : null}
          {artifact.recommendation?.body ? (
            <section className="operator-concierge-recommendation"
                     data-testid="operator-concierge-recommendation">
              <span className="operator-concierge-eyebrow">Recommendation</span>
              <p className="operator-concierge-recommendation-body">
                {artifact.recommendation.body}
              </p>
            </section>
          ) : null}
          {artifact.sources?.length ? (
            <section className="operator-concierge-sources"
                     data-testid="operator-concierge-sources">
              <span className="operator-concierge-eyebrow">Evidence sources</span>
              <ul className="operator-concierge-source-list">
                {artifact.sources.map((s) => (
                  <li key={s.source}>
                    <span className="operator-concierge-source-name">{s.source}</span>
                    <span className="operator-concierge-source-detail">{s.detail}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </li>
      )
    })}
  </ol>
  )
}

export default ConciergeConversation
