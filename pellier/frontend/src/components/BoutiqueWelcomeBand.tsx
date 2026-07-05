/**
 * BoutiqueWelcomeBand — dismissible editorial welcome under the hero.
 *
 * Symmetric with AtelierWelcome (which lives atop /atelier/sessions).
 * Sits between the BoutiqueHero photograph and the memory handoff.
 * This is intentionally compact: the hero owns the drama, and the
 * memory card owns the agentic proof moment.
 *
 *   1. Describe the need. (hero search bar, command palette, mic)
 *   2. Shop in profile. (header pill - Marco/Anna/Theo)
 *   3. Continue the visit. (saved pieces, sizing, restocks)
 *
 * Dismiss persists in sessionStorage so returning attendees inside
 * the same browser session skip past it. Fresh tabs or re-opened
 * tabs get the intro again so every live demo starts clean.
 */
import { useState } from 'react'
import { X } from 'lucide-react'

const DISMISS_KEY = 'boutique-welcome-dismissed'

function hasBeenDismissed(): boolean {
  try {
    return sessionStorage.getItem(DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

interface PillarProps {
  mark: string
  verb: string
  title: string
  description: string
}

function Pillar({ mark, verb, title, description }: PillarProps) {
  return (
    <div
      style={{
        background: '#FAF3E8',
        border: '1px solid rgba(31, 20, 16, 0.08)',
        borderRadius: '8px',
        padding: '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      {/* Number mark */}
      <div
        style={{
          width: 38,
          height: 30,
          borderRadius: '8px',
          background: 'rgba(31, 20, 16, 0.04)',
          border: '1px solid rgba(31, 20, 16, 0.10)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#a8423a',
          fontFamily: 'var(--mono)',
          fontSize: '11px',
          letterSpacing: '0.12em',
          fontWeight: 700,
          marginBottom: 2,
        }}
      >
        {mark}
      </div>

      {/* Verb (burgundy mono eyebrow) */}
      <div
        style={{
          fontFamily: 'var(--mono)',
          fontSize: '10px',
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: '#a8423a',
          fontWeight: 600,
        }}
      >
        {verb}
      </div>

      {/* Headline (Fraunces italic) */}
      <div
        className="font-display italic"
        style={{
          fontSize: '18px',
          fontWeight: 400,
          letterSpacing: '-0.01em',
          color: '#1f1410',
          lineHeight: 1.15,
        }}
      >
        {title}
      </div>

      {/* Description */}
      <p
        className="font-sans"
        style={{
          fontSize: '13px',
          lineHeight: 1.55,
          color: 'var(--ink-soft)',
          margin: 0,
        }}
      >
        {description}
      </p>
    </div>
  )
}

export default function BoutiqueWelcomeBand() {
  const [dismissed, setDismissed] = useState(hasBeenDismissed)

  const handleDismiss = () => {
    try {
      sessionStorage.setItem(DISMISS_KEY, '1')
    } catch {
      /* ignore */
    }
    setDismissed(true)
  }

  if (dismissed) return null

  return (
    <section
      aria-label="Welcome to Pellier"
      className="w-full"
      style={{
        background:
          'linear-gradient(180deg, #FAF3E8 0%, #F7EFE3 100%)',
        borderTop: '1px solid rgba(31, 20, 16, 0.06)',
        borderBottom: '1px solid rgba(31, 20, 16, 0.06)',
      }}
    >
      <div
        className="max-w-[1440px] mx-auto px-container-x"
        style={{ padding: '34px 0 38px', position: 'relative' }}
      >
        {/* Dismiss button — absolute to the band content */}
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss welcome"
          className="transition-colors duration-150"
          style={{
            position: 'absolute',
            top: 20,
            right: 20,
            width: 32,
            height: 32,
            borderRadius: '50%',
            border: 'none',
            background: 'rgba(31, 20, 16, 0.05)',
            color: 'var(--ink-soft)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(31, 20, 16, 0.10)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(31, 20, 16, 0.05)'
          }}
        >
          <X size={14} strokeWidth={2.5} />
        </button>

        {/* Header block */}
        <div
          className="px-container-x"
          style={{ maxWidth: '820px', marginBottom: '20px' }}
        >
          {/* Eyebrow */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginBottom: '14px',
            }}
          >
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#a8423a',
                display: 'inline-block',
                boxShadow: '0 0 0 3px rgba(168, 66, 58, 0.18)',
              }}
            />
            <span
              className="font-sans"
              style={{
                fontSize: '10.5px',
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
                color: '#a8423a',
                fontWeight: 600,
              }}
            >
              Welcome to Pellier
            </span>
          </div>

          {/* Headline */}
          <h2
            className="font-display italic"
            style={{
              fontSize: 'clamp(28px, 3.4vw, 40px)',
              fontWeight: 400,
              lineHeight: 1.08,
              letterSpacing: 0,
              color: '#1f1410',
              margin: '0 0 14px',
            }}
          >
            A storefront that remembers the visit.
          </h2>

          {/* Summary */}
          <p
            className="font-sans"
            style={{
              fontSize: '15px',
              lineHeight: 1.58,
              color: 'var(--ink-soft)',
              margin: 0,
            }}
          >
            Choose Marco, Anna, or Theo, then ask for the trip, gift, material,
            size, or warehouse. Pellier keeps the edit tied to the active
            shopper profile as the conversation moves.
          </p>
        </div>

        {/* Pillar cards */}
        <div
          className="px-container-x"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))',
            gap: '12px',
          }}
        >
          <Pillar
            mark="01"
            verb="Describe the need"
            title="Occasion, size, material."
            description={
              'Ask for Goa linen, a housewarming gift, or stock in Brooklyn. Pellier turns the request into a focused catalog edit.'
            }
          />
          <Pillar
            mark="02"
            verb="Shop in profile"
            title="One customer at a time."
            description={
              'The active profile carries taste, order history, saved pieces, and sizing into the hero, product floor, and concierge.'
            }
          />
          <Pillar
            mark="03"
            verb="Continue the visit"
            title="Context stays attached."
            description={
              'Recent questions, favorites, inventory checks, and stylist handoffs stay with the same shopper thread.'
            }
          />
        </div>
      </div>
    </section>
  )
}
