/**
 * GovernedTurnReceipt — the compact receipt under a completed answer.
 *
 * Design stance: quiet governance in Boutique. The shopper gets a beautiful
 * answer; the receipt is a single restrained line that says what the system
 * actually did, with the full accounting one click away in Atelier.
 *
 * The hard rule is **only render what the turn emitted**. Every field here
 * is optional, and an absent field renders as an honest "not reported"
 * rather than a zero. Inferring "0 sources" from a missing field would be a
 * fabricated claim about retrieval, and inferring a policy outcome from
 * silence would be worse — this workshop's entire point is that ALLOW,
 * DENY, and not-evaluated are three different things.
 *
 * Named `GovernedTurnReceipt` rather than `TurnReceipt` because
 * `components/TurnReceipt.tsx` already exists as the copy-reference chip.
 * Two components with one name in different namespaces is how a codebase
 * ends up with two divergent evidence models.
 */
import type React from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Database, Wrench } from 'lucide-react'
import {
  GovernedSeal,
  PolicyDecisionBadge,
  receiptRoute,
  type PolicyDecision,
  type RailDecision,
} from '../shared'

export interface GovernedTurnReceiptProps {
  /** Session the turn belongs to; drives the evidence deep link. */
  sessionId?: string | null
  /** Stable per-turn id from the backend, when emitted. */
  turnId?: string | null
  /** OTEL trace id, when the turn reported one. */
  traceId?: string | null
  /** Number of catalog rows the answer was grounded in. */
  sourceCount?: number | null
  /** Number of tools that actually executed. */
  toolCount?: number | null
  /** Cedar outcome. Omit entirely when no policy was evaluated. */
  policyDecision?: PolicyDecision | null
  /** Reason text from the policy engine, when present. */
  policyReason?: string | null
  /** Wall-clock latency the backend reported, in ms. */
  latencyMs?: number | null
  /** Rail decision, used for the seal. */
  railDecision?: RailDecision | null
}

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--dl-font-mono)',
  fontSize: '10.5px',
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: 'var(--dl-muted)',
}

const valueStyle: React.CSSProperties = {
  fontFamily: 'var(--dl-font-sans)',
  fontSize: '13px',
  color: 'var(--dl-ink)',
  fontWeight: 500,
}

/** One metric cell. Renders "not reported" when the turn emitted nothing. */
const Metric: React.FC<{
  icon: React.ReactNode
  label: string
  value: number | null | undefined
  suffix?: string
}> = ({ icon, label, value, suffix }) => {
  const known = typeof value === 'number' && Number.isFinite(value)
  return (
    <span
      style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
      title={known ? undefined : `${label} was not reported for this turn`}
    >
      <span aria-hidden="true" style={{ color: 'var(--dl-muted)', display: 'flex' }}>
        {icon}
      </span>
      <span style={labelStyle}>{label}</span>
      {known ? (
        <span style={valueStyle}>
          {value}
          {suffix ?? ''}
        </span>
      ) : (
        <span
          style={{ ...valueStyle, color: 'var(--gov-unavailable-fg)', fontWeight: 400 }}
        >
          not reported
        </span>
      )}
    </span>
  )
}

export const GovernedTurnReceipt: React.FC<GovernedTurnReceiptProps> = ({
  sessionId,
  turnId,
  traceId,
  sourceCount,
  toolCount,
  policyDecision,
  policyReason,
  latencyMs,
  railDecision,
}) => {
  // Nothing to show is a valid outcome — a triage reply that ran no tools
  // and read no catalog rows should not sprout an empty evidence strip.
  const hasAnything =
    typeof sourceCount === 'number' ||
    typeof toolCount === 'number' ||
    typeof latencyMs === 'number' ||
    !!policyDecision ||
    !!railDecision ||
    !!sessionId

  if (!hasAnything) return null

  return (
    <div
      data-testid="governed-turn-receipt"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '14px',
        padding: '10px 12px',
        marginTop: '8px',
        background: 'var(--gov-surface-evidence)',
        border: `1px solid ${'var(--gov-hairline)'}`,
        borderRadius: 'var(--gov-radius-md)',
      }}
    >
      <Metric
        icon={<Database size={13} />}
        label="Sources"
        value={sourceCount ?? null}
      />
      <Metric icon={<Wrench size={13} />} label="Tools" value={toolCount ?? null} />

      {/* Policy is shown only when a decision exists. Absence is not ALLOW. */}
      {policyDecision && (
        <PolicyDecisionBadge decision={policyDecision} reason={policyReason} />
      )}

      {typeof latencyMs === 'number' && Number.isFinite(latencyMs) && (
        <Metric
          icon={<span style={{ fontSize: '11px' }}>⏱</span>}
          label="Latency"
          value={Math.round(latencyMs)}
          suffix="ms"
        />
      )}

      {railDecision && <GovernedSeal railDecision={railDecision} />}

      <span style={{ flex: 1 }} />

      {/* Base-path-safe: <Link> applies the router basename, so this works
          behind the Workshop Studio /ports/8000/ proxy. */}
      <Link
        to={receiptRoute({ sessionId, turnId, traceId })}
        className="gov-focusable"
        data-testid="governed-receipt-link"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          fontFamily: 'var(--dl-font-sans)',
          fontSize: '13px',
          fontWeight: 500,
          color: 'var(--gov-terracotta)',
          textDecoration: 'none',
          // 44px-tall target on touch without inflating the desktop row.
          minHeight: '32px',
          padding: '4px 2px',
        }}
      >
        Why this answer?
        <ArrowUpRight size={14} aria-hidden="true" />
      </Link>
    </div>
  )
}

export default GovernedTurnReceipt
