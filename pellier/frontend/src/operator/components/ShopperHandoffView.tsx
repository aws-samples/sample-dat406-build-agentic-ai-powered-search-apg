import React from 'react'
import {
  GitBranch,
  MessageSquareQuote,
  ShieldAlert,
  Wrench,
} from 'lucide-react'

import type { ShopperHandoff } from '../../services/operatorConcierge'

interface Props {
  handoff: ShopperHandoff
  clientName?: string
  compact?: boolean
}

function specialistLabel(value?: string): string {
  if (!value) return 'Specialist not recorded'
  return value
    .replace(/_agent$/i, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

const ShopperHandoffView: React.FC<Props> = ({
  handoff,
  clientName,
  compact = false,
}) => {
  const tools = handoff.routing?.tools ?? []
  const transcript = handoff.transcriptExcerpt ?? []
  const name = clientName?.trim() || 'the shopper'

  return (
    <section
      className="operator-handoff"
      data-compact={compact ? 'true' : undefined}
      data-testid="operator-shopper-handoff"
    >
      <div className="operator-handoff-heading">
        <div>
          <h2>What {name} asked Pellier</h2>
          <p>
            Original storefront context. The operator workflow re-reads current
            business facts before making a recommendation.
          </p>
        </div>
        <span className="operator-handoff-trust">
          <ShieldAlert size={14} strokeWidth={1.8} aria-hidden="true" />
          Reported context
        </span>
      </div>

      <blockquote className="operator-handoff-request">
        <MessageSquareQuote size={18} strokeWidth={1.7} aria-hidden="true" />
        <p>{handoff.shopperRequest}</p>
      </blockquote>

      <dl className="operator-handoff-route">
        <div>
          <dt>
            <GitBranch size={14} strokeWidth={1.8} aria-hidden="true" />
            Storefront route
          </dt>
          <dd>{specialistLabel(handoff.routing?.specialist)}</dd>
        </div>
        <div>
          <dt>
            <Wrench size={14} strokeWidth={1.8} aria-hidden="true" />
            Tools observed
          </dt>
          <dd>{tools.length ? tools.join(', ') : 'None recorded'}</dd>
        </div>
      </dl>

      {transcript.length ? (
        <details className="operator-handoff-transcript">
          <summary>View the bounded storefront excerpt</summary>
          <ol>
            {transcript.map((message, index) => (
              <li key={`${message.role}-${index}`}>
                <span>{message.role === 'user' ? name : 'Pellier'}</span>
                <p>{message.content}</p>
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </section>
  )
}

export default ShopperHandoffView
