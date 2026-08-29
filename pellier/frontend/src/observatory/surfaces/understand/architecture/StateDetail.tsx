/**
 * StateDetail — Architecture detail page for Routing & State.
 *
 * Storefront Dispatcher plus the bounded Operator Concierge graph.
 *
 * Requirements: 7.1, 7.6, 7.7
 */

import React from 'react';
import DetailPageShell from './DetailPageShell';
import { ExpCard } from '../../../components';
import { useObservatoryData } from '../../../hooks/useObservatoryData';
import type { ArchitectureConcept } from '../../../types';
import { DetailLoadingState, DetailErrorState, DetailEmptyState } from './DetailStates';
import { ARCHITECTURE_CODE_BLOCK, ARCHITECTURE_CODE_BLOCK_COMPACT } from './codeStyles';

const StateDetail: React.FC = () => {
  const { data, loading, error, refetch } = useObservatoryData<ArchitectureConcept[]>({
    key: 'architecture',
  });

  const concept = data?.find((c) => c.slug === 'state-management');

  return (
    <DetailPageShell
      numeral="IV"
      conceptName="Routing & State"
      category="live"
      title="Routing, explicit."
      prose="Pellier ships two explicit orchestration paths. The Storefront uses deterministic Dispatcher routing to one owning specialist. Operator Concierge uses a bounded Strands graph: Case Investigator, then Resolution Planner."
      cheatSheet={[
        {
          numeral: 'i.',
          text: 'Storefront state flows in one direction: triage and intent classification select one specialist, then grounded tool results shape the reply.',
        },
        {
          numeral: 'ii.',
          text: 'Operator graph state is also bounded: current evidence, untrusted handoff context, review id, action hash, node outcomes, and timings.',
        },
        {
          numeral: 'iii.',
          text: 'PostgreSQL creates the pending review before the graph runs and records the later human decision after it. The graph invocation never waits for a person.',
        },
      ]}
      liveState={{
        label: 'The two shipped orchestration paths and the durable checkpoint between requests.',
        values: [
          { label: 'Storefront', value: 'Dispatcher' },
          { label: 'Operator', value: 'Strands Graph' },
          { label: 'Human checkpoint', value: 'PostgreSQL' },
        ],
      }}
    >
      {loading && <DetailLoadingState />}
      {error && <DetailErrorState message={error} onRetry={refetch} />}
      {!loading && !error && !concept && <DetailEmptyState conceptName="Routing & State" />}
      {!loading && !error && concept && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* State flow diagram */}
          <ExpCard>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <SectionLabel label="The shipped paths" />
              <h3 style={titleStyle}>One fast route; one ordered graph.</h3>
              <p style={proseStyle}>
                Storefront turns favor one deterministic owner. Operator turns earn a
                graph because investigation and planning have separate responsibilities.
                The pending review and later human decision remain durable outside the graph.
              </p>
              <StateFlowDiagram />
            </div>
          </ExpCard>

          {/* State keys */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <StateKeyCard
              keyName="intent"
              description="Classified user intent – pricing, inventory, support, search, or recommendation."
              example='classified_intent = "search"'
            />
            <StateKeyCard
              keyName="operator_graph"
              description="Two ordered agents: Case Investigator establishes a bounded brief; Resolution Planner produces the deliverable."
              example='edge = "case-investigator -> resolution-planner"'
            />
            <StateKeyCard
              keyName="memory_context"
              description="STM/LTM context scoped by persona and session namespace."
              example="memory_context = { stm, ltm }"
            />
            <StateKeyCard
              keyName="checkpoint"
              description="The review and action hash persist in PostgreSQL. A later authenticated request records the human decision."
              example='checkpoint = "WAITING_FOR_HUMAN"'
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

const StateKeyCard: React.FC<{
  keyName: string;
  description: string;
  example: string;
}> = ({ keyName, description, example }) => (
  <ExpCard>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <span
        style={{
          fontFamily: 'var(--obs-mono)',
          fontSize: '14px',
          fontWeight: 600,
          color: 'var(--obs-ink-1)',
        }}
      >
        {keyName}
      </span>
      <p style={{ fontFamily: 'var(--obs-sans)', fontSize: '14px', lineHeight: 1.5, color: 'var(--obs-ink-1)', margin: 0 }}>
        {description}
      </p>
      <pre
        style={{
          ...ARCHITECTURE_CODE_BLOCK_COMPACT,
          whiteSpace: 'pre',
        }}
      >
        {example}
      </pre>
    </div>
  </ExpCard>
);

const StateFlowDiagram: React.FC = () => (
  <svg
    viewBox="0 0 700 270"
    width="100%"
    role="img"
    aria-label="Storefront Dispatcher and Operator Concierge Graph execution paths"
    style={{ maxWidth: '760px', display: 'block', margin: '0 auto' }}
  >
    <defs>
      <marker id="state-arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
        <polygon points="0 0, 8 3, 0 6" fill="rgba(168,66,58,0.5)" />
      </marker>
    </defs>

    <text x="20" y="24" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="rgba(31,20,16,0.5)" letterSpacing="1.6">STOREFRONT DISPATCHER</text>
    {[153, 323, 493].map((x) => (
      <line key={`store-${x}`} x1={x} y1="73" x2={x + 42} y2="73" stroke="rgba(168,66,58,0.5)" strokeWidth="1.5" markerEnd="url(#state-arrowhead)" />
    ))}
    {[
      { x: 20, label: 'shopper request', dark: true },
      { x: 190, label: 'Dispatcher' },
      { x: 360, label: 'one specialist' },
      { x: 530, label: 'grounded reply' },
    ].map((node) => (
      <g key={node.label}>
        <rect
          x={node.x}
          y="48"
          width="133"
          height="50"
          rx="8"
          fill={node.dark ? '#1f1410' : 'var(--cream-warm)'}
          stroke={node.dark ? '#1f1410' : 'rgba(31,29,26,0.3)'}
        />
        <text x={node.x + 66.5} y="78" textAnchor="middle" fontFamily="Instrument Sans, sans-serif" fontSize="12" fill={node.dark ? 'var(--cream-warm)' : '#1f1410'}>{node.label}</text>
      </g>
    ))}

    <text x="20" y="142" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="rgba(31,20,16,0.5)" letterSpacing="1.6">OPERATOR CONCIERGE GRAPH</text>
    {[153, 323, 493].map((x) => (
      <line key={`operator-${x}`} x1={x} y1="191" x2={x + 42} y2="191" stroke="rgba(168,66,58,0.5)" strokeWidth="1.5" markerEnd="url(#state-arrowhead)" />
    ))}
    {[
      { x: 20, label: 'handoff + review', dark: true },
      { x: 190, label: 'Case Investigator' },
      { x: 360, label: 'Resolution Planner' },
      { x: 530, label: 'persisted artifact' },
    ].map((node) => (
      <g key={node.label}>
        <rect
          x={node.x}
          y="166"
          width="133"
          height="50"
          rx="8"
          fill={node.dark ? '#1f1410' : 'var(--cream-warm)'}
          stroke={node.dark ? '#1f1410' : 'rgba(31,29,26,0.3)'}
        />
        <text x={node.x + 66.5} y="196" textAnchor="middle" fontFamily="Instrument Sans, sans-serif" fontSize="11.5" fill={node.dark ? 'var(--cream-warm)' : '#1f1410'}>{node.label}</text>
      </g>
    ))}
    <text x="350" y="250" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="rgba(31,20,16,0.5)" letterSpacing="1">
      HUMAN DECISION FOLLOWS IN A SEPARATE REQUEST
    </text>
  </svg>
);

/* ---- Shared styles ---- */

const SectionLabel: React.FC<{ label: string }> = ({ label }) => (
  <span style={{ fontFamily: 'var(--obs-mono)', fontSize: '9px', letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--obs-ink-4)', fontWeight: 500 }}>
    {label}
  </span>
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

export default StateDetail;
