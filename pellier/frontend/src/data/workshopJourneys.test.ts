import { describe, expect, it } from 'vitest'
import {
  WORKSHOP_JOURNEYS,
  WORKSHOP_TURN_STAGES,
  journeyForLab,
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

  it('maps every Observatory lab id to its named anchor', () => {
    expect(journeyForLab('grounded-inventory')).toBe(WORKSHOP_JOURNEYS.marco)
    expect(journeyForLab('retrieval-acceptance')).toBe(WORKSHOP_JOURNEYS.anna)
    expect(journeyForLab('managed-agent-path')).toBe(WORKSHOP_JOURNEYS.theo)
    expect(journeyForLab('fail-closed-policy')).toBe(WORKSHOP_JOURNEYS.jessica)
  })
})
