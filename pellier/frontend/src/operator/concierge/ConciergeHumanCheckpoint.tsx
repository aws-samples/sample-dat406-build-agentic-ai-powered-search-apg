import React, { useMemo, useState } from 'react'
import { ArrowRight, CheckCircle2, ShieldCheck, UserCheck } from 'lucide-react'

import type {
  OperatorClientRecord,
  OperatorOrder,
} from '../../services/operator'

const RETURN_REASONS = [
  ['damaged', 'Damaged'],
  ['wrong_size', 'Wrong size'],
  ['not_as_described', 'Not as described'],
  ['changed_mind', 'Changed mind'],
  ['other', 'Other'],
] as const

function materialReason(reason: string): string {
  const labels: Record<string, string> = {
    damaged: 'damaged',
    wrong_size: 'the wrong size',
    not_as_described: 'not as described',
    changed_mind: 'no longer wanted',
    other: 'another stated reason',
  }
  return labels[reason] ?? reason.replace(/_/g, ' ')
}

function candidates(record: OperatorClientRecord): OperatorOrder[] {
  const ticketText = record.tickets
    .filter((ticket) => ticket.status === 'open' || ticket.status === 'pending')
    .map((ticket) => `${ticket.subject} ${ticket.lastNote}`)
    .join(' ')
    .toLowerCase()
  const stop = new Set(['pellier', 'luxury', 'bath', 'sage'])
  const mentioned = record.orders.filter((order) =>
    order.productName
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .some(
        (token) =>
          token.length >= 4 &&
          !stop.has(token) &&
          ticketText.includes(token),
      ),
  )
  return (mentioned.length ? mentioned : record.orders.slice(0, 2)).slice(0, 3)
}

interface Props {
  record: OperatorClientRecord
  disabled: boolean
  onPrepare: (request: string) => void
}

const ConciergeHumanCheckpoint: React.FC<Props> = ({
  record,
  disabled,
  onPrepare,
}) => {
  const items = useMemo(() => candidates(record), [record])
  const [productId, setProductId] = useState(items[0]?.productId ?? '')
  const [reason, setReason] = useState('not_as_described')
  const item = items.find((candidate) => candidate.productId === productId)

  if (!record.client.returnEvidence?.unconfirmedReturnAssertion || !items.length) {
    return null
  }

  return (
    <section
      className="operator-concierge-human-checkpoint"
      data-testid="operator-concierge-human-checkpoint"
      aria-labelledby="operator-concierge-checkpoint-title"
    >
      <div className="operator-concierge-human-checkpoint-head">
        <h3 id="operator-concierge-checkpoint-title">
          Decide what should enter review
        </h3>
        <p>
          This prepares a review. It does not authorize or execute the return.
        </p>
      </div>

      <ol className="operator-concierge-boundary">
        <li data-state="current">
          <UserCheck size={16} aria-hidden="true" />
          <span><strong>You choose</strong> the exact item and reason</span>
        </li>
        <li>
          <CheckCircle2 size={16} aria-hidden="true" />
          <span><strong>Human confirms</strong> in Action Queue</span>
        </li>
        <li>
          <ShieldCheck size={16} aria-hidden="true" />
          <span><strong>Policy and Aurora</strong> decide execution later</span>
        </li>
      </ol>

      <fieldset className="operator-concierge-human-checkpoint-items">
        <legend>Choose the disputed piece</legend>
        {items.map((candidate) => (
          <label key={`${candidate.orderId}-${candidate.productId}`}>
            <input
              type="radio"
              name="service-recovery-item"
              value={candidate.productId}
              checked={candidate.productId === productId}
              onChange={(event) => setProductId(event.target.value)}
            />
            <span>
              <strong>{candidate.productName}</strong>
              <small>
                Order #{candidate.orderId} · ${candidate.price.toFixed(2)}
              </small>
            </span>
          </label>
        ))}
      </fieldset>

      <label className="operator-concierge-human-checkpoint-reason">
        <span>Return reason</span>
        <select
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          disabled={disabled}
        >
          {RETURN_REASONS.map(([value, label]) => (
            <option value={value} key={value}>{label}</option>
          ))}
        </select>
      </label>

      <button
        type="button"
        className="operator-concierge-human-checkpoint-action"
        disabled={disabled || !item}
        onClick={() => {
          if (!item) return
          onPrepare(
            `Prepare the return for "${item.productName}" on order ` +
              `#${item.orderId} for review because it was ` +
              `${materialReason(reason)}.`,
          )
        }}
      >
        Prepare for human review
        <ArrowRight size={15} aria-hidden="true" />
      </button>
    </section>
  )
}

export default ConciergeHumanCheckpoint
