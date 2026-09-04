/**
 * PellierSpotlight - the first-visit orientation for the governed storefront.
 *
 * It frames Pellier the way the architecture actually works: a Storefront
 * Dispatcher routing shopper turns to specialists, a separate two-agent
 * Operator Concierge graph, shared Aurora customer truth, and every
 * state-changing action behind a human confirmation.
 *
 * Claims here are deliberately limited to what ships. Comparable retail-agent
 * architectures spread this across four engines (a vector index, a key-value
 * store, an external cache); Pellier does it in Aurora PostgreSQL alone, so
 * the copy says Aurora and names no service this app does not use. It also
 * does not mention promotions or notifications, which are not implemented.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, X } from 'lucide-react'
import { imageSrc } from '../utils/assetPath'

interface SpotlightStep {
  label: string
  eyebrow: string
  headline: string
  body: string
  image: string
  imageAlt: string
}

const STEPS: SpotlightStep[] = [
  {
    label: 'Choose',
    eyebrow: 'Welcome to Pellier',
    headline: 'Begin with the edit.',
    body: 'Choose a point of view, then browse a collection shaped by the details that matter to that shopper.',
    image: '/products/marco-leather-weekend-holdall-960.webp',
    imageAlt: 'Leather Weekend Holdall on travertine beside folded linen in warm daylight',
  },
  {
    label: 'Ask',
    eyebrow: 'Ask Pellier',
    headline: 'Use your own words.',
    body: 'Ask for a piece or occasion. Pellier reads the current catalog and your chosen point of view before it recommends a place to start.',
    image: '/products/hero-anna.png',
    imageAlt: 'Wrapped gift, beeswax candles, and a ceramic ring dish',
  },
  {
    label: 'Trace',
    eyebrow: 'Operator and Observatory',
    headline: 'Follow the evidence.',
    body: 'When a recommendation becomes a case, the Operator workspace and Observatory follow the evidence from grounded answers through retrieval, managed execution, policy, and Aurora.',
    image: '/products/tour-observatory-top-panel-960.png',
    imageAlt: 'Pellier Observatory top panel with the current four-stage evidence journey',
  },
]

export const SPOTLIGHT_SEEN_KEY = 'pellier-storefront-spotlight-seen'
const SPOTLIGHT_SEEN_EVENT = 'pellier:spotlight-seen'
const MOTION_EASE: [number, number, number, number] = [0.16, 1, 0.3, 1]
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function hasSeenSpotlight(): boolean {
  if (typeof window === 'undefined') return true
  try {
    return window.sessionStorage.getItem(SPOTLIGHT_SEEN_KEY) === 'true'
  } catch {
    return true
  }
}

function markSpotlightSeen(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(SPOTLIGHT_SEEN_KEY, 'true')
  } catch {
    // Storage is optional. Do not trap the visitor in the tour.
  }
  window.dispatchEvent(new Event(SPOTLIGHT_SEEN_EVENT))
}

/**
 * Whether the welcome tour has already run this session. The hero used to
 * keep its "Who are you shopping for?" chooser on screen behind the tour and
 * after it, so a first visit asked the persona question three times (tour,
 * hero card, header pill). Once the tour has been seen, the header pill is the
 * persistent mechanism and the hero card retires.
 */
export function useSpotlightSeen(): boolean {
  const [seen, setSeen] = useState<boolean>(() => hasSeenSpotlight())
  useEffect(() => {
    const sync = () => setSeen(hasSeenSpotlight())
    window.addEventListener(SPOTLIGHT_SEEN_EVENT, sync)
    return () => window.removeEventListener(SPOTLIGHT_SEEN_EVENT, sync)
  }, [])
  return seen
}

