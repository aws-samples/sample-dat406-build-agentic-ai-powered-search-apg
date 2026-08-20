/**
 * Eyebrow — Readable uppercase UI label with burgundy dot.
 *
 * Uses Instrument Sans so longer workshop labels remain easy to scan.
 *
 * Requirements: 15.4
 */

import React from 'react';

export interface EyebrowProps {
  label: string;
  variant?: 'burgundy' | 'muted';
  className?: string;
}

export const Eyebrow: React.FC<EyebrowProps> = ({
  label,
  variant = 'burgundy',
  className = '',
}) => {
  const dotColor =
    variant === 'burgundy' ? 'var(--obs-red-1)' : 'var(--obs-ink-4)';
  const textColor =
    variant === 'burgundy' ? 'var(--obs-red-1)' : 'var(--obs-ink-4)';

  return (
    <span
      className={className.trim()}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        fontFamily: 'var(--obs-heading)',
        fontSize: 'var(--obs-eyebrow-size)',
        fontWeight: 'var(--obs-eyebrow-weight)',
        letterSpacing: 'var(--obs-eyebrow-tracking)',
        textTransform: 'uppercase',
        color: textColor,
        lineHeight: 1,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          display: 'inline-block',
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: dotColor,
          flexShrink: 0,
        }}
      />
      {label}
    </span>
  );
};
