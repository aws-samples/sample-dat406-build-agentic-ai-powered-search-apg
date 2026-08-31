/**
 * Full-width Pellier Observatory shell for live agent inspection.
 */

import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import TopBar from './TopBar';
import ObservatoryContextBanner from './ObservatoryContextBanner';
import ObservatoryModeBanner from './ObservatoryModeBanner';
import ObservatoryErrorBoundary from './ObservatoryErrorBoundary';
import { interactionForPath } from './observatoryInteraction';
import '../styles/base.css';

const ObservatoryFrame: React.FC = () => {
  // Key the error boundary on the pathname so a crash on one surface doesn't
  // strand the operator on every other surface — navigating remounts it,
  // clearing stale error state.
  const { pathname } = useLocation();

  return (
    <div className="observatory-root pellier-page-surface">
      <div className="observatory-frame">
        <div className="observatory-canvas">
          <TopBar />
          <ObservatoryContextBanner />
          <main
            className="observatory-surface"
            data-mode={interactionForPath(pathname)}
            data-workbench={
              pathname === '/observatory/workbench' ||
              pathname.startsWith('/observatory/workbench/')
                ? 'true'
                : 'false'
            }
          >
            <ObservatoryModeBanner />
            <ObservatoryErrorBoundary key={pathname}>
              <Outlet />
            </ObservatoryErrorBoundary>
          </main>
        </div>
      </div>
    </div>
  );
};

export default ObservatoryFrame;
