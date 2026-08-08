/**
 * TopBar — Horizontal bar above the Atelier canvas.
 *
 * Contains the SurfaceToggle (reused from existing component),
 * a BreadcrumbTrail derived from the current route, live status
 * metadata, and the persona avatar.
 *
 * Requirements: 1.9, 1.10, 1.11, 1.12
 */

import React, { useMemo, useState } from 'react';
import { Menu, X } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import SurfaceToggle from '../../components/SurfaceToggle';
import PersonaModal from '../../components/PersonaModal';
import { BreadcrumbTrail } from '../components/BreadcrumbTrail';
import { usePersona } from '../../contexts/PersonaContext';
import { getPersonaPhoto } from '../../data/personaPhotos';
import { PresencePill } from '../../shared';

/* -----------------------------------------------------------------------
 * Route → breadcrumb mapping
 * ----------------------------------------------------------------------- */

/** Prettify a route segment into a human-readable breadcrumb label. */
function prettifySegment(segment: string): string {
  // Known labels
  const labels: Record<string, string> = {
    atelier: 'Atelier',
    'proof-board': 'Proof Board',
    'audit-proof': 'Audit Proof',
    sessions: 'Sessions',
    observatory: 'Observatory',
    'persona-journeys': 'Persona Journeys',
    architecture: 'Architecture Brief',
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
    const parts = pathname
      .split('/')
      .filter(Boolean)
      .map(prettifySegment);

    // Always start with "Atelier" — it's the root
    if (parts.length === 0) return ['Atelier'];
    return parts;
  }, [pathname]);
}

/* -----------------------------------------------------------------------
 * TopBar component
 * ----------------------------------------------------------------------- */

export interface TopBarProps {
  /** True when the responsive navigation drawer is open. */
  navOpen?: boolean;
  /** Toggle the drawer. Rendered only at drawer widths (see base.css). */
  onToggleNav?: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ navOpen = false, onToggleNav }) => {
  const breadcrumbs = useBreadcrumbs();
  const { persona } = usePersona();
  const [personaModalOpen, setPersonaModalOpen] = useState(false);

  const avatarInitial = persona?.avatar_initial ?? '?';
  const avatarColor = persona?.avatar_color ?? '#665f58';
  const personaLabel = persona?.display_name?.split(' ')[0] ?? 'Choose profile';

  return (
    <>
      <header
        data-testid="atelier-topbar"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          padding: '12px 24px',
          borderBottom: '1px solid var(--at-rule-1)',
          background: 'var(--at-cream-1)',
          minHeight: '52px',
        }}
      >
        {/* Navigation drawer toggle. CSS hides it at widths where the rail
            is already visible, so it never duplicates present navigation. */}
        {onToggleNav && (
          <button
            type="button"
            className="atelier-nav-toggle gov-focusable"
            data-testid="atelier-nav-toggle"
            onClick={onToggleNav}
            aria-label={navOpen ? 'Close lab navigation' : 'Open lab navigation'}
            aria-expanded={navOpen}
            style={{
              alignItems: 'center',
              justifyContent: 'center',
              width: '40px',
              height: '40px',
              border: '1px solid var(--at-rule-2)',
              borderRadius: 'var(--gov-radius-sm)',
              background: 'var(--at-cream-elev)',
              color: 'var(--at-ink-1)',
              cursor: 'pointer',
            }}
          >
            {navOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        )}

        {/* Surface toggle */}
        <SurfaceToggle />

        {/* Breadcrumb trail */}
        <BreadcrumbTrail segments={breadcrumbs} />

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Presence — the Atelier is an operator surface, so it reports the
            evidence/environment state rather than the shopper-facing one.
            Passing surface="boutique" here mislabelled the whole console. */}
        <PresencePill surface="atelier" personaId={persona?.id} />

        {/* Persona switcher */}
        <button
          type="button"
          data-testid="atelier-persona-switcher"
          onClick={() => setPersonaModalOpen(true)}
          aria-label={`Switch persona${persona?.display_name ? ` from ${persona.display_name}` : ''}`}
          title="Switch persona"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '9px',
            padding: '4px 9px 4px 4px',
            border: '1px solid var(--at-rule-1)',
            borderRadius: '999px',
            background: 'var(--at-cream-2)',
            color: 'var(--at-ink-1)',
            cursor: 'pointer',
          }}
        >
          {(() => {
            const photoUrl = persona ? getPersonaPhoto(persona.id) : undefined;
            return photoUrl ? (
              <img
                src={photoUrl}
                alt=""
                aria-hidden="true"
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  objectFit: 'cover',
                  flexShrink: 0,
                  border: '1.5px solid rgba(31, 20, 16, 0.1)',
                }}
              />
            ) : (
              <span
                aria-hidden="true"
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: avatarColor,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: 'var(--at-sans)',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#fff',
                  flexShrink: 0,
                }}
              >
                {avatarInitial}
              </span>
            );
          })()}
          <span
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              lineHeight: 1.1,
            }}
          >
            <span
              style={{
                fontFamily: 'var(--at-heading)',
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: 'var(--at-ink-4)',
              }}
            >
              Persona
            </span>
            <span
              style={{
                fontFamily: 'var(--at-sans)',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--at-ink-1)',
              }}
            >
              {personaLabel}
            </span>
          </span>
        </button>
      </header>
      <PersonaModal open={personaModalOpen} onClose={() => setPersonaModalOpen(false)} />
    </>
  );
};

export default TopBar;
