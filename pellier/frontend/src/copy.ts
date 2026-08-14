// Pellier frontend user-facing copy.
//
// This module is the single source of truth for every customer-facing string
// authored by the storefront UI. Announcement bar, nav, hero intents,
// reasoning chips, banners, modals, footer, and error strings all live here.
//
// All strings in this module must satisfy the storefront copy rules:
//   - no emoji
//   - no em dashes (use regular hyphens)
//   - none of the forbidden words listed in storefront.md
//
// The companion scanner lives at src/__tests__/copy.test.ts (or .mjs).

export interface LiveFloorFinding {
  /** Uppercase sans label that leads the copy. */
  verb?: string;
  /** Body text. */
  text: string;
  /** Mono trace stamp on the right. */
  trace?: string;
}

export const LIVE_FLOOR_FINDINGS: LiveFloorFinding[] = [
  {
    verb: "Catalog edit",
    text: "Alba Linen Lounge Set, Olive Branch Vessel, and Santal & Fig Candle anchor the seeded Resort Edit.",
  },
  {
    verb: "Catalog focus",
    text: "Italian Linen Camp Shirt anchors the workshop catalog's linen and travel edit.",
  },
  {
    verb: "Travel edit",
    text: "Packable linen, leather carry, and sun-ready accessories for long weekends and warm-weather escapes.",
  },
  {
    verb: "Gift edit",
    text: "Gift, candle, ceramic, and home tags shape the workshop's gifting shortlist.",
  },
  {
    verb: "Concierge",
    text: "Ask for a packing list, a gift shortlist, or a home ritual and Pellier will build the edit with you.",
  },
  {
    verb: "Workshop",
    text: "Search the seeded catalog, inspect the evidence, and complete the return scenario without a live transaction.",
  },
];

export const PAGE_TITLE = "Pellier - Resort Edit No. 06";

// Top nav (Requirement 1.2.1)
export const NAV = {
  HOME: "Home",
  SHOP: "Shop",
  STORYBOARD: "Storyboard",
  STORIES: "Stories",
  DISCOVER: "Discover",
  ABOUT: "About",
  ACCOUNT: "Account",
  ASK_PELLIER: "Ask Pellier",
  WORDMARK: "Pellier",
} as const;

// Account button labels (Requirement 1.2.2, 1.2.3)
export const ACCOUNT_LABEL_SIGNED_OUT = "Account";
export const accountLabelSignedIn = (givenName: string): string =>
  `Hi, ${givenName}`;

export const SEARCH_PILL_PLACEHOLDER =
  "Tell Pellier what you're looking for...";

// Hero headline block that sits above the rotating stage.
export const HERO_HEADLINE = {
  EYEBROW: "Resort Edit \u00b7 No. 06",
  TITLE_TOP: "Search,", // copy-allow: search-as-verb
  TITLE_BOTTOM: "re:Engineered.",
  SUBHEADLINE: "Tell Pellier what you're looking for. Watch the pieces find you.",
} as const;

export const BOUTIQUE_HERO_SIGNED_OUT = {
  LINE_1: "Choose a shopper profile to begin.",
  LINE_2: "Pellier will tailor the floor around that visit.",
} as const;

// Product grid section header that reveals on scroll (parallax).
export const PRODUCT_GRID_HEADER = {
  EYEBROW: "Picked for your summer",
  TITLE: "Things worth discovering",
  SORT_LABEL: "Sort: Most loved",
} as const;

// Sign-in strip (Requirement 1.4.1)
export const SIGN_IN_STRIP = {
  EYEBROW: "PERSONALIZED VISIONS",
  HEADLINE: "Sign in and watch Pellier tailor the boutique to you.",
  CTA: "Sign in for personalized visions",
  DISMISS: "Not now",
} as const;

// Curated banner (Requirement 1.4.3)
export const curatedHeadline = (
  givenName: string,
  prefs: [string, string, string],
): string =>
  `Tailored to your preferences, ${givenName}. ${prefs[0]} \u00b7 ${prefs[1]} \u00b7 ${prefs[2]}`;

export const CURATED_BANNER = {
  LABEL: "CURATED FOR YOU",
  ADJUST_LINK: "Adjust preferences",
  headline: curatedHeadline,
} as const;

// Category chips (Requirement 1.5.3)
export const CATEGORY_CHIPS = [
  "All",
  "Linen",
  "Dresses",
  "Accessories",
  "Outerwear",
  "Footwear",
  "Home",
] as const;

// Refinement panel (Requirement 1.8.1)
export const REFINEMENT = {
  // Single-letter mark inside the brand circle. "P" matches the
  // header wordmark - the refinement chip and the header speak with
  // the same brand voice.
  B_MARK_PREFIX: "P",
  PROMPT: "Pellier here, want me to narrow this down?",
  CHIPS: [
    "Under $100",
    "Ships by Friday",
    "Gift-wrappable",
    "From smaller makers",
  ],
} as const;

