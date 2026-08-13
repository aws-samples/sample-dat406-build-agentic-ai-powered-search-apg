/**
 * RationaleBand — italic Fraunces pull-quote that explains the agent's
 * curation strategy for the grid below it. Sits between the curated
 * section eyebrow + headline and the product grid.
 *
 * The text describes the deterministic tag-ranking rule used for the
 * selected workshop profile. It does not imply live browsing or inventory
 * evidence that the participant has not generated.
 *
 * Visual: thin terracotta left rule + `you said …` eyebrow + the
 * rationale clause. No new tokens — same accent / espresso / Fraunces.
 */
import { usePersona } from '../contexts/PersonaContext'
import type { CSSProperties } from 'react'

interface PersonaRationale {
  /** Eyebrow above the rationale ("you said …" / "you've been browsing …"). */
  eyebrow: string
  /** Italic body line — single sentence preferred. */
  text: string
}

const PERSONA_RATIONALE: Record<string, PersonaRationale> = {
  marco: {
    eyebrow: 'Profile seed · travel and natural fibers',
    text: 'Marco ranks linen, travel, leather, and classic tags higher. Each card below shows the reason it made the edit.',
  },
  anna: {
    eyebrow: 'Profile seed · gifting and home',
    text: 'Anna ranks gift, candle, ceramic, and home tags higher. Each card below shows the reason it made the edit.',
  },
  theo: {
    eyebrow: 'Profile seed · slow craft and home rituals',
    text: 'Theo ranks ceramic, slow, artisanal, and home tags higher. Each card below shows the reason it made the edit.',
  },
  fresh: {
    eyebrow: 'No profile selected · catalog order',
    text: 'The default floor preserves the authored catalog order. Choose a workshop profile to apply its explicit tag weights.',
  },
}

export default function RationaleBand() {
  const { persona } = usePersona()
  const personaId = persona?.id ?? null
  const r = PERSONA_RATIONALE[personaId ?? 'fresh'] ?? PERSONA_RATIONALE.fresh
  const personaAccent = persona?.avatar_color ?? 'var(--accent)'

  return (
    <div
      data-testid="rationale-band"
      data-persona={personaId ?? 'fresh'}
      className="max-w-[1440px] mx-auto px-container-x mb-7 md:mb-9"
      style={{ '--boutique-accent': personaAccent } as CSSProperties}
    >
      <p
        className="font-display italic text-espresso m-0"
        style={{
          fontSize: 'clamp(17px, 1.4vw, 19px)',
          lineHeight: 1.55,
          maxWidth: 780,
          borderLeft:
            '2px solid color-mix(in srgb, var(--boutique-accent) 82%, transparent)',
          padding: '6px 0 6px 18px',
        }}
      >
        <span
          className="font-mono"
          style={{
            display: 'block',
            fontStyle: 'normal',
            fontWeight: 600,
            fontSize: 'var(--dl-fs-eyebrow)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'color-mix(in srgb, var(--boutique-accent) 78%, var(--ink))',
            marginBottom: 8,
          }}
        >
          {r.eyebrow}
        </span>
        {r.text}
      </p>
    </div>
  )
}
