import { describe, expect, it } from 'vitest'
import {
  WORKSHOP_JOURNEYS,
  WORKSHOP_TURN_STAGES,
  journeyForLab,
  nextJourneyPrompt,
} from './workshopJourneys'

const EXPECTED = {
  marco: [
    'What linen do you have for 10 days in Goa?',
    'What would go with the Hadley shirt?',
    'Is the Hadley shirt at the Brooklyn warehouse, and can it still ship in time?',
  ],
  anna: [
    'A thoughtful gift for someone who loves morning rituals',
    'Keep the gift under $100 and show me the strongest two options.',
    'Which one should I choose, and prove it stayed in budget and in stock?',
  ],
  theo: [
    'Hand-thrown ceramics for a slower morning routine',
    'What goes well with the pour-over set?',
    'My Wabi-Sabi Bowl arrived chipped. Please help me return it.',
  ],
  jessica: [
    "Investigate Jessica's open service issue (TKT-2026-3015) and recommend the next fair step. Distinguish what the records establish from what a source reports.",
    'Which customer, order, return, and identity records are authoritative for this decision?',
    'Prepare the fairest next step for human review without executing it.',
  ],
} as const

describe('four-lab workshop journey contract', () => {
  it('defines exactly three required turns and one surface for every anchor', () => {
    expect(WORKSHOP_TURN_STAGES).toEqual([
      'Establish context',
      'Exercise boundary',
      'Prove outcome',
    ])
    for (const [anchor, prompts] of Object.entries(EXPECTED)) {
      const journey = WORKSHOP_JOURNEYS[anchor as keyof typeof WORKSHOP_JOURNEYS]
      expect(journey.prompts).toEqual(prompts)
      expect(journey.prompts).toHaveLength(3)
    }
    expect(WORKSHOP_JOURNEYS.marco.surface).toBe('storefront')
    expect(WORKSHOP_JOURNEYS.anna.surface).toBe('storefront')
    expect(WORKSHOP_JOURNEYS.theo.surface).toBe('storefront')
    expect(WORKSHOP_JOURNEYS.jessica.surface).toBe('operator')
  })

  // The storefront pins this as the first follow-up chip, so the three-turn
  // journey flows without anyone retyping it and the room stays on its clock.
  describe('nextJourneyPrompt', () => {
    it('offers turn 2 after turn 1 and turn 3 after turn 2', () => {
      const marco = WORKSHOP_JOURNEYS.marco.prompts
      expect(nextJourneyPrompt(marco[0])).toBe(
        'What would go with the Hadley shirt?',
      )
      expect(nextJourneyPrompt(marco[1])).toBe(
        'Is the Hadley shirt at the Brooklyn warehouse, and can it still ship in time?',
      )
    })

    it('carries every storefront anchor, not just Marco', () => {
      for (const anchor of ['marco', 'anna', 'theo'] as const) {
        const prompts = WORKSHOP_JOURNEYS[anchor].prompts
        expect(nextJourneyPrompt(prompts[0])).toBe(prompts[1])
        expect(nextJourneyPrompt(prompts[1])).toBe(prompts[2])
      }
    })

    it('ends the journey at the last turn rather than inventing a fourth', () => {
      for (const journey of Object.values(WORKSHOP_JOURNEYS)) {
        expect(nextJourneyPrompt(journey.prompts[2])).toBeUndefined()
      }
    })

    it('ignores whitespace and casing, since the chip text is echoed back', () => {
      expect(
        nextJourneyPrompt('  what linen do you   have for 10 days in Goa?  '),
      ).toBe('What would go with the Hadley shirt?')
    })

    // A fuzzy match would let an ordinary shopper question that merely
    // resembles a turn hijack the thread into a script nobody chose.
    it('does not fire on a question that only resembles a turn', () => {
      expect(nextJourneyPrompt('What linen do you have for Goa?')).toBeUndefined()
      expect(nextJourneyPrompt('Do you have linen shirts?')).toBeUndefined()
      expect(nextJourneyPrompt('')).toBeUndefined()
      expect(nextJourneyPrompt(undefined)).toBeUndefined()
    })
  })

  it('maps every Observatory lab id to its named anchor', () => {
    expect(journeyForLab('grounded-inventory')).toBe(WORKSHOP_JOURNEYS.marco)
    expect(journeyForLab('retrieval-acceptance')).toBe(WORKSHOP_JOURNEYS.anna)
    expect(journeyForLab('managed-agent-path')).toBe(WORKSHOP_JOURNEYS.theo)
    expect(journeyForLab('fail-closed-policy')).toBe(WORKSHOP_JOURNEYS.jessica)
  })
})
