/**
 * Performance surface tests — live vs fixture provenance separation.
 *
 * The governed-workshop audit's A7 finding: the Search Strategy Comparison
 * card merged live latency and live product order onto the *fixture's*
 * recall@5 value inside the same table row. An attendee reading that row
 * would reasonably conclude the recall score described the query they had
 * just run, which it never did.
 *
 * These tests pin the fix in both directions:
 *   - Before a live run, recall renders with an explicit "fixture baseline"
 *     provenance label.
 *   - After a live run, the recall cell reads "not measured" and the
 *     fixture numbers appear only in a visually separate reference block.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import performanceRaw from '../../fixtures/performance.json';
import type { PerformanceData } from '../../types';

vi.mock('../../hooks/useObservatoryData', () => ({
  useObservatoryData: () => ({
    data: performanceRaw as unknown as PerformanceData,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

import Performance from './Performance';

const data = performanceRaw as unknown as PerformanceData;

function renderSurface() {
  return render(
    <MemoryRouter>
      <Performance />
    </MemoryRouter>,
  );
}

/** One live payload shaped like the compare endpoint's response. */
function liveComparePayload() {
  return {
    query: 'A milestone gift for a new homeowner',
    strategies: data.searchStrategies.map((s, index) => ({
      strategy: s.strategy,
      observedMs: 120 + index,
      modeledCostPerThousandUsd: s.modeledCostPerThousandUsd,
      products: [{ name: `Live product ${index}`, productId: index + 1 }],
      ...(s.strategy.includes('rerank')
        ? {
            rerank: {
              status: 'applied' as const,
              model: 'cohere.rerank-v3-5:0',
              candidates: 30,
              returned: 5,
              fallbackOrder: null,
            },
          }
        : {}),
      ...(s.isShipped
        ? {
            extractedFilters: {
              categories: ['Home Decor'],
              tags: ['gift'],
              priceMaxUsd: 100,
              inStockOnly: true,
              softSignal: 'considered housewarming gift',
              filterUsed: 'strict' as const,
            },
          }
        : {}),
    })),
  };
}

describe('Performance · recall provenance', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => liveComparePayload(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('labels fixture recall as a baseline before any live run', () => {
    renderSurface();

    expect(screen.getAllByText(/fixture baseline/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/not measured/i)).toBeNull();
  });

  it('stops showing a fixture recall number once results are live', async () => {
    renderSurface();

    await userEvent.click(
      screen.getByRole('button', { name: /run on aurora/i }),
    );

    // Scope to the exact cell text: the surrounding explanatory copy also
    // contains the phrase "not measured live".
    await waitFor(() => {
      expect(screen.getAllByText('not measured').length).toBe(
        data.searchStrategies.length,
      );
    });
    // The in-row fixture label is gone; recall moved to its own block.
    expect(screen.queryByText(/fixture baseline/i)).toBeNull();
  });

  it('moves fixture recall into a separate reference-baseline block when live', async () => {
    renderSurface();

    await userEvent.click(
      screen.getByRole('button', { name: /run on aurora/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByText(/reference baseline · fixture, not this query/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/these describe the seeded catalog overall/i),
    ).toBeInTheDocument();
  });

  it('states plainly that latency is live and recall is not', async () => {
    renderSurface();

    await userEvent.click(
      screen.getByRole('button', { name: /run on aurora/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByText(/recall is\s+not measured live/i),
      ).toBeInTheDocument();
    });
  });

  it('shows whether Cohere actually reranked instead of trusting the strategy label', async () => {
    renderSurface();

    await userEvent.click(
      screen.getByRole('button', { name: /run on aurora/i }),
    );

    await waitFor(() => {
      expect(screen.getAllByText(/Cohere applied/i)).toHaveLength(2);
    });
    expect(screen.getAllByText(/cohere\.rerank-v3-5:0/i)).toHaveLength(2);
  });
});
