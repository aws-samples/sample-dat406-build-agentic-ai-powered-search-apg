/**
 * BoutiqueWelcomeBand — dismissible editorial welcome under the hero.
 *
 * Symmetric with AtelierWelcome (which lives atop /atelier/sessions).
 * Sits between the BoutiqueHero photograph and the memory handoff.
 * This is intentionally compact: the hero owns the drama, and the
 * memory card owns the agentic proof moment.
 *
 *   1. You can just ask. (hero search bar, ⌘K, mic)
 *   2. Pick a persona. (header pill — Marco/Anna/Theo)
 *   3. Peek the wires. (Atelier toggle in the header)
 *
 * Dismiss persists in sessionStorage so returning attendees inside
 * the same browser session skip past it. Fresh tabs or re-opened
 * tabs get the intro again so every live demo starts clean.
 */
import { useState } from 'react'
import { X, Sparkles, UserCircle2, Microscope } from 'lucide-react'

const DISMISS_KEY = 'boutique-welcome-dismissed'

function hasBeenDismissed(): boolean {
  try {
    return sessionStorage.getItem(DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

interface PillarProps {
  icon: React.ReactNode
  verb: string
  title: string
  description: string
}

function Pillar({ icon, verb, title, description }: PillarProps) {
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
      {/* Icon tile */}
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: '8px',
          background: 'rgba(168, 66, 58, 0.10)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#a8423a',
          marginBottom: 2,
        }}
      >
        {icon}
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
            A quieter way to shop.
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
            Ask in your own words, let the active persona shape the floor, and
            open the Atelier when the recommendation needs a paper trail.
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
            icon={<Sparkles size={18} strokeWidth={2} />}
            verb="Ask Pellier"
            title="Ask naturally."
            description={
              "Type or speak the way a shopper would. Pellier reads intent, inventory, memory, and context together."
            }
          />
          <Pillar
            icon={<UserCircle2 size={18} strokeWidth={2} />}
            verb="Pick a persona"
            title="Let taste travel."
            description={
              'Marco, Anna, and Theo each reshape the hero, grid, and concierge with visible signals.'
            }
          />
          <Pillar
            icon={<Microscope size={18} strokeWidth={2} />}
            verb="Peek the wires"
            title="Follow the proof."
            description={
              'The Atelier keeps the trace: decisions, tools, memory reads, and governed handoffs.'
            }
          />
        </div>
      </div>
    </section>
  )
}
