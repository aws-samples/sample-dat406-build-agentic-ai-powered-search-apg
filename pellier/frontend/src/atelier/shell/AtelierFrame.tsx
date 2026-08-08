/**
 * AtelierFrame — Root layout shell for the Atelier Observatory.
 *
 * A 300px navigation rail + flexible canvas grid at desktop width. The rail
 * becomes a compact icon strip between 1024px and 1279px, and an off-canvas
 * drawer below 1024px (see `atelier/styles/base.css`). The canvas contains
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
import AtelierContextBanner from './AtelierContextBanner';
import AtelierErrorBoundary from './AtelierErrorBoundary';
import { useUI } from '../../contexts/UIContext';
import '../styles/base.css';
import AtelierSpotlight from '../../components/AtelierSpotlight';

const AtelierFrame: React.FC = () => {
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
    <div className="atelier-root" data-nav-open={navOpen ? 'true' : 'false'}>
      <div className="atelier-frame">
        <Sidebar />
        <div className="atelier-canvas">
          <TopBar
            navOpen={navOpen}
            onToggleNav={() => setNavOpen((open) => !open)}
          />
          <AtelierContextBanner />
          <main className="atelier-surface">
            <AtelierErrorBoundary key={pathname}>
              <Outlet />
            </AtelierErrorBoundary>
          </main>
        </div>
      </div>
      {/* Scrim. Rendered only in drawer mode via CSS, but the click target
          needs to exist in the DOM to be dismissible by pointer. */}
      {navOpen && (
        <button
          type="button"
          className="atelier-nav-scrim"
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
      {/* First-visit orientation for the evidence surface. Session-gated. */}
      <AtelierSpotlight />
    </div>
  );
};

export default AtelierFrame;
