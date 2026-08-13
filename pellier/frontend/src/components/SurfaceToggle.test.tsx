/**
 * SurfaceToggle tests — global Boutique ↔ Agent Trace segmented control.
 *
 * Covers:
 *   - Both segments render with the correct labels + testids.
 *   - The active segment reflects the current route (/ → storefront,
 *     /agent-trace → agentTrace, /agent-trace/x → agentTrace).
 *   - The inactive segment links to the other surface.
 *   - aria-current + data-active are only set on the active segment.
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import SurfaceToggle from './SurfaceToggle'
import { SURFACE_TOGGLE } from '../copy'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <SurfaceToggle />
    </MemoryRouter>,
  )
}

describe('SurfaceToggle — render', () => {
  it('renders both segments with the canonical copy', () => {
    renderAt('/')
    const storefront = screen.getByTestId('surface-toggle-storefront')
    const agentTrace = screen.getByTestId('surface-toggle-agent-trace')
    expect(storefront).toHaveTextContent(SURFACE_TOGGLE.STOREFRONT)
    expect(agentTrace).toHaveTextContent(SURFACE_TOGGLE.AGENT_TRACE)
  })

  it('wraps the group with an aria-label for assistive tech', () => {
    renderAt('/')
    const group = screen.getByTestId('surface-toggle')
    expect(group.getAttribute('aria-label')).toBe(SURFACE_TOGGLE.ARIA_LABEL)
    expect(group.getAttribute('role')).toBe('group')
  })
})

describe('SurfaceToggle — active state reflects route', () => {
  it('marks Boutique active on /', () => {
    renderAt('/')
    expect(
      screen.getByTestId('surface-toggle-storefront').getAttribute('data-active'),
    ).toBe('true')
    expect(
      screen.getByTestId('surface-toggle-storefront').getAttribute('aria-current'),
    ).toBe('page')
    expect(
      screen.getByTestId('surface-toggle-agent-trace').getAttribute('data-active'),
    ).toBe('false')
  })

  it('marks Agent Trace active on /agent-trace', () => {
    renderAt('/agent-trace')
    expect(
      screen.getByTestId('surface-toggle-agent-trace').getAttribute('data-active'),
    ).toBe('true')
    expect(
      screen.getByTestId('surface-toggle-storefront').getAttribute('data-active'),
    ).toBe('false')
  })

  it('treats /agent-trace subroutes as agentTrace', () => {
    renderAt('/agent-trace/something-deep')
    expect(
      screen.getByTestId('surface-toggle-agent-trace').getAttribute('data-active'),
    ).toBe('true')
  })
})

describe('SurfaceToggle — links to the correct target surface', () => {
  it('agentTrace segment links to /agent-trace', () => {
    renderAt('/')
    expect(
      screen.getByTestId('surface-toggle-agent-trace').getAttribute('href'),
    ).toBe('/agent-trace')
  })

  it('storefront segment links to /', () => {
    renderAt('/agent-trace')
    expect(
      screen.getByTestId('surface-toggle-storefront').getAttribute('href'),
    ).toBe('/')
  })
})
