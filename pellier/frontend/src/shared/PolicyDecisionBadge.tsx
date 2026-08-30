/**
 * PolicyDecisionBadge — a Cedar decision, rendered asymmetrically.
 *
 * The asymmetry is the point. ALLOW and DENY must differ by icon, by text,
 * and by accessible name — never by color alone. Two badges that differ
 * only in hue are unreadable to a colorblind attendee and invisible in a
 * grayscale conference projection, which is precisely where this workshop
 * gets demonstrated.
 *
 * The three states carry different claims:
 *
 *   ALLOW         the policy permitted the action; execution is a separate fact
 *   DENY          the policy blocked it *before* execution — no tool ran
 *   NOT_EVALUATED no policy decision exists for this turn
 *
 * `NOT_EVALUATED` is deliberately not styled as either success or failure.
 * Absence of a decision is a real, honest state; coloring it green would
 * claim a permission nobody granted.
 */
import type React from 'react'
import { Check, MinusCircle, ShieldOff } from 'lucide-react'
import type { PolicyDecision } from './governedTypes'

export interface PolicyDecisionBadgeProps {
  decision: PolicyDecision
  /** `sm` for inline chips, `md` for card headers. */
  size?: 'sm' | 'md'
  /** Reason text shown as a tooltip; also appended to the accessible name. */
  reason?: string | null
  className?: string
}

interface DecisionPresentation {
  /** Visible text. Never omitted — this is what makes the badge readable. */
  label: string
  /** Distinct glyph per decision, not a recolored copy of the same mark. */
  Icon: typeof Check
  /** Accessible name. Differs per decision by contract, asserted in tests. */
  accessibleName: string
  fg: string
  bg: string
  border: string
}

const PRESENTATION: Record<PolicyDecision, DecisionPresentation> = {
  ALLOW: {
    label: 'ALLOW',
    Icon: Check,
    accessibleName:
      'Policy decision: ALLOW — the policy permitted the action; execution is reported separately',
    fg: 'var(--gov-allow-fg)',
    bg: 'var(--gov-allow-bg)',
    border: 'var(--gov-allow-border)',
  },
  DENY: {
    label: 'DENY',
    Icon: ShieldOff,
    accessibleName:
      'Policy decision: DENY — blocked before execution, the tool did not run',
    fg: 'var(--gov-deny-fg)',
    bg: 'var(--gov-deny-bg)',
    border: 'var(--gov-deny-border)',
  },
  NOT_EVALUATED: {
    label: 'NOT EVALUATED',
    Icon: MinusCircle,
    accessibleName: 'Policy decision: not evaluated for this turn',
    fg: 'var(--gov-neutral-fg)',
    bg: 'var(--gov-neutral-bg)',
    border: 'var(--gov-neutral-border)',
  },
}

export const PolicyDecisionBadge: React.FC<PolicyDecisionBadgeProps> = ({
  decision,
  size = 'sm',
  reason,
  className,
}) => {
  const p = PRESENTATION[decision] ?? PRESENTATION.NOT_EVALUATED
  const iconSize = size === 'md' ? 15 : 13
  const accessibleName = reason
    ? `${p.accessibleName}. Reason: ${reason}`
    : p.accessibleName

  return (
    <span
      className={className}
      data-testid="policy-decision-badge"
      data-decision={decision}
      title={reason ?? p.accessibleName}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        fontFamily: 'var(--dl-font-mono)',
        fontSize: size === 'md' ? '12px' : '11px',
        letterSpacing: '0.1em',
        fontWeight: 600,
        color: p.fg,
        backgroundColor: p.bg,
        border: `1px solid ${p.border}`,
        borderRadius: 'var(--gov-radius-sm)',
        padding: size === 'md' ? '4px 9px' : '2px 7px',
        whiteSpace: 'nowrap',
      }}
    >
      <p.Icon size={iconSize} aria-hidden="true" />
      {/* Visible text carries the decision for sighted users; the hidden
          span carries the full claim for assistive technology. */}
      <span aria-hidden="true">{p.label}</span>
      <span className="gov-visually-hidden">{accessibleName}</span>
    </span>
  )
}

export default PolicyDecisionBadge
