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
