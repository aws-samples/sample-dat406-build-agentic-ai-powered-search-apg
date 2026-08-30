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
      'dispatcher',
      'fast',
    )

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body as string)).toMatchObject({
      guardrails_enabled: true,
      customer_id: 'CUST-ANNA',
      pattern: 'dispatcher',
      response_mode: 'fast',
    })
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

  it('does not blame the shopper for a missing route', async () => {
    // A 404 means the endpoint is not there — a wrong backend target or a dev
    // proxy pointed at the other branch's port. Classing it as a request
    // validation failure told the shopper to reword a perfectly good question,
    // so it must degrade as service availability and stay retryable.
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not Found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('Is the Hadley shirt at the Brooklyn warehouse?', [], vi.fn()),
    ).rejects.toMatchObject({
      code: 'service_unavailable',
      status: 404,
      retryable: true,
    })
  })

  it('still classifies real request validation as invalid_request', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'customer_id failed pattern check' }), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toMatchObject({
      code: 'invalid_request',
      status: 422,
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

  it('does not turn an infrastructure AccessDeniedException into a policy verdict', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: 'AccessDeniedException while invoking the configured model',
        }),
        { status: 503, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toMatchObject({
      code: 'service_unavailable',
      status: 503,
    })
  })

  it('treats an unstructured HTTP 403 as an authentication boundary', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: 'not authorized' }),
        { status: 403, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const { sendChatMessageStreaming } = await import('./chat')

    await expect(
      sendChatMessageStreaming('hello', [], vi.fn()),
    ).rejects.toMatchObject({
      code: 'authentication_required',
      status: 403,
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
