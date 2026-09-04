/**
 * ChatDrawer — right-side chat drawer for the storefront.
 *
 * The storefront's only conversational surface. Slides in from the right at
 * 240ms ease-out; backdrop dims the storefront to 35%
 * espresso. Matches docs/storefront-hero-drawer.html State 3.
 *
 * Three entry points (all external — the drawer itself is passive):
 *   1. Floating CommandPill click → ``activeModal === 'drawer'``
 *   2. ⌘K shortcut → same (UIProvider routes to 'drawer' on storefront)
 *   3. Suggestion pill click → ``openDrawerWithQuery(text)``
 *
 * Mounts via ``createPortal(..., document.body)`` — mandatory because
 * the storefront header's ``backdrop-filter: blur(12px)`` creates a
 * containing block that traps ``position: fixed`` descendants (same
 * bug we hit with PersonaModal).
 *
 * Reuses ``useAgentChat`` for state, streaming, and persistence.
 * Observatory and Operator do not mount this component: their evidence and
 * operational workflows remain scoped to their own surfaces.
 */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import {
  ArrowUp,
  LoaderCircle,
  MessageCircle,
  Trash2,
  X,
} from 'lucide-react'
import { useUI } from '../contexts/UIContext'
import { useLayout } from '../contexts/LayoutContext'
import { useCart } from '../contexts/CartContext'
import { usePersona } from '../contexts/PersonaContext'
import {
  useAgentChat,
  type AgentChatMessage,
} from '../hooks/useAgentChat'
import PellierChatBody from './PellierChatBody'
import PellierWelcome from './PellierWelcome'
import StatusLines from './StatusLines'
import '../styles/chat-drawer.css'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const FRESH_GREETING =
  "Welcome to Pellier. I'm your personal shopping concierge. Tell me what you're looking for and I'll find the right pieces for you."
const RETURNING_GREETING =
  "Welcome back. Tell me what you're looking for and I'll find the right pieces for you."

// ---------------------------------------------------------------------------
// Platform detection for keyboard hint
// ---------------------------------------------------------------------------

