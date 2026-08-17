/**
 * Write-path — Theo's third Aurora capability surface.
 *
 * Shows how mutating tools (process_return, restock_shelf) flow through
 * a two-layer enforcement gate (managed AgentCore Policy at the Gateway
 * + SQL ownership) and leave a paper trail in pellier.tool_audit that's
 * reconstructible from a single SELECT.
 *
 * Three sections:
 *   1. Two-layer enforcement diagram — conceptual
 *   2. Cedar policies — live list of the managed engine's policies from
 *      /api/agent-trace/policies
 *   3. Recent tool_audit rows — live from /api/agent-trace/tool-audit/recent
 *
 * Pedagogical role: anchors Aurora's third capability (system-of-record)
 * the way Tools anchors discovery and Memory anchors LTM. Without this
 * surface, Theo's write-path teaching lives entirely in the lab content
 * with nothing to point at in Pellier Labs.
 */

import React, { useEffect, useState } from 'react';
import {
  EditorialTitle,
  ExpCard,
  Eyebrow,
} from '../../components';

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
  fontFamily: 'var(--dl-font-mono)',
  fontSize: '12.5px',
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
  fontFamily: 'var(--dl-font-mono)',
  fontSize: '11.5px',
  background: 'var(--dl-ink)',
  color: 'var(--dl-accent-soft)',
  borderRadius: '6px',
  padding: '3px 7px',
};

/* -----------------------------------------------------------------------
 * Two-layer enforcement diagram
 *
 * Visualizes the chain:
 *   Agent calls process_return
 *     → Cedar (managed Policy at the Gateway) — gates on reason == 'damaged'
 *     → SQL (BusinessLogic) — gates on customer ownership
 *     → 3 writes in one transaction
 *     → tool_audit row (AfterToolCallEvent updates result + latency)
 * ----------------------------------------------------------------------- */

