import { afterEach, describe, expect, it, vi } from 'vitest'

describe('assetPath helpers', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('asset() leaves paths unchanged at root base', async () => {
    vi.stubEnv('BASE_URL', '/')
    const { asset } = await import('./assetPath')
    expect(asset('/products/hero.png')).toBe('/products/hero.png')
  })

  it('asset() prefixes workshop CloudFront base', async () => {
    vi.stubEnv('BASE_URL', '/ports/8000/')
    const { asset } = await import('./assetPath')
    expect(asset('/products/hero.png')).toBe('/ports/8000/products/hero.png')
  })

  it('routerBasename() is empty at root', async () => {
    vi.stubEnv('BASE_URL', '/')
    const { routerBasename } = await import('./assetPath')
    expect(routerBasename()).toBe('')
  })

  it('routerBasename() strips trailing slash for Workshop Studio', async () => {
    vi.stubEnv('BASE_URL', '/ports/8000/')
    const { routerBasename } = await import('./assetPath')
    expect(routerBasename()).toBe('/ports/8000')
  })

  it('routePath() prefixes in-app routes for plain anchors', async () => {
    vi.stubEnv('BASE_URL', '/ports/8000/')
    const { routePath } = await import('./assetPath')
    expect(routePath('/pellier-labs/memory')).toBe('/ports/8000/pellier-labs/memory')
  })

  it('responsiveImageSrcSet() builds base-aware local variants', async () => {
    vi.stubEnv('BASE_URL', '/ports/8000/')
    const { responsiveImageSrcSet } = await import('./assetPath')

    expect(
      responsiveImageSrcSet('/products/hero.png', [480, 960], 'avif'),
    ).toBe(
      '/ports/8000/products/hero-480.avif 480w, /ports/8000/products/hero-960.avif 960w',
    )
  })

  it('responsiveImageSrcSet() leaves remote images on their fallback', async () => {
    const { responsiveImageSrcSet } = await import('./assetPath')
    expect(
      responsiveImageSrcSet('https://example.com/product.png', [480], 'webp'),
    ).toBeUndefined()
  })
})
