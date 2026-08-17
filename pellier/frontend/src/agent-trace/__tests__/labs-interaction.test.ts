import { describe, expect, it } from 'vitest'

import {
  INTERACTIVE_PATHS,
  interactionForPath,
  isInteractivePath,
  modeCopyForPath,
} from '../shell/labsInteraction'

/**
 * The interaction contract decides what a participant is told to do on each of
 * the fifteen Labs views, so a wrong answer here sends someone hunting for a
 * button that does not exist. These lock the rules that are easy to break.
 */
describe('labs interaction contract', () => {
  it('treats every declared interactive path as interactive', () => {
    for (const path of INTERACTIVE_PATHS) {
      expect(isInteractivePath(path), path).toBe(true)
      expect(interactionForPath(path), path).toBe('interactive')
    }
  })

  it('normalizes a trailing slash on the index', () => {
    // Regression: `/pellier-labs/` resolved to read, so the primary hands-on
    // surface announced itself as reference.
    expect(isInteractivePath('/pellier-labs/')).toBe(true)
    expect(interactionForPath('/pellier-labs/')).toBe('interactive')
    expect(modeCopyForPath('/pellier-labs/').label).toBe('Live Workbench')
  })

  it('marks the explainer views as reference', () => {
    for (const path of [
      '/pellier-labs/architecture',
      '/pellier-labs/references',
      '/pellier-labs/persona-journeys',
      '/pellier-labs/sessions',
      '/pellier-labs/tools',
      '/pellier-labs/search',
      '/pellier-labs/skills',
      '/pellier-labs/agents',
      '/pellier-labs/memory',
      '/pellier-labs/routing',
      '/pellier-labs/proof-board',
      '/pellier-labs/evaluations',
      // Performance runs a benchmark, but it is a depth surface for advanced
      // participants rather than a step on the guided path.
      '/pellier-labs/performance',
    ]) {
      expect(interactionForPath(path), path).toBe('reference')
      expect(modeCopyForPath(path).label, path).toBe('Optional reference')
    }
  })

  it('does not let an interactive path leak onto an unrelated sibling route', () => {
    // A different route that merely starts with the root text is not live.
    expect(isInteractivePath('/pellier-labs/toolsmith')).toBe(false)
    expect(isInteractivePath('/pellier-labs/searchable')).toBe(false)
  })

  it('keeps nested supporting routes optional', () => {
    expect(interactionForPath('/pellier-labs/tools/find_pieces')).toBe('reference')
    expect(modeCopyForPath('/pellier-labs/tools/find_pieces').label).toBe(
      'Optional reference',
    )
    expect(interactionForPath('/pellier-labs/sessions/marco-x')).toBe('reference')
  })

  it('declares only the workbench as interactive', () => {
    expect(INTERACTIVE_PATHS).toEqual(['/pellier-labs'])
    expect(modeCopyForPath('/pellier-labs').detail.length).toBeGreaterThan(20)
  })
})
