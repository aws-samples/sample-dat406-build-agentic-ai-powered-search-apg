/**
 * Prepared actions waiting on a person.
 *
 * The desk's entry point for work that arrived from the storefront. An operator
 * must be able to find Theo without already knowing to look for him, so this
 * surface leads the book rather than hiding behind a client search.
 *
 * Each card reads as continuity from Pellier, not as a support ticket that
 * appeared from nowhere: the origin line names where it began and when. Raw
 * session and turn identifiers are deliberately absent from the default view —
 * they belong behind the proof link on the action itself.
 */

import React, { useEffect, useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  fetchReviewQueue,
  OperatorApiError,
  type OperatorReview,
  type OperatorReviewQueue,
} from '../../services/operator'
import ClientAvatar from '../components/ClientAvatar'

/** Proposed actions in the operator's language, not the tool's. */
const ACTION_LABELS: Record<string, string> = {
  initiate_return: 'Return',
  issue_credit: 'Goodwill credit',
}

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action
}

/**
 * "2 hours ago" from an ISO timestamp, or null when absent.
 *
 * Relative rather than absolute: an operator triaging a queue cares how long
 * someone has been waiting, not the wall-clock time it landed.
 */
export function relativeTime(iso: string | null, now: Date = new Date()): string | null {
  if (!iso) return null
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return null
  const seconds = Math.round((now.getTime() - then.getTime()) / 1000)
  if (seconds < 0) return 'just now'
  if (seconds < 90) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} minutes ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return hours === 1 ? 'an hour ago' : `${hours} hours ago`
  const days = Math.round(hours / 24)
  return days === 1 ? 'yesterday' : `${days} days ago`
}

/**
 * What became of a review, in one line.
 *
 * Every row said "<action> proposed, awaiting a person" regardless of state, so the
 * three reviews under "Already decided" — one written return, one Cedar denial, one
 * row-level-security refusal — all claimed to be waiting. The right-hand state chip
 * carries the HUMAN axis only, which is why it read "Confirmed" beside that sentence
 * and nothing contradicted it.
 *
 * The axes come from the API, which resolves them from the stored execution receipt.
 * Nothing is inferred here.
 */
export function outcomeLine(review: OperatorReview): string {
  const action = actionLabel(review.action)
  if (review.humanState === 'confirmation_required') {
    return `${action} proposed, awaiting a person`
  }
  if (review.humanState === 'declined') {
    return `${action} declined. Nothing was submitted.`
  }
  // Confirmed. What happened next depends on whether it was carried out at all.
  if (!review.execution) {
    return `${action} approved, not yet carried out`
  }
  const { policy, aurora } = review.assurance
  if (policy === 'DENY') return `${action} refused by AgentCore Policy`
  if (policy === 'WOULD_DENY') {
    return `${action} would have been refused; enforcement was off`
  }
  if (aurora === 'DENIED') return `${action} permitted, then refused by Aurora`
  if (aurora === 'PERMITTED') return `${action} carried out`
  return `${action} attempted; the outcome was not recorded`
}

const ReviewCard: React.FC<{ review: OperatorReview }> = ({ review }) => {
  const when = relativeTime(review.requestedAt)
  const humanState =
    review.humanState === 'confirmation_required'
      ? 'Confirmation required'
      : review.humanState === 'confirmed'
        ? 'Confirmed'
        : 'Declined'

  return (
    <Link
      to={`/operator/reviews/${review.reviewId}`}
      className="operator-review-row"
      data-testid={`operator-review-${review.reviewId}`}
      data-human-state={review.humanState}
    >
      <ClientAvatar
        customerId={review.customerId}
        name={review.customerName}
        personaId={review.personaId}
      />
      <span className="operator-review-body">
        <span className="operator-review-origin">
          Prepared from Pellier{when ? ` · ${when}` : ''}
        </span>
        <span className="operator-client-name">{review.customerName}</span>
        <span className="operator-cell-note">
          {review.issue || 'Action details awaiting inspection'}
        </span>
      </span>
      <span className="operator-review-action-cell">
        <span className="operator-review-cell-label">Prepared action</span>
        <span className="operator-review-cell-value">
          {actionLabel(review.action)}
        </span>
        <span
          className="operator-cell-note"
          data-testid="operator-review-outcome"
        >
          {outcomeLine(review)}
        </span>
      </span>
      <span className="operator-review-state" data-state={review.humanState}>
        <span className="operator-review-cell-label">Human decision</span>
        <span>{humanState}</span>
      </span>
      <ArrowUpRight className="operator-review-open" aria-hidden />
    </Link>
  )
}

