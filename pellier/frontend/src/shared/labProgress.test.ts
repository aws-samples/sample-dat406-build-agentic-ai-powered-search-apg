import { beforeEach, describe, expect, it } from 'vitest'

import {
  LAB_PROGRESS_KEY,
  readLabProgress,
  resumeHref,
  writeLabProgress,
} from './labProgress'

describe('labProgress', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('has nothing to resume before any lab is opened', () => {
    expect(readLabProgress()).toBeNull()
  })

  it('round-trips lab, step and next action under the documented key', () => {
    writeLabProgress({
      lab: 'retrieval-acceptance',
      step: 'inspect',
      nextAction: 'Compare the four retrieval strategies on Aurora.',
    })

    const stored = JSON.parse(localStorage.getItem(LAB_PROGRESS_KEY) as string)
    expect(stored.lab).toBe('retrieval-acceptance')
    expect(stored.step).toBe('inspect')
    expect(typeof stored.updatedAt).toBe('string')

    const progress = readLabProgress()
    expect(progress).toMatchObject({
      lab: 'retrieval-acceptance',
      step: 'inspect',
      nextAction: 'Compare the four retrieval strategies on Aurora.',
    })
    expect(Number.isNaN(Date.parse(progress?.updatedAt ?? ''))).toBe(false)
  })

  it('discards a malformed or unknown record rather than resuming into nowhere', () => {
    localStorage.setItem(LAB_PROGRESS_KEY, 'not json')
    expect(readLabProgress()).toBeNull()

    localStorage.setItem(LAB_PROGRESS_KEY, JSON.stringify({ step: 'run' }))
    expect(readLabProgress()).toBeNull()

    localStorage.setItem(
      LAB_PROGRESS_KEY,
      JSON.stringify({ lab: 'no-such-lab', step: 'run', updatedAt: 'x' }),
    )
    expect(readLabProgress()).toBeNull()
  })

  it('builds a resume link that carries both the lab and the step', () => {
    expect(
      resumeHref({
        lab: 'managed-agent-path',
        step: 'reconcile',
        nextAction: '',
        updatedAt: '2026-09-04T09:00:00.000Z',
      }),
    ).toBe('/observatory/workbench?lab=managed-agent-path&step=reconcile')
  })
})
