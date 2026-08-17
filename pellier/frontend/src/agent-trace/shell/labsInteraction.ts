/**
 * labsInteraction — which Labs surfaces a participant acts on, and which ones
 * they only read.
 *
 * Every Labs view is optional: this is an inspection surface, not a checklist.
 * The split is therefore about capability, not obligation. Some views expose
 * live controls that query Aurora or run the router; the rest explain how the
 * live path is built. Stating which is which saves a participant from opening
 * fifteen views to find out, without implying any of them are required.
 *
 * The wording matters. An earlier pass grouped these as "You run this", which
 * read as an instruction; `interactive` versus `reference` describes what the
 * surface offers and leaves the choice to the reader.
 *
 * This module is the single source for that contract. The route picker groups by
 * it and the shell renders a banner from it, so the two can never disagree.
 *
 * Which views are `interactive` is a curriculum call, not a code call. Adding a
 * view here does not give it a control; it claims it has one.
 */

export type LabsInteraction = 'interactive' | 'reference';

/**
 * Surfaces that expose a live control.
 *
 * Verified against the rendered pages: each of these either fires real work (a
 * live turn, `Run on Aurora`, `Run router`) or reads a live source a
 * participant can interrogate per persona (Agents, Memory).
 */
export const INTERACTIVE_PATHS: readonly string[] = [
  '/pellier-labs',
  '/pellier-labs/tools',
  '/pellier-labs/search',
  '/pellier-labs/skills',
  '/pellier-labs/agents',
  '/pellier-labs/memory',
];

export interface LabsModeCopy {
  /** Tracked-caps label on the banner. */
  label: string;
  /** One line telling the participant what this surface is for. */
  detail: string;
}

const INTERACTIVE_COPY: Record<string, LabsModeCopy> = {
  '/pellier-labs': {
    label: 'Interactive',
    detail: 'Pick a shopper turn and watch the evidence ledger fill as it runs.',
  },
  '/pellier-labs/tools': {
    label: 'Interactive',
    detail:
      'Confirm the registered tool count, then open a tool for its live contract.',
  },
  '/pellier-labs/search': {
    label: 'Interactive',
    detail: 'Run a query on Aurora and compare the ranking before and after rerank.',
  },
  '/pellier-labs/skills': {
    label: 'Interactive',
    detail: 'Run the router and see which skills a request actually loads.',
  },
  '/pellier-labs/agents': {
    label: 'Interactive',
    detail:
      'Inspect each specialist against its live contract, tools, and handoffs.',
  },
  '/pellier-labs/memory': {
    label: 'Interactive',
    detail:
      'Read the four memory substrates for the selected persona, live from AgentCore and Aurora.',
  },
};

/*
 * Performance stays in Reference on purpose. It runs a benchmark, but it is a
 * depth surface for participants who want to dig into pgvector retrieval rather
 * than a step the guided path sends everyone to. Reference here means "not on
 * the required path", not "nothing to do".
 */

const REFERENCE_COPY: LabsModeCopy = {
  label: 'Reference',
  detail:
    'Read-only. This explains how the live path is built, with no controls to operate.',
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

/** Picker group headings. Phrased as the participant's job, not a category. */
export const GROUP_LABELS: Record<LabsInteraction, string> = {
  interactive: 'Interactive',
  reference: 'Reference',
};
