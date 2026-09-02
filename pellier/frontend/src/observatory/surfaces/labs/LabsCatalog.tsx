import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

import { imageSrc } from '../../../utils/assetPath';
import WorkbenchResources from '../../components/WorkbenchResources';
import { LAB_EXERCISES } from '../../labs/labCatalog';
import { statusForExercise } from '../../labs/evidence';
import { useLabEvidence } from '../../labs/useLabEvidence';
import {
  EvidenceLoadNotice,
  LabStatusMark,
} from './LabShared';
import './Labs.css';

export default function LabsCatalog() {
  const { data, error, loading, reload } = useLabEvidence();

  return (
    <div className="labs-catalog" data-testid="labs-catalog">
      <header className="labs-catalog-hero">
        <div className="labs-catalog-hero-copy">
          <h1 className="font-display">Governed Lab Collection</h1>
          <p>
            Four labs, one live workbench: build the boundary, measure its
            behavior, prove the exact evidence, and explain the tradeoff.
          </p>
          <Link to="/observatory/workbench?lab=grounded-inventory">
            Enter labs and workbench
            <ArrowRight size={16} strokeWidth={1.8} aria-hidden="true" />
          </Link>
        </div>
        <div className="labs-catalog-contact-sheet" aria-label="Four lab themes">
          {LAB_EXERCISES.map((exercise, index) => (
            <figure key={exercise.id}>
              <img
                src={imageSrc(exercise.image)}
                width={exercise.imageWidth}
                height={exercise.imageHeight}
                alt=""
                aria-hidden="true"
                loading={index < 2 ? 'eager' : 'lazy'}
                decoding="async"
              />
              <figcaption>
                <span>
                  {exercise.anchorName} · Lab {Number(exercise.number)}
                </span>
                <strong>{exercise.shortTitle}</strong>
              </figcaption>
            </figure>
          ))}
        </div>
      </header>

      <section className="labs-catalog-body" aria-labelledby="labs-catalog-heading">
        <div className="labs-catalog-intro">
          <div>
            <h2 id="labs-catalog-heading" className="font-display">
              Four evidence-first labs
            </h2>
            <p>
              Each card carries its lab context into the same workbench. Card
              states summarize current environment evidence; they do not claim
              participant completion.
            </p>
          </div>
          <span>{LAB_EXERCISES.length} labs</span>
        </div>

        {error ? <EvidenceLoadNotice error={error} onRetry={reload} /> : null}

        <div className="labs-catalog-grid">
          {LAB_EXERCISES.map((exercise, index) => {
            const status = statusForExercise(exercise, data);
            return (
              <Link
                key={exercise.id}
                to={`/observatory/workbench?lab=${exercise.id}`}
                className="labs-catalog-card"
                data-lab={exercise.number}
                aria-label={`Lab ${Number(exercise.number)}: ${exercise.title}. ${loading ? 'Reading evidence' : status.label}`}
              >
                <div className="labs-catalog-card-media">
                  <img
                    src={imageSrc(exercise.image)}
                    width={exercise.imageWidth}
                    height={exercise.imageHeight}
                    alt=""
                    aria-hidden="true"
                    loading={index === 0 ? 'eager' : 'lazy'}
                    decoding="async"
                  />
                </div>
                <div className="labs-catalog-card-copy">
                  <span className="labs-catalog-card-number">
                    {exercise.anchorName} · Lab {Number(exercise.number)}
                  </span>
                  <h3>{exercise.title}</h3>
                  <p>{exercise.summary}</p>
                  <LabStatusMark status={status} loading={loading} />
                  <span className="labs-catalog-card-open">
                    Open in workbench
                    <ArrowRight size={16} strokeWidth={1.8} aria-hidden="true" />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
      <WorkbenchResources />
    </div>
  );
}
