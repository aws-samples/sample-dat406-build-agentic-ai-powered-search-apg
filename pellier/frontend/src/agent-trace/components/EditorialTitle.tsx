/**
 * Compact technical header shared by the supporting Pellier Labs surfaces.
 */

import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface TechnicalReference {
  label: string;
  value: string;
  code?: boolean;
}

export interface EditorialTitleProps {
  eyebrow: string;
  title: string;
  summary?: string;
  references?: TechnicalReference[];
  className?: string;
  backToReferences?: boolean;
}

export const EditorialTitle: React.FC<EditorialTitleProps> = ({
  eyebrow,
  title,
  summary,
  references = [],
  className = '',
  backToReferences = false,
}) => {
  return (
    <header className={`pellier-labs-surface-header ${className}`.trim()}>
      {backToReferences ? (
        <Link
          to="/pellier-labs/references"
          className="pellier-labs-reference-return"
          aria-label="Back to Deep Dives"
        >
          <ArrowLeft size={15} strokeWidth={1.8} aria-hidden="true" />
          <span>Deep Dives</span>
        </Link>
      ) : null}
      <span className="sr-only">{eyebrow}</span>
      <h1>{title}</h1>
      {summary ? <p>{summary}</p> : null}
      {references.length > 0 ? (
        <dl className="pellier-labs-technical-references" aria-label="Implementation references">
          {references.map((reference) => (
            <div key={`${reference.label}-${reference.value}`}>
              <dt>{reference.label}</dt>
              <dd data-code={reference.code ? 'true' : undefined}>
                {reference.code ? <code>{reference.value}</code> : reference.value}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
    </header>
  );
};
