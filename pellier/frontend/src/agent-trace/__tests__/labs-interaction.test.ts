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
    expect(modeCopyForPath('/pellier-labs/').label).toBe('Live Workbench');
  });

  it('keeps governed supporting surfaces optional', () => {
    for (const path of [
      '/pellier-labs/tools',
      '/pellier-labs/search',
      '/pellier-labs/skills',
      '/pellier-labs/memory',
      '/pellier-labs/proof-board',
      '/pellier-labs/audit-proof',
      '/pellier-labs/architecture',
      '/pellier-labs/write-path',
      '/pellier-labs/performance',
      '/pellier-labs/production-patterns',
    ]) {
      expect(interactionForPath(path), path).toBe('reference');
      expect(modeCopyForPath(path).label, path).toBe('Optional deep dive');
    }
  });

  it('does not let an interactive path match a similarly named sibling', () => {
    expect(isInteractivePath('/pellier-labs/toolsmith')).toBe(false);
    expect(isInteractivePath('/pellier-labs/searchable')).toBe(false);
  });

  it('keeps nested supporting routes optional', () => {
    expect(interactionForPath('/pellier-labs/tools/find_pieces')).toBe(
      'reference',
    );
    expect(interactionForPath('/pellier-labs/architecture/runtime')).toBe(
      'reference',
    );
  });
});