// Reasoning chip copy (Requirement 1.7). The pricing style exposes its urgent
// clause separately so the UI can render it in terracotta.
export const reasoningPicked = (reason: string): string =>
  `Picked because ${reason}`;

export const reasoningMatched = (
  attr1: string,
  attr2: string,
  attr3: string,
): string => `Matched on: ${attr1} \u00b7 ${attr2} \u00b7 ${attr3}`;

export interface PricingReasoning {
  lead: string;
  urgent: string;
}
export const reasoningPricing = (
  _amountBelow: number,
  _unitsLeft: number,
): PricingReasoning => ({
  lead: "Catalog price shown above.",
  urgent: "Ask Pellier to compare this edit.",
});

export const reasoningContext = (text: string): string => text;

export const REASONING = {
  picked: reasoningPicked,
  matched: reasoningMatched,
  pricing: reasoningPricing,
  context: reasoningContext,
  DEFAULT_CONTEXT: "Gift-ready: signature packaging available",
} as const;

// Storyboard teaser cards (Requirement 1.9.4)
//
// Each card composes to the eyebrow line
//   `{badge} \u00b7 {volume} \u00b7 {theme}` above the italic Fraunces title,
// followed by a 2-3 sentence excerpt and the terracotta `link`. See
// StoryboardTeaser.tsx for the rendering contract.
export interface StoryboardTeaser {
  badge: string;
  volume: string;
  theme: string;
  title: string;
  excerpt: string;
  link: string;
  imageUrl: string;
  imageAlt: string;
}
export const STORYBOARD_TEASERS: StoryboardTeaser[] = [
  {
    badge: "WORKSHOP EDIT",
    volume: "Vol. 12",
    theme: "Catalog",
    title: "The seeded summer catalog.",
    excerpt:
      "Linen, ceramic, travel, and gifting products create one controlled corpus for comparing retrieval and agent behavior.",
    link: "Open the workshop story \u203a",
    imageUrl:
      "https://images.unsplash.com/photo-1693928126497-d9bda6903c03?w=1600&q=85",
    imageAlt: "Golden afternoon light falling across a linen-draped table",
  },
  {
    badge: "PROFILE DESIGN",
    volume: "Vol. 11",
    theme: "Ranking",
    title: "How a profile changes the floor.",
    excerpt:
      "Marco, Anna, and Theo start from explicit tag weights and seeded order histories that participants can inspect.",
    link: "Open the workshop story \u203a",
    imageUrl:
      "https://images.unsplash.com/photo-1607556671927-78a6605e290b?w=1600&q=85",
    imageAlt: "A pair of hands shaping clay on a potter's wheel",
  },
  {
    badge: "PROOF PATH",
    volume: "Vol. 10",
    theme: "Evidence",
    title: "How an answer earns its proof.",
    excerpt:
      "Follow a request through Aurora retrieval, specialist tools, working memory, and a session-scoped action receipt.",
    link: "Open the workshop story \u203a",
    imageUrl:
      "https://images.unsplash.com/photo-1761896902115-49793a359daf?w=1600&q=85",
    imageAlt: "An open edit room with fabric swatches laid out on a warm wood table",
  },
];

// Minimal Storyboard and Discover routes (Requirement 1.13)
export const STORYBOARD_PAGE_COMING_SOON =
  "Coming soon - the full editorial hub arrives with the next Edit.";
export const DISCOVER_PAGE_SIGNED_OUT =
  "Discover is tailored to you. Sign in and watch the boutique tune itself.";
export const DISCOVER_PAGE_COMING_SOON = STORYBOARD_PAGE_COMING_SOON;

// Footer \u2014 three live columns + a brand + a bottom strip.
//
// Earlier iterations carried four product/editorial columns with a
// dozen links, a newsletter form, and a bottom strip. Every one of
// those links was a stub. Replaced with three columns pointing at
// routes that actually exist: Explore (the three real storefront
// routes), Storyboard (editorial entry), Pellier Labs (the workshop).
// Fewer promises, every promise kept.
export const FOOTER = {
  BRAND: {
    TAGLINE: "Curated goods for travel, gifting, and home rituals",
  },
  EXPLORE: {
    HEADING: "Explore",
    ITEMS: [
      { label: "Shop", href: "/#shop" },
      { label: "Stories", href: "/storyboard" },
      { label: "About", href: "/about" },
    ],
  },
  STORYBOARD: {
    HEADING: "Stories",
    COPY: "Field notes from a slower kind of shopping \u2014 one short essay at a time.",
    CTA_LABEL: "Read the stories",
    CTA_HREF: "/storyboard",
  },
  AGENT_TRACE: {
    HEADING: "Pellier Labs",
    COPY: "Inspect the routing, retrieval, tools, memory, and evidence behind each workshop turn.",
    CTA_LABEL: "Open Pellier Labs",
    CTA_HREF: "/pellier-labs",
  },
  BOTTOM_STRIP: {
    COPYRIGHT: "\u00a9 Pellier",
    /** Centered service line \u2014 retail boilerplate moved out of the
     * hero capabilities strip so the strip can stay focused on agent
     * claims. Lives in the footer where shipping/returns info belongs. */
    SERVICE: "Workshop demo | Seeded catalog | No live checkout",
    /** Right-hand credit in the footer strip (replaces workshop banner). */
    ATTRIBUTION: "\u00a9 Shayon Sanyal",
  },
} as const;

