/**
 * personaCurations — the single source of truth for how each persona
 * reshapes the storefront's "Curated for you" ordering and
 * "Because you asked..." editorial lineup.
 *
 * Design:
 *   - Each persona declares a set of weighted tag interests. Those
 *     interests are applied against SHOWCASE_PRODUCTS[*].tags to
 *     compute a score per product; the Curated grid sorts products
 *     descending by score.
 *   - Each persona also declares its own ordered list of editorial
 *     cards for the "Because you asked..." band. Marco sees
 *     travel/linen cards first, Anna sees gift-focused, Theo sees
 *     home rituals.
 *   - The "fresh" persona (anonymous / first-time visitor) falls
 *     through to the canonical unbiased ordering — same product list,
 *     no scoring, and the generic editorial cards.
 *
 * Why not backend: the point of this round is the demo surface — the
 * personalization should be visible the instant an attendee picks a
 * persona from the welcome chip, no network round-trip. When a real
 * recommendation service ships, this file becomes a client-side
 * fallback that mirrors the server's ranking heuristic.
 */

import type { BoutiqueProduct } from '../services/types'

// ---------------------------------------------------------------------
// Persona interest profiles. Scores are 0-10; higher = stronger lean.
// Applied as a dot product against the product's tag set.
// ---------------------------------------------------------------------

export interface PersonaInterests {
  /** Tag → weight. Unmatched tags contribute 0. */
  tagWeights: Record<string, number>
  /** Optional section headline override. Falls back to canonical if unset. */
  curatedHeadline?: string
  /** Optional section eyebrow override. */
  curatedEyebrow?: string
}

export const PERSONA_INTERESTS: Record<string, PersonaInterests> = {
  marco: {
    // Natural fibers, travel-ready, timeless accessories. Marco reads
    // the storefront looking for pieces that hold up on the road and
    // get softer with wear.
    tagWeights: {
      linen: 10,
      travel: 9,
      leather: 8,
      classic: 7,
      warm: 6,
      earth: 6,
      timeless: 6,
      accessories: 5,
      minimal: 5,
      resort: 5,
      everyday: 4,
      neutral: 3,
    },
    curatedEyebrow: 'Curated for Marco',
    curatedHeadline: 'Pieces that travel.',
  },
  anna: {
    // Gift-focused, milestone occasions. Anna lands on the site with
    // a someone in mind — she wants pieces that arrive well-wrapped,
    // land across price bands, and read as considered.
    tagWeights: {
      candle: 10,
      beauty: 9,
      apothecary: 9,
      ceramic: 8,
      home: 7,
      sculptural: 7,
      artisanal: 7,
      warm: 6,
      minimal: 6,
      accessories: 5,
      timeless: 5,
      classic: 4,
    },
    curatedEyebrow: 'Curated for Anna',
    curatedHeadline: 'Gifts, thoughtfully matched.',
  },
  theo: {
    // Slow-craft, home rituals. Theo cares about ceramics, linen that
    // softens with washing, objects with patina. The home/wellness
    // cluster wins over travel or accessories.
    tagWeights: {
      ceramic: 10,
      slow: 10,
      artisanal: 9,
      home: 9,
      wellness: 8,
      linen: 8,
      sculptural: 7,
      minimal: 6,
      neutral: 5,
      warm: 5,
      loungewear: 5,
      candle: 4,
    },
    curatedEyebrow: 'Curated for Theo',
    curatedHeadline: 'Quiet pieces, lived-in.',
  },
  fresh: {
    // Canonical editorial ordering — no persona lean. Equal weights
    // are a no-op against the sort comparator, so the products render
    // in their declared showcase order.
    tagWeights: {},
  },
}

/**
 * Score one product against a persona's tag weights. Returns 0 for the
 * fresh persona or any persona with an empty weight map — in that case
 * callers fall through to the product's natural order.
 */
