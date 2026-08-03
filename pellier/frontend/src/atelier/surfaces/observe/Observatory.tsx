/**
 * Observatory - workshop map and Atelier reference.
 *
 * The page mirrors Workshop Studio's five required labs so participants never
 * have to translate between two workshop taxonomies.
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

type LabItem = {
  lab: string;
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
    verb: 'Verify',
    title: 'Proof Board',
    description:
      'Read live evidence checkpoints in the same order as the five required labs, with a terminal or SQL fallback on every card.',
  },
  {
    verb: 'Inspect',
    title: 'Tools, retrieval, memory, policy',
    description:
      'Open one focused view when the lab calls for it, then return to Boutique or Code Editor for the canonical proof.',
  },
  {
    verb: 'Explore',
    title: 'Extension labs',
    description:
      'Agent Behavior & Routing, Retrieval Engineering, and Defense in Depth begin only after their named checkpoint.',
  },
];

const LABS: LabItem[] = [
  {
    lab: 'Lab 1',
    title: 'Build a Specialist Agent',
    summary:
      "Complete Stock Keeper and floor_check, then prove Marco's warehouse turn against live Aurora inventory and tool_audit.",
    primary: {
      to: '/atelier/proof-board#marco-floor-check',
      label: 'Open floor_check proof',
      detail: 'Lab 1 checkpoint',
      testId: 'observatory-cta-proof-board',
    },
    secondary: [
      {
        to: '/atelier/tools',
        label: 'Tool Registry',
        detail: 'Before-and-after visual',
      },
    ],
  },
  {
    lab: 'Lab 2',
    title: 'Measure Hybrid Search',
    summary:
      "Compare Anna's vector, hybrid, hybrid plus rerank, and agentic paths, then defend one choice with quality, latency, and cost.",
    primary: {
      to: '/atelier/performance',
      label: 'Open retrieval comparison',
      detail: 'Atelier visual',
    },
    secondary: [
      {
        to: '/atelier/proof-board#retrieval-comparison',
        label: 'Retrieval checkpoint',
        detail: 'Lab 2 proof card',
      },
      {
        to: '/atelier/search',
        label: 'Search Pipeline',
        detail: 'Mechanism read',
      },
    ],
  },
  {
    lab: 'Lab 3',
    title: 'Prove AgentCore Memory',
    summary:
      "Send two authenticated turns and prove turn two receives turn-one context through AgentCore Memory, managed Runtime, and Gateway.",
    primary: {
      to: '/atelier/memory',
      label: 'Open Memory',
      detail: 'Managed memory read',
    },
    secondary: [
      {
        to: '/atelier/proof-board#managed-rail',
        label: 'Managed Runtime & Gateway',
        detail: 'Lab 3 proof card',
      },
    ],
  },
  {
    lab: 'Lab 4',
    title: 'Audit Agent Actions',
    summary:
      "Trigger Theo's return, query tool_audit, and reconstruct the seeded principal-versus-customer mismatch from governed_receipts.",
    primary: {
      to: '/atelier/audit-proof',
      label: 'Open audit proof',
      detail: 'SQL remains canonical',
    },
    secondary: [
      {
        to: '/atelier/proof-board#audit-ledger',
        label: 'Audit checkpoint',
        detail: 'Lab 4 proof card',
      },
    ],
  },
  {
    lab: 'Lab 5',
    title: 'Enforce Cedar Policy',
    summary:
      'Apply one Cedar rule, prove DENY leaves a receipt but no execution row, confirm ALLOW still executes, and reset the participant policy.',
    primary: {
      to: '/atelier/write-path',
      label: 'Open Gateway & Policy',
      detail: 'Atelier visual',
    },
    secondary: [
      {
        to: '/atelier/proof-board#runtime-gateway-policy',
        label: 'Policy checkpoint',
        detail: 'Lab 5 proof card',
      },
      {
        to: '/atelier/proof-board#managed-rail',
        label: 'Governed receipt',
        detail: 'Runtime, Gateway, and JWT',
      },
    ],
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

const ActionLink: React.FC<LinkItem & { primary?: boolean }> = ({
  to,
  label,
  detail,
  testId,
  primary = false,
}) => (
  <Link
    to={to}
    data-testid={testId}
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '12px',
      padding: primary ? '12px 0 13px' : '10px 0',
      color: 'inherit',
      textDecoration: 'none',
      borderTop: primary ? '1px solid var(--at-rule-1)' : 'none',
      borderBottom: '1px solid var(--at-rule-1)',
    }}
  >
    <span style={{ display: 'flex', flexDirection: 'column', gap: '3px', minWidth: 0 }}>
      <span
        className="font-sans"
        style={{
          color: primary ? 'var(--at-red-1)' : 'var(--at-ink-1)',
          fontSize: primary ? '15px' : '14px',
          fontWeight: 600,
          lineHeight: 1.25,
        }}
      >
        {label}
      </span>
      <span
        className="font-mono"
        style={{
          color: 'var(--at-ink-3)',
          fontSize: '10.5px',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          lineHeight: 1.35,
        }}
      >
        {detail}
      </span>
    </span>
    <ArrowRight
      aria-hidden="true"
      size={16}
      strokeWidth={2}
      style={{ color: 'var(--at-red-1)', flexShrink: 0 }}
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

const LabCard: React.FC<LabItem> = ({ lab, title, summary, primary, secondary }) => (
  <article
    style={{
      ...cardStyle,
      padding: '22px',
      display: 'grid',
      gap: '18px',
    }}
  >
    <div>
      <SectionEyebrow>{lab}</SectionEyebrow>
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

    <ActionLink {...primary} primary />

    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        columnGap: '18px',
      }}
    >
      {secondary.map((item) => (
        <ActionLink key={`${lab}-${item.to}-${item.label}`} {...item} />
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
          padding: '8px 0 4px',
          marginBottom: '34px',
        }}
      >
        <SectionEyebrow>Observatory</SectionEyebrow>
        <h1
          id="observatory-title"
          className="font-display italic text-espresso"
          style={{
            fontSize: '48px',
            fontWeight: 400,
            lineHeight: 1.05,
            letterSpacing: 0,
            margin: '16px 0 14px',
            maxWidth: '820px',
          }}
        >
          The workshop, in one view.
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
          Boutique and Code Editor remain the primary work surfaces. Atelier is
          the evidence layer: open the checkpoint named by the current lab,
          inspect it, then return to the required path.
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
          Start with the required path.
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
          The labels and order below match Workshop Studio exactly. Each card
          points to the narrow Atelier view for that lab; terminal and SQL
          commands remain the canonical proof.
        </p>
        <div style={{ display: 'grid', gap: '16px' }}>
          {LABS.map((item) => (
            <LabCard key={item.lab} {...item} />
          ))}
        </div>
      </section>

    </div>
  );
};

export default Observatory;
