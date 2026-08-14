/**
 * AgentTraceFrame — Root layout shell for the Agent Trace Observatory.
 *
 * A 300px navigation rail + flexible canvas grid at desktop width. The rail
 * becomes a compact icon strip between 1024px and 1279px, and an off-canvas
 * drawer below 1024px (see `agent-trace/styles/base.css`). The canvas contains
 * the TopBar and a React Router `<Outlet />` for nested routes.
 *
 * Drawer state lives here rather than in the Sidebar because two siblings
 * need it: the toggle in the TopBar and the rail itself. It is deliberately
 * component state, not a URL parameter — a shared receipt link should not
 * reopen someone else's navigation drawer.
 *
 * Requirements: 1.1, 20.1
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import AgentTraceContextBanner from './AgentTraceContextBanner';
import AgentTraceErrorBoundary from './AgentTraceErrorBoundary';
import { useUI } from '../../contexts/UIContext';
import '../styles/base.css';

const AgentTraceFrame: React.FC = () => {
  const { setChatSurface } = useUI();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    setChatSurface('concierge');
  }, [setChatSurface]);

  // Key the error boundary on the pathname so a crash on one surface doesn't
  // strand the operator on every other surface — navigating remounts it,
  // clearing stale error state.
  const { pathname } = useLocation();

  // Navigating closes the drawer. Leaving it open over the destination the
  // attendee just chose is the classic mobile-nav annoyance.
  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  // Escape closes the drawer, matching every other dismissible surface here.
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setNavOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navOpen]);

  const closeNav = useCallback(() => setNavOpen(false), []);

  return (
    <div className="agent-trace-root" data-nav-open={navOpen ? 'true' : 'false'}>
      <div className="agent-trace-frame">
        <Sidebar />
        <div className="agent-trace-canvas">
          <TopBar
            navOpen={navOpen}
            onToggleNav={() => setNavOpen((open) => !open)}
          />
          <AgentTraceContextBanner />
          <main className="agent-trace-surface">
            <AgentTraceErrorBoundary key={pathname}>
              <Outlet />
            </AgentTraceErrorBoundary>
          </main>
        </div>
      </div>
      {/* Scrim. Rendered only in drawer mode via CSS, but the click target
          needs to exist in the DOM to be dismissible by pointer. */}
      {navOpen && (
        <button
          type="button"
          className="agent-trace-nav-scrim"
          aria-label="Close navigation"
          onClick={closeNav}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 56,
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
          }}
        />
      )}
    </div>
  );
};

export default AgentTraceFrame;
