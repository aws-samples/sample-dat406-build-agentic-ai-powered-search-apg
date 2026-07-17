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

  it('uses boutique-specific follow-ups when a turn has no product artifacts', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ response: 'No exact matches', products: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const { sendChatMessage } = await import('./chat')
    const result = await sendChatMessage('linen layers for travel')

    expect(result.suggestions).toEqual([
      'Show lighter layers',
      'Keep the edit under $150',
      'Check current availability',
    ])
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

  it('classifies non-2xx responses using status and response detail', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Chat service not initialized' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toMatchObject({
      name: 'ChatServiceError',
      code: 'service_unavailable',
      status: 503,
      retryable: true,
    })
  })

  it('does not misclassify a bare 401 as a policy denial', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: 'HTTP 401 Unauthorized: invalid bearer token' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toMatchObject({
      code: 'authentication_required',
      retryable: false,
    })
  })

  it('rejects structured error events instead of returning fallback content', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        [
          'data: {"type":"content_delta","delta":"Starting..."}',
          'data: {"type":"error","code":"policy_denied","message":"Request blocked by the active policy.","retryable":false}',
          '',
        ].join('\n\n'),
        { status: 200 },
      ),
    )

    const { sendChatMessageStreaming } = await import('./chat')
    const updates: unknown[] = []

    await expect(
      sendChatMessageStreaming('process this return', [], event => updates.push(event)),
    ).rejects.toMatchObject({
      code: 'policy_denied',
      retryable: false,
    })
    expect(updates).toHaveLength(2)
  })

  it('rejects a stream that closes before a complete event', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('data: {"type":"content_delta","delta":"Partial answer"}\n\n', {
        status: 200,
      }),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toMatchObject({
      code: 'stream_interrupted',
      retryable: true,
    })
  })

  it('normalizes fetch failures as retryable network errors', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toMatchObject({
      code: 'network_error',
      retryable: true,
    })
  })
})
