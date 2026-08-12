import React, { useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, ArrowDown } from 'lucide-react';
import { lookupVocab } from '../../shared';

const PROOF_ANCHOR_LABELS: Record<string, string> = {
  'runtime-gateway-policy': 'Runtime, Gateway, and policy proof',
  'marco-floor-check': "Marco's floor_check proof",
  'retrieval-comparison': 'retrieval comparison proof',
  'audit-ledger': 'audit ledger proof',
};

function anchorLabel(hash: string): string {
  const anchor = hash.replace(/^#/, '');
  return PROOF_ANCHOR_LABELS[anchor] ?? 'the matching proof section';
}

const AgentTraceContextBanner: React.FC = () => {
  const location = useLocation();

  const context = useMemo(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('from') !== 'boutique') return null;
    const trace = params.get('trace') ?? 'tool.transparency';
    const vocab = lookupVocab(trace);
    return {
      label: vocab.label,
      trace,
      section: location.pathname.endsWith('/audit-proof')
        ? 'audit ledger proof'
        : anchorLabel(location.hash),
    };
  }, [location.pathname, location.search, location.hash]);

  if (!context) return null;

  const cleanPath = `${location.pathname}${location.hash}`;

  return (
    <aside
      className="agent-trace-context-banner"
      data-testid="agent-trace-context-banner"
      aria-label="Pellier trace context"
    >
      <div className="agent-trace-context-copy">
        <span className="agent-trace-context-kicker">Pellier trace</span>
        <strong>{context.label}</strong>
        <span>
          Landed here from a shopper-facing trace chip. This Pellier Labs view shows {context.section}.
        </span>
      </div>
      <div className="agent-trace-context-actions">
        <Link to="/" className="agent-trace-context-link">
          <ArrowLeft size={13} aria-hidden="true" />
          Pellier
        </Link>
        <Link to={cleanPath} className="agent-trace-context-link">
          <ArrowDown size={13} aria-hidden="true" />
          Keep proof
        </Link>
      </div>
    </aside>
  );
};

export default AgentTraceContextBanner;
