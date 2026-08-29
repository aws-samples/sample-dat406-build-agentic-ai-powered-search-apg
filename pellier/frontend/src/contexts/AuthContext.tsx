/**
 * AuthContext — Cognito OAuth2 login + AgentCore Identity-backed preferences.
 *
 * Uses the backend authorization-code flow. Cognito tokens remain in secure,
 * httpOnly cookies set by `/api/auth/callback`; browser code never handles
 * tokens from a URL fragment or localStorage. This context is the source of
 * truth for:
 *
 *   - `user`               — Cognito claims (sub, email, givenName)
 *   - `preferences`        — saved preferences from AgentCore Memory
 *   - `refresh()`          — re-reads /api/auth/me + /api/user/preferences
 *   - `savePreferences(p)` — POSTs /api/user/preferences and bumps prefsVersion
 *   - `isLoading`          — alias for `loading` per the design signature
 *   - `prefsVersion`       — monotonic counter ProductGrid uses as `key=`
 *
 * The fields (`login`, `logout`, `accessToken`, `isAuthenticated`, `loading`)
 * remain compatible with existing call sites
 * (`LoginButton`, `SignInPage`, `AuthGate`, etc.). New code SHOULD import
 * from `utils/auth.ts` which re-exports `useAuth`.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import type { Preferences } from '../services/types'

interface AuthUser {
  sub: string
  email: string
  givenName?: string
}

interface AuthContextType {
  user: AuthUser | null
  isAuthenticated: boolean
  accessToken: string | null
  login: () => void
  logout: () => void
  loading: boolean
  /** Alias for `loading` — matches the design-document signature. */
  isLoading: boolean
  /**
   * Saved preferences from AgentCore Memory, fetched via
   * `/api/user/preferences`. `null` means either unauthenticated or no
   * preferences saved yet. AuthStateBand (Task 4.4) uses the null branch
   * to trigger the preferences onboarding modal.
   */
  preferences: Preferences | null
  /**
   * Monotonic counter that advances each time preferences are saved.
   * `ProductGrid` (Task 4.6) uses this as `key={prefsVersion}` so the
   * grid remounts and re-fires the parallax reveal on every save
   * (Req 1.6.6). Starts at 0.
   */
  prefsVersion: number
  /**
   * Re-read /api/auth/me and /api/user/preferences. Called by the app
   * shell after a sign-in callback and on first mount.
   */
  refresh: () => Promise<void>
  /**
   * POST /api/user/preferences. On success, updates local state and
   * advances `prefsVersion` so the product grid remounts and re-parallaxes.
   */
  savePreferences: (p: Preferences) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

const AUTH_SESSION_MARKER_KEY = 'pellier-auth-session'
const JUST_SIGNED_IN_COOKIE = 'just_signed_in'

function hasCookie(name: string): boolean {
  if (typeof document === 'undefined') return false
  return document.cookie
    .split(';')
    .some(cookie => cookie.trim().startsWith(`${name}=`))
}

// Shape returned by GET /api/auth/me (see Req 3.1.3). The server returns
// camelCase fields matching the `User` wire type in services/types.ts.
interface MeResponse {
  userId?: string
  user_id?: string
  email: string
  givenName?: string
  given_name?: string
}

// Shape returned by GET /api/user/preferences (see Req 3.2.1). The server
// returns `{ preferences: Preferences | null }`; we only care about the
// inner object.
interface PreferencesResponse {
  preferences: Preferences | null
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const accessToken: string | null = null
  const [loading, setLoading] = useState(true)
  const [preferences, setPreferences] = useState<Preferences | null>(null)
  const [prefsVersion, setPrefsVersion] = useState(0)

  /**
   * `refresh()` — hydrate `user` from /api/auth/me and `preferences` from
   * /api/user/preferences. Both calls send the httpOnly cookies via
   * `credentials: 'include'`. A 401 on `/api/auth/me` means the user is
   * unauthenticated and we clear any stale state.
   */
  const refresh = useCallback(async () => {
    try {
      const meRes = await fetch('/api/auth/me', {
        method: 'GET',
        credentials: 'include',
      })
      if (!meRes.ok) {
        setUser(null)
        setPreferences(null)
        if (typeof window !== 'undefined') {
          localStorage.removeItem(AUTH_SESSION_MARKER_KEY)
        }
        return
      }
      const me = (await meRes.json()) as MeResponse
      if (typeof window !== 'undefined') {
        localStorage.setItem(AUTH_SESSION_MARKER_KEY, '1')
      }
      setUser({
        sub: me.userId ?? me.user_id ?? '',
        email: me.email,
        givenName: me.givenName ?? me.given_name,
      })

      // Fetch preferences only once we know we have a verified user.
      const prefsRes = await fetch('/api/user/preferences', {
        method: 'GET',
        credentials: 'include',
      })
      if (prefsRes.ok) {
        const body = (await prefsRes.json()) as PreferencesResponse
        setPreferences(body.preferences ?? null)
      } else {
        setPreferences(null)
      }
    } catch {
      // Network failure — surface as "unauthenticated" rather than leaving
      // stale state. The caller can retry via its own error path.
      setUser(null)
      setPreferences(null)
      if (typeof window !== 'undefined') {
        localStorage.removeItem(AUTH_SESSION_MARKER_KEY)
      }
    }
  }, [])

  /**
   * `savePreferences(p)` — POST /api/user/preferences. On 2xx, bumps
   * `prefsVersion` so the ProductGrid remounts (Req 1.6.6). On non-2xx,
   * throws so the PreferencesModal (Task 5.3) can surface the error.
   */
  const savePreferences = useCallback(async (p: Preferences) => {
    const res = await fetch('/api/user/preferences', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(p),
    })
    if (!res.ok) {
      throw new Error(`savePreferences failed: HTTP ${res.status}`)
    }
    // Server echoes the saved object (Req 3.2.2). Prefer the echo over the
    // input so any server-side normalization is respected.
    let saved: Preferences = p
    try {
      const body = await res.json()
      if (body && typeof body === 'object') {
        // Accept either `{ preferences: Preferences }` or a bare Preferences.
        saved = (body.preferences ?? body) as Preferences
      }
    } catch {
      // Empty body is fine — keep the input.
    }
    setPreferences(saved)
    setPrefsVersion(v => v + 1)
  }, [])

  // On mount, hydrate only when the callback marker or an existing authenticated
  // session says cookie-backed state may exist. This avoids a noisy 401 on every
  // clean anonymous page load.
  useEffect(() => {
    let cancelled = false

    const hydrate = async () => {
      const shouldRefresh =
        hasCookie(JUST_SIGNED_IN_COOKIE) ||
        (typeof window !== 'undefined' &&
          localStorage.getItem(AUTH_SESSION_MARKER_KEY) === '1')

      if (shouldRefresh) {
        await refresh()
      }

      if (!cancelled) setLoading(false)
    }

    void hydrate()
    return () => {
      cancelled = true
    }
    // Intentional: refresh is stable (useCallback with empty deps).
  }, [])

  const login = useCallback(() => {
    const returnTo = `${window.location.pathname}${window.location.search}`
    window.location.assign(
      `/api/auth/signin?provider=email&returnTo=${encodeURIComponent(returnTo)}`,
    )
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_SESSION_MARKER_KEY)
    setUser(null)
    setPreferences(null)
    void fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    }).finally(() => window.location.reload())
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        accessToken,
        login,
        logout,
        loading,
        isLoading: loading,
        preferences,
        prefsVersion,
        refresh,
        savePreferences,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
