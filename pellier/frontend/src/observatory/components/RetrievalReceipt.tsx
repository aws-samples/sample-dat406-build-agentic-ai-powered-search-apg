/**
 * RetrievalReceipt — the candidate table behind one retrieval or rerank
 * ledger event: every product the turn considered, its rank in each branch,
 * the fused RRF score and the rerank score, plus the stage latencies and the
 * memory records the search plan used. The same numbers the Search pipeline
 * page shows for a typed query, here for the query the shopper actually sent.
 */
import React from 'react';
import type { RetrievalReceiptView } from '../labs/retrievalReceipt';

const dash = '–';

function rank(value: number | null): string {
  return value === null ? dash : String(value);
}

function score(value: number | null, digits: number): string {
  return value === null ? dash : value.toFixed(digits);
}

export const RetrievalReceipt: React.FC<{ view: RetrievalReceiptView }> = ({
  view,
}) => (
  <div
    className="observatory-retrieval-receipt"
    data-testid="observatory-retrieval-receipt"
  >
    <div className="observatory-retrieval-receipt-head">
      <span>
        {view.candidates.length} candidate
        {view.candidates.length === 1 ? '' : 's'} ranked
        {view.queryPreview ? (
          <>
            {' '}
            for <code>{view.queryPreview}</code>
          </>
        ) : null}
      </span>
      {view.latency.length > 0 ? (
        <span className="observatory-retrieval-latency">
          {view.latency.map(({ stage, ms }) => (
            <code key={stage}>
              {stage.replace(/_ms$/, '')} {ms} ms
            </code>
          ))}
        </span>
      ) : null}
    </div>
    <div className="observatory-retrieval-table-wrap">
      <table className="observatory-retrieval-table">
        <thead>
          <tr>
            <th scope="col">product</th>
            {view.stages.vector ? <th scope="col">vector</th> : null}
            {view.stages.lexical ? <th scope="col">lexical</th> : null}
            {view.stages.rrf ? <th scope="col">rrf</th> : null}
            {view.stages.rerank ? <th scope="col">rerank</th> : null}
          </tr>
        </thead>
        <tbody>
          {view.candidates.map((candidate) => (
            <tr key={candidate.productId}>
              <td>{candidate.productId}</td>
              {view.stages.vector ? <td>{rank(candidate.vectorRank)}</td> : null}
              {view.stages.lexical ? (
                <td>{rank(candidate.lexicalRank)}</td>
              ) : null}
              {view.stages.rrf ? <td>{score(candidate.rrfScore, 4)}</td> : null}
              {view.stages.rerank ? (
                <td>{score(candidate.rerankScore, 3)}</td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    {view.memoryRecordIds.length > 0 || view.merchandisingRules > 0 ? (
      <div className="observatory-retrieval-receipt-foot">
        {view.memoryRecordIds.length > 0 ? (
          <span>
            memory records used:{' '}
            {view.memoryRecordIds.map((id) => (
              <code key={id}>{id}</code>
            ))}
          </span>
        ) : null}
        {view.merchandisingRules > 0 ? (
          <span>
            {view.merchandisingRules} merchandising rule
            {view.merchandisingRules === 1 ? '' : 's'} applied
          </span>
        ) : null}
      </div>
    ) : null}
  </div>
);

export default RetrievalReceipt;
