// @vitest-environment node

import { describe, expect, it } from 'vitest'
import config from './vite.config'

describe('local API proxy', () => {
  it('preserves the browser host for the OAuth entrypoint', () => {
    const proxy = config.server?.proxy
    const apiProxy =
      proxy && typeof proxy === 'object' && '/api' in proxy
        ? proxy['/api']
        : undefined

    expect(apiProxy).toMatchObject({ changeOrigin: false })
  })
})
