/**
 * EmptyState — what a surface says when it has nothing to show.
 *
 * These two surfaces are evidence instruments, so an empty panel is a claim
 * and not a gap: nothing was recorded, nothing was provisioned, nothing was
 * denied. The Observatory and the desk had eighteen of these between them and
 * every one said it differently, several of them in 14px muted grey that read
 * as a rendering failure rather than as an answer.
 *
 * Four parts, and the order is the argument:
 *
 *   eyebrow   which panel is empty
 *   headline  one sentence, in the display face at 22-24px. Fraunces here is
 *             deliberate: an empty state is the one moment a technical surface
 *             has nothing to be dense about, so it gets the product's own
 *             voice rather than shrinking apologetically.
 *   body      optional prose: what would fill it
 *   reason    optional mono line: the table, service or window that came back
 *             empty. Mono because this one is an identifier, and it is the
 *             part an attendee can go and check.
 *   action    at most one. Two actions in an empty state means the surface
 *             does not know what it wants the reader to do.
 *
 * The headline renders as a `<p>`, not a heading. `base.css` forces every
 * `h1`-`h6` under `.observatory-root` to the sans stack with `!important`
 * unless it carries `.font-display`, and `index.css` then forces
 * `.pellier-page-surface .font-display` back to sans. A paragraph with an
 * inline family is the one form that keeps Fraunces on both surfaces, and an
 * empty state is not page structure anyway.
 */
import type React from 'react'

import { SectionEyebrow } from './SectionEyebrow'

export interface EmptyStateProps {
  /** Names the panel that is empty. */
  eyebrow: string
  /** One sentence. Say what is absent, not "no data". */
  headline: React.ReactNode
  /** Optional prose: what would put something here. */
  body?: React.ReactNode
  /** Optional mono line naming the source that came back empty. */
  reason?: React.ReactNode
  /** At most one action. */
  action?: React.ReactNode
  align?: 'start' | 'center'
  className?: string
  'data-testid'?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  eyebrow,
  headline,
  body,
  reason,
  action,
  align = 'start',
  className,
  'data-testid': testId,
}) => {
  const centered = align === 'center'

  return (
    <div
      className={className}
      data-testid={testId}
      data-align={align}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: centered ? 'center' : 'flex-start',
        textAlign: centered ? 'center' : 'left',
        gap: '12px',
      }}
    >
      <SectionEyebrow tone="muted">{eyebrow}</SectionEyebrow>

      <p
        style={{
          margin: 0,
          maxWidth: '46ch',
          fontFamily: 'var(--display)',
          fontSize: 'clamp(22px, 2vw, 24px)',
          fontWeight: 400,
          lineHeight: 1.25,
          letterSpacing: '-0.012em',
          color: 'var(--obs-ink-1)',
        }}
      >
        {headline}
      </p>

      {body ? (
        <p
          style={{
            margin: 0,
            maxWidth: '52ch',
            fontFamily: 'var(--obs-sans)',
            fontSize: '15px',
            lineHeight: 1.55,
            color: 'var(--obs-ink-3)',
          }}
        >
          {body}
        </p>
      ) : null}

      {reason ? (
        <p
          data-empty-reason="true"
          style={{
            margin: 0,
            maxWidth: '52ch',
            fontFamily: 'var(--obs-mono)',
            fontSize: '12px',
            lineHeight: 1.5,
            letterSpacing: '0.02em',
            color: 'var(--obs-ink-4)',
            overflowWrap: 'anywhere',
          }}
        >
          {reason}
        </p>
      ) : null}

      {action ? <div style={{ marginTop: '4px' }}>{action}</div> : null}
    </div>
  )
}

export default EmptyState
