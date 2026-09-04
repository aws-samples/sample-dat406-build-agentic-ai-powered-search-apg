/**
 * EmptyState contract.
 *
 * Two things must hold or the primitive is pointless.
 *
 * The headline keeps the display face. On the Observatory that is fragile:
 * `base.css` forces every heading to sans with `!important`, and `index.css`
 * forces `.font-display` back to sans on top of that. A paragraph carrying an
 * inline family is the one form that survives both, so the test pins the tag
 * as well as the family.
 *
 * And the reason line stays monospace and separate from the prose, because it
 * is the part naming a source an attendee can go and query.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('sets the headline in the display face at 22 to 24px', () => {
    render(
      <EmptyState
        eyebrow="No telemetry"
        headline="No telemetry panels have been recorded for this session."
        data-testid="empty"
      />,
    )

    const headline = screen.getByText(
      'No telemetry panels have been recorded for this session.',
    )
    expect(headline).toHaveStyle({
      fontFamily: 'var(--display)',
      fontSize: 'clamp(22px, 2vw, 24px)',
      fontWeight: '400',
    })
  })

  it('renders the headline as a paragraph, not a heading', () => {
    // A heading here would be captured by the two !important family rules on
    // the Observatory and would render sans, and an empty state is not page
    // structure anyway.
    render(<EmptyState eyebrow="Empty" headline="Nothing was recorded." />)
    expect(screen.getByText('Nothing was recorded.').tagName).toBe('P')
    expect(screen.queryByRole('heading')).toBeNull()
  })

  it('opens with the eyebrow in the shared label recipe', () => {
    render(<EmptyState eyebrow="No telemetry" headline="Nothing yet." />)
    const eyebrow = screen.getByText('No telemetry')
    expect(eyebrow).toHaveAttribute('data-tone', 'muted')
    expect(eyebrow).toHaveStyle({ fontSize: '11px', fontWeight: '600' })
  })

  it('keeps the reason line in mono and apart from the prose', () => {
    render(
      <EmptyState
        eyebrow="No telemetry"
        headline="Nothing was recorded."
        body="Panels appear as the system processes each step."
        reason="pellier.observatory_spans: 0 rows for this session"
        data-testid="empty"
      />,
    )

    const reason = screen.getByText(
      'pellier.observatory_spans: 0 rows for this session',
    )
    expect(reason).toHaveAttribute('data-empty-reason', 'true')
    expect(reason).toHaveStyle({ fontFamily: 'var(--obs-mono)' })

    const body = screen.getByText(
      'Panels appear as the system processes each step.',
    )
    expect(body).toHaveStyle({ fontFamily: 'var(--obs-sans)' })
    expect(body).not.toHaveAttribute('data-empty-reason')
  })

  it('omits the optional slots entirely rather than reserving space', () => {
    const { container } = render(
      <EmptyState eyebrow="Empty" headline="Nothing was recorded." />,
    )
    expect(container.querySelector('[data-empty-reason]')).toBeNull()
    // eyebrow + headline only.
    expect(container.querySelectorAll('p')).toHaveLength(1)
  })

  it('renders the single action it is given', () => {
    render(
      <EmptyState
        eyebrow="Empty"
        headline="Nothing was recorded."
        action={<button type="button">Run a benchmark</button>}
      />,
    )
    expect(
      screen.getByRole('button', { name: 'Run a benchmark' }),
    ).toBeInTheDocument()
  })

  it('centres only when asked, and says which alignment it used', () => {
    const { unmount } = render(
      <EmptyState eyebrow="Empty" headline="Nothing." data-testid="empty" />,
    )
    expect(screen.getByTestId('empty')).toHaveAttribute('data-align', 'start')
    expect(screen.getByTestId('empty')).toHaveStyle({ textAlign: 'left' })
    unmount()

    render(
      <EmptyState
        eyebrow="Empty"
        headline="Nothing."
        align="center"
        data-testid="empty"
      />,
    )
    expect(screen.getByTestId('empty')).toHaveStyle({ textAlign: 'center' })
  })
})