// Command pill (Requirement 1.11.1)
export const COMMAND_PILL = {
  LABEL: "Ask Pellier",
  KEY_CAP_MAC: "\u2318K",
  KEY_CAP_WIN: "Ctrl K",
} as const;

// Auth modal (storefront.md "Auth modal" section, Requirement 2.6.6)
export const AUTH_MODAL = {
  HEADER: "Welcome to Pellier",
  SUBHEADER: "Sign in for a boutique built for you",
  EYEBROW: "PERSONALIZED VISIONS",
  ITALIC_HEADLINE: "Let the boutique find you.",
  BUTTON_GOOGLE: "Continue with Google",
  BUTTON_APPLE: "Continue with Apple",
  BUTTON_EMAIL: "Continue with email",
  DISCLAIMER: "This workshop redirects to the configured sign-in provider.",
  FOOTER: "Authentication handled by Amazon Cognito",
  VERSION: "v2.4",
} as const;

// Preferences onboarding modal (storefront.md "Preferences onboarding modal")
export interface PreferenceChip {
  label: string;
  descriptor?: string;
  swatch?: string;
}
export interface PreferenceGroup {
  heading: string;
  kind: "card" | "pill";
  chips: PreferenceChip[];
}
export const PREFERENCES_MODAL = {
  HEADER: "A quick tune-up",
  SUBHEADER: "Takes about 20 seconds. You can change these anytime.",
  ITALIC_HEADLINE: "What moves you?",
  SUBHEADLINE: "Pick what resonates. Pellier will take it from here.",
  GROUPS: [
    {
      heading: "Your overall vibe",
      kind: "card",
      chips: [
        { label: "Minimal", descriptor: "Quiet \u00b7 Considered" },
        { label: "Bold", descriptor: "Statement \u00b7 Saturated" },
        { label: "Serene", descriptor: "Soft \u00b7 Calming" },
        { label: "Adventurous", descriptor: "Outdoor \u00b7 Durable" },
        { label: "Creative", descriptor: "Layered \u00b7 Textured" },
        { label: "Classic", descriptor: "Timeless \u00b7 Refined" },
      ],
    },
    {
      heading: "Favorite colors",
      kind: "pill",
      chips: [
        { label: "Warm tones", swatch: "terracotta-to-amber" },
        { label: "Neutrals", swatch: "sand-to-ink-soft" },
        { label: "Earth", swatch: "ink-soft-to-dusk" },
        { label: "Soft pastels", swatch: "cream-warm-to-cream" },
        { label: "Deep and moody", swatch: "ink-to-near-black" },
      ],
    },
    {
      heading: "Where you wear it",
      kind: "pill",
      chips: [
        { label: "Everyday" },
        { label: "Travel" },
        { label: "Evenings out" },
        { label: "Outdoor" },
        { label: "Slow mornings" },
        { label: "Work" },
      ],
    },
    {
      heading: "Categories you love",
      kind: "pill",
      chips: [
        { label: "Linen" },
        { label: "Footwear" },
        { label: "Outerwear" },
        { label: "Accessories" },
        { label: "Home" },
        { label: "Dresses" },
      ],
    },
  ] as PreferenceGroup[],
  SKIP: "Skip for now",
  SUBMIT: "Save and see my boutique",
  FOOTER: "Preferences are scoped to your signed-in profile",
} as const;

// Error copy (design.md "Error Handling" table). Machine codes are colocated
// for grep-ability; the scanner still treats them as regular string values.
export const ERRORS = {
  AGENT_TIMEOUT: "Taking a moment. Try again?",
  DB_UNAVAILABLE: "I can't reach the catalog right now.",
  AUTH_INTERRUPTED: "Something interrupted the sign-in. Try again.",
  EMPTY_SEARCH_RESULT: "Nothing yet. Try a different wording.",
  SILENT_REFRESH_SAY: "",
  SEARCH_FALLBACK_LOADING: "Pellier is thinking...",
} as const;

export const ERROR_CODES = {
  AGENT_TIMEOUT: "agent_timeout",
  AUTH_FAILED: "auth_failed",
  INVALID_STATE: "invalid_state",
  INVALID_PREFERENCES: "invalid_preferences",
  UNAVAILABLE: "unavailable",
  DB_UNAVAILABLE: "db_unavailable",
} as const;
