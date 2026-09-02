/**
 * Footer — masthead row, four live columns, disclaimer, legal strip.
 *
 * An earlier footer shipped five columns and a newsletter form where every
 * link pointed at a placeholder route. That was replaced with columns that map
 * 1:1 onto routes the router actually serves, and this revision keeps that
 * rule while giving the footer the weight a finished storefront has:
 *
 *   - Masthead:     brand lockup left, disclosed demo payment marks right.
 *   - Brand column: tagline plus what this storefront is, as badges. The
 *                   P mark now sits in the masthead, not here.
 *   - Explore:      The floor (`/#shop`), Stories, About.
 *   - Storyboard:   Italic blurb + a real link to `/storyboard`.
 *   - Observatory:  Italic blurb + a real link to `/observatory`.
 *   - Disclaimer:   States that nothing is charged and the catalog is synthetic.
 *   - Legal strip:  Copyright, licence, team credit, source link. No Privacy/Terms/
 *                   Accessibility stubs — those were the same dead links the
 *                   earlier rewrite eliminated, and inventing them back would
 *                   undo it.
 *
 * The footer keeps official marks inside an explicitly disclosed demo checkout:
 * no payment is processed, and no card is charged. The palette is unchanged -
 * sand (#e7e9ed) on espresso (#181a1f).
 *
 * Copy from `FOOTER` in copy.ts.
 */
import { Link } from 'react-router-dom'

import { FOOTER } from '../copy'

export default function Footer() {
  const year = new Date().getFullYear()
  const copyrightLine = `${FOOTER.BOTTOM_STRIP.COPYRIGHT} ${year}`

  return (
    <footer
      data-testid="footer"
      role="contentinfo"
      className="bg-sand text-espresso font-sans border-t border-sand/50"
      style={{
        padding: '56px 24px 32px',
      }}
    >
      <div className="max-w-[1440px] mx-auto px-container-x">
        <Masthead />
        <div
          data-testid="footer-columns"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 48,
            paddingBottom: 40,
          }}
        >
          <BrandColumn />
          <ExploreColumn />
          <EditorialColumn
            testId="footer-column-storyboard"
            heading={FOOTER.STORYBOARD.HEADING}
            copy={FOOTER.STORYBOARD.COPY}
            ctaLabel={FOOTER.STORYBOARD.CTA_LABEL}
            ctaHref={FOOTER.STORYBOARD.CTA_HREF}
          />
          <EditorialColumn
            testId="footer-column-observatory"
            heading={FOOTER.OBSERVATORY.HEADING}
            copy={FOOTER.OBSERVATORY.COPY}
            ctaLabel={FOOTER.OBSERVATORY.CTA_LABEL}
            ctaHref={FOOTER.OBSERVATORY.CTA_HREF}
          />
        </div>
        <Disclaimer />
        <BottomStrip
          copyrightLine={copyrightLine}
          rights={FOOTER.BOTTOM_STRIP.RIGHTS}
          license={FOOTER.BOTTOM_STRIP.LICENSE}
          attribution={FOOTER.BOTTOM_STRIP.ATTRIBUTION}
          githubUrl={FOOTER.BOTTOM_STRIP.GITHUB_URL}
          githubLabel={FOOTER.BOTTOM_STRIP.GITHUB_LABEL}
        />
      </div>
    </footer>
  )
}

/**
 * Brand lockup opposite the disclosed demo payment strip. This is the row that
 * makes the footer read as a shopfront rather than a sitemap.
 */
function Masthead() {
  return (
    <div
      data-testid="footer-masthead"
      className="flex flex-col gap-5 pb-10 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden="true"
          className="pellier-logo-chip bg-espresso text-cream-50"
        >
          P
        </span>
        <span className="font-display text-xl font-medium tracking-tight">
          Pellier
        </span>
      </div>
      <CheckoutTrust />
    </div>
  )
}

