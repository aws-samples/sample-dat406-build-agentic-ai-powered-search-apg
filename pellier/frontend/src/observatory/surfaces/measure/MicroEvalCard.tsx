/**
 * Micro-eval: the same query, two rerank candidate pools.
 *
 * The reranker can only reorder what retrieval handed it, so the size of the
 * candidate pool is a retrieval decision wearing a ranking costume. This card
 * puts both pools in one table and states the trade in a line, so "make it
 * faster" is weighed against what the faster pool stops finding.
 *
 * Every number is measured server-side, and every caption here names what the
 * backend actually computes: the definitions live in
 * `services/planned_hybrid_retrieval.py::micro_eval_variant`, and a caption
 * that drifts from them is worse than no caption. When the endpoint is not
 * there the card says so rather than drawing an empty table.
 *
 * The run is asked for, never automatic. One press is two pool sizes times
 * the endpoint's repetition count of live Aurora retrieval, each with a
 * Cohere Rerank call, so firing on mount would bill every participant who
 * scrolled past the Performance surface.
 */
import React, { useEffect, useRef, useState } from 'react';

import { ExpCard, Eyebrow } from '../../components';
import {
  fetchMicroEval,
  poolCostReading,
  type MicroEvalResult,
  type MicroEvalVariant,
} from '../../../services/microEval';

type Format = 'rate' | 'ratio' | 'count' | 'flag' | 'ms';

interface MetricRow {
  label: string;
  field: keyof MicroEvalVariant;
  format: Format;
  /** What the backend computes for this field, in the participant's terms. */
  note: string;
}

/**
 * The table, in the backend's own definitions.
 *
 * `golden ids` are the labeled relevant rows for the canonical query, pinned
 * in `CANONICAL_ANNA_GOLDEN_IDS`; `returned` is the top `limit` rows after
 * the eligibility recheck.
 */
const METRICS: readonly MetricRow[] = [
  {
    label: 'Candidate coverage',
    field: 'candidate_coverage',
    format: 'rate',
    note: 'labelled relevant rows that reached the rerank pool',
  },
  {
    label: 'Context precision',
    field: 'context_precision',
    format: 'rate',
    note: 'returned rows that are labelled relevant',
  },
  {
    label: 'Reciprocal rank',
    field: 'mrr',
    format: 'ratio',
    note: 'one over the rank of the first labelled relevant row; 1.00 is top',
  },
  {
    label: 'Hard-constraint violations',
    field: 'hard_constraint_violations',
    format: 'count',
    note: 'returned rows over the price ceiling or out of stock',
  },
  {
    label: 'Short result',
    field: 'short_result_rate',
    format: 'flag',
    note: 'the pass returned fewer rows than the limit asked for',
  },
  {
    label: 'Citation coverage',
    field: 'citation_coverage',
    format: 'rate',
    note: 'returned rows carrying a citable product id',
  },
  {
    label: 'Latency p50',
    field: 'latency_ms_p50',
    format: 'ms',
    note: 'median across the repetitions',
  },
  {
    label: 'Latency p95',
    field: 'latency_ms_p95',
    format: 'ms',
    note: '95th percentile across the repetitions',
  },
];

function formatValue(value: number, format: Format): string {
  if (format === 'rate') return `${Math.round(value * 100)}%`;
  // A reciprocal rank is 1, 1/2, 1/3 ...: a position, not a rate. Rendering
  // it as a percentage invited "83% of what?".
  if (format === 'ratio') return value.toFixed(2);
  if (format === 'flag') return value > 0 ? 'Yes' : 'No';
  if (format === 'ms') return `${Math.round(value)} ms`;
  return String(value);
}

const cellStyle: React.CSSProperties = {
  padding: '9px 12px',
  borderTop: '1px solid var(--obs-rule-1)',
  fontFamily: 'var(--obs-mono)',
  fontSize: '13px',
  color: 'var(--obs-ink-1)',
  textAlign: 'right',
  whiteSpace: 'nowrap',
};

const headerStyle: React.CSSProperties = {
  padding: '0 12px 8px',
  fontFamily: 'var(--obs-heading)',
  fontSize: '12px',
  fontWeight: 600,
  letterSpacing: '0.04em',
  color: 'var(--obs-ink-3)',
  textAlign: 'right',
};

