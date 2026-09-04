/**
 * EvaluationsDetail — Architecture detail page for Evaluations.
 *
 * Agent quality measurement and tracking — accuracy, latency, citation rates.
 *
 * Requirements: 7.1, 7.6, 7.7
 */

import React from 'react';
import DetailPageShell from './DetailPageShell';
import { ExpCard } from '../../../components';
import { useObservatoryData } from '../../../hooks/useObservatoryData';
import type { ArchitectureConcept } from '../../../types';
import { DetailLoadingState, DetailErrorState, DetailEmptyState } from './DetailStates';
import { ARCHITECTURE_CODE_BLOCK } from './codeStyles';
import { SectionEyebrow } from '../../../../shared';

const EvaluationsDetail: React.FC = () => {
  const { data, loading, error, refetch } = useObservatoryData<ArchitectureConcept[]>({
    key: 'architecture',
  });

  const concept = data?.find((c) => c.slug === 'evaluations');

  return (
    <DetailPageShell
      numeral="VI"
      conceptName="Evaluations"
      category="quality"
      title="Evaluations, measured."
      prose="Evaluations are the quality layer. They are not in the request path; they help decide whether a retrieval, rerank, routing, or write-path change is worth shipping."
      cheatSheet={[
        {
          numeral: 'i.',
          text: 'Every agent has a scorecard: accuracy, latency P50/P95, and citation rate. These are the four numbers that matter.',
        },
        {
          numeral: 'ii.',
          text: 'Version-over-version trends show whether changes improve or regress quality. Track the trend, not just the snapshot.',
        },
        {
          numeral: 'iii.',
          text: 'Evaluation recipes are specific test cases. Each recipe tests one capability – search accuracy, recommendation relevance, pricing correctness.',
        },
      ]}
      liveState={{
        label: 'Current evaluation state across all agents. Shows aggregate accuracy and the number of evaluation recipes tracked.',
        values: [
          { label: 'Agents evaluated', value: '5' },
          { label: 'Avg accuracy', value: '91%' },
          { label: 'Recipes', value: '12' },
        ],
      }}
    >
      {loading && <DetailLoadingState />}
      {error && <DetailErrorState message={error} onRetry={refetch} />}
      {!loading && !error && !concept && <DetailEmptyState conceptName="Evaluations" />}
      {!loading && !error && concept && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Scorecard structure */}
          <ExpCard>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <SectionLabel label="The scorecard" />
              <h3 style={titleStyle}>Four metrics, one card.</h3>
              <p style={proseStyle}>
                Each agent's scorecard captures accuracy (how often the response is correct),
                latency (P50 and P95 response times), and citation rate (how often the agent
                grounds its response in data). These four numbers tell you if the agent is
                working.
              </p>
            </div>
          </ExpCard>

          {/* Sample scorecards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <ScorecardCard
              agent="Search"
              accuracy={94}
              latencyP50={340}
              latencyP95={620}
              citationRate={88}
            />
            <ScorecardCard
              agent="Recommendation"
              accuracy={89}
              latencyP50={420}
              latencyP95={780}
              citationRate={92}
            />
            <ScorecardCard
              agent="Pricing"
              accuracy={97}
              latencyP50={180}
              latencyP95={310}
              citationRate={95}
            />
            <ScorecardCard
              agent="Inventory"
              accuracy={91}
              latencyP50={220}
              latencyP95={450}
              citationRate={85}
            />
          </div>

          {/* Code snippet */}
          <ExpCard>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <SectionLabel label="Code" />
              <pre style={codeStyle}>{concept.codeSnippet}</pre>
            </div>
          </ExpCard>
        </div>
      )}
    </DetailPageShell>
  );
};

/* ---- Sub-components ---- */

const ScorecardCard: React.FC<{
  agent: string;
  accuracy: number;
  latencyP50: number;
  latencyP95: number;
  citationRate: number;
}> = ({ agent, accuracy, latencyP50, latencyP95, citationRate }) => (
  <ExpCard>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <span style={{ fontFamily: 'var(--obs-heading)', fontSize: '18px', color: 'var(--obs-ink-1)' }}>
        {agent}
      </span>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        <MetricCell label="Accuracy" value={`${accuracy}%`} />
        <MetricCell label="P50 latency" value={`${latencyP50}ms`} />
        <MetricCell label="P95 latency" value={`${latencyP95}ms`} />
        <MetricCell label="Citation rate" value={`${citationRate}%`} />
      </div>
    </div>
  </ExpCard>
);

const MetricCell: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
    <SectionEyebrow tone="muted" dot={false}>
      {label}
    </SectionEyebrow>
    {/* A measured value is a figure, and every figure on these surfaces is
        set in the display face. */}
    <span
      style={{
        fontFamily: 'var(--obs-display)',
        fontSize: '22px',
        fontWeight: 400,
        color: 'var(--obs-ink-1)',
        letterSpacing: '-0.02em',
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      {value}
    </span>
  </div>
);

/* ---- Shared styles ---- */

/* One label register on the surface. This was six identical copies of a mono
   0.22em recipe, one per detail page; mono here marked prose, not an
   identifier, which is the distinction the shared primitive restores. */
const SectionLabel: React.FC<{ label: string }> = ({ label }) => (
  <SectionEyebrow tone="muted" dot={false}>
    {label}
  </SectionEyebrow>
);

const titleStyle: React.CSSProperties = {
  fontFamily: 'var(--obs-heading)', fontSize: '22px', fontWeight: 400,
  lineHeight: 1.15, color: 'var(--obs-ink-1)', margin: 0,
};

const proseStyle: React.CSSProperties = {
  fontFamily: 'var(--obs-sans)', fontSize: 'var(--obs-body-size)', lineHeight: 'var(--obs-body-leading)',
  color: 'var(--obs-ink-1)', margin: 0, maxWidth: '560px',
};

const codeStyle: React.CSSProperties = {
  ...ARCHITECTURE_CODE_BLOCK,
  whiteSpace: 'pre',
};

export default EvaluationsDetail;
