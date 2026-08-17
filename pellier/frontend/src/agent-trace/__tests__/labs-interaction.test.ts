import { describe, expect, it } from 'vitest';

import {
  INTERACTIVE_PATHS,
  interactionForPath,
  isInteractivePath,
  modeCopyForPath,
} from '../shell/labsInteraction';

describe('governed Labs interaction contract', () => {
  it('treats every declared interactive path as interactive', () => {
    for (const path of INTERACTIVE_PATHS) {
      expect(interactionForPath(path), path).toBe('interactive');
      expect(isInteractivePath(path), path).toBe(true);
    }
  });

  it('normalizes a trailing slash on the workbench', () => {
    expect(interactionForPath('/pellier-labs/')).toBe('interactive');
    expect(modeCopyForPath('/pellier-labs/').label).toBe('Interactive');
  });

  it('keeps governed proof and Cedar reference surfaces read-only', () => {
    for (const path of [
      '/pellier-labs/proof-board',
      '/pellier-labs/audit-proof',
      '/pellier-labs/architecture',
      '/pellier-labs/write-path',
      '/pellier-labs/performance',
      '/pellier-labs/production-patterns',
    ]) {
      expect(interactionForPath(path), path).toBe('reference');
      expect(modeCopyForPath(path).label, path).toBe('Reference');
    }
  });

  it('does not let an interactive path match a similarly named sibling', () => {
    expect(isInteractivePath('/pellier-labs/toolsmith')).toBe(false);
    expect(isInteractivePath('/pellier-labs/searchable')).toBe(false);
  });

  it('lets a nested interactive route inherit its parent contract', () => {
    expect(interactionForPath('/pellier-labs/tools/find_pieces')).toBe(
      'interactive',
    );
    expect(interactionForPath('/pellier-labs/architecture/runtime')).toBe(
      'reference',
    );
  });
});
