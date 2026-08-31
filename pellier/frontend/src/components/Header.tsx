/**
 * Header — Pellier sticky header.
 *
 * Centered "Pellier" wordmark — Fraunces (`font-display`) + circular P
 * chip; word one step above footer (`text-2xl` vs `text-xl`). Four left
 * nav items (Shop, Stories, Ask Pellier, About), and right cluster: search
 * IconButton, persona Avatar dropdown, bag IconButton with count badge, and
 * a direct link to Pellier Observatory.
 *
 * The persona Avatar dropdown replaces the old PersonaPill + PersonaModal
 * pattern. It calls `switchPersona` and `signOut` directly from `usePersona()`.
 *
 * Validates Requirements 4.3, 5.1, 5.2, 5.3, 5.4, 5.5, 15.3.
 *
 * Copy comes from `copy.ts`. Design tokens from `design/tokens.ts` and
 * Tailwind extended config.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useCart } from '../contexts/CartContext'
import { usePersona, type PersonaListItem } from '../contexts/PersonaContext'
import { useUI } from '../contexts/UIContext'
import { NAV } from '../copy'
import { Avatar } from '../design/primitives'
import { getPersonaPhoto } from '../data/personaPhotos'
import { MEMBERSHIP } from '../data/membership'
import { IconButton } from '../design/primitives'
import { ConciergeBell,
  Search,
  ShoppingBag,
  User as UserIcon,
  ChevronDown,
  LogOut,
  Menu,
  X,
  Telescope,
} from 'lucide-react'

// Keep old NavItem values for backward compatibility with consuming pages,
// plus new values for the redesigned nav.
export type NavItem =
  | 'home'
  | 'shop'
  | 'storyboard'
  | 'stories'
  | 'discover'
  | 'about'
  | 'account'
  | 'ask-pellier'

interface HeaderProps {
  /** Which nav item is the current page — gets the espresso highlight. Defaults to 'home'. */
  current?: NavItem
  /** Optional click handler fired when any nav link is activated. */
  onNavigate?: (item: NavItem) => void
}

/** The four nav items rendered in the redesigned header. */
const NAV_ITEMS: Array<{ item: NavItem; label: string }> = [
  { item: 'shop', label: NAV.SHOP },
  { item: 'stories', label: NAV.STORIES },
  { item: 'ask-pellier', label: NAV.ASK_PELLIER },
  { item: 'about', label: NAV.ABOUT },
]

const MENU_EASE: [number, number, number, number] = [0.16, 1, 0.3, 1]

// ---------------------------------------------------------------------------
// Wordmark
// ---------------------------------------------------------------------------

function Wordmark() {
  return (
    <Link
      to="/"
      data-testid="wordmark"
      aria-label={NAV.WORDMARK}
      className="flex items-center gap-2.5 select-none"
    >
      <span
        aria-hidden="true"
        className="pellier-logo-chip bg-espresso text-cream-50"
      >
        P
      </span>
      <span className="font-display text-2xl font-medium tracking-tight text-espresso">
        {NAV.WORDMARK}
      </span>
    </Link>
  )
}

// ---------------------------------------------------------------------------
// NavLink
// ---------------------------------------------------------------------------

interface NavLinkProps {
  item: NavItem
  label: string
  current: NavItem
  onClick?: (item: NavItem) => void
}

function NavLink({ item, label, current, onClick }: NavLinkProps) {
  const isCurrent = current === item
  return (
    <button
      type="button"
      data-nav-item={item}
      data-current={isCurrent ? 'true' : 'false'}
      aria-current={isCurrent ? 'page' : undefined}
      onClick={() => onClick?.(item)}
      className={[
        'text-[14px] transition-colors duration-fade ease-out',
        'hover:opacity-70 bg-transparent cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
        isCurrent ? 'text-espresso font-semibold' : 'text-ink-soft font-normal',
      ].join(' ')}
      style={{
        fontFamily: 'var(--sans)',
        padding: '6px 0',
      }}
    >
      {label}
    </button>
  )
}

