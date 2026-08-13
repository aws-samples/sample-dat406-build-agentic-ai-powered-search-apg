import { ArrowRight } from 'lucide-react'
import { asset } from '../utils/assetPath'

const COLLECTIONS = [
  {
    number: '01',
    title: 'Travel light',
    description: 'Linen and packable layers.',
    image: asset('/products/marco-linen-camp-shirt-indigo.png'),
    alt: 'Indigo linen camp shirt from the Pellier catalog',
  },
  {
    number: '02',
    title: 'Considered gifting',
    description: 'Useful objects, ready to give.',
    image: asset('/products/anna-beeswax-taper-candles.png'),
    alt: 'Beeswax taper candles from the Pellier catalog',
  },
  {
    number: '03',
    title: 'Slow craft',
    description: 'Ceramics for daily rituals.',
    image: asset('/products/theo-stoneware-pour-over.png'),
    alt: 'Stoneware pour-over set from the Pellier catalog',
  },
  {
    number: '04',
    title: 'Weekend form',
    description: 'Enduring pieces for the road.',
    image: asset('/products/fresh-nocturne-leather-weekender.png'),
    alt: 'Nocturne leather weekender from the Pellier catalog',
  },
] as const

interface BoutiqueCollectionsProps {
  onOpenCatalog: () => void
}

export default function BoutiqueCollections({
  onOpenCatalog,
}: BoutiqueCollectionsProps) {
  return (
    <section
      data-testid="boutique-collections"
      aria-labelledby="boutique-collections-title"
      className="w-full px-container-x py-10 md:py-14"
    >
      <div className="mx-auto max-w-[1440px]">
        <header className="mb-5 flex items-end justify-between gap-5">
          <div>
            <p
              className="mb-2 font-sans text-[10px] font-semibold uppercase text-accent-ink"
              style={{ letterSpacing: '0.18em' }}
            >
              From the seeded catalog
            </p>
            <h2
              id="boutique-collections-title"
              className="font-display text-[32px] font-normal leading-none text-espresso md:text-[40px]"
              style={{ letterSpacing: 0 }}
            >
              The Pellier edit
            </h2>
          </div>
          <button
            type="button"
            onClick={onOpenCatalog}
            className="
              inline-flex min-h-11 shrink-0 items-center gap-2 font-sans
              text-[13px] font-semibold text-espresso transition hover:text-accent-ink
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso
              focus-visible:ring-offset-4
            "
          >
            View catalog
            <ArrowRight size={17} aria-hidden="true" />
          </button>
        </header>

        <div
          className="
            -mx-container-x flex snap-x snap-mandatory gap-3 overflow-x-auto
            px-container-x pb-2 md:mx-0 md:grid md:grid-cols-4 md:overflow-visible
            md:px-0 md:pb-0
          "
        >
          {COLLECTIONS.map((collection) => (
            <article
              key={collection.number}
              className="
                group relative aspect-[4/3] w-[78vw] max-w-[300px] shrink-0
                snap-start overflow-hidden rounded-[8px] bg-espresso
                md:w-auto md:max-w-none
              "
            >
              <img
                src={collection.image}
                alt={collection.alt}
                loading="eager"
                className="
                  h-full w-full object-cover transition-transform duration-300
                  group-hover:scale-[1.025]
                "
              />
              <div
                aria-hidden="true"
                className="absolute inset-0 bg-[linear-gradient(0deg,rgba(24,16,12,0.90)_0%,rgba(24,16,12,0.12)_68%)]"
              />
              <div className="absolute inset-x-0 bottom-0 p-4 text-cream md:p-5">
                <p
                  className="font-sans text-[9px] font-semibold uppercase text-cream/80"
                  style={{ letterSpacing: '0.16em' }}
                >
                  Edit {collection.number}
                </p>
                <h3
                  className="mt-1 font-display text-[21px] font-medium leading-tight text-cream"
                  style={{ letterSpacing: 0 }}
                >
                  {collection.title}
                </h3>
                <p className="mt-1 font-sans text-[11px] leading-4 text-cream/80">
                  {collection.description}
                </p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
