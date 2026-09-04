/**
 * StateBadge — one system state, said in words.
 *
 * `PolicyDecisionBadge` is the model this follows and the reason it exists as
 * a separate component: a Cedar decision is a single, closed vocabulary with
 * fixed accessible sentences, and it should never be reachable through a
 * generic `tone` prop. StateBadge is for everything else the two surfaces
 * report (shipped, available, live, fixture, degraded, not evaluated) which
 * the codebase had spelled 52 different inline ways.
 *
 * The rules it inherits from PolicyDecisionBadge:
 *
 *   - The label is always visible text. Colour is reinforcement, never the
 *     carrier: the workshop is projected in rooms with bad colour and attended
 *     by colourblind engineers.
 *   - Every tone gets a distinct glyph, not the same dot recoloured.
 *   - Absence of evidence (`neutral`, `unavailable`) is neither success nor
 *     failure and is not styled as either.
 *
 * Shape: 4px, not a pill. On these surfaces a pill is something you press:
 * filters, account controls, the disclosure button. A state is something you
 * read. Mixing the two shapes is most of why one surface read like a different
 * product from the surface beside it.
 *
 * Colour resolves to `--obs-status-*` for system state and `--gov-prov-*` for
 * provenance. The `--obs-status-*` family is declared on `.observatory-root`
 * only, so every reference carries the equivalent Daylight primitive as its
 * fallback and the badge renders correctly on the desk too.
 */
import type React from 'react'
import {
  Check,
  CircleDashed,
  CircleSlash,
  Database,
  FlaskConical,
  MinusCircle,
  TriangleAlert,
} from 'lucide-react'

export type StateBadgeTone =
  /* System state */
  | 'ok'
  | 'attention'
  | 'degraded'
  | 'neutral'
  /* Provenance: where the number in front of you came from */
  | 'live'
  | 'fixture'
  | 'modeled'
  | 'unavailable'

export interface StateBadgeProps {
  /** The visible label. Required: colour never carries the state alone. */
  children: React.ReactNode
  tone?: StateBadgeTone
  /** Suppress the glyph where the badge sits in a column of its own. */
  icon?: boolean
  /**
   * Longer sentence for assistive technology and the tooltip. Without it the
   * visible label is the whole accessible name, which is correct for a label
   * that already reads as a sentence fragment ("Shipped", "Not evaluated").
   */
  description?: string
  className?: string
  'data-testid'?: string
}

interface TonePresentation {
  fg: string
  bg: string
  border: string
  Icon: typeof Check
}

const PRESENTATION: Record<StateBadgeTone, TonePresentation> = {
  ok: {
    fg: 'var(--obs-status-ok-fg, var(--dl-ok))',
    bg: 'var(--obs-status-ok-bg, rgba(63, 98, 18, 0.1))',
    border: 'var(--obs-status-ok-line, rgba(63, 98, 18, 0.32))',
    Icon: Check,
  },
  attention: {
    fg: 'var(--obs-status-attention-fg, var(--dl-accent))',
    bg: 'var(--obs-status-attention-bg, rgba(154, 52, 18, 0.1))',
    border: 'var(--obs-status-attention-line, rgba(154, 52, 18, 0.32))',
    Icon: CircleDashed,
  },
  degraded: {
    fg: 'var(--obs-status-degraded-fg, var(--dl-warn))',
    bg: 'var(--obs-status-degraded-bg, rgba(180, 83, 9, 0.1))',
    border: 'var(--obs-status-degraded-line, rgba(180, 83, 9, 0.32))',
    Icon: TriangleAlert,
  },
  neutral: {
    fg: 'var(--obs-status-neutral-fg, var(--dl-ink-2))',
    bg: 'var(--obs-status-neutral-bg, rgba(31, 20, 16, 0.06))',
    border: 'var(--obs-status-neutral-line, var(--dl-line))',
    Icon: MinusCircle,
  },
  live: {
    fg: 'var(--gov-prov-live)',
    bg: 'rgba(63, 98, 18, 0.1)',
    border: 'rgba(63, 98, 18, 0.32)',
    Icon: Database,
  },
  fixture: {
    fg: 'var(--gov-prov-fixture)',
    bg: 'var(--dl-paper-2)',
    border: 'var(--gov-hairline)',
    Icon: FlaskConical,
  },
  modeled: {
    fg: 'var(--gov-prov-modeled)',
    bg: 'rgba(180, 83, 9, 0.1)',
    border: 'rgba(180, 83, 9, 0.32)',
    Icon: TriangleAlert,
  },
  unavailable: {
    fg: 'var(--gov-prov-unavailable)',
    bg: 'transparent',
    border: 'var(--gov-hairline)',
    Icon: CircleSlash,
  },
}

export const StateBadge: React.FC<StateBadgeProps> = ({
  children,
  tone = 'neutral',
  icon = true,
  description,
  className,
  'data-testid': testId,
}) => {
  const p = PRESENTATION[tone] ?? PRESENTATION.neutral

  return (
    <span
      className={className}
      data-tone={tone}
      data-testid={testId}
      title={description}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        fontFamily: 'var(--obs-heading)',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        lineHeight: 1.4,
        color: p.fg,
        backgroundColor: p.bg,
        border: `1px solid ${p.border}`,
        borderRadius: 'var(--gov-radius-sm)',
        padding: '3px 8px',
        whiteSpace: 'nowrap',
      }}
    >
      {icon ? <p.Icon size={12} strokeWidth={2} aria-hidden="true" /> : null}
      <span>{children}</span>
      {description ? (
        <span className="gov-visually-hidden">{description}</span>
      ) : null}
    </span>
  )
}

export default StateBadge