function detectMac(): boolean {
  if (typeof navigator === 'undefined') return false
  const uaData = (navigator as unknown as {
    userAgentData?: { platform?: string }
  }).userAgentData
  const platform = uaData?.platform ?? navigator.platform ?? ''
  return /mac|iphone|ipad|ipod/i.test(platform)
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ChatDrawer() {
  const { activeModal, closeModal, openModal, consumePendingQuery } = useUI()
  const { guardrailsEnabled } = useLayout()
  const { addToCart } = useCart()
  const { persona } = usePersona()

  const isOpen = activeModal === 'drawer'
  const reducedMotion = useReducedMotion()
  const [isMac, setIsMac] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const openerRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    setIsMac(detectMac())
  }, [])

  // Persona-first workshop flow: when signed out, hide chat surfaces.
  useEffect(() => {
    if (!persona && isOpen) {
      closeModal()
    }
  }, [persona, isOpen, closeModal])

  // First-turn greeting stays generic. Personal claims belong to the Aurora
  // profile context that the backend loads for a concrete shopper request.
  const initialMessages = useMemo<AgentChatMessage[]>(() => {
    const firstName = persona ? persona.display_name.split(' ')[0] : ''
    const h = new Date().getHours()
    const tod = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
    const content = persona && persona.id !== 'fresh'
      ? `${tod}, ${firstName}. ${RETURNING_GREETING}`
      : FRESH_GREETING
    return [
      {
        role: 'assistant',
        content,
        timestamp: new Date(),
      },
    ]
  }, [persona])

  // Read session ID for AgentCore STM hydration — same ID the backend
  // uses to scope the conversation namespace.
  const currentSessionId = (() => {
    try { return localStorage.getItem('pellier-session-id') ?? undefined }
    catch { return undefined }
  })()

  const {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    sendMessage,
    retryMessage,
    clearChat,
  } = useAgentChat({
    mode: 'storefront',
    guardrailsEnabled,
    initialMessages,
    persistKey: 'pellier-drawer-storefront',
    sessionId: currentSessionId,
  })

  // Clear the conversation when the persona changes so the new
  // persona's welcome screen and LTM context take effect immediately.
  const prevPersonaId = useRef(persona?.id ?? null)
  useEffect(() => {
    const currentId = persona?.id ?? null
    if (prevPersonaId.current !== currentId) {
      prevPersonaId.current = currentId
      clearChat(initialMessages)
    }
  }, [persona?.id, clearChat, initialMessages])

  // Turn count (user messages only)
  const turnCount = messages.filter(m => m.role === 'user').length

  // Focus input on open
  useEffect(() => {
    if (!isOpen) return
    openerRef.current = document.activeElement as HTMLElement
    const t = setTimeout(() => inputRef.current?.focus(), 50)
    return () => clearTimeout(t)
  }, [isOpen])

  // Return focus on close
  useEffect(() => {
    if (isOpen) return
    openerRef.current?.focus()
    openerRef.current = null
  }, [isOpen])

  // Consume pending query (from suggestion pill click).
  //
  // Uses useLayoutEffect (not useEffect) so the pending query is
  // consumed and sendMessage fires BEFORE the browser paints the first
  // frame. This prevents a one-frame flicker where the empty-state
  // ("What can Pellier help you find today?") renders before the user
  // message appears. sendMessage adds the user message to state
  // synchronously (via setMessages) so the first visible paint already
  // shows the user bubble + the "thinking" placeholder.
  // A pending query adds to the active thread. Storefront suggestions are
  // follow-on shopping questions, so clearing the conversation here silently
  // discarded the shopper's context.
  const hasConsumedRef = useRef(false)
  useLayoutEffect(() => {
    if (!isOpen) {
      hasConsumedRef.current = false
      return
    }
    if (hasConsumedRef.current) return
    hasConsumedRef.current = true
    const seeded = consumePendingQuery()
    if (seeded) {
      void sendMessage(seeded)
    }
  }, [isOpen, consumePendingQuery, sendMessage])

  // Auto-scroll
  const messagesEndRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!isOpen) return
    // This drawer is an active concierge conversation. A long streamed answer
    // can move the end marker more than 120px in one render, so a "near bottom"
    // check made turn 02/03 appear stuck on turn 01. Follow every active update;
    // once streaming stops, the shopper can still scroll back through history.
    const t = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }, 50)
    return () => clearTimeout(t)
  }, [messages, isOpen])

  // Focus trap: Tab/Shift+Tab cycle within drawer
  const drawerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!isOpen) return
    const el = drawerRef.current
    if (!el) return
    const handler = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return
      const focusable = el.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen])

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
        e.preventDefault()
        sendMessage()
      }
    },
    [isLoading, sendMessage],
  )

  const hasUserMessages = messages.some(m => m.role === 'user')
  const keycap = isMac ? '⌘K' : 'Ctrl+K'

  useLayoutEffect(() => {
    const input = inputRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(input.scrollHeight, 104)}px`
  }, [inputValue])

  if (!persona) return null

  return createPortal(
    <>
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="cd-backdrop"
            data-testid="chat-drawer-backdrop"
            initial={reducedMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={reducedMotion ? { duration: 0 } : { duration: 0.24 }}
            onClick={() => closeModal()}
          />

          {/* Drawer */}
          <motion.div
            ref={drawerRef}
            className="cd-drawer"
            data-testid="chat-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Chat with Pellier"
            initial={reducedMotion ? false : { x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={reducedMotion
              ? { duration: 0 }
              : { duration: 0.24, ease: [0.4, 0, 0.2, 1] }}
          >
            {/* Mobile drag handle (decorative) */}
            <div className="cd-drag-handle" aria-hidden />

            {/* Header */}
            <div className="cd-head">
              <div className="cd-head-stack">
                <div className="cd-head-eyebrow">Concierge</div>
                <h3 className="cd-head-title">
                  Ask <em>Pellier.</em>
                </h3>
                <div className="cd-head-meta">
                  {persona && persona.id !== 'fresh' && (
                    <>
                      <span className="cd-persona-mark">
                        <span
                          className="cd-persona-av"
                          style={{
                            background: persona.avatar_color,
                            color: '#F7F3EE',
                          }}
                        >
                          {persona.avatar_initial}
                        </span>
                        <span className="cd-persona-name">
                          {persona.display_name.split(' ')[0]}
                        </span>
                      </span>
                      <span className="cd-meta-sep">·</span>
                    </>
                  )}
                  <span>
                    turn {String(turnCount).padStart(2, '0')}
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="cd-close"
                aria-label="Close drawer"
                onClick={() => closeModal()}
              >
                <X size={14} />
              </button>
            </div>

            {/* Three facts, three sources: scenario, verified identity, rail. */}
            <StatusLines messages={messages} />

            {/* Body */}
            <div className="cd-body">
              {!hasUserMessages && (
                <PellierWelcome
                  persona={persona}
                  onSend={(text) => void sendMessage(text)}
                />
              )}
              {hasUserMessages && (
                <PellierChatBody
                  messages={messages}
                  sendMessage={sendMessage}
                  retryMessage={retryMessage}
                  onEditRequest={(text) => {
                    setInputValue(text)
                    window.requestAnimationFrame(() => inputRef.current?.focus())
                  }}
                  onAuthenticate={() => openModal('auth')}
                  addToCart={addToCart}
                  persona={persona}
                />
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Footer */}
            <div className="cd-foot">
              <div className="cd-input-row">
                <textarea
                  ref={inputRef}
                  className="cd-input"
                  rows={1}
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  onKeyDown={handleKeyPress}
                  aria-label="Message Pellier"
                  placeholder={
                    hasUserMessages
                      ? 'Continue the conversation…'
                      : "Tell Pellier what you're looking for…"
                  }
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="cd-send"
                  disabled={!inputValue.trim() || isLoading}
                  aria-label={isLoading ? 'Pellier is responding' : 'Ask Pellier'}
                  title={isLoading ? 'Pellier is responding' : 'Ask Pellier'}
                  data-loading={isLoading}
                  onClick={() => sendMessage()}
                >
                  {isLoading ? (
                    <LoaderCircle size={16} aria-hidden="true" />
                  ) : (
                    <ArrowUp size={16} aria-hidden="true" />
                  )}
                </button>
              </div>
              <div className="cd-foot-meta">
                <span>
                  {`Esc to close · ${keycap} to focus`}
                </span>
                <span>Conversation persists this session</span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>

    {/* "Continue chat" pill — shows when drawer is closed but has
        an active conversation. Gives the user a way to reopen or clear
        the persisted storefront thread. */}
    <AnimatePresence>
      {!isOpen && hasUserMessages && (
        <motion.div
          data-testid="continue-chat-pill"
          initial={reducedMotion ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={reducedMotion ? { duration: 0 } : { duration: 0.25, delay: 0.3 }}
          className="cd-continue-shell"
        >
          <button
            type="button"
            className="cd-continue-main"
            onClick={() => openModal('drawer')}
          >
            <MessageCircle size={16} aria-hidden="true" />
            <span>Continue chat</span>
            <span className="cd-continue-key">{keycap}</span>
          </button>
          <button
            type="button"
            className="cd-continue-clear"
            onClick={() => clearChat(initialMessages)}
            aria-label="Clear chat"
            title="Clear chat"
          >
            <Trash2 size={15} aria-hidden="true" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
    </>,
    document.body,
  )
}
