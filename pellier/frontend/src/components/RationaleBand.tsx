/**
 * RationaleBand — italic Fraunces pull-quote that explains the agent's
 * curation strategy for the grid below it. Sits between the curated
 * section eyebrow + headline and the product grid.
 *
 * The text describes the deterministic tag-ranking rule used for the
 * selected workshop profile. It does not imply live browsing or inventory
 * evidence that the participant has not generated.
 *
 * The storefront only needs the shopper-facing rationale sentence. Detailed
 * signal and tool provenance remains available inside each card disclosure.
 */
import { usePersona } from '../contexts/PersonaContext'

interface PersonaRationale {
  text: string
}

const PERSONA_RATIONALE: Record<string, PersonaRationale> = {
  marco: {
    text: 'Marco ranks linen, travel, leather, and classic tags higher. Each card below shows the reason it made the edit.',
  },
  anna: {
    text: 'Anna ranks gift, candle, ceramic, and home tags higher. Each card below shows the reason it made the edit.',
  },
  theo: {
    text: 'Theo ranks ceramic, slow, artisanal, and home tags higher. Each card below shows the reason it made the edit.',
  },
  fresh: {
    text: 'The floor opens in its authored order. Choose who is shopping and it rearranges around their taste.',
  },
}

export default function RationaleBand() {
  const { persona } = usePersona()
  const personaId = persona?.id ?? null
  const r = PERSONA_RATIONALE[personaId ?? 'fresh'] ?? PERSONA_RATIONALE.fresh

  return (
    <p
      data-testid="rationale-band"
      data-persona={personaId ?? 'fresh'}
      className="mt-3 max-w-[660px] font-sans text-[14px] leading-6 text-ink-soft"
    >
      {r.text}
    </p>
  )
}
