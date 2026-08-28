/**
 * The book — every client, richest standing first.
 *
 * Reads `GET /api/operator/clients`, which is open. Membership counts come
 * from the API rather than being recomputed here, so the summary cannot
 * disagree with the rows.
 */

import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MEMBERSHIP,
  MEMBERSHIP_RUNGS,
  type Membership,
} from '../../data/membership'
import {
  fetchClientBook,
  OperatorApiError,
  type OperatorBook,
} from '../../services/operator'
import ClientAvatar from '../components/ClientAvatar'
import MembershipRung from '../components/MembershipRung'

function money(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  })
}

const ClientBook: React.FC = () => {
  const navigate = useNavigate()
  const [book, setBook] = useState<OperatorBook | null>(null)
  // Client-side: the whole book is already loaded, so filtering needs no
  // round trip. Null means "no filter", not "registered".
  const [rungFilter, setRungFilter] = useState<Membership | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    fetchClientBook()
      .then((data) => {
        if (active) setBook(data)
      })
      .catch((err: unknown) => {
        if (!active) return
        setError(
          err instanceof OperatorApiError
            ? err.code
            : 'operator_unavailable',
        )
      })
    return () => {
      active = false
    }
  }, [])

  if (error) {
    return (
      <div className="operator-state" data-testid="operator-book-error">
        <span className="operator-state-title">The book is unavailable</span>
        Aurora did not return the client list. If this is a fresh deployment,
        confirm migration <code>018_client_book.sql</code> has been applied.
        <div className="operator-receipt-key" style={{ marginTop: 10 }}>
          {error}
        </div>
      </div>
    )
  }

  if (!book) {
    return (
      <div className="operator-state" data-testid="operator-book-loading">
        Reading the client book from Aurora…
      </div>
    )
  }

  const visible = rungFilter
    ? book.clients.filter((c) => c.membership === rungFilter)
    : book.clients

  // Richest rung first, and a rung with nobody in it is not a section.
  const sections = [...MEMBERSHIP_RUNGS]
    .reverse()
    .map((rung) => ({
      rung,
      clients: visible.filter((c) => c.membership === rung),
    }))
    .filter((section) => section.clients.length > 0)

  if (book.total === 0) {
    return (
      <div className="operator-state" data-testid="operator-book-empty">
        <span className="operator-state-title">No clients seeded</span>
        The desk is wired but <code>pellier.customers</code> holds no client
        rows. Apply <code>018_client_book.sql</code> to seed the book.
      </div>
    )
  }

  return (
    <div data-testid="operator-book">
      {/* An introduction to the surface rather than a label for it: an advisor
          arriving here needs to know what they can do, not what the list is
          called. No kicker above the heading. */}
      <h1 className="operator-title">Every client the house knows</h1>
      <p className="operator-lede">
        This is the advisor&rsquo;s side of the same agent that serves the
        storefront. Open a client to read their standing, order history, and
        support record, then act on it — a goodwill credit or a return
        resolution, each one confirmed by a person and written to Aurora. Every
        figure below is read from the database on load, so this desk and the
        storefront can never disagree about the same client.
      </p>

      {/* The ladder, defined where the choice is made. */}
      <div className="operator-ladder" data-testid="operator-book-summary">
        {MEMBERSHIP_RUNGS.map((rung: Membership) => {
          const active = rungFilter === rung
          const count = book.byMembership[rung] ?? 0
          return (
            <button
              type="button"
              className="operator-ladder-cell"
              key={rung}
              aria-pressed={active}
              data-rung={rung}
              data-testid={`operator-ladder-${rung}`}
              // A count beside a label already implies a filter. Clicking
              // again clears it rather than trapping the operator in a subset.
              onClick={() => setRungFilter(active ? null : rung)}
              title={
                active
                  ? `Showing ${MEMBERSHIP[rung].label} only. Click to show all.`
                  : `Show only ${MEMBERSHIP[rung].label} clients`
              }
            >
              <span className="operator-ladder-head">
                <MembershipRung membership={rung} />
                {/* The label is the brand; the descriptor is the
                    comprehension. An advisor new to the ladder still knows
                    what "private client" means. */}
                <span className="operator-ladder-descriptor">
                  {MEMBERSHIP[rung].descriptor}
                </span>
                <span className="operator-ladder-count">{count}</span>
              </span>
              <span className="operator-ladder-threshold">
                {MEMBERSHIP[rung].threshold}
              </span>
              <span className="operator-ladder-earns">
                {MEMBERSHIP[rung].earns}
              </span>
            </button>
          )
        })}
      </div>

      {rungFilter ? (
        <p className="operator-filter-note" data-testid="operator-filter-note">
          <span>
            Showing {visible.length} of {book.total} ·{' '}
            {MEMBERSHIP[rungFilter].label}
          </span>
          <button
            type="button"
            className="operator-filter-clear"
            onClick={() => setRungFilter(null)}
            data-testid="operator-filter-clear"
          >
            Show all clients
          </button>
        </p>
      ) : null}

      <div className="operator-book">
        {/* Unfiltered, the list is grouped and the mark appears once per
            section. Filtered, the caption above already names the rung, so
            neither headers nor per-row pills are repeated. */}
        {sections.map(({ rung, clients }) => (
          <React.Fragment key={rung}>
            {rungFilter ? null : (
              <div className="operator-section" data-rung={rung}>
                <MembershipRung membership={rung} />
                {/* Identity and benefit are separated by space, not a
                    middle dot: joined by a dot they read as one long
                    sentence. */}
                <span className="operator-section-descriptor">
                  {MEMBERSHIP[rung].descriptor}
                </span>
                <span className="operator-section-earns">
                  {MEMBERSHIP[rung].earns}
                </span>
                <span className="operator-section-count">
                  {clients.length}
                </span>
              </div>
            )}
            {clients.map((client) => (
          <button
            key={client.customerId}
            type="button"
            className="operator-book-row"
            data-testid={`operator-client-${client.slug}`}
            onClick={() => navigate(`/operator/clients/${client.customerId}`)}
          >
            <ClientAvatar
              customerId={client.customerId}
              name={client.name}
              personaId={client.personaId}
            />
            <span>
              <span className="operator-client-name">{client.name}</span>
              <span className="operator-client-note">{client.note}</span>
            </span>
            <span className="operator-figure">
              <span className="operator-figure-label">12-month spend</span>
              {money(client.spend12mo)}
            </span>
            <span className="operator-figure">
              <span className="operator-figure-label">Orders</span>
              {client.orderCount}
            </span>
          </button>
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}

export default ClientBook
