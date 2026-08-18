/**
 * PellierHero - the storefront's compact first-viewport entry point.
 *
 * Pellier's local, persona-specific photography carries the scene. The
 * interaction layer stays deliberately small: choose a workshop profile, or
 * submit a query once a profile is active. The catalog edit follows directly
 * below this component.
 */
import { useCallback, useState } from 'react'
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
import ResponsiveImage from './ResponsiveImage'

const PERSONA_HEROES: Record<
  string,
  { image: string; alt: string; subheadline: string }
> = {
  fresh: {
    image: '/products/hero-fresh-2.png',
    alt: 'Pellier leather tote, linen, and olive branches in warm daylight',
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

const PROFILE_FOCUS: Record<string, string> = {
  marco: 'Travel edit',
  anna: 'Gift edit',
  theo: 'Home rituals',
}

export default function PellierHero() {
  const { openDrawerWithQuery } = useUI()
  const { persona, switchPersona, switching } = usePersona()
  const [searchValue, setSearchValue] = useState('')

  const personaId = persona?.id ?? 'fresh'
  const hero = PERSONA_HEROES[personaId] ?? PERSONA_HEROES.fresh
  const allSuggestions = heroPillsForPersona(persona?.id)
  const suggestionIndexes = persona?.id === 'marco' ? [0, 1, 4] : [0, 1, 2]
  const suggestions = suggestionIndexes.map((index) => ({
    index,
    query: allSuggestions[index],
  }))
  const profileSignal = becauseChipsForPersona(persona?.id)[0]?.text

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
      aria-label="Pellier resort edit"
      className="px-3 pt-2 md:px-container-x md:pt-4"
    >
      <div
        className="
          relative mx-auto max-w-[1440px] overflow-hidden
          rounded-[8px] border border-[rgba(24,26,31,0.12)]
        "
        style={{
          minHeight: 'clamp(540px, calc(100dvh - 128px), 640px)',
        }}
      >
        <ResponsiveImage
          src={hero.image}
          alt={hero.alt}
          widths={[480, 960, 1600]}
          sizes="(min-width: 1440px) 1440px, 100vw"
          loading="eager"
          fetchPriority="high"
          pictureClassName="absolute inset-0 block h-full w-full"
          className="h-full w-full object-cover object-[30%_center] transition-opacity duration-300 md:object-center"
        />
        <div
          aria-hidden="true"
          className="
            absolute inset-0
            bg-[linear-gradient(0deg,rgba(243,244,246,0.98)_0%,rgba(243,244,246,0.88)_46%,rgba(243,244,246,0.08)_78%)]
            md:bg-[linear-gradient(90deg,rgba(243,244,246,0.02)_24%,rgba(243,244,246,0.50)_50%,rgba(243,244,246,0.98)_76%)]
          "
        />

        <div
          className="relative flex items-end md:items-center md:justify-end"
          style={{
            minHeight: 'clamp(540px, calc(100dvh - 128px), 640px)',
          }}
        >
          <div className="w-full px-5 pb-7 pt-56 md:w-[54%] md:max-w-[680px] md:px-10 md:py-9 lg:px-14">
            <h1
              data-testid="pellier-hero-headline"
              className="font-display text-[42px] font-normal leading-[1.02] text-espresso md:text-[60px]"
              style={{ letterSpacing: 0 }}
            >
              Pellier
              <span className="block font-medium text-accent-ink">Resort Edit.</span>
            </h1>

            <p
              data-testid="pellier-hero-subheadline"
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
                    data-testid="pellier-hero-search"
                    value={searchValue}
                    onChange={(event) => setSearchValue(event.target.value)}
                    placeholder={
                      isListening ? 'Listening...' : 'Ask Pellier anything...'
                    }
                    aria-label="Ask Pellier anything"
                    className="
                      h-[58px] w-full rounded-full border border-[rgba(24,26,31,0.16)]
                      bg-[rgba(255,255,255,0.94)] pl-[52px] pr-[58px]
                      font-sans text-[15px] text-espresso shadow-warm-sm
                      outline-none transition
                      placeholder:text-[rgba(24,26,31,0.48)]
                      focus:border-[rgba(24,26,31,0.34)] focus:ring-2
                      focus:ring-[rgba(122,38,58,0.16)]
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
                  data-testid="pellier-hero-pills"
                  className="mt-3 flex max-w-[620px] gap-2 overflow-x-auto pb-1"
                  aria-label="Suggested queries"
                >
                  {suggestions.map(({ index, query }) => (
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
                <p className="mb-3 font-sans text-[13px] font-medium text-espresso">
                  Choose a workshop profile
                </p>
                <div className="grid grid-cols-3 gap-2.5">
                  {LOCAL_PERSONAS.map((profile) => (
                    <button
                      key={profile.id}
                      type="button"
                      data-testid={`hero-profile-${profile.id}`}
                      disabled={switching}
                      onClick={() => void switchPersona(profile.id)}
                      className="
                        min-w-0 rounded-[8px] border border-[rgba(24,26,31,0.16)]
                        bg-[rgba(255,255,255,0.90)] p-3 text-left
                        transition hover:-translate-y-px hover:border-[rgba(24,26,31,0.34)]
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
                          <span className="block truncate font-sans text-[11px] text-ink-soft">
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
    </section>
  )
}