function ObservatoryLink({
  mobile = false,
  onClick,
}: {
  mobile?: boolean
  onClick?: () => void
}) {
  return (
    <Link
      to="/observatory"
      data-testid={mobile ? 'observatory-link-mobile' : 'observatory-link'}
      onClick={onClick}
      className={[
        'items-center gap-2 text-[13px] font-medium text-espresso',
        'transition-colors duration-fade ease-out hover:text-accent',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
        mobile
          ? 'flex w-full px-1 py-2'
          : 'inline-flex min-h-9 border-l border-sand pl-3',
      ].join(' ')}
      style={{ fontFamily: 'var(--sans)' }}
    >
      <Telescope className="h-4 w-4" strokeWidth={1.8} aria-hidden />
      <span>{NAV.OBSERVATORY}</span>
      {/* The badge is part of the link's accessible name on purpose: a screen
          reader should hear "Pellier Observatory, Optional" rather than a bare
          destination, since optionality is the thing a participant most needs
          before deciding to spend time here. */}
      <span
        data-testid={mobile ? 'observatory-optional-mobile' : 'observatory-optional'}
        className={[
          'rounded-full border border-sand bg-cream-warm px-1.5 py-0.5',
          'text-[10px] font-medium uppercase tracking-[0.08em] text-ink-quiet',
        ].join(' ')}
      >
        {NAV.OBSERVATORY_OPTIONAL}
      </span>
    </Link>
  )
}

function OperatorLink({
  mobile = false,
  onClick,
}: {
  mobile?: boolean
  onClick?: () => void
}) {
  return (
    <Link
      to="/operator"
      data-testid={mobile ? 'operator-link-mobile' : 'operator-link'}
      onClick={onClick}
      className={[
        'items-center gap-2 text-[13px] font-medium text-espresso',
        'transition-colors duration-fade ease-out hover:text-accent',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
        mobile
          ? 'flex w-full px-1 py-2'
          : 'inline-flex min-h-9 border-l border-sand pl-3',
      ].join(' ')}
      style={{ fontFamily: 'var(--sans)' }}
    >
      <ConciergeBell className="h-4 w-4" strokeWidth={1.8} aria-hidden />
      <span>{NAV.OPERATOR}</span>
      {/* Deliberately no "Optional" badge. The Observatory carries one because
          it is an inspection surface nothing depends on; the operator desk is
          a working surface, and labelling it optional would misdescribe it. */}
    </Link>
  )
}

// ---------------------------------------------------------------------------
// PersonaDropdown — replaces PersonaPill + PersonaModal
// ---------------------------------------------------------------------------