const EnforcementDiagram: React.FC = () => {
  const stepStyle: React.CSSProperties = {
    fontFamily: 'var(--at-mono)',
    fontSize: '14px',
    color: 'var(--at-ink-1)',
    padding: '10px 14px',
    borderRadius: '6px',
    background: 'var(--at-cream-2)',
    border: '1px solid var(--at-card-border)',
  };
  const arrowStyle: React.CSSProperties = {
    fontFamily: 'var(--at-mono)',
    color: 'var(--at-ink-3)',
    textAlign: 'center' as const,
    fontSize: '13px',
    margin: '4px 0',
  };
  const layerLabel: React.CSSProperties = {
    fontFamily: 'var(--at-mono)',
    fontSize: '11px',
    letterSpacing: '0.08em',
    textTransform: 'uppercase' as const,
    color: 'var(--at-ink-3)',
    marginBottom: '6px',
  };
  return (
    <ExpCard>
      <Eyebrow label="Two-layer enforcement" />
      <h3
        style={{
          fontFamily: 'var(--at-serif)',
          fontSize: '24px',
          fontWeight: 400,
          margin: '6px 0 16px',
          color: 'var(--at-ink-1)',
        }}
      >
        Cedar guards what; SQL guards whose.
      </h3>
      <p
        style={{
          fontFamily: 'var(--at-sans)',
          fontSize: '14px',
          lineHeight: 1.6,
          color: 'var(--at-ink-2)',
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
        <div style={stepStyle}>process_return(customer_id, product_id, reason)</div>
        <div style={arrowStyle}>↓</div>

        <div style={{ ...layerLabel, color: 'var(--at-burgundy)' }}>
          Layer 1 · Cedar (managed Policy · Gateway · ENFORCE)
        </div>
        <div style={stepStyle}>
          forbid when reason ∉ {`{damaged, wrong_size, ...}`}
          <span style={{ color: 'var(--at-ink-3)', marginLeft: '8px' }}>
            → DENY → no SQL fires
          </span>
        </div>
        <div style={arrowStyle}>↓ ALLOW</div>

        <div style={{ ...layerLabel, color: 'var(--at-burgundy)' }}>
          Layer 2 · SQL (BusinessLogic.process_return)
        </div>
        <div style={stepStyle}>
          SELECT 1 FROM orders WHERE customer_id=? AND product_id=?
          <span style={{ color: 'var(--at-ink-3)', marginLeft: '8px' }}>
            → not owned → reject
          </span>
        </div>
        <div style={arrowStyle}>↓ owned</div>

        <div style={layerLabel}>3 writes in one transaction</div>
        <div style={stepStyle}>
          INSERT INTO pellier.returns
          <br />
          UPDATE pellier.product_catalog SET quantity = quantity - 1 WHERE reason = 'damaged'
          <br />
          UPDATE pellier.tool_audit SET result, latency_ms
        </div>
        <div style={arrowStyle}>↓ commit</div>

        <div style={{ ...layerLabel, color: 'var(--at-shipped)' }}>
          Aurora as system-of-record
        </div>
        <div style={stepStyle}>
          Every mutation is reconstructible from a single SELECT against
          tool_audit.
        </div>
      </div>
    </ExpCard>
  );
};

/* -----------------------------------------------------------------------
 * Cedar policies — fetched live from /api/agent-trace/policies (the managed
 * AgentCore Policy engine attached to the Gateway in ENFORCE mode)
 * ----------------------------------------------------------------------- */

const PoliciesCard: React.FC = () => {
  const [policies, setPolicies] = useState<CedarPolicy[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/agent-trace/policies')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => setPolicies(data.policies ?? []))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <ExpCard>
      <Eyebrow label={`Cedar policies · ${policies?.length ?? '–'} on the managed engine`} />
      <h3
        style={{
          fontFamily: 'var(--at-serif)',
          fontSize: '24px',
          fontWeight: 400,
          margin: '6px 0 16px',
          color: 'var(--at-ink-1)',
        }}
      >
        Policy is code, code is enforcement.
      </h3>
      <p
        style={{
          fontFamily: 'var(--at-sans)',
          fontSize: '14px',
          lineHeight: 1.6,
          color: 'var(--at-ink-2)',
          marginBottom: '20px',
        }}
      >
        Each policy is a Cedar block on the managed AgentCore Policy
        engine, enforced at the Gateway in{' '}
        <code style={{ fontFamily: 'var(--at-mono)', color: 'var(--at-ink-1)' }}>
          ENFORCE
        </code>{' '}
        mode – argument-aware, default-deny, forbid-wins, evaluated
        before the tool target runs. New rules are rendered and deployed by
        the pinned AgentCore CLI project, not by application code.
      </p>

      {error && (
        <div style={{ fontFamily: 'var(--at-mono)', fontSize: '13px', color: 'var(--at-red-1)' }}>
          Managed policy list unavailable here: {error}
        </div>
      )}

      {policies && policies.length === 0 && (
        <div style={{ fontFamily: 'var(--at-mono)', fontSize: '13px', color: 'var(--at-ink-3)' }}>
          (no policies registered)
        </div>
      )}

      {policies && policies.length > 0 && (
        <div style={{ display: 'grid', gap: '14px' }}>
          {policies.map((p) => (
            <div
              key={p.id}
              style={{
                border: '1px solid var(--at-card-border)',
                borderRadius: '6px',
                padding: '14px',
                background: 'var(--at-cream-1)',
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
                    fontFamily: 'var(--at-serif)',
                    fontSize: '17px',
                    color: 'var(--at-ink-1)',
                    fontWeight: 500,
                  }}
                >
                  {p.name}
                </strong>
                {p.applies_to && (
                  <code
                    style={{
                      fontFamily: 'var(--at-mono)',
                      fontSize: '12px',
                      color: 'var(--at-ink-3)',
                    }}
                  >
                    applies_to: {p.applies_to}
                  </code>
                )}
              </div>
              <div
                style={{
                  fontFamily: 'var(--at-sans)',
                  fontSize: '13px',
                  color: 'var(--at-ink-2)',
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
 * Recent tool_audit rows — fetched live from /api/agent-trace/tool-audit/recent
 * ----------------------------------------------------------------------- */

const ToolAuditCard: React.FC = () => {
  const [rows, setRows] = useState<ToolAuditRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/agent-trace/tool-audit/recent?limit=10')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => setRows(data.rows ?? []))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <ExpCard>
      <Eyebrow label={`tool_audit · last ${rows?.length ?? '–'} rows`} />
      <h3
        style={{
          fontFamily: 'var(--at-serif)',
          fontSize: '24px',
          fontWeight: 400,
          margin: '6px 0 16px',
          color: 'var(--at-ink-1)',
        }}
      >
        Every mutation, replayable from a single row.
      </h3>
      <p
        style={{
          fontFamily: 'var(--at-sans)',
          fontSize: '14px',
          lineHeight: 1.6,
          color: 'var(--at-ink-2)',
          marginBottom: '20px',
        }}
      >
        Once the Gateway's managed Cedar policy ALLOWs a tool call, the
        tool runs and a row lands in <code style={{ fontFamily: 'var(--at-mono)' }}>tool_audit</code>{' '}
        with the placeholder fields, then the result + measured latency
        are written back when the call returns. The whole turn lives in{' '}
        <code style={{ fontFamily: 'var(--at-mono)' }}>args</code>{' '}
        (input) and <code style={{ fontFamily: 'var(--at-mono)' }}>result</code> (output).
        A call the Gateway DENIES never runs, so it leaves no row – the
        absence is the signal.
      </p>

      {error && (
        <div style={{ fontFamily: 'var(--at-mono)', fontSize: '13px', color: 'var(--at-red-1)' }}>
          Live tool_audit read unavailable here: {error}
        </div>
      )}

      {rows && rows.length === 0 && (
        <div style={{ fontFamily: 'var(--at-mono)', fontSize: '13px', color: 'var(--at-ink-3)' }}>
          No tool_audit rows yet – fire a process_return turn or restock_shelf to populate.
        </div>
      )}

      {rows && rows.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontFamily: 'var(--at-mono)',
              fontSize: '12px',
            }}
          >
            <thead>
              <tr style={{ textAlign: 'left' as const, color: 'var(--at-ink-3)' }}>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                  audit_id
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                  tool
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                  caller
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                  args
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                  latency_ms
                </th>
                <th style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                  created_at
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.audit_id}>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                    {r.audit_id}
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                    {r.tool}
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                    {r.caller}
                  </td>
                  <td
                    style={{
                      padding: '6px 8px',
                      borderBottom: '1px solid var(--at-card-border)',
                      maxWidth: '320px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap' as const,
                    }}
                    title={JSON.stringify(r.args)}
                  >
                    <code style={DARK_INLINE_CODE}>{JSON.stringify(r.args)}</code>
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
                    {r.latency_ms ?? '–'}
                  </td>
                  <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--at-card-border)' }}>
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
    <div className="pellier-labs-reference-page" style={{ maxWidth: '960px' }}>
      <EditorialTitle
        backToReferences
        eyebrow="Understand · Write-path · Aurora as system-of-record"
        title="Guarded writes"
        summary="Trace a mutation from policy decision through the tool invocation to an Aurora audit receipt."
        references={[
          { label: 'Source', value: 'services/tool_audit_writer.py', code: true },
          { label: 'Pattern', value: 'policy -> tool -> Aurora audit', code: true },
        ]}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <EnforcementDiagram />
        <PoliciesCard />
        <ToolAuditCard />
      </div>
    </div>
  );
};

export default WritePath;
