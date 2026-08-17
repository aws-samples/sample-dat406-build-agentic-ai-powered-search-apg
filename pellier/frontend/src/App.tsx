/**
 * App — root component.
 *
 * Composition is intentionally minimal: provider chain, BrowserRouter,
 * root-level modal hosts (AuthModal, PreferencesModal, ChatDrawer,
 * ComparisonHost), and the final route table. The two surfaces are
 * BoutiquePage (`/`) and AgentTraceFrame (`/pellier-labs/*`).
 *
 * AuthGate is exported so Pellier Labs surface can be gated when Cognito
 * is configured.
 */
import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
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
import { safeReturnTo } from './utils/auth'
import './styles/premium-heading-styles.css'

const BoutiquePage = lazy(() => import('./pages/BoutiquePage'))
const AgentTraceFrame = lazy(() => import('./agent-trace/shell/AgentTraceFrame'))
const SessionsList = lazy(() => import('./agent-trace/surfaces/observe/SessionsList'))
const SessionView = lazy(() => import('./agent-trace/surfaces/observe/SessionView'))
const ChatTab = lazy(() => import('./agent-trace/surfaces/observe/ChatTab'))
const TelemetryTab = lazy(() => import('./agent-trace/surfaces/observe/TelemetryTab'))
const BriefTab = lazy(() => import('./agent-trace/surfaces/observe/BriefTab'))
const Observatory = lazy(() => import('./agent-trace/surfaces/observe/Observatory'))
const ProofBoard = lazy(() => import('./agent-trace/surfaces/observe/ProofBoard'))
const PellierLabsWorkbench = lazy(
  () => import('./agent-trace/surfaces/observe/PellierLabsWorkbench'),
)
const PersonaJourneys = lazy(() => import('./agent-trace/surfaces/observe/PersonaJourneys'))
const ArchitectureIndex = lazy(
  () => import('./agent-trace/surfaces/understand/ArchitectureIndex'),
)
const ArchitectureDetail = lazy(
  () => import('./agent-trace/surfaces/understand/ArchitectureDetail'),
)
const Agents = lazy(() => import('./agent-trace/surfaces/understand/Agents'))
const Tools = lazy(() => import('./agent-trace/surfaces/understand/Tools'))
const Search = lazy(() => import('./agent-trace/surfaces/understand/Search'))
const Skills = lazy(() => import('./agent-trace/surfaces/understand/Skills'))
const Routing = lazy(() => import('./agent-trace/surfaces/understand/Routing'))
const MemoryDashboard = lazy(
  () => import('./agent-trace/surfaces/understand/MemoryDashboard'),
)
const WritePath = lazy(() => import('./agent-trace/surfaces/understand/WritePath'))
const Performance = lazy(() => import('./agent-trace/surfaces/measure/Performance'))
const Evaluations = lazy(() => import('./agent-trace/surfaces/measure/Evaluations'))
const ProductionPatterns = lazy(
  () => import('./agent-trace/surfaces/measure/ProductionPatterns'),
)
const AgentTraceSettings = lazy(() => import('./agent-trace/surfaces/Settings'))
const InspectorPage = lazy(() => import('./pages/InspectorPage'))
const StoryboardPage = lazy(() => import('./pages/StoryboardPage'))
const DiscoverPage = lazy(() => import('./pages/DiscoverPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))

// ---------------------------------------------------------------------------
// AuthGate — Cognito-aware auth wrapper. Gates Pellier Labs surface when
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
// and navigates to `/pellier-labs` should keep talking to Pellier. The
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

export function isPellierSurfacePath(pathname: string) {
  return (
    pathname === '/' ||
    pathname === '/signin' ||
    pathname.startsWith('/storyboard') ||
    pathname.startsWith('/discover') ||
    pathname.startsWith('/about') ||
    pathname.startsWith('/pellier-labs')
  )
}

function PellierSurfaceRoute() {
  const { pathname } = useLocation()
  const isPellierSurface = isPellierSurfacePath(pathname)

  useEffect(() => {
    document.body.classList.toggle('pellier-surface', isPellierSurface)
    return () => document.body.classList.remove('pellier-surface')
  }, [isPellierSurface])

  return null
}

function SignInChooserRoute() {
  const { activeModal, openModal } = useUI()
  const { search } = useLocation()
  const navigate = useNavigate()
  const [opened, setOpened] = useState(false)
  const returnTo = safeReturnTo(new URLSearchParams(search).get('returnTo'))

  useEffect(() => {
    openModal('auth')
    setOpened(true)
  }, [openModal])

  useEffect(() => {
    if (opened && activeModal !== 'auth') {
      navigate(returnTo, { replace: true })
    }
  }, [activeModal, navigate, opened, returnTo])

  return <BoutiquePage />
}

function LegacyLabsRedirect() {
  const { pathname, search, hash } = useLocation()
  const legacyPrefix = pathname.startsWith('/agent-trace')
    ? '/agent-trace'
    : '/labs'
  const suffix = pathname.slice(legacyPrefix.length)
  return (
    <Navigate
      to={`/pellier-labs${suffix}${search}${hash}`}
      replace
    />
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

export function AppRoutes() {
  return (
    <>
      <PellierSurfaceRoute />
      <Suspense fallback={<RouteLoading />}>
        <Routes>
          {/*
           *   /           -> BoutiquePage (storefront shell)
           *   /signin     -> BoutiquePage + provider chooser
           *   /pellier-labs/* -> Pellier Labs
           *   /inspector  -> InspectorPage (frozen session-scoped trace view)
           *   /storyboard -> StoryboardPage
           *   /discover   -> DiscoverPage
           *   *           -> redirect to /
           */}
          <Route path="/" element={<BoutiquePage />} />
          <Route path="/signin" element={<SignInChooserRoute />} />
          <Route path="/agent-trace/*" element={<LegacyLabsRedirect />} />
          <Route path="/labs/*" element={<LegacyLabsRedirect />} />
          <Route path="/pellier-labs" element={<AgentTraceFrame />}>
            <Route index element={<PellierLabsWorkbench />} />
            <Route path="proof-board" element={<ProofBoard />} />
            <Route path="sessions" element={<SessionsList />} />
            <Route path="sessions/:id" element={<SessionView />}>
              <Route index element={<Navigate to="chat" replace />} />
              <Route path="chat" element={<ChatTab />} />
              <Route path="telemetry" element={<TelemetryTab />} />
              <Route path="brief" element={<BriefTab />} />
            </Route>
            <Route path="architecture" element={<ArchitectureIndex />} />
            <Route path="architecture/:concept" element={<ArchitectureDetail />} />
            <Route path="agents" element={<Agents />} />
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
            <Route path="settings" element={<AgentTraceSettings />} />
          </Route>
          <Route path="/inspector" element={<InspectorPage />} />
          <Route path="/storyboard" element={<StoryboardPage />} />
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </>
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
             * AuthModal + PreferencesModal are route-independent. Storefront
             * chat and comparison live inside BrowserRouter; Pellier Labs is
             * intentionally chat-free.
             */}
            <AuthModal />
            <PreferencesModal />
            <PersonaTransitionOverlay />
            <CartPanelSlot />
            <ToastSlot />
            <BrowserRouter basename={routerBasename()}>
              <ModalRouteGuard />
              <ChatDrawer />
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
