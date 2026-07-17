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

  const personaId = persona?.id ?? '';
  const displayName = persona?.display_name ?? 'Choose profile';
  const roleTag = persona?.role_tag ?? 'NO ACTIVE SHOPPER';
  const avatarInitial = persona?.avatar_initial ?? '?';
  const avatarColor = persona?.avatar_color ?? '#665f58';

  // Keep the same four-lab spine as Workshop Studio. Reference-only routes
  // remain deep-linkable without competing with the required participant path.
  const navSections: NavSection[] = [
    {
      eyebrow: 'START HERE',
      items: [
        { label: 'Proof Board', path: 'proof-board', liveDot: true },
      ],
    },
    {
      eyebrow: 'CORE LAB 1 · BUILD AND TRACE',
      items: [
        {
          label: 'Tool Registry',
          path: 'tools',
          badge: buildState.toolTotal > 0
            ? `${buildState.toolShipped}/${buildState.toolTotal}`
            : '14/15',
        },
      ],
    },
    {
      eyebrow: 'CORE LAB 2 · MEASURE RETRIEVAL',
      items: [
        { label: 'Retrieval Comparison', path: 'performance' },
      ],
    },
    {
      eyebrow: 'CORE LAB 3 · QUERY EVIDENCE',
      items: [
        {
          label: 'Audit Proof',
          path: 'audit-proof',
        },
        { label: 'Memory', path: 'memory', badge: 'opt' },
      ],
    },
    {
      eyebrow: 'CORE LAB 4 · ENFORCE POLICY',
      items: [
        { label: 'Gateway & Policy', path: 'write-path' },
      ],
    },
    {
      eyebrow: 'OPTIONAL LABS',
      items: [
        { label: 'Routing Patterns', path: 'routing', badge: 'opt' },
      ],
    },
    {
      eyebrow: 'REFERENCE',
      items: [
        { label: 'Workshop Map', path: 'observatory' },
        { label: 'Sessions', path: 'sessions' },
        { label: 'Search Pipeline', path: 'search' },
        { label: 'Architecture', path: 'architecture' },
      ],
    },
  ];

  return (
    <aside
      data-testid="atelier-sidebar"
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
        {navSections.map((section) => (
          <div key={section.eyebrow} style={{ marginBottom: '4px' }}>
            {/* Section eyebrow */}
            <div
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
              <SidebarNavItem key={item.path} item={item} />
            ))}
          </div>
        ))}

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
      aria-current={isActive ? 'page' : undefined}
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
    </Link>
  );
};

export default Sidebar;
