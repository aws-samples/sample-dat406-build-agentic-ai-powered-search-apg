/**
 * MemoryDetail - Architecture detail page for Memory.
 *
 * Four substrates (working / semantic / episodic / procedural), each
 * shown in its own panel with honest provenance.
 */

import React from 'react';
import DetailPageShell from './DetailPageShell';
import { ExpCard, CategoryBadge } from '../../../components';
import { useAgentTraceData } from '../../../hooks/useAgentTraceData';
import { usePersona } from '../../../../contexts/PersonaContext';
import type {
  MemoryState,
  MemorySubstratePanel,
  MemoryItem,
} from '../../../types';
import { ARCHITECTURE_CODE_BLOCK } from './codeStyles';

/* Anonymous / unknown personas fall through to Marco, the required path
 * persona, so the brief starts from the workshop's primary memory path. */
const MEMORY_PERSONA_IDS: ReadonlySet<string> = new Set(['marco', 'anna', 'theo']);

/* -----------------------------------------------------------------------
 * Source pill - tiny chip beside each panel header so attendees can
 * see whether each substrate read live or is waiting on async extraction.
 * ----------------------------------------------------------------------- */

const SOURCE_COPY: Record<MemorySubstratePanel['source'], { label: string; bg: string; fg: string }> = {
  live: { label: 'Live', bg: 'var(--at-status-shipped-bg)', fg: 'var(--at-status-shipped-text)' },
  settling: { label: 'Settling', bg: 'var(--at-status-exercise-bg)', fg: 'var(--at-status-exercise-text)' },
};

const SourcePill: React.FC<{ source: MemorySubstratePanel['source'] }> = ({ source }) => {
  const { label, bg, fg } = SOURCE_COPY[source];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 8px',
        borderRadius: '999px',
        background: bg,
        color: fg,
        fontFamily: 'var(--at-mono)',
        fontSize: '9px',
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        fontWeight: 600,
      }}
    >
      {source === 'live' ? '● ' : ''}
      {label}
    </span>
  );
};

/* -----------------------------------------------------------------------
 * Provenance legend - one-liner that explains the Live source pill.
 * ----------------------------------------------------------------------- */

const ProvenanceLegend: React.FC = () => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '10px',
      fontFamily: 'var(--at-sans)',
      fontSize: '12px',
      lineHeight: 1.5,
      color: 'var(--at-ink-2)',
    }}
  >
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
      <SourcePill source="live" />
      <span>read from the real source on this request</span>
    </span>
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
      <SourcePill source="settling" />
      <span>read succeeded, but async extraction has not produced records yet</span>
    </span>
  </span>
);

/* -----------------------------------------------------------------------
 * Substrate panel - one of the four cards in the 2x2 grid below the
 * tier cards. Shows the items the route returned, with provenance.
 * ----------------------------------------------------------------------- */

interface SubstratePanelProps {
  panel: MemorySubstratePanel;
}

