/**
 * One client record: standing, order history, tickets, credits, and the
 * governed actions an operator can take.
 *
 * The action rail is the only place in Pellier where a credit carries an
 * `issued_by`. It requires an operator token; without one the buttons render
 * in a labelled signed-out state rather than failing on click.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { MEMBERSHIP } from '../../data/membership'
import {
  fetchClientRecord,
  issueCredit,
  OperatorApiError,
  resolveReturn,
  type OperatorActionResult,
  type OperatorClientRecord,
} from '../../services/operator'
import { imageSrc } from '../../utils/assetPath'
import ClientAvatar from '../components/ClientAvatar'
import OperatorConcierge from '../concierge/OperatorConcierge'
import MembershipRung from '../components/MembershipRung'

const RETURN_REASONS = [
  'damaged',
  'wrong_size',
  'not_as_described',
  'changed_mind',
  'other',
] as const

function money(value: number): string {
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function shortDate(iso: string | null): string {
  if (!iso) return '—'
  const parsed = new Date(iso)
  return Number.isNaN(parsed.getTime())
    ? '—'
    : parsed.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
}

/** Map a tool envelope onto the three visual outcomes the rail renders.
 *
 * Tolerates a missing or malformed envelope. A receipt that throws takes the
 * whole record down with it, which is strictly worse than reporting that the
 * result could not be read. */
function outcomeOf(result: OperatorActionResult['result'] | undefined): string {
  if (result?.status === 'success') return 'success'
  if (result?.status === 'policy_blocked') return 'blocked'
  return 'error'
}

const ActionReceipt: React.FC<{ action: OperatorActionResult }> = ({
  action,
}) => {
  const result = action.result ?? {
    status: 'error' as const,
    message: 'The write returned no result envelope.',
  }
  const outcome = outcomeOf(result)
  const replayed = result.idempotent_replay === true
  return (
    <div
      className="operator-receipt"
      data-outcome={outcome}
      data-testid="operator-action-receipt"
      role="status"
    >
      <div className="operator-receipt-head">
        {outcome === 'success'
          ? replayed
            ? 'Already applied'
            : 'Applied'
          : outcome === 'blocked'
            ? 'Blocked by policy'
            : 'Not applied'}
      </div>
      {result.message ? <div>{result.message}</div> : null}
      {result.status === 'success' && result.amount ? (
        <div>
          Credit of ${result.amount} recorded
          {result.balance_cents !== undefined
            ? `. Balance now ${money(result.balance_cents / 100)}.`
            : '.'}
        </div>
      ) : null}
      {replayed ? (
        <div>
          The idempotency key had already been used, so the original result was
          returned instead of writing a second time.
        </div>
      ) : null}
      <div className="operator-receipt-key" style={{ marginTop: 6 }}>
        key {action.idempotencyKey}
        {action.actedBy ? ` · by ${action.actedBy}` : ''}
      </div>
    </div>
  )
}

