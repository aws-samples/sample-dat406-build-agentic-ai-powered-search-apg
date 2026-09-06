import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  fetchTurnEvidenceLedger,
  requiredEvidenceSatisfied,
} from './evidenceLedger'
import type { EvidenceSufficiencyCheck } from '../shared/evidenceLedger'

function check(status: EvidenceSufficiencyCheck['status']): EvidenceSufficiencyCheck {
  return { id: status, label: status, status, detail: '' }
}

describe('requiredEvidenceSatisfied', () => {
  it('is false for an empty ledger: nothing recorded is not everything recorded', () => {
    expect(requiredEvidenceSatisfied([])).toBe(false)
  })

  it('ignores checks that do not apply to the turn', () => {
    expect(
      requiredEvidenceSatisfied([
        check('satisfied'),
        check('not_applicable'),
      ]),
    ).toBe(true)
  })

  it.each([
    'missing',
    'unavailable',
    'not_reached',
    'not_enforced',
    // A refuted claim is the strongest reason of all to withhold the seal.
    'contradicted',
  ] as const)(
    'is false when any required check reads %s',
    (status) => {
      expect(
        requiredEvidenceSatisfied([check('satisfied'), check(status)]),
      ).toBe(false)
    },
  )
})

describe('fetchTurnEvidenceLedger', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('reads the principal-scoped ledger for one turn with credentials', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ turnId: 't/1', events: [], evidenceSufficiency: [] }), {
        status: 200,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const ledger = await fetchTurnEvidenceLedger('t/1')

    expect(ledger?.turnId).toBe('t/1')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/observatory/turns/t%2F1/ledger',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('returns null rather than a fabricated ledger when the API refuses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('{"detail":"ledger_not_found"}', { status: 404 })),
    )

    expect(await fetchTurnEvidenceLedger('missing')).toBeNull()
  })
})
