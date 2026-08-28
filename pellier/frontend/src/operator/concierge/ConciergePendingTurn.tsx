/**
 * The in-flight turn: the request, plus steps as the backend finishes them.
 *
 * Every row here arrived from the server having actually happened. The one
 * exception is the synthesis row, which reports `running` while the request is
 * genuinely with Bedrock — a real state, not a simulated tick. Nothing is ever shown
 * complete before it is.
 */

import React from 'react'

import type { ConciergeInvestigationStep } from '../../services/operatorConcierge'

interface Props {
  request: string
  steps: ConciergeInvestigationStep[]
}

const ConciergePendingTurn: React.FC<Props> = ({ request, steps }) => (
  <li className="operator-concierge-turn" data-testid="operator-concierge-pending">
    <div className="operator-concierge-request">
      <span className="operator-concierge-eyebrow">Operator request</span>
      <p className="operator-concierge-request-body">{request}</p>
    </div>
    <section className="operator-concierge-investigation">
      <span className="operator-concierge-eyebrow">Investigation</span>
      <ol className="operator-concierge-steps">
        {steps.map((step) => (
          <li
            className="operator-concierge-step"
            key={step.kind}
            data-step-status={step.status}
          >
            <span className="operator-concierge-step-label">{step.label}</span>
            <span className="operator-concierge-step-source">
              {step.status === 'running' ? 'in progress' : step.source}
            </span>
          </li>
        ))}
      </ol>
    </section>
  </li>
)

export default ConciergePendingTurn
