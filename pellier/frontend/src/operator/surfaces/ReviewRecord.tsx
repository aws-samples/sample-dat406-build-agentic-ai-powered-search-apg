/**
 * One prepared request, and the decision it needs.
 *
 * Reading order is the operator's reasoning order: who the client is, what they
 * reported, what they actually bought, what Pellier proposes and why, the exact
 * action with its parameters, then the decision — and only then the four
 * assurance axes.
 *
 * Everything factual on this page is hydrated by the API from the table that
 * owns it. The review row supplies references and workflow state; membership,
 * spend, the order, live stock, and the client's return history are read at
 * request time. That is why there are no literals for Theo's rung or his spend
 * anywhere in this file.
 *
 * Confirming records that a person agreed to these parameters. It does not carry
 * the action out, and this page must never imply otherwise: the assurance axes
 * come from the API and are printed as given.
 */

import { CheckCircle2, CircleX, LoaderCircle } from 'lucide-react'
import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { MEMBERSHIP } from '../../data/membership'
import {
  confirmReview,
  declineReview,
  executeReview,
  fetchReview,
  OperatorApiError,
  type OperatorExecutionResult,
  type OperatorReviewDetail,
} from '../../services/operator'
import ActionAssurance from '../components/ActionAssurance'
import ClientAvatar from '../components/ClientAvatar'
import MembershipRung from '../components/MembershipRung'
import ShopperHandoffView from '../components/ShopperHandoffView'
import { useOperatorQueueRefresh } from '../shell/OperatorFrame'

function money(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  })
}

function centsToMoney(cents: number): string {
  return money(cents / 100)
}

/** Parameter names as an operator reads them, not as the tool declares them. */
const PARAMETER_LABELS: Record<string, string> = {
  customer_id: 'Client',
  product_id: 'Product',
  reason: 'Reason',
  amount_cents: 'Amount',
}

const ACTION_TITLES: Record<string, string> = {
  initiate_return: 'File a return',
  issue_credit: 'Issue a goodwill credit',
}

/**
 * The headline, with the review's own reason in it.
 *
 * The map used to read "File a damaged return" for every `initiate_return`, which
 * was true only while `damaged` was the sole scenario. A Concierge-prepared
 * not-as-described return rendered a headline naming a reason the review does not
 * carry — the narrative disagreeing with the parameters directly beneath it.
 */
function actionTitle(action: string, parameters: Record<string, unknown>): string {
  const base = ACTION_TITLES[action] ?? action
  const reason = parameters.reason
  if (action === 'initiate_return' && typeof reason === 'string' && reason) {
    return `File a ${reason.replace(/_/g, ' ')} return`
  }
  return base
}

function formatParameter(key: string, value: unknown): string {
  if (key === 'amount_cents' && typeof value === 'number') {
    return centsToMoney(value)
  }
  if (key === 'reason' && typeof value === 'string') {
    return value.replace(/_/g, ' ')
  }
  return String(value)
}

/** The issue sentence: "<piece> <problem>", without repeating the piece. */
export function issueLine(productName: string | undefined, issue: string): string {
  const problem = (issue || '').trim()
  const piece = (productName || '').trim()
  if (!piece) return problem
  if (!problem) return piece
  // The issue already names the piece, either because it IS the name or because the
  // operator wrote a full sentence about it.
  if (problem.toLowerCase().includes(piece.toLowerCase())) return problem
  return `${piece} ${problem}`
}

