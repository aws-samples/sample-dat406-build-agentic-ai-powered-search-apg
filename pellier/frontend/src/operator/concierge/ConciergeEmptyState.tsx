/**
 * The opening state. Editorial and generous, not four colourful SaaS cards.
 *
 * The lede only. Contextual suggestions are a sibling component so that they derive
 * from loaded record state rather than from this component's props, and so a client
 * whose context supports nothing renders no suggestion rail at all instead of an
 * encouraging row that dead-ends.
 */

import React from 'react'

interface Props {
  loading: boolean
}

const ConciergeEmptyState: React.FC<Props> = ({ loading }) => {
  if (loading) {
    return (
      <div className="operator-concierge-empty" data-testid="operator-concierge-empty">
        <p className="operator-concierge-empty-lede">Loading client conversation…</p>
      </div>
    )
  }

  return (
    <div className="operator-concierge-empty" data-testid="operator-concierge-empty">
      <p className="operator-concierge-empty-lede">
        Investigate an order, understand a service issue, compare products, or prepare
        a response using verified client context.
      </p>
    </div>
  )
}

export default ConciergeEmptyState