export function scoreProduct(
  product: BoutiqueProduct,
  weights: Record<string, number>,
): number {
  if (!product.tags || product.tags.length === 0) return 0
  let score = 0
  for (const tag of product.tags) {
    score += weights[tag] ?? 0
  }
  return score
}

/**
 * Stable sort SHOWCASE_PRODUCTS for a given persona. Products with no
 * matching tags keep their original relative order (stable sort), so
 * a persona without a full coverage of the catalog still sees the
 * remainder in a predictable sequence.
 */
export function rankProductsForPersona<T extends BoutiqueProduct>(
  products: readonly T[],
  personaId: string | null | undefined,
): T[] {
  const interests = personaId ? PERSONA_INTERESTS[personaId] : undefined
  if (!interests || Object.keys(interests.tagWeights).length === 0) {
    return [...products]
  }
  // Decorate-sort-undecorate preserves the original index as a
  // tiebreaker, giving a stable sort without needing Array.sort's
  // stability guarantee (which holds in modern engines but is safer
  // made explicit for workshop attendees reading the code).
  const decorated = products.map((p, i) => ({
    product: p,
    score: scoreProduct(p, interests.tagWeights),
    index: i,
  }))
  decorated.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    return a.index - b.index
  })
  return decorated.map(d => d.product)
}

// ---------------------------------------------------------------------
// Editorial cards for "Because you asked..."
//
// Each persona gets a hand-picked set of cards that echo the language
// they'd have used in chat. The fresh persona falls back to the
// canonical generic set (Gifts / Performance / Linen / Home Rituals).
// ---------------------------------------------------------------------

export interface EditorialCard {
  category: string
  title: string
  description: string
}

export const CANONICAL_EDITORIAL: EditorialCard[] = [
  {
    category: 'Gifts',
    title: 'The art of giving well.',
    description:
      'Thoughtful pieces that arrive wrapped in tissue and tied with intention. For the person who notices the details.',
  },
  {
    category: 'Performance and Luxury',
    title: 'Where function meets form.',
    description:
      'Technical fabrics, considered construction. Pieces that perform without announcing it.',
  },
  {
    category: 'Linen Edits',
    title: 'The fabric of slower days.',
    description:
      'Washed, softened, lived-in. Our linen collection gets better with every wear and every wash.',
  },
  {
    category: 'Home Rituals',
    title: 'Objects worth reaching for.',
    description:
      'Ceramic, stoneware, hand-thrown. The everyday pieces that turn a morning routine into a ritual.',
  },
]

export const PERSONA_EDITORIAL: Record<string, EditorialCard[]> = {
  marco: [
    {
      category: 'Weekend escapes',
      title: 'Packed in a single bag.',
      description:
        'Linen that wrinkles honestly, leather that patinas. The pieces that make a 48-hour trip feel unhurried.',
    },
    {
      category: 'Linen edits',
      title: 'Softened by the sun.',
      description:
        'Breathable weaves, warm oat tones. Shirts that earn their golden hour and forgive the rest.',
    },
    {
      category: 'Everyday carry',
      title: 'The weekender, reconsidered.',
      description:
        'Full-grain leather, canvas lining, the quiet kind of heft. A bag that outlasts the trips.',
    },
    {
      category: 'Quiet accessories',
      title: 'Classic, undated.',
      description:
        'Rectangular watches, apothecary notes. Pieces that do not announce themselves. They just show up.',
    },
  ],
  anna: [
    {
      category: 'Gifting',
      title: 'Wrapped with intention.',
      description:
        'Ceramic, candle, tumbler. Pieces that arrive ready, with no last-minute ribbon or second-guessing.',
    },
    {
      category: 'Milestones',
      title: 'For the occasion that matters.',
      description:
        'Anniversary, housewarming, just-because. Considered objects across every price band.',
    },
    {
      category: 'Home rituals',
      title: 'Everyday beauty, wrapped.',
      description:
        'Sculptural vessels, hand-thrown ceramic. The kind of piece someone actually displays.',
    },
    {
      category: 'Apothecary',
      title: 'Scent, considered.',
      description:
        'Neroli, santal, fig. Small-batch candles and oils that make a gift arrive before it’s opened.',
    },
  ],
  theo: [
    {
      category: 'Slow living',
      title: 'Ritual, not routine.',
      description:
        'Hand-thrown ceramic, washed linen, stoneware tumblers. Objects that reward slowness.',
    },
    {
      category: 'Home rituals',
      title: 'The morning table.',
      description:
        'Woven mats, sculptural vessels. Pieces that make a quiet hour feel intentional.',
    },
    {
      category: 'Wellness',
      title: 'Considered craft.',
      description:
        'Small-batch, artisanal, made in volumes that matter. Pieces with patina, not polish.',
    },
    {
      category: 'Linen edits',
      title: 'Softer with every wash.',
      description:
        'Lounge sets that lean into the weekend. Fabric that loosens around you over seasons.',
    },
  ],
}

