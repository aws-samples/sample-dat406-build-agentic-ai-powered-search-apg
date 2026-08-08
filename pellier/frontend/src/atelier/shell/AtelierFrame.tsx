/**
 * AtelierFrame — Root layout shell for the Atelier Observatory.
 *
 * Renders a 440px sidebar + flexible canvas grid. The canvas area
 * contains the TopBar and a React Router `<Outlet />` for nested
 * route rendering.
 *
 * Requirements: 1.1, 20.1
 */

import React, { useEffect } from 'react';
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

  useEffect(() => {
    setChatSurface('concierge');
  }, [setChatSurface]);

  // Key the error boundary on the pathname so a crash on one surface doesn't
  // strand the operator on every other surface — navigating remounts it,
  // clearing stale error state.
  const { pathname } = useLocation();
  return (
    <div className="atelier-root">
      <div className="atelier-frame">
        <Sidebar />
        <div className="atelier-canvas">
          <TopBar />
          <AtelierContextBanner />
          <main className="atelier-surface">
            <AtelierErrorBoundary key={pathname}>
              <Outlet />
            </AtelierErrorBoundary>
          </main>
        </div>
      </div>
      {/* First-visit orientation for the evidence surface. Session-gated. */}
      <AtelierSpotlight />
    </div>
  );
};

export default AtelierFrame;
