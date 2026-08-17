/**
 * Sidebar — Espresso-colored left navigation for Pellier Labs Observatory.
 *
 * Three sections (OBSERVE, UNDERSTAND, EVALUATE), a Settings divider,
 * and a persona footer. Uses React Router `<NavLink>` for active state
 * highlighting (espresso-2 bg, 2px burgundy accent bar, full-opacity icon).
 *
 * UNDERSTAND items follow the learning arc:
 *   Architecture (the map) → Agents (the characters) →
 *   Skills (persona-specific knowledge) → Tools (what they reach for) →
 *   Routing (how requests find them) → Memory (what persists between turns).
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.13
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { X } from 'lucide-react';
import { usePersona } from '../../contexts/PersonaContext';
import { useBuildState } from '../hooks/useBuildState';
import { StatusDot } from '../components/StatusDot';

/* -----------------------------------------------------------------------
 * Nav item definitions
 * ----------------------------------------------------------------------- */

interface NavItemDef {
  label: string;
  path: string;
  badge?: string;
  liveDot?: boolean;
}

interface NavSection {
  eyebrow: string;
  items: NavItemDef[];
}

/* -----------------------------------------------------------------------
 * Persona headshot photos — Unsplash free-to-use portraits. Each URL
 * points to a 200×200 crop so the sidebar avatar renders a real face.
 * Falls back to the colored-initial circle when no photo is mapped.
 * ----------------------------------------------------------------------- */

// Shared persona photos from data/personaPhotos.ts
import { PERSONA_PHOTOS } from '../../data/personaPhotos';

/* -----------------------------------------------------------------------
 * Sidebar component
 * ----------------------------------------------------------------------- */