/**
 * Resolve the editorial lineup for the active persona, falling back to
 * the canonical set for fresh/unknown personas.
 */
export function editorialForPersona(
  personaId: string | null | undefined,
): EditorialCard[] {
  if (!personaId) return CANONICAL_EDITORIAL
  return PERSONA_EDITORIAL[personaId] ?? CANONICAL_EDITORIAL
}

// ---------------------------------------------------------------------
// Hero suggestion pills — persona-specific "Try asking" queries.
// Each persona sees 5 pills grounded in their interests.
// Fresh visitors see the canonical set.
// ---------------------------------------------------------------------

// Hero pills are the canonical five-turn journeys shared by the storefront,
// Pellier Labs, Persona Journeys, and replay fixtures.
export const PERSONA_HERO_PILLS: Record<string, string[]> = {
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
  fresh: [
    'A thoughtful gift for someone who runs',
    'Pieces for slow Sunday mornings',
    'Something to wear for warm evenings out',
    'Linen pieces that travel well',
    'A cozy layer for cooler nights',
  ],
}

/** Marco Turn 5 is the workshop's stub-to-wired Stock Keeper checkpoint. */
export const MARCO_BUILDER_SESSION_QUERY = PERSONA_HERO_PILLS.marco[4]

/**
 * Short display labels for hero pills. The underlying click-fire query
 * (in PERSONA_HERO_PILLS) stays verbatim — these labels exist purely so
 * longer query strings do not crowd the compact storefront pill grid. A
 * `null` (or missing entry) falls back to the full query.
 */
export const PERSONA_HERO_PILL_LABELS: Record<string, (string | null)[]> = {
  marco: [null, null, null, null, null],
  anna: [null, null, null, null, 'A sensitive sympathy gift'],
  theo: [null, null, null, null, 'Durability exception for the linen throw'],
  fresh: [null, null, null, null, null],
}

/** Display label for hero pill at `index` in the persona's list. */
export function heroPillLabel(
  personaId: string | null | undefined,
  index: number,
  fallback: string,
): string {
  const key = personaId ?? 'fresh'
  return PERSONA_HERO_PILL_LABELS[key]?.[index] ?? fallback
}

export function heroPillsForPersona(
  personaId: string | null | undefined,
): string[] {
  if (!personaId) return PERSONA_HERO_PILLS.fresh
  return PERSONA_HERO_PILLS[personaId] ?? PERSONA_HERO_PILLS.fresh
}

export interface PersonaTurnTrace {
  skills: string[]
  tools: string[]
}

export const PERSONA_TURN_TRACES: Record<string, PersonaTurnTrace[]> = {
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
  fresh: PERSONA_HERO_PILLS.fresh.map(() => ({
    skills: [],
    tools: ['find_pieces'],
  })),
}

