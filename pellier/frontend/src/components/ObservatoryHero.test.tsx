/**
 * ObservatoryHero tests — editorial hero above the /workshop split.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ObservatoryHero from './ObservatoryHero'

describe('ObservatoryHero', () => {
  it('renders the display title and italic epigraph', () => {
    render(<ObservatoryHero />)
    expect(screen.getByText(/^Pellier Observatory\.$/)).toBeInTheDocument()
    expect(screen.getByText(/Where Agents think aloud/)).toBeInTheDocument()
  })

  it('renders the PELLIER OBSERVATORY · NO. 06 kicker by default', () => {
    render(<ObservatoryHero />)
    expect(screen.getByText(/PELLIER OBSERVATORY · NO\. 06/)).toBeInTheDocument()
  })

  it('respects editionNumber prop and zero-pads single digits', () => {
    render(<ObservatoryHero editionNumber={3} />)
    expect(screen.getByText(/PELLIER OBSERVATORY · NO\. 03/)).toBeInTheDocument()
  })
})