const ReviewRecord: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>()
  const { user } = useAuth()
  const refreshQueue = useOperatorQueueRefresh()
  const [detail, setDetail] = useState<OperatorReviewDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deciding, setDeciding] = useState(false)
  const [decisionError, setDecisionError] = useState<string | null>(null)
  // THIS session's execution response. The durable record lives on the server in
  // `review.execution`, so a reload no longer loses the verdicts: this state only
  // makes the answer immediate for the operator who just pressed the button.
  const [execution, setExecution] = useState<OperatorExecutionResult | null>(null)
  const [executing, setExecuting] = useState(false)

  const numericId = Number(reviewId)

  const load = useCallback(() => {
    if (!Number.isFinite(numericId)) {
      setError('review_not_found')
      return
    }
    fetchReview(numericId)
      .then(setDetail)
      .catch((err: unknown) => {
        setError(
          err instanceof OperatorApiError ? err.code : 'operator_unavailable',
        )
      })
  }, [numericId])

  useEffect(load, [load])

  const execute = async () => {
    if (!detail) return
    setExecuting(true)
    setDecisionError(null)
    try {
      // The fingerprint is stale-view protection only. Every action parameter
      // comes from the persisted review, server-side.
      const outcome = await executeReview(
        detail.review.reviewId,
        detail.review.actionHash,
      )
      setExecution(outcome)
      // Re-read both projections from their owners. The detail fetch hydrates
      // the durable receipt; the shell fetch owns the queue count.
      refreshQueue()
      const fresh = await fetchReview(detail.review.reviewId)
      setDetail(fresh)
    } catch (err: unknown) {
      setDecisionError(
        err instanceof OperatorApiError ? err.code : 'operator_unavailable',
      )
    } finally {
      setExecuting(false)
    }
  }

  const decide = async (kind: 'confirm' | 'decline') => {
    if (!detail) return
    setDeciding(true)
    setDecisionError(null)
    try {
      if (kind === 'confirm') {
        // The fingerprint of the parameters shown above is echoed back. If any
        // material value moved since this page loaded, the server refuses rather
        // than applying the confirmation to different terms.
        await confirmReview(detail.review.reviewId, detail.review.actionHash)
      } else {
        await declineReview(detail.review.reviewId)
      }
      // The decision endpoint has committed at this point. Invalidate the
      // queue even if the following detail read is temporarily unavailable.
      refreshQueue()
      // Re-read rather than patching local state: the decision's authoritative
      // shape, including the assurance axes, comes from the server.
      const fresh = await fetchReview(detail.review.reviewId)
      setDetail(fresh)
    } catch (err: unknown) {
      setDecisionError(
        err instanceof OperatorApiError ? err.code : 'operator_unavailable',
      )
    } finally {
      setDeciding(false)
    }
  }

  if (error) {
    const authenticationRequired =
      error === 'authentication_required' || error === 'invalid_credentials'
    const operatorRequired = error === 'operator_group_required'
    return (
      <div className="operator-state" data-testid="operator-review-error">
        <span className="operator-state-title">
          {authenticationRequired
            ? 'Operator sign-in required'
            : operatorRequired
              ? 'Operator access required'
              : error === 'review_not_found'
                ? 'No such action'
                : 'This prepared action is unavailable'}
        </span>
        {authenticationRequired ? (
          <span>
            Sign in with the workshop operator account to read this prepared
            action. No database request was attempted.
          </span>
        ) : operatorRequired ? (
          <span>
            This signed-in account is not a member of the operator group. No
            database request was attempted.
          </span>
        ) : null}
        <Link to="/operator/reviews" className="operator-filter-clear">
          Back to Action Queue
        </Link>
        <div className="operator-receipt-key" style={{ marginTop: 10 }}>
          {error}
        </div>
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="operator-state" data-testid="operator-review-loading">
        Reading action details from Aurora…
      </div>
    )
  }

  const {
    review,
    shopperHandoff,
    client,
    order,
    product,
    fulfilment,
    returns,
  } = detail
  const rung = MEMBERSHIP[client.membership]
  const pending = review.humanState === 'confirmation_required'
  // The return this review produced is not part of the client's prior history. It is
  // identified by the write key the execution receipt carries, not by being the newest
  // — a timestamp comparison would misattribute a return filed seconds earlier by
  // someone else.
  const producedReturnId = review.execution?.producedReturnId ?? null
  const priorDamaged = returns.filter(
    (r) => r.reason === 'damaged' && r.returnId !== producedReturnId,
  )
  // This session's response first, then the stored receipt. Both describe the same
  // attempt; only the first is available the instant the button returns. Reading the
  // stored one is what stops the page offering "Execute this action" again after a
  // reload, and what keeps the rail sentence on screen.
  const attempted = execution ?? review.execution
  // One resolved set of axes for the whole page. This session's response if there is
  // one, otherwise the server's, which it resolves from the stored receipt.
  const axes = execution ? execution.assurance : review.assurance
  const phase = deciding
    ? ('recording_decision' as const)
    : executing
      ? ('executing' as const)
      : undefined
  const completed = Boolean(attempted) && axes.evidence === 'RECEIPTED'
  const blocked = Boolean(attempted) && !completed
  const actionState = deciding
    ? 'recording'
    : executing
      ? 'executing'
      : completed
        ? 'completed'
        : blocked
          ? 'blocked'
          : review.humanState
  const actionStateLabel = deciding
    ? 'Recording decision'
    : executing
      ? 'Evaluating'
      : completed
        ? 'Completed'
        : blocked
          ? 'Not applied'
          : pending
            ? 'Decision required'
            : review.humanState === 'confirmed'
              ? 'Ready to execute'
              : 'Declined'
  const decisionActor =
    review.decidedBy && user?.sub === review.decidedBy
      ? 'you'
      : 'an authorized operator'
  const decisionTime = review.decidedAt
    ? new Date(review.decidedAt).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : null

  return (
    <div
      className="operator-review-record-layout"
      data-testid="operator-review-record"
    >
      <nav className="operator-back">
        <Link to="/operator/reviews">Action Queue</Link>
        <span aria-hidden="true">/</span>
        <span>{client.name}</span>
      </nav>

      {/* Origin, stated once and early. The issue is joined rather than interpolated
          because it is genuinely optional — a review prepared from an operator request
          may carry none — and a template left "Rachel Green ·" trailing a separator
          with nothing after it. */}
      <p className="operator-review-origin" data-testid="operator-review-origin">
        {['Prepared from Pellier', client.name, review.issue]
          .filter(Boolean)
          .join(' · ')}
      </p>

      {/* CUSTOMER */}
      <header className="operator-review-head" data-testid="operator-review-client">
        <ClientAvatar
          customerId={client.customerId}
          name={client.name}
          personaId={client.personaId}
        />
        <div>
          <h1 className="operator-title">{client.name}</h1>
          <p className="operator-review-standing">
            <MembershipRung membership={client.membership} />
            <span className="operator-ladder-descriptor">{rung.descriptor}</span>
            <span className="operator-figure-label">
              {money(client.spend12mo)} in 12 months
            </span>
          </p>
          <Link
            to={`/operator/clients/${client.customerId}`}
            className="operator-filter-clear"
            data-testid="operator-review-client-link"
          >
            Open the full client record
          </Link>
        </div>
        <div
          className="operator-review-head-state"
          data-state={actionState}
        >
          <span className="operator-review-cell-label">Action state</span>
          <span>{actionStateLabel}</span>
        </div>
      </header>

      {shopperHandoff ? (
        <div className="operator-card operator-review-handoff-card">
          <ShopperHandoffView handoff={shopperHandoff} clientName={client.name} />
        </div>
      ) : null}

      {/* ISSUE */}
      <section
        className="operator-card operator-review-context-card"
        data-testid="operator-review-issue"
      >
        <h2 className="operator-card-title">Issue</h2>
        <p className="operator-review-issue-text">
          {/* The issue describes the PROBLEM ("arrived damaged"), and the product name
              is prefixed to make a sentence of it. But `prepare_proposal` defaults the
              issue to the item name when the operator stated no problem, which rendered
              "Ivory Cashmere Throw Ivory Cashmere Throw". Prefix only when the issue is
              actually saying something else. */}
          {issueLine(product?.name, review.issue)}
        </p>
        {priorDamaged.length > 0 ? (
          <p className="operator-cell-note" data-testid="operator-review-prior">
            {/* The status belongs to the most recent one, so say which. Appending it
                bare to a count read as though every return shared that status. */}
            This client has {priorDamaged.length} previous damaged{' '}
            {priorDamaged.length === 1 ? 'return' : 'returns'} on record
            {priorDamaged[0]
              ? `, most recently ${priorDamaged[0].status}`
              : ''}
            . Worth weighing before a second courtesy remedy.
          </p>
        ) : null}
      </section>

      {/* ORDER */}
      <section
        className="operator-card operator-review-order-card"
        data-testid="operator-review-order"
      >
        <h2 className="operator-card-title">Order</h2>
        {order ? (
          <div className="operator-table-wrap"><table className="operator-table">
            <thead>
              <tr>
                <th scope="col">Order</th>
                <th scope="col">Piece</th>
                <th scope="col">Placed</th>
                <th scope="col">Paid</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="operator-table-id">{order.orderId}</td>
                <td>
                  {order.productName}
                  {/* A div, not a span: `operator-cell-note` carries no display
                      rule, so inline rendering ran the brand straight onto the
                      piece name — "Coral Lacquer CatchallPellier Maison". The
                      client record already stacks them this way. */}
                  <div className="operator-cell-note">{order.brand}</div>
                </td>
                <td>
                  {order.placedAt
                    ? new Date(order.placedAt).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })
                    : '—'}
                </td>
                <td>{money(order.price * order.quantity)}</td>
              </tr>
            </tbody>
          </table></div>
        ) : (
          <p className="operator-cell-note">
            No order row resolved for this review.
          </p>
        )}
        {/* pellier.orders carries no status column, so the honest lifecycle
            signal is the return record rather than an invented status. */}
        {returns.length > 0 ? (
          <p className="operator-cell-note" data-testid="operator-review-returns">
            Return history: {returns.length} on file, most recent{' '}
            {returns[0].reason.replace(/_/g, ' ')} ({returns[0].status}).
          </p>
        ) : (
          <p className="operator-cell-note">No returns on file for this client.</p>
        )}
      </section>

      {/* AGENT RECOMMENDATION */}
      <section
        className="operator-card operator-review-recommendation-card"
        data-testid="operator-review-recommendation"
      >
        <h2 className="operator-card-title">Pellier recommends</h2>
        <p className="operator-review-issue-text">
          {actionTitle(review.action, review.parameters)}
        </p>
        {review.recommendation.rationale ? (
          <p className="operator-cell-note">{review.recommendation.rationale}</p>
        ) : null}
        {/* Replacement availability is a live fact, resolved on this read. */}
        <p className="operator-cell-note" data-testid="operator-review-fulfilment">
          {fulfilment.availabilityVerified === false
            ? 'Replacement availability is not verified for this piece.'
            : fulfilment.replacementAvailable
              ? `A replacement is available: ${fulfilment.totalUnits} units across ${fulfilment.warehouses.length} warehouses.`
              : 'No replacement stock is available right now.'}
        </p>
        {review.recommendation.secondarySuggestion ? (
          <p
            className="operator-cell-note"
            data-testid="operator-review-secondary"
          >
            Optional:{' '}
            {review.recommendation.secondarySuggestion.action === 'issue_credit'
              ? `a courtesy credit of ${centsToMoney(
                  review.recommendation.secondarySuggestion.amountCents ?? 0,
                )}`
              : review.recommendation.secondarySuggestion.action}
            . {review.recommendation.secondarySuggestion.rationale ?? ''}
          </p>
        ) : null}
      </section>

      {/* PROPOSED ACTION */}
      <section
        className="operator-card operator-review-action-card"
        data-testid="operator-review-action"
      >
        <h2 className="operator-card-title">Proposed action</h2>
        <p className="operator-table-id operator-review-action-name">
          {review.action}
        </p>
        <div className="operator-table-wrap"><table className="operator-table">
          <thead>
            <tr>
              <th scope="col">Parameter</th>
              <th scope="col">Value</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(review.parameters).map(([key, value]) => (
              <tr key={key} data-testid={`operator-review-param-${key}`}>
                <td>{PARAMETER_LABELS[key] ?? key}</td>
                <td className="operator-table-id">{formatParameter(key, value)}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        <p className="operator-cell-note">
          Confirming binds to exactly these values. If any of them changes, the
          confirmation stops being valid and this returns to needing a person.
        </p>
      </section>

      {/* HUMAN DECISION */}
      <section
        className="operator-card operator-review-decision-card"
        data-testid="operator-review-decision"
      >
        <h2 className="operator-card-title">Your decision</h2>
        {deciding ? (
          <p
            className="operator-review-live-status"
            data-state="active"
            data-testid="operator-review-live-status"
            role="status"
          >
            <LoaderCircle className="operator-review-live-icon" aria-hidden />
            <span>
              <strong>Recording your decision</strong>
              PostgreSQL is persisting the decision before this page changes
              state.
            </span>
          </p>
        ) : executing ? (
          <p
            className="operator-review-live-status"
            data-state="active"
            data-testid="operator-review-live-status"
            role="status"
          >
            <LoaderCircle className="operator-review-live-icon" aria-hidden />
            <span>
              <strong>Evaluating the governed action</strong>
              The persisted action is entering its configured execution rail.
              The returned receipt will show whether AgentCore Policy evaluated
              it and whether Aurora was reached.
            </span>
          </p>
        ) : null}
        {pending ? (
          <>
            <div className="operator-review-actions">
              <button
                type="button"
                className="operator-button operator-button-inline"
                onClick={() => decide('confirm')}
                disabled={deciding}
                data-testid="operator-review-confirm"
              >
                {deciding ? 'Recording…' : 'Confirm this action'}
              </button>
              <button
                type="button"
                className="operator-button operator-button-inline operator-button-quiet"
                onClick={() => decide('decline')}
                disabled={deciding}
                data-testid="operator-review-decline"
              >
                Decline
              </button>
            </div>
            <p className="operator-cell-note">
              Confirming records your approval of these terms. Carrying the
              action out is a separate, authorized step.
            </p>
          </>
        ) : (
          <>
            <p
              className="operator-review-decision-summary"
              data-testid="operator-review-decided"
            >
              {review.humanState === 'confirmed' ? (
                <CheckCircle2
                  className="operator-review-decision-icon"
                  aria-hidden
                />
              ) : (
                <CircleX
                  className="operator-review-decision-icon"
                  aria-hidden
                />
              )}
              <span>
                <strong>
                  {review.humanState === 'confirmed' ? 'Confirmed' : 'Declined'}{' '}
                  by {decisionActor}
                </strong>
                {decisionTime ? <span>{decisionTime}</span> : null}
              </span>
            </p>
            {review.decidedBy || review.decidedAt ? (
              <details className="operator-review-audit-identity">
                <summary>Audit identity</summary>
                <dl>
                  {review.decidedBy ? (
                    <div>
                      <dt>Principal</dt>
                      <dd className="operator-receipt-key">
                        {review.decidedBy}
                      </dd>
                    </div>
                  ) : null}
                  {review.decidedAt ? (
                    <div>
                      <dt>Recorded</dt>
                      <dd className="operator-receipt-key">
                        {review.decidedAt}
                      </dd>
                    </div>
                  ) : null}
                </dl>
              </details>
            ) : null}
            {review.humanState === 'confirmed' && !attempted ? (
              <>
                <div className="operator-review-actions">
                  <button
                    type="button"
                    className="operator-button operator-button-inline"
                    onClick={execute}
                    disabled={executing}
                    data-testid="operator-review-execute"
                  >
                    {executing ? 'Executing…' : 'Execute this action'}
                  </button>
                </div>
                <p className="operator-cell-note">
                  A person has approved these terms. Executing asks whether the
                  system is authorised to carry them out, which is a separate
                  question with its own answer.
                </p>
              </>
            ) : null}
            {attempted ? (
              <p
                className="operator-cell-note"
                data-testid="operator-review-execution"
              >
                {/* A denied action was never executed, so "Executed on the managed
                    Gateway rail" was false on every DENY — and the row-scope clause
                    was irrelevant, because nothing reached the database to be scoped.
                    Submitted is the honest verb for the attempt; executed is reserved
                    for the calls that entered the tool. */}
                {axes.policy === 'DENY' ? (
                  <>
                    <strong>Action blocked.</strong>{' '}
                    Submitted on the{' '}
                    {attempted.rail === 'gateway-mcp'
                      ? 'managed Gateway rail'
                      : 'in-process rail'}
                    {' '}and refused before the tool was entered.
                  </>
                ) : (
                  <>
                    <strong>
                      {axes.evidence === 'RECEIPTED'
                        ? 'Action completed.'
                        : 'Action not applied.'}
                    </strong>{' '}
                    Executed on the{' '}
                    {attempted.rail === 'gateway-mcp'
                      ? 'managed Gateway rail'
                      : 'in-process rail'}
                    {attempted.customerSubject
                      ? ', scoped to the client\u2019s own rows.'
                      : '. This client has no identity mapping, so no row scope was resolved.'}
                  </>
                )}
              </p>
            ) : null}
          </>
        )}
        {decisionError ? (
          <p
            className="operator-receipt-key"
            data-testid="operator-review-decision-error"
          >
            {decisionError === 'parameters_changed'
              ? 'The proposed values changed since this page loaded. Reload and read the new terms before confirming.'
              : decisionError === 'operator_sign_in_required'
                ? 'A verified operator sign-in is required to decide this action.'
                : decisionError}
          </p>
        ) : null}
      </section>

      <ActionAssurance
        assurance={axes}
        phase={phase}
        /* The server's specific sentences — which policy matched, which client had
           no mapping — outrank the static ones, and they must survive a reload. The
           stored receipt carries the same two it returned. */
        notes={execution?.notes ?? review.execution?.notes}
        caption="Four separate questions. None of them answers another."
      />

      {/* What produced the verdicts above. The axes are a claim; this is its basis,
          and "Allow" without the engine and the mode cannot be told apart from an
          unenforced observation under LOG_ONLY. Rendered from the stored receipt, so
          it is here for anyone who opens the page later — not only for the operator
          who pressed the button. */}
      {review.execution ? (
        <section
          className="operator-receipt"
          data-testid="operator-review-receipt"
          data-mode={review.execution.gatewayMode || 'unknown'}
        >
          <h2 className="operator-card-title">What decided this</h2>
          <dl className="operator-receipt-rows">
            <div>
              <dt>Policy engine</dt>
              <dd className="operator-receipt-key">
                {review.execution.policyEngineId || 'None — this rail consults no engine'}
              </dd>
            </div>
            <div>
              <dt>Enforcement</dt>
              <dd>
                {review.execution.gatewayMode === 'ENFORCE'
                  ? 'ENFORCE — a denial would have been enforced'
                  : review.execution.gatewayMode === 'LOG_ONLY'
                    ? 'LOG_ONLY — decisions were observed, not enforced'
                    : 'Not recorded'}
              </dd>
            </div>
            <div>
              <dt>Action evaluated</dt>
              <dd className="operator-receipt-key">
                {review.execution.gatewayActionId}
              </dd>
            </div>
            {review.execution.matchingForbids.length ? (
              <div>
                {/* Named, not blamed. The same conditional forbid is listed beside an
                    ALLOW, where it means the rule was evaluated and did not apply. */}
                <dt>Forbid rules naming this action</dt>
                <dd className="operator-receipt-key">
                  {review.execution.matchingForbids.join(', ')}
                </dd>
              </div>
            ) : null}
            <div>
              <dt>Write key</dt>
              <dd className="operator-receipt-key">
                {review.execution.idempotencyKey}
              </dd>
            </div>
            {review.execution.recordedAt ? (
              <div>
                <dt>Recorded</dt>
                <dd>
                  {new Date(review.execution.recordedAt).toLocaleString('en-US')}
                </dd>
              </div>
            ) : null}
          </dl>
        </section>
      ) : null}

      {/* The evidence link, where the raw identifiers belong. */}
      {review.sourceTurnId ? (
        <p className="operator-cell-note">
          <Link
            to={`/observatory?turn=${encodeURIComponent(review.sourceTurnId)}`}
            data-testid="operator-review-observatory-link"
          >
            Inspect the originating turn in Pellier Observatory
          </Link>{' '}
          <span className="operator-receipt-key">{review.sourceTurnId}</span>
        </p>
      ) : null}
    </div>
  )
}

export default ReviewRecord
