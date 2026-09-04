/**
 * SectionEyebrow — the one label that opens a section.
 *
 * Both technical surfaces had drifted to five eyebrow recipes. The
 * Observatory shipped a sans version with a dot, a legacy `.at-section-eyebrow`
 * class, and three mono recipes; the Operator desk carried six more selectors,
 * one of them mono at 10px. Five registers for one job is what makes a surface
 * read as several products.
 *
 * One recipe: Instrument Sans, 11px, 600, 0.08em, uppercase.
 *
 * Sans, not mono, and this is the load-bearing decision. Monospace on these
 * surfaces means "this is an identifier, a table, a duration, a value you
 * could paste into psql". A section label is none of those. Spending mono on
 * prose labels is what left the real identifiers with no way to stand out.
 *
 * `tone="brand"` is burgundy and names a section that belongs to the product's
 * own structure. `tone="muted"` names a subordinate label inside a card, where
 * a second burgundy mark would compete with the section above it.
 */
import type React from 'react'

export type SectionEyebrowTone = 'brand' | 'muted'

export interface SectionEyebrowProps {
  children: React.ReactNode
  /** `brand` for a section opener, `muted` for a label inside a card. */
  tone?: SectionEyebrowTone
  /** The leading dot. Drop it where the eyebrow is already inside a rule. */
  dot?: boolean
  as?: 'span' | 'div' | 'p'
  id?: string
  className?: string
  'data-testid'?: string
}

const TONE_COLOR: Record<SectionEyebrowTone, string> = {
  brand: 'var(--pellier-burgundy)',
  muted: 'var(--obs-ink-4)',
}

export const SectionEyebrow: React.FC<SectionEyebrowProps> = ({
  children,
  tone = 'brand',
  dot = true,
  as: Tag = 'span',
  id,
  className,
  'data-testid': testId,
}) => {
  const color = TONE_COLOR[tone] ?? TONE_COLOR.brand

  return (
    <Tag
      id={id}
      className={className}
      data-tone={tone}
      data-testid={testId}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        fontFamily: 'var(--obs-heading)',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        lineHeight: 1,
        color,
      }}
    >
      {dot ? (
        <span
          aria-hidden="true"
          style={{
            width: '5px',
            height: '5px',
            borderRadius: '999px',
            background: 'currentColor',
            flexShrink: 0,
          }}
        />
      ) : null}
      {children}
    </Tag>
  )
}

export default SectionEyebrow
