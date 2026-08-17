/**
 * Shared interaction contract for governed Pellier Labs.
 *
 * The picker and mode banner read from this module so a surface cannot be
 * listed as hands-on in one place and reference-only in another.
 */

export type LabsInteraction = 'interactive' | 'reference';

/** Governed surfaces that expose a participant-facing live control. */
export const INTERACTIVE_PATHS: readonly string[] = [
  '/pellier-labs',
  '/pellier-labs/tools',
  '/pellier-labs/search',
  '/pellier-labs/skills',
  '/pellier-labs/memory',
];

export interface LabsModeCopy {
  label: string;
  detail: string;
}

const INTERACTIVE_COPY: Record<string, LabsModeCopy> = {
  '/pellier-labs': {
    label: 'Interactive',
    detail: 'Pick a shopper turn and watch governed evidence stream into the ledger.',
  },
  '/pellier-labs/tools': {
    label: 'Interactive',
    detail: 'Inspect the governed tool contracts and run their available checks.',
  },
  '/pellier-labs/search': {
    label: 'Interactive',
    detail: 'Run a query on Aurora and compare the retrieval path before rerank.',
  },
  '/pellier-labs/skills': {
    label: 'Interactive',
    detail: 'Run the router and see which skill overlays the governed path loads.',
  },
  '/pellier-labs/memory': {
    label: 'Interactive',
    detail: 'Read the selected persona memory substrates from their live sources.',
  },
};

const REFERENCE_COPY: LabsModeCopy = {
  label: 'Reference',
  detail:
    'Read-only. This surface documents the governed path, its controls, and its receipts.',
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

export const GROUP_LABELS: Record<LabsInteraction, string> = {
  interactive: 'Interactive',
  reference: 'Reference',
};
