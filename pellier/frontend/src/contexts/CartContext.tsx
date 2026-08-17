/**
 * Cart Context — Centralizes cart state, checkout metrics, and toast notifications.
 * Replaces prop-threaded cart state from App.tsx and the window.addToCart global.
 */
import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react'
import { useLayout, type WorkshopMode } from './LayoutContext'
import { useAuth } from './AuthContext'
import {
  CommerceApiError,
  confirmCommerceQuote,
  createCommerceQuote,
  executeCommerceOrder,
  type CommerceQuote,
  type CommerceReceipt,
  type ConfirmationGrant,
} from '../services/commerce'

// --- Types ---

export type CartItemOrigin = 'manual' | 'search-quick-add' | 'chat' | 'bundle' | 'memory'

export interface CartItem {
  productId: number
  name: string
  price: number
  quantity: number
  image?: string
  origin: CartItemOrigin
  addedAt: number
}

interface CartAdditionEvent {
  origin: CartItemOrigin
  timestamp: number
}

export interface CheckoutMetrics {
  searchCount: number
  productViews: number
  additions: CartAdditionEvent[]
}

interface PreviousModeSnapshot {
  mode: WorkshopMode
  totalSteps: number
}

export type CheckoutStage =
  | 'bag'
  | 'quoting'
  | 'review'
  | 'confirming'
  | 'executing'
  | 'complete'
  | 'error'

export interface CheckoutFailure {
  code: string
  message: string
}

interface CartContextValue {
  items: CartItem[]
  metrics: CheckoutMetrics
  previousModeSteps: PreviousModeSnapshot | null
  cartOpen: boolean
  setCartOpen: (open: boolean) => void
  showToast: boolean
  toastMessage: string
  dismissToast: () => void
  /** Fire a one-off toast from any consumer (e.g., "Wishlist is coming soon"). */
  notify: (message: string) => void
  addToCart: (product: { productId: number; name: string; price: number; image?: string; origin: CartItemOrigin }) => void
  addAllToCart: (products: Array<{ productId: number; name: string; price: number; image?: string }>, origin: CartItemOrigin) => void
  updateQuantity: (productId: number, quantity: number) => void
  removeFromCart: (productId: number) => void
  clearCart: () => void
  handleCheckout: () => Promise<void>
  confirmAndPlaceOrder: () => Promise<void>
  checkoutStage: CheckoutStage
  checkoutQuote: CommerceQuote | null
  checkoutReceipt: CommerceReceipt | null
  checkoutError: CheckoutFailure | null
  checkoutComplete: boolean
  resetCheckout: () => void
  incrementSearch: () => void
  incrementProductView: () => void
}

// --- Context + Hook ---

const CartContext = createContext<CartContextValue | undefined>(undefined)

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used within CartProvider')
  return ctx
}

// --- Helpers ---

const STORAGE_KEY = 'pellier-cart'
const CART_SESSION_KEY = 'pellier-cart-session'

function hydrateItems(): CartItem[] {
  try {
    // Session-scope the cart: if the browser session is fresh (no
    // session ID stored) or the session ID changed (persona switch,
    // new tab), start with an empty cart rather than resurfacing
    // phantom items from a prior persona or demo run. Items added
    // during the current session will re-persist normally.
    const currentSession = localStorage.getItem('pellier-session-id') || ''
    const cartSession = localStorage.getItem(CART_SESSION_KEY) || ''
    if (!currentSession || currentSession !== cartSession) {
      // Stale or first load — clear the persisted cart and record
      // the new session so subsequent navigations within the same
      // session keep their cart.
      localStorage.removeItem(STORAGE_KEY)
      if (currentSession) {
        localStorage.setItem(CART_SESSION_KEY, currentSession)
      }
      return []
    }

    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved) as Array<Partial<CartItem>>
      return parsed.map(item => ({
        productId: item.productId ?? 0,
        name: item.name ?? '',
        price: item.price ?? 0,
        quantity: item.quantity ?? 1,
        image: item.image,
        origin: item.origin ?? 'manual',
        addedAt: item.addedAt ?? 0,
      }))
    }
  } catch { /* ignore corrupt data */ }
  return []
}

function emptyMetrics(): CheckoutMetrics {
  return { searchCount: 0, productViews: 0, additions: [] }
}

function totalSteps(m: CheckoutMetrics): number {
  return m.searchCount + m.productViews + m.additions.length
}

// --- Provider ---

