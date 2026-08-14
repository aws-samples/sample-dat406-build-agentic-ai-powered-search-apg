import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { LegacyLabsRedirect } from './App'

function LocationProbe() {
  const { pathname, search, hash } = useLocation()
  return <output data-testid="location">{`${pathname}${search}${hash}`}</output>
}

describe('Pellier Labs route aliases', () => {
  it.each([
    {
      legacyPrefix: '/agent-trace' as const,
      from: '/agent-trace/proof-board?turn=turn-7#managed-rail',
      to: '/pellier-labs/proof-board?turn=turn-7#managed-rail',
    },
    {
      legacyPrefix: '/labs' as const,
      from: '/labs/sessions/session-4/telemetry?trace=trace-2',
      to: '/pellier-labs/sessions/session-4/telemetry?trace=trace-2',
    },
  ])('redirects $from to the canonical Pellier Labs URL', async ({
    legacyPrefix,
    from,
    to,
  }) => {
    render(
      <MemoryRouter initialEntries={[from]}>
        <Routes>
          <Route
            path={`${legacyPrefix}/*`}
            element={<LegacyLabsRedirect legacyPrefix={legacyPrefix} />}
          />
          <Route path="/pellier-labs/*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByTestId('location')).toHaveTextContent(to)
  })
})
