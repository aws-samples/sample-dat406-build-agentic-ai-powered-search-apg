/**
 * Eyebrow — the Observatory's name for the one shared section label.
 *
 * This used to be a second implementation of `shared/SectionEyebrow`: same
 * job, same family, same weight and tracking, but 12px against the
 * primitive's 11px and a 6px dot against its 5px. Two implementations of one
 * label is how a surface drifts, so this is now a thin adapter and the
 * primitive is the only recipe. The name and the `label` / `variant` props
 * stay because forty-odd call sites read better with them than with
 * `<SectionEyebrow>{label}</SectionEyebrow>`.
 *
 * Requirements: 15.4
 */

import React from 'react';

import { SectionEyebrow } from '../../shared';

export interface EyebrowProps {
  label: string;
  variant?: 'burgundy' | 'muted';
  className?: string;
}

export const Eyebrow: React.FC<EyebrowProps> = ({
  label,
  variant = 'burgundy',
  className = '',
}) => (
  <SectionEyebrow
    tone={variant === 'burgundy' ? 'brand' : 'muted'}
    className={className.trim() || undefined}
  >
    {label}
  </SectionEyebrow>
);