export function CartProvider({ children }: { children: ReactNode }) {
  const { workshopMode } = useLayout()
  const { isAuthenticated } = useAuth()

  // Cart items
  const [items, setItems] = useState<CartItem[]>(hydrateItems)

  // Checkout metrics
  const [metrics, setMetrics] = useState<CheckoutMetrics>(emptyMetrics)
  const [previousModeSteps, setPreviousModeSteps] = useState<PreviousModeSnapshot | null>(null)

  // UI state
  const [cartOpen, setCartOpen] = useState(false)
  const [checkoutStage, setCheckoutStage] = useState<CheckoutStage>('bag')
  const [checkoutQuote, setCheckoutQuote] = useState<CommerceQuote | null>(null)
  const [checkoutReceipt, setCheckoutReceipt] = useState<CommerceReceipt | null>(null)
  const [checkoutError, setCheckoutError] = useState<CheckoutFailure | null>(null)
  const [showToast, setShowToast] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

  // Track mode changes — skip initial mount
  const prevModeRef = useRef(workshopMode)
  const isMounted = useRef(false)
  const executionKeyRef = useRef<string | null>(null)
  const confirmationGrantRef = useRef<ConfirmationGrant | null>(null)

  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true
      return
    }
    // Workshop mode changed — snapshot current steps, then reset
    const prevMode = prevModeRef.current
    const steps = totalSteps(metrics)
    if (steps > 0) {
      setPreviousModeSteps({ mode: prevMode, totalSteps: steps })
    }
    setMetrics(emptyMetrics())
    prevModeRef.current = workshopMode
  }, [workshopMode])

  // Persist cart to localStorage + stamp the session so stale carts
  // from prior sessions don't resurrect on the next page load.
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
    try {
      const sid = localStorage.getItem('pellier-session-id')
      if (sid) localStorage.setItem(CART_SESSION_KEY, sid)
    } catch { /* ignore */ }
  }, [items])

  // --- Cart operations ---

  const toast = useCallback((msg: string) => {
    setToastMessage(msg)
    setShowToast(true)
  }, [])

  const dismissToast = useCallback(() => {
    setShowToast(false)
  }, [])

  const invalidateCheckout = useCallback(() => {
    setCheckoutStage('bag')
    setCheckoutQuote(null)
    setCheckoutReceipt(null)
    setCheckoutError(null)
    executionKeyRef.current = null
    confirmationGrantRef.current = null
  }, [])

  const addToCart = useCallback((product: { productId: number; name: string; price: number; image?: string; origin: CartItemOrigin }) => {
    invalidateCheckout()
    const now = Date.now()
    setItems(prev => {
      const existing = prev.find(i => i.productId === product.productId)
      if (existing) {
        toast(`Updated quantity for ${product.name.substring(0, 30)}...`)
        return prev.map(i =>
          i.productId === product.productId
            ? { ...i, quantity: i.quantity + 1, origin: product.origin, addedAt: now }
            : i
        )
      }
      toast(`Added ${product.name.substring(0, 30)}... to cart`)
      return [...prev, {
        productId: product.productId,
        name: product.name,
        price: product.price,
        quantity: 1,
        image: product.image,
        origin: product.origin,
        addedAt: now,
      }]
    })
    setMetrics(prev => ({
      ...prev,
      additions: [...prev.additions, { origin: product.origin, timestamp: now }],
    }))
    setCartOpen(true)
  }, [invalidateCheckout, toast])

  const addAllToCart = useCallback((products: Array<{ productId: number; name: string; price: number; image?: string }>, origin: CartItemOrigin) => {
    invalidateCheckout()
    const now = Date.now()
    setItems(prev => {
      let updated = [...prev]
      for (const product of products) {
        const idx = updated.findIndex(i => i.productId === product.productId)
        if (idx >= 0) {
          updated = updated.map((item, i) =>
            i === idx ? { ...item, quantity: item.quantity + 1, origin, addedAt: now } : item
          )
        } else {
          updated.push({
            productId: product.productId,
            name: product.name,
            price: product.price,
            quantity: 1,
            image: product.image,
            origin,
            addedAt: now,
          })
        }
      }
      return updated
    })
    // Single event for the entire bundle
    setMetrics(prev => ({
      ...prev,
      additions: [...prev.additions, { origin, timestamp: now }],
    }))
    toast(`Added ${products.length} items to cart`)
    setCartOpen(true)
  }, [invalidateCheckout, toast])

  const updateQuantity = useCallback((productId: number, quantity: number) => {
    invalidateCheckout()
    if (quantity <= 0) {
      setItems(prev => prev.filter(item => item.productId !== productId))
    } else {
      setItems(prev =>
        prev.map(item =>
          item.productId === productId ? { ...item, quantity } : item
        )
      )
    }
  }, [invalidateCheckout])

  const removeFromCart = useCallback((productId: number) => {
    invalidateCheckout()
    setItems(prev => prev.filter(item => item.productId !== productId))
  }, [invalidateCheckout])

  const clearCart = useCallback(() => {
    if (confirm('Are you sure you want to clear your cart?')) {
      invalidateCheckout()
      setItems([])
      toast('Cart cleared')
    }
  }, [invalidateCheckout, toast])

  const setCommerceFailure = useCallback((error: unknown) => {
    const code = error instanceof CommerceApiError ? error.code : 'commerce_unavailable'
    const messages: Record<string, string> = {
      sign_in_required: 'Sign in to review and place this order.',
      auth_failed: 'Your sign-in has expired. Sign in again to continue.',
      product_unavailable: 'One of these pieces is no longer available.',
      inventory_unavailable: 'The requested quantity is no longer available.',
      quote_expired: 'This quote expired. Review the current price and availability.',
      quote_changed: 'The price or availability changed. Review a fresh quote.',
      quote_unavailable: 'This quote can no longer be used.',
      confirmation_expired: 'The confirmation expired. Review the order again.',
      confirmation_already_used: 'This confirmation has already been used.',
      idempotency_key_reused: 'This checkout reference was already used. Try placing the order again.',
      commerce_unavailable: 'Checkout status could not be confirmed. Try again to safely resume this order.',
    }
    setCheckoutError({
      code,
      message: messages[code] ?? 'Checkout status could not be confirmed. Try again to safely resume this order.',
    })
    if ([
      'quote_expired',
      'quote_changed',
      'quote_unavailable',
      'confirmation_expired',
      'confirmation_already_used',
    ].includes(code)) {
      setCheckoutQuote(null)
      executionKeyRef.current = null
      confirmationGrantRef.current = null
    }
    if (code === 'idempotency_key_reused') {
      executionKeyRef.current = null
    }
    setCheckoutStage('error')
  }, [])

  const handleCheckout = useCallback(async () => {
    if (!isAuthenticated) {
      setCommerceFailure(new CommerceApiError('sign_in_required', 401))
      return
    }
    if (items.length === 0) return
    setCheckoutError(null)
    setCheckoutStage('quoting')
    confirmationGrantRef.current = null
    try {
      const sessionId = localStorage.getItem('pellier-session-id') || undefined
      const quote = await createCommerceQuote(
        items.map(item => ({
          productId: item.productId,
          quantity: item.quantity,
        })),
        sessionId,
      )
      executionKeyRef.current =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? `checkout-${crypto.randomUUID()}`
          : `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`
      setCheckoutQuote(quote)
      setCheckoutStage('review')
    } catch (error) {
      setCommerceFailure(error)
    }
  }, [isAuthenticated, items, setCommerceFailure])

  const confirmAndPlaceOrder = useCallback(async () => {
    if (!checkoutQuote) {
      await handleCheckout()
      return
    }
    if (!executionKeyRef.current) {
      executionKeyRef.current =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? `checkout-${crypto.randomUUID()}`
          : `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`
    }
    setCheckoutError(null)
    setCheckoutStage('confirming')
    try {
      const grant =
        confirmationGrantRef.current ?? await confirmCommerceQuote(checkoutQuote)
      confirmationGrantRef.current = grant
      setCheckoutStage('executing')
      const receipt = await executeCommerceOrder(
        grant.confirmationGrantId,
        executionKeyRef.current,
      )
      setCheckoutReceipt(receipt)
      setCheckoutStage('complete')
    } catch (error) {
      setCommerceFailure(error)
    }
  }, [checkoutQuote, handleCheckout, setCommerceFailure])

  const resetCheckout = useCallback(() => {
    const paid = checkoutReceipt?.status === 'paid'
    if (paid) {
      setItems([])
      setCartOpen(false)
      toast(`${checkoutReceipt.orderNumber} is complete`)
    }
    invalidateCheckout()
  }, [checkoutReceipt, invalidateCheckout, toast])

  const incrementSearch = useCallback(() => {
    setMetrics(prev => ({ ...prev, searchCount: prev.searchCount + 1 }))
  }, [])

  const incrementProductView = useCallback(() => {
    setMetrics(prev => ({ ...prev, productViews: prev.productViews + 1 }))
  }, [])

  return (
    <CartContext.Provider value={{
      items,
      metrics,
      previousModeSteps,
      cartOpen,
      setCartOpen,
      showToast,
      toastMessage,
      dismissToast,
      notify: toast,
      addToCart,
      addAllToCart,
      updateQuantity,
      removeFromCart,
      clearCart,
      handleCheckout,
      confirmAndPlaceOrder,
      checkoutStage,
      checkoutQuote,
      checkoutReceipt,
      checkoutError,
      checkoutComplete: checkoutStage === 'complete',
      resetCheckout,
      incrementSearch,
      incrementProductView,
    }}>
      {children}
    </CartContext.Provider>
  )
}
