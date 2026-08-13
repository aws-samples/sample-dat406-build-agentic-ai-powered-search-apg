/**
 * AgentTraceFrame — Root layout shell for Pellier Labs Observatory.
 *
 * Renders a 240px sidebar + flexible canvas grid. The canvas area
 * contains the TopBar and a React Router `<Outlet />` for nested
 * route rendering.
 *
 * Requirements: 1.1, 20.1
 */

import React, { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import AgentTraceErrorBoundary from './AgentTraceErrorBoundary';
import '../styles/base.css';

const AgentTraceFrame: React.FC = () => {
  // Key the error boundary on the pathname so a crash on one surface doesn't
  // strand the operator on every other surface — navigating remounts it,
  // clearing stale error state.
  const { pathname } = useLocation();
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);

  useEffect(() => {
    setMobileNavigationOpen(false);
  }, [pathname]);

  return (
    <div className="agent-trace-root">
      <div className="agent-trace-frame">
        <button
          type="button"
          className="labs-sidebar-scrim"
          data-open={mobileNavigationOpen ? 'true' : 'false'}
          aria-label="Close Pellier Labs navigation"
          onClick={() => setMobileNavigationOpen(false)}
        />
        <Sidebar
          mobileOpen={mobileNavigationOpen}
          onClose={() => setMobileNavigationOpen(false)}
        />
        <div className="agent-trace-canvas">
          <TopBar onOpenNavigation={() => setMobileNavigationOpen(true)} />
          <main className="agent-trace-surface">
            <AgentTraceErrorBoundary key={pathname}>
              <Outlet />
            </AgentTraceErrorBoundary>
          </main>
        </div>
      </div>
    </div>
  );
};

export default AgentTraceFrame;
