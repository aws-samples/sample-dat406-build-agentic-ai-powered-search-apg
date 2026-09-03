import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RetrievalReceipt } from './RetrievalReceipt';
import { parseRetrievalReceipt } from '../labs/retrievalReceipt';

describe('RetrievalReceipt', () => {
  it('renders one row per candidate with only the stages that ran', () => {
    const view = parseRetrievalReceipt({
      vector_ranks: { '11': 1, '16': 2 },
      rrf_scores: { '11': 0.0325, '16': 0.0161 },
      latency_breakdown: { vector_ms: 12 },
      query_preview: 'linen shirt',
    });
    render(<RetrievalReceipt view={view!} />);
    const table = screen.getByRole('table');
    expect(table.querySelectorAll('thead th')).toHaveLength(3);
    expect(table.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(screen.getByText('linen shirt')).toBeInTheDocument();
    expect(screen.getByText('vector 12 ms')).toBeInTheDocument();
    expect(screen.queryByText('rerank')).not.toBeInTheDocument();
  });
});
