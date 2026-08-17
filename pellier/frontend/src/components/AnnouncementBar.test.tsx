import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LIVE_FLOOR_FINDINGS } from '../copy'
import AnnouncementBar from './AnnouncementBar'

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('AnnouncementBar', () => {
  it('does not announce automatic rotations through a live region', () => {
    render(<AnnouncementBar />)
    expect(screen.getByTestId('announcement-bar')).not.toHaveAttribute('aria-live')
  })

  it('stays on the first message when reduced motion is requested', () => {
    vi.useFakeTimers()
    vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))

    render(<AnnouncementBar />)
    expect(screen.getByText(LIVE_FLOOR_FINDINGS[0].text)).toBeInTheDocument()

    vi.advanceTimersByTime(10_000)
    expect(screen.getByText(LIVE_FLOOR_FINDINGS[0].text)).toBeInTheDocument()
  })
})
