import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  createConciergeSession: vi.fn(),
  fetchCapabilities: vi.fn(),
  fetchConciergeConfig: vi.fn(),
  fetchConciergeSession: vi.fn(),
  fetchLatestConciergeSession: vi.fn(),
  streamConciergeTurn: vi.fn(),
}))

vi.mock('../../services/operator', () => mocks)

import { useOperatorConcierge } from './useOperatorConcierge'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('useOperatorConcierge client isolation', () => {
  it('does not allow submission before the current client load settles', async () => {
    const latest = deferred<string | null>()
    mocks.fetchCapabilities.mockResolvedValue({
      governedActionsAvailable: false,
    })
    mocks.fetchConciergeConfig.mockResolvedValue({ composerEnabled: true })
    mocks.fetchLatestConciergeSession.mockReturnValue(latest.promise)

    const { result } = renderHook(() => useOperatorConcierge('CUST-JESSICA'))

    await act(async () => {
      await result.current.submit('Investigate this case')
    })

    expect(result.current.composerEnabled).toBe(false)
    expect(mocks.createConciergeSession).not.toHaveBeenCalled()

    await act(async () => {
      latest.resolve(null)
      await latest.promise
    })
    await waitFor(() => expect(result.current.composerEnabled).toBe(true))
  })

  it('ignores an earlier client load that resolves after the client changes', async () => {
    const oldLatest = deferred<string | null>()
    mocks.fetchCapabilities.mockResolvedValue({
      governedActionsAvailable: false,
    })
    mocks.fetchConciergeConfig.mockResolvedValue({ composerEnabled: true })
    mocks.fetchLatestConciergeSession.mockImplementation((clientId: string) =>
      clientId === 'CUST-OLD'
        ? oldLatest.promise
        : Promise.resolve('session-new'),
    )
    mocks.fetchConciergeSession.mockImplementation(
      (clientId: string, sessionId: string) =>
        Promise.resolve({
          sessionId,
          customerId: clientId,
          messages: [
            {
              messageId: clientId === 'CUST-OLD' ? 1 : 2,
              role: 'assistant',
              content: clientId === 'CUST-OLD' ? 'Old client' : 'New client',
              turnId: clientId === 'CUST-OLD' ? 'turn-old' : 'turn-new',
              turnState: 'complete',
              actorType: 'assistant',
              artifact: null,
              artifactVersion: 2,
              createdAt: null,
            },
          ],
        }),
    )

    const { result, rerender } = renderHook(
      ({ clientId }) => useOperatorConcierge(clientId),
      { initialProps: { clientId: 'CUST-OLD' } },
    )

    rerender({ clientId: 'CUST-NEW' })

    await waitFor(() => {
      expect(result.current.messages[0]?.content).toBe('New client')
    })

    await act(async () => {
      oldLatest.resolve('session-old')
      await oldLatest.promise
      await Promise.resolve()
    })

    expect(result.current.sessionId).toBe('session-new')
    expect(result.current.messages[0]?.content).toBe('New client')
  })
})
