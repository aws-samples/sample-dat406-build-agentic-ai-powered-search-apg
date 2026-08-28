/**
 * PersonaJourneys — the workshop's narrative spine in one screen.
 *
 * Three returning personas (Marco / Anna / Theo) each surface five Pellier
 * hero pills from `PERSONA_HERO_PILLS` — the same strings as the
 * storefront "Try asking" row. For each turn we list agent / tool /
 * model / outcome and link into captured session fixtures when they
 * exist (Marco Turn 4 links twice: opening demo = check_inventory stub,
 * midpoint = wired warehouse answer).
 *
 * Lives under OBSERVE — adjacent to Sessions (replay) and Observatory.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { EditorialTitle, ExpCard, Eyebrow } from '../../components';
import { PERSONA_HERO_PILLS, PERSONA_TURN_TRACES } from '../../../data/personaCurations';

interface JourneyTurn {
  n: number;
  pill: string;
  agent: string;
  model: string;
  skill?: string;
  tool?: string;
  outcome: string;
  /** Primary Observatory fixture for this turn (stub path, or only path). */
  sessionId?: string;
  /** When set, second fixture shows the post-build / wired path (e.g. check_inventory). */
  wiredSessionId?: string;
}

interface PersonaJourney {
  id: 'marco' | 'anna' | 'theo';
  displayName: string;
  capability: string;
  capabilityRole: string;
  blurb: string;
  turns: JourneyTurn[];
  capstoneNote?: string;
}

const MARCO_TURNS_META: Omit<JourneyTurn, 'pill' | 'n'>[] = [
  {
    agent: 'Search Agent',
    model: 'Claude Opus 4.6',
    tool: 'search_products',
    outcome: '3 linen pieces with editorial voice',
    sessionId: 'marco-opening-demo',
  },
  {
    agent: 'Personalization Agent (the-packing-list)',
    model: 'Claude Opus 4.6',
    tool: 'search_products → get_related_products',
    outcome: 'Complementary pieces; voice mentions packability',
    sessionId: 'marco-opening-demo',
  },
  {
    agent: 'Pricing Agent',
    model: 'Claude Sonnet 4.6',
    tool: 'get_price_analysis',
    outcome: '"$88 to $285, median $148"',
    sessionId: 'marco-opening-demo',
  },
  {
    agent: 'Inventory Agent',
    model: 'Claude Sonnet 4.6',
    tool: 'check_inventory',
    outcome:
      'Opening demo: Dispatcher matches stock intent; check_inventory still stubbed → fall-through telemetry (no tool). Midpoint: same Pellier pill - real warehouse breakdown after the build.',
    sessionId: 'marco-opening-demo',
    wiredSessionId: 'marco-midpoint-checkpoint',
  },
  {
    agent: 'Search Agent (the-packing-list)',
    model: 'Claude Opus 4.6',
    tool: 'escalate_to_human',
    outcome:
      'Capstone - human-stylist handoff. Catalog tools cannot dress a body for an occasion; escalate_to_human is the honest fallback.',
    sessionId: 'marco-capstone',
  },
];

const ANNA_TURNS_META: Omit<JourneyTurn, 'pill' | 'n'>[] = [
  {
    agent: 'Personalization Agent (the-gift-table)',
    model: 'Claude Opus 4.6',
    tool: 'search_products_hybrid',
    outcome:
      'Vector → Postgres FTS → RRF → Rerank v3.5. Four SSE telemetry spans visible.',
    sessionId: 'anna-morning-ritual',
  },
  {
    agent: 'Personalization Agent',
    model: 'Claude Opus 4.6',
    tool: 'search_products_hybrid',
    outcome: 'Soft "beautiful" + literal "$100" - hybrid handles both.',
    sessionId: 'anna-under-100',
  },
  {
    agent: 'Personalization Agent',
    model: 'Claude Opus 4.6',
    tool: 'search_products_hybrid',
    outcome: 'Candle as anchor + "with something else" reranks the band.',
    sessionId: 'anna-candle-pairing',
  },
  {
    agent: 'Personalization Agent',
    model: 'Claude Opus 4.6',
    tool: 'search_products_hybrid',
    outcome: 'Beeswax Taper Candles at rank 1 - Cohere reads "wrap-ready" intent.',
    sessionId: 'anna-birthday-gift',
  },
  {
    agent: 'Personalization Agent (the-gift-table)',
    model: 'Claude Opus 4.6',
    tool: 'escalate_to_human',
    outcome:
      'Capstone - human-stylist handoff for sympathy gifting. Hybrid retrieval can find candles; it cannot read the room.',
    sessionId: 'anna-housewarming',
  },
];