const runButtonStyle: React.CSSProperties = {
  marginTop: '14px',
  padding: '9px 18px',
  border: '1px solid var(--obs-ink-1)',
  borderRadius: '4px',
  backgroundColor: 'var(--obs-ink-1)',
  color: 'var(--obs-cream-1)',
  fontFamily: 'var(--obs-heading)',
  fontSize: '12px',
  fontWeight: 600,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const noteStyle: React.CSSProperties = {
  marginTop: '12px',
  fontFamily: 'var(--obs-sans)',
  fontSize: '14px',
  lineHeight: 1.5,
  color: 'var(--obs-ink-3)',
};

type RunState = 'idle' | 'running' | 'done';

const MicroEvalCard: React.FC = () => {
  const [result, setResult] = useState<MicroEvalResult | null>(null);
  const [state, setState] = useState<RunState>('idle');
  const abortRef = useRef<AbortController | null>(null);

  // Unmounting is the only way a run in flight is abandoned: once the surface
  // is gone the request has nothing left to report to.
  useEffect(() => () => abortRef.current?.abort(), []);

  const run = () => {
    if (state === 'running') return;
    // Nothing is in flight at this point. The guard above and the disabled
    // button both refuse a press while a run is going, so this retires an
    // already-settled controller rather than cancelling live work.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState('running');
    void fetchMicroEval(controller.signal).then((payload) => {
      if (controller.signal.aborted) return;
      setResult(payload);
      setState('done');
    });
  };

  const runControl = (
    <button
      type="button"
      onClick={run}
      disabled={state === 'running'}
      data-testid="micro-eval-run"
      style={{
        ...runButtonStyle,
        cursor: state === 'running' ? 'not-allowed' : 'pointer',
        opacity: state === 'running' ? 0.4 : 1,
      }}
    >
      {state === 'running' ? 'Running\u2026' : 'Run both pools on Aurora'}
    </button>
  );

  if (state === 'idle') {
    return (
      <ExpCard>
        <Eyebrow label="Rerank pool micro-eval" variant="muted" />
        <p style={noteStyle}>
          Runs the canonical query at pool_k 20 and pool_k 3 and scores both
          against the labelled relevant rows. Every pass is live Aurora
          retrieval plus a Cohere Rerank call, so it runs when you ask.
        </p>
        {runControl}
      </ExpCard>
    );
  }

  if (state === 'running') {
    return (
      <ExpCard>
        <Eyebrow label="Rerank pool micro-eval" variant="muted" />
        <p data-testid="micro-eval-loading" role="status" style={noteStyle}>
          Running the canonical query at both pool sizes.
        </p>
        {runControl}
      </ExpCard>
    );
  }

  if (!result) {
    return (
      <ExpCard>
        <Eyebrow label="Rerank pool micro-eval" variant="muted" />
        <p data-testid="micro-eval-unavailable" style={noteStyle}>
          The micro-eval endpoint did not answer, so there is nothing measured
          to compare. Numbers invented here would describe no run.
        </p>
        {runControl}
      </ExpCard>
    );
  }

  const sorted = [...result.variants].sort((a, b) => b.pool_k - a.pool_k);
  const [wide, narrow] = sorted;

  return (
    <ExpCard>
      <Eyebrow label="Rerank pool micro-eval" />
      <p
        style={{
          margin: '12px 0 4px',
          fontFamily: 'var(--obs-sans)',
          fontSize: '14px',
          lineHeight: 1.5,
          color: 'var(--obs-ink-2)',
        }}
      >
        <span style={{ fontFamily: 'var(--obs-mono)', fontSize: '13px' }}>
          {result.query}
        </span>
      </p>
      <p
        style={{
          margin: '0 0 14px',
          fontFamily: 'var(--obs-sans)',
          fontSize: '12px',
          color: 'var(--obs-ink-3)',
        }}
      >
        {`Top ${result.limit} results, ${result.repetitions} repetitions per pool, measured on Aurora.`}
      </p>

      <div style={{ overflowX: 'auto' }}>
        <table
          aria-label="Rerank pool comparison"
          style={{ width: '100%', borderCollapse: 'collapse' }}
        >
          <thead>
            <tr>
              <th scope="col" style={{ ...headerStyle, textAlign: 'left' }}>
                Metric
              </th>
              {sorted.map((variant) => (
                <th key={variant.pool_k} scope="col" style={headerStyle}>
                  {`pool_k ${variant.pool_k}`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map((metric) => (
              <tr key={metric.field}>
                <th
                  scope="row"
                  style={{
                    ...cellStyle,
                    textAlign: 'left',
                    fontFamily: 'var(--obs-sans)',
                    fontWeight: 500,
                    whiteSpace: 'normal',
                  }}
                >
                  {metric.label}
                  <span
                    style={{
                      display: 'block',
                      fontSize: '11px',
                      color: 'var(--obs-ink-3)',
                    }}
                  >
                    {metric.note}
                  </span>
                </th>
                {sorted.map((variant) => (
                  <td key={variant.pool_k} style={cellStyle}>
                    {formatValue(variant[metric.field], metric.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {wide && narrow ? (
        <p
          data-testid="micro-eval-reading"
          style={{
            margin: '14px 0 0',
            paddingTop: '12px',
            borderTop: '1px solid var(--obs-rule-1)',
            fontFamily: 'var(--obs-sans)',
            fontSize: '14px',
            lineHeight: 1.5,
            color: 'var(--obs-ink-1)',
          }}
        >
          {poolCostReading(wide, narrow)}
        </p>
      ) : null}
      {runControl}
    </ExpCard>
  );
};

export default MicroEvalCard;
