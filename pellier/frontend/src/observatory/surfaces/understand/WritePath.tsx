/**
 * Write-path — Theo's third Aurora capability surface.
 *
 * Shows how mutating tools (initiate_return, restock_inventory) flow through
 * a two-layer enforcement gate (managed AgentCore Policy at the Gateway
 * + SQL ownership) and leave a paper trail in pellier.tool_audit that's
 * reconstructible from a single SELECT.
 *
 * Three sections:
 *   1. Two-layer enforcement diagram — conceptual
 *   2. Cedar policies — live list of the managed engine's policies from
 *      /api/observatory/policies
 *   3. Recent tool_audit rows — live from /api/observatory/tool-audit/recent
 *
 * Pedagogical role: anchors Aurora's third capability (system-of-record)
 * the way Tools anchors discovery and Memory anchors LTM. Without this
 * surface, Theo's write-path teaching lives entirely in the lab content
 * with nothing to point at in the Observatory.
 */

import React, { useEffect, useState } from 'react';
import {
  EditorialTitle,
  ExpCard,
  Eyebrow,
} from '../../components';
import IdentityBoundaryCard from './IdentityBoundaryCard';

/* -----------------------------------------------------------------------
 * Types
 * ----------------------------------------------------------------------- */

interface CedarPolicy {
  id: string;
  name: string;
  description: string;
  applies_to?: string;
  cedar: string;
}

interface ToolAuditRow {
  audit_id: number;
  session_id: string;
  tool: string;
  caller: string;
  args: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  latency_ms: number | null;
  created_at: string;
}

const DARK_CODE_BLOCK: React.CSSProperties = {
  fontFamily: 'var(--obs-mono)',
  fontSize: '12px',
  lineHeight: 1.6,
  background: 'var(--dl-ink)',
  color: 'var(--dl-accent-soft)',
  borderRadius: 'var(--dl-r-lg)',
  border: '1px solid color-mix(in srgb, var(--dl-accent-soft) 18%, transparent)',
  padding: '14px 16px',
  overflow: 'auto',
  margin: 0,
  whiteSpace: 'pre-wrap',
};

const DARK_INLINE_CODE: React.CSSProperties = {
  fontFamily: 'var(--obs-mono)',
  fontSize: '11px',
  background: 'var(--dl-ink)',
  color: 'var(--dl-accent-soft)',
  borderRadius: '6px',
  padding: '3px 7px',
};

/* -----------------------------------------------------------------------
 * Two-layer enforcement diagram
 *
 * Visualizes the chain:
 *   Agent calls initiate_return
 *     → Cedar (managed Policy at the Gateway) — gates on reason == 'damaged'
 *     → SQL stored function — gates ownership and claims an idempotency key
 *     → return + warehouse/catalog inventory writes in one transaction
 *     → Gateway Lambda appends the tool_audit execution receipt
 * ----------------------------------------------------------------------- */

