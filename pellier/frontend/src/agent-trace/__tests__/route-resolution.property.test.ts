/**
 * Property test: Route resolution correctness (Property 5)
 *
 * Generates valid Agent Trace route paths from the defined route segments
 * and verifies React Router resolves each to a non-null component.
 *
 * **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8**
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import { matchRoutes, type RouteObject } from 'react-router-dom'

// ---------------------------------------------------------------------------
// Route configuration — mirrors the nested route tree from App.tsx.
// We use plain `element: true` as a truthy stand-in for the real React
// elements. matchRoutes only cares about path matching, not rendering.
// ---------------------------------------------------------------------------
const agentTraceRoutes: RouteObject[] = [
  {
    path: '/agent-trace',
    element: true as unknown as React.ReactNode,
    children: [
      { index: true, element: true as unknown as React.ReactNode },
      { path: 'proof-board', element: true as unknown as React.ReactNode },
      { path: 'sessions', element: true as unknown as React.ReactNode },
      {
        path: 'sessions/:id',
        element: true as unknown as React.ReactNode,
        children: [
          { index: true, element: true as unknown as React.ReactNode },
          { path: 'chat', element: true as unknown as React.ReactNode },
          { path: 'telemetry', element: true as unknown as React.ReactNode },
          { path: 'brief', element: true as unknown as React.ReactNode },
        ],
      },
      { path: 'architecture', element: true as unknown as React.ReactNode },
      { path: 'architecture/:concept', element: true as unknown as React.ReactNode },
      { path: 'agents', element: true as unknown as React.ReactNode },
      { path: 'skills', element: true as unknown as React.ReactNode },
      { path: 'tools', element: true as unknown as React.ReactNode },
      { path: 'search', element: true as unknown as React.ReactNode },
      { path: 'routing', element: true as unknown as React.ReactNode },
      { path: 'memory', element: true as unknown as React.ReactNode },
      { path: 'write-path', element: true as unknown as React.ReactNode },
      { path: 'performance', element: true as unknown as React.ReactNode },
      { path: 'evaluations', element: true as unknown as React.ReactNode },
      { path: 'production-patterns', element: true as unknown as React.ReactNode },
      { path: 'observatory', element: true as unknown as React.ReactNode },
      { path: 'persona-journeys', element: true as unknown as React.ReactNode },
      { path: 'settings', element: true as unknown as React.ReactNode },
    ],
  },
]

// ---------------------------------------------------------------------------
// Generators — produce valid Agent Trace paths from defined route segments.
// ---------------------------------------------------------------------------

/** Alphanumeric + hex-style IDs for parameterized segments. */
const paramValueArb = fc.string({
  minLength: 1,
  maxLength: 12,
  unit: fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789'.split('')),
})

/** Architecture concept slugs matching the 8 defined concepts. */
const conceptSlugArb = fc.constantFrom(
  'memory',
  'mcp',
  'state-management',
  'tool-registry',
  'skills',
  'runtime',
  'evaluations',
  'grounding',
)

/** Session sub-tab paths. */
const sessionTabArb = fc.constantFrom('chat', 'telemetry', 'brief')

/**
 * Generates a valid Agent Trace route path. The generator picks from all
 * defined route segments, including parameterized routes with generated
 * parameter values.
 */
const agentTracePathArb: fc.Arbitrary<string> = fc.oneof(
  // Static leaf routes
  fc.constant('/agent-trace'),
  fc.constant('/agent-trace/proof-board'),
  fc.constant('/agent-trace/sessions'),
  fc.constant('/agent-trace/architecture'),
  fc.constant('/agent-trace/agents'),
  fc.constant('/agent-trace/skills'),
  fc.constant('/agent-trace/tools'),
  fc.constant('/agent-trace/search'),
  fc.constant('/agent-trace/routing'),
  fc.constant('/agent-trace/memory'),
  fc.constant('/agent-trace/write-path'),
  fc.constant('/agent-trace/performance'),
  fc.constant('/agent-trace/evaluations'),
  fc.constant('/agent-trace/production-patterns'),
  fc.constant('/agent-trace/observatory'),
  fc.constant('/agent-trace/persona-journeys'),
  fc.constant('/agent-trace/settings'),

  // Parameterized: sessions/:id
  paramValueArb.map((id) => `/agent-trace/sessions/${id}`),

  // Parameterized: sessions/:id/:tab
  fc.tuple(paramValueArb, sessionTabArb).map(
    ([id, tab]) => `/agent-trace/sessions/${id}/${tab}`,
  ),

  // Parameterized: architecture/:concept
  conceptSlugArb.map((concept) => `/agent-trace/architecture/${concept}`),
)

// ---------------------------------------------------------------------------
// Property test
// ---------------------------------------------------------------------------
describe('Property 5: Route resolution correctness', () => {
  it('every valid Agent Trace path resolves to a non-null route match', () => {
    fc.assert(
      fc.property(agentTracePathArb, (path) => {
        const matches = matchRoutes(agentTraceRoutes, path)

        // matchRoutes returns null when no route matches the path.
        // Every valid Agent Trace path must produce at least one match.
        expect(matches).not.toBeNull()
        expect(matches!.length).toBeGreaterThan(0)

        // The deepest (last) match must have a non-null route element,
        // confirming a component is assigned to handle this path.
        const deepest = matches![matches!.length - 1]
        expect(deepest.route.element).toBeTruthy()
      }),
      { numRuns: 200 },
    )
  })
})
