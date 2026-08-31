import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useObservatoryData } from '../hooks/useObservatoryData';
import { useToolDiscovery } from '../hooks/useToolDiscovery';

describe('useObservatoryData', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  it('loads only the live API endpoint', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([{ id: 'live-session' }]),
    });
    const { result } = renderHook(() => useObservatoryData({ key: 'sessions' }));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(fetchMock).toHaveBeenCalledWith('/api/observatory/sessions');
    expect(result.current.data).toEqual([{ id: 'live-session' }]);
    expect(result.current.error).toBeNull();
  });

  it('leaves data empty and exposes an API failure', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
    });
    const { result } = renderHook(() => useObservatoryData({ key: 'tools' }));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBeNull();
    expect(result.current.error).toContain('503');
  });
});

describe('useToolDiscovery', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('calls Aurora-backed discovery and returns its payload verbatim', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          results: [{ rank: 1, name: 'search_products' }],
          duration_ms: 42,
          sql: 'SELECT name FROM pellier.tools',
        }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useToolDiscovery());

    await act(async () => {
      await result.current.discover('linen products');
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/observatory/tools/discover',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result.current.results).toEqual([{ rank: 1, name: 'search_products' }]);
    expect(result.current.sql).toContain('pellier.tools');
  });
});
