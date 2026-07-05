/**
 * Observatory — first stop inside Atelier.
 *
 * The page introduces why the Atelier exists, then narrows participants into
 * Act I, Act II, and Act III.
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
      'Five specialists, 15 tools, five skills, and the memory surfaces that explain what persisted.',
  },
  {
    verb: 'Evaluate',
    title: 'Proof Board & Routing',
    description:
      'Required proof cards first, then the routing read when the lab asks for it.',
  },
];

const ACTS: ActItem[] = [
  {
    act: 'Act I',
    title: 'Build Marco, then prove it.',
    summary:
      "Complete Stock Keeper, wire floor_check, shape Marco's skill, and compare Anna's retrieval path.",
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
        to: '/atelier/skills',
        label: 'Skills',
        detail: 'Persona playbooks',
      },
      {
        to: '/atelier/search',
        label: 'Search',
        detail: 'Retrieval comparison',
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
    title: 'Prove memory and the ledger.',
    summary:
      "Read Marco's session timeline, then prove Theo's return from Aurora tool_audit rows.",
    primary: {
      to: '/atelier/proof-board#audit-ledger',
      label: 'Open audit proof',
      detail: 'Required SQL checkpoint',
    },
    secondary: [
      {
        to: '/atelier/memory',
        label: 'Memory',
        detail: 'Working-memory readback',
      },
      {
        to: '/atelier/proof-board#retrieval-comparison',
        label: 'Retrieval proof',
        detail: 'Anna comparison checkpoint',
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
    title: 'Place the managed boundary.',
    summary:
      'Read routing, MCP, Gateway, and Policy after the required SQL proof is complete.',
    primary: {
      to: '/atelier/routing',
      label: 'Open routing',
      detail: 'Dispatcher checkpoint',
    },
    secondary: [
      {
        to: '/atelier/proof-board#runtime-gateway-policy',
        label: 'Governed trace',
        detail: 'Runtime/Gateway/Policy read',
      },
      {
        to: '/atelier/proof-board#managed-rail',
        label: 'Managed rail',
        detail: 'Fast-finisher comparison',
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
          fontWeight: 650,
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

    <ActionLink {...primary} primary />

    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        columnGap: '18px',
      }}
    >
      {secondary.map((item) => (
        <ActionLink key={`${act}-${item.to}-${item.label}`} {...item} />
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
            fontSize: 'clamp(44px, 6vw, 76px)',
            fontWeight: 400,
            lineHeight: 1.05,
            letterSpacing: '-0.015em',
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
          here in governed, inspectable detail.
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
          These are the three participant rails. Use them only when the lab asks
          for an Atelier check, then return to Code Editor or the Boutique.
        </p>
        <div style={{ display: 'grid', gap: '16px' }}>
          {ACTS.map((item) => (
            <ActCard key={item.act} {...item} />
          ))}
        </div>
      </section>

    </div>
  );
};

export default Observatory;