const THEO_TURNS_META: Omit<JourneyTurn, 'pill' | 'n'>[] = [
  {
    agent: 'Personalization Agent (the-makers-shelf)',
    model: 'Claude Opus 4.6',
    tool: 'search_products',
    outcome: 'Stoneware Pour-Over Set at rank 1 - patina vibe matches.',
    sessionId: 'theo-pour-over',
  },
  {
    agent: 'Personalization Agent',
    model: 'Claude Opus 4.6',
    tool: 'search_products → get_related_products',
    outcome: 'Ceramic Tumblers + Woven Mat Set - same kiln register.',
    sessionId: 'theo-pour-over-pairing',
  },
  {
    agent: 'Search Agent',
    model: 'Claude Opus 4.6',
    tool: 'search_products',
    outcome: 'Washed-linen pieces with patina-leaning prose.',
    sessionId: 'theo-linen-seasons',
  },
  {
    agent: 'Customer Service Agent',
    model: 'Claude Opus 4.6',
    tool: 'search_products → get_return_policy → initiate_return',
    outcome:
      'Three writes in one transaction · returns row + product_catalog decrement + tool_audit · Cedar + SQL gated',
    sessionId: 'theo-ceramics-return',
  },
  {
    agent: 'Customer Service Agent (the-makers-shelf)',
    model: 'Claude Opus 4.6',
    tool: 'escalate_to_human',
    outcome:
      'Capstone - exception-return handoff. Outside the standard window; initiate_return refuses, escalate_to_human is the honest fallback.',
    sessionId: 'theo-home-not-wardrobe',
  },
];

function attachPills(
  meta: Omit<JourneyTurn, 'pill' | 'n'>[],
  pills: string[],
  traces: Array<{ skill?: string; tools: string[] }>,
): JourneyTurn[] {
  return meta.map((m, idx) => ({
    n: idx + 1,
    pill: pills[idx],
    ...m,
    skill: traces[idx]?.skill,
    tool: traces[idx]?.tools.join(' → ') ?? m.tool,
  }));
}

const JOURNEYS: PersonaJourney[] = [
  {
    id: 'marco',
    displayName: 'Marco',
    capability: 'pgvector semantic search',
    capabilityRole: 'Foundation · Capability 1',
    blurb:
      "Returning customer. Natural fabrics, linen, travel-ready, warm tones. Marco's arc anchors pgvector cosine over Cohere Embed v4. Turn 4 is the workshop build: same hero pill ships stub telemetry in opening demo, then a real check_inventory replay after the required path lands.",
    turns: attachPills(MARCO_TURNS_META, PERSONA_HERO_PILLS.marco, PERSONA_TURN_TRACES.marco),
    capstoneNote:
      "Claude Opus 4.6 handles editorial turns; Claude Sonnet 4.6 handles routing and reporting turns. That architectural split is visible here - and Turn 4 is where the wiring exercise lands.",
  },
  {
    id: 'anna',
    displayName: 'Anna',
    capability: 'hybrid + Cohere Rerank v3.5',
    capabilityRole: 'Capability 2 · when pure vector wears thin',
    blurb:
      "Gift-giver - observe & learn only. Her five Pellier hero strings are a live demo of Capability 2 (hybrid + rerank); there is no required wiring exercise on this arc. Use Sessions and Observatory to study spans and cost.",
    turns: attachPills(ANNA_TURNS_META, PERSONA_HERO_PILLS.anna, PERSONA_TURN_TRACES.anna),
    capstoneNote:
      "Recall@5 jumps ~20 points; p50 doubles; cost goes 6×. The Proof Board keeps the required retrieval checkpoint - there's no universally right answer per query class.",
  },
  {
    id: 'theo',
    displayName: 'Theo',
    capability: 'Aurora as agent system-of-record',
    capabilityRole: 'Capability 3 · writes leave a paper trail',
    blurb:
      "Slow-craft buyer - observe & learn only. This arc demonstrates Capability 3 (writes + tool_audit / Cedar). No participant coding checkpoint on Theo in the required path; replay session fixtures to see the paper trail.",
    turns: attachPills(THEO_TURNS_META, PERSONA_HERO_PILLS.theo, PERSONA_TURN_TRACES.theo),
    capstoneNote:
      'Every mutation is reconstructible from tool_audit - see Write-path.',
  },
];

