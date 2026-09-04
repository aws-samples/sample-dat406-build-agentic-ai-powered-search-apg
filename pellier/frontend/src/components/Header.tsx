/**
 * Header — Pellier sticky header.
 *
 * Centered "Pellier" wordmark — Fraunces (`font-display`) + circular P
 * chip; word one step above footer (`text-2xl` vs `text-xl`). Four left
 * nav items (Shop, Stories, Ask Pellier, About), and right cluster: search
 * IconButton, persona Avatar dropdown, bag IconButton with count badge, and
 * a direct link to Pellier Observatory.
 *
 * Visitors without a scenario see a "Select scenario" pill. Once a persona is
 * active, the same header pill opens the shared portrait-led PersonaModal
 * used by Pellier Observatory. Neither state is a Cognito sign-in.
 *
 * Validates Requirements 4.3, 5.1, 5.2, 5.3, 5.4, 5.5, 15.3.
 *
 * Copy comes from `copy.ts`. Design tokens from `design/tokens.ts` and
 * Tailwind extended config.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useCart } from '../contexts/CartContext'
import { usePersona } from '../contexts/PersonaContext'
import { useUI } from '../contexts/UIContext'
import { NAV, SCENARIO } from '../copy'
import { Avatar } from '../design/primitives'
import { getPersonaPhoto } from '../data/personaPhotos'
import { IconButton } from '../design/primitives'
import PersonaModal from './PersonaModal'
import {
  Search,
  ShoppingBag,
  User as UserIcon,
  ChevronDown,
  Menu,
  X,
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
      className="flex min-h-[44px] items-center gap-2.5 select-none"
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
        'inline-flex min-h-[44px] min-w-[44px] items-center justify-center text-[14px] transition-colors duration-fade ease-out',
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
        'items-center gap-1.5 text-[14px] font-medium text-ink-quiet',
        'transition-colors duration-fade ease-out hover:text-accent',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
        mobile
          ? 'flex min-h-[44px] w-full px-1 py-2'
          : 'inline-flex min-h-[44px] border-l border-sand pl-3',
      ].join(' ')}
      style={{ fontFamily: 'var(--sans)' }}
    >
      <span>{NAV.OBSERVATORY}</span>
      {/* The badge is part of the link's accessible name on purpose: a screen
          reader should hear "Pellier Observatory, Optional" rather than a bare
          destination, since optionality is the thing a participant most needs
          before deciding to spend time here. */}
      <span
        data-testid={mobile ? 'observatory-optional-mobile' : 'observatory-optional'}
        className={[
          'rounded-full border border-sand bg-cream-warm px-1.5 py-0.5',
          'text-[11px] font-medium uppercase tracking-[0.08em] text-ink-quiet',
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
        'items-center gap-1.5 text-[14px] font-medium text-ink-quiet',
        'transition-colors duration-fade ease-out hover:text-accent',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
        mobile
          ? 'flex min-h-[44px] w-full px-1 py-2'
          : 'inline-flex min-h-[44px] border-l border-sand pl-3',
      ].join(' ')}
      style={{ fontFamily: 'var(--sans)' }}
    >
      <span>{NAV.OPERATOR}</span>
      {/* Deliberately no "Optional" badge. The Observatory carries one because
          it is an inspection surface nothing depends on; the operator desk is
          a working surface, and labelling it optional would misdescribe it. */}
    </Link>
  )
}

// ---------------------------------------------------------------------------
// Signed-out persona menu
// ---------------------------------------------------------------------------

function SignedOutPersonaTrigger({
  open,
  onOpen,
}: {
  open: boolean
  onOpen: () => void
}) {
  // The signed-out pill used to open a compact dropdown of the three
  // personas, a second chooser beside the modal the active-persona pill
  // already opens. Both now open the same three-card modal, which the
  // header owns so the signed-out Ask Pellier item can open it too.
  return (
    <button
      type="button"
      onClick={onOpen}
      data-testid="persona-pill"
      className={[
        'pellier-account-pill',
        'flex min-h-[44px] items-center gap-2 text-[13.5px] transition-colors duration-fade ease-out',
        'cursor-pointer rounded-full',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
      ].join(' ')}
      style={{ padding: '7px 14px' }}
      aria-haspopup="dialog"
      aria-expanded={open}
    >
      <UserIcon className="w-4 h-4" aria-hidden />
      <span style={{ fontFamily: 'var(--sans)' }}>{SCENARIO.SELECT}</span>
    </button>
  )
}

function AuthenticatedPersonaTrigger() {
  const { persona } = usePersona()
  const [open, setOpen] = useState(false)

  if (!persona) return null

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        data-testid="persona-pill"
        className={[
          'pellier-account-pill',
          'flex min-h-[44px] items-center gap-2 text-[13.5px] transition-colors duration-fade ease-out',
          'cursor-pointer rounded-full',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso focus-visible:ring-offset-2',
        ].join(' ')}
        style={{
          padding: '4px 12px 4px 4px',
          background: 'var(--ink)',
          color: 'var(--cream)',
          border: '1px solid var(--ink)',
        }}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
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
      </button>
      <PersonaModal open={open} onClose={() => setOpen(false)} />
    </>
  )
}

function PersonaAccountControl({
  chooserOpen,
  onOpenChooser,
}: {
  chooserOpen: boolean
  onOpenChooser: () => void
}) {
  const { persona } = usePersona()
  return persona ? (
    <AuthenticatedPersonaTrigger />
  ) : (
    <SignedOutPersonaTrigger open={chooserOpen} onOpen={onOpenChooser} />
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
  const [chooserOpen, setChooserOpen] = useState(false)
  const reduceMotion = Boolean(useReducedMotion())
  const cartItemCount = cartItems.reduce((sum, item) => sum + item.quantity, 0)
  const navItems = NAV_ITEMS
  const openChooser = useCallback(() => setChooserOpen(true), [])

  // The storefront's search is Pellier - the chat drawer. Clicking the
  // Search icon opens the same concierge the pill uses, which keeps the
  // header honest: one search surface, two entry points. Signed out, both
  // lead to the chooser first, because the concierge needs a shopper.
  const handleSearchClick = useCallback(() => {
    if (!persona) {
      setChooserOpen(true)
      return
    }
    openModal('drawer')
  }, [persona, openModal])

  const handleNavigate = useCallback(
    (item: NavItem) => {
      setMobileMenuOpen(false)
      if (item === 'ask-pellier' && !persona) {
        setChooserOpen(true)
        return
      }
      onNavigate?.(item)
    },
    [onNavigate, persona],
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

            <PersonaAccountControl chooserOpen={chooserOpen} onOpenChooser={openChooser} />

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
      {!persona ? (
        <PersonaModal open={chooserOpen} onClose={() => setChooserOpen(false)} />
      ) : null}
    </header>
  )
}
