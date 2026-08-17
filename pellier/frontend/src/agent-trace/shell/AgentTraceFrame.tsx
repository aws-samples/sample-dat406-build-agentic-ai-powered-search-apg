/**
 * Full-width Pellier Labs shell for live agent inspection.
 */

import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import TopBar from './TopBar';
import AgentTraceContextBanner from './AgentTraceContextBanner';
import LabsModeBanner from './LabsModeBanner';
import AgentTraceErrorBoundary from './AgentTraceErrorBoundary';
import { interactionForPath } from './labsInteraction';
import { useUI } from '../../contexts/UIContext';
import '../styles/base.css';

const AgentTraceFrame: React.FC = () => {
  const { setChatSurface } = useUI();

  useEffect(() => {
    setChatSurface('concierge');
  }, [setChatSurface]);

  // Key the error boundary on the pathname so a crash on one surface doesn't
  // strand the operator on every other surface — navigating remounts it,
  // clearing stale error state.
  const { pathname } = useLocation();

  return (
    <div className="agent-trace-root pellier-page-surface">
      <div className="agent-trace-frame">
        <div className="agent-trace-canvas">
          <TopBar />
          <AgentTraceContextBanner />
          <main
            className="agent-trace-surface"
            data-mode={interactionForPath(pathname)}
            data-workbench={
              pathname === '/pellier-labs' || pathname === '/pellier-labs/'
                ? 'true'
                : 'false'
            }
          >
            <LabsModeBanner />
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