const ClientRecord: React.FC = () => {
  const { customerId = '' } = useParams()
  const [record, setRecord] = useState<OperatorClientRecord | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [amount, setAmount] = useState('40.00')
  const [reason, setReason] = useState('')
  const [returnProductId, setReturnProductId] = useState('')
  const [returnReason, setReturnReason] = useState<string>(RETURN_REASONS[0])
  const [busy, setBusy] = useState(false)
  const [action, setAction] = useState<OperatorActionResult | null>(null)
  const [needsSignIn, setNeedsSignIn] = useState(false)

  const load = useCallback(() => {
    let active = true
    fetchClientRecord(customerId)
      .then((data) => {
        if (active) {
          setRecord(data)
          setError(null)
        }
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
  }, [customerId])

  useEffect(load, [load])

  // Cents, parsed once here. The API takes integer cents so no float ever
  // reaches the ledger.
  const amountCents = useMemo(() => {
    const parsed = Number.parseFloat(amount)
    if (!Number.isFinite(parsed)) return 0
    return Math.round(parsed * 100)
  }, [amount])

  const creditValid =
    amountCents >= 1 && amountCents <= 50_000 && reason.trim().length > 0

  async function run(fn: () => Promise<OperatorActionResult>) {
    setBusy(true)
    setNeedsSignIn(false)
    try {
      const result = await fn()
      setAction(result)
      load()
    } catch (err: unknown) {
      if (err instanceof OperatorApiError && err.needsOperatorSignIn) {
        setNeedsSignIn(true)
      } else {
        setAction({
          result: {
            status: 'error',
            message:
              err instanceof OperatorApiError
                ? err.code
                : 'The write did not complete.',
          },
          idempotencyKey: '—',
          actedBy: null,
        })
      }
    } finally {
      setBusy(false)
    }
  }

  if (error) {
    const authenticationRequired =
      error === 'authentication_required' || error === 'invalid_credentials'
    const operatorRequired = error === 'operator_group_required'
    return (
      <div className="operator-state" data-testid="operator-record-error">
        <Link to="/operator" className="operator-back">
          ← Clients
        </Link>
        <span className="operator-state-title">
          {authenticationRequired
            ? 'Operator sign-in required'
            : operatorRequired
              ? 'Operator access required'
              : 'Record unavailable'}
        </span>
        {authenticationRequired ? (
          <>
            Sign in with the workshop operator account to read this client
            record. No database request was attempted.
          </>
        ) : operatorRequired ? (
          <>
            This signed-in account is not a member of the operator group. No
            database request was attempted.
          </>
        ) : (
          <>
            The live database did not return a record for{' '}
            <code>{customerId}</code>.
          </>
        )}
        <div className="operator-receipt-key" style={{ marginTop: 10 }}>
          {error}
        </div>
      </div>
    )
  }

  if (!record) {
    return (
      <div className="operator-state" data-testid="operator-record-loading">
        Reading the client record from Aurora…
      </div>
    )
  }

  const { client, orders, tickets, credits } = record

  const membershipLabel = `${MEMBERSHIP[client.membership].label} \u00b7 ${
    MEMBERSHIP[client.membership].descriptor
  }`

  return (
    // Two panes, both first class. The record keeps every field and interaction it
    // had; the Concierge is ADDED beside it rather than replacing it, so the left
    // column is not reduced to a SaaS sidebar.
    <div className="operator-workbench" data-testid="operator-record">
      <div className="operator-workbench-record">
      {/* Destination, then the record's own identifier. The customer id is
          the value an operator pastes into a query, so it is shown as data
          rather than hidden. */}
      <nav className="operator-crumb" aria-label="Breadcrumb">
        <Link to="/operator" className="operator-back">
          ← Clients
        </Link>
        <span className="operator-crumb-sep" aria-hidden="true">
          /
        </span>
        <span className="operator-crumb-id">{client.customerId}</span>
      </nav>

      <div className="operator-record-head">
        <ClientAvatar
          customerId={client.customerId}
          name={client.name}
          personaId={client.personaId}
          size="lg"
        />
        <div style={{ minWidth: 0 }}>
          <h1 className="operator-title">{client.name}</h1>
          <p className="operator-lede">{client.note}</p>
          <p className="operator-hint">
            {MEMBERSHIP[client.membership].label} &middot;{' '}
            {MEMBERSHIP[client.membership].descriptor}. Earns{' '}
            {MEMBERSHIP[client.membership].earns.toLowerCase()}.
          </p>
          {/* Said plainly on the surface where an operator is about to act:
              standing shapes what the house offers, and decides nothing about
              whether this action is permitted. */}
          <p className="operator-hint">
            Standing is business context. It may qualify this client for an
            expedited replacement or a larger courtesy allowance, but AgentCore
            Policy still decides whether the action is permitted and Aurora
            still decides whether the data may be changed.
          </p>
        </div>

        {/* Identity on the left, what the house owes them on the right. */}
        <div className="operator-standing">
          <MembershipRung membership={client.membership} describe />
          <div className="operator-standing-row">
            <span>Storefront</span>
            <Link
              to={
                client.personaId
                  ? `/?persona=${encodeURIComponent(client.personaId)}`
                  : `/?clientPreview=${encodeURIComponent(client.customerId)}`
              }
              className="operator-back"
              data-testid="operator-storefront-handoff"
            >
              {client.personaId
                ? `Open ${client.name.split(' ')[0]}'s storefront`
                : 'Preview client context'}
            </Link>
          </div>
        </div>
      </div>

      {/* Four figures an advisor needs before speaking. */}
      <div className="operator-quad" data-testid="operator-quad">
        <div className="operator-quad-cell">
          <div className="operator-quad-label">12-month spend</div>
          <div className="operator-quad-value">{money(client.spend12mo)}</div>
          <div className="operator-quad-note">
            Membership is derived from this figure.
          </div>
        </div>
        <div className="operator-quad-cell">
          <div className="operator-quad-label">Store credit</div>
          <div
            className="operator-quad-value"
            data-tone={client.creditBalanceCents ? 'authority' : 'quiet'}
          >
            {money((client.creditBalanceCents ?? 0) / 100)}
          </div>
          <div className="operator-quad-note">
            {credits.length === 0
              ? 'Nothing on file.'
              : `${credits.length} credit${credits.length === 1 ? '' : 's'} on file.`}
          </div>
        </div>
        <div className="operator-quad-cell">
          <div className="operator-quad-label">Order value</div>
          <div className="operator-quad-value">{money(client.orderValue)}</div>
          <div className="operator-quad-note">
            {orders.length === 0
              ? 'No orders on record.'
              : `Across ${orders.length} order${orders.length === 1 ? '' : 's'}.`}
          </div>
        </div>
        <div className="operator-quad-cell">
          <div className="operator-quad-label">Open tickets</div>
          <div
            className="operator-quad-value"
            data-tone={client.openTicketCount ? 'authority' : 'quiet'}
          >
            {client.openTicketCount ?? 0}
          </div>
          <div className="operator-quad-note">
            {client.openTicketCount
              ? 'Awaiting a decision.'
              : 'Nothing outstanding.'}
          </div>
        </div>
      </div>

      <div className="operator-record">
        <div>
          <section className="operator-card" data-testid="operator-orders">
            <h2 className="operator-card-title">
              Order history <span>{orders.length}</span>
            </h2>
            {orders.length === 0 ? (
              <p className="operator-hint">No orders on record.</p>
            ) : (
              <div className="operator-table-wrap">
                <table className="operator-table">
                <thead>
                  <tr>
                    <th />
                    <th>Piece</th>
                    <th className="operator-col-optional">Placed</th>
                    <th className="operator-table-num">Qty</th>
                    <th className="operator-table-num">Price</th>
                    <th className="operator-table-num">ID</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.orderId}>
                      <td>
                        <OrderThumb
                          src={order.imageUrl}
                          name={order.productName}
                        />
                      </td>
                      <td>
                        {order.productName}
                        <div className="operator-cell-note">{order.brand}</div>
                      </td>
                      <td className="operator-table-date operator-col-optional">
                        {shortDate(order.placedAt)}
                      </td>
                      <td className="operator-table-num">{order.quantity}</td>
                      <td className="operator-table-num">
                        {money(order.price)}
                      </td>
                      <td className="operator-table-id">
                        {order.productId}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}
          </section>

          <section className="operator-card" data-testid="operator-tickets">
            <h2 className="operator-card-title">
              Support history <span>{tickets.length}</span>
            </h2>
            {tickets.length === 0 ? (
              <p className="operator-hint">
                No tickets on record for this client.
              </p>
            ) : (
              <div className="operator-table-wrap">
                <table className="operator-table">
                <thead>
                  <tr>
                    <th className="operator-col-optional">Ticket</th>
                    <th>Subject</th>
                    <th>Status</th>
                    <th className="operator-col-optional">Opened</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                    <tr key={ticket.ticketId}>
                      <td className="operator-table-id operator-col-optional">
                        {ticket.ticketId}
                      </td>
                      <td>
                        {ticket.subject}
                        <div className="operator-cell-note">
                          {ticket.lastNote}
                        </div>
                      </td>
                      <td>
                        <span
                          className="operator-status"
                          data-status={ticket.status}
                        >
                          {ticket.status}
                        </span>
                      </td>
                      <td className="operator-table-date operator-col-optional">
                        {shortDate(ticket.openedAt)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}
          </section>

          <section className="operator-card" data-testid="operator-credits">
            <h2 className="operator-card-title">
              Store credits
              {client.creditBalanceCents ? (
                <span>${client.creditBalance}</span>
              ) : null}
            </h2>
            {credits.length === 0 ? (
              <p className="operator-hint">No credits issued.</p>
            ) : (
              <div className="operator-table-wrap">
                <table className="operator-table">
                <thead>
                  <tr>
                    <th>Reason</th>
                    <th className="operator-col-optional">Issued</th>
                    <th>By</th>
                    <th className="operator-table-num">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {credits.map((credit) => (
                    <tr key={credit.creditId}>
                      <td>{credit.reason}</td>
                      <td className="operator-table-date operator-col-optional">
                        {shortDate(credit.createdAt)}
                      </td>
                      <td className="operator-table-id">
                        {credit.issuedBy ?? 'seed'}
                      </td>
                      <td className="operator-table-num">${credit.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}
          </section>
        </div>

        <aside className="operator-rail" data-testid="operator-actions">
          <section className="operator-card">
            <h2 className="operator-card-title">Issue a goodwill credit</h2>
            <label className="operator-field">
              <span className="operator-field-label">Amount (USD)</span>
              <input
                className="operator-input"
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                data-testid="operator-credit-amount"
              />
            </label>
            <label className="operator-field">
              <span className="operator-field-label">Reason (audited)</span>
              <textarea
                className="operator-textarea"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Why this credit is warranted"
                data-testid="operator-credit-reason"
              />
            </label>
            <button
              type="button"
              className="operator-button"
              disabled={busy || !creditValid}
              data-testid="operator-credit-submit"
              onClick={() =>
                run(() =>
                  issueCredit({
                    customerId: client.customerId,
                    amountCents,
                    reason: reason.trim(),
                  }),
                )
              }
            >
              {busy ? 'Applying…' : 'Issue credit'}
            </button>
            <p className="operator-hint">
              Capped at $500.00 by a database constraint, not by this form. The
              write claims an idempotency key first, so a double-click applies
              once.
            </p>
          </section>

          <section className="operator-card">
            <h2 className="operator-card-title">Resolve a return</h2>
            <label className="operator-field">
              <span className="operator-field-label">Product ID</span>
              <input
                className="operator-input"
                inputMode="numeric"
                value={returnProductId}
                onChange={(event) => setReturnProductId(event.target.value)}
                placeholder="e.g. 41"
                data-testid="operator-return-product"
              />
            </label>
            <label className="operator-field">
              <span className="operator-field-label">Reason</span>
              <select
                className="operator-select"
                value={returnReason}
                onChange={(event) => setReturnReason(event.target.value)}
                data-testid="operator-return-reason"
              >
                {RETURN_REASONS.map((value) => (
                  <option key={value} value={value}>
                    {value.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="operator-button"
              disabled={busy || !/^\d+$/.test(returnProductId)}
              data-testid="operator-return-submit"
              onClick={() =>
                run(() =>
                  resolveReturn({
                    customerId: client.customerId,
                    productId: Number.parseInt(returnProductId, 10),
                    reason: returnReason,
                  }),
                )
              }
            >
              {busy ? 'Applying…' : 'Resolve return'}
            </button>
            <p className="operator-hint">
              Ownership is checked in SQL: a return for a piece this client never
              ordered is refused by the database, not by this form.
            </p>
          </section>

          {needsSignIn ? (
            <div
              className="operator-receipt"
              data-outcome="blocked"
              data-testid="operator-needs-signin"
              role="status"
            >
              <div className="operator-receipt-head">
                Operator sign-in required
              </div>
              This desk and its actions require a verified operator-group
              identity so every read, decision, and mutation is attributable.
            </div>
          ) : null}

          {action ? <ActionReceipt action={action} /> : null}
        </aside>
      </div>
      </div>

      <div className="operator-workbench-concierge">
        <OperatorConcierge
          clientId={client.customerId}
          clientName={client.name}
          membershipLabel={membershipLabel}
          spendLabel={`${money(client.spend12mo)} \u00b7 12mo spend`}
          record={record}
        />
      </div>
    </div>
  )
}

/** Product thumbnail with a designed fallback tile, never a grey box. */
const OrderThumb: React.FC<{ src: string; name: string }> = ({ src, name }) => {
  const [failed, setFailed] = useState(false)
  // Resolved through imageSrc: a bare root-relative path 404s behind the
  // Workshop Studio `/ports/8000/` proxy.
  const resolved = imageSrc(src)
  if (!resolved || failed) {
    return (
      <span className="operator-thumb-fallback" aria-hidden="true">
        {name.slice(0, 1).toUpperCase()}
      </span>
    )
  }
  return (
    <img
      src={resolved}
      alt=""
      aria-hidden="true"
      className="operator-thumb"
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  )
}

export default ClientRecord
