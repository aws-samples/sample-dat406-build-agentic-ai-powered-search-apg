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

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import { ClipboardCheck, LogIn, LogOut, UsersRound } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import PellierHomeLink from '../../components/PellierHomeLink'
import { useAuth } from '../../contexts/AuthContext'
import { fetchReviewQueue } from '../../services/operator'
import '../styles/operator.css'

const OperatorQueueRefreshContext = createContext<() => void>(() => undefined)

/**
 * Invalidates the shell's queue count after a nested route changes a review.
 *
 * The default no-op keeps ReviewRecord independently renderable in focused
 * tests and Storybook-style surfaces that do not mount the operator shell.
 */
export function useOperatorQueueRefresh(): () => void {
  return useContext(OperatorQueueRefreshContext)
}

/**
 * The count of prepared requests waiting on a person.
 *
 * Always shows a real value once the queue has been read, including zero. A
 * failed read shows an em dash instead of a number, because "0" there would
 * claim there is no work when the truth is that nobody could ask.
 */
const PendingReviewLink: React.FC<{ refreshRevision: number }> = ({
  refreshRevision,
}) => {
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
  }, [refreshRevision])

  return (
    <NavLink
      to="/operator/reviews"
      className={({ isActive }) =>
        `operator-topbar-link${isActive ? ' operator-topbar-link-active' : ''}`
      }
      data-testid="operator-reviews-link"
      title="Action Queue"
    >
      <ClipboardCheck className="operator-topbar-icon" aria-hidden />
      <span className="operator-topbar-label">Action Queue</span>
      {unreachable ? (
        <span
          className="operator-topbar-count"
          data-count="unavailable"
          data-testid="operator-reviews-count"
          title="The action queue could not be read"
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
    </NavLink>
  )
}

const OperatorAuthControl: React.FC = () => {
  const { user, isAuthenticated, loading, login, logout } = useAuth()

  if (loading) {
    return (
      <span
        className="operator-auth-control operator-auth-loading"
        aria-label="Checking operator sign-in"
      />
    )
  }

  if (isAuthenticated && user) {
    return (
      <button
        type="button"
        className="operator-auth-control"
        onClick={logout}
        title={`Signed in as ${user.email}`}
      >
        <span className="operator-auth-identity">
          {user.givenName || user.email}
        </span>
        <LogOut className="operator-topbar-icon" aria-hidden />
        <span>Sign out</span>
      </button>
    )
  }

  return (
    <button
      type="button"
      className="operator-auth-control operator-auth-signin"
      onClick={login}
      data-testid="operator-sign-in"
    >
      <LogIn className="operator-topbar-icon" aria-hidden />
      <span>Sign in</span>
    </button>
  )
}

const OperatorFrame: React.FC = () => {
  const [queueRefreshRevision, setQueueRefreshRevision] = useState(0)
  const refreshQueue = useCallback(() => {
    setQueueRefreshRevision((revision) => revision + 1)
  }, [])

  return (
    <OperatorQueueRefreshContext.Provider value={refreshQueue}>
      <div className="operator-root" data-testid="operator-root">
        <header className="operator-topbar" data-testid="operator-topbar">
          <div className="operator-topbar-inner">
            <div className="operator-topbar-start">
              <Link to="/operator" className="operator-wordmark">
                Pellier Operator
              </Link>
              <span className="operator-topbar-context">
                Clienteling and service recovery
              </span>
            </div>
            <div className="operator-topbar-end">
              <nav className="operator-topbar-nav" aria-label="Operator sections">
                <NavLink
                  to="/operator"
                  end
                  className={({ isActive }) =>
                    `operator-topbar-link${isActive ? ' operator-topbar-link-active' : ''}`
                  }
                  title="Clients"
                >
                  <UsersRound className="operator-topbar-icon" aria-hidden />
                  <span className="operator-topbar-label">Clients</span>
                </NavLink>
                <PendingReviewLink refreshRevision={queueRefreshRevision} />
              </nav>
              <OperatorAuthControl />
              <PellierHomeLink testId="operator-exit" />
            </div>
          </div>
        </header>
        <main className="operator-shell">
          <Outlet />
        </main>
      </div>
    </OperatorQueueRefreshContext.Provider>
  )
}

export default OperatorFrame
