/**
 * States whether the current Labs view can be operated or only inspected.
 */

import React from 'react';
import { useLocation } from 'react-router-dom';

import { interactionForPath, modeCopyForPath } from './labsInteraction';

const LabsModeBanner: React.FC = () => {
  const { pathname } = useLocation();
  const mode = interactionForPath(pathname);
  const copy = modeCopyForPath(pathname);

  return (
    <div className="labs-mode-banner" data-mode={mode}>
      <span className="labs-mode-banner-label">
        {mode === 'interactive' ? (
          <span className="labs-mode-banner-dot" aria-hidden="true" />
        ) : null}
        {copy.label}
      </span>
      <p className="labs-mode-banner-detail">{copy.detail}</p>
    </div>
  );
};

export default LabsModeBanner;