const EnforcementDiagram: React.FC = () => {
  const stepStyle: React.CSSProperties = {
    fontFamily: 'var(--obs-mono)',
    fontSize: '14px',
    color: 'var(--obs-ink-1)',
    padding: '10px 14px',
    borderRadius: '6px',
    background: 'var(--obs-cream-2)',
    border: '1px solid var(--obs-card-border)',
    overflowWrap: 'anywhere',
  };
  const arrowStyle: React.CSSProperties = {
    fontFamily: 'var(--obs-mono)',
    color: 'var(--obs-ink-3)',
    textAlign: 'center' as const,
    fontSize: '13px',
    margin: '4px 0',
  };
  const layerLabel: React.CSSProperties = {
    fontFamily: 'var(--obs-heading)',
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.04em',
    textTransform: 'uppercase' as const,
    color: 'var(--obs-ink-3)',
    marginBottom: '6px',
  };
  return (
    <ExpCard>
      <Eyebrow label="Two-layer enforcement" />
      <h3
        style={{
          fontFamily: 'var(--obs-heading)',
          fontSize: '24px',
          fontWeight: 600,
          margin: '6px 0 16px',
          color: 'var(--obs-ink-1)',
        }}
      >
        Cedar guards what; SQL guards whose.
      </h3>
      <p
        style={{
          fontFamily: 'var(--obs-sans)',
          fontSize: '14px',
          lineHeight: 1.6,
          color: 'var(--obs-ink-2)',
          marginBottom: '24px',
        }}
      >
        Mutating tools (the ones with the burgundy WRITE badge on the
        Tools page) pass through two enforcement layers before any row
        gets written. The first is Cedar, declarative and static,
        enforced by the managed AgentCore Policy engine at the Gateway.
        The second is SQL, dynamic and live. Removing either layer
        breaks the contract.
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr',
          gap: 0,
          maxWidth: '560px',
        }}
      >
        <div style={layerLabel}>Agent</div>
        <div style={stepStyle}>
          initiate_return(customer_id, product_id, reason, idempotency_key)
        </div>
        <div style={arrowStyle}>↓</div>

        <div style={{ ...layerLabel, color: 'var(--obs-burgundy)' }}>
          Layer 1 · Cedar (managed Policy · Gateway · ENFORCE)
        </div>
        <div style={stepStyle}>
          forbid when reason != damaged
          <span style={{ color: 'var(--obs-ink-3)', marginLeft: '8px' }}>
            → DENY → no SQL fires
          </span>
        </div>
        <div style={arrowStyle}>↓ ALLOW</div>

        <div style={{ ...layerLabel, color: 'var(--obs-burgundy)' }}>
          Layer 2 · SQL (process_return_idempotent)
        </div>
        <div style={stepStyle}>
          claim idempotency_key + SELECT 1 FROM orders
          <span style={{ color: 'var(--obs-ink-3)', marginLeft: '8px' }}>
            → replay or not owned → no duplicate write
          </span>
        </div>
        <div style={arrowStyle}>↓ owned</div>

        <div style={layerLabel}>One Aurora transaction</div>
        <div style={stepStyle}>
          INSERT INTO pellier.returns
          <br />
          UPDATE pellier.warehouse_inventory
          <br />
          UPDATE pellier.product_catalog from warehouse aggregate
          <br />
          COMPLETE pellier.write_operations
        </div>
        <div style={arrowStyle}>↓ commit + Gateway execution receipt</div>

        <div style={{ ...layerLabel, color: 'var(--obs-shipped)' }}>
          Aurora as system-of-record
        </div>
        <div style={stepStyle}>
          pellier.tool_audit records the managed action, result, latency, and
          caller after Lambda execution.
        </div>
      </div>
    </ExpCard>
  );
};

/* -----------------------------------------------------------------------
 * Cedar policies — fetched live from /api/observatory/policies (the managed
 * AgentCore Policy engine attached to the Gateway in ENFORCE mode)
 * ----------------------------------------------------------------------- */

const PoliciesCard: React.FC = () => {
  const [policies, setPolicies] = useState<CedarPolicy[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/observatory/policies')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => setPolicies(data.policies ?? []))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <ExpCard>
      <Eyebrow label={`Cedar policies · ${policies?.length ?? '–'} on the managed engine`} />
      <h3
        style={{
          fontFamily: 'var(--obs-heading)',
          fontSize: '24px',
          fontWeight: 600,
          margin: '6px 0 16px',
          color: 'var(--obs-ink-1)',
        }}
      >
        Policy is code, code is enforcement.
      </h3>
      <p
        style={{
          fontFamily: 'var(--obs-sans)',
          fontSize: '14px',
          lineHeight: 1.6,
          color: 'var(--obs-ink-2)',
          marginBottom: '20px',
        }}
      >
        Each policy is a Cedar block on the managed AgentCore Policy
        engine, enforced at the Gateway in{' '}
        <code style={{ fontFamily: 'var(--obs-mono)', color: 'var(--obs-ink-1)' }}>
          ENFORCE
        </code>{' '}
        mode – argument-aware, default-deny, forbid-wins, evaluated
        before the tool's Lambda ever runs. New rules are added to the
        declarative AgentCore project with{' '}
        <code style={{ fontFamily: 'var(--obs-mono)' }}>agentcore add policy</code>,
        validated, and deployed through the same CLI.
      </p>

      {error && (
        <div style={{ fontFamily: 'var(--obs-mono)', fontSize: '13px', color: 'var(--obs-red-1)' }}>
          Managed policy list unavailable here: {error}
        </div>
      )}

      {policies && policies.length === 0 && (
        <div style={{ fontFamily: 'var(--obs-mono)', fontSize: '13px', color: 'var(--obs-ink-3)' }}>
          (no policies registered)
        </div>
      )}

      {policies && policies.length > 0 && (
        <div style={{ display: 'grid', gap: '14px' }}>
          {policies.map((p) => (
            <div
              key={p.id}
              style={{
                border: '1px solid var(--obs-card-border)',
                borderRadius: '6px',
                padding: '14px',
                background: 'var(--obs-cream-1)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  marginBottom: '8px',
                }}
              >
                <strong
                  style={{
                    fontFamily: 'var(--obs-heading)',
                    fontSize: '17px',
                    color: 'var(--obs-ink-1)',
                    fontWeight: 600,
                  }}
                >
                  {p.name}
                </strong>
                {p.applies_to && (
                  <code
                    style={{
                      fontFamily: 'var(--obs-mono)',
                      fontSize: '12px',
                      color: 'var(--obs-ink-3)',
                    }}
                  >
                    applies_to: {p.applies_to}
                  </code>
                )}
              </div>
              <div
                style={{
                  fontFamily: 'var(--obs-sans)',
                  fontSize: '13px',
                  color: 'var(--obs-ink-2)',
                  marginBottom: '10px',
                }}
              >
                {p.description}
              </div>
              <pre
                style={{
                  ...DARK_CODE_BLOCK,
                  fontSize: '12px',
                }}
              >
                {p.cedar}
              </pre>
            </div>
          ))}
        </div>
      )}
    </ExpCard>
  );
};

