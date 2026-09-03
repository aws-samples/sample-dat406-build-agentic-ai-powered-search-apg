/**
 * Parses the retrieval receipt a ledger event carries in `details` into rows a
 * table can render. `pellier.retrieval_receipts` stores each ranking stage as
 * a product-id keyed map; the per-turn ledger merges those maps into the
 * `retrieval` and `rerank` events. Nothing here is fabricated: a stage the
 * turn never ran is simply absent and its cells render as em dashes.
 */

export interface RetrievalCandidate {
  productId: string;
  vectorRank: number | null;
  lexicalRank: number | null;
  rrfScore: number | null;
  rerankScore: number | null;
}

export interface RetrievalReceiptView {
  candidates: RetrievalCandidate[];
  latency: Array<{ stage: string; ms: number }>;
  merchandisingRules: number;
  memoryRecordIds: string[];
  queryPreview: string | null;
  stages: { vector: boolean; lexical: boolean; rrf: boolean; rerank: boolean };
}

function numericMap(value: unknown): Record<string, number> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  const out: Record<string, number> = {};
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    const n = typeof raw === 'number' ? raw : Number(raw);
    if (Number.isFinite(n)) out[key] = n;
  }
  return out;
}

/** Returns null when the details carry no ranking stage at all. */
export function parseRetrievalReceipt(
  details: Record<string, unknown> | undefined,
): RetrievalReceiptView | null {
  if (!details) return null;
  const vector = numericMap(details.vector_ranks);
  const lexical = numericMap(details.lexical_ranks);
  const rrf = numericMap(details.rrf_scores);
  const rerank = numericMap(details.rerank_scores);
  const ids = new Set([
    ...Object.keys(vector),
    ...Object.keys(lexical),
    ...Object.keys(rrf),
    ...Object.keys(rerank),
  ]);
  if (ids.size === 0) return null;

  const candidates: RetrievalCandidate[] = [...ids].map((productId) => ({
    productId,
    vectorRank: productId in vector ? vector[productId] : null,
    lexicalRank: productId in lexical ? lexical[productId] : null,
    rrfScore: productId in rrf ? rrf[productId] : null,
    rerankScore: productId in rerank ? rerank[productId] : null,
  }));
  // Final order first: rerank score when it ran, otherwise RRF, otherwise the
  // best branch rank, so the table reads top to bottom as the shopper saw it.
  candidates.sort((a, b) => {
    if (a.rerankScore !== null || b.rerankScore !== null) {
      return (b.rerankScore ?? -Infinity) - (a.rerankScore ?? -Infinity);
    }
    if (a.rrfScore !== null || b.rrfScore !== null) {
      return (b.rrfScore ?? -Infinity) - (a.rrfScore ?? -Infinity);
    }
    const ra = Math.min(a.vectorRank ?? Infinity, a.lexicalRank ?? Infinity);
    const rb = Math.min(b.vectorRank ?? Infinity, b.lexicalRank ?? Infinity);
    return ra - rb;
  });

  const latency = Object.entries(numericMap(details.latency_breakdown)).map(
    ([stage, ms]) => ({ stage, ms }),
  );
  const rules = Array.isArray(details.merchandising_rules)
    ? details.merchandising_rules.length
    : 0;
  const memoryRecordIds = Array.isArray(details.memory_record_ids_used)
    ? details.memory_record_ids_used.map((id) => String(id))
    : [];
  const queryPreview =
    typeof details.query_preview === 'string' && details.query_preview.trim()
      ? details.query_preview.trim()
      : null;

  return {
    candidates,
    latency,
    merchandisingRules: rules,
    memoryRecordIds,
    queryPreview,
    stages: {
      vector: Object.keys(vector).length > 0,
      lexical: Object.keys(lexical).length > 0,
      rrf: Object.keys(rrf).length > 0,
      rerank: Object.keys(rerank).length > 0,
    },
  };
}
