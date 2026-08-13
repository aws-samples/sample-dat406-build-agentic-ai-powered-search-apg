/**
 * AgentTraceHero tests — editorial hero above the /workshop split.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import AgentTraceHero from './AgentTraceHero'

describe('AgentTraceHero', () => {
  it('renders the display title and italic epigraph', () => {
    render(<AgentTraceHero />)
    expect(screen.getByText(/^Pellier Labs\.$/)).toBeInTheDocument()
    expect(screen.getByText(/Where agents think aloud/)).toBeInTheDocument()
  })

  it('renders the PELLIER LABS · NO. 06 kicker by default', () => {
    render(<AgentTraceHero />)
    expect(screen.getByText(/PELLIER LABS · NO\. 06/)).toBeInTheDocument()
  })

  it('respects editionNumber prop and zero-pads single digits', () => {
    render(<AgentTraceHero editionNumber={3} />)
    expect(screen.getByText(/PELLIER LABS · NO\. 03/)).toBeInTheDocument()
  })
})
