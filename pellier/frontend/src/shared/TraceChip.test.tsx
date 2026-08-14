import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TraceChip } from './TraceChip'

describe('TraceChip', () => {
  it('links a trace chip to its Pellier Labs explainer', () => {
    render(<TraceChip tool="memory.recall" linkToAgentTrace />)

    expect(screen.getByTestId('trace-chip-memory.recall')).toHaveAttribute(
      'href',
      '/pellier-labs/proof-board#runtime-gateway-policy',
    )
  })
})
