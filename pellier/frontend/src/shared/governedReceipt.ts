/**
 * Base-path-safe deep links from a Boutique turn to its Agent Trace evidence.
 *
 * Two constraints shape this file.
 *
 * **Base path.** Workshop Studio serves the SPA behind a CloudFront
 * `/ports/8000/` proxy, so an origin-root URL breaks. Every link here goes
 * through `routePath()` from `utils/assetPath`, which applies the router
 * basename. Nothing concatenates `location.origin`.
 *
 * **Real routes only.** These functions target destinations that already
 * exist in `App.tsx` — `/agent-trace/proof-board`,
 * `/agent-trace/sessions/:id/telemetry`, `/agent-trace/audit-proof`, and
 * `/inspector`. No route is invented here; a link to a non-existent path
 * would silently fall through to the catch-all redirect and land the
 * attendee on the Boutique home page, which reads as "the evidence is
 * missing" rather than "the link was wrong".
 *
 * The turn identifier travels as a query parameter rather than a path
 * segment: it is optional (older turns predate it), and a query keeps the
 * existing session routes unchanged.
 */
import { routePath } from '../utils/assetPath'

/** Query key carrying the per-turn identifier across surfaces. */
export const TURN_QUERY_KEY = 'turn'

export interface ReceiptTarget {
  /** Session the turn belongs to. Required — it selects the evidence set. */
  sessionId?: string | null
  /** Stable per-turn id when the backend emitted one. */
  turnId?: string | null
  /** Trace id, used by the inspector when present. */
  traceId?: string | null
}

function withQuery(path: string, params: Record<string, string | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

/**
 * In-app route (for React Router `<Link to>`) to a turn's session evidence.
 *
 * Returns a router-relative path WITHOUT the basename, because
 * `<Link to>` applies the basename itself. Double-prefixing is the classic
 * way these links break behind the proxy.
 *
 * @param target Session, turn, and trace identifiers.
 * @returns A route path, or the Agent Trace audit-proof route when no session
 *   is known — the general evidence surface is a truthful fallback, an
 *   invented session id is not.
 */
export function receiptRoute(target: ReceiptTarget): string {
  if (target.turnId) {
    return withQuery('/agent-trace/proof-board', { [TURN_QUERY_KEY]: target.turnId })
  }
  if (!target.sessionId) return '/agent-trace/audit-proof'
  return withQuery(
    `/agent-trace/sessions/${encodeURIComponent(target.sessionId)}/telemetry`,
    { trace: target.traceId },
  )
}

/**
 * Absolute in-app href (for plain `<a href>`), base-path applied.
 *
 * Use only where React Router is unavailable. Prefer `receiptRoute` with
 * `<Link>` so client-side navigation preserves state.
 */
export function receiptHref(target: ReceiptTarget): string {
  return routePath(receiptRoute(target))
}

/**
 * Route to the session-scoped trace inspector.
 *
 * `/inspector` takes `session` as a query parameter in the current router.
 */
export function inspectorRoute(target: ReceiptTarget): string {
  return withQuery('/inspector', {
    session: target.sessionId,
    [TURN_QUERY_KEY]: target.turnId,
  })
}

/** Base-path-applied href for the inspector. */
export function inspectorHref(target: ReceiptTarget): string {
  return routePath(inspectorRoute(target))
}

/** Route back to the Boutique, preserving the base path via `<Link>`. */
export function boutiqueRoute(): string {
  return '/'
}

/**
 * Read the turn id from a location search string.
 *
 * Used by Agent Trace to restore the selected turn after a reload, which is
 * what makes a shared receipt link actually reproducible.
 *
 * @param search A `location.search` value, with or without the leading `?`.
 */
export function turnIdFromSearch(search: string): string | null {
  const params = new URLSearchParams(
    search.startsWith('?') ? search.slice(1) : search,
  )
  const value = params.get(TURN_QUERY_KEY)
  return value && value.trim() ? value : null
}
