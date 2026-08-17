/**
 * LabsModeBanner — states the interaction contract for the current view.
 *
 * Rendered once by AgentTraceFrame rather than added to each of the fifteen
 * surfaces. One mount means every view is covered, no page can forget it, and
 * the wording cannot drift between them.
 *
 * It is a statement, not a control: a participant who lands on a reference view
 * should know within a second that there is nothing to run, without having to
 * scan the page for a button that does not exist.
 */

import React from 'react';
import { BookOpen } from 'lucide-react';
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
        ) : (
          <BookOpen size={13} strokeWidth={1.8} aria-hidden="true" />
        )}
        {copy.label}
      </span>
      <p className="labs-mode-banner-detail">{copy.detail}</p>
    </div>
  );
};

export default LabsModeBanner;
