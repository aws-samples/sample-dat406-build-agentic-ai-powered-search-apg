import { beforeEach, describe, expect, it } from 'vitest';

import {
  FOCUS_PANELS,
  WORKBENCH_VIEW_KEY,
  readWorkbenchView,
  writeWorkbenchView,
} from './workbenchView';

describe('workbench view persistence', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to focus mode for a first visit', () => {
    expect(readWorkbenchView()).toBe('focus');
  });

  it('persists the expert choice under the documented key', () => {
    writeWorkbenchView('expert');
    expect(localStorage.getItem(WORKBENCH_VIEW_KEY)).toBe('expert');
    expect(readWorkbenchView()).toBe('expert');
  });

  it('falls back to focus when the stored value is not a view', () => {
    localStorage.setItem(WORKBENCH_VIEW_KEY, 'dashboard');
    expect(readWorkbenchView()).toBe('focus');
  });

  it('steps through Run, Inspect evidence, Reconcile answer in that order', () => {
    expect(FOCUS_PANELS.map((panel) => panel.label)).toEqual([
      'Run',
      'Inspect evidence',
      'Reconcile answer',
    ]);
  });
});
