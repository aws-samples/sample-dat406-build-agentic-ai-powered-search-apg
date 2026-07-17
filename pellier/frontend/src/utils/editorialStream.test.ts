import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createEditorialStreamController,
  splitEditorialDelta,
} from './editorialStream'

afterEach(() => {
  vi.useRealTimers()
})

describe('editorialStream', () => {
  it('paces bursty deltas while preserving every character', async () => {
    vi.useFakeTimers()
    let rendered = ''
    const stream = createEditorialStreamController({
      onAppend: chunk => {
        rendered += chunk
      },
      onReset: () => {
        rendered = ''
      },
    })
    const answer = 'For ten days in Goa, start with washed linen.'

    stream.push(answer)

    expect(rendered).toBe('For ')
    expect(rendered).not.toBe(answer)

    const settled = stream.settle()
    await vi.runAllTimersAsync()
    await settled

    expect(rendered).toBe(answer)
  })

  it('drops queued pre-tool prose across a content reset', async () => {
    vi.useFakeTimers()
    let rendered = ''
    const stream = createEditorialStreamController({
      onAppend: chunk => {
        rendered += chunk
      },
      onReset: () => {
        rendered = ''
      },
    })

    stream.push('Draft language that must not leak through.')
    expect(rendered).toBe('Draft ')

    stream.reset()
    stream.push('Final considered answer.')

    const settled = stream.settle()
    await vi.runAllTimersAsync()
    await settled

    expect(rendered).toBe('Final considered answer.')
  })

  it('renders deltas immediately when reduced motion is requested', async () => {
    let rendered = ''
    const stream = createEditorialStreamController({
      onAppend: chunk => {
        rendered += chunk
      },
      onReset: () => {
        rendered = ''
      },
      reducedMotion: true,
    })

    stream.push('No artificial pacing.')
    await stream.settle()

    expect(rendered).toBe('No artificial pacing.')
  })

  it('splits words without changing whitespace or punctuation', () => {
    const delta = 'Linen,  layered\nfor Goa.'
    expect(splitEditorialDelta(delta).join('')).toBe(delta)
  })
})
