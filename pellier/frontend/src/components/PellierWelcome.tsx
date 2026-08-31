/**
 * Live concierge empty state.
 *
 * The welcome drawer reads its cover and suggested turns from Aurora. A
 * failed data-plane read is visible to the shopper; it never becomes a
 * locally authored recommendation.
 */
import { useEffect, useState } from 'react'
import type { PersonaSnapshot } from '../contexts/PersonaContext'
import type { PellierProduct } from '../services/types'
import { imageSrc } from '../utils/assetPath'
import '../styles/pellier-welcome.css'

interface PellierWelcomeProps {
  onSend: (text: string) => void
  persona?: PersonaSnapshot | null
}

interface LiveScenario {
  id: number
  prompt: string
}

type TimeOfDay = 'morning' | 'afternoon' | 'evening'

function timeOfDay(): TimeOfDay {
  const hour = new Date().getHours()
  if (hour < 12) return 'morning'
  if (hour < 17) return 'afternoon'
  return 'evening'
}

const TIME_GREETING: Record<TimeOfDay, string> = {
  morning: 'Good morning',
  afternoon: 'Good afternoon',
  evening: 'Good evening',
}

const TIME_EYEBROW: Record<TimeOfDay, string> = {
  morning: 'This morning at Pellier',
  afternoon: 'This afternoon at Pellier',
  evening: 'Tonight at Pellier',
}

export function composeWelcomeGreeting(
  timeGreeting: string,
  greetingSuffix: string,
): string {
  const suffix = greetingSuffix.trim()
  return `${timeGreeting}${suffix}${suffix.endsWith('.') ? '' : '.'}`
}

export default function PellierWelcome({ onSend, persona }: PellierWelcomeProps) {
  const [catalog, setCatalog] = useState<PellierProduct[]>([])
  const [scenarios, setScenarios] = useState<LiveScenario[]>([])
  const [error, setError] = useState<string | null>(null)
  const profileId = persona?.id ?? 'fresh'
  const tod = timeOfDay()

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    setCatalog([])
    setScenarios([])
    setError(null)

    void Promise.all([
      fetch(`/api/products?persona=${encodeURIComponent(profileId)}`, {
        credentials: 'include',
        signal: controller.signal,
      }),
      fetch(`/api/observatory/scenarios?persona=${encodeURIComponent(profileId)}`, {
        signal: controller.signal,
      }),
    ])
      .then(async ([catalogResponse, scenarioResponse]) => {
        if (!catalogResponse.ok || !scenarioResponse.ok) {
          throw new Error('Live concierge context is unavailable.')
        }
        return Promise.all([
          catalogResponse.json() as Promise<PellierProduct[]>,
          scenarioResponse.json() as Promise<{ scenarios?: LiveScenario[] }>,
        ])
      })
      .then(([products, payload]) => {
        if (!active) return
        setCatalog(products)
        setScenarios(payload.scenarios ?? [])
      })
      .catch((reason: unknown) => {
        if (!active || (reason as { name?: string })?.name === 'AbortError') return
        setError(
          reason instanceof Error
            ? reason.message
            : 'Live concierge context is unavailable.',
        )
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [profileId])

  const cover = catalog[0]
  const greeting = composeWelcomeGreeting(
    TIME_GREETING[tod],
    persona && persona.id !== 'fresh' ? `, ${persona.display_name.split(' ')[0]}` : '',
  )
  const primary = scenarios.slice(0, 3)
  const more = scenarios.slice(3, 5)

  return (
    <div className="sf-welcome">
      <div className="sf-cover">
        {cover ? (
          <img src={imageSrc(cover.imageUrl)} alt={cover.name} className="sf-cover-img" />
        ) : (
          <div className="sf-cover-img bg-cream-warm" aria-hidden="true" />
        )}
        <div className="sf-cover-overlay">
          <div className="sf-cover-eyebrow">
            <span className="sf-cover-dot" />
            {cover ? 'Live Aurora catalog' : 'Live catalog loading'}
          </div>
        </div>
      </div>

      <div className="sf-body">
        <div className="sf-eyebrow-row">
          <span className="sf-eyebrow-sm">{TIME_EYEBROW[tod]}</span>
          <span className="sf-eyebrow-rule" />
        </div>

        <h2 className="sf-greeting"><em>{greeting}</em></h2>
        <p className="sf-context">
          {error
            ? error
            : catalog.length
              ? `${catalog.length} current pieces are available in this live edit.`
              : 'Reading the current catalog and guided requests from Aurora…'}
        </p>

        {!error && primary.length > 0 ? (
          <div className="sf-section">
            <div className="sf-section-head">
              <span className="sf-eyebrow-sm sf-eyebrow-red">
                <span className="sf-dot" />
                Guided requests
              </span>
              <span className="sf-count sf-count-hero">Live</span>
            </div>
            <div className="sf-actions-stack">
              {primary.map((scenario, index) => (
                <button
                  key={scenario.id}
                  type="button"
                  className={`sf-action ${index === 0 ? 'sf-action-primary' : ''}`}
                  onClick={() => onSend(scenario.prompt)}
                >
                  {scenario.prompt}
                  <span className="sf-action-arrow">→</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {more.length > 0 ? (
          <>
            <div className="sf-divider" />
            <p className="sf-prompt">Or choose another live starting point.</p>
            <div className="sf-postscript-list">
              {more.map((scenario) => (
                <button
                  key={scenario.id}
                  type="button"
                  className="sf-overheard"
                  onClick={() => onSend(scenario.prompt)}
                >
                  <span className="sf-overheard-line">
                    <span className="sf-overheard-bullet">&middot;</span>
                    <span className="sf-overheard-quote">&ldquo;{scenario.prompt}&rdquo;</span>
                  </span>
                </button>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}
