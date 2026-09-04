/**
 * StateBadge contract.
 *
 * Inherited from PolicyDecisionBadge and asserted rather than assumed: the
 * label is always visible text, tones differ by glyph and not only by hue, and
 * absence of evidence is styled as neither success nor failure.
 *
 * Plus the shape rule the surfaces converge on: 4px, because a pill is
 * something you press and a state is something you read.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StateBadge } from './StateBadge'

describe('StateBadge', () => {
  it('always renders the state as visible text', () => {
    render(<StateBadge tone="ok" data-testid="badge">Shipped</StateBadge>)
    expect(screen.getByTestId('badge')).toHaveTextContent('Shipped')
  })

  it('gives each tone a distinct glyph, not one mark recoloured', () => {
    const glyphFor = (tone: Parameters<typeof StateBadge>[0]['tone']) => {
      const { container, unmount } = render(
        <StateBadge tone={tone}>State</StateBadge>,
      )
      const svg = container.querySelector('svg')
      const signature = svg?.innerHTML ?? ''
      unmount()
      return signature
    }

    const glyphs = [
      glyphFor('ok'),
      glyphFor('attention'),
      glyphFor('degraded'),
      glyphFor('neutral'),
      glyphFor('live'),
      glyphFor('fixture'),
      glyphFor('unavailable'),
    ]

    expect(glyphs.every((g) => g.length > 0)).toBe(true)
    expect(new Set(glyphs).size).toBe(glyphs.length)
  })

  it('reads 4px, not a pill: a state is read, a control is pressed', () => {
    render(<StateBadge data-testid="badge">Available</StateBadge>)
    expect(screen.getByTestId('badge')).toHaveStyle({
      borderRadius: 'var(--gov-radius-sm)',
    })
  })

  it('renders the label recipe: sans 11/600/0.08em uppercase', () => {
    render(<StateBadge data-testid="badge">Available</StateBadge>)
    expect(screen.getByTestId('badge')).toHaveStyle({
      fontFamily: 'var(--obs-heading)',
      fontSize: '11px',
      fontWeight: '600',
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
    })
  })

  it('does not colour absence of evidence as success or failure', () => {
    // `neutral` and `unavailable` both mean "no claim". Painting either one
    // green would assert a state nobody observed.
    for (const tone of ['neutral', 'unavailable'] as const) {
      const { unmount } = render(
        <StateBadge tone={tone} data-testid="badge">
          Not evaluated
        </StateBadge>,
      )
      const style = screen.getByTestId('badge').getAttribute('style') ?? ''
      expect(style).not.toMatch(/--obs-status-ok-fg|--gov-prov-live|--dl-err/)
      unmount()
    }
  })

  it('resolves status colour on a surface that does not define --obs-status-*', () => {
    // The `--obs-status-*` family is declared on `.observatory-root` only.
    // Without a fallback every badge on the Operator desk renders unstyled.
    render(<StateBadge tone="ok" data-testid="badge">Live</StateBadge>)
    const style = screen.getByTestId('badge').getAttribute('style') ?? ''
    expect(style).toMatch(/var\(--obs-status-ok-fg,\s*var\(--dl-ok\)\)/)
  })

  it('carries a longer claim to assistive technology when given one', () => {
    render(
      <StateBadge
        tone="live"
        description="Read from Aurora at request time"
        data-testid="badge"
      >
        Live
      </StateBadge>,
    )
    const badge = screen.getByTestId('badge')
    expect(badge).toHaveAttribute('title', 'Read from Aurora at request time')
    expect(badge).toHaveTextContent('Read from Aurora at request time')
  })

  it('reports its tone so a call site can be asserted without reading colour', () => {
    render(<StateBadge tone="degraded" data-testid="badge">Degraded</StateBadge>)
    expect(screen.getByTestId('badge')).toHaveAttribute('data-tone', 'degraded')
  })
})