/* -----------------------------------------------------------------------
 * Recent tool_audit rows — fetched live from /api/observatory/tool-audit/recent
 * ----------------------------------------------------------------------- */

const ToolAuditCard: React.FC = () => {
  const [rows, setRows] = useState<ToolAuditRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/observatory/tool-audit/recent?limit=10')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => setRows(data.rows ?? []))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <ExpCard>
      <Eyebrow label={`tool_audit · last ${rows?.length ?? '–'} rows`} />
      <h3
        style={{
          fontFamily: 'var(--obs-heading)',
          fontSize: '24px',
          fontWeight: 600,
          margin: '6px 0 16px',
          color: 'var(--obs-ink-1)',
        }}
      >
        Every mutation, replayable from a single row.
      </h3>
      <p
        style={{
          fontFamily: 'var(--obs-sans)',
          fontSize: '14px',
          lineHeight: 1.6,
          color: 'var(--obs-ink-2)',
          marginBottom: '20px',
        }}
      >
        Once the Gateway's managed Cedar policy ALLOWs a tool call, the
        tool runs and a row lands in <code style={{ fontFamily: 'var(--obs-mono)' }}>tool_audit</code>{' '}
        with the placeholder fields, then the result + measured latency
        are written back when the call returns. The whole turn lives in{' '}
        <code style={{ fontFamily: 'var(--obs-mono)' }}>args</code>{' '}
        (input) and <code style={{ fontFamily: 'var(--obs-mono)' }}>result</code> (output).
        A call the Gateway DENIES never runs, so it leaves no row – the
        absence is the signal.
      </p>

      {error && (
        <div style={{ fontFamily: 'var(--obs-mono)', fontSize: '13px', color: 'var(--obs-red-1)' }}>
          Live tool_audit read unavailable here: {error}
        </div>
      )}

      {rows && rows.length === 0 && (
        <div style={{ fontFamily: 'var(--obs-mono)', fontSize: '13px', color: 'var(--obs-ink-3)' }}>
          No tool_audit rows yet – fire a initiate_return turn or restock_inventory to populate.
        </div>
      )}

      {rows && rows.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontFamily: 'var(--obs-mono)',
              fontSize: '12px',
            }}
          >
            <thead>
              <tr style={{ textAlign: 'left' as const, color: 'var(--obs-ink-3)' }}>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                  audit_id
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                  tool
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                  caller
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                  args
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                  latency_ms
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                  created_at
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.audit_id}>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                    {r.audit_id}
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                    {r.tool}
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                    {r.caller}
                  </td>
                  <td
                    style={{
                      padding: '6px 8px',
                      borderBottom: '1px solid var(--obs-card-border)',
                      maxWidth: '320px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap' as const,
                    }}
                    title={JSON.stringify(r.args)}
                  >
                    <code style={DARK_INLINE_CODE}>{JSON.stringify(r.args)}</code>
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                    {r.latency_ms ?? '–'}
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--obs-card-border)' }}>
                    {r.created_at?.replace('T', ' ').slice(0, 19)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ExpCard>
  );
};

/* -----------------------------------------------------------------------
 * Page
 * ----------------------------------------------------------------------- */

const WritePath: React.FC = () => {
  return (
    <div style={{ padding: '40px 48px', maxWidth: '960px' }}>
      <EditorialTitle
        backToReferences
        eyebrow="Understand · Write-path · Aurora as system-of-record"
        title="Write path"
        summary="Marco read. Anna read harder. Theo writes – and every write leaves a paper trail. The agent calls a mutating tool; Cedar gates on what; SQL gates on whose; Aurora records the turn in tool_audit. Replayable from a single SELECT."
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <EnforcementDiagram />
        {/* Placed above the policy source: "who was refused, and what proves
            it" is the question a participant arrives with. The Cedar text and
            the raw ledger answer "how", and follow. */}
        <IdentityBoundaryCard />
        <PoliciesCard />
        <ToolAuditCard />
      </div>
    </div>
  );
};

export default WritePath;
