import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

import { imageSrc } from '../../../utils/assetPath';
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
        <img
          src={imageSrc('/products/landing-approach-atelier-960.avif')}
          width={960}
          height={540}
          alt=""
          aria-hidden="true"
          loading="eager"
          decoding="async"
        />
        <div className="labs-catalog-hero-copy">
          <h1>Governed Lab Collection</h1>
          <p>
            Build the artifact, measure its behavior, prove the exact evidence,
            and govern the failure path.
          </p>
          <Link to="/observatory/workbench">
            Open live workbench
            <ArrowRight size={16} strokeWidth={1.8} aria-hidden="true" />
          </Link>
        </div>
      </header>

      <section className="labs-catalog-body" aria-labelledby="labs-catalog-heading">
        <div className="labs-catalog-intro">
          <div>
            <h2 id="labs-catalog-heading">Five evidence-first exercises</h2>
            <p>
              Card states summarize the current environment response. They do not
              claim participant completion.
            </p>
          </div>
          <span>{LAB_EXERCISES.length} exercises</span>
        </div>

        {error ? <EvidenceLoadNotice error={error} onRetry={reload} /> : null}

        <div className="labs-catalog-grid">
          {LAB_EXERCISES.map((exercise, index) => {
            const status = statusForExercise(exercise, data);
            return (
              <Link
                key={exercise.id}
                to={`/observatory/labs/${exercise.id}`}
                className="labs-catalog-card"
                data-lab={exercise.number}
                aria-label={`${exercise.title}. ${loading ? 'Reading evidence' : status.label}`}
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
                    Exercise {exercise.number}
                  </span>
                  <h3>{exercise.title}</h3>
                  <p>{exercise.summary}</p>
                  <LabStatusMark status={status} loading={loading} />
                  <span className="labs-catalog-card-open">
                    Open exercise
                    <ArrowRight size={16} strokeWidth={1.8} aria-hidden="true" />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
