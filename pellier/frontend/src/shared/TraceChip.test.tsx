import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

describe('TraceChip', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('prefixes Agent Trace anchor links with the Vite base path', async () => {
    vi.stubEnv('BASE_URL', '/ports/8000/')
    const { TraceChip } = await import('./TraceChip')

    render(<TraceChip tool="memory.recall" linkToAgentTrace />)

    expect(screen.getByTestId('trace-chip-memory.recall')).toHaveAttribute(
      'href',
      '/ports/8000/agent-trace/proof-board#runtime-gateway-policy',
    )
  })
})
