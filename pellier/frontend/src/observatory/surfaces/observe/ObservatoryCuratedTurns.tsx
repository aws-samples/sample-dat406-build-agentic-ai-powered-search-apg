/**
 * Guided requests are durable Aurora workshop_scenarios rows. They are not
 * browser fixtures: when the data plane is unavailable, the Workbench says so
 * instead of presenting a convincing but disconnected list.
 */

import { useEffect, useState } from 'react';
import { AlertCircle, Loader2, Play } from 'lucide-react';
import ResponsiveImage from '../../../components/ResponsiveImage';

interface LiveScenario {
  id: number;
  ordinal: number;
  prompt: string;
  productName: string | null;
  imageUrl: string | null;
}

export interface ObservatoryCuratedTurnsProps {
  personaId: string;
  personaLabel: string;
  running: boolean;
  activeIndex: number | null;
  onInspect: (query: string, index: number) => void;
  id?: string;
}

export default function ObservatoryCuratedTurns({
  personaId,
  personaLabel,
  running,
  activeIndex,
  onInspect,
  id = 'curated-turns',
}: ObservatoryCuratedTurnsProps) {
  const [scenarios, setScenarios] = useState<LiveScenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setScenarios([]);
    void fetch(`/api/observatory/scenarios?persona=${encodeURIComponent(personaId)}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Live scenario request failed: ${response.status}`);
        }
        return response.json() as Promise<{ scenarios?: LiveScenario[] }>;
      })
      .then((payload) => {
        if (!cancelled) setScenarios(payload.scenarios ?? []);
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : 'Live scenarios are unavailable.',
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [personaId]);

  const namedPersona = personaId !== 'fresh' && personaId !== 'anonymous';
  return (
    <section className="labs-turns" id={id} aria-labelledby="labs-turns-title">
      <header className="labs-turns-heading">
        <h2 id="labs-turns-title">Shopper turns</h2>
        <p>
          {namedPersona
            ? `Aurora-backed guided requests for ${personaLabel}`
            : 'Aurora-backed guided requests for the storefront'}
        </p>
      </header>

      {loading ? (
        <div className="labs-turns-state" role="status">
          <Loader2 className="spin" size={16} aria-hidden="true" />
          Loading live scenarios…
        </div>
      ) : null}
      {error ? (
        <div className="labs-turns-state" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          {error}
        </div>
      ) : null}
      {!loading && !error && scenarios.length === 0 ? (
        <div className="labs-turns-state">
          Aurora has no guided requests for this profile yet.
        </div>
      ) : null}

      {!loading && !error && scenarios.length > 0 ? (
        <ol className="labs-turns-list">
          {scenarios.map((scenario, index) => {
            const isActive = activeIndex === index;
            return (
              <li key={scenario.id}>
                <button
                  type="button"
                  className="labs-turn"
                  data-active={isActive ? 'true' : undefined}
                  disabled={running}
                  aria-label={`Inspect: ${scenario.prompt}`}
                  onClick={() => onInspect(scenario.prompt, index)}
                >
                  <span className="labs-turn-media" aria-hidden="true">
                    {scenario.imageUrl ? (
                      <ResponsiveImage
                        src={scenario.imageUrl}
                        alt=""
                        loading="lazy"
                        decoding="async"
                        sizes="74px"
                      />
                    ) : (
                      <span>No catalog image</span>
                    )}
                  </span>
                  <span className="labs-turn-copy">
                    <strong>{scenario.prompt}</strong>
                    <small>
                      {scenario.productName
                        ? `Catalog preview · ${scenario.productName}`
                        : 'Aurora scenario'}
                    </small>
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
      ) : null}
    </section>
  );
}
