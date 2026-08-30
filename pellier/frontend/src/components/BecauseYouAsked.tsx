/**
 * BecauseYouAsked — "Because you asked..." editorial cards section.
 *
 * An unframed editorial index. Each story has a category, title, and brief
 * description without repeating the product-card visual treatment.
 *
 * Personalization:
 *   - When a persona is active (Marco / Anna / Theo), the card
 *     lineup and the section headline both swap to a persona-tailored
 *     set from data/personaCurations.ts. Marco sees travel + linen
 *     edits, Anna sees gifting + apothecary, Theo sees slow-living +
 *     home rituals.
 *   - Fresh / anonymous visitors see the canonical editorial cards
 *     (Gifts / Performance / Linen / Home Rituals) — same as before.
 *   - Small persona-aware photographs make each story legible without
 *     repeating the primary product-card treatment.
 */
import { usePersona } from '../contexts/PersonaContext'
import { editorialForPersona } from '../data/personaCurations'
import ResponsiveImage from './ResponsiveImage'

const STORY_IMAGES: Record<
  string,
  Array<{ src: string; alt: string }>
> = {
  fresh: [
    {
      src: '/products/anna-brass-photo-frame.png',
      alt: 'Brass photo frame styled as a considered gift',
    },
    {
      src: '/products/fresh-cloudform-studio-runner.png',
      alt: 'Cloudform studio runner in a neutral palette',
    },
    {
      src: '/products/fresh-pellier-linen-shirt.png',
      alt: 'Pellier linen shirt in soft daylight',
    },
    {
      src: '/products/theo-stoneware-pour-over.png',
      alt: 'Stoneware pour-over set for a morning ritual',
    },
  ],
  marco: [
    {
      src: '/products/marco-leather-weekend-holdall.png',
      alt: 'Leather weekend holdall ready for travel',
    },
    {
      src: '/products/marco-linen-camp-shirt-indigo.png',
      alt: 'Indigo linen camp shirt',
    },
    {
      src: '/products/marco-canvas-dopp-kit.png',
      alt: 'Canvas dopp kit for everyday carry',
    },
    {
      src: '/products/fresh-heritage-rectangular-watch.png',
      alt: 'Heritage rectangular watch',
    },
  ],
  anna: [
    {
      src: '/products/anna-brass-photo-frame.png',
      alt: 'Brass photo frame styled for gifting',
    },
    {
      src: '/products/anna-botanical-scarf.png',
      alt: 'Botanical scarf folded for a milestone gift',
    },
    {
      src: '/products/anna-ceramic-bud-vase.png',
      alt: 'Ceramic bud vase for the home',
    },
    {
      src: '/products/anna-reed-diffuser.png',
      alt: 'Reed diffuser from the apothecary edit',
    },
  ],
  theo: [
    {
      src: '/products/theo-stoneware-pour-over.png',
      alt: 'Stoneware pour-over set',
    },
    {
      src: '/products/theo-raw-linen-throw.png',
      alt: 'Raw linen throw with a lived-in texture',
    },
    {
      src: '/products/theo-wabi-sabi-bowl.png',
      alt: 'Hand-finished wabi-sabi bowl',
    },
    {
      src: '/products/theo-beeswax-pillar-candle.png',
      alt: 'Beeswax pillar candle for an evening ritual',
    },
  ],
}

const PERSONA_HEADLINES: Record<string, { eyebrow: string; headline: string }> = {
  marco: {
    eyebrow: "From Marco's profile",
    headline: 'Stories for the road.',
  },
  anna: {
    eyebrow: "From Anna's profile",
    headline: 'Stories worth wrapping.',
  },
  theo: {
    eyebrow: "From Theo's profile",
    headline: 'Stories for quieter days.',
  },
}

const DEFAULT_HEADLINE = {
  eyebrow: 'From the catalog edit',
  headline: 'Stories worth exploring.',
}

export default function BecauseYouAsked() {
  const { persona } = usePersona()
  const personaId = persona?.id ?? null

  const cards = editorialForPersona(personaId)
  const copy = (personaId && PERSONA_HEADLINES[personaId]) || DEFAULT_HEADLINE
  const storyImages = STORY_IMAGES[personaId ?? 'fresh'] ?? STORY_IMAGES.fresh

  return (
    <section
      data-testid="because-you-asked"
      aria-label="Profile-guided stories"
      className="w-full border-t border-sand bg-cream py-16 md:py-20 lg:py-24"
      style={{
        background: 'var(--cream)',
      }}
    >
      <div className="max-w-[1440px] mx-auto px-container-x">
        <div className="mb-10">
          <h2
            data-testid="because-you-asked-headline"
            className="font-display text-espresso"
            style={{
              fontSize: 'clamp(28px, 3.5vw, 44px)',
              lineHeight: 1.15,
              letterSpacing: 0,
              fontWeight: 400,
            }}
          >
            {copy.headline}
          </h2>
          <p className="mt-3 font-sans text-[14px] text-ink-soft">
            {copy.eyebrow}
          </p>
        </div>

        <div
          data-testid="because-you-asked-grid"
          className="grid grid-cols-1 gap-x-10 md:grid-cols-2"
        >
          {cards.map((card, index) => (
            <article
              key={card.category}
              className="grid grid-cols-[minmax(0,1fr)_96px] gap-5 border-t border-sand py-6 md:grid-cols-[minmax(0,1fr)_112px] md:py-8"
            >
              <div className="min-w-0">
                <p className="mb-3 font-sans text-[13px] font-medium text-accent-ink">
                  {card.category}
                </p>
                <h3
                  className="mb-3 font-display text-espresso"
                  style={{
                    fontSize: 'clamp(18px, 1.5vw, 22px)',
                    lineHeight: 1.25,
                    fontWeight: 400,
                  }}
                >
                  {card.title}
                </h3>
                <p
                  className="font-sans text-ink-soft"
                  style={{
                    fontSize: 'clamp(13px, 1vw, 14px)',
                    lineHeight: 1.6,
                  }}
                >
                  {card.description}
                </p>
              </div>
              <ResponsiveImage
                src={storyImages[index].src}
                alt={storyImages[index].alt}
                loading="lazy"
                decoding="async"
                sizes="(min-width: 768px) 112px, 96px"
                pictureClassName="block aspect-[4/5] overflow-hidden rounded-[8px] border border-sand bg-cream-warm"
                className="h-full w-full object-cover"
              />
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
