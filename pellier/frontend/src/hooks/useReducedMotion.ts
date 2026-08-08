/**
 * Respect the OS "reduce motion" setting in JavaScript-driven animation.
 *
 * CSS animations are already guarded by `@media (prefers-reduced-motion)`
 * in the stylesheets, but Framer Motion variants, streaming typewriter
 * effects, and auto-rotating content are decided in JS and need to ask.
 *
 * Returns `false` during SSR/tests where `matchMedia` is unavailable —
 * i.e. it does not claim a preference it could not read.
 */
import { useEffect, useState } from 'react'

const QUERY = '(prefers-reduced-motion: reduce)'

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia(QUERY).matches
  })

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia(QUERY)
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches)
    // `addEventListener` is the modern API; older Safari needs addListener.
    if (mq.addEventListener) {
      mq.addEventListener('change', onChange)
      return () => mq.removeEventListener('change', onChange)
    }
    mq.addListener(onChange)
    return () => mq.removeListener(onChange)
  }, [])

  return reduced
}

export default useReducedMotion
