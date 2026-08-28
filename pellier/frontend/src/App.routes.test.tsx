import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

/** Read a source file from the project root, for structural assertions. */
function readSource(relative: string): string {
  return readFileSync(resolve(process.cwd(), relative), 'utf8')
}

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

describe('surface boundaries', () => {
  // The shopper's Ask Pellier drawer was mounted on every route, so its
  // "Continue chat" pill floated over Pellier Operator whenever the browser held a
  // storefront thread. Operator is a different product with its own Concierge.
  it('keeps the shopper chat drawer off the Operator console', () => {
    const source = readSource('src/App.tsx')
    expect(source).toContain('function ShopperChatSlot()')
    expect(source).toContain("if (pathname.startsWith('/operator')) return null")
    expect(source).toContain('<ShopperChatSlot />')
    // Mounted through the slot only, never directly.
    expect(source.match(/<ChatDrawer \/>/g)?.length).toBe(1)
  })

  it('still mounts it on the storefront and the Observatory', () => {
    const source = readSource('src/App.tsx')
    const start = source.indexOf('function ShopperChatSlot()')
    // To the end of the function, not to the first "}" - which closes the JSX guard.
    const body = source.slice(start, source.indexOf('\n}', start))
    // Exactly one route prefix is excluded, and it is not the Observatory.
    expect(body.match(/startsWith\(/g)?.length).toBe(1)
    expect(body).toContain("startsWith('/operator')")
    expect(body).not.toContain("startsWith('/observatory')")
  })
})
