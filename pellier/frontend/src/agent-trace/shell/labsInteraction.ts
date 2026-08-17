/**
 * labsInteraction — which Labs surfaces a participant acts on, and which ones
 * they only read.
 *
 * The Live Workbench is the one participant-facing interactive surface.
 * Everything else is optional reference, even when a deeper page happens to
 * expose a control. This keeps the curriculum contract aligned with the
 * workshop: storefront + code editor first, workbench when directed, depth on
 * demand.
 *
 * This module is the single source for that contract. The shell renders a
 * banner from it so no deep route can accidentally present itself as required.
 */

export type LabsInteraction = 'interactive' | 'reference';

/**
 * The one primary Labs surface. Deeper pages can contain live controls without
 * becoming part of the participant's required path.
 */
export const INTERACTIVE_PATHS: readonly string[] = [
  '/pellier-labs',
];

export interface LabsModeCopy {
  /** Tracked-caps label on the banner. */
  label: string;
  /** One line telling the participant what this surface is for. */
  detail: string;
}

const INTERACTIVE_COPY: Record<string, LabsModeCopy> = {
  '/pellier-labs': {
    label: 'Live Workbench',
    detail: 'Pick a shopper turn and watch the evidence ledger fill as it runs.',
  },
};

const REFERENCE_COPY: LabsModeCopy = {
  label: 'Optional reference',
  detail:
    'Use this supporting view only when a lab step or your investigation sends you here.',
};

/** Longest-prefix match, so nested routes inherit their parent's contract. */
export function interactionForPath(pathname: string): LabsInteraction {
  return isInteractivePath(pathname) ? 'interactive' : 'reference';
}

/**
 * Trailing slashes are stripped first. `/pellier-labs/` is the same surface as
 * `/pellier-labs`, and without this the index, which is the primary hands-on
 * view, resolved to `read` whenever it was reached with the slash.
 */
function normalize(pathname: string): string {
  return pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
}

export function isInteractivePath(pathname: string): boolean {
  const path = normalize(pathname);
  return INTERACTIVE_PATHS.some(
    (runPath) =>
      path === runPath ||
      (runPath !== '/pellier-labs' && path.startsWith(`${runPath}/`)),
  );
}

/**
 * Banner copy for a route. Run surfaces each say what to do; read surfaces
 * share one line, because repeating a bespoke "you cannot act here" per page
 * would be noise.
 */
export function modeCopyForPath(pathname: string): LabsModeCopy {
  if (!isInteractivePath(pathname)) return REFERENCE_COPY;
  const path = normalize(pathname);
  const exact = INTERACTIVE_COPY[path];
  if (exact) return exact;
  const parent = INTERACTIVE_PATHS.find(
    (runPath) =>
      runPath !== '/pellier-labs' && path.startsWith(`${runPath}/`),
  );
  return (parent && INTERACTIVE_COPY[parent]) || INTERACTIVE_COPY['/pellier-labs'];
}
