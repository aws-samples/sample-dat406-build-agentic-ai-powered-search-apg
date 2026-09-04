/**
 * Where the API lives.
 *
 * Empty by default, which makes every request same-origin and lets Vite's dev
 * proxy and the Workshop Studio CloudFront path both work untouched. Set
 * `VITE_API_URL` when the API is served from another origin.
 *
 * One definition on purpose: a client that builds its own path is a client
 * that 404s the moment the API moves, and a pill or a card that reports the
 * failure as "the backend is down" inverts the very fact it exists to report.
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || ''