const Sidebar: React.FC<{
  mobileOpen?: boolean;
  onClose?: () => void;
}> = ({ mobileOpen = false, onClose }) => {
  const { persona } = usePersona();
  const buildState = useBuildState();
  const [mobileViewport, setMobileViewport] = React.useState(false);
  const sidebarRef = React.useRef<HTMLElement | null>(null);

  React.useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const query = window.matchMedia('(max-width: 900px)');
    const update = () => setMobileViewport(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  React.useEffect(() => {
    if (!sidebarRef.current) return;
    const sidebar = sidebarRef.current as HTMLElement & { inert: boolean };
    sidebar.inert = mobileViewport && !mobileOpen;
    return () => {
      sidebar.inert = false;
    };
  }, [mobileOpen, mobileViewport]);

  const personaId = persona?.id ?? 'fresh';
  const displayName = persona?.display_name ?? 'Marco';
  const roleTag = persona?.role_tag ?? 'RETURNING CUSTOMER';
  const avatarInitial = persona?.avatar_initial ?? 'M';
  const avatarColor = persona?.avatar_color ?? '#a8423a';

  // Build dynamic, product-oriented sections with live shipped/total badges.
  // Workshop guides can deep-link to any route without encoding their lab
  // sequence into the shared application shell.
  const navSections: NavSection[] = [
    {
      eyebrow: 'EVIDENCE',
      items: [
        { label: 'Inspection Workbench', path: '', liveDot: true },
        { label: 'Observatory', path: 'observatory' },
        { label: 'Sessions', path: 'sessions' },
      ],
    },
    {
      eyebrow: 'SYSTEM',
      items: [
        {
          label: 'Agents',
          path: 'agents',
          // No hardcoded count fallback. The Tools badge is the primary
          // signal that the floor_check exercise landed (14/15 -> 15/15), so
          // a stale literal here reads as a confident "not wired yet" when
          // the truth is "build state unavailable" — indistinguishable from
          // the pre-exercise state, on the one number a participant is told
          // to watch. An em-dash says "unknown" honestly.
          badge: buildState.agentTotal > 0
            ? `${buildState.agentShipped}/${buildState.agentTotal}`
            : '—',
        },
        { label: 'Skills', path: 'skills', badge: '5' },
        {
          label: 'Tools',
          path: 'tools',
          badge: buildState.toolTotal > 0
            ? `${buildState.toolShipped}/${buildState.toolTotal}`
            : '—',
        },
      ],
    },
    {
      eyebrow: 'RETRIEVAL & QUALITY',
      items: [
        { label: 'Search', path: 'search' },
        { label: 'Performance', path: 'performance' },
        { label: 'Evaluations', path: 'evaluations' },
      ],
    },
    {
      eyebrow: 'PRODUCTION',
      items: [
        { label: 'Routing', path: 'routing', badge: '3' },
        { label: 'Memory', path: 'memory' },
        { label: 'Write-path', path: 'write-path' },
        { label: 'Production Patterns', path: 'production-patterns', badge: '4' },
      ],
    },
    {
      eyebrow: 'REFERENCE',
      items: [
        { label: 'Persona Journeys', path: 'persona-journeys' },
      ],
    },
  ];

  return (
    <aside
      ref={sidebarRef}
      className="agent-trace-sidebar"
      data-testid="agent-trace-sidebar"
      data-mobile-open={mobileOpen ? 'true' : 'false'}
      aria-label="Pellier Labs navigation"
      aria-hidden={mobileViewport && !mobileOpen ? true : undefined}
      style={{
        width: 'var(--at-sidebar-width)',
        minHeight: '100vh',
        background: 'var(--at-sidebar-bg)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Brand row */}
      <div
        style={{
          padding: '20px 20px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}
      >
        <div
          className="pellier-logo-chip"
          style={{
            background: 'var(--at-espresso-2)',
            color: 'var(--at-sidebar-text-active)',
            boxShadow: 'inset 0 0 0 1px rgba(251, 248, 242, 0.12)',
          }}
        >
          {/* Pellier wordmark glyph - matches the storefront brand mark. */}
          P
        </div>
        <span
          className="font-display text-xl font-medium tracking-tight"
          style={{
            color: 'var(--at-sidebar-text-active)',
          }}
        >
          Pellier Labs
        </span>
        <button
          type="button"
          className="labs-sidebar-close"
          aria-label="Close Pellier Labs navigation"
          title="Close Pellier Labs navigation"
          onClick={onClose}
        >
          <X size={18} strokeWidth={1.8} aria-hidden="true" />
        </button>
      </div>

      {/* Navigation sections */}
      <nav
        style={{
          flex: 1,
          padding: '0 0 8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          overflowY: 'auto',
        }}
      >
        {navSections.map((section) => (
          <div key={section.eyebrow} style={{ marginBottom: '4px' }}>
            {/* Section eyebrow */}
            <div
              style={{
                padding: '12px 20px 6px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontFamily: 'var(--at-mono)',
                fontSize: '11px',
                fontWeight: 500,
                letterSpacing: 'var(--at-eyebrow-tracking)',
                textTransform: 'uppercase',
                color: 'var(--at-red-1)',
                lineHeight: 1,
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  display: 'inline-block',
                  width: '5px',
                  height: '5px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--at-red-1)',
                  flexShrink: 0,
                }}
              />
              {section.eyebrow}
            </div>

            {/* Nav items */}
            {section.items.map((item) => (
              <SidebarNavItem key={item.path} item={item} onNavigate={onClose} />
            ))}
          </div>
        ))}

        {/* Divider */}
        <div
          style={{
            margin: '8px 20px',
            height: '1px',
            background: 'rgba(250, 243, 232, 0.12)',
          }}
        />

        {/* Settings */}
        <SidebarNavItem
          item={{ label: 'Settings', path: 'settings' }}
          onNavigate={onClose}
        />
      </nav>

      {/* Persona footer */}
      <div
        style={{
          padding: '16px 20px',
          borderTop: '1px solid rgba(250, 243, 232, 0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        {PERSONA_PHOTOS[personaId] ? (
          <img
            src={PERSONA_PHOTOS[personaId]}
            alt={displayName}
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              objectFit: 'cover',
              flexShrink: 0,
              border: '2px solid rgba(250, 243, 232, 0.15)',
            }}
          />
        ) : (
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: avatarColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: 'var(--at-sans)',
              fontSize: '17px',
              fontWeight: 600,
              color: '#fff',
              flexShrink: 0,
            }}
          >
            {avatarInitial}
          </div>
        )}
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontFamily: 'var(--at-serif)',
              fontSize: '16px',
              color: 'var(--at-sidebar-text-active)',
              lineHeight: 1.2,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {displayName}
          </div>
          <div
            style={{
              fontFamily: 'var(--at-mono)',
              fontSize: '11px',
              fontWeight: 500,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: 'var(--at-sidebar-text)',
              lineHeight: 1,
              marginTop: '3px',
            }}
          >
            {roleTag}
          </div>
        </div>
      </div>
    </aside>
  );
};

/* -----------------------------------------------------------------------
 * SidebarNavItem — single nav link with active state
 * ----------------------------------------------------------------------- */

const SidebarNavItem: React.FC<{
  item: NavItemDef;
  onNavigate?: () => void;
}> = ({ item, onNavigate }) => {
  const target = item.path ? `/pellier-labs/${item.path}` : '/pellier-labs';
  return (
    <NavLink
      to={target}
      onClick={onNavigate}
      end={
        item.path === ''
        || item.path === 'sessions'
        || item.path === 'architecture'
      }
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '8px 20px',
        margin: '0 8px',
        borderRadius: '6px',
        textDecoration: 'none',
        fontFamily: 'var(--at-sans)',
        fontSize: '15px',
        fontWeight: isActive ? 500 : 400,
        color: isActive
          ? 'var(--at-sidebar-text-active)'
          : 'var(--at-sidebar-text)',
        background: isActive ? 'var(--at-sidebar-active-bg)' : 'transparent',
        borderLeft: isActive
          ? '2px solid var(--at-sidebar-accent)'
          : '2px solid transparent',
        transition: 'background 0.15s, color 0.15s',
        position: 'relative',
      })}
    >
      <span style={{ flex: 1 }}>{item.label}</span>

      {item.liveDot && (
        <StatusDot status="live" size={7} />
      )}

      {item.badge && !item.liveDot && (
        <span
          style={{
            fontFamily: 'var(--at-mono)',
            fontSize: '12px',
            fontWeight: 500,
            color: 'var(--at-sidebar-text)',
            opacity: 0.7,
          }}
        >
          {item.badge}
        </span>
      )}
    </NavLink>
  );
};

export default Sidebar;
