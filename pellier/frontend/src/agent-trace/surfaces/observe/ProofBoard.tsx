/**
 * ProofBoard - system evidence surface.
 *
 * One route that maps the hands-on flow to concrete evidence:
 * readiness checks, evidence cards, and terminal fallbacks.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
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
  gatewayAuditAbsenceVerified?: boolean;
  latestGatewayAuditId?: number | null;
  latestGatewayAuditAt?: string;
  governedReceiptPresent?: boolean;
  latestGovernedReceiptId?: number | null;
  latestGovernedReceiptAt?: string;
  governedAuditId?: number | null;
  governedPrincipalId?: string;
  governedPrincipalLabel?: string;
  governedVerifiedSubject?: string;
  governedVerifiedUsername?: string;
  governedIdentitySource?: string;
  governedTokenFingerprint?: string;
  governedDecision?: string;
  governedTool?: string;
  governedPolicyName?: string;
  governedArgs?: Record<string, unknown>;
  absenceCheckDetail?: string;
}

interface ProofCard {
  id: string;
  lab?: string;
  group?: string;
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

interface ProofBoardProps {
  focusCardId?: string;
}

interface GovernanceReceipt {
  id: 'policy' | 'execution' | 'data';
  label: string;
  question: string;
  detail: string;
  evidence: string;
  state: TraceStepState;
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

// Four-lab workshop spine.
const LAB_BY_CARD_ID: Record<string, string> = {
  'marco-floor-check': 'Lab 1: Ground Answers in Live Data',
  'retrieval-comparison': 'Lab 2: Design the Retrieval Strategy',
  'managed-rail': 'Lab 3: Run Agents in a Managed Runtime',
  'audit-ledger': 'Lab 3: Run Agents in a Managed Runtime',
  'runtime-gateway-policy': 'Lab 4: Govern and Trace Agent Actions',
};

function cardLab(card: ProofCard): string {
  return LAB_BY_CARD_ID[card.id] ?? card.lab ?? 'Lab checkpoint';
}

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
        fontFamily: 'var(--at-heading)',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.03em',
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
        fontFamily: 'var(--at-heading)',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.03em',
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
          style={{
            fontFamily: 'var(--at-heading)',
            fontSize: '11.5px',
            fontWeight: 600,
            letterSpacing: '0.04em',
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
                style={{
                  fontFamily: 'var(--at-heading)',
                  fontSize: '11px',
                  fontWeight: 600,
                  letterSpacing: '0.03em',
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
                fontFamily: 'var(--at-heading)',
                fontSize: '20px',
                fontWeight: 600,
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
        style={{
          color: tone.color,
          fontFamily: 'var(--at-heading)',
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.03em',
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
          fontWeight: 600,
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

const GovernanceReceiptCard: React.FC<{ receipt: GovernanceReceipt }> = ({ receipt }) => {
  const tone = TRACE_TONE[receipt.state];
  return (
    <article
      data-testid={`governance-receipt-${receipt.id}`}
      style={{
        border: `1px solid ${tone.border}`,
        borderRadius: '8px',
        background: 'var(--at-card-bg)',
        minHeight: '218px',
        padding: '18px 20px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          marginBottom: '18px',
        }}
      >
        <span
          style={{
            color: 'var(--at-red-1)',
            fontFamily: 'var(--at-heading)',
            fontSize: '12px',
            fontWeight: 700,
            textTransform: 'uppercase',
          }}
        >
          {receipt.label}
        </span>
        <span
          style={{
            borderRadius: '999px',
            padding: '4px 8px',
            color: tone.color,
            background: tone.bg,
            fontFamily: 'var(--at-heading)',
            fontSize: '10.5px',
            fontWeight: 700,
            textTransform: 'uppercase',
            whiteSpace: 'nowrap',
          }}
        >
          {tone.label}
        </span>
      </div>
      <h3
        style={{
          margin: '0 0 12px',
          color: 'var(--at-ink-1)',
          fontFamily: 'var(--at-heading)',
          fontSize: '20px',
          fontWeight: 600,
          lineHeight: 1.2,
        }}
      >
        {receipt.question}
      </h3>
      <p
        style={{
          margin: '0 0 14px',
          color: 'var(--at-ink-2)',
          fontFamily: 'var(--at-sans)',
          fontSize: '13.5px',
          lineHeight: 1.5,
        }}
      >
        {receipt.detail}
      </p>
      <p
        className="font-mono"
        style={{
          margin: 'auto 0 0',
          color: 'var(--at-ink-3)',
          fontSize: '11.5px',
          lineHeight: 1.45,
          overflowWrap: 'anywhere',
        }}
      >
        {receipt.evidence}
      </p>
    </article>
  );
};

const ReceiptStrip: React.FC<{ receipt: ManagedReceipt }> = ({ receipt }) => {
  const gatewayAuditAt = formatTimestamp(receipt.latestGatewayAuditAt);
  const governedAt = formatTimestamp(receipt.latestGovernedReceiptAt);
  const customerId = typeof receipt.governedArgs?.customer_id === 'string'
    ? receipt.governedArgs.customer_id
    : '';
  const isDeny = receipt.governedDecision === 'DENY';
  const absenceVerified = Boolean(receipt.gatewayAuditAbsenceVerified);
  const receiptSeen = Boolean(receipt.present || receipt.governedReceiptPresent);
  const tokenFingerprint = receipt.governedTokenFingerprint
    ? `${receipt.governedTokenFingerprint.slice(0, 12)}...`
    : '';
  const traceSteps: Array<{ label: string; detail: string; state: TraceStepState }> = [
    {
      label: 'Verified identity',
      detail: receipt.governedVerifiedUsername
        ? `${receipt.governedVerifiedUsername} via ${receipt.governedIdentitySource || 'Cognito JWT'}`
        : receipt.governedPrincipalLabel
          ? receipt.governedPrincipalLabel
          : receipt.jwtPassthrough
            ? 'Caller JWT forwarded'
            : 'Signed-in JWT not observed',
      state: receipt.governedReceiptPresent || receipt.jwtPassthrough ? 'pass' : 'pending',
    },
    {
      label: 'JWT binding',
      detail: tokenFingerprint && receipt.governedVerifiedSubject
        ? `sha256 ${tokenFingerprint} · subject ${receipt.governedVerifiedSubject}`
        : 'No verified token fingerprint on receipt',
      state: tokenFingerprint && receipt.governedVerifiedSubject
        ? 'pass'
        : receipt.governedReceiptPresent ? 'warn' : 'pending',
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
      detail: receipt.governedDecision
        ? `${receipt.governedDecision}${receipt.governedPolicyName ? ` via ${receipt.governedPolicyName}` : ''}${governedAt ? ` at ${governedAt}` : ''}`
        : receipt.policyConfigured ? 'Policy engine configured' : 'Policy engine id missing',
      state: receipt.governedReceiptPresent
        ? 'pass'
        : receipt.policyConfigured ? (receipt.present ? 'pass' : 'pending') : 'warn',
    },
    {
      label: 'Tool result',
      detail: receipt.gatewayAuditPresent
        ? `${receipt.governedTool || 'Gateway tool'} audit ${receipt.latestGatewayAuditId}`
        : isDeny && absenceVerified
          ? 'Cedar DENY: tool target did not execute'
          : isDeny
            ? 'DENY receipt present; absence check pending'
            : 'No Gateway ALLOW row',
      state: receipt.gatewayAuditPresent || (isDeny && absenceVerified)
        ? 'pass'
        : receiptSeen ? 'warn' : 'pending',
    },
    {
      label: 'Aurora audit',
      detail: gatewayAuditAt
        ? `tool_audit at ${gatewayAuditAt}${customerId ? ` for ${customerId}` : ''}`
        : absenceVerified
          ? 'Gateway/Cedar DENY left no tool_audit row'
          : 'No Gateway audit row for this receipt',
      state: receipt.gatewayAuditPresent || absenceVerified ? 'pass' : receiptSeen ? 'warn' : 'pending',
    },
  ];
  const governanceReceipts: GovernanceReceipt[] = [
    {
      id: 'policy',
      label: 'Policy receipt',
      question: 'Was the action permitted?',
      detail: receipt.governedDecision
        ? `${receipt.governedDecision}${receipt.governedPolicyName ? ` via ${receipt.governedPolicyName}` : ''}${governedAt ? ` at ${governedAt}` : ''}`
        : receipt.policyConfigured
          ? 'Policy is configured; run the governed turn to capture a decision.'
          : 'No policy decision is available yet.',
      evidence: receipt.governedVerifiedUsername
        ? `${receipt.governedVerifiedUsername} via ${receipt.governedIdentitySource || 'Cognito JWT'}`
        : receipt.governedPrincipalLabel || 'No verified principal on the latest receipt',
      state: receipt.governedReceiptPresent
        ? 'pass'
        : receipt.policyConfigured ? 'warn' : 'pending',
    },
    {
      id: 'execution',
      label: 'Execution receipt',
      question: 'What actually ran?',
      detail: isDeny && receipt.governedReceiptPresent
        ? `${receipt.governedTool || 'The governed tool'} was stopped before target execution.`
        : receipt.gatewayAuditPresent
          ? `${receipt.governedTool || 'The governed tool'} ran through ${receipt.rail || 'the Gateway MCP rail'}.`
          : receipt.present
            ? `${receipt.runtime || 'AgentCore Runtime'} returned on ${receipt.rail || 'the managed rail'}; tool evidence is pending.`
            : 'No managed Runtime execution receipt is available yet.',
      evidence: receipt.present
        ? `${receipt.runtime || 'AgentCore Runtime'} · ${receipt.rail || 'managed rail'}`
        : 'Runtime and Gateway correlation not observed',
      state: receipt.gatewayAuditPresent || (isDeny && receipt.governedReceiptPresent)
        ? 'pass'
        : receipt.present ? 'warn' : 'pending',
    },
    {
      id: 'data',
      label: 'Data receipt',
      question: 'What reached the system of record?',
      detail: receipt.gatewayAuditPresent
        ? `Aurora recorded tool_audit row ${receipt.latestGatewayAuditId}${gatewayAuditAt ? ` at ${gatewayAuditAt}` : ''}.`
        : absenceVerified
          ? 'Aurora has no linked tool_audit row because Cedar denied the action before execution.'
          : 'No linked Aurora execution row or verified DENY absence is available yet.',
      evidence: receipt.gatewayAuditPresent
        ? `tool_audit.audit_id=${receipt.latestGatewayAuditId}${customerId ? ` · customer_id=${customerId}` : ''}`
        : absenceVerified
          ? 'governed receipt present · linked tool_audit row absent'
          : 'Database evidence pending',
      state: receipt.gatewayAuditPresent || absenceVerified
        ? 'pass'
        : receiptSeen ? 'warn' : 'pending',
    },
  ];

  return (
    <section
      aria-label="Three governance receipts"
      style={{
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
        <div>
          <Eyebrow label="Three receipts" />
          <h2
            style={{
              margin: '7px 0 0',
              color: 'var(--at-ink-1)',
              fontFamily: 'var(--at-heading)',
              fontSize: '24px',
              fontWeight: 600,
              lineHeight: 1.15,
            }}
          >
            Reconstruct one governed action.
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
          {receipt.present ? receipt.traceKind || 'managed receipt' : 'after SQL proof'}
        </span>
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '14px',
        }}
      >
        {governanceReceipts.map((item) => (
          <GovernanceReceiptCard key={item.id} receipt={item} />
        ))}
      </div>
      <details style={{ marginTop: '16px' }}>
        <summary
          style={{
            cursor: 'pointer',
            color: 'var(--at-red-1)',
            fontFamily: 'var(--at-heading)',
            fontSize: '13px',
            fontWeight: 600,
          }}
        >
          Inspect end-to-end correlation
        </summary>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '10px',
            marginTop: '12px',
          }}
        >
          {traceSteps.map((step) => (
            <TraceStep key={step.label} {...step} />
          ))}
        </div>
      </details>
      <p
        style={{
          margin: '12px 0 0',
          color: 'var(--at-ink-3)',
          fontFamily: 'var(--at-sans)',
          fontSize: '12.5px',
          lineHeight: 1.5,
        }}
      >
        No-row DENY is scoped to the Gateway/Cedar rail. In-process tool calls can still write audit rows
        because they execute before local return handling completes.
      </p>
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
        style={{
          fontFamily: 'var(--at-heading)',
          fontSize: '11.5px',
          fontWeight: 600,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          color: 'var(--at-red-1)',
        }}
      >
        {cardLab(card)}
      </span>
      {statusPill(card.status)}
      <span
        style={{
          fontFamily: 'var(--at-heading)',
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.03em',
          textTransform: 'uppercase',
          color: 'var(--at-ink-3)',
        }}
      >
        {card.required ? 'Required path' : 'Optional visual'}
      </span>
    </div>
    <h2
      style={{
        margin: '0 0 6px',
        color: 'var(--at-ink-1)',
        fontFamily: 'var(--at-heading)',
        fontSize: '26px',
        lineHeight: 1.15,
        fontWeight: 600,
      }}
    >
      {card.title}
    </h2>
    <p
      style={{
        margin: '0 0 12px',
        color: 'var(--at-ink-3)',
        fontFamily: 'var(--at-heading)',
        fontSize: '11.5px',
        fontWeight: 600,
        letterSpacing: '0.04em',
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
              style={{
                color: 'var(--at-ink-3)',
                fontFamily: 'var(--at-heading)',
                fontSize: '10.5px',
                fontWeight: 600,
                letterSpacing: '0.04em',
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
              style={{
                color: 'var(--at-ink-3)',
                fontFamily: 'var(--at-heading)',
                fontSize: '10.5px',
                fontWeight: 600,
                letterSpacing: '0.04em',
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
        style={{
          fontFamily: 'var(--at-heading)',
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.04em',
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
            fontFamily: 'var(--at-heading)',
            fontSize: '12.5px',
            fontWeight: 600,
          }}
        >
          {link.label}
        </Link>
      ))}
    </div>
  </article>
  );
};

function groupCardsByLab(cards: ProofCard[]) {
  const groups = new Map<string, ProofCard[]>();
  for (const card of cards) {
    const lab = cardLab(card);
    const items = groups.get(lab) ?? [];
    items.push(card);
    groups.set(lab, items);
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
  const groupedCards = groupCardsByLab(cards);
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
              fontFamily: 'var(--at-heading)',
              fontSize: '24px',
              fontWeight: 600,
              lineHeight: 1.15,
            }}
          >
            {title}
          </h2>
        </div>
        <span
          style={{
            color: 'var(--at-ink-3)',
            fontFamily: 'var(--at-heading)',
            fontSize: '11.5px',
            fontWeight: 600,
            letterSpacing: '0.03em',
            textTransform: 'uppercase',
          }}
        >
          {cards.length} {cards.length === 1 ? 'card' : 'cards'}
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
      {groupedCards.map(([lab, labCards]) => (
        <div key={lab} style={{ marginBottom: '20px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginBottom: '12px',
            }}
          >
            <Eyebrow label={lab} />
            <span
              style={{
                color: 'var(--at-ink-3)',
                fontFamily: 'var(--at-heading)',
                fontSize: '11.5px',
                fontWeight: 600,
                letterSpacing: '0.03em',
                textTransform: 'uppercase',
              }}
            >
              {labCards.length} {labCards.length === 1 ? 'card' : 'cards'}
            </span>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
              gap: '16px',
            }}
          >
            {labCards.map((card) => (
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

const ProofBoard: React.FC<ProofBoardProps> = ({ focusCardId }) => {
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
  const focusedCardId = focusCardId ?? activeAnchor;
  const isAuditFocus = focusedCardId === 'audit-ledger';

  const rails = useMemo(() => {
    const cards = data?.cards ?? [];
    return {
      required: cards.filter((card) => card.required),
      optional: cards.filter((card) => !card.required),
    };
  }, [data]);
  const focusedCard = useMemo(
    () => data?.cards.find((card) => card.id === focusedCardId) ?? null,
    [data, focusedCardId],
  );

  return (
    <div style={{ padding: '40px 48px', maxWidth: '1180px' }}>
      {isAuditFocus && (
        <Link
          to="/agent-trace/proof-board"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '7px',
            marginBottom: '24px',
            color: 'var(--at-ink-2)',
            fontFamily: 'var(--at-heading)',
            fontSize: '13px',
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          <ArrowLeft size={15} aria-hidden="true" />
          All checkpoints
        </Link>
      )}
      <EditorialTitle
        eyebrow={isAuditFocus ? 'Lab 3 · Run Agents in a Managed Runtime' : 'Labs 1-4 · Proof Board'}
        title={isAuditFocus ? 'Audit proof, row by row.' : 'Evidence checkpoints, in lab order.'}
        summary={
          isAuditFocus
            ? 'A focused read of the live Aurora ledger and governed receipt. The SQL result remains the canonical proof; this view confirms that the expected evidence is present.'
            : "Use this board when a required lab asks for an Agent Trace check. Checkpoints follow the four-lab order; Memory, managed Runtime, Gateway, and Policy are required in the governed format."
        }
      />

      {loading && (
        <p className="font-mono" style={{ color: 'var(--at-ink-3)' }}>
          {isAuditFocus ? 'Loading audit proof...' : 'Loading proof board...'}
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
        isAuditFocus ? (
          focusedCard ? (
            <section
              aria-label="Lab 3 audit evidence"
              style={{ maxWidth: '860px' }}
            >
              <ProofCardView card={focusedCard} highlighted />
            </section>
          ) : (
            <div
              role="alert"
              style={{
                border: '1px solid var(--at-card-border)',
                borderRadius: '8px',
                padding: '18px 20px',
                color: 'var(--at-ink-2)',
                fontFamily: 'var(--at-sans)',
              }}
            >
              The audit-ledger checkpoint is not available from this backend.
            </div>
          )
        ) : (
          <>
            <ReadinessPanel checks={data.readiness.checks} />

            <ProofRail
              eyebrow="Required path"
              title="Lab checkpoints"
              summary="These cards mirror evidence from the required path. Use their terminal or SQL fallbacks when you need canonical proof."
              cards={rails.required}
              activeAnchor={activeAnchor}
            />
            <ReceiptStrip receipt={data.managedReceipt} />
            <ProofRail
              eyebrow="Extension evidence"
              title="Managed boundary"
              summary="These cards remain optional only in the separate builders format."
              cards={rails.optional}
              activeAnchor={activeAnchor}
            />
          </>
        )
      )}
    </div>
  );
};

export default ProofBoard;