/* -----------------------------------------------------------------------
 * Turn row
 * ----------------------------------------------------------------------- */

function sessionLinkLabel(id: string, suffix?: string): string {
  const base = id.replace(/-/g, ' ');
  return suffix ? `${base} · ${suffix}` : base;
}

const TurnRow: React.FC<{ turn: JourneyTurn; isFirst?: boolean }> = ({ turn, isFirst }) => {
  const links =
    turn.sessionId || turn.wiredSessionId ? (
      <div
        style={{
          marginTop: '10px',
          display: 'flex',
          flexWrap: 'wrap' as const,
          gap: '12px',
        }}
      >
        {turn.sessionId && (
          <Link
            to={`/observatory/sessions/${turn.sessionId}`}
            style={{
              fontFamily: 'var(--obs-mono)',
              fontSize: '11px',
              color: 'var(--obs-burgundy)',
              textDecoration: 'none',
            }}
          >
            {sessionLinkLabel(turn.sessionId, turn.wiredSessionId ? 'stub / arc' : 'replay')}
            →
          </Link>
        )}
        {turn.wiredSessionId && (
          <Link
            to={`/observatory/sessions/${turn.wiredSessionId}`}
            style={{
              fontFamily: 'var(--obs-mono)',
              fontSize: '11px',
              color: 'var(--obs-burgundy)',
              textDecoration: 'none',
            }}
          >
            {sessionLinkLabel(turn.wiredSessionId, 'wired')}→
          </Link>
        )}
      </div>
    ) : null;

  return (
    <div
      style={{
        padding: '14px 16px',
        borderTop: isFirst ? 'none' : '1px solid var(--obs-card-border)',
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '32px 1fr 200px',
          gap: '14px',
          alignItems: 'flex-start',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--obs-mono)',
            fontSize: '13px',
            color: 'var(--obs-ink-3)',
            paddingTop: '2px',
          }}
        >
          T{turn.n}
        </span>

        <div>
          <div
            style={{
              fontFamily: 'var(--obs-sans)',
              fontSize: '14px',
              color: 'var(--obs-ink-1)',
              marginBottom: '4px',
            }}
          >
            “{turn.pill}”
          </div>
          <div
            style={{
              fontFamily: 'var(--obs-sans)',
              fontSize: '13px',
              color: 'var(--obs-ink-2)',
              lineHeight: 1.55,
            }}
          >
            {turn.outcome}
          </div>
          {links}
        </div>

        <div
          style={{
            fontFamily: 'var(--obs-mono)',
            fontSize: '12px',
            color: 'var(--obs-ink-3)',
            textAlign: 'right' as const,
            lineHeight: 1.6,
          }}
        >
          <div style={{ color: 'var(--obs-ink-1)' }}>{turn.agent}</div>
          <div>{turn.model}</div>
          {turn.skill && <div>skill.{turn.skill}</div>}
          {turn.tool && <div>{turn.tool}</div>}
        </div>
      </div>
    </div>
  );
};

/* -----------------------------------------------------------------------
 * Persona section
 * ----------------------------------------------------------------------- */

