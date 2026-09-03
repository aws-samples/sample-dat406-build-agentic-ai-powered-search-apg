/**
 * Performance surface: a payload with samples but no recorded panels.
 *
 * The live endpoint returned exactly this shape during the design audit:
 * 123 warm samples, a cold-start median of zero, and every array empty. The
 * page rendered the full "live" layout around three structurally empty
 * panels and a "0ms" median that read as a measurement. Evaluations, one
 * nav group away, names what is unavailable; Performance must too.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { PerformanceData } from '../../types';

const sparse = {
  coldStartP50: 0,
  warmReuseP50: 2939,
  sampleCount: 123,
  histogram: [],
  latencyBudget: [],
  pgvectorComparison: [],
  pgvectorTuning: [],
  searchStrategies: [],
  storageUsage: [],
} as unknown as PerformanceData;

vi.mock('../../hooks/useObservatoryData', () => ({
  useObservatoryData: () => ({
    data: sparse,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

import Performance from './Performance';

describe('Performance with samples but no recorded panels', () => {
  it('never prints a zero median as a measurement', () => {
    render(
      <MemoryRouter>
        <Performance />
      </MemoryRouter>,
    );
    expect(screen.queryByText('0ms')).not.toBeInTheDocument();
    expect(screen.getByTestId('performance-stat-cold-start')).toHaveTextContent(
      'No cold starts recorded',
    );
  });

  it('names each unrecorded panel instead of drawing it empty', () => {
    render(
      <MemoryRouter>
        <Performance />
      </MemoryRouter>,
    );
    const notes = screen.getAllByTestId('performance-panel-unrecorded');
    expect(notes.map((n) => n.getAttribute('data-panel'))).toEqual([
      'cold-start-distribution',
      'latency-budget',
      'pgvector-comparison',
      'storage-usage',
    ]);
    expect(document.querySelector('svg rect')).toBeNull();
  });
});
