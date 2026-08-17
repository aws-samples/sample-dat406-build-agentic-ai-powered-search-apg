/**
 * BoutiqueSpotlight — guided first-visit walkthrough for the boutique.
 *
 * A three-step, once-per-session orientation for the one-hour workshop.
 * It introduces the shopper point of view, the real concierge interaction,
 * and the optional evidence surface without teaching the whole application.
 *
 * Keyboard: Escape dismisses. ArrowRight advances. ArrowLeft goes back.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { cssVar as c } from '../design/cssVars'


interface SpotlightStep {
  numeral: string
  kicker: string
  headline: string
  body: string
}

const STEPS: SpotlightStep[] = [
  {
    numeral: 'I',
    kicker: 'Start with a shopper',
    headline: 'Choose the point of view',
    body: 'Browse the fresh edit, or choose Marco, Anna, or Theo. Each profile changes the catalog signals and the workshop story.',
  },
  {
    numeral: 'II',
    kicker: 'Your concierge',
    headline: 'Ask Pellier',
    body: 'Use the hero prompt or open the concierge and ask in your own words. The answer is grounded in the live boutique and its deterministic tools.',
  },
  {
    numeral: 'III',
    kicker: 'Optional evidence',
    headline: 'Verify the answer',
    body: 'Open Pellier Labs after a turn to inspect routing, tools, retrieval, and Aurora evidence. The timed workshop keeps this surface optional.',
  },
]

const FINAL_CTA = 'Explore Pellier'

// One-shot gate: once the visitor dismisses the spotlight in a
// session, don't re-show it on route changes or refreshes within
// the same tab. sessionStorage is the right shelf for this — it
// clears when the tab closes so a fresh session still gets the
// walkthrough.
const SPOTLIGHT_SEEN_KEY = 'pellier-storefront-spotlight-seen'

function hasSeenSpotlight(): boolean {
  if (typeof window === 'undefined') return true
  try {
    return window.sessionStorage.getItem(SPOTLIGHT_SEEN_KEY) === 'true'
  } catch {
    // private mode / storage disabled — skip rather than re-show
    // forever. Losing the gate is safer than spamming the overlay.
    return true
  }
}

function markSpotlightSeen(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(SPOTLIGHT_SEEN_KEY, 'true')
  } catch {
    /* noop */
  }
}

export default function BoutiqueSpotlight() {
  // Initialize from sessionStorage so the overlay stays dismissed
  // across the lifetime of a tab.
  const [visible, setVisible] = useState(() => !hasSeenSpotlight())
  const [step, setStep] = useState(0)
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const reduceMotion = Boolean(useReducedMotion())

  const dismiss = useCallback(() => {
    markSpotlightSeen()
    setVisible(false)
  }, [])

  const next = useCallback(() => {
    if (step < STEPS.length - 1) setStep((s) => s + 1)
    else dismiss()
  }, [step, dismiss])

  const prev = useCallback(() => {
    if (step > 0) setStep((s) => s - 1)
  }, [step])

  useEffect(() => {
    if (!visible) return
    const previousOverflow = document.body.style.overflow
    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    document.body.style.overflow = 'hidden'
    dialogRef.current?.focus()
    return () => {
      document.body.style.overflow = previousOverflow
      previousFocusRef.current?.focus()
    }
  }, [visible])

  useEffect(() => {
    if (!visible) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismiss()
      if (e.key === 'ArrowRight') next()
      if (e.key === 'ArrowLeft') prev()
      if (e.key === 'Tab') {
        const focusable = Array.from(
          dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled)') ?? [],
        )
        const first = focusable[0]
        const last = focusable.at(-1)
        if (!first || !last) return
        if (e.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [visible, dismiss, next, prev])

  if (!visible) return null

  const current = STEPS[step]
  const isLast = step === STEPS.length - 1

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[999] flex items-center justify-center p-4"
        style={{
          background: 'rgba(31, 20, 16, 0.52)',
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.18 }}
        onClick={dismiss}
      >
        <motion.div
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="boutique-tour-title"
          aria-describedby="boutique-tour-description"
          tabIndex={-1}
          className="relative w-full max-w-[460px] overflow-hidden rounded-[8px] outline-none"
          style={{
            background: c.bg,
            border: '1px solid rgba(45, 24, 16, 0.08)',
            boxShadow: '0 25px 60px rgba(45, 24, 16, 0.18)',
          }}
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 20, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.98 }}
          transition={
            reduceMotion
              ? { duration: 0 }
              : { type: 'spring', stiffness: 340, damping: 30 }
          }
          onClick={(e) => e.stopPropagation()}
        >
          {/* Editorial numeral mark — replaces the icon badge */}
          <div className="flex items-center justify-center pt-12 pb-2">
            <div
              className="leading-none select-none"
              style={{
                fontFamily: 'Fraunces, Georgia, serif',
                fontWeight: 300,
                fontStyle: 'italic',
                color: c.accent,
                fontSize: 64,
                letterSpacing: 0,
              }}
            >
              {current.numeral}
            </div>
          </div>

          {/* Content */}
          <div className="px-8 pb-3 text-center">
            <p
              className="text-[10px] font-medium uppercase mb-3"
              style={{ color: c.accent, letterSpacing: 0 }}
            >
              {current.kicker}
            </p>
            <h2
              id="boutique-tour-title"
              className="text-[32px] leading-[1.1] mb-4"
              style={{
                fontFamily: 'Fraunces, Georgia, serif',
                fontWeight: 400,
                fontStyle: 'italic',
                color: c.ink,
                letterSpacing: 0,
              }}
            >
              {current.headline}
            </h2>
            <p
              id="boutique-tour-description"
              className="text-[15px] leading-[1.7] mx-auto"
              style={{ color: c.ink2, maxWidth: 360 }}
            >
              {current.body}
            </p>
          </div>

          {/* Footer — dots + navigation */}
          <div className="px-8 pt-4 pb-8 flex items-center justify-between">
            {/* Step dots */}
            <div className="flex items-center gap-2">
              {STEPS.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setStep(i)}
                  aria-label={`Step ${i + 1}`}
                  aria-current={i === step ? 'step' : undefined}
                  className="rounded-full transition-all duration-200"
                  style={{
                    width: i === step ? 20 : 7,
                    height: 7,
                    background:
                      i === step
                        ? c.accent
                        : 'color-mix(in srgb, var(--ink-quiet) 50%, transparent)',
                  }}
                />
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              {step > 0 && (
                <button
                  type="button"
                  onClick={prev}
                  className="rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors"
                  style={{ color: c.ink2 }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = c.paper)
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = 'transparent')
                  }
                >
                  Back
                </button>
              )}
              {!isLast && (
                <button
                  type="button"
                  onClick={dismiss}
                  className="rounded-[8px] px-3 py-1.5 text-[13px]"
                  style={{ color: c.muted }}
                >
                  Skip tour
                </button>
              )}
              <button
                type="button"
                onClick={next}
                className="inline-flex items-center gap-1.5 rounded-[8px] px-5 py-2 text-[13px] font-medium transition-colors"
                style={{ background: c.ink, color: c.bg }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = 'var(--ink)')
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = c.ink)
                }
              >
                {isLast ? FINAL_CTA : 'Next'}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
