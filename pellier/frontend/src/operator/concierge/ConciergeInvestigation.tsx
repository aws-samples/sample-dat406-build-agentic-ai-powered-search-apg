/**
 * Observable system activity. Never a reasoning trace.
 *
 * The distinction is the point: these rows are operations that happened and the
 * system that performed them. No model interiors, no "let me think through this",
 * no hidden prompt state — the backend refuses to persist those keys, and this
 * component has nowhere to render them.
 *
 * A source row appears only when that system actually participated. Listing every
 * service in the architecture would be decoration.
 */

import React, { useState } from 'react'

import type { ConciergeInvestigationStep } from '../../services/operatorConcierge'

interface Props {
  steps: ConciergeInvestigationStep[]
  durationMs?: number | null
}

const ConciergeInvestigation: React.FC<Props> = ({ steps, durationMs }) => {
  const [open, setOpen] = useState(true)
  if (!steps.length) return null

  const measured = durationMs ?? steps.reduce((sum, s) => sum + (s.durationMs ?? 0), 0)

  return (
    <section className="operator-concierge-investigation"
             data-testid="operator-concierge-investigation">
      <button
        type="button"
        className="operator-concierge-investigation-head"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="operator-concierge-eyebrow">Investigation</span>
        <span className="operator-concierge-investigation-meta">
          {steps.length} {steps.length === 1 ? 'step' : 'steps'}
          {/* Only a measured duration. Never an invented one. */}
          {measured > 0 ? ` · ${(measured / 1000).toFixed(1)}s` : ''}
        </span>
      </button>
      {open ? (
        <ol className="operator-concierge-steps">
          {steps.map((step, index) => (
            <li className="operator-concierge-step" key={`${step.kind}-${index}`}
                data-step-status={step.status}>
              <span className="operator-concierge-step-label">{step.label}</span>
              <span className="operator-concierge-step-source">{step.source}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  )
}

export default ConciergeInvestigation
