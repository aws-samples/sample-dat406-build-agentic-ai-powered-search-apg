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

const AtelierContextBanner: React.FC = () => {
  const location = useLocation();

  const context = useMemo(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('from') !== 'boutique') return null;
    const trace = params.get('trace') ?? 'tool.transparency';
    const vocab = lookupVocab(trace);
    return {
      label: vocab.label,
      trace,
      section: anchorLabel(location.hash),
    };
  }, [location.search, location.hash]);

  if (!context) return null;

  const cleanPath = `${location.pathname}${location.hash}`;

  return (
    <aside
      className="atelier-context-banner"
      data-testid="atelier-context-banner"
      aria-label="Boutique trace context"
    >
      <div className="atelier-context-copy">
        <span className="atelier-context-kicker">Boutique trace</span>
        <strong>{context.label}</strong>
        <span>
          Landed here from a shopper-facing trace chip. This Atelier view shows {context.section}.
        </span>
      </div>
      <div className="atelier-context-actions">
        <Link to="/" className="atelier-context-link">
          <ArrowLeft size={13} aria-hidden="true" />
          Boutique
        </Link>
        <Link to={cleanPath} className="atelier-context-link">
          <ArrowDown size={13} aria-hidden="true" />
          Keep proof
        </Link>
      </div>
    </aside>
  );
};

export default AtelierContextBanner;
