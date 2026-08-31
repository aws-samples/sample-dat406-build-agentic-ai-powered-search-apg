/**
 * PersonaConcierge - the hero's profile surface.
 *
 * Wraps the persona selection that used to sit inline in PellierHero. The
 * behaviour is unchanged: selecting a profile calls `switchPersona`, which
 * mints a new session and reranks the floor. Nothing here invents
 * personalization the application does not already perform.
 *
 * Guest is a real state, not a dismissal. With no active profile the
 * storefront renders the canonical unranked ordering, so the guest action
 * takes a shopper to that floor rather than pretending to tailor it.
 */
import { useEffect, useState } from 'react'
import { ArrowRight, Sparkles } from 'lucide-react'
import { usePersona, type PersonaListItem } from '../contexts/PersonaContext'
import { getPersonaPortrait } from '../data/personaPhotos'
import { HERO_CONCIERGE } from '../copy'

interface PersonaConciergeProps {
  /** Browse the floor without selecting a profile. */
  onContinueAsGuest: () => void
}

export default function PersonaConcierge({
  onContinueAsGuest,
}: PersonaConciergeProps) {
  const { persona, switchPersona, switching, switchError } = usePersona()
  const [profiles, setProfiles] = useState<PersonaListItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetch('/api/observatory/personas')
      .then(async (response) => {
        if (!response.ok) throw new Error(`Live personas unavailable: ${response.status}`)
        return response.json() as Promise<PersonaListItem[]>
      })
      .then((items) => setProfiles(items.filter((item) => item.id !== 'fresh')))
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'Live personas unavailable.'),
      )
  }, [])

  return (
    <aside
      className="pellier-concierge"
      data-testid="persona-concierge"
      aria-labelledby="persona-concierge-title"
    >
      <div className="pellier-concierge-heading">
        <span className="pellier-eyebrow">{HERO_CONCIERGE.EYEBROW}</span>
        <h2 id="persona-concierge-title">{HERO_CONCIERGE.TITLE}</h2>
        <p>{HERO_CONCIERGE.HELPER}</p>
      </div>

      <ul className="pellier-concierge-profiles">
        {profiles.map((profile) => {
          const isActive = persona?.id === profile.id
          const portrait = getPersonaPortrait(profile.id)
          return (
            <li key={profile.id}>
              <button
                type="button"
                className="pellier-profile"
                data-testid={`hero-profile-${profile.id}`}
                data-active={isActive ? 'true' : undefined}
                aria-pressed={isActive}
                disabled={switching}
                onClick={() => void switchPersona(profile.id)}
              >
                <span
                  className="pellier-profile-portrait"
                  style={
                    portrait ? undefined : { background: profile.avatar_color }
                  }
                >
                  {portrait ? (
                    <img
                      src={portrait}
                      alt=""
                      aria-hidden="true"
                      loading="lazy"
                      decoding="async"
                      width={160}
                      height={160}
                    />
                  ) : null}
                </span>
                <span className="pellier-profile-name">
                  {profile.display_name}
                </span>
                <span className="pellier-profile-note">
                  {profile.blurb}
                </span>
                {/* Active profile is stated, not only tinted. */}
                {isActive ? (
                  <span className="pellier-profile-state">Shopping</span>
                ) : null}
              </button>
            </li>
          )
        })}
      </ul>
      {error || switchError ? (
        <p className="pellier-concierge-seed" role="alert">
          {error ?? switchError}
        </p>
      ) : null}

      {persona ? (
        <p className="pellier-concierge-seed" data-testid="concierge-seed">
          <strong>{persona.display_name}</strong> is shopping from an
          Aurora-backed client profile.
        </p>
      ) : (
        <button
          type="button"
          className="pellier-concierge-guest"
          data-testid="concierge-guest"
          onClick={onContinueAsGuest}
        >
          <Sparkles size={14} aria-hidden="true" />
          {HERO_CONCIERGE.GUEST_ACTION}
          <ArrowRight size={14} aria-hidden="true" />
        </button>
      )}
    </aside>
  )
}
