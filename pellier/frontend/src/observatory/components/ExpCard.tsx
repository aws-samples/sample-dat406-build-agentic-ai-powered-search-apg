/**
 * ExpCard — shared Observatory working surface.
 *
 * The visual contract lives in base.css so sessions, traces, architecture,
 * Gateway and policy, evaluation, and proof views evolve as one system.
 */

import React from 'react';

export interface ExpCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const ExpCard: React.FC<ExpCardProps> = ({
  children,
  className = '',
  onClick,
}) => {
  const isClickable = !!onClick;

  return (
    <div
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      className={`observatory-exp-card ${className}`.trim()}
      data-clickable={isClickable ? 'true' : undefined}
    >
      {children}
    </div>
  );
};
