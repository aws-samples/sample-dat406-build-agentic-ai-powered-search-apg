/**
 * RuntimeDetail — Architecture detail page for Runtime Envelope.
 *
 * Managed deployment envelope around bounded Storefront and Operator invocations.
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

const RuntimeDetail: React.FC = () => {
  const { data, loading, error, refetch } = useObservatoryData<ArchitectureConcept[]>({
    key: 'architecture',
  });

  const concept = data?.find((c) => c.slug === 'runtime');

  return (
    <DetailPageShell
      numeral="V"
      conceptName="Runtime Envelope"
      category="workshop"
      title="Runtime, bounded."
      prose="AgentCore Runtime is the deployment target for the Storefront Dispatcher and the Operator Concierge Strands graph. Each invocation finishes and persists its result. PostgreSQL, not a suspended Runtime process, holds the human checkpoint between requests."
      cheatSheet={[
        {
          numeral: 'i.',
          text: 'A Storefront invocation runs triage, Dispatcher, one specialist/tool path, telemetry, and response streaming.',
        },
        {
          numeral: 'ii.',
          text: 'An Operator Concierge invocation runs Case Investigator, then Resolution Planner, and persists graph metadata and node timings with the answer.',
        },
        {
          numeral: 'iii.',
          text: 'The pending review exists before the graph. Human confirmation and governed execution are separate authenticated requests after the graph.',
        },
      ]}
      liveState={{
        label: 'Managed deployment target and the durable state boundary between invocations.',
        values: [
          { label: 'Deployment target', value: 'AgentCore Runtime' },
          { label: 'Operator topology', value: '2-agent graph' },
          { label: 'Human wait state', value: 'PostgreSQL' },
        ],
      }}
    >
      {loading && <DetailLoadingState />}
      {error && <DetailErrorState message={error} onRetry={refetch} />}
      {!loading && !error && !concept && <DetailEmptyState conceptName="Runtime Envelope" />}
      {!loading && !error && concept && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Runtime layers */}
          <ExpCard>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <SectionLabel label="The layers" />
              <h3 style={titleStyle}>Short invocations; durable continuity.</h3>
              <p style={proseStyle}>
                Runtime executes agent work. PostgreSQL carries the review, action hash,
                decision, and receipts across requests. No worker, graph node, or model
                call stays open while a person decides.
              </p>
              <RuntimeLayersDiagram />
            </div>
          </ExpCard>

          {/* Layer cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <LayerCard
              name="Storefront invocation"
              timing="bounded"
              description="Dispatcher chooses one specialist and returns a grounded shopper response."
            />
            <LayerCard
              name="Operator graph invocation"
              timing="2 nodes"
              description="Case Investigator feeds Resolution Planner; the artifact and node timings persist with the conversation."
            />
            <LayerCard
              name="Human checkpoint"
              timing="between requests"
              description="PostgreSQL stores the pending review and exact action hash until an authenticated operator decides."
            />
            <LayerCard
              name="Governed execution"
              timing="new request"
              description="A separate deterministic path invokes Gateway and Policy, then records database and evidence outcomes."
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

const LayerCard: React.FC<{
  name: string;
  timing: string;
  description: string;
}> = ({ name, timing, description }) => (
  <ExpCard>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
        <span style={{ fontFamily: 'var(--obs-heading)', fontSize: '16px', color: 'var(--obs-ink-1)' }}>
          {name}
        </span>
        <span style={{ fontFamily: 'var(--obs-mono)', fontSize: '11px', color: 'var(--obs-ink-4)' }}>
          {timing}
        </span>
      </div>
      <p style={{ fontFamily: 'var(--obs-sans)', fontSize: '14px', lineHeight: 1.5, color: 'var(--obs-ink-1)', margin: 0 }}>
        {description}
      </p>
    </div>
  </ExpCard>
);

const RuntimeLayersDiagram: React.FC = () => (
  <svg
    viewBox="0 0 900 240"
    width="100%"
    role="img"
    aria-label="Bounded AgentCore Runtime invocations separated by durable PostgreSQL checkpoints"
    style={{ maxWidth: '900px', display: 'block', margin: '0 auto' }}
  >
    <defs>
      <marker id="runtime-arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
        <polygon points="0 0, 8 3, 0 6" fill="rgba(168,66,58,0.5)" />
      </marker>
    </defs>
    {[164, 342, 520, 698].map((x) => (
      <line key={x} x1={x} y1="105" x2={x + 42} y2="105" stroke="rgba(168,66,58,0.5)" strokeWidth="1.5" markerEnd="url(#runtime-arrowhead)" />
    ))}
    {[
      { x: 10, title: 'Storefront', detail: 'Dispatcher Runtime', platform: true },
      { x: 188, title: 'Handoff + review', detail: 'PostgreSQL', platform: false },
      { x: 366, title: 'Operator graph', detail: 'Runtime target', platform: true },
      { x: 544, title: 'Human decision', detail: 'PostgreSQL', platform: false },
      { x: 722, title: 'Execution', detail: 'Gateway + Policy', platform: true },
    ].map((node) => (
      <g key={node.title}>
        <rect
          x={node.x}
          y="70"
          width="154"
          height="70"
          rx="8"
          fill={node.platform ? '#1f1410' : 'var(--cream-warm)'}
          stroke={node.platform ? '#1f1410' : 'rgba(168,66,58,0.55)'}
        />
        <text x={node.x + 77} y="100" textAnchor="middle" fontFamily="Instrument Sans, sans-serif" fontSize="13" fill={node.platform ? 'var(--cream-warm)' : '#1f1410'}>{node.title}</text>
        <text x={node.x + 77} y="121" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="11" fill={node.platform ? 'rgba(255,248,238,0.7)' : 'rgba(31,20,16,0.55)'}>{node.detail}</text>
      </g>
    ))}
    <text x="450" y="188" textAnchor="middle" fontFamily="Instrument Sans, sans-serif" fontSize="12" fill="rgba(31,20,16,0.62)">
      Every Runtime invocation terminates; PostgreSQL carries continuity between requests.
    </text>
    <line x1="10" y1="211" x2="876" y2="211" stroke="rgba(31,20,16,0.2)" strokeWidth="1" />
    <text x="443" y="230" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="rgba(31,20,16,0.55)" letterSpacing="2">TIME</text>
  </svg>
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

export default RuntimeDetail;