const ReviewQueue: React.FC = () => {
  const [queue, setQueue] = useState<OperatorReviewQueue | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    fetchReviewQueue()
      .then((data) => {
        if (active) setQueue(data)
      })
      .catch((err: unknown) => {
        if (!active) return
        setError(
          err instanceof OperatorApiError ? err.code : 'operator_unavailable',
        )
      })
    return () => {
      active = false
    }
  }, [])

  if (error) {
    const authenticationRequired =
      error === 'authentication_required' || error === 'invalid_credentials'
    const operatorRequired = error === 'operator_group_required'
    return (
      <div className="operator-state" data-testid="operator-reviews-error">
        <span className="operator-state-title">
          {authenticationRequired
            ? 'Operator sign-in required'
            : operatorRequired
              ? 'Operator access required'
              : 'The action queue is unavailable'}
        </span>
        {authenticationRequired ? (
          <>
            Sign in with the workshop operator account to read the action queue.
            No database request was attempted.
          </>
        ) : operatorRequired ? (
          <>
            This signed-in account is not a member of the operator group. No
            database request was attempted.
          </>
        ) : (
          <>
            The live database did not return prepared actions. If this is a
            fresh deployment, confirm migration{' '}
            <code>020_operator_review.sql</code> has been applied.
          </>
        )}
        <div className="operator-receipt-key" style={{ marginTop: 10 }}>
          {error}
        </div>
      </div>
    )
  }

  if (!queue) {
    return (
      <div className="operator-state" data-testid="operator-reviews-loading">
        Reading the action queue from Aurora…
      </div>
    )
  }

  const pending = queue.reviews.filter(
    (r) => r.humanState === 'confirmation_required',
  )
  const decided = queue.reviews.filter(
    (r) => r.humanState !== 'confirmation_required',
  )

  return (
    <div data-testid="operator-reviews">
      <h1 className="operator-title">Actions awaiting decision</h1>
      <p className="operator-lede">
        Pellier stops consequential work here. Decide the exact terms;
        authorization and execution remain separate.
      </p>

      <dl className="operator-queue-summary" aria-label="Action queue summary">
        <div>
          <dt>Needs decision</dt>
          <dd data-tone={pending.length > 0 ? 'authority' : 'quiet'}>
            {pending.length}
          </dd>
        </div>
        <div>
          <dt>Decided</dt>
          <dd>{decided.length}</dd>
        </div>
        <div>
          <dt>Current boundary</dt>
          <dd className="operator-queue-boundary">Human confirmation</dd>
        </div>
      </dl>

      {pending.length === 0 ? (
        <div className="operator-state" data-testid="operator-reviews-empty">
          {/* A clean environment starts here: nothing seeds this table, so an empty
              queue is the designed first impression rather than a failure to load.
              Copy states the mechanism instead of instructing the reader, and stays
              clear of the "all caught up" register - there is nothing to be caught up
              on, and a celebration over an empty queue reads as filler. */}
          <span className="operator-state-title">No actions waiting</span>
          Consequential actions that Pellier prepares but may not take on its own
          appear here for an operator to confirm. A shopper asking to return a
          damaged piece is the usual source.
        </div>
      ) : (
        <div className="operator-action-list" data-testid="operator-review-pending">
          {pending.map((review) => (
            <ReviewCard review={review} key={review.reviewId} />
          ))}
        </div>
      )}

      {decided.length > 0 ? (
        <>
          <div className="operator-section" data-testid="operator-review-decided-head">
            <span className="operator-section-descriptor">Decision history</span>
            <span className="operator-section-count">{decided.length}</span>
          </div>
          <div className="operator-action-list" data-testid="operator-review-decided">
            {decided.map((review) => (
              <ReviewCard review={review} key={review.reviewId} />
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}

export default ReviewQueue
