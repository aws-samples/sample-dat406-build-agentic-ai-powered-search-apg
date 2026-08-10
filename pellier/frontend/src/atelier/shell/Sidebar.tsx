/**
 * Sidebar — Espresso-colored left navigation for the Atelier Observatory.
 *
 * Workshop-first left navigation for Atelier.
 *
 * The broader Atelier routes still exist for deep links and reference tests,
 * but the sidebar only advertises surfaces the governed lab asks
 * participants to open. Atelier should read as an observation surface, not a
 * second app to wander through.
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.13
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { usePersona } from '../../contexts/PersonaContext';
import { useBuildState } from '../hooks/useBuildState';
import { StatusDot } from '../components/StatusDot';

/* -----------------------------------------------------------------------
 * Nav item definitions
 * ----------------------------------------------------------------------- */

interface NavItemDef {
  label: string;
  path: string;
  anchor?: string;
  badge?: string;
  liveDot?: boolean;
}

interface NavSection {
  eyebrow: string;
  items: NavItemDef[];
  /** Lab number for numbered progress. Omitted for Cockpit/Deep Dives. */
  labNumber?: number;
  /** Collapsed by default; only the active lab expands. */
  collapsible?: boolean;
}

/**
 * Lab completion state.
 *
 * `complete` is only claimed from real build-state evidence — a lab that
 * merely has a visited route is not a lab an attendee finished.
 */
type LabStatus = 'not-started' | 'in-progress' | 'complete' | 'optional';

const STATUS_LABEL: Record<LabStatus, string> = {
  'not-started': 'Not started',
  'in-progress': 'In progress',
  complete: 'Complete',
  optional: 'Optional',
};

/** True when the current route belongs to this section. */
function isSectionActive(section: NavSection, pathname: string): boolean {
  return section.items.some((item) => {
    const base = item.path.split('#', 1)[0];
    const target = `/atelier/${base}`;
    return pathname === target || pathname.startsWith(`${target}/`);
  });
}

/**
 * Resolve a lab's status from real evidence.
 *
 * Only Lab 1 can currently be proven complete: the build-state endpoint
 * reports how many tools are shipped, which is a fact. The other labs have
 * no completion signal in the app, so they report `in-progress` while the
 * attendee is on them and `not-started` otherwise. Claiming `complete`
 * without evidence would be the same dishonesty the evidence surfaces
 * exist to prevent.
 */
