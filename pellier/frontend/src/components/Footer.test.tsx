/**
 * Footer tests — brand + three live columns + bottom strip.
 *
 * The previous footer spec (five columns, newsletter form, Privacy/
 * Terms/Accessibility bottom strip) was frozen around placeholder
 * links. This rewrite replaces it with a living spec:
 *
 *   - Four sections only: Brand, Explore, Storyboard, Pellier Labs.
 *   - Every Explore link points at a real router route.
 *   - Storyboard + Pellier Labs each carry an italic blurb and a single
 *     call-to-action link to `/storyboard` / `/pellier-labs`.
 *   - Bottom strip shows the copyright line and a signature tag.
 *     No placeholder Privacy/Terms/Accessibility links.
 */
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import Footer from './Footer'
import { FOOTER } from '../copy'

function renderFooter() {
  return render(
    <MemoryRouter>
      <Footer />
    </MemoryRouter>,
  )
}

describe('Footer — four live columns', () => {
  it('renders exactly four column sections in order', () => {
    renderFooter()
    const container = screen.getByTestId('footer-columns')
    const regions = within(container).getAllByRole('region', { hidden: true })
    expect(regions).toHaveLength(4)
    expect(screen.getByTestId('footer-column-brand')).toBeInTheDocument()
    expect(screen.getByTestId('footer-column-explore')).toBeInTheDocument()
    expect(screen.getByTestId('footer-column-storyboard')).toBeInTheDocument()
    expect(screen.getByTestId('footer-column-agent-trace')).toBeInTheDocument()
  })

  it('renders the brand column with the tagline from copy.ts', () => {
    renderFooter()
    expect(screen.getByTestId('footer-brand-tagline')).toHaveTextContent(
      FOOTER.BRAND.TAGLINE,
    )
  })

  it('renders every Explore link pointing at a real route', () => {
    renderFooter()
    const explore = screen.getByTestId('footer-column-explore')
    FOOTER.EXPLORE.ITEMS.forEach(({ label, href }) => {
      const link = within(explore).getByText(label).closest('a')
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', href)
    })
  })

  it('renders Storyboard column with italic blurb + "Read the latest" CTA linking to /storyboard', () => {
    renderFooter()
    const col = screen.getByTestId('footer-column-storyboard')
    expect(within(col).getByText(FOOTER.STORYBOARD.COPY)).toBeInTheDocument()
    const cta = within(col).getByTestId('footer-column-storyboard-cta')
    expect(cta).toHaveAttribute('href', '/storyboard')
    expect(cta).toHaveTextContent(FOOTER.STORYBOARD.CTA_LABEL)
  })

  it('renders Pellier Labs column with italic blurb + "Open Pellier Labs" CTA linking to /pellier-labs', () => {
    renderFooter()
    const col = screen.getByTestId('footer-column-agent-trace')
    expect(within(col).getByText(FOOTER.AGENT_TRACE.COPY)).toBeInTheDocument()
    const cta = within(col).getByTestId('footer-column-agent-trace-cta')
    expect(cta).toHaveAttribute('href', '/pellier-labs')
    expect(cta).toHaveTextContent(FOOTER.AGENT_TRACE.CTA_LABEL)
  })
})

describe('Footer — bottom strip', () => {
  it('renders the copyright line with the current year', () => {
    renderFooter()
    const strip = screen.getByTestId('footer-bottom-strip')
    const copyright = within(strip).getByTestId('footer-copyright')
    expect(copyright.textContent).toContain(FOOTER.BOTTOM_STRIP.COPYRIGHT)
    expect(copyright.textContent).toContain(String(new Date().getFullYear()))
  })

  it('renders the attribution credit', () => {
    renderFooter()
    const strip = screen.getByTestId('footer-bottom-strip')
    expect(within(strip).getByTestId('footer-attribution')).toHaveTextContent(
      FOOTER.BOTTOM_STRIP.ATTRIBUTION,
    )
  })

  it('does not render Privacy / Terms / Accessibility placeholder links', () => {
    renderFooter()
    const strip = screen.getByTestId('footer-bottom-strip')
    // Explicit negative assertion: the placeholder links the earlier
    // footer shipped with should not surface in the rewrite.
    expect(within(strip).queryByText('Privacy')).not.toBeInTheDocument()
    expect(within(strip).queryByText('Terms')).not.toBeInTheDocument()
    expect(within(strip).queryByText('Accessibility')).not.toBeInTheDocument()
  })
})

describe('Footer — masthead, demo payment strip, and service badges', () => {
  it('renders the brand lockup in the masthead', () => {
    renderFooter()
    const masthead = screen.getByTestId('footer-masthead')
    expect(within(masthead).getByText('Pellier')).toBeInTheDocument()
  })

  it('renders what this storefront is, as discrete badges', () => {
    renderFooter()
    const list = screen.getByTestId('footer-service-items')
    FOOTER.BOTTOM_STRIP.SERVICE_ITEMS.forEach((item) => {
      expect(within(list).getByText(item)).toBeInTheDocument()
    })
  })

  it('renders official marks inside the disclosed demo contract', () => {
    renderFooter()
    expect(screen.getByTestId('footer-checkout-label')).toHaveTextContent(
      FOOTER.CHECKOUT.LABEL,
    )
    const methods = screen.getByRole('list', {
      name: FOOTER.CHECKOUT.ARIA_LABEL,
    })
    expect(
      within(methods)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(FOOTER.CHECKOUT.PAYMENT_METHODS.map(({ label }) => label))
    expect(
      [...methods.querySelectorAll('img')].map((image) =>
        image.getAttribute('src'),
      ),
    ).toEqual(
      FOOTER.CHECKOUT.PAYMENT_METHODS.map(
        ({ id }) => `/assets/icons/payment/${id}.svg`,
      ),
    )
    expect(
      [...methods.querySelectorAll('img')].map((image) =>
        image.getAttribute('height'),
      ),
    ).toEqual(['20', '20', '20', '20', '20', '20'])
    for (const item of within(methods).getAllByRole('listitem')) {
      expect(item).toHaveClass('h-9', 'px-2.5')
    }
    for (const image of methods.querySelectorAll('img')) {
      expect(image).toHaveAttribute('alt', '')
      expect(image).toHaveAttribute('aria-hidden', 'true')
    }
    expect(methods.textContent).not.toMatch(/hsa|fsa|eligible/i)
  })
})

describe('Footer — disclaimer and licence', () => {
  it('states that nothing is charged and the catalog is synthetic', () => {
    renderFooter()
    expect(screen.getByTestId('footer-disclaimer')).toHaveTextContent(
      FOOTER.DISCLAIMER,
    )
  })

  it('renders the copyright holder and the real licence', () => {
    renderFooter()
    const legal = screen.getByTestId('footer-legal')
    expect(legal).toHaveTextContent(FOOTER.BOTTOM_STRIP.RIGHTS)
    expect(legal).toHaveTextContent(FOOTER.BOTTOM_STRIP.LICENSE)
  })

  it('does not claim MIT-0, which the repository NOTICE rules out', () => {
    // NOTICE: "released under the MIT License (NOT MIT-0). Attribution is a
    // condition of reuse, not a courtesy."
    renderFooter()
    const text = screen.getByTestId('footer').textContent ?? ''
    expect(text).not.toContain('MIT-0')
    expect(text).toContain('MIT License')
  })
})
