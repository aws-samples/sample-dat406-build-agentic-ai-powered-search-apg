/**
 * App — root component.
 *
 * Composition is intentionally minimal: provider chain, BrowserRouter,
 * root-level modal hosts (AuthModal, PreferencesModal, ConciergeModal,
 * ComparisonHost), and the final route table. The two surfaces are
 * PellierPage (`/`) and the Pellier Observatory frame (`/observatory/*`).
 *
 * AuthGate is exported so the Pellier Observatory surface can be gated when Cognito
 * is configured.
 */
import { lazy, Suspense, useEffect, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { CartProvider, useCart } from './contexts/CartContext'
import { UIProvider, useUI } from './contexts/UIContext'
import { LayoutProvider } from './contexts/LayoutContext'
import { PersonaProvider } from './contexts/PersonaContext'
import AuthModal from './components/AuthModal'
import CartPanel from './components/CartPanel'
import Toast from './components/Toast'
import PersonaTransitionOverlay from './components/PersonaTransitionOverlay'
import PreferencesModal from './components/PreferencesModal'
import ChatDrawer from './components/ChatDrawer'
import ComparisonHost from './components/ComparisonHost'
import SignInPage from './components/SignInPage'
import { routerBasename } from './utils/assetPath'
import './styles/premium-heading-styles.css'

const PellierPage = lazy(() => import('./pages/PellierPage'))
const ConciergeModal = lazy(() => import('./components/ConciergeModal'))
const ObservatoryFrame = lazy(() => import('./observatory/shell/ObservatoryFrame'))
const OperatorFrame = lazy(() => import('./operator/shell/OperatorFrame'))
const ClientBook = lazy(() => import('./operator/surfaces/ClientBook'))
const ClientRecord = lazy(() => import('./operator/surfaces/ClientRecord'))
const ReviewQueue = lazy(() => import('./operator/surfaces/ReviewQueue'))
const ReviewRecord = lazy(() => import('./operator/surfaces/ReviewRecord'))
const SessionsList = lazy(() => import('./observatory/surfaces/observe/SessionsList'))
const SessionView = lazy(() => import('./observatory/surfaces/observe/SessionView'))
const ChatTab = lazy(() => import('./observatory/surfaces/observe/ChatTab'))
const TelemetryTab = lazy(() => import('./observatory/surfaces/observe/TelemetryTab'))
const BriefTab = lazy(() => import('./observatory/surfaces/observe/BriefTab'))
const WorkshopMap = lazy(() => import('./observatory/surfaces/observe/WorkshopMap'))
const ProofBoard = lazy(() => import('./observatory/surfaces/observe/ProofBoard'))
const ObservatoryWorkbench = lazy(
  () => import('./observatory/surfaces/observe/ObservatoryWorkbench'),
)
const ReferencesIndex = lazy(
  () => import('./observatory/surfaces/ReferencesIndex'),
)
const PersonaJourneys = lazy(() => import('./observatory/surfaces/observe/PersonaJourneys'))
const ArchitectureIndex = lazy(
  () => import('./observatory/surfaces/understand/ArchitectureIndex'),
)
const ArchitectureDetail = lazy(
  () => import('./observatory/surfaces/understand/ArchitectureDetail'),
)
const Tools = lazy(() => import('./observatory/surfaces/understand/Tools'))
const Search = lazy(() => import('./observatory/surfaces/understand/Search'))
const Skills = lazy(() => import('./observatory/surfaces/understand/Skills'))
const Routing = lazy(() => import('./observatory/surfaces/understand/Routing'))
const MemoryDashboard = lazy(
  () => import('./observatory/surfaces/understand/MemoryDashboard'),
)
const WritePath = lazy(() => import('./observatory/surfaces/understand/WritePath'))
const Performance = lazy(() => import('./observatory/surfaces/measure/Performance'))
const Evaluations = lazy(() => import('./observatory/surfaces/measure/Evaluations'))
const ProductionPatterns = lazy(
  () => import('./observatory/surfaces/measure/ProductionPatterns'),
)
const ObservatorySettings = lazy(() => import('./observatory/surfaces/Settings'))
const ProductDetailPage = lazy(() => import('./pages/ProductDetailPage'))
const InspectorPage = lazy(() => import('./pages/InspectorPage'))
const StoryboardPage = lazy(() => import('./pages/StoryboardPage'))
const DiscoverPage = lazy(() => import('./pages/DiscoverPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))

// ---------------------------------------------------------------------------
// AuthGate — Cognito-aware auth wrapper. Gates the Pellier Observatory surface when
// Cognito is configured. When Cognito is not configured (local dev without
// env vars), children pass through directly.
// ---------------------------------------------------------------------------
export function AuthGate({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()
  const cognitoConfigured = !!(
    import.meta.env.VITE_COGNITO_DOMAIN && import.meta.env.VITE_COGNITO_CLIENT_ID
  )

  if (!cognitoConfigured) return <>{children}</>

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: 'var(--cream)' }}
      >
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-black/10 border-t-black/40 rounded-full animate-spin" />
          <p className="text-sm" style={{ color: 'rgba(0,0,0,0.45)' }}>
            Loading...
          </p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) return <SignInPage />
  return <>{children}</>
}

// ---------------------------------------------------------------------------
// ModalRouteGuard — closes transient modals when the route changes.
//
// UIProvider sits above BrowserRouter so it can't call useLocation()
// directly. This tiny watcher mounts inside the router, subscribes
// to pathname changes, and closes anything non-persistent. Chat
// surfaces (drawer / concierge) and the comparison modal are
// intentional leave-open cases — a user who opens the chat on `/`
// and navigates to `/observatory` should keep talking to Pellier. The
// auth, preferences, and cart modals close because they're
// context-bound to a specific page.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// CartPanelSlot — bridges CartContext's open/close to CartPanel props.
// Mounted at the App root so it survives route changes (same as AuthModal).
// ---------------------------------------------------------------------------
function CartPanelSlot() {
  const { cartOpen, setCartOpen } = useCart()
  return <CartPanel isOpen={cartOpen} onClose={() => setCartOpen(false)} />
}

// ---------------------------------------------------------------------------
// ToastSlot — bridges CartContext's toast state to the Toast component.
// ---------------------------------------------------------------------------
function ToastSlot() {
  const { showToast, toastMessage, dismissToast } = useCart()
  return <Toast message={toastMessage} show={showToast} onClose={dismissToast} />
}

const TRANSIENT_MODALS = new Set(['auth', 'preferences', 'cart', 'checkout'])

function ModalRouteGuard() {
  const { pathname } = useLocation()
  const { activeModal, closeModal } = useUI()
  useEffect(() => {
    if (activeModal && TRANSIENT_MODALS.has(activeModal)) {
      closeModal()
    }
    // intentionally only run on pathname changes — activeModal in the
    // dep array would close the modal the instant it opened.
  }, [pathname])
  return null
}

/**
 * The shopper's Ask Pellier drawer, and the surfaces it does not belong on.
 *
 * `ChatDrawer` was mounted for every route, so its "Continue chat" pill floated over
 * Pellier Operator whenever the browser held a storefront thread — the shopper
 * conversation following an operator around their own console. It is a surface-boundary
 * leak rather than a bug in the drawer: Operator is a different product with its own
 * Concierge, and offering a shopper thread there invites clicking into the wrong one.
 *
 * Gated on the route rather than removed, because the drawer is correct everywhere
 * else, including the Observatory, where a participant legitimately wants to keep a
 * shopper turn open while reading its evidence.
 */
function ShopperChatSlot() {
  const { pathname } = useLocation()
  if (pathname.startsWith('/operator')) return null
  return <ChatDrawer />
}

function ObservatoryConciergeSlot() {
  const { pathname } = useLocation()
  if (!pathname.startsWith('/observatory')) return null
  return (
    <Suspense fallback={null}>
      <ConciergeModal />
    </Suspense>
  )
}

/**
 * Every path the inspection surface has ever lived at, newest last.
 *
 * The surface has been renamed twice: Observatory, then Pellier Labs, now the
 * Observatory. Workshop screenshots, the lab guide, and browser history all
 * still point at the old paths, and a participant following a screenshot into
 * a 404 has no way to know the page was renamed rather than removed.
 *
 * Order matters only in that no entry may be a prefix of `/observatory`, or the
 * redirect would resolve to itself.
 */
const LEGACY_SURFACE_PREFIXES = ['/agent-trace', '/pellier-labs', '/labs'] as const

function LegacyPathRedirect() {
  const { pathname, search, hash } = useLocation()
  const legacyPrefix = LEGACY_SURFACE_PREFIXES.find((prefix) =>
    pathname.startsWith(prefix),
  )
  // Nothing matched, which means this component was mounted on a route it does
  // not own. Send the visitor to the surface root rather than to a path built
  // from a prefix that was never there.
  const suffix = legacyPrefix ? pathname.slice(legacyPrefix.length) : ''
  return <Navigate to={`/observatory${suffix}${search}${hash}`} replace />
}

function RouteLoading() {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="min-h-[40vh] flex items-center justify-center"
    >
      <span className="w-7 h-7 rounded-full border-2 border-black/10 border-t-black/50 animate-spin" />
    </div>
  )
}

