// @vitest-environment node

import { describe, expect, it } from 'vitest'
import config from './vite.config'

describe('local API proxy', () => {
  it('uses the isolated local backend and preserves the browser host for OAuth', () => {
    const proxy = config.server?.proxy
    const apiProxy =
      proxy && typeof proxy === 'object' && '/api' in proxy
        ? proxy['/api']
        : undefined

    expect(apiProxy).toMatchObject({
      target: 'http://127.0.0.1:8003',
      changeOrigin: false,
    })
  })
})