export interface OperatorTurn {
  id: 'running-low' | 'restock-product-37'
  label: string
  query: string
  tools: string[]
  access: 'read' | 'write'
}

/** Inventory operations stay explicit and separate from shopper personas. */
export const OPERATOR_TURNS: OperatorTurn[] = [
  {
    id: 'running-low',
    label: 'Review low stock',
    query: 'Which pieces are running low?',
    tools: ['running_low'],
    access: 'read',
  },
  {
    id: 'restock-product-37',
    label: 'Restock product 37',
    query: 'Restock product 37 by 12 units.',
    tools: ['restock_shelf'],
    access: 'write',
  },
]

// ---------------------------------------------------------------------
// Turn preview imagery — the catalog photograph shown on each curated
// turn card in Pellier Labs.
//
// Every entry is a real SHOWCASE_PRODUCTS id whose 480/960 AVIF + WebP
// derivatives exist under public/products/, so Labs renders the same
// optimized imagery the storefront does.
//
// IMPORTANT: this is an editorial preview of the turn's SUBJECT, not a
// claim about its result set. The live agent decides what a turn
// actually returns; those results render separately from the run. Card
// copy must never present these as the products the turn will return.
//
// `null` means the card renders with no photograph because the turn returns
// proof or a human handoff rather than a catalog recommendation.
// ---------------------------------------------------------------------

export const PERSONA_TURN_PREVIEW: Record<string, (number | null)[]> = {
  marco: [
    11, // Italian Linen Camp Shirt - linen for warm-weather travel
    14, // Linen Drawstring Trousers - the pairing ask
    2,  // Hadley Linen Shirt - one side of the comparison
    16, // Linen Overshirt, Sage - a linen shirt in the price band
    2,  // Hadley Linen Shirt - the inventory ask names it
  ],
  anna: [
    27,   // Ceramic Bud Vase - housewarming ceramics
    21,   // Beeswax Taper Candles - anniversary gift candidate
    31,   // Stoneware Pour-Over Set - trending home object
    null, // audit receipt: no product
    null, // stylist handoff: no product
  ],
  theo: [
    31,   // Stoneware Pour-Over Set - morning ritual
    32,   // Raw Linen Throw - care and return policy
    37,   // Wabi-Sabi Bowl - damaged return
    null, // audit receipt: no product
    null, // exception handoff: no product
  ],
  fresh: [
    9,    // Cloudform Studio Runner — a gift for someone who runs
    8,    // Alba Linen Lounge Set — slow Sunday mornings
    11,   // Italian Linen Camp Shirt — warm evenings out
    14,   // Linen Drawstring Trousers — travels well
    16,   // Linen Overshirt, Sage — a cooler-night layer
  ],
}

/**
 * Preview product id for the curated turn at `index`, or null when the card
 * should render without a photograph.
 */
export function turnPreviewProductId(
  personaId: string | null | undefined,
  index: number,
): number | null {
  const key = personaId ?? 'fresh'
  const previews = PERSONA_TURN_PREVIEW[key] ?? PERSONA_TURN_PREVIEW.fresh
  return previews[index] ?? null
}

// ---------------------------------------------------------------------
// Featured product ID — the big hero product slot per persona.
// Maps persona → product ID from SHOWCASE_PRODUCTS.
// Fresh visitors see the Nocturne Leather Weekender (id:3 in the
// original lineup; check actual IDs in showcaseProducts.ts).
// ---------------------------------------------------------------------

export const PERSONA_FEATURED_PRODUCT_ID: Record<string, number> = {
  marco: 2,   // Pellier Linen Shirt — Marco's signature linen piece
  anna: 21,    // Beeswax Taper Candles & Fig Candle — gift-forward, wrap-ready
  theo: 31,    // Stoneware Pour-Over Set Woven Mat Set — slow ritual centerpiece
  fresh: 3,   // Nocturne Leather Weekender — editorial hero for new visitors
}

