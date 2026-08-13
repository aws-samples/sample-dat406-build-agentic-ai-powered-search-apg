/**
 * BoutiqueHero - the storefront's compact first-viewport entry point.
 *
 * Pellier's local, persona-specific photography carries the scene. The
 * interaction layer stays deliberately small: choose a workshop profile, or
 * submit a query once a profile is active. The catalog edit follows directly
 * below this component.
 */
import { useCallback, useState, type CSSProperties } from 'react'
import { Mic, MicOff, Send, Sparkles } from 'lucide-react'
import { usePersona } from '../contexts/PersonaContext'
import { useUI } from '../contexts/UIContext'
import {
  becauseChipsForPersona,
  heroPillLabel,
  heroPillsForPersona,
} from '../data/personaCurations'
import { LOCAL_PERSONAS } from '../data/personas'
import { getPersonaPhoto } from '../data/personaPhotos'
import { useVoiceSearch } from '../hooks/useVoiceSearch'
import { PresencePill } from '../shared'
import { asset } from '../utils/assetPath'

const PERSONA_HEROES: Record<
  string,
  { image: string; alt: string; subheadline: string }
> = {
  fresh: {
    image: asset('/products/hero-fresh-2.png'),
    alt: 'Pellier leather tote, linen, and olive branches in warm daylight',
    subheadline:
      'Choose a workshop profile, then explore a floor shaped by explicit catalog signals.',
  },
  marco: {
    image: asset('/products/hero-marco.png'),
    alt: 'Leather weekender and folded linen shirts in warm daylight',
    subheadline:
      "Marco's seeded profile favors natural fibers, travel-ready layers, and enduring pieces.",
  },
  anna: {
    image: asset('/products/hero-anna.png'),
    alt: 'Wrapped gift, beeswax candles, and ceramic ring dish',
    subheadline:
      "Anna's seeded profile favors considered gifts, home objects, and clear budget constraints.",
  },
  theo: {
    image: asset('/products/hero-theo.png'),
    alt: 'Stoneware pour-over set on a sunlit wooden table',
    subheadline:
      "Theo's seeded profile favors slow craft, ceramics, and durable post-purchase care.",
  },
}

const PROFILE_FOCUS: Record<string, string> = {
  marco: 'Travel edit',
  anna: 'Gift edit',
  theo: 'Home rituals',
}

