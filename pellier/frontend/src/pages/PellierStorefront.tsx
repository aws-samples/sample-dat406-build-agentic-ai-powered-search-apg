/**
 * PellierStorefront — the `/` route composition (Pellier redesign).
 *
 * Two-act layout:
 *
 *   ACT 1 (above the fold — full viewport):
 *     Header (sticky) → PellierHero (full-height search surface)
 *
 *   ACT 2 (below the fold — scroll to discover):
 *     Featured product image (weekender bag) + "Weekend, re:defined."
 *     → 8 remaining products in a staggered grid
 *     → "Because you asked..." editorial cards
 *     → Footer
 *
 * The hero occupies the entire viewport so the first impression is
 * the search bar. Scrolling reveals the editorial product showcase.
 */
import { useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import AnnouncementBar from '../components/AnnouncementBar'
import Header, { type NavItem } from '../components/Header'
import PellierHero from '../components/PellierHero'
import PellierCollections from '../components/PellierCollections'
import BecauseYouAsked from '../components/BecauseYouAsked'
import MemoryHandoffCard from '../components/MemoryHandoffCard'
import RationaleBand from '../components/RationaleBand'
import ProductCard from '../components/ProductCard'
import ResponsiveImage from '../components/ResponsiveImage'
import Footer from '../components/Footer'
import PellierSpotlight from '../components/PellierSpotlight'
// CommandPill removed — hero search bar is the primary entry point
import { useAuth } from '../contexts/AuthContext'
import { useCart } from '../contexts/CartContext'
import { usePersona } from '../contexts/PersonaContext'
import { useUI } from '../contexts/UIContext'
import {
  SHOWCASE_PRODUCTS,
  FRESH_PRODUCTS,
  MARCO_PRODUCTS,
  ANNA_PRODUCTS,
  THEO_PRODUCTS,
} from '../data/showcaseProducts'

const PERSONA_PRODUCTS: Record<string, typeof SHOWCASE_PRODUCTS> = {
  fresh: FRESH_PRODUCTS,
  marco: MARCO_PRODUCTS,
  anna: ANNA_PRODUCTS,
  theo: THEO_PRODUCTS,
}
import {
  PERSONA_INTERESTS,
  rankProductsForPersona,
  featuredProductIdForPersona,
  weekendEditForPersona,
} from '../data/personaCurations'
import { splitHeadlineAtRe } from '../utils/headlineAccent'

const NAV_ROUTES: Record<NavItem, string> = {
  home: '/',
  shop: '/#shop',
  storyboard: '/storyboard',
  stories: '/storyboard',
  discover: '/discover',
  about: '/about',
  account: '/',
  'ask-pellier': '/',
}

// Featured product + grid are now persona-aware (computed inside component)

export default function PellierStorefront() {
  const { prefsVersion } = useAuth()
  const { openModal, setChatSurface } = useUI()
  const { addToCart } = useCart()
  const { persona } = usePersona()
  const navigate = useNavigate()

  // Persona-aware featured product + grid ordering + weekend edit.
  const personaId = persona?.id ?? null

  // Each persona sees ONLY their 9 products — zero overlap
  const personaProducts = PERSONA_PRODUCTS[personaId ?? 'fresh'] ?? FRESH_PRODUCTS

  const featuredProduct = useMemo(() => {
    const fid = featuredProductIdForPersona(personaId)
    return personaProducts.find(p => p.id === fid) ?? personaProducts[0]
  }, [personaId, personaProducts])

  const gridProducts = useMemo(
    () => personaProducts.filter(p => p.id !== featuredProduct.id),
    [personaProducts, featuredProduct],
  )

  const weekendEdit = weekendEditForPersona(personaId)
  const weekendHeadlineParts = splitHeadlineAtRe(weekendEdit.headline)

  const rankedGridProducts = useMemo(
    () => rankProductsForPersona(gridProducts, personaId),
    [gridProducts, personaId],
  )
  const personaInterests = personaId ? PERSONA_INTERESTS[personaId] : undefined
  const curatedHeadline =
    personaInterests?.curatedHeadline ?? 'Things worth discovering.'

  useEffect(() => {
    setChatSurface('drawer')
  }, [setChatSurface])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (window.location.hash === '#shop') {
      requestAnimationFrame(() => {
        document.getElementById('shop')?.scrollIntoView({ behavior: 'smooth' })
      })
    }
  }, [])

  const handleNavigate = (item: NavItem) => {
    if (item === 'account') {
      openModal('auth')
      return
    }
    if (item === 'home') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }
    if (item === 'shop') {
      document.getElementById('shop')?.scrollIntoView({ behavior: 'smooth' })
      return
    }
    if (item === 'ask-pellier') {
      // Open the concierge drawer — that's what "Ask Pellier" promises.
      openModal('drawer')
      return
    }
    const target = NAV_ROUTES[item]
    if (target) navigate(target)
  }

  const handleAddToBag = (product: typeof SHOWCASE_PRODUCTS[0]) =>
    addToCart({
      productId: product.id,
      name: product.name,
      price: product.price,
      image: product.imageUrl,
      origin: 'manual',
    })

  const handleOpenCatalog = () => {
    document.getElementById('shop')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="pellier-page-surface min-h-dvh bg-cream-50">
      {/* Announcement bar — full-width above the header */}
      <AnnouncementBar />

      <Header current="home" onNavigate={handleNavigate} />

      <main className="bg-cream">
        {/* ── ACT 1: Full-viewport hero ── */}
        <PellierHero />

        {/* Four local-image edits bring the catalog into the first scroll,
            matching the landing shell without adding another route. */}
        <PellierCollections onOpenCatalog={handleOpenCatalog} />

        {/* ── Profile handoff card — names the deterministic seed and
             session boundary before the participant generates memory or
             action evidence. ── */}
        <MemoryHandoffCard />

        {/* ── ACT 2: Below the fold ── */}
        <section
          id="shop"
          className="w-full"
          aria-label="Featured products"
          style={{
            scrollMarginTop: 84,
            background: 'var(--cream-warm)',
            borderTop: '1px solid var(--rule-1)',
          }}
        >
          {/* Featured product: large image + editorial title */}
          <div className="max-w-[1440px] mx-auto px-container-x pt-16 md:pt-24 pb-12">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
              {/* Left: featured image */}
              <div className="relative aspect-[4/5] rounded-[8px] overflow-hidden shadow-warm-md">
                <ResponsiveImage
                  src={featuredProduct.imageUrl}
                  alt={featuredProduct.name}
                  widths={[480, 960]}
                  sizes="(min-width: 1440px) 696px, (min-width: 1024px) 48vw, 100vw"
                  className="w-full h-full object-cover"
                  loading="lazy"
                  decoding="async"
                  pictureClassName="block h-full w-full"
                />
              </div>

              {/* Right: editorial title + product info */}
              <div className="flex flex-col justify-center py-8 lg:py-0">
                <h2
                  className="font-display"
                  style={{
                    fontSize: 'clamp(36px, 5vw, 64px)',
                    lineHeight: 1.08,
                    letterSpacing: 0,
                    fontWeight: 400,
                    whiteSpace: 'pre-line',
                  }}
                >
                  {weekendHeadlineParts.tail ? (
                    <>
                      <span className="text-espresso">{weekendHeadlineParts.lead}</span>
                      <span className="text-accent-ink">{weekendHeadlineParts.tail}</span>
                    </>
                  ) : (
                    <span className="text-espresso">{weekendHeadlineParts.lead}</span>
                  )}
                </h2>
                <p
                  className="mt-5 max-w-[440px] font-sans text-ink-soft"
                  style={{
                    fontSize: 'clamp(14px, 1.1vw, 16px)',
                    lineHeight: 1.65,
                  }}
                >
                  {weekendEdit.subheadline}
                </p>

                {/* Featured product details */}
                <div className="mt-8 pt-6 border-t border-sand/50">
                  <p className="mb-1 font-sans text-[12px] text-ink-quiet">
                    {featuredProduct.brand}
                  </p>
                  <p className="font-display text-xl text-espresso">
                    {featuredProduct.name}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-sm text-ink-soft font-sans">
                    <span className="text-espresso font-medium">${featuredProduct.price}</span>
                    <span>★ {featuredProduct.rating.toFixed(1)}</span>
                    <span className="text-ink-quiet">({featuredProduct.reviewCount})</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAddToBag(featuredProduct)}
                    className="mt-5 rounded-full bg-espresso text-cream-50 px-8 py-3 text-sm font-sans font-medium transition-colors duration-fade hover:bg-dusk cursor-pointer"
                  >
                    Add to bag
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Curated grid: 8 products, reordered by active persona.
              Fresh visitors get the canonical showcase sequence; Marco,
              Anna, and Theo see a tag-ranked ordering with a matching
              eyebrow + headline + "for <name>" chip so the
              personalization is visible rather than silent. */}
          <div className="max-w-[1440px] mx-auto px-container-x pb-16 md:pb-24">
            <div className="mb-8">
              <div>
                <h2
                  data-testid="curated-headline"
                  className="font-display text-espresso"
                  style={{
                    fontSize: 'clamp(28px, 3.5vw, 44px)',
                    lineHeight: 1.15,
                    letterSpacing: 0,
                    fontWeight: 400,
                  }}
                >
                  {curatedHeadline}
                </h2>
                <RationaleBand />
              </div>
            </div>

            <div
              // Re-mount on prefsVersion OR persona change so the grid's
              // per-card reveal animation re-fires for the new ordering.
              key={`${prefsVersion}-${personaId ?? 'fresh'}`}
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: '1.5rem',
              }}
            >
              {rankedGridProducts.map((product, index) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  index={index % 3}
                  onAddToBag={handleAddToBag}
                />
              ))}
            </div>
          </div>
        </section>

        {/* "Because you asked..." editorial cards */}
        <BecauseYouAsked />
      </main>

      <Footer />
      {/* CommandPill removed — hero search bar opens the drawer directly */}
      <PellierSpotlight />
    </div>
  )
}