function CheckoutTrust() {
  return (
    <div
      data-testid="footer-checkout-trust"
      className="flex flex-col gap-2 sm:items-end"
    >
      <span
        data-testid="footer-checkout-label"
        className="font-sans text-[11px] font-semibold tracking-[0.18em] uppercase text-ink-quiet"
      >
        {FOOTER.CHECKOUT.LABEL}
      </span>
      <ul
        aria-label={FOOTER.CHECKOUT.ARIA_LABEL}
        className="grid w-fit grid-cols-3 gap-1.5 m-0 p-0 list-none sm:flex sm:flex-wrap sm:justify-end"
      >
        {FOOTER.CHECKOUT.PAYMENT_METHODS.map((method) => (
          <li
            key={method.id}
            className="flex h-9 shrink-0 items-center justify-center rounded-[3px] border border-espresso/20 bg-cream-50 px-2.5"
          >
            <img
              alt=""
              aria-hidden="true"
              className="h-5 w-auto object-contain"
              height={20}
              src={`/assets/icons/payment/${method.id}.svg`}
            />
            <span className="sr-only">{method.label}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function BrandColumn() {
  return (
    <section
      data-testid="footer-column-brand"
      aria-label="Pellier"
      className="flex flex-col gap-4"
    >
      <p
        data-testid="footer-brand-tagline"
        className="text-[13px] leading-relaxed text-ink-soft m-0 max-w-[260px]"
      >
        {FOOTER.BRAND.TAGLINE}
      </p>
      <ul
        data-testid="footer-service-items"
        role="list"
        className="flex flex-col gap-2 m-0 p-0 list-none"
      >
        {FOOTER.BOTTOM_STRIP.SERVICE_ITEMS.map((item) => (
          <li
            key={item}
            className="flex items-start gap-2 text-xs leading-relaxed text-ink-quiet"
          >
            <span
              aria-hidden="true"
              className="mt-[6px] block h-1.5 w-1.5 shrink-0 rounded-full bg-accent"
            />
            {item}
          </li>
        ))}
      </ul>
    </section>
  )
}

function ExploreColumn() {
  return (
    <section
      data-testid="footer-column-explore"
      aria-labelledby="footer-column-explore-heading"
      className="flex flex-col gap-3.5"
    >
      <h3
        id="footer-column-explore-heading"
        className="font-sans text-[11px] font-semibold tracking-[0.18em] uppercase text-ink-quiet m-0"
      >
        {FOOTER.EXPLORE.HEADING}
      </h3>
      <ul
        role="list"
        className="flex flex-col gap-2.5 m-0 p-0 list-none"
      >
        {FOOTER.EXPLORE.ITEMS.map(({ label, href }) => (
          <li key={label}>
            <Link
              to={href}
              data-testid={`footer-explore-link-${label.toLowerCase().replace(/\s+/g, '-')}`}
              className="inline-flex min-h-[44px] min-w-[44px] items-center py-1 text-espresso text-sm no-underline transition-colors duration-fade ease-out hover:text-accent"
            >
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

interface EditorialColumnProps {
  testId: string
  heading: string
  copy: string
  ctaLabel: string
  ctaHref: string
}

function EditorialColumn({
  testId,
  heading,
  copy,
  ctaLabel,
  ctaHref,
}: EditorialColumnProps) {
  return (
    <section
      data-testid={testId}
      aria-labelledby={`${testId}-heading`}
      className="flex flex-col gap-3.5"
    >
      <h3
        id={`${testId}-heading`}
        className="font-sans text-[11px] font-semibold tracking-[0.18em] uppercase text-ink-quiet m-0"
      >
        {heading}
      </h3>
      <p className="font-display font-normal text-[15px] leading-[1.55] text-espresso m-0">
        {copy}
      </p>
      <Link
        to={ctaHref}
        data-testid={`${testId}-cta`}
        className="font-sans text-[13px] font-medium tracking-tight text-accent no-underline mt-1 inline-flex min-h-[44px] items-center gap-1.5 py-1 transition-all duration-fade ease-out hover:underline"
      >
        {ctaLabel}
        <span aria-hidden>&rarr;</span>
      </Link>
    </section>
  )
}

/**
 * Said outright, above the legal strip rather than buried in it. A storefront
 * this finished invites the assumption that it transacts and that its reviews
 * and stock counts are real; both are false and cheap to state.
 */
function Disclaimer() {
  return (
    <p
      data-testid="footer-disclaimer"
      className="font-sans text-xs leading-relaxed text-ink-quiet m-0 max-w-[720px] pt-8 border-t border-sand/50"
    >
      {FOOTER.DISCLAIMER}
    </p>
  )
}

interface BottomStripProps {
  copyrightLine: string
  rights: string
  license: string
  attribution: string
  githubUrl: string
  githubLabel: string
}

function BottomStrip({
  copyrightLine,
  rights,
  license,
  attribution,
  githubUrl,
  githubLabel,
}: BottomStripProps) {
  return (
    <div
      data-testid="footer-bottom-strip"
      className="flex flex-col items-start gap-2 pt-6 sm:flex-row sm:items-center sm:justify-between"
    >
      <span
        data-testid="footer-copyright"
        className="text-xs text-ink-quiet"
      >
        {copyrightLine}
      </span>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span
          data-testid="footer-legal"
          className="font-sans text-xs text-ink-quiet tracking-tight"
        >
          {rights}
          <span aria-hidden className="mx-2 text-ink-quiet/50">
            &middot;
          </span>
          {license}
          <span aria-hidden className="mx-2 text-ink-quiet/50">
            &middot;
          </span>
          <span data-testid="footer-attribution">{attribution}</span>
        </span>
        <a
          data-testid="footer-github-link"
          href={githubUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={githubLabel}
          title={githubLabel}
          className="group inline-flex min-h-[44px] min-w-[44px] items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-espresso"
        >
          <img
            data-testid="footer-github-icon"
            src="/assets/icons/github-mark.svg"
            alt=""
            aria-hidden="true"
            width={18}
            height={18}
            className="h-[18px] w-[18px] opacity-65 transition-opacity group-hover:opacity-100"
          />
        </a>
      </div>
    </div>
  )
}
