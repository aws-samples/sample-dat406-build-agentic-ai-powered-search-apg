import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TraceChip } from './TraceChip'

describe('TraceChip', () => {
  it('preserves the Pellier trace context in an Observatory link', () => {
    render(<TraceChip tool="memory.recall" linkToObservatory />)

    expect(screen.getByTestId('trace-chip-memory.recall')).toHaveAttribute(
      'href',
      '/observatory/proof-board?from=pellier&trace=memory.recall#runtime-gateway-policy',
    )
  })
})
