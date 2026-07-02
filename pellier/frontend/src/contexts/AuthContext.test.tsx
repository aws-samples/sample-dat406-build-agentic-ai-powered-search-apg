import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'

function wrapper({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>
}

function clearCookie(name: string) {
  document.cookie = `${name}=; Max-Age=0; path=/`
}

function okJson(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockAuthFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString()
    if (url.includes('/api/auth/me')) {
      return okJson({
        userId: 'user-1',
        email: 'avery@example.com',
        givenName: 'Avery',
      })
    }
    if (url.includes('/api/user/preferences')) {
      return okJson({ preferences: null })
    }
    return okJson({})
  })
}

describe('AuthContext hydration', () => {
  beforeEach(() => {
    localStorage.clear()
    clearCookie('just_signed_in')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
    clearCookie('just_signed_in')
  })

  it('does not call /api/auth/me on a clean anonymous page load', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('hydrates the code-flow callback path when just_signed_in is present', async () => {
    const fetchMock = mockAuthFetch()
    vi.stubGlobal('fetch', fetchMock)
    document.cookie = 'just_signed_in=1; path=/'

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user?.email).toBe('avery@example.com')
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/me',
      expect.objectContaining({ credentials: 'include' }),
    )
    expect(localStorage.getItem('pellier-auth-session')).toBe('1')
  })

  it('uses the auth-session marker to hydrate later cookie-backed loads', async () => {
    const fetchMock = mockAuthFetch()
    vi.stubGlobal('fetch', fetchMock)
    localStorage.setItem('pellier-auth-session', '1')

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user?.email).toBe('avery@example.com')
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/me',
      expect.objectContaining({ credentials: 'include' }),
    )
  })
})
