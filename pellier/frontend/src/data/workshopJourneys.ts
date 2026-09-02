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

const JOURNEY_BY_LAB = new Map(
  Object.values(WORKSHOP_JOURNEYS).map((journey) => [journey.labId, journey]),
)

export function journeyForLab(
  labId: string | null | undefined,
): WorkshopJourney | undefined {
  return labId ? JOURNEY_BY_LAB.get(labId as WorkshopLabId) : undefined
}