function PersonaDropdown() {
  const { persona, switchPersona, signOut, switching } = usePersona()
  const [open, setOpen] = useState(false)
  const [personas, setPersonas] = useState<PersonaListItem[]>([])
  const [fetched, setFetched] = useState(false)
  const [personaError, setPersonaError] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const reduceMotion = Boolean(useReducedMotion())

  // Fetch persona list on first open
  useEffect(() => {
    if (!open || fetched) return
    fetch('/api/observatory/personas')
      .then((r) => {
        if (!r.ok) throw new Error(`Live personas unavailable: ${r.status}`)
        return r.json()
      })
      .then((data) => {
        const list = Array.isArray(data) ? data : []
        // Remove Fresh — signed-out state IS the baseline.
        // Only show Marco, Anna, Theo as selectable personas.
        const withoutFresh = list.filter((p: { id: string }) => p.id !== 'fresh')
        setPersonas(withoutFresh)
        setFetched(true)
      })
      .catch((error: unknown) => {
        setPersonas([])
        setPersonaError(error instanceof Error ? error.message : 'Live personas unavailable.')
        setFetched(true)
      })
  }, [open, fetched])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  const handleSelect = useCallback(
    async (id: string) => {
      await switchPersona(id)
      setOpen(false)
    },
    [switchPersona],
  )

  const handleSignOut = useCallback(() => {
    signOut()
    setOpen(false)
  }, [signOut])

  return (
    <div ref={dropdownRef} className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        data-testid="persona-pill"
        className={[
          'pellier-account-pill',
          'flex items-center gap-2 text-[13.5px] transition-colors duration-fade ease-out',
          'cursor-pointer rounded-full',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
        ].join(' ')}
        style={{
          ...(persona
            ? {
                padding: '4px 12px 4px 4px',
                background: 'var(--ink)',
                color: 'var(--cream)',
                border: '1px solid var(--ink)',
              }
            : { padding: '7px 14px' }),
        }}
        aria-expanded={open}
        aria-haspopup="true"
      >
        {persona ? (
          <>
            <Avatar
              initial={persona.avatar_initial}
              bgColor={persona.avatar_color}
              photoUrl={getPersonaPhoto(persona.id)}
              size="sm"
            />
            <span
              className="text-cream-50 truncate"
              style={{
                fontFamily: 'var(--sans)',
                fontSize: 13,
                fontWeight: 500,
                maxWidth: 118,
              }}
            >
              {persona.display_name}
            </span>
            <ChevronDown
              size={14}
              className="text-cream-50 opacity-60"
              aria-hidden
            />
          </>
        ) : (
          <>
            <UserIcon className="w-4 h-4" aria-hidden />
            <span style={{ fontFamily: 'var(--sans)' }}>
              Sign in
            </span>
          </>
        )}
      </button>

      {/* Dropdown */}
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            data-testid="persona-dropdown"
            className={[
              'absolute right-0 top-full mt-2 z-50',
              'bg-cream-50 border border-sand rounded-lg shadow-warm-md',
              'min-w-[240px] py-2',
            ].join(' ')}
            role="menu"
            aria-label="Persona menu"
            initial={
              reduceMotion
                ? { opacity: 0 }
                : { opacity: 0, transform: 'translateY(-4px) scale(0.98)' }
            }
            animate={
              reduceMotion
                ? { opacity: 1 }
                : { opacity: 1, transform: 'translateY(0) scale(1)' }
            }
            exit={
              reduceMotion
                ? { opacity: 0 }
                : { opacity: 0, transform: 'translateY(-4px) scale(0.98)' }
            }
            transition={{
              duration: reduceMotion ? 0.12 : 0.18,
              ease: MENU_EASE,
            }}
            style={{ transformOrigin: 'top right' }}
          >
            {/* The active shopper's rung. Stated once, quietly: the
                authoritative value lives on pellier.customers.membership and
                is what policy reads. This is only the shopper's view of it. */}
            {persona && (
              <div
                data-testid="persona-membership"
                className="px-4 pt-2 pb-3 mb-1 border-b border-sand"
              >
                <div
                  style={{
                    fontFamily: 'var(--sans)',
                    fontSize: 10,
                    fontWeight: 600,
                    letterSpacing: '0.14em',
                    textTransform: 'uppercase',
                    color: 'var(--pellier-burgundy)',
                  }}
                >
                  {MEMBERSHIP[persona.membership].label}
                </div>
                <div
                  className="text-ink-soft"
                  style={{
                    fontFamily: 'var(--sans)',
                    fontSize: 11,
                    lineHeight: 1.4,
                    marginTop: 3,
                  }}
                >
                  {MEMBERSHIP[persona.membership].earns}
                </div>
              </div>
            )}

            {!fetched && personas.length === 0 && (
              <div
                className="px-4 py-2.5 text-ink-soft text-[12px]"
                style={{ fontFamily: 'var(--sans)' }}
                aria-live="polite"
              >
                Loading personas…
              </div>
            )}
          {personaError ? (
            <p className="px-4 py-3 text-sm text-ink-quiet">{personaError}</p>
          ) : null}
          {personas.map((p) => {
              const isActive = persona?.id === p.id
              return (
                <button
                  key={p.id}
                  type="button"
                  role="menuitem"
                  disabled={switching}
                  data-testid={`persona-option-${p.id}`}
                  onClick={() => handleSelect(p.id)}
                  className={[
                    'w-full flex items-center gap-3 py-2.5 text-left border-l-[3px] transition-colors duration-fade ease-out',
                    'hover:bg-sand/50 cursor-pointer',
                    'focus-visible:outline-none focus-visible:bg-sand/50',
                    isActive
                      ? 'border-espresso bg-sand/70 pl-[13px] pr-4'
                      : 'border-transparent pl-[13px] pr-4',
                  ].join(' ')}
                >
                  <Avatar
                    initial={p.avatar_initial}
                    bgColor={p.avatar_color}
                    photoUrl={getPersonaPhoto(p.id)}
                    size="sm"
                  />
                  <div className="flex flex-col min-w-0">
                    <span
                      className="text-espresso text-[13px] font-medium truncate"
                      style={{ fontFamily: 'var(--sans)' }}
                    >
                      {p.display_name}
                    </span>
                    <span
                      className="text-ink-soft text-[11px] truncate"
                      style={{ fontFamily: 'var(--sans)' }}
                    >
                      {p.role_tag}
                    </span>
                  </div>
                </button>
              )
            })}

            {persona && (
              <>
                <div className="border-t border-sand my-1" />
                <button
                  type="button"
                  role="menuitem"
                  data-testid="persona-sign-out"
                  onClick={handleSignOut}
                  className={[
                    'w-full flex items-center gap-3 px-4 py-2.5 text-left',
                    'transition-colors duration-fade ease-out',
                    'hover:bg-sand/50 cursor-pointer text-espresso',
                    'focus-visible:outline-none focus-visible:bg-sand/50',
                  ].join(' ')}
                >
                  <LogOut size={16} className="text-ink-soft" aria-hidden />
                  <span
                    className="text-[13px] font-medium"
                    style={{ fontFamily: 'var(--sans)' }}
                  >
                    Sign out
                  </span>
                </button>
              </>
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

export default function Header({
  current = 'home',
  onNavigate,
}: HeaderProps) {
  const { items: cartItems, setCartOpen } = useCart()
  const { openModal } = useUI()
  const { persona } = usePersona()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const reduceMotion = Boolean(useReducedMotion())
  const cartItemCount = cartItems.reduce((sum, item) => sum + item.quantity, 0)
  const navItems = persona
    ? NAV_ITEMS
    : NAV_ITEMS.filter(({ item }) => item !== 'ask-pellier')

  // The storefront's search is Pellier - the chat drawer. Clicking the
  // Search icon opens the same concierge pill uses, which keeps the
  // header honest: one search surface, two entry points.
  const handleSearchClick = useCallback(() => {
    if (!persona) return
    openModal('drawer')
  }, [persona, openModal])

  const handleNavigate = useCallback(
    (item: NavItem) => {
      setMobileMenuOpen(false)
      onNavigate?.(item)
    },
    [onNavigate],
  )

  useEffect(() => {
    if (!mobileMenuOpen) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileMenuOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [mobileMenuOpen])

  return (
    <header
      role="banner"
      data-testid="sticky-header"
      className="sticky top-0 z-40 w-full border-b border-sand/50"
      style={{
        background: 'var(--header-bg)',
        WebkitBackdropFilter: 'blur(12px)',
        backdropFilter: 'blur(12px)',
      }}
    >
      <nav
        aria-label="Primary"
        className="relative h-[60px]"
        style={{ padding: '0 clamp(16px, 4vw, 48px)' }}
      >
        {/*
         * Three-column grid:
         *   1fr  | auto | 1fr
         *   left | mark | right
         *
         * The center column hugs the wordmark's intrinsic width; the 1fr
         * left/right columns split remaining space evenly at desktop widths.
         */}
        <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between gap-3 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:gap-5">
          {/* Left: four text nav items */}
          <div className="hidden min-w-0 items-center gap-5 lg:flex">
            {navItems.map(({ item, label }) => (
              <NavLink
                key={item}
                item={item}
                label={label}
                current={current}
                onClick={handleNavigate}
              />
            ))}
          </div>

          {/* Center: wordmark — its own grid track, no absolute positioning */}
          <div data-testid="wordmark-wrapper" className="flex items-center">
            <Wordmark />
          </div>

          {/* Right: search, persona dropdown, wishlist, bag, surface toggle */}
          <div className="flex items-center gap-1.5 justify-end min-w-0">
            {persona && (
              <div className="hidden xl:block">
                <IconButton
                  icon={<Search className="w-5 h-5" />}
                  ariaLabel="Search: ask Pellier"
                  onClick={handleSearchClick}
                  size="md"
                />
              </div>
            )}

            <PersonaDropdown />

            <div className="relative">
              <IconButton
                icon={<ShoppingBag className="w-5 h-5" />}
                ariaLabel="Bag"
                onClick={() => setCartOpen(true)}
                size="md"
              />
              {cartItemCount > 0 && (
                <span
                  data-testid="bag-count"
                  className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full flex items-center justify-center text-[10px] font-semibold bg-espresso text-cream-50 pointer-events-none"
                >
                  {cartItemCount}
                </span>
              )}
            </div>

            <div className="hidden lg:block ml-1">
              <OperatorLink />
            </div>

            <div className="hidden lg:block ml-1">
              <ObservatoryLink />
            </div>

            <IconButton
              icon={
                mobileMenuOpen ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Menu className="h-5 w-5" />
                )
              }
              ariaLabel={
                mobileMenuOpen ? 'Close navigation' : 'Open navigation'
              }
              onClick={() => setMobileMenuOpen((open) => !open)}
              size="md"
              className="lg:hidden"
            />
          </div>
        </div>

        <AnimatePresence initial={false}>
          {mobileMenuOpen ? (
            <motion.div
              data-testid="mobile-menu"
              className="
                absolute left-0 right-0 top-full border-b border-sand
                bg-cream px-4 py-3 shadow-warm-md lg:hidden
              "
              initial={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, transform: 'translateY(-6px)' }
              }
              animate={
                reduceMotion
                  ? { opacity: 1 }
                  : { opacity: 1, transform: 'translateY(0)' }
              }
              exit={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, transform: 'translateY(-6px)' }
              }
              transition={{
                duration: reduceMotion ? 0.12 : 0.18,
                ease: MENU_EASE,
              }}
              style={{ transformOrigin: 'top center' }}
            >
              <div className="grid gap-1">
                {navItems.map(({ item, label }) => (
                  <NavLink
                    key={item}
                    item={item}
                    label={label}
                    current={current}
                    onClick={handleNavigate}
                  />
                ))}
              </div>
              <div className="mt-3 border-t border-sand pt-3">
                <OperatorLink
                  mobile
                  onClick={() => setMobileMenuOpen(false)}
                />
                <ObservatoryLink
                  mobile
                  onClick={() => setMobileMenuOpen(false)}
                />
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </nav>
    </header>
  )
}
