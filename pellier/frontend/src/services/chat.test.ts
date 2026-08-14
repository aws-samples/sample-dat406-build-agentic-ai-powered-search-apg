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
    expect(JSON.parse(init.body as string)).toMatchObject({
      response_mode: 'balanced',
    })
    expect(updates).toHaveLength(1)
    expect(result.response).toBe('done')
  })

  it('sends the selected live agent configuration', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        'data: {"type":"complete","response":{"response":"done","products":[]}}\n\n',
        { status: 200 },
      ),
    )

    const { sendChatMessageStreaming } = await import('./chat')
    await sendChatMessageStreaming(
      'find a gift',
      [],
      vi.fn(),
      undefined,
      true,
      'CUST-ANNA',
      'graph',
      'fast',
    )

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body as string)).toMatchObject({
      guardrails_enabled: true,
      customer_id: 'CUST-ANNA',
      pattern: 'graph',
      response_mode: 'fast',
    })
  })

  it('rejects an SSE error instead of returning fallback success text', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        [
          'data: {"type":"content_delta","delta":"Starting..."}',
          'data: {"type":"error","error":"Agent execution timed out"}',
          '',
        ].join('\n\n'),
        { status: 200 },
      ),
    )

    const { sendChatMessageStreaming } = await import('./chat')
    const updates: unknown[] = []

    await expect(
      sendChatMessageStreaming('hello', [], event => updates.push(event)),
    ).rejects.toThrow('Agent execution timed out')
    expect(updates).toHaveLength(2)
  })

  it('rejects a stream that closes before a complete event', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('data: {"type":"content_delta","delta":"Partial"}\n\n', {
        status: 200,
      }),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toThrow('ended before the agent completed')
  })
})
