/**
 * StatusPill — Shipped (sage green) or Exercise (burgundy) pill.
 *
 * Shipped: green-soft bg, green-1 text.
 * Exercise: red-soft bg, red-1 text.
 *
 * Requirements: 15.5
 */

import React from 'react';

export interface StatusPillProps {
  status: 'shipped' | 'exercise';
  className?: string;
}

const pillStyles: Record<
  StatusPillProps['status'],
  { bg: string; color: string; label: string }
> = {
  shipped: {
    bg: 'var(--at-status-shipped-bg)',
    color: 'var(--at-status-shipped-text)',
    label: 'Shipped',
  },
  exercise: {
    bg: 'var(--at-status-exercise-bg)',
    color: 'var(--at-status-exercise-text)',
    label: 'Exercise',
  },
};

export const StatusPill: React.FC<StatusPillProps> = ({
  status,
  className = '',
}) => {
  const { bg, color, label } = pillStyles[status];

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '3px 10px',
        borderRadius: '999px',
        backgroundColor: bg,
        color: color,
        fontFamily: 'var(--at-heading)',
        fontSize: '11px',
        fontWeight: 600,
        letterSpacing: '0.02em',
        lineHeight: 1.4,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
};