export function featuredProductIdForPersona(
  personaId: string | null | undefined,
): number {
  if (!personaId) return PERSONA_FEATURED_PRODUCT_ID.fresh
  return PERSONA_FEATURED_PRODUCT_ID[personaId] ?? PERSONA_FEATURED_PRODUCT_ID.fresh
}

// ---------------------------------------------------------------------
// Weekend Edit — persona-specific editorial eyebrow + headline + copy.
// The "Weekend, re:defined." block on BoutiquePage swaps entirely
// based on persona so the editorial voice matches the shopper.
// ---------------------------------------------------------------------

export interface WeekendEditContent {
  eyebrow: string
  headline: string
  subheadline: string
}

export const PERSONA_WEEKEND_EDIT: Record<string, WeekendEditContent> = {
  marco: {
    eyebrow: 'The Travel Edit',
    headline: 'Packed light,\nlived fully.',
    subheadline:
      'Linen that softens on the road, leather that earns its patina. A 48-hour wardrobe that never feels rushed.',
  },
  anna: {
    eyebrow: 'The Gift Edit',
    headline: 'Giving,\nre:considered.',
    subheadline:
      'Pieces that arrive wrapped with intention. For the milestone, the just-because, and the person who has everything.',
  },
  theo: {
    eyebrow: 'The Slow Edit',
    headline: 'Ritual,\nnot routine.',
    subheadline:
      'Hand-thrown ceramic, washed linen, stoneware that rewards slowness. The morning table, made intentional.',
  },
  fresh: {
    eyebrow: 'Weekend Edit',
    headline: 'Weekend,\nre:defined.',
    subheadline:
      'Pieces that move with you from morning markets to golden-hour terraces. Linen, leather, and ceramic for a considered weekend wardrobe.',
  },
}

export function weekendEditForPersona(
  personaId: string | null | undefined,
): WeekendEditContent {
  if (!personaId) return PERSONA_WEEKEND_EDIT.fresh
  return PERSONA_WEEKEND_EDIT[personaId] ?? PERSONA_WEEKEND_EDIT.fresh
}

// ---------------------------------------------------------------------
// Profile-aware prompts — a second row of suggestion pills under the hero
// search bar. Copy describes declared workshop seeds, never uncollected live
// memory, trend, or inventory evidence.
// Each chip carries a `kind` (memory | trend | inventory | weather) and
// the human-readable copy that follows. The hero renders them as
// dashed italic chips with the kind label as a tiny eyebrow.
// ---------------------------------------------------------------------

export type BecauseChipKind = 'memory' | 'trend' | 'inventory' | 'weather'

export interface BecauseChip {
  kind: BecauseChipKind
  /** Human-readable reason, leads with a verb-less clause. */
  text: string
  /** Optional query to fire when the chip is clicked. */
  query?: string
}

export const PERSONA_BECAUSE_CHIPS: Record<string, BecauseChip[]> = {
  marco: [
    {
      kind: 'memory',
      text: "Marco's profile favors linen and travel",
      query: 'Show me linen pieces like the Camp Shirt',
    },
    {
      kind: 'trend',
      text: 'build a lightweight edit for a ten-day trip',
      query: PERSONA_HERO_PILLS.marco[0],
    },
  ],
  anna: [
    {
      kind: 'memory',
      text: "Anna's profile favors gifting and home",
      // Fires Anna's canonical rerank anchor verbatim so the lab guide's
      // "click, don't type" path matches memory-anna.json and the
      // search-strategies comparison. Keep this string in sync with the
      // Performance card's pre-filled query.
      query: 'A milestone gift for a new homeowner',
    },
    {
      kind: 'trend',
      text: 'compare a candle with a wrapped pairing',
      query: 'Show me the Beeswax Taper Candles',
    },
  ],
  theo: [
    {
      kind: 'memory',
      text: "Theo's profile favors slow craft and ceramics",
      query: 'Pieces that pair with the Pour-Over Set',
    },
    {
      kind: 'inventory',
      text: 'run the damaged-bowl return flow',
      query: 'File a damaged return for the Wabi-Sabi Bowl',
    },
  ],
  fresh: [
    {
      kind: 'trend',
      text: 'explore the linen edit',
      query: 'Show me linen pieces',
    },
    {
      kind: 'inventory',
      text: 'build a thoughtful gift shortlist',
      query: 'A thoughtful gift for someone who runs',
    },
  ],
}

