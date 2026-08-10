/**
 * App — root component.
 *
 * Composition is intentionally minimal: provider chain, BrowserRouter,
 * root-level modal hosts (AuthModal, PreferencesModal, ConciergeModal,
 * ComparisonHost), and the final route table. The two surfaces are
 * BoutiquePage (`/`) and AtelierFrame (`/atelier/*`).
 *
 * AuthGate is exported so the Atelier surface can be gated when Cognito
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

const BoutiquePage = lazy(() => import('./pages/BoutiquePage'))
const ConciergeModal = lazy(() => import('./components/ConciergeModal'))
const AtelierFrame = lazy(() => import('./atelier/shell/AtelierFrame'))
const SessionsList = lazy(() => import('./atelier/surfaces/observe/SessionsList'))
const SessionView = lazy(() => import('./atelier/surfaces/observe/SessionView'))
const ChatTab = lazy(() => import('./atelier/surfaces/observe/ChatTab'))
const TelemetryTab = lazy(() => import('./atelier/surfaces/observe/TelemetryTab'))
const BriefTab = lazy(() => import('./atelier/surfaces/observe/BriefTab'))
const Observatory = lazy(() => import('./atelier/surfaces/observe/Observatory'))
const ProofBoard = lazy(() => import('./atelier/surfaces/observe/ProofBoard'))
const PersonaJourneys = lazy(() => import('./atelier/surfaces/observe/PersonaJourneys'))
const ArchitectureIndex = lazy(
  () => import('./atelier/surfaces/understand/ArchitectureIndex'),
)
const ArchitectureDetail = lazy(
  () => import('./atelier/surfaces/understand/ArchitectureDetail'),
)
const Tools = lazy(() => import('./atelier/surfaces/understand/Tools'))
const Search = lazy(() => import('./atelier/surfaces/understand/Search'))
const Skills = lazy(() => import('./atelier/surfaces/understand/Skills'))
const Routing = lazy(() => import('./atelier/surfaces/understand/Routing'))
const MemoryDashboard = lazy(
  () => import('./atelier/surfaces/understand/MemoryDashboard'),
)
const WritePath = lazy(() => import('./atelier/surfaces/understand/WritePath'))
const Performance = lazy(() => import('./atelier/surfaces/measure/Performance'))
const Evaluations = lazy(() => import('./atelier/surfaces/measure/Evaluations'))
const ProductionPatterns = lazy(
  () => import('./atelier/surfaces/measure/ProductionPatterns'),
)
const AtelierSettings = lazy(() => import('./atelier/surfaces/Settings'))
const InspectorPage = lazy(() => import('./pages/InspectorPage'))
const StoryboardPage = lazy(() => import('./pages/StoryboardPage'))
const DiscoverPage = lazy(() => import('./pages/DiscoverPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))

// ---------------------------------------------------------------------------
// AuthGate — Cognito-aware auth wrapper. Gates the Atelier surface when
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
// and navigates to `/atelier` should keep talking to Pellier. The
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

function AtelierConciergeSlot() {
  const { pathname } = useLocation()
  if (!pathname.startsWith('/atelier')) return null
  return (
    <Suspense fallback={null}>
      <ConciergeModal />
    </Suspense>
  )
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
            <BrowserRouter
              basename={routerBasename()}
              future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
              }}
            >
              <ModalRouteGuard />
              <AtelierConciergeSlot />
              <ChatDrawer />
              <ComparisonHost />
              <Suspense fallback={<RouteLoading />}>
                <Routes>
                {/*
                 *   /           → BoutiquePage (storefront shell)
                 *   /atelier/*  → AtelierFrame (instrumentation, gated by AuthGate)
                 *   /inspector  → InspectorPage (frozen session-scoped trace view)
                 *   /storyboard → StoryboardPage
                 *   /discover   → DiscoverPage
                 *   *           → redirect to /
                 */}
                <Route path="/" element={<BoutiquePage />} />
                {/* Atelier Observatory — nested routes under AtelierFrame shell.
                    The frame renders the wide workshop sidebar + canvas grid with
                    React Router <Outlet /> for surface rendering. */}
                <Route path="/atelier" element={<AtelierFrame />}>
                  <Route index element={<Navigate to="proof-board" replace />} />
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
                  <Route path="agents" element={<Navigate to="/atelier/tools" replace />} />
                  <Route path="tools" element={<Tools />} />
                  <Route path="search" element={<Search />} />
                  <Route path="skills" element={<Skills />} />
                  <Route path="routing" element={<Routing />} />
                  <Route path="memory" element={<MemoryDashboard />} />
                  <Route path="write-path" element={<WritePath />} />
                  <Route path="performance" element={<Performance />} />
                  <Route path="evaluations" element={<Evaluations />} />
                  <Route path="production-patterns" element={<ProductionPatterns />} />
                  <Route path="observatory" element={<Observatory />} />
                  <Route path="persona-journeys" element={<PersonaJourneys />} />
                  <Route path="settings" element={<AtelierSettings />} />
                </Route>
                <Route path="/inspector" element={<InspectorPage />} />
                <Route path="/storyboard" element={<StoryboardPage />} />
                <Route path="/discover" element={<DiscoverPage />} />
                <Route path="/about" element={<AboutPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Suspense>
            </BrowserRouter>
          </UIProvider>
        </CartProvider>
      </LayoutProvider>
      </PersonaProvider>
    </AuthProvider>
  )
}

export default App
