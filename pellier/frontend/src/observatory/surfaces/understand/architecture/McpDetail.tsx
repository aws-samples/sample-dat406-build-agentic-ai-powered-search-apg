/**
 * McpDetail — Architecture detail page for the MCP Gateway concept.
 *
 * Model Context Protocol gateway — required governed tool rail.
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

const McpDetail: React.FC = () => {
  const { data, loading, error, refetch } = useObservatoryData<ArchitectureConcept[]>({
    key: 'architecture',
  });

  const concept = data?.find((c) => c.slug === 'mcp');

  return (
    <DetailPageShell
      numeral="VIII"
      conceptName="MCP Gateway"
      category="workshop"
      title="Gateway, governed."
      prose="AgentCore Gateway publishes Pellier's complete 15-tool contract over MCP. Governed Runtime requests require this rail, forward the caller JWT, and fail closed when Gateway is unavailable. The separate builders format retains in-process Strands tools."
      cheatSheet={[
        {
          numeral: 'i.',
          text: 'The governed agent asks Gateway for the complete tool catalog – names, signatures, and descriptions. This is MCP discovery.',
        },
        {
          numeral: 'ii.',
          text: 'The governed agent calls tools by name through Gateway, where the caller JWT and Cedar decision stay attached to the managed boundary.',
        },
        {
          numeral: 'iii.',
          text: 'Gateway is mandatory for the governed format. Only the separate builders format uses the in-process dispatcher without this managed boundary.',
        },
      ]}
      liveState={{
        label: 'Current MCP Gateway state. Shows the required governed rail and its separate builders fallback.',
        values: [
          { label: 'Governed path', value: 'Required' },
          { label: 'Tool contract', value: '15 tools' },
          { label: 'Protocol', value: 'MCP' },
        ],
      }}
    >
      {loading && <DetailLoadingState />}
      {error && <DetailErrorState message={error} onRetry={refetch} />}
      {!loading && !error && !concept && <DetailEmptyState conceptName="MCP Gateway" />}
      {!loading && !error && concept && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Network diagram card */}
          <ExpCard>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <ConceptEyebrow label="The network" />
              <h3 style={sectionTitleStyle}>Three nodes, one governed rail.</h3>
              <p style={sectionProseStyle}>
                Governed Runtime asks what is available, receives the 15-tool MCP catalog, and
                invokes tools through the managed Gateway and Cedar boundary. The builders format
                keeps its smaller in-process path separate.
              </p>
              <McpNetworkDiagram />
            </div>
          </ExpCard>

          {/* Node descriptions */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
            <NodeCard
              nodeKey="A"
              name="The Agent"
              tag="Governed Runtime"
              description="Strands agent running in managed Runtime. Requires AGENTCORE_GATEWAY_URL and fails closed when the rail is unavailable."
            />
            <NodeCard
              nodeKey="B"
              name="The Gateway"
              tag="Required infra"
              description="AgentCore Gateway publishes all 15 tools as MCP and applies the managed identity and Cedar boundary."
            />
            <NodeCard
              nodeKey="C"
              name="The Tools"
              tag="Live tools"
              description="The same @tool-decorated functions the in-process dispatcher can call directly."
            />
          </div>

          {/* Code snippet */}
          <ExpCard>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <ConceptEyebrow label="Code" />
              <pre style={codeBlockStyle}>{concept.codeSnippet}</pre>
            </div>
          </ExpCard>
        </div>
      )}
    </DetailPageShell>
  );
};

/* ---- Sub-components ---- */

const NodeCard: React.FC<{
  nodeKey: string;
  name: string;
  tag: string;
  description: string;
}> = ({ nodeKey, name, tag, description }) => (
  <ExpCard>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            fontFamily: 'var(--obs-mono)',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--obs-red-1)',
            width: '20px',
            height: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
            backgroundColor: 'var(--obs-red-soft)',
          }}
        >
          {nodeKey}
        </span>
        <span style={{ fontFamily: 'var(--obs-heading)', fontSize: '14px', color: 'var(--obs-ink-1)' }}>
          {name}
        </span>
      </div>
      <span
        style={{
          fontFamily: 'var(--obs-mono)',
          fontSize: '9px',
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: 'var(--obs-ink-4)',
        }}
      >
        {tag}
      </span>
      <p style={{ fontFamily: 'var(--obs-sans)', fontSize: '14px', lineHeight: 1.5, color: 'var(--obs-ink-1)', margin: 0 }}>
        {description}
      </p>
    </div>
  </ExpCard>
);

