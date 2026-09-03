/**
 * The book — every client, richest standing first.
 *
 * Reads the operator-gated `GET /api/operator/clients`. Membership counts
 * come from the API rather than being recomputed here, so the summary cannot
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
import OperatorSignInAction from '../components/OperatorSignInAction'

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
  // Typed name filter. Fifteen clients fit on one screen; forty do not, and an
  // associate who knows the name should not have to scan the ladder for it.
  const [query, setQuery] = useState('')
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
    const authenticationRequired =
      error === 'authentication_required' || error === 'invalid_credentials'
    const operatorRequired = error === 'operator_group_required'
    const unavailable = error === 'operator_unavailable'
    return (
      <div className="operator-state" data-testid="operator-book-error">
        <span className="operator-state-title">
          {authenticationRequired
            ? 'Operator sign-in required'
            : operatorRequired
              ? 'Operator access required'
              : unavailable
                ? 'Operator is temporarily unavailable'
                : 'The book is unavailable'}
        </span>
        {authenticationRequired ? (
          <>
            Sign in with the workshop operator account to read the client book.
            No database request was attempted.
          </>
        ) : operatorRequired ? (
          <>
            This signed-in account is not a member of the operator group. No
            database request was attempted.
          </>
        ) : unavailable ? (
          <>
            The governed service could not be reached, so no current client
            book was returned.
          </>
        ) : (
          <>
            The live database did not return the client list. If this is a fresh
            deployment, confirm migration <code>018_client_book.sql</code> has
            been applied.
          </>
        )}
        {authenticationRequired ? <OperatorSignInAction /> : null}
        <div className="operator-receipt-key" style={{ marginTop: 10 }}>
          {error}
        </div>
      </div>
    )
  }

  if (!book) {
    return (
      <div className="operator-state" data-testid="operator-book-loading">
        Reading the live client book…
      </div>
    )
  }

  const needle = query.trim().toLowerCase()
  const visible = book.clients.filter(
    (c) =>
      (!rungFilter || c.membership === rungFilter) &&
      (!needle ||
        c.name.toLowerCase().includes(needle) ||
        c.slug.toLowerCase().includes(needle) ||
        (c.note ?? '').toLowerCase().includes(needle)),
  )
  const jessicaCase = book.clients.find(
    (client) =>
      client.slug === 'jessica' &&
      /return|dispute|service/i.test(client.note),
  )

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
        Operator Concierge runs a separate investigation and resolution graph
        over the same Aurora customer record the storefront reads. Open a client
        to review standing, orders, and support history. The Concierge can then
        prepare one exact resolution for Action Queue; a person confirms it
        before policy and Aurora independently decide what may execute.
      </p>

      {jessicaCase ? (
        <section
          className="operator-case-entry"
          data-testid="operator-jessica-case-entry"
          aria-labelledby="operator-jessica-case-title"
        >
          <ClientAvatar
            customerId={jessicaCase.customerId}
            name={jessicaCase.name}
            personaId={jessicaCase.personaId}
          />
          <div className="operator-case-entry-copy">
            <span className="operator-case-entry-kicker">Service recovery case</span>
            <h2 id="operator-jessica-case-title">{jessicaCase.name}</h2>
            <p>{jessicaCase.note}</p>
          </div>
          <button
            type="button"
            className="operator-case-entry-action"
            onClick={() =>
              navigate(
                `/operator/clients/${jessicaCase.customerId}` +
                  '?guided=service-recovery#operator-concierge-title',
              )
            }
          >
            Open Jessica&apos;s case
          </button>
        </section>
      ) : null}

      <label className="operator-search" htmlFor="operator-book-search">
        <span>Find a client</span>
        <input
          id="operator-book-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Name or note"
          autoComplete="off"
          data-testid="operator-book-search"
        />
      </label>

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

      {rungFilter || needle ? (
        <p className="operator-filter-note" data-testid="operator-filter-note">
          <span>
            Showing {visible.length} of {book.total}
            {rungFilter ? ` · ${MEMBERSHIP[rungFilter].label}` : ''}
            {needle ? ` · matching "${query.trim()}"` : ''}
          </span>
          <button
            type="button"
            className="operator-filter-clear"
            onClick={() => {
              setRungFilter(null)
              setQuery('')
            }}
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
