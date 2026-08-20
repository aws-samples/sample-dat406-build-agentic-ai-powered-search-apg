/**
 * PellierSpotlight - the four-screen first-visit orientation for the
 * governed storefront. It explains the shopper path without interrupting the
 * Labs proof surface or making claims that have not happened yet.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import {
  ArrowRight,
  FlaskConical,
  MessageCircle,
  Store,
  User,
  X,
  type LucideIcon,
} from 'lucide-react'
import { asset } from '../utils/assetPath'

interface SpotlightStep {
  label: string
  eyebrow: string
  headline: string
  body: string
  image: string
  imageAlt: string
  icon: LucideIcon
}

const STEPS: SpotlightStep[] = [
  {
    label: 'Browse',
    eyebrow: 'Welcome to Pellier',
    headline: 'Begin with the edit.',
    body: 'Browse the current collection or start with a specific piece you have in mind.',
    image: asset('/products/hero-fresh-2.png'),
    imageAlt: 'Pellier leather tote, linen, and olive branches in warm daylight',
    icon: Store,
  },
  {
    label: 'Personalize',
    eyebrow: 'Choose a profile',
    headline: 'Make the floor personal.',
    body: 'Choose Marco, Anna, or Theo in the hero. Each profile applies its own explicit catalog signals.',
    image: asset('/products/hero-marco.png'),
    imageAlt: 'Leather weekender and folded linen shirts in warm daylight',
    icon: User,
  },
  {
    label: 'Ask',
    eyebrow: 'Ask Pellier',
    headline: 'Use your own words.',
    body: 'Search from the hero or open the concierge from the header when you are ready to compare pieces.',
    image: asset('/products/hero-anna.png'),
    imageAlt: 'Wrapped gift, beeswax candles, and a ceramic ring dish',
    icon: MessageCircle,
  },
  {
    label: 'Inspect',
    eyebrow: 'Pellier Observatory',
    headline: 'See the governed path.',
    body: 'Open Labs to inspect the tool calls, policy decision, and evidence from a completed turn.',
    image: asset('/products/hero-theo.png'),
    imageAlt: 'Stoneware pour-over set on a sunlit wooden table',
    icon: FlaskConical,
  },
]

const SPOTLIGHT_SEEN_KEY = 'pellier-storefront-spotlight-seen'
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
  const CurrentIcon = current.icon
  const isLast = step === STEPS.length - 1

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
          className="relative w-full max-w-[500px] overflow-hidden rounded-[8px] border border-[rgba(24,26,31,0.16)] bg-cream-warm text-espresso shadow-[0_28px_70px_rgba(24,26,31,0.26)] outline-none"
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
            className="absolute right-3 top-3 z-10 inline-flex h-9 w-9 items-center justify-center rounded-[8px] border border-white/30 bg-[rgba(24,26,31,0.56)] text-white transition-colors hover:bg-[rgba(24,26,31,0.78)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[rgba(24,26,31,0.56)]"
          >
            <X size={17} strokeWidth={1.8} aria-hidden="true" />
          </button>

          <div className="h-[172px] overflow-hidden bg-cream-2">
            <AnimatePresence initial={false} mode="wait">
              <motion.img
                key={current.image}
                src={current.image}
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
            <div className="-mt-6 flex h-12 w-12 items-center justify-center rounded-[8px] border border-[rgba(24,26,31,0.16)] bg-cream-warm text-accent shadow-[0_8px_20px_rgba(24,26,31,0.11)]">
              <CurrentIcon size={21} strokeWidth={1.7} aria-hidden="true" />
            </div>

            <AnimatePresence initial={false} mode="wait">
              <motion.div
                key={current.label}
                className="pt-5"
                initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 7 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -5 }}
                transition={{
                  duration: reduceMotion ? 0.1 : 0.2,
                  ease: MOTION_EASE,
                }}
              >
                <p className="mb-2 font-sans text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
                  {current.eyebrow}
                </p>
                <h2
                  id="pellier-spotlight-title"
                  className="max-w-[18ch] font-sans text-[30px] font-semibold leading-[1.08] text-espresso sm:text-[34px]"
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

          <div className="mt-6 flex items-center justify-between border-t border-sand px-6 py-4 sm:px-8">
            <nav className="flex items-center gap-1.5" aria-label="Welcome tour progress">
              {STEPS.map((tourStep, index) => (
                <button
                  key={tourStep.label}
                  type="button"
                  onClick={() => setStep(index)}
                  aria-label={`Show ${tourStep.label}`}
                  aria-current={index === step ? 'step' : undefined}
                  className={[
                    'h-2 rounded-full transition-[width,background-color] duration-200',
                    index === step
                      ? 'w-7 bg-accent'
                      : 'w-2 bg-[rgba(24,26,31,0.18)] hover:bg-[rgba(24,26,31,0.36)]',
                  ].join(' ')}
                />
              ))}
            </nav>

            <div className="flex items-center gap-2">
              {step > 0 ? (
                <button
                  type="button"
                  onClick={previous}
                  className="min-h-10 rounded-[8px] px-3.5 font-sans text-[13px] font-medium text-ink-soft transition-colors hover:bg-cream-2 hover:text-espresso focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
                >
                  Back
                </button>
              ) : (
                <button
                  type="button"
                  onClick={dismiss}
                  className="min-h-10 rounded-[8px] px-3.5 font-sans text-[13px] font-medium text-ink-soft transition-colors hover:bg-cream-2 hover:text-espresso focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
                >
                  Skip
                </button>
              )}
              <button
                type="button"
                onClick={next}
                className="inline-flex min-h-10 items-center gap-2 rounded-[8px] bg-accent px-4 font-sans text-[13px] font-semibold text-white transition-colors hover:bg-accent-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
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
