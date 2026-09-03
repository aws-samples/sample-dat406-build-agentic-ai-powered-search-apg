import { describe, expect, it } from 'vitest';
import { parseRetrievalReceipt } from './retrievalReceipt';

describe('parseRetrievalReceipt', () => {
  it('returns null when the event carries no ranking stage', () => {
    expect(parseRetrievalReceipt(undefined)).toBeNull();
    expect(parseRetrievalReceipt({ caller: 'search_agent' })).toBeNull();
  });

  it('merges the per-stage maps into one candidate table in final order', () => {
    const view = parseRetrievalReceipt({
      vector_ranks: { '11': 1, '16': 2, '14': 3 },
      lexical_ranks: { '16': 1, '11': 4 },
      rrf_scores: { '11': 0.0325, '16': 0.0328, '14': 0.0161 },
      rerank_scores: { '11': 0.91, '16': 0.77 },
      latency_breakdown: { embed_ms: 41, vector_ms: 12, lexical_ms: 6, rerank_ms: 320 },
      merchandising_rules: [{ rule: 'bestseller_boost' }],
      memory_record_ids_used: ['mem-1'],
      query_preview: 'linen shirt for Goa',
    });
    expect(view).not.toBeNull();
    expect(view!.candidates.map((c) => c.productId)).toEqual(['11', '16', '14']);
    expect(view!.candidates[0]).toEqual({
      productId: '11',
      vectorRank: 1,
      lexicalRank: 4,
      rrfScore: 0.0325,
      rerankScore: 0.91,
    });
    expect(view!.candidates[2].lexicalRank).toBeNull();
    expect(view!.candidates[2].rerankScore).toBeNull();
    expect(view!.latency).toEqual([
      { stage: 'embed_ms', ms: 41 },
      { stage: 'vector_ms', ms: 12 },
      { stage: 'lexical_ms', ms: 6 },
      { stage: 'rerank_ms', ms: 320 },
    ]);
    expect(view!.merchandisingRules).toBe(1);
    expect(view!.memoryRecordIds).toEqual(['mem-1']);
    expect(view!.queryPreview).toBe('linen shirt for Goa');
    expect(view!.stages).toEqual({ vector: true, lexical: true, rrf: true, rerank: true });
  });

  it('falls back to RRF order when rerank never ran', () => {
    const view = parseRetrievalReceipt({
      vector_ranks: { a: 2, b: 1 },
      rrf_scores: { a: 0.02, b: 0.03 },
      rerank_scores: {},
    });
    expect(view!.candidates.map((c) => c.productId)).toEqual(['b', 'a']);
    expect(view!.stages.rerank).toBe(false);
  });
});
