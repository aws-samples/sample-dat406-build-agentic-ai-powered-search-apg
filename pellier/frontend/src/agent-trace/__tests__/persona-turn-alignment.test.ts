import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  OPERATOR_TURNS,
  PERSONA_HERO_PILLS,
  PERSONA_TURN_PREVIEW,
  PERSONA_TURN_TRACES,
  turnPreviewProductId,
} from '../../data/personaCurations'
import { SHOWCASE_PRODUCTS } from '../../data/showcaseProducts'
import sessions from '../fixtures/sessions.json'
import annaMorningRitual from '../fixtures/session-anna-morning-ritual.json'
import annaUnder100 from '../fixtures/session-anna-under-100.json'
import annaCandlePairing from '../fixtures/session-anna-candle-pairing.json'
import annaBirthdayGift from '../fixtures/session-anna-birthday-gift.json'
import annaHousewarming from '../fixtures/session-anna-housewarming.json'
import marcoCapstone from '../fixtures/session-marco-capstone.json'
import marcoMidpoint from '../fixtures/session-marco-midpoint-checkpoint.json'
import marcoOpening from '../fixtures/session-marco-opening-demo.json'
import theoCeramicsReturn from '../fixtures/session-theo-ceramics-return.json'
import theoHomeNotWardrobe from '../fixtures/session-theo-home-not-wardrobe.json'
import theoLinenSeasons from '../fixtures/session-theo-linen-seasons.json'
import theoPourOver from '../fixtures/session-theo-pour-over.json'
import theoPourOverPairing from '../fixtures/session-theo-pour-over-pairing.json'

const CANONICAL_PERSONAS = ['marco', 'anna', 'theo'] as const

const EXPECTED_TURNS = {
  marco: [
    'Browse linen for a Goa carry-on',
    'Pair something with the Hadley shirt',
    'Compare Hadley with the Italian Linen Camp Shirt',
    'Linen shirt price range',
    'Hadley availability in Brooklyn',
  ],
  anna: [
    'Housewarming gift under $200 for a ceramics lover',
    'Anniversary gift using past orders',
    'Trending home gifts',
    'Latest receipt for find_pieces_hybrid',
    'A sensitive sympathy gift that needs a human touch',
  ],
  theo: [
    'Hand-thrown pieces for a morning ritual',
    'Care and return window for the linen throw',
    'File a damaged Wabi-Sabi Bowl return',
    'Prove the return was recorded',
    'Out-of-window durability exception for the linen throw',
  ],
} satisfies Record<(typeof CANONICAL_PERSONAS)[number], string[]>

const EXPECTED_TRACES = {
  marco: [
    { skills: ['the-packing-list'], tools: ['explore_collection'] },
    {
      skills: ['the-packing-list'],
      tools: ['find_pieces', 'style_match'],
    },
    { skills: [], tools: ['find_pieces', 'side_by_side'] },
    { skills: [], tools: ['price_intelligence'] },
    { skills: [], tools: ['floor_check'] },
  ],
  anna: [
    {
      skills: ['the-gift-table', 'the-makers-shelf'],
      tools: ['find_pieces_hybrid'],
    },
    {
      skills: ['the-proof-counter', 'the-gift-table'],
      tools: ['preference_snapshot', 'find_pieces_hybrid'],
    },
    { skills: ['the-gift-table'], tools: ['whats_trending'] },
    { skills: ['the-proof-counter'], tools: ['trace_receipt'] },
    { skills: ['the-gift-table'], tools: ['escalate_to_stylist'] },
  ],
  theo: [
    { skills: ['the-makers-shelf'], tools: ['find_pieces'] },
    {
      skills: ['the-care-card'],
      tools: ['find_pieces', 'returns_and_care'],
    },
    {
      skills: ['the-care-card'],
      tools: ['find_pieces', 'returns_and_care', 'process_return'],
    },
    { skills: ['the-proof-counter'], tools: ['trace_receipt'] },
    { skills: ['the-care-card'], tools: ['escalate_to_stylist'] },
  ],
} satisfies Pick<typeof PERSONA_TURN_TRACES, (typeof CANONICAL_PERSONAS)[number]>

const FIXTURE_ENTRYPOINTS = [
  { session: marcoOpening, expected: PERSONA_HERO_PILLS.marco[0] },
  { session: marcoMidpoint, expected: PERSONA_HERO_PILLS.marco[4] },
  { session: marcoCapstone, expected: PERSONA_HERO_PILLS.marco[2] },
  { session: annaMorningRitual, expected: PERSONA_HERO_PILLS.anna[0] },
  { session: annaUnder100, expected: PERSONA_HERO_PILLS.anna[1] },
  { session: annaCandlePairing, expected: PERSONA_HERO_PILLS.anna[2] },
  { session: annaBirthdayGift, expected: PERSONA_HERO_PILLS.anna[3] },
  { session: annaHousewarming, expected: PERSONA_HERO_PILLS.anna[4] },
  { session: theoPourOver, expected: PERSONA_HERO_PILLS.theo[0] },
  { session: theoPourOverPairing, expected: PERSONA_HERO_PILLS.theo[3] },
  { session: theoLinenSeasons, expected: PERSONA_HERO_PILLS.theo[1] },
  { session: theoCeramicsReturn, expected: PERSONA_HERO_PILLS.theo[2] },
  { session: theoHomeNotWardrobe, expected: PERSONA_HERO_PILLS.theo[4] },
] as const