const SubstratePanel: React.FC<SubstratePanelProps> = ({ panel }) => (
  <ExpCard>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            fontFamily: 'var(--at-mono)',
            fontSize: '9px',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: 'var(--at-ink-4)',
            fontWeight: 500,
          }}
        >
          {panel.label}
        </span>
        <SourcePill source={panel.source} />
      </div>
      <span
        style={{
          fontFamily: 'var(--at-mono)',
          fontSize: '11px',
          color: 'var(--at-ink-2)',
          letterSpacing: '0.02em',
        }}
      >
        {panel.store}
      </span>

      {panel.caveat && (
        <p
          style={{
            fontFamily: 'var(--at-sans)',
            fontSize: '12.5px',
            lineHeight: 1.5,
            color: 'var(--at-ink-2)',
            margin: 0,
            paddingLeft: '10px',
            borderLeft: '2px solid var(--at-ink-4)',
          }}
        >
          {panel.caveat}
        </p>
      )}

      {panel.items.length === 0 ? (
        <p
          style={{
            fontFamily: 'var(--at-sans)',
            fontSize: '13px',
            color: 'var(--at-ink-4)',
            margin: 0,
          }}
        >
          No items for this persona yet.
        </p>
      ) : (
        <ul
          style={{
            listStyle: 'none',
            padding: 0,
            margin: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {panel.items.map((item) => (
            <SubstrateItem key={item.id} item={item} />
          ))}
        </ul>
      )}
    </div>
  </ExpCard>
);

const SubstrateItem: React.FC<{ item: MemoryItem }> = ({ item }) => {
  const meta: string[] = [];
  if (item.tsOffsetDays != null) meta.push(`${item.tsOffsetDays}d`);
  if (item.similarity != null) meta.push(item.similarity.toFixed(2));

  return (
    <li
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: '10px',
        padding: '8px 10px',
        background: 'var(--at-cream-2)',
        border: '1px solid var(--at-card-border)',
        borderRadius: '6px',
      }}
    >
      <span
        style={{
          fontFamily: 'var(--at-sans)',
          fontSize: '13px',
          lineHeight: 1.5,
          color: 'var(--at-ink-1)',
          flex: 1,
        }}
      >
        {item.content}
      </span>
      {meta.length > 0 && (
        <span
          style={{
            fontFamily: 'var(--at-mono)',
            fontSize: '11px',
            color: 'var(--at-ink-4)',
            letterSpacing: '0.04em',
            flexShrink: 0,
            paddingTop: '2px',
          }}
        >
          {meta.join(' · ')}
        </span>
      )}
    </li>
  );
};

/* -----------------------------------------------------------------------
 * Tier card - explainer card sitting above the live panels, one per
 * substrate. Same purpose as before: code snippet + role + prose.
 * ----------------------------------------------------------------------- */

interface TierCardProps {
  tierName: string;
  category: 'live' | 'optional';
  title: string;
  role: string;
  prose: string;
  codeSnippet: string;
}

const TierCard: React.FC<TierCardProps> = ({
  tierName,
  category,
  title,
  role,
  prose,
  codeSnippet,
}) => (
  <ExpCard>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span
          style={{
            fontFamily: 'var(--at-mono)',
            fontSize: '9px',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: 'var(--at-ink-4)',
            fontWeight: 500,
          }}
        >
          {tierName}
        </span>
        <CategoryBadge category={category} />
      </div>
      <h3
        style={{
          fontFamily: 'var(--at-heading)',
          fontSize: '22px',
          fontWeight: 400,
          lineHeight: 1.15,
          letterSpacing: '-0.012em',
          color: 'var(--at-ink-1)',
          margin: 0,
        }}
      >
        {title}
      </h3>
      <p
        style={{
          fontFamily: 'var(--at-sans)',
          fontSize: '14px',
          lineHeight: 1.45,
          color: 'var(--at-red-1)',
          margin: 0,
        }}
      >
        {role}
      </p>
      <p
        style={{
          fontFamily: 'var(--at-sans)',
          fontSize: 'var(--at-body-size)',
          lineHeight: 'var(--at-body-leading)',
          color: 'var(--at-ink-1)',
          margin: 0,
        }}
      >
        {prose}
      </p>
      <pre
        style={{
          ...ARCHITECTURE_CODE_BLOCK,
          whiteSpace: 'pre',
        }}
      >
        {codeSnippet}
      </pre>
    </div>
  </ExpCard>
);

/* -----------------------------------------------------------------------
 * Main component
 * ----------------------------------------------------------------------- */

