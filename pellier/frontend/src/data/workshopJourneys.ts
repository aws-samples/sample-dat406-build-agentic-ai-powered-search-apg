export const WORKSHOP_TURN_STAGES = [
  'Establish context',
  'Exercise boundary',
  'Prove outcome',
] as const

export type WorkshopTurnStage = (typeof WORKSHOP_TURN_STAGES)[number]
export type WorkshopAnchorId = 'marco' | 'anna' | 'theo' | 'jessica'
export type WorkshopJourneySurface = 'storefront' | 'operator'
export type WorkshopLabId =
  | 'grounded-inventory'
  | 'retrieval-acceptance'
  | 'managed-agent-path'
  | 'fail-closed-policy'

export interface WorkshopJourney {
  anchorId: WorkshopAnchorId
  anchorName: 'Marco' | 'Anna' | 'Theo' | 'Jessica'
  customerId: 'CUST-MARCO' | 'CUST-ANNA' | 'CUST-THEO' | 'CUST-JESSICA'
  labId: WorkshopLabId
  surface: WorkshopJourneySurface
  prompts: readonly [string, string, string]
}

export const WORKSHOP_JOURNEYS: Record<WorkshopAnchorId, WorkshopJourney> = {
  marco: {
    anchorId: 'marco',
    anchorName: 'Marco',
    customerId: 'CUST-MARCO',
    labId: 'grounded-inventory',
    surface: 'storefront',
    prompts: [
      'What linen do you have for 10 days in Goa?',
      'What would go with the Hadley shirt?',
      'Is the Hadley shirt at the Brooklyn warehouse, and can it still ship in time?',
    ],
  },
  anna: {
    anchorId: 'anna',
    anchorName: 'Anna',
    customerId: 'CUST-ANNA',
    labId: 'retrieval-acceptance',
    surface: 'storefront',
    prompts: [
      'A thoughtful gift for someone who loves morning rituals',
      'Keep the gift under $100 and show me the strongest two options.',
      'Which one should I choose, and prove it stayed in budget and in stock?',
    ],
  },
  theo: {
    anchorId: 'theo',
    anchorName: 'Theo',
    customerId: 'CUST-THEO',
    labId: 'managed-agent-path',
    surface: 'storefront',
    prompts: [
      'Hand-thrown ceramics for a slower morning routine',
      'What goes well with the pour-over set?',
      'My Wabi-Sabi Bowl arrived chipped. Please help me return it.',
    ],
  },
  jessica: {
    anchorId: 'jessica',
    anchorName: 'Jessica',
    customerId: 'CUST-JESSICA',
    labId: 'fail-closed-policy',
    surface: 'operator',
    prompts: [
      "Investigate Jessica's open service issue (TKT-2026-3015) and recommend the next fair step. Distinguish what the records establish from what a source reports.",
      'Which customer, order, return, and identity records are authoritative for this decision?',
      'Prepare the fairest next step for human review without executing it.',
    ],
  },
}

/**
 * The next scripted prompt after `query`, when `query` is a journey turn.
 *
 * The storefront pins this as the first follow-up chip so a shopper who
 * clicked Marco's turn 1 is offered turn 2 rather than a generic catalog
 * action. Two things make that safe to force: the room is on a clock and the
 * journey is the demo, and the chip is the participant's own next step rather
 * than a claim about the answer.
 *
 * Matching is exact after normalisation, deliberately. A fuzzy match would let
 * an ordinary shopper question that merely resembles a turn hijack the thread
 * into a script they never chose. The pills send these strings verbatim, so
 * exact is the behaviour that is wanted.
 *
 * Returns undefined for the last turn: a journey that has ended has no next
 * step, and inventing one would push past the bounded path.
 */
function normalizePrompt(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ')
}

export function nextJourneyPrompt(
  query: string | null | undefined,
): string | undefined {
  if (!query) return undefined
  const needle = normalizePrompt(query)
  if (!needle) return undefined
  for (const journey of Object.values(WORKSHOP_JOURNEYS)) {
    const turn = journey.prompts.findIndex(
      (prompt) => normalizePrompt(prompt) === needle,
    )
    if (turn >= 0 && turn + 1 < journey.prompts.length) {
      return journey.prompts[turn + 1]
    }
  }
  return undefined
}

const JOURNEY_BY_LAB = new Map(
  Object.values(WORKSHOP_JOURNEYS).map((journey) => [journey.labId, journey]),
)

export function journeyForLab(
  labId: string | null | undefined,
): WorkshopJourney | undefined {
  return labId ? JOURNEY_BY_LAB.get(labId as WorkshopLabId) : undefined
}
