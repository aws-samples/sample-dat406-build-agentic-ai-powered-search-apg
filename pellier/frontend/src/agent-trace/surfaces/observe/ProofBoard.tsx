/**
 * ProofBoard - system evidence surface.
 *
 * One route that maps the hands-on flow to concrete evidence:
 * readiness checks, evidence cards, and terminal fallbacks.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { EditorialTitle, Eyebrow } from '../../components';

type CheckState = 'pass' | 'warn' | 'fail';
type CardStatus = 'complete' | 'needs_build' | 'needs_run' | 'needs_data' | 'needs_config' | 'pending' | 'available';
type TraceStepState = 'pass' | 'warn' | 'pending';

interface ReadinessCheck {
  id: string;
  label: string;
  state: CheckState;
  detail: string;
  required: boolean;
  href?: string;
}

interface ManagedReceipt {
  present: boolean;
  traceKind: string;
  runtime: string;
  rail: string;
  jwtPassthrough: boolean;
  gatewayPassthrough: boolean;
  policyConfigured?: boolean;
  gatewayAuditPresent?: boolean;
  latestGatewayAuditId?: number | null;
  latestGatewayAuditAt?: string;
}

interface ProofCard {
  id: string;
  group: string;
  title: string;
  status: CardStatus;
  required: boolean;
  surface: string;
  summary: string;
  evidenceSource?: string;
  lastUpdated?: string | null;
  evidence: string[];
  fallback: {
    label: string;
    command: string;
  };
  links: Array<{ label: string; to: string }>;
}

interface ProofBoardPayload {
  status: 'ready' | 'attention' | 'not_ready';
  readiness: {
    status: 'ready' | 'attention' | 'not_ready';
    checks: ReadinessCheck[];
  };
  managedReceipt: ManagedReceipt;
  cards: ProofCard[];
}

const STATUS_LABEL: Record<CardStatus, string> = {
  complete: 'Complete',
  needs_build: 'Build',
  needs_run: 'Run',
  needs_data: 'Data',
  needs_config: 'Config',
  pending: 'Pending',
  available: 'Available',
};

const STATUS_TONE: Record<CardStatus, { color: string; bg: string }> = {
  complete: { color: 'var(--at-green-1)', bg: 'rgba(73, 116, 88, 0.12)' },
  needs_build: { color: 'var(--at-red-1)', bg: 'rgba(168, 66, 58, 0.12)' },
  needs_run: { color: 'var(--at-red-1)', bg: 'rgba(168, 66, 58, 0.12)' },
  needs_data: { color: '#7c5b18', bg: 'rgba(184, 138, 58, 0.14)' },
  needs_config: { color: '#7c5b18', bg: 'rgba(184, 138, 58, 0.14)' },
  pending: { color: 'var(--at-ink-3)', bg: 'rgba(31, 20, 16, 0.06)' },
  available: { color: 'var(--at-ink-2)', bg: 'rgba(31, 20, 16, 0.06)' },
};

const CHECK_TONE: Record<CheckState, { label: string; color: string; bg: string }> = {
  pass: { label: 'Pass', color: 'var(--at-green-1)', bg: 'rgba(73, 116, 88, 0.12)' },
  warn: { label: 'Warn', color: '#7c5b18', bg: 'rgba(184, 138, 58, 0.14)' },
  fail: { label: 'Fix', color: 'var(--at-red-1)', bg: 'rgba(168, 66, 58, 0.12)' },
};

const TRACE_TONE: Record<TraceStepState, { label: string; color: string; bg: string; border: string }> = {
  pass: {
    label: 'Seen',
    color: 'var(--at-green-1)',
    bg: 'rgba(73, 116, 88, 0.12)',
    border: 'rgba(73, 116, 88, 0.28)',
  },
  warn: {
    label: 'Gap',
    color: '#7c5b18',
    bg: 'rgba(184, 138, 58, 0.14)',
    border: 'rgba(184, 138, 58, 0.32)',
  },
  pending: {
    label: 'Pending',
    color: 'var(--at-ink-3)',
    bg: 'rgba(31, 20, 16, 0.05)',
    border: 'var(--at-card-border)',
  },
};

const CODE_STYLE: React.CSSProperties = {
  margin: 0,
  padding: '12px 14px',
  borderRadius: '8px',
  background: 'var(--dl-ink)',
  color: 'var(--dl-accent-soft)',
  border: '1px solid color-mix(in srgb, var(--dl-accent-soft) 18%, transparent)',
  fontFamily: 'var(--at-mono)',
  fontSize: '12px',
  lineHeight: 1.55,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

function formatTimestamp(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

function statusPill(status: CardStatus) {
  const tone = STATUS_TONE[status];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: '999px',
        padding: '4px 9px',
        color: tone.color,
        background: tone.bg,
        fontFamily: 'var(--at-mono)',
        fontSize: '10px',
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

const CheckPill: React.FC<{ state: CheckState }> = ({ state }) => {
  const tone = CHECK_TONE[state];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: '999px',
        padding: '3px 8px',
        color: tone.color,
        background: tone.bg,
        fontFamily: 'var(--at-mono)',
        fontSize: '10px',
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
      }}
    >
      {tone.label}
    </span>
  );
};

const ReadinessPanel: React.FC<{ checks: ReadinessCheck[] }> = ({ checks }) => {
  return (
    <section aria-label="Environment readiness" style={{ marginBottom: '32px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          marginBottom: '14px',
        }}
      >
        <Eyebrow label="Readiness panel" />
        <span
          className="font-mono"
          style={{
            fontSize: '11px',
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            color: 'var(--at-ink-3)',
          }}
        >
          No service calls from this view
        </span>
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '12px',
        }}
      >
        {checks.map((check) => (
          <div
            key={check.id}
            style={{
              border: '1px solid var(--at-card-border)',
              borderRadius: '8px',
              background: 'var(--at-card-bg)',
              padding: '14px 16px',
              minHeight: '126px',
              display: 'flex',
              flexDirection: 'column',
              gap: '9px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <CheckPill state={check.state} />
              <span
                className="font-mono"
                style={{
                  fontSize: '10px',
                  letterSpacing: '0.12em',
                  textTransform: 'uppercase',
                  color: 'var(--at-ink-3)',
                }}
              >
                {check.required ? 'Baseline' : 'Managed'}
              </span>
            </div>
            <h3
              style={{
                margin: 0,
                color: 'var(--at-ink-1)',
                fontFamily: 'var(--at-serif)',
                fontSize: '20px',
                fontWeight: 400,
              }}
            >
              {check.label}
            </h3>
            <p
              style={{
                margin: 0,
                color: 'var(--at-ink-2)',
                fontFamily: 'var(--at-sans)',
                fontSize: '13px',
                lineHeight: 1.5,
              }}
            >
              {check.detail}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
};

const TraceStep: React.FC<{ label: string; detail: string; state: TraceStepState }> = ({
  label,
  detail,
  state,
}) => {
  const tone = TRACE_TONE[state];
  return (
    <div
      style={{
        border: `1px solid ${tone.border}`,
        borderRadius: '8px',
        background: tone.bg,
        minHeight: '96px',
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}
    >
      <div
        className="font-mono"
        style={{
          color: tone.color,
          fontSize: '10px',
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          marginBottom: '8px',
        }}
      >
        {tone.label}
      </div>
      <div
        style={{
          color: 'var(--at-ink-1)',
          fontFamily: 'var(--at-sans)',
          fontSize: '14px',
          fontWeight: 650,
          lineHeight: 1.25,
          marginBottom: '6px',
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: 'var(--at-ink-2)',
          fontFamily: 'var(--at-sans)',
          fontSize: '12px',
          lineHeight: 1.35,
        }}
      >
        {detail}
      </div>
    </div>
  );
};

const ReceiptStrip: React.FC<{ receipt: ManagedReceipt }> = ({ receipt }) => {
  const gatewayAuditAt = formatTimestamp(receipt.latestGatewayAuditAt);
  const traceSteps: Array<{ label: string; detail: string; state: TraceStepState }> = [
    {
      label: 'Cognito user',
      detail: receipt.jwtPassthrough ? 'Caller JWT forwarded' : 'Signed-in JWT not observed',
      state: receipt.jwtPassthrough ? 'pass' : 'pending',
    },
    {
      label: 'Runtime',
      detail: receipt.present ? receipt.runtime || 'Managed receipt present' : 'No managed receipt',
      state: receipt.present ? 'pass' : 'pending',
    },
    {
      label: 'Gateway',
      detail: receipt.gatewayPassthrough ? receipt.rail || 'Gateway MCP rail' : 'Gateway hop not observed',
      state: receipt.gatewayPassthrough ? 'pass' : 'pending',
    },
    {
      label: 'Cedar decision',
      detail: receipt.policyConfigured ? 'Policy engine configured' : 'Policy engine id missing',
      state: receipt.policyConfigured ? (receipt.present ? 'pass' : 'pending') : 'warn',
    },
    {
      label: 'Tool result',
      detail: receipt.gatewayAuditPresent ? `Gateway audit ${receipt.latestGatewayAuditId}` : 'No Gateway ALLOW row',
      state: receipt.gatewayAuditPresent ? 'pass' : receipt.present ? 'warn' : 'pending',
    },
    {
      label: 'Aurora audit',
      detail: gatewayAuditAt ? `tool_audit at ${gatewayAuditAt}` : 'DENY leaves no tool_audit row',
      state: receipt.gatewayAuditPresent ? 'pass' : receipt.present ? 'warn' : 'pending',
    },
  ];

  return (
    <section
      aria-label="Gateway JWT trace receipt"
      style={{
        border: '1px solid var(--at-card-border)',
        borderRadius: '8px',
        background: 'var(--at-cream-2)',
        padding: '18px 20px',
        marginBottom: '30px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: '14px',
          flexWrap: 'wrap',
          marginBottom: '14px',
        }}
      >
        <Eyebrow label="Gateway/JWT trace receipt" />
        <span
          className="font-mono"
          style={{
            color: 'var(--at-ink-3)',
            fontSize: '11px',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}
        >
          {receipt.present ? receipt.traceKind || 'managed receipt' : 'managed rail pending'}
        </span>
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '10px',
        }}
      >
        {traceSteps.map((step) => (
          <TraceStep key={step.label} {...step} />
        ))}
      </div>
    </section>
  );
};

const ProofCardView: React.FC<{ card: ProofCard; highlighted?: boolean }> = ({
  card,
  highlighted = false,
}) => {
  const lastUpdated = formatTimestamp(card.lastUpdated);
  return (
  <article
    id={card.id}
    data-testid={`proof-card-${card.id}`}
    style={{
      border: highlighted ? '1px solid var(--at-red-1)' : '1px solid var(--at-card-border)',
      borderRadius: '8px',
      background: highlighted ? 'color-mix(in srgb, var(--at-card-bg) 86%, var(--at-red-1) 14%)' : 'var(--at-card-bg)',
      padding: '22px 24px',
      scrollMarginTop: '80px',
      boxShadow: highlighted
        ? '0 0 0 3px rgba(168, 66, 58, 0.12), 0 2px 10px rgba(45, 24, 16, 0.04)'
        : '0 2px 10px rgba(45, 24, 16, 0.04)',
    }}
  >
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        flexWrap: 'wrap',
        marginBottom: '12px',
      }}
    >
      <span
        className="font-mono"
        style={{
          fontSize: '11px',
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: 'var(--at-red-1)',
        }}
      >
        {card.group}
      </span>
      {statusPill(card.status)}
      <span
        className="font-mono"
        style={{
          fontSize: '10px',
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: 'var(--at-ink-3)',
        }}
      >
        {card.required ? 'Core evidence' : 'Extended evidence'}
      </span>
    </div>
    <h2
      style={{
        margin: '0 0 6px',
        color: 'var(--at-ink-1)',
        fontFamily: 'var(--at-serif)',
        fontSize: '26px',
        lineHeight: 1.15,
        fontWeight: 400,
      }}
    >
      {card.title}
    </h2>
    <p
      className="font-mono"
      style={{
        margin: '0 0 12px',
        color: 'var(--at-ink-3)',
        fontSize: '11px',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}
    >
      {card.surface}
    </p>
    <p
      style={{
        margin: '0 0 16px',
        color: 'var(--at-ink-2)',
        fontFamily: 'var(--at-sans)',
        fontSize: '14px',
        lineHeight: 1.55,
      }}
    >
      {card.summary}
    </p>
    {(card.evidenceSource || lastUpdated) && (
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '8px',
          margin: '0 0 14px',
        }}
      >
        {card.evidenceSource && (
          <div>
            <div
              className="font-mono"
              style={{
                color: 'var(--at-ink-3)',
                fontSize: '9.5px',
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                marginBottom: '4px',
              }}
            >
              Evidence source
            </div>
            <div
              style={{
                color: 'var(--at-ink-2)',
                fontFamily: 'var(--at-mono)',
                fontSize: '11.5px',
                lineHeight: 1.45,
                wordBreak: 'break-word',
              }}
            >
              {card.evidenceSource}
            </div>
          </div>
        )}
        {lastUpdated && (
          <div>
            <div
              className="font-mono"
              style={{
                color: 'var(--at-ink-3)',
                fontSize: '9.5px',
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                marginBottom: '4px',
              }}
            >
              Last updated
            </div>
            <div
              style={{
                color: 'var(--at-ink-2)',
                fontFamily: 'var(--at-mono)',
                fontSize: '11.5px',
                lineHeight: 1.45,
              }}
            >
              {lastUpdated}
            </div>
          </div>
        )}
      </div>
    )}
    <ul
      style={{
        margin: '0 0 16px',
        paddingLeft: '18px',
        color: 'var(--at-ink-2)',
        fontFamily: 'var(--at-sans)',
        fontSize: '13.5px',
        lineHeight: 1.55,
      }}
    >
      {card.evidence.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
    <div style={{ marginBottom: '16px' }}>
      <div
        className="font-mono"
        style={{
          fontSize: '10px',
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: 'var(--at-ink-3)',
          marginBottom: '7px',
        }}
      >
        {card.fallback.label}
      </div>
      <pre style={CODE_STYLE}>{card.fallback.command}</pre>
    </div>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
      {card.links.map((link) => (
        <Link
          key={`${card.id}-${link.to}`}
          to={link.to}
          style={{
            color: 'var(--at-red-1)',
            border: '1px solid var(--at-card-border)',
            borderRadius: '999px',
            padding: '5px 10px',
            textDecoration: 'none',
            fontFamily: 'var(--at-mono)',
            fontSize: '12px',
          }}
        >
          {link.label}
        </Link>
      ))}
    </div>
  </article>
  );
};

function groupCards(cards: ProofCard[]) {
  const groups = new Map<string, ProofCard[]>();
  for (const card of cards) {
    const items = groups.get(card.group) ?? [];
    items.push(card);
    groups.set(card.group, items);
  }
  return Array.from(groups.entries());
}

const ProofRail: React.FC<{
  eyebrow: string;
  title: string;
  summary: string;
  cards: ProofCard[];
  activeAnchor: string;
}> = ({ eyebrow, title, summary, cards, activeAnchor }) => {
  if (!cards.length) return null;
  const groupedCards = groupCards(cards);
  return (
    <section aria-label={title} style={{ marginBottom: '36px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '14px',
          flexWrap: 'wrap',
          marginBottom: '10px',
        }}
      >
        <div>
          <Eyebrow label={eyebrow} />
          <h2
            style={{
              margin: '6px 0 0',
              color: 'var(--at-ink-1)',
              fontFamily: 'var(--at-serif)',
              fontSize: '24px',
              fontWeight: 400,
              lineHeight: 1.15,
            }}
          >
            {title}
          </h2>
        </div>
        <span
          className="font-mono"
          style={{
            color: 'var(--at-ink-3)',
            fontSize: '11px',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}
        >
          {cards.length} cards
        </span>
      </div>
      <p
        style={{
          color: 'var(--at-ink-2)',
          fontFamily: 'var(--at-sans)',
          fontSize: '14px',
          lineHeight: 1.55,
          margin: '0 0 16px',
          maxWidth: '760px',
        }}
      >
        {summary}
      </p>
      {groupedCards.map(([group, groupCards]) => (
        <div key={group} style={{ marginBottom: '20px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginBottom: '12px',
            }}
          >
            <Eyebrow label={group} />
            <span
              className="font-mono"
              style={{
                color: 'var(--at-ink-3)',
                fontSize: '11px',
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
              }}
            >
              {groupCards.length} cards
            </span>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
              gap: '16px',
            }}
          >
            {groupCards.map((card) => (
              <ProofCardView
                key={card.id}
                card={card}
                highlighted={activeAnchor === card.id}
              />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
};

const ProofBoard: React.FC = () => {
  const location = useLocation();
  const [data, setData] = useState<ProofBoardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetch('/api/agent-trace/proof-board')
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((json: ProofBoardPayload) => {
        if (active) {
          setData(json);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const activeAnchor = useMemo(() => {
    if (!location.hash) return '';
    return decodeURIComponent(location.hash.replace(/^#/, ''));
  }, [location.hash]);

  const rails = useMemo(() => {
    const cards = data?.cards ?? [];
    return {
      required: cards.filter((card) => card.required),
      optional: cards.filter((card) => !card.required),
    };
  }, [data]);

  return (
    <div style={{ padding: '40px 48px', maxWidth: '1180px' }}>
      <EditorialTitle
        eyebrow="Evidence · proof board"
        title="Inspect evidence, then boundaries."
        summary="Each card connects a system claim to live evidence and keeps a terminal fallback beside the visual proof."
      />

      {loading && (
        <p className="font-mono" style={{ color: 'var(--at-ink-3)' }}>
          Loading proof board...
        </p>
      )}
      {error && (
        <div
          role="alert"
          style={{
            border: '1px solid rgba(168, 66, 58, 0.35)',
            background: 'rgba(168, 66, 58, 0.08)',
            borderRadius: '8px',
            padding: '14px 16px',
            color: 'var(--at-red-1)',
            fontFamily: 'var(--at-sans)',
            marginBottom: '24px',
          }}
        >
          Proof board API unavailable: {error}
        </div>
      )}

      {data && (
        <>
          <ReadinessPanel checks={data.readiness.checks} />
          <ReceiptStrip receipt={data.managedReceipt} />

          <ProofRail
            eyebrow="Core evidence"
            title="Application evidence"
            summary="These cards cover the application, retrieval, and operational evidence available on the default execution path."
            cards={rails.required}
            activeAnchor={activeAnchor}
          />
          <ProofRail
            eyebrow="Extended evidence"
            title="Managed boundaries"
            summary="These cards become live when the environment has Runtime, Gateway, identity, and Policy configured."
            cards={rails.optional}
            activeAnchor={activeAnchor}
          />
        </>
      )}
    </div>
  );
};

export default ProofBoard;
