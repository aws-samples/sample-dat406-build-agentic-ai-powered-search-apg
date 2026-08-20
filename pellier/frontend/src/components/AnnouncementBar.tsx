/**
 * AnnouncementBar — storefront service strip above the sticky header.
 *
 * Cycles through editorial "just in" findings every 5 seconds with a
 * smooth vertical crossfade. Each line reads like a concierge aside —
 * the agent quietly surfacing what it noticed while watching the floor.
 *
 * A pulse dot on the left, a small-caps-style verb (NEW ARRIVALS /
 * RESTOCKED / SERVICE) in sans semibold + wide tracking, and body copy
 * in cream. Pellier keeps this retail-facing; Pellier Observatory carries the
 * proof and trace vocabulary.
 *
 * Copy lives in copy.ts so the rotating strip stays aligned with the
 * current catalog and proof language.
 */
import { useState, useEffect } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { LIVE_FLOOR_FINDINGS } from '../copy'
import { cssVar as c } from '../design/cssVars'

const MONO_STACK = 'var(--mono)'

const CYCLE_MS = 5000

export default function AnnouncementBar() {
  const [index, setIndex] = useState(0)
  const reduceMotion = useReducedMotion()
  const finding = LIVE_FLOOR_FINDINGS[index]

  useEffect(() => {
    if (reduceMotion) return
    const t = setInterval(() => {
      setIndex((i) => (i + 1) % LIVE_FLOOR_FINDINGS.length)
    }, CYCLE_MS)
    return () => clearInterval(t)
  }, [reduceMotion])

  return (
    <div
      role="region"
      aria-label="Storefront announcements"
      data-testid="announcement-bar"
      className="w-full relative overflow-hidden"
      style={{
        background: c.ink,
        color: c.bg,
        fontFamily: 'var(--sans)',
        fontSize: '12.5px',
        letterSpacing: '0.04em',
        lineHeight: 1.2,
        padding: '0 24px',
        height: 44,
        fontWeight: 400,
      }}
    >
      {/* Pulse dot — agent presence cue, anchored left of the rotating copy */}
      <span
        aria-hidden="true"
        data-testid="announcement-pulse"
        style={{
          position: 'absolute',
          left: 24,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 8,
          height: 8,
          borderRadius: 999,
          background: c.accent,
          zIndex: 1,
        }}
      >
        <style>{`
          @keyframes pelliers-floor-pulse {
            0% { transform: scale(0.6); opacity: 0.9; }
            100% { transform: scale(1.8); opacity: 0; }
          }
        `}</style>
        <span
          style={{
            position: 'absolute',
            inset: -6,
            borderRadius: 999,
            background: 'color-mix(in srgb, var(--accent) 35%, transparent)',
            animation: reduceMotion
              ? 'none'
              : 'pelliers-floor-pulse 1.8s ease-out infinite',
          }}
        />
      </span>

      <AnimatePresence mode="wait">
        <motion.span
          key={index}
          className="absolute inset-0 flex items-center justify-center"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: -8 }}
          transition={{ duration: reduceMotion ? 0 : 0.35, ease: 'easeOut' }}
          style={{ padding: '0 60px' }}
        >
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              maxWidth: '100%',
            }}
          >
            {finding.verb ? (
              <span
                style={{
                  fontFamily: 'var(--sans)',
                  fontStyle: 'normal',
                  fontWeight: 600,
                  fontSize: '13px',
                  letterSpacing: '0.22em',
                  textTransform: 'uppercase',
                  color: c.accent,
                  whiteSpace: 'nowrap',
                }}
              >
                {finding.verb}
              </span>
            ) : null}
            <span
              style={{
                color: c.bg,
                opacity: 0.92,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {finding.text}
            </span>
            {finding.trace ? (
              <span
                aria-hidden="true"
                style={{
                  fontFamily: MONO_STACK,
                  fontSize: '10.5px',
                  letterSpacing: '0.04em',
                  color: 'rgba(251,244,232,0.55)',
                  borderLeft: '1px solid rgba(251,244,232,0.18)',
                  paddingLeft: 12,
                  marginLeft: 4,
                  whiteSpace: 'nowrap',
                }}
              >
                {finding.trace}
              </span>
            ) : null}
          </span>
        </motion.span>
      </AnimatePresence>
    </div>
  )
}
