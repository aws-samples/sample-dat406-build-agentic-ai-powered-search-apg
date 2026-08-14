import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TraceChip } from './TraceChip'

describe('TraceChip', () => {
  it('preserves the Boutique trace context in an Agent Trace link', () => {
    render(<TraceChip tool="memory.recall" linkToAgentTrace />)

    expect(screen.getByTestId('trace-chip-memory.recall')).toHaveAttribute(
      'href',
      '/pellier-labs/proof-board?from=boutique&trace=memory.recall#runtime-gateway-policy',
    )
  })
})