const PersonaSection: React.FC<{ journey: PersonaJourney }> = ({ journey }) => (
  <ExpCard>
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        marginBottom: '8px',
      }}
    >
      <Eyebrow label={journey.capabilityRole} />
      <code
        style={{
          fontFamily: 'var(--obs-mono)',
          fontSize: '12px',
          color: 'var(--obs-burgundy)',
        }}
      >
        {journey.capability}
      </code>
    </div>
    <h2
      className="font-display italic text-espresso"
      style={{
        fontSize: 'clamp(28px, 3.5vw, 44px)',
        fontWeight: 400,
        margin: '4px 0 12px',
        letterSpacing: '-0.015em',
        lineHeight: 1.1,
      }}
    >
      {journey.displayName}
    </h2>
    <p
      style={{
        fontFamily: 'var(--obs-sans)',
        fontSize: '14px',
        lineHeight: 1.6,
        color: 'var(--obs-ink-2)',
        marginBottom: '20px',
      }}
    >
      {journey.blurb}
    </p>

    <div
      style={{
        border: '1px solid var(--obs-card-border)',
        borderRadius: '6px',
        background: 'var(--obs-cream-1)',
        overflow: 'hidden' as const,
      }}
    >
      {journey.turns.map((t, i) => (
        <TurnRow key={t.n} turn={t} isFirst={i === 0} />
      ))}
    </div>

    {journey.capstoneNote && (
      <div
        style={{
          marginTop: '16px',
          paddingTop: '14px',
          borderTop: '1px solid var(--obs-card-border)',
          fontFamily: 'var(--obs-sans)',
          fontSize: '13px',
          color: 'var(--obs-ink-2)',
          lineHeight: 1.6,
        }}
      >
        {journey.capstoneNote}
      </div>
    )}
  </ExpCard>
);

/* -----------------------------------------------------------------------
 * Page
 * ----------------------------------------------------------------------- */

const PersonaJourneys: React.FC = () => (
  <div style={{ padding: '40px 48px', maxWidth: '1100px' }}>
    <EditorialTitle
      backToReferences
      eyebrow="Observe · Persona Journeys · 15 Pellier hero turns"
      title="Three personas, fifteen hero queries."
      summary="Each row mirrors one Pellier “Try asking” pill, so the storefront and Pellier Observatory tell the same story turn by turn. The right rail shows what happened under the hood: which persona skill loaded, which tools ran, and which replay proves it. Marco Turn 4 appears twice because the workshop first shows the stubbed check_inventory, then the wired warehouse answer after the build."
    />

    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {JOURNEYS.map((j) => (
        <PersonaSection key={j.id} journey={j} />
      ))}
    </div>

    <div
      style={{
        marginTop: '32px',
        padding: '18px 20px',
        background: 'var(--dl-ink)',
        border: '1px solid color-mix(in srgb, var(--dl-accent-soft) 18%, transparent)',
        borderRadius: 'var(--dl-r-lg)',
        fontFamily: 'var(--obs-mono)',
        fontSize: '12.5px',
        lineHeight: 1.6,
        color: 'var(--dl-accent-soft)',
      }}
    >
      <p
        style={{
          margin: '0 0 12px',
          lineHeight: 1.6,
        }}
      >
        <span style={{ color: '#8a8270' }}>-- backend trace markers</span>
        {'\n'}
        <span style={{ color: '#f7c873' }}>skills.route</span>
        <span> loaded + considered skills</span>
        {'\n'}
        <span style={{ color: '#f7c873' }}>tool.start / tool.done</span>
        <span> lifecycle + latency for every tool call</span>
        {'\n'}
        <span style={{ color: '#f7c873' }}>chat_stream.done</span>
        <span> compact per-turn tool waterfall</span>
        {'\n'}
        <span style={{ color: '#8a8270' }}>
          -- Pellier "Under the hood" is the shopper-facing view of the same events.
        </span>
      </p>
      <Link
        to="/observatory/architecture/grounding"
        style={{ color: '#e8927c', textDecoration: 'none' }}
      >
        → Read the architecture brief on Grounding (the capability ladder
        in detail)
      </Link>
    </div>
  </div>
);

export default PersonaJourneys;
