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
import { ArrowRight, Sparkles } from 'lucide-react'
import { usePersona } from '../contexts/PersonaContext'
import { LOCAL_PERSONAS } from '../data/personas'
import { getPersonaPortrait } from '../data/personaPhotos'
import { becauseChipsForPersona } from '../data/personaCurations'
import { HERO_CONCIERGE } from '../copy'

interface PersonaConciergeProps {
  /** Browse the floor without selecting a profile. */
  onContinueAsGuest: () => void
}

type ProfileId = keyof typeof HERO_CONCIERGE.PROFILES

function profileNote(id: string): string {
  return HERO_CONCIERGE.PROFILES[id as ProfileId] ?? ''
}

export default function PersonaConcierge({
  onContinueAsGuest,
}: PersonaConciergeProps) {
  const { persona, switchPersona, switching } = usePersona()

  // The seed line is the same signal the hero used to print under the
  // search bar: it names why the floor looks the way it does.
  const profileSignal = becauseChipsForPersona(persona?.id)[0]?.text

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
        {LOCAL_PERSONAS.map((profile) => {
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
                  {profileNote(profile.id)}
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

      {persona ? (
        <p className="pellier-concierge-seed" data-testid="concierge-seed">
          {profileSignal ? (
            <>
              <strong>Because</strong> {profileSignal}.
            </>
          ) : (
            <>
              <strong>{persona.display_name}</strong> is shopping. Select
              another profile to reshape the floor.
            </>
          )}
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
