/**
 * Full-width Pellier Labs shell for live agent inspection.
 */

import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useUI } from '../../contexts/UIContext';
import TopBar from './TopBar';
import AgentTraceErrorBoundary from './AgentTraceErrorBoundary';
import '../styles/base.css';

const AgentTraceFrame: React.FC = () => {
  const { setChatSurface } = useUI();
  const { pathname } = useLocation();

  useEffect(() => {
    setChatSurface('concierge');
  }, [setChatSurface]);

  return (
    <div className="agent-trace-root">
      <div className="agent-trace-frame">
        <div className="agent-trace-canvas">
          <TopBar />
          <main
            className="agent-trace-surface"
            data-workbench={
              pathname === '/pellier-labs' || pathname === '/pellier-labs/'
                ? 'true'
                : 'false'
            }
          >
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
