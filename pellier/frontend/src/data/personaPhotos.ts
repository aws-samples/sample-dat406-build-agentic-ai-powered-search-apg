/**
 * Persona portraits, served from `public/products`.
 *
 * These were remote Unsplash URLs. A workshop box has no guaranteed egress
 * to images.unsplash.com, so a blocked request left every avatar as a bare
 * initial circle. Local files remove that dependency.
 *
 * Two sizes, two roles:
 *
 *   `PERSONA_PHOTOS`    160px avatar crop. Chrome: header pill, Labs top
 *                       bar, persona modal, transition overlay.
 *   `PERSONA_PORTRAITS` 480px editorial crop. The hero concierge panel,
 *                       where the face is a composition element.
 *
 * Both are width-suffixed WebP derivatives of the tracked source PNGs
 * (`persona-<id>-portrait.png`), matching the `-<width>.<format>`
 * convention in `utils/assetPath.ts`.
 *
 * The maps hold root-relative repository paths. The accessors resolve them
 * through `imageSrc()` so a caller can assign the result straight to
 * `<img src>`: a bare root-relative path 404s behind the Workshop Studio
 * `/ports/8000/` proxy, and every consumer here renders a plain `<img>`.
 */
import { imageSrc } from '../utils/assetPath'

/** Avatar-sized crops for interface chrome. */
export const PERSONA_PHOTOS: Record<string, string> = {
  marco: '/products/persona-marco-portrait-160.webp',
  anna: '/products/persona-anna-portrait-160.webp',
  theo: '/products/persona-theo-portrait-160.webp',
}

/** Editorial crops for the hero concierge panel. */
export const PERSONA_PORTRAITS: Record<string, string> = {
  marco: '/products/persona-marco-portrait-480.webp',
  anna: '/products/persona-anna-portrait-480.webp',
  theo: '/products/persona-theo-portrait-480.webp',
}

/**
 * Client-book portraits, same treatment and same two sizes.
 *
 * Clients are operator-side records, not switchable personas, so they get
 * their own map rather than being folded into `PERSONA_PHOTOS`. Keeping the
 * split explicit stops a client id from ever resolving as a signed-in
 * shopper.
 */
const CLIENT_SLUGS = [
  'jessica', 'sarah', 'catherine', 'amara', 'julian', 'david',
  'priya', 'elena', 'thomas', 'michael', 'rachel', 'kevin',
] as const

function clientMap(size: 160 | 480): Record<string, string> {
  return Object.fromEntries(
    CLIENT_SLUGS.map((slug) => [
      slug,
      `/products/client-${slug}-portrait-${size}.webp`,
    ]),
  )
}

/** Avatar-sized crops for the client book list. */
export const CLIENT_PHOTOS: Record<string, string> = clientMap(160)

/** Editorial crops for the client record header. */
export const CLIENT_PORTRAITS: Record<string, string> = clientMap(480)

/**
 * Resolve a client portrait from a customer id such as `CUST-JESSICA`, or
 * from a bare slug. Returns undefined for an unknown client so callers fall
 * back to the initial-circle avatar they already render.
 */
function clientSlug(customerId: string | null | undefined): string | undefined {
  if (!customerId) return undefined
  const slug = customerId.replace(/^CUST-/i, '').toLowerCase()
  return slug in CLIENT_PHOTOS ? slug : undefined
}

export function getClientPhoto(
  customerId: string | null | undefined,
): string | undefined {
  const slug = clientSlug(customerId)
  return slug ? imageSrc(CLIENT_PHOTOS[slug]) : undefined
}

export function getClientPortrait(
  customerId: string | null | undefined,
): string | undefined {
  const slug = clientSlug(customerId)
  return slug ? imageSrc(CLIENT_PORTRAITS[slug]) : undefined
}

/**
 * Get the base-resolved avatar URL for a persona ID. Returns undefined for
 * an unknown or absent persona so callers fall back to the initial-circle
 * avatar they already render.
 */
export function getPersonaPhoto(personaId: string | null | undefined): string | undefined {
  if (!personaId) return undefined
  return imageSrc(PERSONA_PHOTOS[personaId])
}

/** Get the base-resolved editorial portrait URL for a persona ID. */
export function getPersonaPortrait(
  personaId: string | null | undefined,
): string | undefined {
  if (!personaId) return undefined
  return imageSrc(PERSONA_PORTRAITS[personaId])
}