export function AppRoutes() {
  return (
    <Suspense fallback={<RouteLoading />}>
      <Routes>
        {/*
         *   /           -> PellierPage (storefront shell)
         *   /product/:id -> ProductDetailPage (one piece, deep-linkable)
         *   /observatory/* -> Pellier Observatory
         *   /inspector  -> InspectorPage (frozen session-scoped trace view)
         *   /storyboard -> StoryboardPage
         *   /discover   -> DiscoverPage
         *   *           -> redirect to /
        */}
        <Route path="/" element={<PellierPage />} />
        <Route path="/product/:productId" element={<ProductDetailPage />} />
        {/* Legacy surface paths. `/observatory/*` is deliberately absent: it
            would shadow the real surface below and redirect to itself. */}
        <Route path="/agent-trace/*" element={<LegacyPathRedirect />} />
        <Route path="/pellier-labs/*" element={<LegacyPathRedirect />} />
        <Route path="/labs/*" element={<LegacyPathRedirect />} />
        {/* Pellier Operator — the clienteling desk. Reads are open so the
            surface is never a blank 401 on a box with no Cognito wired; the
            write actions are gated by require_operator server-side. */}
        <Route path="/operator" element={<OperatorFrame />}>
          <Route index element={<ClientBook />} />
          <Route path="clients/:customerId" element={<ClientRecord />} />
          {/* Prepared requests handed off from Pellier. The queue is the desk's
              entry point for storefront work, so an operator finds a waiting
              client without already knowing to search for them. */}
          <Route path="reviews" element={<ReviewQueue />} />
          <Route path="reviews/:reviewId" element={<ReviewRecord />} />
        </Route>
        <Route path="/observatory" element={<ObservatoryFrame />}>
          <Route index element={<ObservatoryWorkbench />} />
          <Route path="references" element={<ReferencesIndex />} />
          <Route path="proof-board" element={<ProofBoard />} />
          <Route
            path="audit-proof"
            element={<ProofBoard focusCardId="audit-ledger" />}
          />
          <Route path="sessions" element={<SessionsList />} />
          <Route path="sessions/:id" element={<SessionView />}>
            <Route index element={<Navigate to="chat" replace />} />
            <Route path="chat" element={<ChatTab />} />
            <Route path="telemetry" element={<TelemetryTab />} />
            <Route path="brief" element={<BriefTab />} />
          </Route>
          <Route path="architecture" element={<ArchitectureIndex />} />
          <Route path="architecture/:concept" element={<ArchitectureDetail />} />
          <Route
            path="agents"
            element={<Navigate to="/observatory/tools" replace />}
          />
          <Route path="tools" element={<Tools />} />
          <Route path="search" element={<Search />} />
          <Route path="skills" element={<Skills />} />
          <Route path="routing" element={<Routing />} />
          <Route path="memory" element={<MemoryDashboard />} />
          <Route path="write-path" element={<WritePath />} />
          <Route path="performance" element={<Performance />} />
          <Route path="evaluations" element={<Evaluations />} />
          <Route path="production-patterns" element={<ProductionPatterns />} />
          <Route path="workshop-map" element={<WorkshopMap />} />
          {/* The page was routed at `observatory` while the navigation
              called it "Workshop Map". The shell now owns that name, so the
              old path redirects rather than 404s for anyone holding a link
              or a screenshot of it. */}
          <Route
            path="observatory"
            element={<Navigate to="/observatory/workshop-map" replace />}
          />
          <Route path="persona-journeys" element={<PersonaJourneys />} />
          <Route path="settings" element={<ObservatorySettings />} />
        </Route>
        <Route path="/inspector" element={<InspectorPage />} />
        <Route path="/storyboard" element={<StoryboardPage />} />
        <Route path="/discover" element={<DiscoverPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

// ---------------------------------------------------------------------------
// App — provider chain + routes.
// ---------------------------------------------------------------------------
function App() {
  return (
    <AuthProvider>
      <PersonaProvider>
      <LayoutProvider>
        <CartProvider>
          <UIProvider>
            {/*
             * Modal singleton slots. Mounting here puts them above every
             * route; they read `UIContext.activeModal` to decide whether
             * to render, so a route change never interrupts an open modal.
             * AuthModal + PreferencesModal are route-independent; Concierge
             * and Comparison live inside BrowserRouter because the
             * concierge reads useLocation() for route-mode selection.
             */}
            <AuthModal />
            <PreferencesModal />
            <PersonaTransitionOverlay />
            <CartPanelSlot />
            <ToastSlot />
            <BrowserRouter basename={routerBasename()}>
              <ModalRouteGuard />
              <ObservatoryConciergeSlot />
              <ShopperChatSlot />
              <ComparisonHost />
              <AppRoutes />
            </BrowserRouter>
          </UIProvider>
        </CartProvider>
      </LayoutProvider>
      </PersonaProvider>
    </AuthProvider>
  )
}

export default App