export default function BoutiqueHero() {
  const { openDrawerWithQuery } = useUI()
  const { persona, switchPersona, switching } = usePersona()
  const [searchValue, setSearchValue] = useState('')

  const personaId = persona?.id ?? 'fresh'
  const hero = PERSONA_HEROES[personaId] ?? PERSONA_HEROES.fresh
  const suggestions = heroPillsForPersona(persona?.id).slice(0, 3)
  const profileSignal = becauseChipsForPersona(persona?.id)[0]?.text
  const personaAccent = persona?.avatar_color ?? 'var(--accent)'

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
      data-testid="boutique-hero"
      aria-label="Pellier resort edit"
      className="px-3 pt-3 md:px-container-x md:pt-5"
      style={{ '--boutique-accent': personaAccent } as CSSProperties}
    >
      <div
        className="
          relative mx-auto min-h-[620px] max-w-[1440px] overflow-hidden
          rounded-[8px] border border-[rgba(31,20,16,0.12)]
          md:min-h-[610px] lg:min-h-[630px]
        "
      >
        <img
          src={hero.image}
          alt={hero.alt}
          className="
            absolute inset-0 h-full w-full object-cover object-[30%_center]
            transition-opacity duration-300 md:object-center
          "
        />
        <div
          aria-hidden="true"
          className="
            absolute inset-0
            bg-[linear-gradient(0deg,rgba(248,241,231,0.98)_0%,rgba(248,241,231,0.88)_46%,rgba(248,241,231,0.08)_78%)]
            md:bg-[linear-gradient(90deg,rgba(248,241,231,0.02)_24%,rgba(248,241,231,0.50)_50%,rgba(248,241,231,0.98)_76%)]
          "
        />

        <div className="relative flex min-h-[620px] items-end md:min-h-[610px] md:items-center md:justify-end lg:min-h-[630px]">
          <div className="w-full px-5 pb-7 pt-72 md:w-[55%] md:max-w-[700px] md:px-10 md:py-10 lg:px-14">
            <p
              data-testid="boutique-hero-eyebrow"
              className="mb-3 flex items-center gap-3 font-sans text-[11px] font-semibold uppercase text-espresso"
              style={{ letterSpacing: '0.18em' }}
            >
              <span className="h-px w-7 bg-accent" aria-hidden="true" />
              Pellier edit No. 06
            </p>

            <h1
              data-testid="boutique-hero-headline"
              className="font-display text-[44px] font-normal leading-[0.98] text-espresso md:text-[62px]"
              style={{ letterSpacing: 0 }}
            >
              Pellier
              <span className="block italic text-accent-ink">Resort Edit.</span>
            </h1>

            <p
              data-testid="boutique-hero-subheadline"
              className="mt-4 max-w-[540px] font-sans text-[15px] leading-6 text-ink-soft md:text-[16px]"
            >
              {hero.subheadline}
            </p>

            {persona ? (
              <div className="mt-6">
                <form
                  role="search"
                  onSubmit={handleSubmit}
                  className="relative max-w-[620px]"
                >
                  <Sparkles
                    aria-hidden="true"
                    className="absolute left-5 top-1/2 z-10 -translate-y-1/2 text-accent"
                    size={19}
                  />
                  <input
                    type="text"
                    data-testid="boutique-hero-search"
                    value={searchValue}
                    onChange={(event) => setSearchValue(event.target.value)}
                    placeholder={
                      isListening ? 'Listening...' : 'Ask Pellier anything...'
                    }
                    aria-label="Ask Pellier anything"
                    className="
                      h-[58px] w-full rounded-full border border-[rgba(31,20,16,0.16)]
                      bg-[rgba(255,252,247,0.96)] pl-[52px] pr-[58px]
                      font-sans text-[15px] text-espresso shadow-warm-sm
                      outline-none transition
                      placeholder:text-[rgba(31,20,16,0.44)]
                      focus:border-[rgba(31,20,16,0.34)] focus:ring-2
                      focus:ring-[rgba(31,20,16,0.08)]
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
                      absolute right-[5px] top-1/2 flex h-12 w-12
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
                  data-testid="boutique-hero-pills"
                  className="mt-3 flex max-w-[620px] gap-2 overflow-x-auto pb-1"
                  aria-label="Suggested queries"
                >
                  {suggestions.map((query, index) => (
                    <button
                      key={query}
                      type="button"
                      onClick={() => submitQuery(query)}
                      className="
                        min-h-10 shrink-0 rounded-full border
                        border-[rgba(31,20,16,0.16)] bg-[rgba(255,252,247,0.86)]
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

                {profileSignal ? (
                  <p className="mt-3 font-sans text-[12px] text-ink-soft">
                    <span className="font-semibold text-espresso">
                      Profile seed:
                    </span>{' '}
                    {profileSignal}
                  </p>
                ) : null}
              </div>
            ) : (
              <div id="profile-selector" className="mt-6 max-w-[620px]">
                <p className="mb-3 font-sans text-[12px] font-semibold uppercase text-espresso">
                  Choose a workshop profile
                </p>
                <div className="grid grid-cols-3 gap-2.5">
                  {LOCAL_PERSONAS.map((profile) => (
                    <button
                      key={profile.id}
                      type="button"
                      disabled={switching}
                      onClick={() => void switchPersona(profile.id)}
                      className="
                        min-w-0 rounded-[8px] border border-[rgba(31,20,16,0.16)]
                        bg-[rgba(255,252,247,0.92)] p-3 text-left
                        transition hover:-translate-y-px hover:border-[rgba(31,20,16,0.34)]
                        hover:bg-cream focus-visible:outline-none focus-visible:ring-2
                        focus-visible:ring-espresso disabled:cursor-wait disabled:opacity-60
                      "
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className="h-8 w-8 shrink-0 overflow-hidden rounded-full"
                          style={{ background: profile.avatar_color }}
                        >
                          <img
                            src={getPersonaPhoto(profile.id)}
                            alt=""
                            className="h-full w-full object-cover"
                          />
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate font-display text-[16px] font-semibold text-espresso">
                            {profile.display_name}
                          </span>
                          <span className="block truncate font-sans text-[10px] uppercase text-ink-soft">
                            {PROFILE_FOCUS[profile.id]}
                          </span>
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div
        data-testid="boutique-hero-trust"
        className="
          mx-auto flex max-w-[1440px] flex-col items-start gap-2
          border-b border-sand px-2 py-3 md:flex-row md:items-center
          md:justify-between md:px-0
        "
      >
        <PresencePill surface="boutique" personaId={persona?.id} />
        <p className="font-sans text-[11px] leading-5 text-ink-soft md:text-right">
          Seeded catalog and profile weights shape the floor. Live memory and
          action receipts appear only after a workshop turn runs.
        </p>
      </div>
    </section>
  )
}
