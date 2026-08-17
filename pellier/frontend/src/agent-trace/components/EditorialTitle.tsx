/**
 * EditorialTitle — Page-level title block (eyebrow + Fraunces title + summary paragraph).
 *
 * Used at the top of each Pellier Labs surface for consistent editorial hierarchy.
 *
 * Requirements: 15.3, 15.7
 */

import React from 'react';
export interface EditorialTitleProps {
  eyebrow: string;
  title: string;
  summary?: string;
  className?: string;
}

export const EditorialTitle: React.FC<EditorialTitleProps> = ({
  eyebrow,
  title,
  summary,
  className = '',
}) => {
  return (
    <header className={`pellier-labs-surface-header ${className}`.trim()}>
      <span className="sr-only">{eyebrow}</span>
      <h1>{title}</h1>
      {summary ? <p>{summary}</p> : null}
    </header>
  );
};
