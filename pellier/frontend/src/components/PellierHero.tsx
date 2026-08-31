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
import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, Send, Sparkles } from 'lucide-react'
import { usePersona } from '../contexts/PersonaContext'
import { useUI } from '../contexts/UIContext'
import { splitHeadlineAtAccent } from '../utils/headlineAccent'
import { HERO_STATEMENT } from '../copy'
import PersonaConcierge from './PersonaConcierge'
import ResponsiveImage from './ResponsiveImage'

interface LiveHeroProfile {
  id: string
  hero_image: string
  hero_alt: string
  hero_subheadline: string
}

interface LiveScenario {
  id: number
  ordinal: number
  prompt: string
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
  const [heroProfile, setHeroProfile] = useState<LiveHeroProfile | null>(null)
  const [suggestions, setSuggestions] = useState<LiveScenario[]>([])

  const personaId = persona?.id ?? 'fresh'
  const statement = statementFor(personaId)
  const headline = splitHeadlineAtAccent(statement.HEADLINE, statement.ACCENT)

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    const targetPersonaId = persona?.id ?? 'fresh'
    setHeroProfile(null)

    void fetch('/api/observatory/personas', { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error(`Live persona request failed: ${response.status}`)
        return response.json() as Promise<LiveHeroProfile[]>
      })
      .then(profiles => {
        if (!active) return
        setHeroProfile(
          profiles.find(profile => profile.id === targetPersonaId) ?? null,
        )
      })
      .catch(() => {
        if (active) setHeroProfile(null)
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [persona?.id])

  useEffect(() => {
    if (!persona) {
      setSuggestions([])
      return
    }
    let active = true
    const controller = new AbortController()
    setSuggestions([])
    void fetch(`/api/observatory/scenarios?persona=${encodeURIComponent(persona.id)}`, {
      signal: controller.signal,
    })
      .then(async response => {
        if (!response.ok) throw new Error(`Live scenario request failed: ${response.status}`)
        return response.json() as Promise<{ scenarios?: LiveScenario[] }>
      })
      .then(payload => {
        if (active) setSuggestions((payload.scenarios ?? []).slice(0, 3))
      })
      .catch(() => {
        if (active) setSuggestions([])
      })
    return () => {
      active = false
      controller.abort()
    }
  }, [persona])

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
            {heroProfile?.hero_subheadline
              ?? 'Loading the current Aurora profile…'}
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
                    'Ask Pellier anything...'
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
                {searchValue.trim() ? (
                  <button
                    type="submit"
                    aria-label="Send"
                    className="
                      absolute right-[5px] top-1/2 flex h-[46px] w-[46px]
                      -translate-y-1/2 items-center justify-center rounded-full
                      bg-espresso text-cream transition hover:bg-accent
                      focus-visible:outline-none focus-visible:ring-2
                      focus-visible:ring-espresso focus-visible:ring-offset-2
                    "
                  >
                    <Send size={18} />
                  </button>
                ) : null}
              </form>

              <div
                data-testid="pellier-hero-pills"
                className="pellier-hero-pills mt-3 flex w-full gap-2 overflow-x-auto pb-1"
                aria-label="Suggested queries"
              >
                {suggestions.map((scenario) => (
                  <button
                    key={scenario.id}
                    type="button"
                    onClick={() => submitQuery(scenario.prompt)}
                    className="
                      min-h-10 shrink-0 rounded-full border
                      border-[rgba(24,26,31,0.16)] bg-[rgba(255,255,255,0.84)]
                      px-4 py-2 text-left font-sans text-[12px] leading-4
                      text-espresso transition hover:border-accent hover:bg-cream
                      focus-visible:outline-none focus-visible:ring-2
                      focus-visible:ring-espresso
                    "
                  >
                    {scenario.prompt}
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
          {heroProfile?.hero_image && heroProfile.hero_alt ? (
            <ResponsiveImage
              src={heroProfile.hero_image}
              alt={heroProfile.hero_alt}
              widths={[480, 960, 1600]}
              sizes="(min-width: 1024px) 52vw, 100vw"
              loading="eager"
              pictureClassName="block h-full w-full"
            />
          ) : (
            <div
              aria-label="Loading live profile image"
              className="h-full w-full bg-[linear-gradient(135deg,#ebe4d8,#f6f2eb)]"
              role="status"
            />
          )}
        </div>

        <PersonaConcierge onContinueAsGuest={browseCollection} />
      </div>
    </section>
  )
}
