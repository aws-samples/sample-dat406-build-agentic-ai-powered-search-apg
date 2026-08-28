-- Migration 024: pellier.operator_episodes — durable episodic memory for the desk.
--
-- WHY THIS EXISTS
--
-- Pellier's memory model names four substrates with different owners:
--
--   working     AgentCore Memory   the session timeline
--   semantic    AgentCore Memory   USER_PREFERENCE, what to remember about a person
--   episodic    Aurora             what actually happened, and how it ended
--   procedural  the repository     checked-in skills and MCP tool contracts
--
-- The episodic substrate has been read-only narrative so far:
-- `pellier.customer_episodic_seed` (migration 003) is demo material that the memory
-- surfaces render. It is not a store any workflow writes to, and it must not be
-- mistaken for one — a seeded "successful past resolution" is a story, not evidence.
--
-- This migration creates the real one. An episode is a SIGNIFICANT DURABLE OUTCOME:
-- a situation, what was decided, what the governance layers said, what the database
-- did, and how it ended. Not one row per conversational turn. A client summary that
-- read five orders is not an episode, and writing one for every turn would turn the
-- table into a second, worse copy of `pellier.messages`.
--
-- WHAT MAKES IT EPISODIC RATHER THAN AUDIT
--
-- `pellier.tool_audit` records that a tool ran with certain arguments.
-- `pellier.write_operations` records that a write applied exactly once.
-- Neither answers "what kind of situation was this, and did the resolution hold?"
-- That question needs the human decision, the policy decision and the database
-- outcome in one row, keyed back to the turn that proposed it — which is what
-- `source_turn_id` is for. The existing correlation family reaches all the way here:
--
--   session_id -> turn_id -> review_id -> execution_turn_id -> tool_audit / domain
--
-- so no new identifier family is introduced.
--
-- FORWARD-ONLY AND IDEMPOTENT
--
-- Additive: one table, four indexes, no changes to existing objects. Re-running is
-- safe. No seed rows: an empty episode store is the honest state until a governed
-- resolution actually completes, and the retrieval path is expected to return
-- "no prior episodes" until then.

\set ON_ERROR_STOP on

BEGIN;

-- ---------------------------------------------------------------------
-- The episode store
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pellier.operator_episodes (
    episode_id        BIGSERIAL PRIMARY KEY,

    -- Who the episode is about. Text rather than a FK to pellier.customers so an
    -- episode survives a customer row being reworked; the desk always resolves the
    -- customer separately anyway.
    customer_id       TEXT NOT NULL,

    -- Lineage back into the existing correlation family. The turn that produced the
    -- episode, and the thread it happened in. Nullable because an episode may be
    -- recorded by a background reconciliation that has no conversational turn.
    source_turn_id    TEXT,
    session_id        TEXT,

    -- What KIND of situation this was. Constrained, because an open vocabulary here
    -- becomes unqueryable within a month. Widen it in a later forward migration when
    -- a genuinely new kind appears.
    episode_type      TEXT NOT NULL
                      CHECK (episode_type IN (
                          'return_resolution',
                          'replacement_offered',
                          'credit_issued',
                          'escalation',
                          'inventory_correction'
                      )),

    -- The situation in one or two sentences, for a human and for FTS.
    situation         TEXT NOT NULL,

    -- What the desk knew, and what it did. JSONB because the useful shape differs
    -- per episode_type and a wide sparse column set would be worse.
    evidence_summary  JSONB NOT NULL DEFAULT '{}'::jsonb,
    action_summary    JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- The three independent outcomes Pellier keeps apart everywhere else, kept apart
    -- here too. A human approval is not a policy ALLOW, and neither one proves the
    -- database changed anything.
    --
    --   human_outcome    confirmed / declined / not_required / pending
    --   policy_outcome   allow / deny / not_evaluated
    --   aurora_outcome   applied / refused / rolled_back / not_attempted
    human_outcome     TEXT NOT NULL DEFAULT 'not_required'
                      CHECK (human_outcome IN
                          ('confirmed', 'declined', 'not_required', 'pending')),
    policy_outcome    TEXT NOT NULL DEFAULT 'not_evaluated'
                      CHECK (policy_outcome IN ('allow', 'deny', 'not_evaluated')),
    aurora_outcome    TEXT NOT NULL DEFAULT 'not_attempted'
                      CHECK (aurora_outcome IN
                          ('applied', 'refused', 'rolled_back', 'not_attempted')),

    -- How it ended, in the desk's own words.
    resolution        TEXT NOT NULL DEFAULT '',

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Same dimension and same distance operator as every other embedding in this
    -- schema, so one embedding configuration serves the whole application.
    -- Nullable: an episode is durable the moment it happens, and embedding it is a
    -- separate concern that must not be able to fail the write.
    embedding         vector(1024)
);

-- One episode per turn per type. A retried write must not append a second episode
-- for the same outcome, and this is the cheapest place to guarantee it.
CREATE UNIQUE INDEX IF NOT EXISTS operator_episodes_turn_idx
    ON pellier.operator_episodes (source_turn_id, episode_type)
    WHERE source_turn_id IS NOT NULL;

-- The two access patterns the desk actually has: this client's history, newest
-- first, and "what kinds of situation have we seen lately".
CREATE INDEX IF NOT EXISTS operator_episodes_customer_idx
    ON pellier.operator_episodes (customer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS operator_episodes_type_idx
    ON pellier.operator_episodes (episode_type, created_at DESC);

-- Lexical retrieval over the situation text, so an episode search can be hybrid
-- rather than vector-only — the same argument the catalog makes.
CREATE INDEX IF NOT EXISTS operator_episodes_situation_fts_idx
    ON pellier.operator_episodes
    USING gin (to_tsvector('english', situation));

-- No HNSW index yet, deliberately.
--
-- The table starts empty and HNSW on an empty table buys nothing: PostgreSQL will
-- sequentially scan a few hundred rows faster than it will traverse a graph built
-- over them, and `pellier.semantic_cache` (migration 019) only earns its index
-- because it is written on every cache-worthy turn. Episodes accrue one per genuine
-- resolution, so the threshold is roughly a thousand rows — the same figure the
-- catalog's own index notes use. Add it in a forward migration then:
--
--   CREATE INDEX operator_episodes_embedding_idx
--       ON pellier.operator_episodes
--       USING hnsw (embedding vector_cosine_ops);
--
-- Until then `<=>` still works, exactly, over a sequential scan.

COMMENT ON TABLE pellier.operator_episodes IS
    'Episodic memory: one row per significant durable outcome, keyed to the turn that produced it. Not a per-turn log, and distinct from pellier.customer_episodic_seed, which is narrative demo material.';

COMMENT ON COLUMN pellier.operator_episodes.source_turn_id IS
    'The Concierge turn that produced this episode. Ties an episode to tool_audit and write_operations through the existing correlation family.';

COMMENT ON COLUMN pellier.operator_episodes.embedding IS
    'vector(1024), matching the catalog and the semantic cache. Nullable: the episode is durable before it is embeddable.';

COMMIT;