const MemoryDetail: React.FC = () => {
  // Track the global persona from the top-right switcher so the panels
  // reflect the active customer. Anonymous / unknown ids fall back to
  // Marco, the required-path persona.
  const { persona } = usePersona();
  const activePersonaId =
    persona && MEMORY_PERSONA_IDS.has(persona.id) ? persona.id : 'marco';

  // Memory is live-only. Disable the static fallback so API failures do not
  // silently render non-live memory data.
  const { data, loading, error, refetch } = useAgentTraceData<MemoryState>({
    key: `memory-${activePersonaId}`,
    source: 'api',
    allowFixtureFallback: false,
  });

  const liveCount = data
    ? [data.working, data.semantic, data.episodic, data.procedural].filter(
        (p) => p.source === 'live',
      ).length
    : 0;
  const totalItems = data
    ? data.working.items.length +
      data.semantic.items.length +
      data.episodic.items.length +
      data.procedural.items.length
    : 0;

  return (
    <DetailPageShell
      numeral="II"
      conceptName="Memory"
      category="live"
      title="Memory, four substrates."
      prose="Memory has four substrates, each with a different storage, lifetime, and write contract. AgentCore Memory owns working and semantic memory under namespaced keys; Aurora owns episodic and procedural memory through customer_episodic_seed and tool_audit. Every turn reads from all four; only working memory writes on every turn."
      seeInBoutique={{
        href: '/?ask=Pick+up+where+I+left+off',
        label: 'See memory.recall fire on the storefront',
      }}
      cheatSheet={[
        {
          numeral: 'i.',
          text: 'Working - AgentCore Memory holds the last K session turns under user-{id}-session-{sid} (or anon-{sid}). Cheap, bounded, always relevant. Read first on every turn.',
        },
        {
          numeral: 'ii.',
          text: 'Semantic - durable preference facts a USER_PREFERENCE strategy extracts from conversation, stored as AgentCore Memory records under /pellier/preferences/{actorId}/. Learned asynchronously from turns (pre-baked at deploy); read when the specialist needs durable persona context.',
        },
        {
          numeral: 'iii.',
          text: 'Episodic - per-customer events in Aurora. customer_episodic_seed for the seeded story today; orders and returns are the real ledger. Reach into it when the turn earns the latency.',
        },
        {
          numeral: 'iv.',
          text: 'Procedural - patterns of which tool tends to win for which intent, derived from tool_audit. Every ALLOWed tool call writes a row (reads and writes alike); intent / persona_id / success columns are the next ticket. Honest about the gap.',
        },
      ]}
      liveState={
        data
          ? {
              label: 'Current memory state for the active persona. Each substrate reads from its own backing store; the source pill tells you which panels were live on this request.',
              values: [
                { label: 'Live substrates', value: `${liveCount} / 4` },
                { label: 'Items', value: String(totalItems) },
                { label: 'Persona', value: data.persona },
              ],
            }
          : undefined
      }
    >
      {loading && <MemoryLoadingState />}
      {error && <MemoryErrorState message={error} onRetry={refetch} />}

      {!loading && !error && data && (
        <>
          {/* Tier explainer cards - 2x2 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '20px',
              marginBottom: '36px',
            }}
          >
            <TierCard
              tierName="Working - AgentCore Memory"
              category="live"
              title="Session turns"
              role="Per-turn append, namespace-scoped"
              prose={`Every authenticated turn ends with append_session_turn(session_ns, turn). Reads via get_session_history bring the last K turns back. Namespace is user-{user_id}-session-{session_id} or anon-{session_id} - physically disjoint so a sign-in flip never silently merges history. Dashes (not colons) because AgentCore session IDs must match [a-zA-Z0-9][a-zA-Z0-9-_]*.`}
              codeSnippet={`# Working - AgentCore Memory
ns = AgentCoreIdentityService.build_namespace(user_id, session_id)
# → "user-{user_id}-session-{session_id}" or "anon-{session_id}"
await memory.append_session_turn(ns, turn)

# Last K turns back into the prompt
history = await memory.get_session_history(ns)`}
            />
            <TierCard
              tierName="Semantic - AgentCore Memory"
              category="live"
              title="Extracted preferences"
              role="Learned from turns, read on every relevant turn"
              prose={`Stable taste signals - fabric, palette, occasion - a USER_PREFERENCE strategy extracts from conversation into durable AgentCore Memory records under /pellier/preferences/{actorId}/. Extraction is asynchronous; when no records exist yet, the semantic panel shows Settling rather than calling the state live or showing seeded prose.`}
              codeSnippet={`# Semantic - AgentCore Memory (USER_PREFERENCE)
prefs = await memory.get_semantic_memories(
    actor_id  # e.g. "CUST-MARCO"
)
# → ["Prefers lightweight linen in warm neutrals", ...]
# records live under /pellier/preferences/{actor_id}/`}
            />
            <TierCard
              tierName="Episodic - Aurora"
              category="live"
              title="Per-customer events"
              role="What this customer has done over time"
              prose="Aurora as system of record. customer_episodic_seed holds 3-6 curated summaries per persona today (with ts_offset_days); orders and returns are the real per-customer ledger that production episodic recall would derive from."
              codeSnippet={`# Episodic - Aurora customer_episodic_seed
seed = await fetch_episodic_seed(customer_id)
# -> [{summary_text, ts_offset_days}, ...]

# Real ledger lives in orders + returns
SELECT product_id, placed_at FROM pellier.orders
WHERE customer_id = $1
ORDER BY placed_at DESC;`}
            />
            <TierCard
              tierName="Procedural - Aurora"
              category="live"
              title="Tool patterns"
              role="What tends to work, learned from tool_audit"
              prose="Aggregate stats over tool_audit: which tools win, at what latency, for which cohorts. Every ALLOWed tool call writes a row (reads and writes), so the per-tool signal is complete; intent, persona_id, and success columns are the next ticket. Honest about the gap."
              codeSnippet={`# Procedural - aggregate over tool_audit
SELECT tool,
       count(*)        AS calls,
       avg(latency_ms) AS avg_ms
  FROM pellier.tool_audit
 GROUP BY tool;`}
            />
          </div>

          {/* Live substrate panels - 2x2 with provenance pills */}
          <div
            style={{
              marginBottom: '12px',
              display: 'flex',
              alignItems: 'baseline',
              flexWrap: 'wrap',
              gap: '14px',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--at-mono)',
                fontSize: '9px',
                letterSpacing: '0.22em',
                textTransform: 'uppercase',
                color: 'var(--at-red-1)',
                fontWeight: 500,
              }}
            >
              Live state for {data.persona}
            </span>
            <ProvenanceLegend />
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '16px',
            }}
          >
            <SubstratePanel panel={data.working} />
            <SubstratePanel panel={data.semantic} />
            <SubstratePanel panel={data.episodic} />
            <SubstratePanel panel={data.procedural} />
          </div>
        </>
      )}

      {!loading && !error && !data && <MemoryEmptyState />}
    </DetailPageShell>
  );
};

