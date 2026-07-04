/**
 * Observatory — first stop inside Atelier.
 *
 * The page introduces why the Atelier exists, then narrows participants into
 * Act I, Act II, Act III before exposing the broader reference catalog.
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

type ActItem = {
  act: string;
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
      'Five specialists, ten tools, two memory tiers. Read how each piece works and which are shipped reference versus yours to wire.',
  },
  {
    verb: 'Evaluate',
    title: 'Performance & Routing',
    description:
      'P50 cold start, HNSW recall, router decisions, and the operational proof behind the boutique experience.',
  },
];

const ACTS: ActItem[] = [
  {
    act: 'Act I',
    title: 'Build the governed tool path.',
    summary:
      'Wire Marco through the required floor_check checkpoint, then keep the tool definition and replay evidence close by.',
    primary: {
      to: '/atelier/proof-board#marco-floor-check',
      label: 'Open Marco floor_check',
      detail: 'Required proof checkpoint',
      testId: 'observatory-cta-proof-board',
    },
    secondary: [
      {
        to: '/atelier/tools',
        label: 'Tools',
        detail: 'Canonical tool registry',
      },
      {
        to: '/atelier/sessions',
        label: 'Sessions',
        detail: 'Signed-in conversation replay',
        testId: 'observatory-cta-sessions',
      },
    ],
  },
  {
    act: 'Act II',
    title: 'Prove retrieval and auditability.',
    summary:
      'Compare retrieval behavior, inspect the SQL audit proof, and connect each visible answer to its database trail.',
    primary: {
      to: '/atelier/proof-board#retrieval-comparison',
      label: 'Open retrieval proof',
      detail: 'Required comparison checkpoint',
    },
    secondary: [
      {
        to: '/atelier/proof-board#audit-ledger',
        label: 'Audit ledger',
        detail: 'tool_audit SQL proof',
      },
      {
        to: '/atelier/search',
        label: 'Search',
        detail: 'Hybrid and vector evidence',
      },
      {
        to: '/atelier/write-path',
        label: 'Write-path',
        detail: 'Policy-backed audit writes',
      },
    ],
  },
  {
    act: 'Act III',
    title: 'Extend through Runtime, Gateway, and Policy.',
    summary:
      'Use the managed rail after the SQL proof to compare agent calls with Gateway-governed invocations.',
    primary: {
      to: '/atelier/proof-board#runtime-gateway-policy',
      label: 'Open governed trace',
      detail: 'Runtime/Gateway/Policy proof',
    },
    secondary: [
      {
        to: '/atelier/proof-board#managed-rail',
        label: 'Managed rail',
        detail: 'Fast-finisher comparison',
      },
      {
        to: '/atelier/routing',
        label: 'Routing',
        detail: 'Intent to specialist handoff',
      },
      {
        to: '/atelier/production-patterns',
        label: 'Production Patterns',
        detail: 'Operational reference',
      },
    ],
  },
];

const REFERENCE_LINKS: LinkItem[] = [
  {
    to: '/atelier/sessions',
    label: 'Sessions',
    detail: 'Replay shopper conversations turn by turn',
    testId: 'observatory-reference-sessions',
  },
  {
    to: '/atelier/persona-journeys',
    label: 'Persona Journeys',
    detail: 'Trace each shopper path through the boutique',
  },
  {
    to: '/atelier/architecture',
    label: 'Architecture',
    detail: 'System map and component glossary',
    testId: 'observatory-cta-architecture',
  },
  {
    to: '/atelier/agents',
    label: 'Agents',
    detail: 'Specialists, shipped references, and build targets',
  },
  {
    to: '/atelier/tools',
    label: 'Tools',
    detail: 'Tool contracts, ownership, and status',
  },
  {
    to: '/atelier/skills',
    label: 'Skills',
    detail: 'Persona-aware prompt context',
  },
  {
    to: '/atelier/search',
    label: 'Search',
    detail: 'Retrieval traces and ranking behavior',
  },
  {
    to: '/atelier/routing',
    label: 'Routing',
    detail: 'Intent classification and specialist dispatch',
  },
  {
    to: '/atelier/memory',
    label: 'Memory',
    detail: 'Short-term and long-term customer memory',
  },
  {
    to: '/atelier/write-path',
    label: 'Write-path',
    detail: 'Cedar policy and audit persistence',
  },
  {
    to: '/atelier/performance',
    label: 'Performance',
    detail: 'Latency, recall, and storage measurements',
  },
  {
    to: '/atelier/evaluations',
    label: 'Evaluations',
    detail: 'Quality checks and grounding measures',
  },
  {
    to: '/atelier/production-patterns',
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

const ActCard: React.FC<ActItem> = ({ act, title, summary, primary, secondary }) => (
  <article
    style={{
      ...cardStyle,
      padding: '22px',
      display: 'grid',
      gap: '18px',
    }}
  >
    <div>
      <SectionEyebrow>{act}</SectionEyebrow>
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
        <LinkCard key={`${act}-${item.to}-${item.label}`} {...item} compact />
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
          The Boutique is where shoppers ask. The Atelier is where you watch.
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

      <section aria-labelledby="workshop-path-title" style={{ marginBottom: '36px' }}>
        <SectionEyebrow>Workshop path</SectionEyebrow>
        <h2
          id="workshop-path-title"
          className="font-display italic text-espresso"
          style={{
            fontSize: '38px',
            fontWeight: 400,
            lineHeight: 1.1,
            letterSpacing: 0,
            margin: '14px 0 8px',
          }}
        >
          Start with the acts.
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
          These are the three participant rails. The reference pages stay below
          them so the first Atelier decision is always the next workshop act.
        </p>
        <div style={{ display: 'grid', gap: '16px' }}>
          {ACTS.map((item) => (
            <ActCard key={item.act} {...item} />
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
          All other Atelier pages.
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
