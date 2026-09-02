/**
 * EditorialTitle — Page-level title block (eyebrow + Fraunces title + summary paragraph).
 *
 * Used at the top of each Observatory surface for consistent editorial hierarchy.
 *
 * Requirements: 15.3, 15.7
 */

import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Eyebrow } from './Eyebrow';

export interface EditorialTitleProps {
  eyebrow: string;
  title: string;
  summary?: string;
  className?: string;
  backToReferences?: boolean;
}

export const EditorialTitle: React.FC<EditorialTitleProps> = ({
  eyebrow,
  title,
  summary,
  className = '',
  backToReferences = false,
}) => {
  return (
    <header
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        marginBottom: '32px',
      }}
    >
      {backToReferences ? (
        <Link
          to="/observatory/workbench#resources"
          className="observatory-reference-return"
          aria-label="Back to Labs and Workbench resources"
        >
          <ArrowLeft size={15} strokeWidth={1.8} aria-hidden="true" />
          <span>Labs &amp; Workbench resources</span>
        </Link>
      ) : null}
      <Eyebrow label={eyebrow} />

      {/* Size, leading, weight and tracking come from
          `.observatory-page-title` so every route shares one page-title step.
          Inline values here previously won over the class and let each surface
          drift to its own size. */}
      <h1
        className="observatory-page-title font-display text-espresso"
        style={{ margin: 0 }}
      >
        {title}
      </h1>

      {summary && (
        <p
          className="font-sans text-ink-soft"
          style={{
            fontSize: 'clamp(15px, 1.2vw, 17px)',
            lineHeight: 1.65,
            maxWidth: '640px',
            margin: 0,
          }}
        >
          {summary}
        </p>
      )}
    </header>
  );
};
