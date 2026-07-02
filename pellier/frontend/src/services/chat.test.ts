import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('chat service auth transport', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.resetModules()
    localStorage.clear()
    fetchMock = vi.fn()
    global.fetch = fetchMock as unknown as typeof fetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('includes cookies on non-streaming chat requests', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ response: 'ok', products: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const { sendChatMessage } = await import('./chat')

    await sendChatMessage('hello')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, init] = fetchMock.mock.calls[0]
    expect(init).toMatchObject({
      method: 'POST',
      credentials: 'include',
    })
  })

  it('includes cookies on streaming chat requests', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        'data: {"type":"complete","response":{"response":"done","products":[],"suggestions":[]}}\n\n',
        { status: 200 },
      ),
    )

    const { sendChatMessageStreaming } = await import('./chat')
    const updates: unknown[] = []

    const result = await sendChatMessageStreaming(
      'hello',
      [],
      (event) => updates.push(event),
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, init] = fetchMock.mock.calls[0]
    expect(init).toMatchObject({
      method: 'POST',
      credentials: 'include',
    })
    expect(updates).toHaveLength(1)
    expect(result.response).toBe('done')
  })
})
