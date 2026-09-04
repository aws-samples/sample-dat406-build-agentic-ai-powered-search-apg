import { afterEach, describe, expect, it, vi } from 'vitest'

import { API_BASE_URL } from './apiBase'
import { fetchMicroEval, poolCostReading } from './microEval'
import type { MicroEvalVariant } from './microEval'

const RESPONSE = {
  query: 'A housewarming gift under $100 that is currently in stock.',
  limit: 5,
  repetitions: 5,
  variants: [
    {
      pool_k: 20,
      candidate_coverage: 0.94,
      context_precision: 0.8,
      mrr: 0.83,
      hard_constraint_violations: 0,
      short_result_rate: 0.0,
      citation_coverage: 1.0,
      latency_ms_p50: 812,
      latency_ms_p95: 963,
    },
    {
      pool_k: 3,
      candidate_coverage: 0.41,
      context_precision: 0.6,
      mrr: 0.5,
      hard_constraint_violations: 2,
      short_result_rate: 0.4,
      citation_coverage: 0.7,
      latency_ms_p50: 512,
      latency_ms_p95: 604,
    },
  ],
}

function variant(over: Partial<MicroEvalVariant>): MicroEvalVariant {
  return { ...RESPONSE.variants[0], ...over }
}

describe('fetchMicroEval', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('asks for both pools in one request', async () => {
    const requested: string[] = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      requested.push(String(input))
      return new Response(JSON.stringify(RESPONSE), { status: 200 })
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchMicroEval()

    expect(requested).toEqual([
      `${API_BASE_URL}/api/observatory/search-strategies/micro-eval` +
        '?pool_k=20&pool_k=3',
    ])
    // The repetition count is the backend's to choose and its own to report.
    // Pinning a literal here would break the moment the default moved.
    expect(requested[0]).not.toMatch(/repetitions/)
    expect(result?.variants.map((entry) => entry.pool_k)).toEqual([20, 3])
  })

  it('returns null rather than a fabricated result when the endpoint is absent', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 404 })))
    expect(await fetchMicroEval()).toBeNull()
  })

  it('returns null when the payload is not the documented shape', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ query: 'x' }), { status: 200 })),
    )
    expect(await fetchMicroEval()).toBeNull()
  })

  it('accepts whatever repetition count the endpoint reports', async () => {
    for (const repetitions of [1, 3, 5, 9]) {
      vi.stubGlobal(
        'fetch',
        vi.fn(
          async () =>
            new Response(JSON.stringify({ ...RESPONSE, repetitions }), {
              status: 200,
            }),
        ),
      )
      expect((await fetchMicroEval())?.repetitions).toBe(repetitions)
    }
  })

  it('rejects a repetition count that cannot describe a run', async () => {
    for (const repetitions of [0, -2, 2.5, '3']) {
      vi.stubGlobal(
        'fetch',
        vi.fn(
          async () =>
            new Response(JSON.stringify({ ...RESPONSE, repetitions }), {
              status: 200,
            }),
        ),
      )
      expect(await fetchMicroEval()).toBeNull()
    }
  })
})

describe('poolCostReading', () => {
  it('names what the smaller pool costs when quality drops', () => {
    const reading = poolCostReading(
      variant({ pool_k: 20, candidate_coverage: 0.94, latency_ms_p50: 812 }),
      variant({ pool_k: 3, candidate_coverage: 0.41, latency_ms_p50: 512 }),
    )
    expect(reading).toContain('53 points of candidate coverage')
    expect(reading).toContain('300 ms')
  })

  it('says so plainly when the smaller pool costs no coverage', () => {
    const reading = poolCostReading(
      variant({ pool_k: 20, candidate_coverage: 0.9, latency_ms_p50: 800 }),
      variant({ pool_k: 3, candidate_coverage: 0.9, latency_ms_p50: 500 }),
    )
    expect(reading).toMatch(/no candidate coverage/i)
    expect(reading).toContain('300 ms')
  })
})
