/**
 * Which governed Labs surfaces are primary and which are optional depth.
 *
 * The Live Workbench is the one participant-facing primary surface. Deeper
 * pages may expose controls, but they remain optional deep dives so the
 * workshop path stays clear.
 */

export type LabsInteraction = 'interactive' | 'reference';

export const INTERACTIVE_PATHS: readonly string[] = [
  '/pellier-labs',
];

export interface LabsModeCopy {
  label: string;
  detail: string;
}

const INTERACTIVE_COPY: Record<string, LabsModeCopy> = {
  '/pellier-labs': {
    label: 'Live Workbench',
    detail:
      'Run a governed shopper request and inspect identity, policy decisions, transaction state, and durable evidence.',
  },
};

const REFERENCE_COPY: LabsModeCopy = {
  label: 'Optional deep dive',
  detail:
    'Use this deep dive only when a lab step or your investigation sends you here.',
};

function normalize(pathname: string): string {
  return pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
}

export function isInteractivePath(pathname: string): boolean {
  const path = normalize(pathname);
  return INTERACTIVE_PATHS.some(
    (interactivePath) =>
      path === interactivePath ||
      (interactivePath !== '/pellier-labs' &&
        path.startsWith(`${interactivePath}/`)),
  );
}

export function interactionForPath(pathname: string): LabsInteraction {
  return isInteractivePath(pathname) ? 'interactive' : 'reference';
}

export function modeCopyForPath(pathname: string): LabsModeCopy {
  if (!isInteractivePath(pathname)) return REFERENCE_COPY;

  const path = normalize(pathname);
  const exact = INTERACTIVE_COPY[path];
  if (exact) return exact;

  const parent = INTERACTIVE_PATHS.find(
    (interactivePath) =>
      interactivePath !== '/pellier-labs' &&
      path.startsWith(`${interactivePath}/`),
  );
  return (
    (parent && INTERACTIVE_COPY[parent]) || INTERACTIVE_COPY['/pellier-labs']
  );
}
