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
    expect(modeCopyForPath('/pellier-labs/').label).toBe('Interactive')
  })

  it('marks the explainer views as reference', () => {
    for (const path of [
      '/pellier-labs/architecture',
      '/pellier-labs/persona-journeys',
      '/pellier-labs/sessions',
      '/pellier-labs/routing',
      '/pellier-labs/proof-board',
      '/pellier-labs/evaluations',
      // Performance runs a benchmark, but it is a depth surface for advanced
      // participants rather than a step on the guided path.
      '/pellier-labs/performance',
    ]) {
      expect(interactionForPath(path), path).toBe('reference')
      expect(modeCopyForPath(path).label, path).toBe('Reference')
    }
  })

  it('does not let an interactive path leak onto an unrelated sibling route', () => {
    // `/pellier-labs/tools` is interactive; a different route that merely starts
    // with the same characters is not.
    expect(isInteractivePath('/pellier-labs/toolsmith')).toBe(false)
    expect(isInteractivePath('/pellier-labs/searchable')).toBe(false)
  })

  it('keeps Agents and Memory interactive', () => {
    // Both read live sources, so participants are meant to operate them.
    for (const path of ['/pellier-labs/agents', '/pellier-labs/memory']) {
      expect(interactionForPath(path), path).toBe('interactive')
      expect(modeCopyForPath(path).label, path).toBe('Interactive')
    }
  })

  it('lets a nested route inherit its parent contract', () => {
    expect(interactionForPath('/pellier-labs/tools/find_pieces')).toBe('interactive')
    expect(modeCopyForPath('/pellier-labs/tools/find_pieces').label).toBe(
      'Interactive',
    )
    expect(interactionForPath('/pellier-labs/sessions/marco-x')).toBe('reference')
  })

  it('gives each interactive surface its own description', () => {
    const details = INTERACTIVE_PATHS.map((p) => modeCopyForPath(p).detail)
    expect(new Set(details).size).toBe(INTERACTIVE_PATHS.length)
    for (const d of details) expect(d.length).toBeGreaterThan(20)
  })
})
