import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ResponsiveImage from './ResponsiveImage'

describe('ResponsiveImage', () => {
  it('falls back to the original local image when a generated variant fails', () => {
    const { container } = render(
      <ResponsiveImage
        src="/products/marco-merino-travel-socks.png"
        alt="Merino Travel Socks"
      />,
    )

    expect(container.querySelectorAll('source')).toHaveLength(2)
    fireEvent.error(screen.getByRole('img', { name: 'Merino Travel Socks' }))

    expect(container.querySelectorAll('source')).toHaveLength(0)
    expect(screen.getByRole('img', { name: 'Merino Travel Socks' })).toHaveAttribute(
      'src',
      '/products/marco-merino-travel-socks.png',
    )
  })

  it('forwards errors when the original image also fails', () => {
    const onError = vi.fn()
    const { container } = render(
      <ResponsiveImage
        src="/products/missing.png"
        alt="Missing product"
        onError={onError}
      />,
    )

    fireEvent.error(screen.getByRole('img', { name: 'Missing product' }))
    expect(container.querySelectorAll('source')).toHaveLength(0)

    fireEvent.error(screen.getByRole('img', { name: 'Missing product' }))
    expect(onError).toHaveBeenCalledTimes(1)
  })
})
