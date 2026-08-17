/**
 * PersonaJourneys — the workshop's narrative spine in one screen.
 *
 * Three returning personas (Marco / Anna / Theo) each surface five Pellier
 * hero pills from `PERSONA_HERO_PILLS` — the same strings as the
 * storefront "Try asking" row. For each turn we list agent / tool /
 * model / outcome and link into captured session fixtures when they
 * exist (Marco Turn 5 links twice: opening demo = floor_check stub,
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
  skills: string[];
  tool?: string;
  outcome: string;
  /** Primary Pellier Labs fixture for this turn (stub path, or only path). */
  sessionId?: string;
  /** When set, second fixture shows the post-build / wired path (e.g. floor_check). */
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

type JourneyTurnMeta = Omit<JourneyTurn, 'pill' | 'n' | 'skills'>;

const MARCO_TURNS_META: JourneyTurnMeta[] = [
  {
    agent: 'Style Advisor',
    model: 'Claude Opus 5',
    outcome: 'Category browse opens a carry-on linen edit without inventing intent.',
    sessionId: 'marco-opening-demo',
  },
  {
    agent: 'Style Advisor',
    model: 'Claude Opus 5',
    outcome: 'Hadley resolves first; style_match returns packable companions.',
    sessionId: 'marco-opening-demo',
  },
  {
    agent: 'Style Advisor',
    model: 'Claude Opus 5',
    outcome: 'Two named shirts resolve to product IDs before a factual comparison.',
    sessionId: 'marco-capstone',
  },
  {
    agent: 'Value Analyst',
    model: 'Claude Sonnet 5',
    outcome: 'A deterministic price distribution keeps the answer numerical.',
    sessionId: 'marco-opening-demo',
  },
  {
    agent: 'Stock Keeper',
    model: 'Claude Sonnet 5',
    outcome:
      'Opening path preserves the floor_check stub; the midpoint replay shows the real Brooklyn breakdown after the build.',
    sessionId: 'marco-opening-demo',
    wiredSessionId: 'marco-midpoint-checkpoint',
  },
];

const ANNA_TURNS_META: JourneyTurnMeta[] = [
  {
    agent: 'Curator',
    model: 'Claude Opus 5',
    outcome:
      'Gift and maker skills shape a ceramics-first hybrid result under budget.',
    sessionId: 'anna-morning-ritual',
  },
  {
    agent: 'Curator',
    model: 'Claude Opus 5',
    outcome: 'Aurora preference proof is read before hybrid retrieval uses past orders.',
    sessionId: 'anna-under-100',
  },
  {
    agent: 'Curator',
    model: 'Claude Opus 5',
    outcome: 'Popularity is answered by whats_trending rather than another search.',
    sessionId: 'anna-candle-pairing',
  },
  {
    agent: 'Curator',
    model: 'Claude Opus 5',
    outcome: 'The Proof Counter reads the latest hybrid-retrieval audit receipt.',
    sessionId: 'anna-birthday-gift',
  },
  {
    agent: 'Curator',
    model: 'Claude Opus 5',
    outcome:
      'Sympathy gifting goes directly to a person; retrieval cannot read the room.',
    sessionId: 'anna-housewarming',
  },
];

const THEO_TURNS_META: JourneyTurnMeta[] = [
  {
    agent: 'Style Advisor',
    model: 'Claude Opus 5',
    outcome: 'Maker language grounds a semantic search in hand-thrown home objects.',
    sessionId: 'theo-pour-over',
  },
  {
    agent: 'Experience Guide',
    model: 'Claude Opus 5',
    outcome: 'The linen throw resolves before its care guidance and return window.',
    sessionId: 'theo-linen-seasons',
  },
  {
    agent: 'Experience Guide',
    model: 'Claude Opus 5',
    outcome: 'Read-before-write order resolves product and policy before filing.',
    sessionId: 'theo-ceramics-return',
  },
  {
    agent: 'Experience Guide',
    model: 'Claude Opus 5',
    outcome: 'The Proof Counter reads tool_audit to verify that the return exists.',
    sessionId: 'theo-pour-over-pairing',
  },
  {
    agent: 'Experience Guide',
    model: 'Claude Opus 5',
    outcome:
      'A known out-of-window durability exception bypasses a doomed write and escalates.',
    sessionId: 'theo-home-not-wardrobe',
  },
];