const McpNetworkDiagram: React.FC = () => (
  <svg viewBox="0 0 480 320" width="100%" style={{ maxWidth: '480px', display: 'block', margin: '0 auto' }}>
    {/* Edges */}
    <line x1="240" y1="90" x2="120" y2="210" stroke="rgba(168,66,58,0.55)" strokeWidth="1.5" />
    <line x1="240" y1="90" x2="360" y2="210" stroke="rgba(168,66,58,0.55)" strokeWidth="1.5" />
    <line x1="120" y1="250" x2="360" y2="250" stroke="rgba(31,20,16,0.18)" strokeWidth="1" strokeDasharray="4,4" />

    {/* Edge labels */}
    <rect x="125" y="135" width="80" height="20" rx="10" fill="var(--cream-warm)" stroke="rgba(168,66,58,0.4)" strokeWidth="1" />
    <text x="165" y="149" textAnchor="middle" fontFamily="Fraunces, serif" fontStyle="italic" fontSize="11" fill="#a8423a">discovers</text>
    <rect x="280" y="135" width="68" height="20" rx="10" fill="var(--cream-warm)" stroke="rgba(168,66,58,0.4)" strokeWidth="1" />
    <text x="314" y="149" textAnchor="middle" fontFamily="Fraunces, serif" fontStyle="italic" fontSize="11" fill="#a8423a">invokes</text>

    {/* Agent (top) */}
    <rect x="180" y="50" width="120" height="55" rx="10" fill="#1f1410" />
    <text x="240" y="78" textAnchor="middle" fontFamily="Fraunces, serif" fontStyle="italic" fontSize="18" fill="var(--cream-warm)">agent</text>
    <text x="240" y="94" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="rgba(250,243,232,0.55)" letterSpacing="1.5">gateway-aware agent</text>

    {/* Gateway (bottom-left) */}
    <rect x="55" y="210" width="130" height="70" rx="10" fill="var(--cream-warm)" stroke="var(--accent)" strokeWidth="1.5" />
    <text x="120" y="240" textAnchor="middle" fontFamily="Fraunces, serif" fontStyle="italic" fontSize="18" fill="#a8423a">gateway</text>
    <text x="120" y="258" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="rgba(31,20,16,0.42)" letterSpacing="1.5">AGENTCORE</text>

    {/* Tools (bottom-right) */}
    <rect x="295" y="210" width="130" height="70" rx="10" fill="var(--cream-warm)" stroke="rgba(31,29,26,0.30)" strokeWidth="1" />
    <text x="360" y="240" textAnchor="middle" fontFamily="Fraunces, serif" fontStyle="italic" fontSize="18" fill="#1f1410">tools</text>
    <text x="360" y="258" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="rgba(31,20,16,0.42)" letterSpacing="1.5">REGISTERED</text>

    {/* Protocol label */}
    <text x="240" y="300" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="rgba(31,20,16,0.42)" letterSpacing="2">PROTOCOL · MCP</text>
  </svg>
);

/* ---- Shared styles ---- */

const ConceptEyebrow: React.FC<{ label: string }> = ({ label }) => (
  <span
    style={{
      fontFamily: 'var(--obs-mono)',
      fontSize: '9px',
      letterSpacing: '0.22em',
      textTransform: 'uppercase',
      color: 'var(--obs-ink-4)',
      fontWeight: 500,
    }}
  >
    {label}
  </span>
);

const sectionTitleStyle: React.CSSProperties = {
  fontFamily: 'var(--obs-heading)',
  fontSize: '22px',
  fontWeight: 400,
  lineHeight: 1.15,
  color: 'var(--obs-ink-1)',
  margin: 0,
};

const sectionProseStyle: React.CSSProperties = {
  fontFamily: 'var(--obs-sans)',
  fontSize: 'var(--obs-body-size)',
  lineHeight: 'var(--obs-body-leading)',
  color: 'var(--obs-ink-1)',
  margin: 0,
  maxWidth: '560px',
};

const codeBlockStyle: React.CSSProperties = {
  ...ARCHITECTURE_CODE_BLOCK,
  whiteSpace: 'pre',
};

export default McpDetail;
