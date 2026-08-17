/**
 * Full-width Pellier Labs shell for live agent inspection.
 */

import React, { useLayoutEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useUI } from '../../contexts/UIContext';
import TopBar from './TopBar';
import LabsModeBanner from './LabsModeBanner';
import AgentTraceErrorBoundary from './AgentTraceErrorBoundary';
import { interactionForPath } from './labsInteraction';
import '../styles/base.css';

const AgentTraceFrame: React.FC = () => {
  const { activeModal, closeModal, setChatSurface } = useUI();
  const { pathname } = useLocation();

  useLayoutEffect(() => {
    setChatSurface('none');
    if (
      activeModal === 'concierge' ||
      activeModal === 'drawer' ||
      activeModal === 'comparison'
    ) {
      closeModal();
    }
  }, [activeModal, closeModal, setChatSurface]);

  return (
    <div className="agent-trace-root pellier-page-surface">
      <div className="agent-trace-frame">
        <div className="agent-trace-canvas">
          <TopBar />
          <main
            className="agent-trace-surface"
            /* data-mode lets any surface style itself against the contract
               without importing the module or duplicating the path list. */
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