describe('persona turn alignment', () => {
  it('keeps Marco, Anna, and Theo at exactly five canonical Pellier turns', () => {
    for (const persona of CANONICAL_PERSONAS) {
      expect(PERSONA_HERO_PILLS[persona]).toHaveLength(5)
      expect(PERSONA_HERO_PILLS[persona]).toEqual(EXPECTED_TURNS[persona])
    }
  })

  it('keeps Pellier Labs replay entrypoints aligned with Pellier turn strings', () => {
    for (const { session, expected } of FIXTURE_ENTRYPOINTS) {
      expect(session.openingQuery).toBe(expected)
      expect(session.chat[0]?.role).toBe('user')
      expect(session.chat[0]?.content).toBe(expected)

      const listedSession = sessions.find((item) => item.id === session.id)
      expect(listedSession?.openingQuery).toBe(expected)
    }
  })

  it('keeps expected skills and tools aligned turn-by-turn', () => {
    for (const persona of CANONICAL_PERSONAS) {
      expect(PERSONA_TURN_TRACES[persona]).toHaveLength(5)
      expect(PERSONA_TURN_TRACES[persona]).toEqual(EXPECTED_TRACES[persona])
    }
  })

  it('covers every registered tool without assigning operator tools to shoppers', () => {
    const shopperTools = new Set(
      CANONICAL_PERSONAS.flatMap((persona) =>
        PERSONA_TURN_TRACES[persona].flatMap((trace) => trace.tools),
      ),
    )
    const operatorTools = new Set(OPERATOR_TURNS.flatMap((turn) => turn.tools))
    const allTools = new Set([...shopperTools, ...operatorTools])

    expect([...allTools].sort()).toEqual(
      [
        'escalate_to_stylist',
        'explore_collection',
        'find_pieces',
        'find_pieces_hybrid',
        'floor_check',
        'preference_snapshot',
        'price_intelligence',
        'process_return',
        'restock_shelf',
        'returns_and_care',
        'running_low',
        'side_by_side',
        'style_match',
        'trace_receipt',
        'whats_trending',
      ].sort(),
    )
    expect(shopperTools).not.toContain('running_low')
    expect(shopperTools).not.toContain('restock_shelf')
    expect([...operatorTools].sort()).toEqual(
      ['restock_shelf', 'running_low'].sort(),
    )
  })

  it('covers all five runtime skills across the canonical shopper turns', () => {
    const skills = new Set(
      CANONICAL_PERSONAS.flatMap((persona) =>
        PERSONA_TURN_TRACES[persona].flatMap((trace) => trace.skills),
      ),
    )
    expect([...skills].sort()).toEqual(
      [
        'the-care-card',
        'the-gift-table',
        'the-makers-shelf',
        'the-packing-list',
        'the-proof-counter',
      ].sort(),
    )
  })

  it('gives every curated turn a preview slot', () => {
    for (const persona of [...CANONICAL_PERSONAS, 'fresh'] as const) {
      expect(PERSONA_TURN_PREVIEW[persona]).toHaveLength(
        PERSONA_HERO_PILLS[persona].length,
      )
    }
  })

  it('resolves every turn preview to a real catalog product', () => {
    for (const [persona, previews] of Object.entries(PERSONA_TURN_PREVIEW)) {
      previews.forEach((productId, index) => {
        if (productId === null) return
        const product = SHOWCASE_PRODUCTS.find((item) => item.id === productId)
        expect(
          product,
          `${persona} turn ${index + 1} preview id ${productId} is not in SHOWCASE_PRODUCTS`,
        ).toBeDefined()
        expect(product?.imageUrl).toMatch(/^\/products\/.+\.png$/)
      })
    }
  })

  it('ships the AVIF and WebP derivatives every turn preview renders', () => {
    for (const [persona, previews] of Object.entries(PERSONA_TURN_PREVIEW)) {
      previews.forEach((productId, index) => {
        if (productId === null) return
        const product = SHOWCASE_PRODUCTS.find((item) => item.id === productId)
        const base = (product?.imageUrl ?? '').replace(/\.png$/, '')
        for (const width of [480, 960]) {
          for (const format of ['avif', 'webp']) {
            const file = resolve(process.cwd(), `public${base}-${width}.${format}`)
            expect(
              existsSync(file),
              `${persona} turn ${index + 1} is missing public${base}-${width}.${format}`,
            ).toBe(true)
          }
        }
      })
    }
  })

  it('omits imagery for proof and human-handoff turns only', () => {
    expect(PERSONA_TURN_PREVIEW.marco).not.toContain(null)
    expect(turnPreviewProductId('anna', 3)).toBeNull()
    expect(turnPreviewProductId('anna', 4)).toBeNull()
    expect(turnPreviewProductId('theo', 3)).toBeNull()
    expect(turnPreviewProductId('theo', 4)).toBeNull()
    expect(turnPreviewProductId('fresh', 4)).not.toBeNull()
  })

  it('falls back to the fresh previews for an unknown persona', () => {
    expect(turnPreviewProductId('nobody', 0)).toBe(
      PERSONA_TURN_PREVIEW.fresh[0],
    )
    expect(turnPreviewProductId(null, 1)).toBe(PERSONA_TURN_PREVIEW.fresh[1])
  })
})