function labStatus(
  section: NavSection,
  active: boolean,
  buildState: { toolShipped: number; toolTotal: number },
): LabStatus {
  if (section.labNumber === 1) {
    if (buildState.toolTotal > 0 && buildState.toolShipped >= buildState.toolTotal) {
      return 'complete';
    }
    return active ? 'in-progress' : 'not-started';
  }
  return active ? 'in-progress' : 'not-started';
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

const Sidebar: React.FC = () => {
  const { persona } = usePersona();
  const buildState = useBuildState();
  const { pathname } = useLocation();

  const personaId = persona?.id ?? '';
  const displayName = persona?.display_name ?? 'Choose profile';
  const roleTag = persona?.role_tag ?? 'NO ACTIVE SHOPPER';
  const avatarInitial = persona?.avatar_initial ?? '?';
  const avatarColor = persona?.avatar_color ?? '#665f58';

  // Four-lab spine. The audit's finding was that seven groups with twelve
  // near-equal destinations made the Atelier read as a second application
  // to learn. These four consolidate the same surfaces:
  //
  //   Lab 1  Build & Trace      tool registry + one live trace
  //   Lab 2  Retrieval Quality  search pipeline + retrieval comparison
  //   Lab 3  Memory & Audit     memory substrates + audit proof
  //   Lab 4  Govern Actions     gateway, policy, write path
  //
  // Every previous route stays reachable — Deep Dives keeps them as deep
  // links. Nothing was deleted; only the default presentation changed.
  const navSections: NavSection[] = [
    {
      eyebrow: 'COCKPIT',
      items: [
        { label: 'Proof Board', path: 'proof-board', liveDot: true },
        { label: 'Workshop Map', path: 'observatory' },
      ],
    },
    {
      eyebrow: 'BUILD & TRACE',
      labNumber: 1,
      collapsible: true,
      items: [
        {
          // No hardcoded count fallback. This badge is the primary signal
          // that the floor_check exercise landed (14/15 -> 15/15), so a
          // stale literal reads as a confident "not wired yet" when the
          // truth is "build state unavailable" — indistinguishable from the
          // pre-exercise state, on the one number a participant watches.
          // An em-dash says "unknown" honestly.
          label: 'Tool Registry',
          path: 'tools',
          badge: buildState.toolTotal > 0
            ? `${buildState.toolShipped}/${buildState.toolTotal}`
            : '—',
        },
        { label: 'Sessions', path: 'sessions' },
      ],
    },
    {
      eyebrow: 'RETRIEVAL QUALITY',
      labNumber: 2,
      collapsible: true,
      items: [
        { label: 'Retrieval Comparison', path: 'performance' },
        { label: 'Search Pipeline', path: 'search' },
      ],
    },
    {
      eyebrow: 'MEMORY & AUDIT',
      labNumber: 3,
      collapsible: true,
      items: [
        { label: 'Memory Substrates', path: 'memory' },
        { label: 'Audit Proof', path: 'audit-proof' },
      ],
    },
    {
      eyebrow: 'GOVERN ACTIONS',
      labNumber: 4,
      collapsible: true,
      items: [
        { label: 'Gateway & Policy', path: 'write-path' },
        { label: 'Managed Rail', path: 'proof-board#managed-rail' },
      ],
    },
    {
      eyebrow: 'DEEP DIVES',
      collapsible: true,
      items: [
        { label: 'Agent Behavior & Routing', path: 'routing' },
        { label: 'Architecture', path: 'architecture' },
        { label: 'Evaluations', path: 'evaluations' },
        { label: 'Production Patterns', path: 'production-patterns' },
        { label: 'Persona Journeys', path: 'persona-journeys' },
        { label: 'Skills', path: 'skills' },
      ],
    },
  ];

  return (
    <aside
      data-testid="atelier-sidebar"
      className="atelier-sidebar"
      style={{
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
          {/* Pellier wordmark glyph — matches Boutique footer / header circular P */}
          P
        </div>
        <span
          className="font-display text-xl font-medium tracking-tight"
          style={{
            color: 'var(--at-sidebar-text-active)',
          }}
        >
          Pellier
        </span>
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
        {navSections.map((section) => {
          const sectionActive = isSectionActive(section, pathname);
          // Only the active lab stays expanded. A fully expanded rail is
          // what made twelve destinations compete for attention; collapsing
          // the rest keeps the current step obvious without hiding any.
          const expanded = !section.collapsible || sectionActive;
          const status = section.labNumber
            ? labStatus(section, sectionActive, buildState)
            : undefined;

          return (
            <div key={section.eyebrow} style={{ marginBottom: '4px' }}>
              {/* Section eyebrow. Numbered for labs so progress reads as a
                  sequence rather than a list of red markers. */}
              <div
                data-nav-eyebrow
                data-section-active={sectionActive ? 'true' : 'false'}
                style={{
                  padding: '12px 20px 6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontFamily: 'var(--at-heading)',
                  fontSize: '11px',
                  fontWeight: 600,
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  color: sectionActive
                    ? 'var(--at-sidebar-text-active)'
                    : 'rgba(250, 243, 232, 0.6)',
                  lineHeight: 1,
                }}
              >
                {section.labNumber ? (
                  <span
                    aria-hidden="true"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      border: `1px solid ${
                        status === 'complete'
                          ? 'var(--gov-allow-fg)'
                          : 'rgba(250, 243, 232, 0.45)'
                      }`,
                      color:
                        status === 'complete'
                          ? 'var(--gov-allow-fg)'
                          : 'inherit',
                      fontSize: '9px',
                      flexShrink: 0,
                    }}
                  >
                    {section.labNumber}
                  </span>
                ) : (
                  <span
                    aria-hidden="true"
                    style={{
                      display: 'inline-block',
                      width: '5px',
                      height: '5px',
                      borderRadius: '50%',
                      backgroundColor: 'rgba(250, 243, 232, 0.5)',
                      flexShrink: 0,
                    }}
                  />
                )}
                <span style={{ flex: 1 }}>
                  {section.labNumber ? `LAB ${section.labNumber} · ` : ''}
                  {section.eyebrow}
                </span>
                {/* Status is text, never color alone. */}
                {status && (
                  <span
                    style={{
                      fontFamily: 'var(--at-mono)',
                      fontSize: '9px',
                      letterSpacing: '0.04em',
                      color:
                        status === 'complete'
                          ? 'var(--gov-allow-fg)'
                          : 'rgba(250, 243, 232, 0.5)',
                    }}
                  >
                    {STATUS_LABEL[status]}
                  </span>
                )}
              </div>

              {/* Nav items */}
              {expanded &&
                section.items.map((item) => (
                  <SidebarNavItem key={item.path} item={item} />
                ))}
            </div>
          );
        })}

      </nav>

      {/* Persona footer. `data-sidebar-footer` lets the compact rail drop it;
          the persona switcher in the TopBar remains the canonical control,
          so hiding this duplicate costs nothing. */}
      <div
        data-sidebar-footer
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
              fontFamily: 'var(--at-heading)',
              fontSize: '16px',
              fontWeight: 600,
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
              fontFamily: 'var(--at-heading)',
              fontSize: '11px',
              fontWeight: 600,
              letterSpacing: '0.06em',
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

const SidebarNavItem: React.FC<{ item: NavItemDef }> = ({ item }) => {
  const { pathname, hash } = useLocation();
  const itemPath = item.path.split('#', 1)[0];
  const targetPath = `/atelier/${itemPath}`;
  const routeIsActive = pathname === targetPath
    || (
      itemPath !== 'sessions'
      && itemPath !== 'architecture'
      && pathname.startsWith(`${targetPath}/`)
    );
  const isActive = item.anchor
    ? routeIsActive && hash === `#${item.anchor}`
    : routeIsActive && !(itemPath === 'proof-board' && hash);

  return (
    <Link
      to={`/atelier/${item.path}`}
      // The compact rail hides the visible label, so the link carries its
      // own accessible name. Without this an icon-only rail is a row of
      // unnamed links to a screen reader.
      aria-label={item.label}
      aria-current={isActive ? 'page' : undefined}
      className="gov-focusable"
      style={{
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
      }}
    >
      {/* data-nav-label lets the compact icon rail hide the text while the
          link keeps its accessible name (aria-label below). */}
      <span data-nav-label style={{ flex: 1 }}>
        {item.label}
      </span>

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
    </Link>
  );
};

export default Sidebar;
