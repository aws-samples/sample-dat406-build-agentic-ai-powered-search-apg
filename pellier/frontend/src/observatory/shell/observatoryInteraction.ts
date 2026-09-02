/**
 * Which governed Labs surfaces are primary and which are optional depth.
 *
 * The collection is the visual entry to one participant-facing workbench.
 * Deeper system pages remain reference views.
 */

export type LabsInteraction = 'interactive' | 'reference';

export const INTERACTIVE_PATHS: readonly string[] = [
  '/observatory',
  '/observatory/labs',
  '/observatory/workbench',
];

export interface ObservatoryModeCopy {
  label: string;
  detail: string;
}

const INTERACTIVE_COPY: Record<string, ObservatoryModeCopy> = {
  '/observatory': {
    label: 'Labs & Workbench',
    detail:
      'Choose one evidence-first lab, then use the same workbench to inspect its live system behavior.',
  },
  '/observatory/labs': {
    label: 'Exercise workbench',
    detail:
      'Follow the bounded participant TODO, measurement target, evidence assertion, and architecture decision for this exercise.',
  },
  '/observatory/workbench': {
    label: 'Labs & Workbench',
    detail:
      'Run a live Storefront Dispatcher request and inspect routing, memory, guardrails, agent activity, tool calls, SQL, and the grounded answer.',
  },
};

/**
 * Every non-Workbench surface gets this.
 *
 * It used to read "Optional deep dive — use this deep dive only when a lab step
 * or your investigation sends you here", which made optionality the third thing
 * on screen saying so: the top bar badge, this banner, and the page's own
 * intro. Optionality is the badge's job now, and it says it once, everywhere.
 *
 * What this banner is actually for is the distinction the badge cannot make:
 * this is a read of recorded evidence, not the live workbench, and it is not
 * the canonical proof either.
 */
const REFERENCE_COPY: ObservatoryModeCopy = {
  label: 'Reference view',
  detail:
    'Inspect system evidence and implementation detail without starting a new shopper turn.',
};

function normalize(pathname: string): string {
  return pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
}

export function isInteractivePath(pathname: string): boolean {
  const path = normalize(pathname);
  return INTERACTIVE_PATHS.some(
    (interactivePath) =>
      path === interactivePath ||
      (interactivePath !== '/observatory' &&
        path.startsWith(`${interactivePath}/`)),
  );
}

export function interactionForPath(pathname: string): LabsInteraction {
  return isInteractivePath(pathname) ? 'interactive' : 'reference';
}

export function modeCopyForPath(pathname: string): ObservatoryModeCopy {
  if (!isInteractivePath(pathname)) return REFERENCE_COPY;

  const path = normalize(pathname);
  const exact = INTERACTIVE_COPY[path];
  if (exact) return exact;

  const parent = [...INTERACTIVE_PATHS]
    .sort((left, right) => right.length - left.length)
    .find(
    (interactivePath) =>
      path.startsWith(`${interactivePath}/`),
    );
  return (
    (parent && INTERACTIVE_COPY[parent]) || INTERACTIVE_COPY['/observatory']
  );
}