function attachPills(
  meta: JourneyTurnMeta[],
  pills: string[],
  traces: Array<{ skills: string[]; tools: string[] }>,
): JourneyTurn[] {
  return meta.map((m, idx) => ({
    n: idx + 1,
    pill: pills[idx],
    ...m,
    skills: traces[idx]?.skills ?? [],
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
      "Returning customer. Marco's five turns move from category browse to pairing, comparison, price intelligence, and live inventory. Turn 5 remains the workshop build: the opening path shows the floor_check gap, then the midpoint replay proves the wired result.",
    turns: attachPills(MARCO_TURNS_META, PERSONA_HERO_PILLS.marco, PERSONA_TURN_TRACES.marco),
    capstoneNote:
      "Claude Opus 5 handles editorial discovery and comparison; Claude Sonnet 5 handles numerical and inventory reporting. Turn 5 is where the wiring exercise lands.",
  },
  {
    id: 'anna',
    displayName: 'Anna',
    capability: 'hybrid + Cohere Rerank v3.5',
    capabilityRole: 'Capability 2 · when pure vector wears thin',
    blurb:
      "Gift-giver - observe and learn only. Anna's arc demonstrates hybrid retrieval, Aurora preference proof, popularity ranking, audit receipts, and an honest human handoff.",
    turns: attachPills(ANNA_TURNS_META, PERSONA_HERO_PILLS.anna, PERSONA_TURN_TRACES.anna),
    capstoneNote:
      "Her first two turns show where hybrid retrieval earns its cost; the later turns prove that retrieval, memory, audit, and escalation are separate capabilities.",
  },
  {
    id: 'theo',
    displayName: 'Theo',
    capability: 'Aurora as agent system-of-record',
    capabilityRole: 'Capability 3 · writes leave a paper trail',
    blurb:
      "Slow-craft buyer - observe and learn only. Theo's arc moves from discovery to care, a read-before-write return, receipt proof, and a durability exception that requires human judgment.",
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
            to={`/pellier-labs/sessions/${turn.sessionId}`}
            style={{
              fontFamily: 'var(--at-mono)',
              fontSize: '11px',
              color: 'var(--at-burgundy)',
              textDecoration: 'none',
            }}
          >
            {sessionLinkLabel(turn.sessionId, turn.wiredSessionId ? 'stub / arc' : 'replay')}
            →
          </Link>
        )}
        {turn.wiredSessionId && (
          <Link
            to={`/pellier-labs/sessions/${turn.wiredSessionId}`}
            style={{
              fontFamily: 'var(--at-mono)',
              fontSize: '11px',
              color: 'var(--at-burgundy)',
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
        borderTop: isFirst ? 'none' : '1px solid var(--at-card-border)',
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
            fontFamily: 'var(--at-mono)',
            fontSize: '13px',
            color: 'var(--at-ink-3)',
            paddingTop: '2px',
          }}
        >
          T{turn.n}
        </span>

        <div>
          <div
            style={{
              fontFamily: 'var(--at-sans)',
              fontSize: '14px',
              color: 'var(--at-ink-1)',
              marginBottom: '4px',
            }}
          >
            “{turn.pill}”
          </div>
          <div
            style={{
              fontFamily: 'var(--at-sans)',
              fontSize: '13px',
              color: 'var(--at-ink-2)',
              lineHeight: 1.55,
            }}
          >
            {turn.outcome}
          </div>
          {links}
        </div>

        <div
          style={{
            fontFamily: 'var(--at-mono)',
            fontSize: '12px',
            color: 'var(--at-ink-3)',
            textAlign: 'right' as const,
            lineHeight: 1.6,
          }}
        >
          <div style={{ color: 'var(--at-ink-1)' }}>{turn.agent}</div>
          <div>{turn.model}</div>
          {turn.skills.map((skill) => (
            <div key={skill}>skill.{skill}</div>
          ))}
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
          fontFamily: 'var(--at-mono)',
          fontSize: '12px',
          color: 'var(--at-burgundy)',
        }}
      >
        {journey.capability}
      </code>
    </div>
    <h2
      className="font-display text-espresso"
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
        fontFamily: 'var(--at-sans)',
        fontSize: '14px',
        lineHeight: 1.6,
        color: 'var(--at-ink-2)',
        marginBottom: '20px',
      }}
    >
      {journey.blurb}
    </p>

    <div
      style={{
        border: '1px solid var(--at-card-border)',
        borderRadius: '6px',
        background: 'var(--at-cream-1)',
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
          borderTop: '1px solid var(--at-card-border)',
          fontFamily: 'var(--at-sans)',
          fontSize: '13px',
          color: 'var(--at-ink-2)',
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
  <div className="pellier-labs-reference-page" style={{ maxWidth: '1100px' }}>
    <EditorialTitle
      eyebrow="Observe · Persona Journeys · 15 Pellier hero turns"
      title="Canonical journeys"
      summary="Compare the storefront prompts with their selected specialist, prompt overlays, tools, and replay evidence."
      references={[
        { label: 'Source', value: 'data/personaCurations.ts', code: true },
        { label: 'Pattern', value: 'storefront prompt -> replay fixture', code: true },
      ]}
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
        fontFamily: 'var(--dl-font-mono)',
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
        to="/pellier-labs/architecture/grounding"
        style={{ color: '#e8927c', textDecoration: 'none' }}
      >
        → Read the architecture brief on Grounding (the capability ladder
        in detail)
      </Link>
    </div>
  </div>
);

export default PersonaJourneys;
