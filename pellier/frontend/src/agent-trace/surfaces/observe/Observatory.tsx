/**
 * Observatory — first stop inside Agent Trace.
 *
 * The page introduces why the Agent Trace exists, then groups its evidence by
 * product domain before exposing the broader reference catalog.
 */

import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

type LinkItem = {
  to: string;
  label: string;
  detail: string;
  testId?: string;
};

type DomainItem = {
  group: string;
  title: string;
  summary: string;
  primary: LinkItem;
  secondary: LinkItem[];
};

type PillarItem = {
  verb: string;
  title: string;
  description: string;
};

const PILLARS: PillarItem[] = [
  {
    verb: 'Observe',
    title: 'Sessions & Observatory',
    description:
      'Replay any shopper conversation turn-by-turn. See the wide-angle dashboard for live agent state, tool activity, and memory counts.',
  },
  {
    verb: 'Understand',
    title: 'Agents, Tools, Memory',
    description:
      'Five specialists, fifteen tools, and four memory substrates. Read how each piece works and where its evidence lives.',
  },
  {
    verb: 'Evaluate',
    title: 'Performance & Routing',
    description:
      'P50 cold start, HNSW recall, router decisions, and the operational proof behind the boutique experience.',
  },
];

const DOMAINS: DomainItem[] = [
  {
    group: 'Agent and tool evidence',
    title: 'Inspect the tool path.',
    summary:
      'Connect the floor_check implementation, public tool contract, and replay evidence without assuming a particular lab sequence.',
    primary: {
      to: '/agent-trace/proof-board#marco-floor-check',
      label: 'Open floor_check evidence',
      detail: 'Source, trace, and audit checkpoint',
      testId: 'observatory-cta-proof-board',
    },
    secondary: [
      {
        to: '/agent-trace/tools',
        label: 'Tools',
        detail: 'Canonical tool registry',
      },
      {
        to: '/agent-trace/sessions',
        label: 'Sessions',
        detail: 'Signed-in conversation replay',
        testId: 'observatory-cta-sessions',
      },
    ],
  },
  {
    group: 'Retrieval and operations',
    title: 'Compare retrieval and auditability.',
    summary:
      'Compare retrieval behavior, inspect the SQL audit proof, and connect each visible answer to its database trail.',
    primary: {
      to: '/agent-trace/proof-board#retrieval-comparison',
      label: 'Open retrieval proof',
      detail: 'Live comparison checkpoint',
    },
    secondary: [
      {
        to: '/agent-trace/proof-board#audit-ledger',
        label: 'Audit ledger',
        detail: 'tool_audit SQL proof',
      },
      {
        to: '/agent-trace/search',
        label: 'Search',
        detail: 'Hybrid and vector evidence',
      },
      {
        to: '/agent-trace/write-path',
        label: 'Write-path',
        detail: 'Policy-backed audit writes',
      },
    ],
  },
  {
    group: 'Managed boundaries',
    title: 'Inspect Runtime, Gateway, and Policy.',
    summary:
      'Compare in-process agent calls with authenticated, policy-controlled Gateway invocations.',
    primary: {
      to: '/agent-trace/proof-board#runtime-gateway-policy',
      label: 'Open managed trace',
      detail: 'Runtime/Gateway/Policy proof',
    },
    secondary: [
      {
        to: '/agent-trace/proof-board#managed-rail',
        label: 'Managed rail',
        detail: 'Invocation comparison',
      },
      {
        to: '/agent-trace/routing',
        label: 'Routing',
        detail: 'Intent to specialist handoff',
      },
      {
        to: '/agent-trace/production-patterns',
        label: 'Production Patterns',
        detail: 'Operational reference',
      },
    ],
  },
];

