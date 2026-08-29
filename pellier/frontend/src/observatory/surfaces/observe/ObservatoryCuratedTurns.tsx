/**
 * Compact, canonical shopper turns. The prompts originate in the storefront
 * source so Labs cannot drift from the participant-facing experience.
 */

import { Loader2, Play } from 'lucide-react';
import ResponsiveImage from '../../../components/ResponsiveImage';
import {
  heroPillsForPersona,
  PERSONA_TURN_TRACES,
  turnPreviewProductId,
} from '../../../data/personaCurations';
import { SHOWCASE_PRODUCTS } from '../../../data/showcaseProducts';

export interface ObservatoryCuratedTurnsProps {
  personaId: string;
  personaLabel: string;
  running: boolean;
  activeIndex: number | null;
  onInspect: (query: string, index: number) => void;
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

export default function ObservatoryCuratedTurns({
  personaId,
  personaLabel,
  running,
  activeIndex,
  onInspect,
  id = 'curated-turns',
}: ObservatoryCuratedTurnsProps) {
  const queries = heroPillsForPersona(personaId);
  const traces = tracesFor(personaId);
  const namedPersona = personaId !== 'fresh' && personaId !== 'anonymous';

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
          const dispatcherOnly = Boolean(
            trace?.tools.includes('initiate_return'),
          );
          const traceLabel = trace
            ? [
                trace.tools.join(' -> '),
                trace.skill ?? '',
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
                disabled={running}
                aria-label={`Inspect: ${query}`}
                onClick={() => onInspect(query, index)}
              >
                <span className="labs-turn-media" aria-hidden="true">
                  {image ? (
                    <ResponsiveImage
                      src={image}
                      alt=""
                      loading="lazy"
                      decoding="async"
                      sizes="74px"
                    />
                  ) : (
                    <span>No catalog result</span>
                  )}
                </span>

                {/* The turn ordinal comes from the `labs-turn` CSS counter in
                    ObservatoryIndex.css, so it is not repeated in markup here. */}
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
    </section>
  );
}