export default function PellierSpotlight() {
  const [visible, setVisible] = useState(() => !hasSeenSpotlight())
  const [step, setStep] = useState(0)
  const dialogRef = useRef<HTMLDivElement>(null)
  const openerRef = useRef<HTMLElement | null>(null)
  const reduceMotion = Boolean(useReducedMotion())

  const dismiss = useCallback(() => {
    markSpotlightSeen()
    setVisible(false)
  }, [])

  const next = useCallback(() => {
    if (step < STEPS.length - 1) {
      setStep((current) => current + 1)
      return
    }
    dismiss()
  }, [dismiss, step])

  const previous = useCallback(() => {
    if (step > 0) setStep((current) => current - 1)
  }, [step])

  useEffect(() => {
    if (!visible) return
    const previousOverflow = document.body.style.overflow
    openerRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null
    document.body.style.overflow = 'hidden'
    dialogRef.current?.focus()
    return () => {
      document.body.style.overflow = previousOverflow
      if (openerRef.current?.isConnected) {
        openerRef.current.focus()
      }
    }
  }, [visible])

  useEffect(() => {
    if (!visible) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        const dialog = dialogRef.current
        if (!dialog) return
        const focusable = Array.from(
          dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
        )
        if (focusable.length === 0) {
          event.preventDefault()
          dialog.focus()
          return
        }

        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        const active = document.activeElement
        if (
          event.shiftKey &&
          (active === first || active === dialog || !dialog.contains(active))
        ) {
          event.preventDefault()
          last.focus()
        } else if (
          !event.shiftKey &&
          (active === last || !dialog.contains(active))
        ) {
          event.preventDefault()
          first.focus()
        }
        return
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        dismiss()
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        next()
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        previous()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [dismiss, next, previous, visible])

  if (!visible) return null

  const current = STEPS[step]
  const isLast = step === STEPS.length - 1
  const currentImageSrc = imageSrc(current.image)

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[999] flex items-center justify-center bg-[rgba(24,26,31,0.48)] p-4 sm:p-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reduceMotion ? 0.1 : 0.18, ease: MOTION_EASE }}
        onClick={dismiss}
      >
        <motion.div
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="pellier-spotlight-title"
          aria-describedby="pellier-spotlight-description"
          tabIndex={-1}
          className="relative w-full max-w-[552px] overflow-hidden rounded-[8px] border border-[rgba(24,26,31,0.16)] bg-cream-warm text-espresso shadow-[0_28px_70px_rgba(24,26,31,0.26)] outline-none"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.985 }}
          animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
          exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 10, scale: 0.99 }}
          transition={{
            duration: reduceMotion ? 0.1 : 0.24,
            ease: MOTION_EASE,
          }}
          onClick={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            aria-label="Skip welcome tour"
            onClick={dismiss}
            className="absolute right-3 top-3 z-10 inline-flex h-12 w-12 items-center justify-center rounded-[8px] border border-white/30 bg-[rgba(24,26,31,0.56)] text-white transition-colors hover:bg-[rgba(24,26,31,0.78)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[rgba(24,26,31,0.56)]"
          >
            <X size={17} strokeWidth={1.8} aria-hidden="true" />
          </button>

          <div className="h-[194px] overflow-hidden bg-cream-2 sm:h-[208px]">
            <AnimatePresence initial={false} mode="wait">
              <motion.img
                key={current.image}
                src={currentImageSrc}
                alt={current.imageAlt}
                className="h-full w-full object-cover"
                initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 1.035 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 1.02 }}
                transition={{
                  duration: reduceMotion ? 0.1 : 0.28,
                  ease: MOTION_EASE,
                }}
              />
            </AnimatePresence>
          </div>

          <div className="relative px-6 pb-2 pt-0 sm:px-8">
            <AnimatePresence initial={false} mode="wait">
              <motion.div
                key={current.label}
                className="pt-6"
                initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 7 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -5 }}
                transition={{
                  duration: reduceMotion ? 0.1 : 0.2,
                  ease: MOTION_EASE,
                }}
              >
                <div className="mb-3 flex items-baseline gap-3">
                  <span
                    aria-hidden="true"
                    className="text-[18px] leading-none text-accent"
                    style={{ fontFamily: 'var(--display)' }}
                  >
                    {String(step + 1).padStart(2, '0')}
                  </span>
                  <p className="font-sans text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
                    {current.eyebrow}
                  </p>
                </div>
                <h2
                  id="pellier-spotlight-title"
                  className="max-w-[18ch] text-[34px] font-normal leading-[1.03] text-espresso sm:text-[38px]"
                  style={{ fontFamily: 'var(--display)' }}
                >
                  {current.headline}
                </h2>
                <p
                  id="pellier-spotlight-description"
                  className="mt-3 max-w-[39ch] font-sans text-[15px] leading-6 text-ink-soft"
                >
                  {current.body}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-t border-sand px-6 py-4 sm:px-8">
            <nav className="flex items-center gap-2.5" aria-label="Welcome tour progress">
              <span
                aria-hidden="true"
                className="font-sans text-[10px] font-semibold tracking-[0.14em] text-ink-quiet"
              >
                01
              </span>
              {STEPS.map((tourStep, index) => (
                <button
                  key={tourStep.label}
                  type="button"
                  onClick={() => setStep(index)}
                  aria-label={`Show ${tourStep.label}, step ${index + 1} of ${STEPS.length}`}
                  aria-current={index === step ? 'step' : undefined}
                  className="group inline-flex h-12 w-12 items-center justify-center rounded-[8px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
                >
                  <span
                    aria-hidden="true"
                    className={[
                      'block h-px transition-[width,background-color] duration-200',
                      index === step
                        ? 'w-7 bg-espresso'
                        : 'w-4 bg-[rgba(24,26,31,0.18)] group-hover:bg-[rgba(24,26,31,0.36)]',
                    ].join(' ')}
                  />
                </button>
              ))}
              <span
                aria-hidden="true"
                className="font-sans text-[10px] font-semibold tracking-[0.14em] text-ink-quiet"
              >
                03
              </span>
            </nav>

            <div className="flex items-center gap-2">
              {step > 0 ? (
                <button
                  type="button"
                  onClick={previous}
                  className="min-h-12 rounded-[8px] px-3.5 font-sans text-[13px] font-medium text-ink-soft transition-colors hover:bg-cream-2 hover:text-espresso focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
                >
                  Back
                </button>
              ) : (
                <button
                  type="button"
                  onClick={dismiss}
                  className="min-h-12 rounded-[8px] px-3.5 font-sans text-[13px] font-medium text-ink-soft transition-colors hover:bg-cream-2 hover:text-espresso focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
                >
                  Skip
                </button>
              )}
              <button
                type="button"
                onClick={next}
                className="inline-flex min-h-12 items-center gap-2 rounded-[8px] bg-accent px-4 font-sans text-[13px] font-semibold text-white transition-colors hover:bg-accent-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
              >
                {isLast ? 'Explore Pellier' : 'Continue'}
                <ArrowRight size={15} strokeWidth={1.8} aria-hidden="true" />
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
