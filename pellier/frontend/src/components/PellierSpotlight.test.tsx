import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import PellierSpotlight from './PellierSpotlight'

describe('PellierSpotlight', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  it('matches the governed four-step welcome tour', () => {
    render(<PellierSpotlight />)

    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true')
    expect(
      screen.getByRole('heading', { name: 'Begin with the edit.' }),
    ).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Show / })).toHaveLength(4)

    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(screen.getByRole('button', { name: 'Show Personalize' })).toHaveAttribute(
      'aria-current',
      'step',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(screen.getByRole('button', { name: 'Show Ask' })).toHaveAttribute(
      'aria-current',
      'step',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(screen.getByRole('button', { name: 'Show Inspect' })).toHaveAttribute(
      'aria-current',
      'step',
    )
  })

  it('respects dismissal for the rest of the browser session', () => {
    const { unmount } = render(<PellierSpotlight />)

    fireEvent.click(screen.getByRole('button', { name: 'Skip welcome tour' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(
      window.sessionStorage.getItem('pellier-storefront-spotlight-seen'),
    ).toBe('true')

    unmount()
    const { container } = render(<PellierSpotlight />)
    expect(container).toBeEmptyDOMElement()
  })

  it('contains keyboard focus and restores it after dismissal', () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    trigger.focus()

    render(<PellierSpotlight />)
    const close = screen.getByRole('button', { name: 'Skip welcome tour' })
    const next = screen.getByRole('button', { name: 'Continue' })
    next.focus()
    fireEvent.keyDown(window, { key: 'Tab' })
    expect(close).toHaveFocus()

    fireEvent.click(close)
    expect(trigger).toHaveFocus()
    trigger.remove()
  })
})
