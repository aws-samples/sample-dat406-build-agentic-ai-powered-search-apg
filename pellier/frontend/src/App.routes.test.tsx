import { render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('./pages/PellierStorefront', () => ({
  default: () => <div>Storefront route</div>,
}))

vi.mock('./agent-trace/shell/AgentTraceFrame', async () => {
  const { Outlet } = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  )
  return {
    default: () => (
      <div>
        Labs frame
        <Outlet />
      </div>
    ),
  }
})

vi.mock('./agent-trace/surfaces/observe/PellierLabsWorkbench', () => ({
  default: () => <div>Pellier Labs workbench</div>,
}))

vi.mock('./agent-trace/surfaces/ReferencesIndex', () => ({
  default: () => <div>Optional deep dives index</div>,
}))

import { AppRoutes, isPellierSurfacePath } from './App'

function LocationProbe() {
  const { pathname, search, hash } = useLocation()
  return <output data-testid="location">{`${pathname}${search}${hash}`}</output>
}

function renderRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('canonical application routes', () => {
  it.each([
    '/',
    '/storyboard',
    '/about',
    '/discover',
    '/pellier-labs',
  ])('uses the shared Pellier surface on %s', (path) => {
    expect(isPellierSurfacePath(path)).toBe(true)
  })

  it('renders Pellier Labs only at the canonical route', async () => {
    renderRoute('/pellier-labs?turn=live#journey')

    expect(
      await screen.findByText('Pellier Labs workbench'),
    ).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/pellier-labs?turn=live#journey',
    )
    expect(document.body).toHaveClass('pellier-surface')
  })

  it('renders the optional deep dives index at its canonical route', async () => {
    renderRoute('/pellier-labs/references')

    expect(await screen.findByText('Optional deep dives index')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/pellier-labs/references',
    )
  })

  it.each([
    ['/agent-trace', '/pellier-labs'],
    ['/agent-trace/proof-board?turn=live#managed', '/pellier-labs/proof-board?turn=live#managed'],
    ['/labs', '/pellier-labs'],
  ])(
    'redirects the retired %s route to %s',
    async (path, expected) => {
      renderRoute(path)

      expect(await screen.findByText('Labs frame')).toBeInTheDocument()
      expect(screen.getByTestId('location')).toHaveTextContent(expected)
    },
  )
})
