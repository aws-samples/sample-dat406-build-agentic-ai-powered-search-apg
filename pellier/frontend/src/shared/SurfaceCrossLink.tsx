/**
 * SurfaceCrossLink — small inline anchor that bridges the two surfaces.
 *
 * Two preset modes:
 *   - "to-pellier" — used on Pellier Labs surfaces. Reads "→ See this in
 *      Pellier" and links back to the storefront, optionally
 *      with an `?ask=` query that opens the chat drawer with a
 *      pre-filled prompt that exercises this concept.
 *   - "to-agent-trace" — used on Pellier surfaces. Reads "How this works
 *      →" and deep-links to Pellier Labs route that explains the
 *      concept (memory, tools, agents, etc).
 *
 * Visual: Instrument Serif / Fraunces italic, 15px, terracotta accent,
 * subtle dotted underline — reads as editorial caption, not a banner CTA.
 * vocabulary (`see · this · in · Pellier`) on every Pellier Labs
 * surface keeps the round trip predictable.
 */
import React from 'react'
import { Link } from 'react-router-dom'

export type CrossLinkDirection = 'to-pellier' | 'to-agent-trace'

export interface SurfaceCrossLinkProps {
  direction: CrossLinkDirection
  /**
   * For `to-pellier`: optional `?ask=` query that auto-fires the
   * Pellier chat drawer with this prompt. For `to-agent-trace`: the
   * Pellier Labs path to navigate to (e.g. "/pellier-labs/memory").
   */
  href?: string
  /** Override the default copy. */
  label?: string
  /** Use upright text when the link sits inside sans/body UI copy. */
  italic?: boolean
}

const ACCENT = 'var(--accent)'

export const SurfaceCrossLink: React.FC<SurfaceCrossLinkProps> = ({
  direction,
  href,
  label,
  italic = true,
}) => {
  const defaultLabel =
    direction === 'to-pellier'
      ? 'See this in Pellier'
      : 'How this works'

  const targetHref =
    href ??
    (direction === 'to-pellier' ? '/' : '/pellier-labs')

  const arrow = direction === 'to-pellier' ? '→' : '→'

  return (
    <Link
      to={targetHref}
      data-testid={`surface-cross-link-${direction}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontFamily: 'var(--serif)',
        fontStyle: italic ? 'italic' : 'normal',
        fontSize: 15,
        fontWeight: 400,
        letterSpacing: '-0.01em',
        color: ACCENT,
        textDecoration: 'none',
        borderBottom: '1px dotted color-mix(in srgb, var(--accent) 42%, transparent)',
        paddingBottom: 2,
        transition: 'border-color 0.15s, color 0.15s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderBottomColor =
          'color-mix(in srgb, var(--accent) 78%, transparent)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderBottomColor =
          'color-mix(in srgb, var(--accent) 42%, transparent)'
      }}
    >
      <span>{label ?? defaultLabel}</span>
      <span aria-hidden="true">{arrow}</span>
    </Link>
  )
}
