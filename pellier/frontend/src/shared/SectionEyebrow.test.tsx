/**
 * SectionEyebrow contract.
 *
 * The whole point of the primitive is that one recipe replaces five, so the
 * recipe itself is what is asserted: sans, 11px, 600, 0.08em, uppercase. A
 * snapshot would pass while someone quietly moved it to mono at 10px, which is
 * exactly the drift this component exists to end.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SectionEyebrow } from './SectionEyebrow'

describe('SectionEyebrow', () => {
  it('renders the one recipe: sans 11/600/0.08em uppercase', () => {
    render(<SectionEyebrow data-testid="eyebrow">Reference views</SectionEyebrow>)

    expect(screen.getByTestId('eyebrow')).toHaveStyle({
      fontFamily: 'var(--obs-heading)',
      fontSize: '11px',
      fontWeight: '600',
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
    })
  })

  it('never renders in the monospace register', () => {
    // Mono on these surfaces means "identifier, table, duration". A section
    // label is none of those, and spending mono on labels is what left the
    // real identifiers with nothing to distinguish them.
    render(<SectionEyebrow data-testid="eyebrow">Namespace pattern</SectionEyebrow>)

    const style = screen.getByTestId('eyebrow').getAttribute('style') ?? ''
    expect(style).not.toMatch(/mono/)
  })

  it('separates the two tones by colour and reports which one it used', () => {
    const { unmount } = render(
      <SectionEyebrow data-testid="brand">Evidence</SectionEyebrow>,
    )
    const brand = screen.getByTestId('brand')
    expect(brand).toHaveAttribute('data-tone', 'brand')
    expect(brand).toHaveStyle({ color: 'var(--pellier-burgundy)' })
    unmount()

    render(
      <SectionEyebrow tone="muted" data-testid="muted">
        Evidence
      </SectionEyebrow>,
    )
    const muted = screen.getByTestId('muted')
    expect(muted).toHaveAttribute('data-tone', 'muted')
    expect(muted).toHaveStyle({ color: 'var(--obs-ink-4)' })
  })

  it('hides the dot from assistive technology and can drop it entirely', () => {
    const { container, unmount } = render(
      <SectionEyebrow>What ran?</SectionEyebrow>,
    )
    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(1)
    unmount()

    const { container: noDot } = render(
      <SectionEyebrow dot={false}>What ran?</SectionEyebrow>,
    )
    expect(noDot.querySelectorAll('[aria-hidden="true"]')).toHaveLength(0)
  })

  it('keeps the label readable as text, not as an image of text', () => {
    render(<SectionEyebrow data-testid="eyebrow">Reference views</SectionEyebrow>)
    // Uppercase is presentational: the accessible text stays as authored.
    expect(screen.getByTestId('eyebrow')).toHaveTextContent('Reference views')
  })
})
