/**
 * Workbench view preference.
 *
 * `focus` shows one panel at a time in the order a participant actually
 * works: run a turn, inspect the evidence it emitted, reconcile the answer
 * against that evidence. `expert` restores the three-panel grid. The choice
 * is a per-browser convenience, so localStorage is the right home for it;
 * an unreadable or absent value always resolves to focus.
 */

export type WorkbenchView = 'focus' | 'expert';

export const WORKBENCH_VIEW_KEY = 'pellier-observatory-view';

export type FocusPanelId = 'run' | 'inspect' | 'reconcile';

export interface FocusPanel {
  id: FocusPanelId;
  label: string;
  /** The `data-motion-panel` value of the grid panel this step reveals. */
  panel: 'requests' | 'trace' | 'results';
}

export const FOCUS_PANELS: readonly FocusPanel[] = [
  { id: 'run', label: 'Run', panel: 'requests' },
  { id: 'inspect', label: 'Inspect evidence', panel: 'trace' },
  { id: 'reconcile', label: 'Reconcile answer', panel: 'results' },
];

/**
 * Index of the Inspect evidence step.
 *
 * A completed run advances here: the evidence panel is worth reading once
 * there is evidence in it, and not while the turn is still streaming.
 */
export const FOCUS_INSPECT_STEP = 1;

function isWorkbenchView(value: unknown): value is WorkbenchView {
  return value === 'focus' || value === 'expert';
}

/** The stored view, or `focus` when nothing valid is stored. */
export function readWorkbenchView(): WorkbenchView {
  try {
    const stored = localStorage.getItem(WORKBENCH_VIEW_KEY);
    return isWorkbenchView(stored) ? stored : 'focus';
  } catch {
    return 'focus';
  }
}

/** Persist the view; storage failures are tolerated because the preference is cosmetic. */
export function writeWorkbenchView(view: WorkbenchView): void {
  try {
    localStorage.setItem(WORKBENCH_VIEW_KEY, view);
  } catch {
    // A private window or a full quota must not break the workbench.
  }
}

/** Index of the focus panel with this id; `run` when the id is unknown. */
export function focusStepIndex(id: string | null | undefined): number {
  const index = FOCUS_PANELS.findIndex((panel) => panel.id === id);
  return index === -1 ? 0 : index;
}
