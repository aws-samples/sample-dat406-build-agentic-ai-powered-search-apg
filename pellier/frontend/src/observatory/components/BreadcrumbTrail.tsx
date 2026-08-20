/**
 * BreadcrumbTrail — Dot-separated Instrument Sans breadcrumb from route path.
 *
 * Renders a navigation breadcrumb trail with dot separators in the
 * Observatory UI-label style.
 *
 * Requirements: 15.3
 */

import React from 'react';

export interface BreadcrumbTrailProps {
  segments: string[];
  className?: string;
}

export const BreadcrumbTrail: React.FC<BreadcrumbTrailProps> = ({
  segments,
  className = '',
}) => {
  if (segments.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        fontFamily: 'var(--obs-heading)',
        fontSize: '12.5px',
        fontWeight: 600,
        letterSpacing: '0.02em',
        color: 'var(--obs-ink-2)',
        lineHeight: 1,
      }}
    >
      <ol
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          listStyle: 'none',
          margin: 0,
          padding: 0,
        }}
      >
        {segments.map((segment, index) => {
          const isLast = index === segments.length - 1;

          return (
            <li
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span
                style={{
                  color: isLast ? 'var(--obs-ink-2)' : 'var(--obs-ink-4)',
                }}
                aria-current={isLast ? 'page' : undefined}
              >
                {segment}
              </span>
              {!isLast && (
                <span
                  aria-hidden="true"
                  style={{
                    display: 'inline-block',
                    width: '3px',
                    height: '3px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--obs-ink-5)',
                    flexShrink: 0,
                  }}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