const REFERENCE_LINKS: LinkItem[] = [
  {
    to: '/agent-trace/sessions',
    label: 'Sessions',
    detail: 'Replay shopper conversations turn by turn',
    testId: 'observatory-reference-sessions',
  },
  {
    to: '/agent-trace/persona-journeys',
    label: 'Persona Journeys',
    detail: 'Trace each shopper path through the boutique',
  },
  {
    to: '/agent-trace/architecture',
    label: 'Architecture',
    detail: 'System map and component glossary',
    testId: 'observatory-cta-architecture',
  },
  {
    to: '/agent-trace/agents',
    label: 'Agents',
    detail: 'Specialists, shipped references, and build targets',
  },
  {
    to: '/agent-trace/tools',
    label: 'Tools',
    detail: 'Tool contracts, ownership, and status',
  },
  {
    to: '/agent-trace/skills',
    label: 'Skills',
    detail: 'Persona-aware prompt context',
  },
  {
    to: '/agent-trace/search',
    label: 'Search',
    detail: 'Retrieval traces and ranking behavior',
  },
  {
    to: '/agent-trace/routing',
    label: 'Routing',
    detail: 'Intent classification and specialist dispatch',
  },
  {
    to: '/agent-trace/memory',
    label: 'Memory',
    detail: 'Short-term and long-term customer memory',
  },
  {
    to: '/agent-trace/write-path',
    label: 'Write-path',
    detail: 'Cedar policy and audit persistence',
  },
  {
    to: '/agent-trace/performance',
    label: 'Performance',
    detail: 'Latency, recall, and storage measurements',
  },
  {
    to: '/agent-trace/evaluations',
    label: 'Evaluations',
    detail: 'Quality checks and grounding measures',
  },
  {
    to: '/agent-trace/production-patterns',
    label: 'Production Patterns',
    detail: 'Managed deployment patterns and tradeoffs',
  },
];

const cardStyle: React.CSSProperties = {
  border: '1px solid var(--at-card-border)',
  borderRadius: '8px',
  background: 'var(--at-card-bg)',
  boxShadow: '0 2px 10px rgba(45, 24, 16, 0.04)',
};

const eyebrowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  fontFamily: 'var(--at-mono)',
  fontSize: '11px',
  fontWeight: 600,
  letterSpacing: '0.18em',
  lineHeight: 1,
  textTransform: 'uppercase',
  color: 'var(--at-red-1)',
};

const SectionEyebrow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={eyebrowStyle}>
    <span
      aria-hidden="true"
      style={{
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        background: 'var(--at-red-1)',
        flexShrink: 0,
      }}
    />
    {children}
  </div>
);

const LinkCard: React.FC<LinkItem & { compact?: boolean }> = ({
  to,
  label,
  detail,
  testId,
  compact = false,
}) => (
  <Link
    to={to}
    data-testid={testId}
    style={{
      ...cardStyle,
      display: 'flex',
      alignItems: compact ? 'center' : 'flex-start',
      justifyContent: 'space-between',
      gap: '14px',
      minHeight: compact ? '82px' : '104px',
      padding: compact ? '16px 18px' : '18px 20px',
      color: 'inherit',
      textDecoration: 'none',
      transition: 'border-color 160ms ease, box-shadow 160ms ease',
    }}
    onMouseEnter={(event) => {
      event.currentTarget.style.borderColor = 'var(--at-red-1)';
      event.currentTarget.style.boxShadow = '0 4px 18px rgba(45, 24, 16, 0.08)';
    }}
    onMouseLeave={(event) => {
      event.currentTarget.style.borderColor = 'var(--at-card-border)';
      event.currentTarget.style.boxShadow = '0 2px 10px rgba(45, 24, 16, 0.04)';
    }}
  >
    <span style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: 0 }}>
      <span
        className="font-display italic text-espresso"
        style={{
          fontSize: compact ? '21px' : '24px',
          lineHeight: 1.15,
          fontWeight: 400,
          letterSpacing: 0,
        }}
      >
        {label}
      </span>
      <span
        className="font-sans text-ink-soft"
        style={{
          fontSize: '13.5px',
          lineHeight: 1.45,
        }}
      >
        {detail}
      </span>
    </span>
    <ArrowRight
      aria-hidden="true"
      size={18}
      strokeWidth={2}
      style={{ color: 'var(--at-red-1)', flexShrink: 0, marginTop: compact ? 0 : '3px' }}
    />
  </Link>
);

const PillarCard: React.FC<PillarItem> = ({ verb, title, description }) => (
  <article
    style={{
      border: '1px solid var(--at-rule-1)',
      borderRadius: '8px',
      background: 'var(--at-cream-2)',
      padding: '18px 20px',
    }}
  >
    <div
      style={{
        fontFamily: 'var(--at-mono)',
        fontSize: '10.5px',
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        color: 'var(--at-red-1)',
        fontWeight: 600,
        marginBottom: '8px',
      }}
    >
      {verb}
    </div>
    <h3
      className="font-display italic text-espresso"
      style={{
        fontSize: '22px',
        fontWeight: 400,
        lineHeight: 1.2,
        letterSpacing: 0,
        margin: '0 0 8px',
      }}
    >
      {title}
    </h3>
    <p
      className="font-sans text-ink-soft"
      style={{
        fontSize: '13.5px',
        lineHeight: 1.55,
        margin: 0,
      }}
    >
      {description}
    </p>
  </article>
);

