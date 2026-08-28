/**
 * Contextual suggestions as thin editorial rows.
 *
 * Each row is offered because the server publishes its workflow AND loaded client
 * state satisfies its requirement, and its description states that reason from real
 * data — "TKT-2026-3015 remains unresolved
 * and its return record is unconfirmed", not a generic invitation. A suggestion
 * whose context cannot be resolved is simply absent rather than a dead end.
 */

import React from 'react'

import { rankTemplates } from './templates'
import type { ConciergeTemplate, TemplateContext } from './templates'

interface Props {
  context: TemplateContext | null
  /** Workflow kinds the server actually implements. Absent means offer nothing. */
  supportedWorkflows: string[] | undefined
  disabled: boolean
  onSelect: (template: ConciergeTemplate) => void
}

const ConciergeSuggestions: React.FC<Props> = ({
  context,
  supportedWorkflows,
  disabled,
  onSelect,
}) => {
  const templates = rankTemplates(context, supportedWorkflows)
  if (!context || templates.length === 0) return null

  return (
    <div
      className="operator-concierge-suggestions"
      data-testid="operator-concierge-suggestions"
    >
      <span className="operator-concierge-eyebrow">Suggested</span>
      <ul className="operator-concierge-suggestion-list">
        {templates.map((template) => (
          <li key={template.id}>
            <button
              type="button"
              className="operator-concierge-suggestion"
              onClick={() => onSelect(template)}
              disabled={disabled}
              data-template={template.id}
              data-testid={`operator-concierge-suggestion-${template.id}`}
            >
              <span className="operator-concierge-suggestion-group">
                {template.group}
              </span>
              <span className="operator-concierge-suggestion-label">
                {template.label}
              </span>
              <span className="operator-concierge-suggestion-why">
                {template.description(context)}
              </span>
              <span className="operator-concierge-suggestion-arrow" aria-hidden="true">
                &rarr;
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ConciergeSuggestions
