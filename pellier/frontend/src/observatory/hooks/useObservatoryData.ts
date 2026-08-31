/**
 * Pellier Observatory — live data-fetching hook.
 *
 * Participant-facing panels read their state from the API. A failed request is
 * rendered as an explicit unavailable state; it is never substituted with a
 * browser fixture that could be mistaken for an Aurora result.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface UseObservatoryDataOptions {
  key: string;
  params?: Record<string, string>;
}

export interface UseObservatoryDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const apiEndpoints: Record<string, string> = {
  sessions: '/api/observatory/sessions',
  agents: '/api/observatory/agents',
  tools: '/api/observatory/tools/list',
  routing: '/api/observatory/routing',
  skills: '/api/observatory/skills',
  performance: '/api/observatory/performance',
  evaluations: '/api/observatory/evaluations',
  architecture: '/api/observatory/architecture',
  'production-patterns': '/api/observatory/production-patterns',
};

function buildApiUrl(key: string, params?: Record<string, string>): string {
  if (key.startsWith('session-') && key !== 'sessions') {
    return `/api/observatory/sessions/${key.replace('session-', '')}`;
  }
  if (key.startsWith('memory-')) {
    return `/api/observatory/memory/${key.replace('memory-', '')}`;
  }

  const base = apiEndpoints[key] ?? `/api/observatory/${key}`;
  if (!params || Object.keys(params).length === 0) return base;
  return `${base}?${new URLSearchParams(params).toString()}`;
}

export function useObservatoryData<T = unknown>(
  options: UseObservatoryDataOptions,
): UseObservatoryDataResult<T> {
  const { key, params } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const paramsKey = JSON.stringify(params ?? {});

  const fetchData = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(buildApiUrl(key, params));
      if (!response.ok) {
        throw new Error(
          `Live data request failed: ${response.status} ${response.statusText}`,
        );
      }
      const payload = await response.json();
      if (requestId === requestIdRef.current) {
        setData(payload as T);
      }
    } catch (err) {
      if (requestId === requestIdRef.current) {
        setData(null);
        setError(
          err instanceof Error ? err.message : 'Live data request failed',
        );
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
    // `paramsKey` supplies a stable dependency for object-shaped query params.
  }, [key, paramsKey]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
