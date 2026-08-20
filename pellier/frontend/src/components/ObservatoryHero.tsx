/**
 * ObservatoryHero — editorial hero for the Observatory surface.
 *
 * Mirrors the storefront's hero register (kicker · display italic ·
 * epigraph) so the two surfaces read as siblings rather than a
 * pellier paired with a developer dashboard.
 */
import { cssVar as c } from '../design/cssVars'

const OBSERVATORY_LABEL = 'Pellier Observatory'

export default function ObservatoryHero({ editionNumber = 6 }: { editionNumber?: number }) {
  const label = `${OBSERVATORY_LABEL.toUpperCase()} · NO. ${String(editionNumber).padStart(
    2,
    '0',
  )}`
  return (
    <section
      data-testid="observatory-hero"
      className="px-6 pt-6 pb-8 text-center"
    >
      <p
        className="font-mono text-[11px] font-medium uppercase mb-5 flex items-center justify-center gap-2"
        style={{ color: c.accent, letterSpacing: '0.22em' }}
      >
        <span
          aria-hidden
          className="inline-block w-[5px] h-[5px] rounded-full"
          style={{ background: c.accent }}
        />
        <span>{label}</span>
        <span
          aria-hidden
          className="inline-block w-[5px] h-[5px] rounded-full"
          style={{ background: c.accent }}
        />
      </p>
      <h1
        className="text-[54px] md:text-[60px] leading-[1] m-0"
        style={{
          color: c.ink,
          fontFamily: 'Fraunces, Georgia, serif',
          fontWeight: 400,
          fontStyle: 'italic',
          letterSpacing: '-0.02em',
        }}
      >
        Pellier Observatory.
      </h1>
      <p
        className="text-[16px] leading-[1.6] max-w-[620px] mx-auto mt-5"
        style={{
          color: c.ink2,
          fontFamily: 'Fraunces, Georgia, serif',
          fontStyle: 'italic',
          fontWeight: 600,
        }}
      >
        Where Agents think aloud. Every step of the reasoning, on display.
      </p>
    </section>
  )
}
