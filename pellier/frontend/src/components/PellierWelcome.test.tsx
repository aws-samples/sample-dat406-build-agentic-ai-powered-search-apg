import { describe, expect, it } from 'vitest'
import { composeWelcomeGreeting } from './PellierWelcome'

describe('composeWelcomeGreeting', () => {
  it('adds terminal punctuation to an unfinished greeting suffix', () => {
    expect(composeWelcomeGreeting('Good evening', ', Anna')).toBe(
      'Good evening, Anna.',
    )
  })

  it('does not duplicate punctuation from a complete suffix', () => {
    expect(composeWelcomeGreeting('Good morning', ', Marco.')).toBe(
      'Good morning, Marco.',
    )
  })
})
