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
import { ClipboardCheck, LogOut, User, UsersRound } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import PellierHomeLink from '../../components/PellierHomeLink'
import { useAuth } from '../../contexts/AuthContext'
import { fetchReviewQueue, OperatorApiError } from '../../services/operator'
import { redirectToSignIn } from '../../utils/auth'
import '../styles/operator.css'

const OperatorQueueRefreshContext = createContext<() => void>(() => undefined)

/**
 * Tab, history and bookmark titles for each desk route. Every route used to
 * inherit the storefront's title from index.html, so an operator with the
 * storefront, the desk and the Observatory open could not tell the tabs apart.
 */
const ROUTE_TITLES: ReadonlyArray<[prefix: string, title: string]> = [
  ['/operator/clients/', 'Client'],
  ['/operator/reviews/', 'Review'],
  ['/operator/reviews', 'Action Queue'],
]

export function operatorTitleForPath(pathname: string): string {
  const match = ROUTE_TITLES.find(([prefix]) => pathname.startsWith(prefix))
  return `${match ? match[1] : 'Clients'} · Pellier Operator`
}

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
 * Always shows a real state once the queue has been read, including zero. A
 * failed read stays visibly distinct from an empty queue: the status names
 * the problem rather than using a symbol that could be mistaken for a control.
 */
const PendingReviewLink: React.FC<{ refreshRevision: number }> = ({
  refreshRevision,
}) => {
  const [pending, setPending] = useState<number | null>(null)
  const [signInRequired, setSignInRequired] = useState(false)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    let active = true
    fetchReviewQueue()
      .then((queue) => {
        if (!active) return
        setPending(queue.pendingCount)
        setSignInRequired(false)
        setUnreachable(false)
      })
      .catch((error: unknown) => {
        if (!active) return
        setPending(null)
        const needsSignIn =
          error instanceof OperatorApiError && error.needsOperatorSignIn
        setSignInRequired(needsSignIn)
        setUnreachable(!needsSignIn)
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
      {signInRequired ? (
        <span
          className="operator-topbar-count"
          data-count="sign-in"
          data-testid="operator-reviews-count"
          title="Sign in as an operator to read the action queue"
        >
          {/* The slot carries queue state. Spelling out the instruction here
              made it the third "sign in" on a gated screen, beside the topbar
              control and the page's own primary action, so it states the
              state and leaves the asking to them. The title attribute keeps
              the full explanation for anyone who needs it. */}
          Locked
        </span>
      ) : unreachable ? (
        <span
          className="operator-topbar-count"
          data-count="unavailable"
          data-testid="operator-reviews-count"
          title="The action queue could not be read"
        >
          Queue unavailable
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
          {pending} pending
        </span>
      )}
    </NavLink>
  )
}

const OperatorAuthControl: React.FC = () => {
  const { user, isAuthenticated, loading, logout } = useAuth()

  if (loading) {
    return (
      <span
        className="pellier-account-pill operator-auth-control operator-auth-loading"
        aria-label="Checking operator sign-in"
      />
    )
  }

  if (isAuthenticated && user) {
    return (
      <button
        type="button"
        className="pellier-account-pill operator-auth-control"
        onClick={logout}
        title={`Signed in as ${user.email}`}
      >
        <span className="operator-auth-identity">
          {presentIdentity(user.givenName || user.email)}
        </span>
        <LogOut className="operator-topbar-icon" aria-hidden />
        <span>Sign out</span>
      </button>
    )
  }

  return (
    <button
      type="button"
      className="pellier-account-pill operator-auth-signin"
      onClick={() => redirectToSignIn('email')}
      data-testid="operator-sign-in"
    >
      <User className="operator-topbar-icon" aria-hidden />
      <span>Sign in</span>
    </button>
  )
}

/**
 * Present a bare Cognito username with a capital.
 *
 * The workshop's operator signs in as `operator`, and the personas as `marco`,
 * `anna` and `theo`, so `given_name` falls back to the username and the desk
 * rendered it lowercase beside a capitalised "Sign out". Only a single bare
 * word is touched: an address keeps its case, because capitalising the local
 * part of an email is wrong, and anything with a space is a real name whose
 * capitalisation is not ours to guess.
 */
function presentIdentity(value: string): string {
  if (!/^[a-z][a-z0-9._-]*$/.test(value)) return value
  return value.charAt(0).toUpperCase() + value.slice(1)
}

const OperatorFrame: React.FC = () => {
  const { pathname } = useLocation()
  const [queueRefreshRevision, setQueueRefreshRevision] = useState(0)
  useEffect(() => {
    const previous = document.title
    document.title = operatorTitleForPath(pathname)
    return () => {
      document.title = previous
    }
  }, [pathname])
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
