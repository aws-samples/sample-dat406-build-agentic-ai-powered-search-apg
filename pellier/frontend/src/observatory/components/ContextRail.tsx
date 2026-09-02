/**
 * ContextRail — 360px right column wrapper for session detail views.
 *
 * Provides a fixed-width sidebar container used in two-column layouts
 * (ChatTab, TelemetryTab) for contextual information cards.
 *
 * Requirements: 15.3
 */

import React from 'react';

export interface ContextRailProps {
  children: React.ReactNode;
  className?: string;
}

export const ContextRail: React.FC<ContextRailProps> = ({
  children,
  className = '',
}) => {
  return (
    <aside
      className={`observatory-context-rail ${className}`.trim()}
    >
      {children}
    </aside>
  );
};
