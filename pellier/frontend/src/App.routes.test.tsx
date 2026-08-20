import { render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('./pages/PellierPage', () => ({
  default: () => <div>Storefront route</div>,
}))

vi.mock('./observatory/shell/ObservatoryFrame', async () => {
  const { Outlet } = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  )
  return {
    default: () => (
      <div>
        Observatory frame
        <Outlet />
      </div>
    ),
  }
})

vi.mock('./observatory/surfaces/observe/ObservatoryWorkbench', () => ({
  default: () => <div>Pellier Observatory workbench</div>,
}))

vi.mock('./observatory/surfaces/ReferencesIndex', () => ({
  default: () => <div>Optional deep dives index</div>,
}))

vi.mock('./pages/ProductDetailPage', () => ({
  default: () => <div>Product detail route</div>,
}))

import { AppRoutes } from './App'

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
  it('renders Pellier Observatory only at the canonical route', async () => {
    renderRoute('/observatory?turn=live#journey')

    expect(
      await screen.findByText('Pellier Observatory workbench'),
    ).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/observatory?turn=live#journey',
    )
  })

  it('renders the optional deep dives index at its canonical route', async () => {
    renderRoute('/observatory/references')

    expect(await screen.findByText('Optional deep dives index')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/observatory/references',
    )
  })

  it('serves one piece at its own deep-linkable route', async () => {
    renderRoute('/product/11')

    expect(await screen.findByText('Product detail route')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/product/11')
  })

  // Every path the surface has lived at. A rename sweep once rewrote this
  // table's inputs to the new path, leaving it asserting /observatory ->
  // /observatory: green, and blind to a redirect that pointed at itself.
  // These inputs are legacy by definition and must never be updated to the
  // current path — that is the whole point of the assertion.
  it.each([
    ['/agent-trace', '/observatory'],
    ['/agent-trace/proof-board', '/observatory/proof-board'],
    ['/pellier-labs', '/observatory'],
    ['/pellier-labs/tools', '/observatory/tools'],
    ['/labs', '/observatory'],
    ['/labs/proof-board?turn=live#managed', '/observatory/proof-board?turn=live#managed'],
  ])('redirects the retired %s to %s', async (path, expected) => {
    renderRoute(path)

    expect(await screen.findByText('Observatory frame')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(expected)
  })

  it('serves the current surface path without redirecting', async () => {
    renderRoute('/observatory/proof-board?turn=live#managed')

    expect(await screen.findByText('Observatory frame')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/observatory/proof-board?turn=live#managed',
    )
  })
})
