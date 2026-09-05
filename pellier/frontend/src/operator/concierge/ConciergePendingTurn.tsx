/**
 * The in-flight turn: the request, plus steps as the backend finishes them.
 *
 * Every row here arrived from the server having actually happened. The one
 * exception is the synthesis row, which reports `running` while the request is
 * genuinely with Bedrock — a real state, not a simulated tick. Nothing is ever shown
 * complete before it is.
 */

import React, { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, LoaderCircle } from 'lucide-react'

import type {
  ConciergeInvestigationStep,
  ConciergeStreamAnswer,
} from '../../services/operatorConcierge'
import ConciergeStepList from './ConciergeStepList'

interface Props {
  request: string
  steps: ConciergeInvestigationStep[]
  answer: ConciergeStreamAnswer | null
}

const ConciergePendingTurn: React.FC<Props> = ({ request, steps, answer }) => {
  /*
   * Open while the work is happening, closed once it is done.
   *
   * The steps are worth watching live: they name the systems the answer came
   * from as each one responds. They are not worth keeping open afterwards,
   * when the answer is the thing to read and the trace pushes it down a
   * viewport-height column. So it collapses itself on completion and stays one
   * click away, with the step count still on the row.
   *
   * An operator who opened or closed it by hand has said what they want, and
   * that decision outranks the automatic one.
   */
  const [open, setOpen] = useState(true)
  const toggledByHand = useRef(false)
  const settled = answer !== null

  useEffect(() => {
    if (settled && !toggledByHand.current) setOpen(false)
  }, [settled])

  const current = steps.at(-1)
  const activeLabel = answer
    ? 'Answer saved to the conversation'
    : current?.status === 'running'
      ? current.label
      : current
        ? 'Moving to the next verified step'
        : 'Starting the investigation'
  const ActiveIcon = answer ? Check : LoaderCircle

  return (
    <li className="operator-concierge-turn" data-testid="operator-concierge-pending">
      <div className="operator-concierge-request">
        <span className="operator-concierge-eyebrow">You</span>
        <p className="operator-concierge-request-body">{request}</p>
      </div>
      <section
        className="operator-concierge-investigation operator-concierge-investigation--live"
        data-testid="operator-concierge-live-activity"
        aria-live="polite"
      >
        <button
          type="button"
          className="operator-concierge-investigation-head"
          aria-expanded={open}
          onClick={() => {
            toggledByHand.current = true
            setOpen((value) => !value)
          }}
        >
          <span className="operator-concierge-activity-status" aria-hidden="true">
            <ActiveIcon size={15} strokeWidth={1.9} />
          </span>
          <span className="operator-concierge-activity-copy">
            <span className="operator-concierge-eyebrow">
              {answer ? 'Response ready' : 'Working with live client data'}
            </span>
            <span className="operator-concierge-activity-label">{activeLabel}</span>
          </span>
          <span className="operator-concierge-investigation-meta">
            {steps.length} {steps.length === 1 ? 'step' : 'steps'}
            {settled && !open ? ' · show' : ''}
          </span>
          <ChevronDown
            className="operator-concierge-disclosure-icon"
            size={15}
            strokeWidth={1.8}
            aria-hidden="true"
          />
        </button>
        {open ? <ConciergeStepList steps={steps} /> : null}
      </section>
      {answer ? (
        <div
          className="operator-concierge-primary operator-concierge-primary--live"
          data-testid="operator-concierge-live-answer"
        >
          {answer.primaryLabel ? (
            <span className="operator-concierge-eyebrow">{answer.primaryLabel}</span>
          ) : null}
          <p className="operator-concierge-conclusion">{answer.summary}</p>
        </div>
      ) : null}
    </li>
  )
}

export default ConciergePendingTurn
