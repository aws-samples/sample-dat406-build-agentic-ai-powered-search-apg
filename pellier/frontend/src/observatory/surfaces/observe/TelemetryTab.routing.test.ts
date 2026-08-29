import { describe, expect, it } from 'vitest'

import { canonicalRoutingPattern } from './TelemetryTab'

describe('Telemetry routing compatibility', () => {
  it('does not relabel legacy Agents-as-Tools traces as Dispatcher', () => {
    expect(canonicalRoutingPattern('Agents as Tools')).toBeNull()
    expect(canonicalRoutingPattern('Dispatcher')).toBe('Dispatcher')
    expect(canonicalRoutingPattern('Strands Graph')).toBe('Graph')
  })
})
