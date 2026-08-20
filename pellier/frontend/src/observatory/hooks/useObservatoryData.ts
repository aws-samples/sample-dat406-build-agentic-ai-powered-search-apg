/**
 * Pellier Observatory — Central data-fetching hook
 *
 * Abstracts static reference data vs. API loading for Observatory surfaces.
 * In fixture mode (default), dynamically imports from /fixtures/ based on key.
 * In API mode, fetches from /api/observatory/* endpoints. Most reference surfaces
 * can fall back to static data during local development; live-only surfaces
 * such as Memory pass allowFixtureFallback=false so API failures are visible.
 *
 * Requirements: 16.1, 16.2, 16.4, 16.5
 */

import { useState, useEffect, useCallback, useRef } from 'react';

type DataSource = 'fixture' | 'api';

export interface UseObservatoryDataOptions {
  key: string;
  params?: Record<string, string>;
  source?: DataSource;
  allowFixtureFallback?: boolean;
}

export interface UseObservatoryDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Map of fixture keys to their dynamic import functions.
 * Each key corresponds to a JSON file in /fixtures/.
 */
const fixtureImporters: Record<string, () => Promise<{ default: unknown }>> = {
  sessions: () => import('../fixtures/sessions.json'),
  // Legacy session detail fixture — kept while older test code still
  // references session-7f5a. New fixtures live under the canonical
  // session IDs from sessions.json.
  'session-7f5a': () => import('../fixtures/session-7f5a.json'),
  // Marco's canonical workshop arc — three session-detail fixtures.
  // See the Workshop Studio repo's content/ for Marco's arc narrative.
  'session-marco-opening-demo': () => import('../fixtures/session-marco-opening-demo.json'),
  'session-marco-midpoint-checkpoint': () => import('../fixtures/session-marco-midpoint-checkpoint.json'),
  'session-marco-capstone': () => import('../fixtures/session-marco-capstone.json'),
  // Supporting personas — evidence of range, no instructional checkpoints.
  'session-anna-morning-ritual': () => import('../fixtures/session-anna-morning-ritual.json'),
  'session-anna-under-100': () => import('../fixtures/session-anna-under-100.json'),
  'session-anna-candle-pairing': () => import('../fixtures/session-anna-candle-pairing.json'),
  'session-anna-birthday-gift': () => import('../fixtures/session-anna-birthday-gift.json'),
  'session-anna-housewarming': () => import('../fixtures/session-anna-housewarming.json'),
  'session-theo-pour-over': () => import('../fixtures/session-theo-pour-over.json'),
  'session-theo-pour-over-pairing': () => import('../fixtures/session-theo-pour-over-pairing.json'),
  'session-theo-linen-seasons': () => import('../fixtures/session-theo-linen-seasons.json'),
  'session-theo-ceramics-return': () => import('../fixtures/session-theo-ceramics-return.json'),
  'session-theo-home-not-wardrobe': () => import('../fixtures/session-theo-home-not-wardrobe.json'),
  agents: () => import('../fixtures/agents.json'),
  tools: () => import('../fixtures/tools.json'),
  skills: () => import('../fixtures/skills.json'),
  routing: () => import('../fixtures/routing.json'),
  performance: () => import('../fixtures/performance.json'),
  evaluations: () => import('../fixtures/evaluations.json'),
  architecture: () => import('../fixtures/architecture.json'),
  'production-patterns': () => import('../fixtures/production-patterns.json'),
};

/**
 * The complete set of fixture keys this hook can load. Exported so the
 * fixture-integrity property test can assert it covers every key (rather
 * than a hard-coded subset that silently drifts when a key is added here).
 */
export const FIXTURE_KEYS: readonly string[] = Object.keys(fixtureImporters);

/**
 * Map of data keys to their API endpoint paths.
 *
 * Note: `production-patterns` is intentionally fixture-only (no backend
 * route); the surface is a teaching catalog and `useObservatoryData` falls back
 * to the fixture loader when the key is absent here.
 */
const apiEndpoints: Record<string, string> = {
  sessions: '/api/observatory/sessions',
  agents: '/api/observatory/agents',
  tools: '/api/observatory/tools/list',
  routing: '/api/observatory/routing',
  skills: '/api/observatory/skills',
  performance: '/api/observatory/performance',
  evaluations: '/api/observatory/evaluations',
  architecture: '/api/observatory/architecture',
};

/**
 * Build the API URL for a given key and optional params.
 */
function buildApiUrl(key: string, params?: Record<string, string>): string {
  // Handle parameterized keys like "session-{id}" or "memory-{persona}"
  if (key.startsWith('session-') && key !== 'sessions') {
    const id = key.replace('session-', '');
    return `/api/observatory/sessions/${id}`;
  }
  if (key.startsWith('memory-')) {
    const persona = key.replace('memory-', '');
    return `/api/observatory/memory/${persona}`;
  }

  const base = apiEndpoints[key];
  if (!base) return `/api/observatory/${key}`;

  if (params) {
    const searchParams = new URLSearchParams(params);
    return `${base}?${searchParams.toString()}`;
  }
  return base;
}

export function useObservatoryData<T = unknown>(
  options: UseObservatoryDataOptions,
): UseObservatoryDataResult<T> {
  const {
    key,
    params,
    source = 'fixture',
    allowFixtureFallback = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track the current request to avoid stale updates
  const requestIdRef = useRef(0);

  const fetchData = useCallback(async () => {
    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    try {
      if (source === 'fixture') {
        const importer = fixtureImporters[key];
        if (!importer) {
          throw new Error(`No fixture found for key: "${key}"`);
        }
        const module = await importer();
        if (currentRequestId === requestIdRef.current) {
          setData(module.default as T);
        }
      } else {
        // API mode. Reference surfaces may opt into a static fallback; live
        // surfaces pass allowFixtureFallback=false and surface the API error.
        try {
          const url = buildApiUrl(key, params);
          const response = await fetch(url);

          if (!response.ok) {
            throw new Error(
              `API request failed: ${response.status} ${response.statusText}`,
            );
          }

          const json = await response.json();
          if (currentRequestId === requestIdRef.current) {
            setData(json as T);
          }
        } catch (apiErr) {
          if (!allowFixtureFallback) {
            if (currentRequestId === requestIdRef.current) {
              const message =
                apiErr instanceof Error
                  ? apiErr.message
                  : 'API request failed';
              setError(message);
              setData(null);
            }
            return;
          }
          // API failed — fall back only for reference surfaces that allow it.
          const importer = fixtureImporters[key];
          if (importer) {
            try {
              const module = await importer();
              if (currentRequestId === requestIdRef.current) {
                setData(module.default as T);
              }
            } catch (fixtureErr) {
              // Both API and fixture fallback failed
              if (currentRequestId === requestIdRef.current) {
                const message =
                  fixtureErr instanceof Error
                    ? fixtureErr.message
                    : 'An unknown error occurred';
                setError(message);
                setData(null);
              }
            }
          } else {
            // No fixture available for this key — surface the original API error
            if (currentRequestId === requestIdRef.current) {
              setError(`API unavailable and no fixture fallback for key: "${key}"`);
              setData(null);
            }
          }
        }
      }
    } catch (err) {
      if (currentRequestId === requestIdRef.current) {
        const message =
          err instanceof Error ? err.message : 'An unknown error occurred';
        setError(message);
        setData(null);
      }
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [key, params, source, allowFixtureFallback]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
