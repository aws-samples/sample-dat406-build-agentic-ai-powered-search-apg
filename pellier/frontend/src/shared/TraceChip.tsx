/**
 * TraceChip — a small mono pill naming the tool/signal that produced
 * a result.
 *
 * The same atom appears on Pellier (under product cards, in the
 * Live Floor Strip, on the Memory Handoff card) and on Pellier Labs
 * (Tools surface, Sessions, Observatory). Importing both surfaces
 * from this single file is the cohesion guarantee — when the visual
 * treatment evolves, every place that names a tool updates together.
 *
 * Visual: warm tint + 1px accent border, mono label at 11px with slight
 * tracking for readable dot-syntax. Optional `duration` renders a faint
 * right-aligned mono timestamp ("· 2.1s ago"). Optional `linkToAgentTrace`
 * wraps the chip in an anchor that deep-links to Pellier Labs route that
 * explains this concept (the "how this works" handoff).
 */
import React from 'react'
import { ArrowUpRight } from 'lucide-react'
import { lookupVocab } from './agentVocabulary'
import { routePath } from '../utils/assetPath'

export interface TraceChipProps {
  /** Tool name, dot-separated. e.g. "memory.recall", "inventory.live". */
  tool: string
  /** Optional trailing duration string ("2.1s ago", "12s ago"). */
  duration?: string
  /**
   * When true, wraps the chip in an anchor tag pointing to the
   * Pellier Labs route that explains this tool. Lets shoppers click
   * any trace and land on the developer-facing explainer for it.
   */
  linkToAgentTrace?: boolean
  /** Visual variant. `solid` is the default technical treatment;
   *  `ghost` is a softer fill suitable for dark surfaces, and
   *  `provenance` is the shopper-facing Pellier label treatment. */
  variant?: 'solid' | 'ghost' | 'provenance'
  /** Label display. `tool` preserves the raw trace, `label` uses the
   *  attendee-friendly vocabulary label while keeping the raw trace in
   *  the tooltip and test id. */
  labelMode?: 'tool' | 'label'
  /** Compact mode shrinks padding for dense tables. */
  compact?: boolean
}

export const TraceChip: React.FC<TraceChipProps> = ({
  tool,
  duration,
  linkToAgentTrace = false,
  variant = 'solid',
  labelMode = 'tool',
  compact = false,
}) => {
  const vocab = lookupVocab(tool)
  const isProvenance = variant === 'provenance'
  const accent = 'var(--trace-accent, var(--accent))'
  const label = labelMode === 'label' ? vocab.label : tool

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: isProvenance ? 5 : 6,
    fontFamily: 'var(--mono)',
    fontSize: isProvenance ? 10.5 : 11,
    fontWeight: isProvenance ? 600 : 500,
    letterSpacing: isProvenance ? '0.08em' : '0.05em',
    fontFeatureSettings: "'calt' 1, 'liga' 1",
    color: isProvenance
      ? `color-mix(in srgb, ${accent} 88%, var(--ink))`
      : 'var(--accent)',
    background:
      isProvenance
        ? `color-mix(in srgb, ${accent} 7%, var(--cream-warm))`
        : variant === 'ghost'
        ? 'color-mix(in srgb, var(--accent) 5%, transparent)'
        : 'color-mix(in srgb, var(--accent) 9%, var(--cream-warm))',
    border: isProvenance
      ? `1px solid color-mix(in srgb, ${accent} 18%, transparent)`
      : '1px solid color-mix(in srgb, var(--accent) 22%, transparent)',
    borderRadius: isProvenance ? 999 : 6,
    padding: isProvenance
      ? compact ? '4px 8px' : '5px 11px'
      : compact ? '4px 8px' : '5px 10px',
    whiteSpace: 'nowrap',
    textDecoration: 'none',
    cursor: linkToAgentTrace ? 'pointer' : 'default',
    transition: 'background 0.15s, border-color 0.15s',
  }

  const content = (
    <>
      {isProvenance ? (
        <span
          aria-hidden="true"
          style={{
            width: 5,
            height: 5,
            borderRadius: 999,
            background: accent,
            opacity: 0.78,
            flexShrink: 0,
          }}
        />
      ) : null}
      <span>{label}</span>
      {duration ? (
        <span style={{ color: 'color-mix(in srgb, var(--accent) 48%, var(--ink))' }}>
          · {duration}
        </span>
      ) : null}
      {isProvenance && linkToAgentTrace ? (
        <ArrowUpRight
          aria-hidden="true"
          size={11}
          strokeWidth={2}
          style={{ opacity: 0.62, flexShrink: 0 }}
        />
      ) : null}
    </>
  )

  if (linkToAgentTrace) {
    return (
      <a
        href={routePath(vocab.agentTracePath)}
        title={`${vocab.label} — ${vocab.description}`}
        data-testid={`trace-chip-${tool}`}
        style={baseStyle}
        onMouseEnter={(e) => {
          e.currentTarget.style.background =
            isProvenance
              ? `color-mix(in srgb, ${accent} 12%, var(--cream-warm))`
              : 'color-mix(in srgb, var(--accent) 14%, var(--cream-warm))'
          e.currentTarget.style.borderColor =
            isProvenance
              ? `color-mix(in srgb, ${accent} 32%, transparent)`
              : 'color-mix(in srgb, var(--accent) 38%, transparent)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background =
            isProvenance
              ? `color-mix(in srgb, ${accent} 7%, var(--cream-warm))`
              : variant === 'ghost'
              ? 'color-mix(in srgb, var(--accent) 5%, transparent)'
              : 'color-mix(in srgb, var(--accent) 9%, var(--cream-warm))'
          e.currentTarget.style.borderColor =
            isProvenance
              ? `color-mix(in srgb, ${accent} 18%, transparent)`
              : 'color-mix(in srgb, var(--accent) 22%, transparent)'
        }}
      >
        {content}
      </a>
    )
  }

  return (
    <span
      title={`${vocab.label} — ${vocab.description}`}
      data-testid={`trace-chip-${tool}`}
      style={baseStyle}
    >
      {content}
    </span>
  )
}
