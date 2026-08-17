import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import BoutiqueSpotlight from './BoutiqueSpotlight'

describe('BoutiqueSpotlight', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  it('guides a first visit through three concise steps', () => {
    render(<BoutiqueSpotlight />)

    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true')
    expect(
      screen.getByRole('heading', { name: 'Choose the point of view' }),
    ).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Step / })).toHaveLength(3)

    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(screen.getByRole('heading', { name: 'Ask Pellier' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(
      screen.getByRole('heading', { name: 'Verify the answer' }),
    ).toBeInTheDocument()
  })

  it('respects dismissal for the rest of the browser session', () => {
    const { unmount } = render(<BoutiqueSpotlight />)

    fireEvent.click(screen.getByRole('button', { name: 'Skip tour' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(
      window.sessionStorage.getItem('pellier-storefront-spotlight-seen'),
    ).toBe('true')

    unmount()
    const { container } = render(<BoutiqueSpotlight />)
    expect(container).toBeEmptyDOMElement()
  })

  it('contains keyboard focus and restores it after dismissal', () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    trigger.focus()

    render(<BoutiqueSpotlight />)
    const stepButtons = screen.getAllByRole('button', { name: /Step / })
    const next = screen.getByRole('button', { name: 'Next' })
    next.focus()
    fireEvent.keyDown(window, { key: 'Tab' })
    expect(stepButtons[0]).toHaveFocus()

    fireEvent.click(screen.getByRole('button', { name: 'Skip tour' }))
    expect(trigger).toHaveFocus()
    trigger.remove()
  })
})
