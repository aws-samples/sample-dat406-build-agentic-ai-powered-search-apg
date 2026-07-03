/**
 * ProofBoard - workshop evidence surface.
 *
 * One route that maps the hands-on flow to concrete evidence:
 * readiness checks, required proof cards, and terminal fallbacks.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { EditorialTitle, Eyebrow } from '../../components';

type CheckState = 'pass' | 'warn' | 'fail';
type CardStatus = 'complete' | 'needs_build' | 'needs_run' | 'needs_data' | 'needs_config' | 'pending' | 'available';

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
}

interface ProofCard {
  id: string;
  act: string;
  title: string;
  status: CardStatus;
  required: boolean;
  surface: string;
  summary: string;
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
    <section aria-label="Workshop readiness" style={{ marginBottom: '32px' }}>
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
                {check.required ? 'Required' : 'Guided'}
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

const ReceiptStrip: React.FC<{ receipt: ManagedReceipt }> = ({ receipt }) => (
  <section
    aria-label="Gateway JWT trace receipt"
    style={{
      border: '1px solid var(--at-card-border)',
      borderRadius: '8px',
      background: 'var(--at-cream-2)',
      padding: '16px 18px',
      marginBottom: '30px',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: '14px',
    }}
  >
    {[
      ['Receipt', receipt.present ? 'Managed turn seen' : 'No managed turn yet'],
      ['Rail', receipt.rail || 'pending'],
      ['JWT passthrough', receipt.jwtPassthrough ? 'true' : 'false'],
      ['Gateway passthrough', receipt.gatewayPassthrough ? 'true' : 'false'],
    ].map(([label, value]) => (
      <div key={label}>
        <div
          className="font-mono"
          style={{
            fontSize: '10px',
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            color: 'var(--at-ink-3)',
            marginBottom: '5px',
          }}
        >
          {label}
        </div>
        <div
          style={{
            color: 'var(--at-ink-1)',
            fontFamily: 'var(--at-sans)',
            fontSize: '14px',
            fontWeight: 600,
          }}
        >
          {value}
        </div>
      </div>
    ))}
  </section>
);

const ProofCardView: React.FC<{ card: ProofCard }> = ({ card }) => (
  <article
    id={card.id}
    data-testid={`proof-card-${card.id}`}
    style={{
      border: '1px solid var(--at-card-border)',
      borderRadius: '8px',
      background: 'var(--at-card-bg)',
      padding: '22px 24px',
      scrollMarginTop: '80px',
      boxShadow: '0 2px 10px rgba(45, 24, 16, 0.04)',
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
        {card.act}
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
        {card.required ? 'Required path' : 'Extra time'}
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

const ProofBoard: React.FC = () => {
  const [data, setData] = useState<ProofBoardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetch('/api/atelier/proof-board')
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

  const groupedCards = useMemo(() => {
    const groups = new Map<string, ProofCard[]>();
    for (const card of data?.cards ?? []) {
      const items = groups.get(card.act) ?? [];
      items.push(card);
      groups.set(card.act, items);
    }
    return Array.from(groups.entries());
  }, [data]);

  return (
    <div style={{ padding: '40px 48px', maxWidth: '1180px' }}>
      <EditorialTitle
        eyebrow="Required path · proof board"
        title="Build, prove, then extend."
        summary="Use this board as the Atelier starting point. Each card maps the workshop flow to live evidence and keeps the terminal fallback next to the UI proof."
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

          {groupedCards.map(([act, cards]) => (
            <section key={act} aria-label={act} style={{ marginBottom: '34px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginBottom: '14px',
                }}
              >
                <Eyebrow label={act} />
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
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                  gap: '16px',
                }}
              >
                {cards.map((card) => (
                  <ProofCardView key={card.id} card={card} />
                ))}
              </div>
            </section>
          ))}
        </>
      )}
    </div>
  );
};

export default ProofBoard;