/* -----------------------------------------------------------------------
 * Loading / error / empty states
 * ----------------------------------------------------------------------- */

const MemoryLoadingState: React.FC = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          style={{
            background: 'var(--at-cream-2)',
            borderRadius: 'var(--at-card-radius)',
            height: '240px',
            opacity: 0.5,
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        />
      ))}
    </div>
  </div>
);

const MemoryErrorState: React.FC<{ message: string; onRetry: () => void }> = ({
  message,
  onRetry,
}) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 24px',
      textAlign: 'center',
    }}
  >
    <p
      style={{
        fontFamily: 'var(--at-sans)',
        fontSize: '16px',
        lineHeight: 1.45,
        color: 'var(--at-ink-1)',
        maxWidth: '420px',
      }}
    >
      We couldn't load the memory data.
    </p>
    <p
      style={{
        fontFamily: 'var(--at-mono)',
        fontSize: '14px',
        color: 'var(--at-ink-4)',
        maxWidth: '480px',
        marginTop: '8px',
      }}
    >
      {message}
    </p>
    <button
      onClick={onRetry}
      style={{
        marginTop: '24px',
        fontFamily: 'var(--at-sans)',
        fontSize: '14px',
        fontWeight: 500,
        color: 'var(--at-cream-1)',
        backgroundColor: 'var(--at-ink-1)',
        border: 'none',
        borderRadius: '8px',
        padding: '10px 24px',
        cursor: 'pointer',
      }}
    >
      Try again
    </button>
  </div>
);

const MemoryEmptyState: React.FC = () => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 24px',
      textAlign: 'center',
    }}
  >
    <p
      style={{
        fontFamily: 'var(--at-sans)',
        fontSize: '16px',
        lineHeight: 1.45,
        color: 'var(--at-ink-1)',
        maxWidth: '420px',
      }}
    >
      No memory data available for this persona.
    </p>
    <p
      style={{
        fontFamily: 'var(--at-sans)',
        fontSize: 'var(--at-body-size)',
        color: 'var(--at-ink-4)',
        maxWidth: '380px',
        marginTop: '8px',
      }}
    >
      Start a conversation in the Boutique, or check that AgentCore Memory and
      Aurora are reachable.
    </p>
  </div>
);

export default MemoryDetail;
