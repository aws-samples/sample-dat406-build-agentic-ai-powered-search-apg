/**
 * Pellier Labs top bar.
 *
 * The Labs identity is singular and the storefront return is explicit so the
 * inspection canvas remains the primary surface at every viewport width.
 */

import React, { useMemo, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import PersonaModal from '../../components/PersonaModal';
import { BreadcrumbTrail } from '../components/BreadcrumbTrail';
import { usePersona } from '../../contexts/PersonaContext';
import { getPersonaPhoto } from '../../data/personaPhotos';
import { PresencePill } from '../../shared';

function prettifySegment(segment: string): string {
  const labels: Record<string, string> = {
    'pellier-labs': 'Pellier Labs',
    'agent-trace': 'Pellier Labs',
    'proof-board': 'Proof Board',
    'audit-proof': 'Audit Proof',
    sessions: 'Sessions',
    observatory: 'Workshop Map',
    'persona-journeys': 'Persona Journeys',
    architecture: 'Architecture',
    agents: 'Agents',
    skills: 'Skills',
    tools: 'Tools',
    search: 'Search',
    routing: 'Routing',
    memory: 'Memory',
    'write-path': 'Gateway & Policy',
    performance: 'Performance',
    evaluations: 'Evaluations',
    'production-patterns': 'Production Patterns',
    settings: 'Settings',
    chat: 'Chat',
    telemetry: 'Telemetry',
    brief: 'Brief',
    mcp: 'MCP',
    runtime: 'Runtime',
    grounding: 'Grounding',
    'state-management': 'State Management',
    'tool-registry': 'Tool Registry',
  };

  return labels[segment.toLowerCase()] ?? segment;
}

function useBreadcrumbs(): string[] {
  const { pathname } = useLocation();
  return useMemo(() => {
    const parts = pathname.split('/').filter(Boolean).map(prettifySegment);
    return parts.length ? parts : ['Pellier Labs'];
  }, [pathname]);
}

const TopBar: React.FC = () => {
  const breadcrumbs = useBreadcrumbs();
  const { persona } = usePersona();
  const [personaModalOpen, setPersonaModalOpen] = useState(false);

  const avatarInitial = persona?.avatar_initial ?? '?';
  const avatarColor = persona?.avatar_color ?? '#665f58';
  const personaLabel = persona?.display_name?.split(' ')[0] ?? 'Choose profile';
  const photoUrl = persona ? getPersonaPhoto(persona.id) : undefined;

  return (
    <>
      <header className="pellier-labs-topbar" data-testid="agent-trace-topbar">
        <div className="pellier-labs-topbar-start">
          <Link to="/pellier-labs" className="pellier-labs-wordmark">
            Pellier Labs
          </Link>

          {breadcrumbs.length > 1 ? (
            <div className="pellier-labs-breadcrumbs">
              <BreadcrumbTrail segments={breadcrumbs.slice(1)} />
            </div>
          ) : null}
        </div>

        <div className="pellier-labs-topbar-end">
          <div className="pellier-labs-presence">
            <PresencePill surface="agentTrace" personaId={persona?.id} />
          </div>

          <button
            type="button"
            data-testid="agent-trace-persona-switcher"
            className="pellier-labs-persona"
            onClick={() => setPersonaModalOpen(true)}
            aria-label={`Switch persona${persona?.display_name ? ` from ${persona.display_name}` : ''}`}
            title="Switch persona"
          >
            {photoUrl ? (
              <img src={photoUrl} alt="" aria-hidden="true" />
            ) : (
              <span
                className="pellier-labs-persona-initial"
                aria-hidden="true"
                style={{ background: avatarColor }}
              >
                {avatarInitial}
              </span>
            )}
            <span className="pellier-labs-persona-copy">
              <small>Persona</small>
              <strong>{personaLabel}</strong>
            </span>
          </button>

          <Link
            to="/"
            data-testid="back-to-pellier"
            aria-label="Back to Pellier"
            className="pellier-labs-back"
          >
            <ArrowLeft size={16} strokeWidth={1.8} aria-hidden="true" />
            <span>Back to Pellier</span>
          </Link>
        </div>
      </header>
      <PersonaModal open={personaModalOpen} onClose={() => setPersonaModalOpen(false)} />
    </>
  );
};

export default TopBar;