export function becauseChipsForPersona(
  personaId: string | null | undefined,
): BecauseChip[] {
  if (!personaId) return PERSONA_BECAUSE_CHIPS.fresh
  return PERSONA_BECAUSE_CHIPS[personaId] ?? PERSONA_BECAUSE_CHIPS.fresh
}

// ---------------------------------------------------------------------
// Workshop profile handoff — the deterministic seed and scenario boundary
// for the selected persona. Durable memory and action receipts are only
// claimed after the participant generates them in the active session.
// ---------------------------------------------------------------------

export interface MemoryHandoffItem {
  /** Source or boundary label rendered in mono. */
  tool: string
  /** Plain-language line. */
  text: string
}

export interface MemoryHandoffContent {
  eyebrow: string
  /** Short italic Fraunces title. */
  title: string
  items: MemoryHandoffItem[]
  /** CTA label (defaults to "Pick up where I left off"). */
  cta?: string
}

export const PERSONA_MEMORY_HANDOFF: Record<string, MemoryHandoffContent> = {
  marco: {
    eyebrow: 'Workshop profile · Marco',
    title: 'Travel and natural-fiber preferences seed this session.',
    items: [
      { tool: 'profile.seed', text: 'Linen, travel, leather, and classic tags receive higher weights' },
      { tool: 'scenario.prompt', text: 'The core prompt asks for a ten-day Goa edit' },
      { tool: 'session.scope', text: 'Memory and receipts appear only after this session runs' },
    ],
    cta: "Open Marco's prompt",
  },
  anna: {
    eyebrow: 'Workshop profile · Anna',
    title: 'Gifting and home preferences seed this session.',
    items: [
      { tool: 'profile.seed', text: 'Gift, candle, ceramic, and home tags receive higher weights' },
      { tool: 'scenario.prompt', text: 'The core prompt asks for a new-homeowner milestone gift' },
      { tool: 'session.scope', text: 'Memory and receipts appear only after this session runs' },
    ],
    cta: "Open Anna's prompt",
  },
  theo: {
    eyebrow: 'Workshop profile · Theo',
    title: 'Slow-craft and home preferences seed this session.',
    items: [
      { tool: 'profile.seed', text: 'Ceramic, slow, artisanal, and home tags receive higher weights' },
      { tool: 'scenario.prompt', text: 'The core action files a damaged Wabi-Sabi Bowl return' },
      { tool: 'session.scope', text: 'Memory and the return receipt appear only after this session runs' },
    ],
    cta: "Open Theo's return flow",
  },
  fresh: {
    eyebrow: 'No workshop profile selected',
    title: 'Choose a profile to start a scoped workshop session.',
    items: [
      { tool: 'profile.seed', text: 'Each profile declares visible tag weights and a core scenario' },
      { tool: 'session.scope', text: 'Messages and action receipts are recorded only after you run them' },
      { tool: 'tool.transparency', text: 'Recommendation cards expose their ranking reason' },
    ],
    cta: 'Try a query',
  },
}

export function memoryHandoffForPersona(
  personaId: string | null | undefined,
): MemoryHandoffContent {
  if (!personaId) return PERSONA_MEMORY_HANDOFF.fresh
  return PERSONA_MEMORY_HANDOFF[personaId] ?? PERSONA_MEMORY_HANDOFF.fresh
}