const DomainCard: React.FC<DomainItem> = ({ group, title, summary, primary, secondary }) => (
  <article
    style={{
      ...cardStyle,
      padding: '22px',
      display: 'grid',
      gap: '18px',
    }}
  >
    <div>
      <SectionEyebrow>{group}</SectionEyebrow>
      <h3
        className="font-display italic text-espresso"
        style={{
          fontSize: '30px',
          fontWeight: 400,
          lineHeight: 1.12,
          letterSpacing: 0,
          margin: '14px 0 10px',
        }}
      >
        {title}
      </h3>
      <p
        className="font-sans text-ink-soft"
        style={{
          fontSize: '15px',
          lineHeight: 1.55,
          margin: 0,
        }}
      >
        {summary}
      </p>
    </div>

    <LinkCard {...primary} />

    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '10px',
      }}
    >
      {secondary.map((item) => (
        <LinkCard key={`${group}-${item.to}-${item.label}`} {...item} compact />
      ))}
    </div>
  </article>
);

const Observatory: React.FC = () => {
  return (
    <div style={{ padding: '40px 48px', maxWidth: '1180px' }}>
      <section
        aria-labelledby="observatory-title"
        style={{
          border: '1px solid var(--at-rule-1)',
          borderRadius: '8px',
          background:
            'linear-gradient(180deg, var(--at-cream-1) 0%, var(--at-cream-2) 100%)',
          padding: '34px 36px 32px',
          marginBottom: '34px',
        }}
      >
        <SectionEyebrow>Observatory</SectionEyebrow>
        <h1
          id="observatory-title"
          className="font-display italic text-espresso"
          style={{
            fontSize: '56px',
            fontWeight: 400,
            lineHeight: 1.04,
            letterSpacing: 0,
            margin: '16px 0 14px',
            maxWidth: '820px',
          }}
        >
          The operator's side of the boutique.
        </h1>
        <p
          className="font-sans text-ink-soft"
          style={{
            fontSize: '16px',
            lineHeight: 1.6,
            margin: '0 0 26px',
            maxWidth: '760px',
          }}
        >
          The Boutique is where shoppers ask. The Agent Trace is where you watch.
          Every agent decision, tool call, memory read, and routing hop shows up
          here in editorial detail - so the magic has a paper trail.
        </p>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '14px',
          }}
        >
          {PILLARS.map((pillar) => (
            <PillarCard key={pillar.verb} {...pillar} />
          ))}
        </div>
      </section>

      <section aria-labelledby="evidence-domain-title" style={{ marginBottom: '36px' }}>
        <SectionEyebrow>Evidence domains</SectionEyebrow>
        <h2
          id="evidence-domain-title"
          className="font-display italic text-espresso"
          style={{
            fontSize: '38px',
            fontWeight: 400,
            lineHeight: 1.1,
            letterSpacing: 0,
            margin: '14px 0 8px',
          }}
        >
          Choose the system boundary.
        </h2>
        <p
          className="font-sans text-ink-soft"
          style={{
            fontSize: '15px',
            lineHeight: 1.55,
            margin: '0 0 18px',
            maxWidth: '720px',
          }}
        >
          Start from the claim you need to verify, then follow its source,
          runtime trace, or durable record.
        </p>
        <div style={{ display: 'grid', gap: '16px' }}>
          {DOMAINS.map((item) => (
            <DomainCard key={item.group} {...item} />
          ))}
        </div>
      </section>

      <section aria-labelledby="reference-title">
        <SectionEyebrow>Reference</SectionEyebrow>
        <h2
          id="reference-title"
          className="font-display italic text-espresso"
          style={{
            fontSize: '34px',
            fontWeight: 400,
            lineHeight: 1.12,
            letterSpacing: 0,
            margin: '14px 0 18px',
          }}
        >
          Explore every Agent Trace surface.
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '12px',
          }}
        >
          {REFERENCE_LINKS.map((item) => (
            <LinkCard key={`${item.to}-${item.label}`} {...item} compact />
          ))}
        </div>
      </section>
    </div>
  );
};

export default Observatory;
