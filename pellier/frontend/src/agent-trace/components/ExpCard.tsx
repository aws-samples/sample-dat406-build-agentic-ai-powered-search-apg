/**
 * ExpCard — Reusable cream content surface.
 *
 * Cream background, a quiet 1px rule, and a compact radius. Accent color is
 * reserved for meaningful status and selection states within the content.
 *
 * Requirements: 15.3
 */

import React from 'react';

export interface ExpCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  /**
   * Optional taxonomy hook. Surfaces that group cards (the architecture index
   * groups by live / workshop / optional / quality) set this so CSS can give a
   * card its category colour without every caller inventing a wrapper.
   */
  'data-category'?: string;
}

export const ExpCard: React.FC<ExpCardProps> = ({
  children,
  className = '',
  onClick,
  'data-category': dataCategory,
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
      className={`pellier-labs-exp-card ${className}`.trim()}
      data-clickable={isClickable ? 'true' : undefined}
      data-category={dataCategory}
      style={{
        position: 'relative',
        background: 'var(--at-card-bg)',
        border: '1px solid var(--at-card-border)',
        borderRadius: '8px',
        padding: '22px',
        cursor: isClickable ? 'pointer' : undefined,
        overflow: 'hidden',
      }}
    >
      {children}
    </div>
  );
};
