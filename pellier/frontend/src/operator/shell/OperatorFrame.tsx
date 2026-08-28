/**
 * Pellier Operator shell.
 *
 * A slim top bar and an outlet. Deliberately NOT a left admin rail: the desk
 * has two destinations, the book and one client record, and a nav rail for two
 * destinations is furniture.
 *
 * Mounted on `.operator-root`, which is intentionally not nested inside
 * `.pellier-page-surface` or `.observatory-root`. Both of those force headings
 * to sans, one of them with `!important`, so an editorial serif heading is
 * only reachable from a scope outside them. All tokens live on `:root`, so
 * nothing is lost by sitting outside.
 */

import React, { useEffect, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import PellierHomeLink from '../../components/PellierHomeLink'
import { fetchReviewQueue } from '../../services/operator'
import '../styles/operator.css'

/**
 * The count of prepared requests waiting on a person.
 *
 * Always shows a real value once the queue has been read, including zero: an
 * unlabelled "Reviews" reads as an empty placeholder rather than as "nothing is
 * waiting", which is a fact an operator wants stated. A failed read shows an em
 * dash instead of a number, because "0" there would claim there is no work when
 * the truth is that nobody could ask.
 */
const PendingReviewLink: React.FC = () => {
  const [pending, setPending] = useState<number | null>(null)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    let active = true
    fetchReviewQueue()
      .then((queue) => {
        if (!active) return
        setPending(queue.pendingCount)
        setUnreachable(false)
      })
      .catch(() => {
        if (!active) return
        setPending(null)
        setUnreachable(true)
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <Link
      to="/operator/reviews"
      className="operator-topbar-link"
      data-testid="operator-reviews-link"
    >
      Reviews
      {unreachable ? (
        <span
          className="operator-topbar-count"
          data-count="unavailable"
          data-testid="operator-reviews-count"
          title="The review queue could not be read"
        >
          &mdash;
        </span>
      ) : pending === null ? null : (
        <span
          className="operator-topbar-count"
          data-count={pending > 0 ? 'waiting' : 'clear'}
          data-testid="operator-reviews-count"
          title={
            pending > 0
              ? `${pending} prepared request${pending === 1 ? '' : 's'} waiting on a person`
              : 'No prepared request is waiting'
          }
        >
          {pending}
        </span>
      )}
    </Link>
  )
}

const OperatorFrame: React.FC = () => (
  <div className="operator-root" data-testid="operator-root">
    <header className="operator-topbar" data-testid="operator-topbar">
      <div className="operator-topbar-start">
        <Link to="/operator" className="operator-wordmark">
          Pellier Operator
        </Link>
        <span className="operator-topbar-context">
          Clienteling and service recovery
        </span>
      </div>
      <div className="operator-topbar-end">
        <PendingReviewLink />
        <PellierHomeLink testId="operator-exit" />
      </div>
    </header>
    <main className="operator-shell">
      <Outlet />
    </main>
  </div>
)

export default OperatorFrame
