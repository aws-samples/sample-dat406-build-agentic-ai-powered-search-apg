/**
 * PellierHero - the storefront's editorial first viewport.
 *
 * Three zones rather than one framed photograph:
 *
 *   left    the editorial statement, the lede, and the primary action
 *   centre  the product photograph, masked into the page rather than boxed
 *   right   PersonaConcierge, the only thing here a shopper acts on first
 *
 * The interaction layer is unchanged from the framed version: choose a
 * workshop profile, then submit a query once a profile is active. A query
 * still needs a profile because the floor is ranked per persona, so the
 * search affordance appears with the profile rather than before it.
 */
import { useCallback, useState } from 'react'
import { ArrowRight, Mic, MicOff, Send, Sparkles } from 'lucide-react'
import { usePersona } from '../contexts/PersonaContext'
import { useUI } from '../contexts/UIContext'
import {
  heroPillLabel,
  heroPillsForPersona,
  PERSONA_TURN_TRACES,
} from '../data/personaCurations'
import { useVoiceSearch } from '../hooks/useVoiceSearch'
import { splitHeadlineAtAccent } from '../utils/headlineAccent'
import { HERO_STATEMENT } from '../copy'
import PersonaConcierge from './PersonaConcierge'
import ResponsiveImage from './ResponsiveImage'

/**
 * Per-persona hero imagery and lede. Each persona keeps its own photograph
 * so the selected profile visibly changes the room, which is the storefront's
 * existing behaviour.
 */
const PERSONA_HEROES: Record<
  string,
  { image: string; alt: string; subheadline: string }
> = {
  fresh: {
    image: '/products/landing-hero-weekender.png',
    alt: 'Leather weekender on a travertine bench beside linen and an olive branch',
    subheadline:
      'Choose a workshop profile, then explore a floor shaped by explicit catalog signals.',
  },
  marco: {
    image: '/products/hero-marco.png',
    alt: 'Leather weekender and folded linen shirts in warm daylight',
    subheadline:
      "Marco's seeded profile favors natural fibers, travel-ready layers, and enduring pieces.",
  },
  anna: {
    image: '/products/hero-anna.png',
    alt: 'Wrapped gift, beeswax candles, and ceramic ring dish',
    subheadline:
      "Anna's seeded profile favors considered gifts, home objects, and clear budget constraints.",
  },
  theo: {
    image: '/products/hero-theo.png',
    alt: 'Stoneware pour-over set on a sunlit wooden table',
    subheadline:
      "Theo's seeded profile favors slow craft, ceramics, and durable post-purchase care.",
  },
}

/**
 * Tools that make a turn a persona's *signature* turn.
 *
 * Most turns exercise retrieval (`search_products`, `get_related_products`), which every
 * persona shares. These tools are the ones that define a particular shopper's
 * journey and that the workshop is built around, so a persona owning one must
 * show it on sign-on:
 *
 *   initiate_return  the Cedar-gated governed write (Theo)
 *   check_inventory     the system-of-record inventory read, and the Lab 1
 *                   exercise (Marco, `MARCO_BUILDER_SESSION_QUERY`)
 *   restock_inventory   the operator write
 *
 * Ordered by precedence, so a persona holding more than one leads with the
 * most consequential. `escalate_to_human` is deliberately absent: it is
 * Turn 5 for every persona, so treating it as a signature would replace a
 * shopping pill with a human handoff on every profile.
 */
const SIGNATURE_TOOLS = ['initiate_return', 'check_inventory', 'restock_inventory']

/**
 * Which canonical turns appear as hero suggestions on sign-on.
 *
 * The first three by default. When a persona's signature turn sits outside
 * that window it leads instead, because the pill row scrolls inside a narrow
 * column and any slot but the first can be scrolled out of sight. The
 * original turn index travels with the query so each pill still resolves its
 * own short label.
 */
function suggestionTurns(
  personaId: string,
): Array<{ query: string; index: number }> {
  const queries = heroPillsForPersona(personaId)
  const traces = PERSONA_TURN_TRACES[personaId] ?? []

  let signatureIndex = -1
  for (const tool of SIGNATURE_TOOLS) {
    signatureIndex = traces.findIndex((trace) => trace?.tools?.includes(tool))
    if (signatureIndex >= 0) break
  }

  const indexes = signatureIndex > 2 ? [signatureIndex, 0, 1] : [0, 1, 2]
  return indexes
    .filter((index) => index < queries.length)
    .map((index) => ({ query: queries[index], index }))
}

type StatementId = 'fresh' | 'marco' | 'anna' | 'theo'

function statementFor(personaId: string) {
  const key = (personaId in HERO_STATEMENT ? personaId : 'fresh') as StatementId
  return HERO_STATEMENT[key]
}

interface PellierHeroProps {
  /**
   * Browse the catalog. Defaults to scrolling the `#shop` band, which is
   * what PellierPage does for every other catalog entry point.
   */
  onBrowseCollection?: () => void
}

