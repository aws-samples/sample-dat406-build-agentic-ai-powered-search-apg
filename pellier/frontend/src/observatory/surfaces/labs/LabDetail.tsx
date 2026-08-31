import { ArrowLeft, CircleAlert } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { imageSrc } from '../../../utils/assetPath';
import { LAB_EXERCISES, findLabExercise } from '../../labs/labCatalog';
import {
  classificationFromPayload,
  evidenceForExercise,
  evidenceIdentity,
  policyEvidence,
  statusForExercise,
} from '../../labs/evidence';
import { useLabEvidence } from '../../labs/useLabEvidence';
import {
  EvidenceClassificationCard,
  EvidenceDatumList,
  EvidenceLoadNotice,
  ExerciseRail,
  LabActionBar,
  LabStatusMark,
  SourceBadge,
  WorkflowStepper,
} from './LabShared';
import './Labs.css';

export default function LabDetail() {
  const { exerciseId } = useParams<{ exerciseId: string }>();
  const exercise = findLabExercise(exerciseId);
  const { data, error, loading, reload } = useLabEvidence();

  if (!exercise) {
    return (
      <div className="lab-not-found">
        <h1>Exercise not found</h1>
        <p>The requested governed lab is not part of this collection.</p>
        <Link to="/observatory">
          <ArrowLeft size={16} aria-hidden="true" />
          Return to Lab Collection
        </Link>
      </div>
    );
  }

  const statuses = new Map(
    LAB_EXERCISES.map((candidate) => [
      candidate.id,
      statusForExercise(candidate, data),
    ]),
  );
  const status = statuses.get(exercise.id) ?? statusForExercise(exercise, data);
  const evidence = evidenceForExercise(exercise, data);
  const identity = evidenceIdentity(data);
  const policy = policyEvidence(data);
  const classification = classificationFromPayload(data);

  return (
    <article className="lab-detail" data-testid="lab-detail">
      <nav className="lab-detail-breadcrumb" aria-label="Breadcrumb">
        <Link to="/observatory">
          <ArrowLeft size={15} strokeWidth={1.8} aria-hidden="true" />
          Lab Collection
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">Exercise {exercise.number}</span>
      </nav>

      <header className="lab-detail-hero">
        <div className="lab-detail-hero-media">
          <img
            src={imageSrc(exercise.image)}
            width={exercise.imageWidth}
            height={exercise.imageHeight}
            alt=""
            aria-hidden="true"
            loading="eager"
            decoding="async"
          />
        </div>
        <div className="lab-detail-summary">
          <span className="lab-detail-number">Exercise {exercise.number}</span>
          <h1>{exercise.title}</h1>
          <p>{exercise.summary}</p>
          <LabStatusMark status={status} loading={loading} />
          <dl className="lab-detail-contract">
            <div>
              <dt>Objective</dt>
              <dd>{exercise.objective}</dd>
            </div>
            <div>
              <dt>Required proof</dt>
              <dd>{exercise.evidenceAssertion}</dd>
            </div>
          </dl>
        </div>
      </header>

      {error ? <EvidenceLoadNotice error={error} onRetry={reload} /> : null}

      <div className="lab-workbench-grid">
        <ExerciseRail
          exercises={LAB_EXERCISES}
          activeExercise={exercise}
          statuses={statuses}
        />

        <main className="lab-workspace">
          <WorkflowStepper />

          <section className="lab-workspace-section">
            <div className="lab-section-heading">
              <h2>Participant TODO</h2>
              <SourceBadge provenance="Derived" />
            </div>
            <p className="lab-todo">{exercise.participantTodo}</p>
          </section>

          <section className="lab-workspace-section">
            <div className="lab-section-heading">
              <h2>Focused run or verify command</h2>
              <span>Exercise contract</span>
            </div>
            <pre className="lab-command">
              <code>{exercise.command}</code>
            </pre>
          </section>

          <section className="lab-workspace-section">
            <div className="lab-section-heading">
              <h2>Measurement</h2>
              <p>Targets remain derived until a scoped verifier records values.</p>
            </div>
            <div className="lab-measurement-grid">
              {[exercise.measurements.before, exercise.measurements.after].map(
                (measurement) => (
                  <div key={measurement.label} className="lab-measurement">
                    <span>{measurement.label}</span>
                    <strong>{measurement.value}</strong>
                    <span className="lab-measurement-meta">
                      <SourceBadge provenance="Derived" compact />
                      <span>Exercise contract</span>
                      <span>Static</span>
                    </span>
                  </div>
                ),
              )}
            </div>
          </section>

          <section className="lab-workspace-section lab-decision">
            <div>
              <h2>Architecture decision</h2>
              <p>{exercise.decisionPrompt}</p>
            </div>
            <span>Explain with measured evidence</span>
          </section>

          {exercise.unavailableReason ? (
            <div className="lab-unavailable-note" role="note">
              <CircleAlert size={17} strokeWidth={1.8} aria-hidden="true" />
              <p>{exercise.unavailableReason}</p>
            </div>
          ) : null}

          <LabActionBar exercise={exercise} />
        </main>

        <aside className="lab-evidence-rail" aria-label="Exercise evidence">
          <div className="lab-evidence-rail-heading">
            <h2>Evidence</h2>
            <p>Exact identities and source boundaries from the current response.</p>
          </div>

          <EvidenceClassificationCard classification={classification} />
          <EvidenceDatumList title="Run identity" data={identity} />
          <EvidenceDatumList
            title="Current evidence"
            data={evidence}
            emptyMessage="No scoped evidence values exist for this exercise."
          />
          <EvidenceDatumList title="Policy identity" data={policy} />

          <section className="lab-evidence-section">
            <h2>Reconciliation</h2>
            <dl className="lab-evidence-data">
              {[
                ['Aurora transaction', 'Unknown'],
                ['Outbox and export', 'Unknown'],
                ['Reset proof', 'Unknown'],
              ].map(([label, value]) => (
                <div key={label} className="lab-evidence-datum">
                  <dt>{label}</dt>
                  <dd>
                    <strong>{value}</strong>
                    <span className="lab-evidence-meta">
                      <SourceBadge provenance="Unknown" compact />
                      <span>Scoped verifier</span>
                      <span>Not observed</span>
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        </aside>
      </div>
    </article>
  );
}
