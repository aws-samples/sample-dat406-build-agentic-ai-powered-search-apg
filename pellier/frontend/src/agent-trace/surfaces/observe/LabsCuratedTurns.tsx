/**
 * Canonical shopper turns in a compact selectable list. Queries come from the
 * same source as the storefront so Labs and Pellier cannot drift.
 */

import { ArrowRight, Check, Loader2, Play, RotateCcw } from 'lucide-react';

import ResponsiveImage from '../../../components/ResponsiveImage';
import {
  heroPillsForPersona,
  labThreadForPersona,
  PERSONA_TURN_TRACES,
  turnPreviewProductId,
} from '../../../data/personaCurations';
import { SHOWCASE_PRODUCTS } from '../../../data/showcaseProducts';
import type { OrchestrationPattern } from '../../../services/chat';

export interface LabsCuratedTurnsProps {
  personaId: string;
  personaLabel: string;
  running: boolean;
  activeIndex: number | null;
  orchestrationPattern: OrchestrationPattern;
  onInspect: (query: string, index: number) => void;
  threadProgress: number | null;
  onStartThread: () => void;
  onContinueThread: () => void;
  id?: string;
}

function tracesFor(personaId: string) {
  return PERSONA_TURN_TRACES[personaId] ?? PERSONA_TURN_TRACES.fresh;
}

function previewImage(personaId: string, index: number): string | null {
  const productId = turnPreviewProductId(personaId, index);
  if (productId === null) return null;
  const product = SHOWCASE_PRODUCTS.find((item) => item.id === productId);
  return product?.imageUrl ?? null;
}

export default function LabsCuratedTurns({
  personaId,
  personaLabel,
  running,
  activeIndex,
  orchestrationPattern,
  onInspect,
  threadProgress,
  onStartThread,
  onContinueThread,
  id = 'curated-turns',
}: LabsCuratedTurnsProps) {
  const queries = heroPillsForPersona(personaId);
  const traces = tracesFor(personaId);
  const namedPersona = personaId !== 'fresh' && personaId !== 'anonymous';
  const thread = labThreadForPersona(personaId);
  const completedThread = threadProgress === thread.turns.length;
  const nextThreadIndex = threadProgress ?? 0;
  const nextThreadQuery = thread.turns[nextThreadIndex];
  const threadActionLabel =
    threadProgress === null
      ? 'Start three-turn memory and retrieval thread'
      : completedThread
        ? 'Restart three-turn memory and retrieval thread'
        : `Continue thread: ${nextThreadQuery}`;

  return (
    <section className="labs-turns" id={id} aria-labelledby="labs-turns-title">
      <header className="labs-turns-heading">
        <h2 id="labs-turns-title">Shopper turns</h2>
        <p>
          {namedPersona
            ? `Canonical requests from ${personaLabel}'s storefront`
            : 'Five canonical requests from the storefront'}
        </p>
      </header>

      <ol className="labs-turns-list">
        {queries.map((query, index) => {
          const image = previewImage(personaId, index);
          const trace = traces[index];
          const isActive = activeIndex === index;
          const dispatcherOnly = trace?.tools.includes('process_return');
          const patternBlocked =
            dispatcherOnly && orchestrationPattern !== 'dispatcher';
          const traceLabel = trace
            ? [
                trace.tools.join(' -> '),
                trace.skills.length ? trace.skills.join(' + ') : '',
                dispatcherOnly ? 'Dispatcher only' : '',
              ]
                .filter(Boolean)
                .join(' / ')
            : 'Agent handoff';

          return (
            <li key={`${personaId}-${index}`}>
              <button
                type="button"
                className="labs-turn"
                data-active={isActive ? 'true' : undefined}
                disabled={running || patternBlocked}
                aria-label={`Inspect: ${query}`}
                title={
                  patternBlocked
                    ? 'Write turns run only through Dispatcher.'
                    : undefined
                }
                onClick={() => onInspect(query, index)}
              >
                <span className="labs-turn-media" aria-hidden="true">
                  {image ? (
                    <ResponsiveImage
                      src={image}
                      alt=""
                      loading="lazy"
                      decoding="async"
                      sizes="64px"
                    />
                  ) : (
                    <span>No catalog result</span>
                  )}
                </span>

                <span className="labs-turn-copy">
                  <strong>{query}</strong>
                  <small>{traceLabel}</small>
                </span>

                <span className="labs-turn-action" aria-hidden="true">
                  {isActive && running ? (
                    <Loader2 className="spin" size={15} />
                  ) : (
                    <Play size={14} fill="currentColor" />
                  )}
                </span>
              </button>
            </li>
          );
        })}
          </ol>

      <section
        className="labs-thread"
        aria-labelledby="labs-thread-title"
        data-status={
          completedThread ? 'complete' : threadProgress === null ? 'idle' : 'active'
        }
      >
        <div className="labs-thread-heading">
          <span>Threaded proof</span>
          <strong id="labs-thread-title">{thread.title}</strong>
          <p>{thread.focus}</p>
        </div>

        <ol className="labs-thread-steps">
          {thread.turns.map((turn, index) => {
            const complete = threadProgress !== null && index < threadProgress;
            const next = !completedThread && index === nextThreadIndex;
            return (
              <li
                key={turn}
                data-complete={complete ? 'true' : undefined}
                data-next={next ? 'true' : undefined}
              >
                <span aria-hidden="true">
                  {complete ? <Check size={12} /> : `0${index + 1}`}
                </span>
                <p>{turn}</p>
              </li>
            );
          })}
        </ol>

        <button
          type="button"
          className="labs-thread-action"
          disabled={running}
          aria-label={threadActionLabel}
          onClick={() => {
            if (threadProgress === null || completedThread) onStartThread();
            else onContinueThread();
          }}
        >
          {threadProgress === null || completedThread ? (
            completedThread ? <RotateCcw size={14} aria-hidden="true" /> : <Play size={14} fill="currentColor" aria-hidden="true" />
          ) : (
            <ArrowRight size={14} aria-hidden="true" />
          )}
          <span>
            {threadProgress === null
              ? 'Run the three-turn thread'
              : completedThread
                ? 'Restart thread'
                : `Continue with turn ${nextThreadIndex + 1}`}
          </span>
        </button>
      </section>
    </section>
  );
}