export default function PellierHero({
  onBrowseCollection,
}: PellierHeroProps) {
  const { openDrawerWithQuery } = useUI()
  const { persona } = usePersona()
  const [searchValue, setSearchValue] = useState('')

  const personaId = persona?.id ?? 'fresh'
  const hero = PERSONA_HEROES[personaId] ?? PERSONA_HEROES.fresh
  const statement = statementFor(personaId)
  const headline = splitHeadlineAtAccent(statement.HEADLINE, statement.ACCENT)
  const suggestions = suggestionTurns(personaId)

  const browseCollection = useCallback(() => {
    if (onBrowseCollection) {
      onBrowseCollection()
      return
    }
    document.getElementById('shop')?.scrollIntoView({ behavior: 'smooth' })
  }, [onBrowseCollection])

  const submitQuery = useCallback(
    (query: string) => {
      if (!persona) return
      const trimmed = query.trim()
      if (!trimmed) return
      openDrawerWithQuery(trimmed)
      setSearchValue('')
    },
    [openDrawerWithQuery, persona],
  )

  const { isListening, startListening, stopListening } = useVoiceSearch({
    onInterimTranscript: setSearchValue,
    onFinalTranscript: submitQuery,
  })

  const handleSubmit = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault()
      submitQuery(searchValue)
    },
    [searchValue, submitQuery],
  )

  return (
    <section
      data-testid="pellier-hero"
      aria-label="Pellier collection"
      className="pellier-hero"
    >
      <div className="pellier-hero-inner">
        <div className="pellier-hero-copy">
          <span className="pellier-eyebrow">Pellier</span>

          <h1
            data-testid="pellier-hero-headline"
            className="pellier-statement"
          >
            {headline.before}
            {headline.accent ? <em>{headline.accent}</em> : null}
            {headline.after}
          </h1>

          <p
            data-testid="pellier-hero-subheadline"
            className="pellier-hero-lede"
          >
            {hero.subheadline}
          </p>

          {persona ? (
            /* Width is the copy column, not a fixed max: a wider block spilled
               the suggestion pills over the photograph and clipped one
               mid-word. */
            <div className="w-full">
              <form
                role="search"
                onSubmit={handleSubmit}
                className="relative w-full"
              >
                <Sparkles
                  aria-hidden="true"
                  className="absolute left-5 top-1/2 z-10 -translate-y-1/2 text-accent"
                  size={19}
                />
                <input
                  type="text"
                  data-testid="pellier-hero-search"
                  value={searchValue}
                  onChange={(event) => setSearchValue(event.target.value)}
                  placeholder={
                    isListening ? 'Listening...' : 'Ask Pellier anything...'
                  }
                  aria-label="Ask Pellier anything"
                  className="
                    h-[56px] w-full rounded-full border border-[rgba(24,26,31,0.16)]
                    bg-[rgba(255,255,255,0.94)] pl-[52px] pr-[58px]
                    font-sans text-[15px] text-espresso shadow-warm-sm
                    outline-none transition
                    placeholder:text-[rgba(24,26,31,0.48)]
                    focus:border-[rgba(24,26,31,0.34)] focus:ring-2
                    focus:ring-[rgba(154,52,18,0.18)]
                  "
                />
                <button
                  type={searchValue.trim() ? 'submit' : 'button'}
                  onClick={
                    searchValue.trim()
                      ? undefined
                      : isListening
                        ? stopListening
                        : startListening
                  }
                  aria-label={
                    searchValue.trim()
                      ? 'Send'
                      : isListening
                        ? 'Stop listening'
                        : 'Voice search'
                  }
                  className="
                    absolute right-[5px] top-1/2 flex h-[46px] w-[46px]
                    -translate-y-1/2 items-center justify-center rounded-full
                    bg-espresso text-cream transition hover:bg-accent
                    focus-visible:outline-none focus-visible:ring-2
                    focus-visible:ring-espresso focus-visible:ring-offset-2
                  "
                >
                  {searchValue.trim() ? (
                    <Send size={18} />
                  ) : isListening ? (
                    <MicOff size={18} />
                  ) : (
                    <Mic size={18} />
                  )}
                </button>
              </form>

              <div
                data-testid="pellier-hero-pills"
                className="pellier-hero-pills mt-3 flex w-full gap-2 overflow-x-auto pb-1"
                aria-label="Suggested queries"
              >
                {suggestions.map(({ query, index }) => (
                  <button
                    key={query}
                    type="button"
                    onClick={() => submitQuery(query)}
                    className="
                      min-h-10 shrink-0 rounded-full border
                      border-[rgba(24,26,31,0.16)] bg-[rgba(255,255,255,0.84)]
                      px-4 py-2 text-left font-sans text-[12px] leading-4
                      text-espresso transition hover:border-accent hover:bg-cream
                      focus-visible:outline-none focus-visible:ring-2
                      focus-visible:ring-espresso
                    "
                  >
                    {heroPillLabel(persona.id, index, query)}
                  </button>
                ))}
              </div>

              {/* Browsing stays available with a profile active, but as the
                  quiet action: asking is the primary one here. */}
              <button
                type="button"
                className="pellier-action-quiet mt-1"
                onClick={browseCollection}
              >
                {HERO_STATEMENT.CTA}
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="pellier-action"
              data-testid="pellier-hero-cta"
              onClick={browseCollection}
            >
              {HERO_STATEMENT.CTA}
            </button>
          )}
        </div>

        <div className="pellier-hero-media">
          <ResponsiveImage
            src={hero.image}
            alt={hero.alt}
            widths={[480, 960, 1600]}
            sizes="(min-width: 1024px) 52vw, 100vw"
            loading="eager"
            pictureClassName="block h-full w-full"
          />
        </div>

        <PersonaConcierge onContinueAsGuest={browseCollection} />
      </div>
    </section>
  )
}
