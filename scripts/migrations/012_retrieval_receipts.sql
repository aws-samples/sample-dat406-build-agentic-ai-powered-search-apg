-- Migration 012: durable retrieval receipts.
--
-- Answers the signature governed-search question:
--   "Why did this result appear, what evidence influenced it, and which
--    constraints were enforced?"
--
-- The execution ledger (pellier.tool_audit) records that a tool ran and
-- what it returned. It cannot say why a particular product won: which
-- constraints were hard, which preferences were widened, what each branch
-- ranked, or which merchandising rule reordered the list. This table is
-- that missing half.
--
-- Retention note: one row per retrieval turn. Keyed on session_id and
-- created_at so a workshop box can prune by age without a scan.

\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS pellier.retrieval_receipts (
    receipt_id              BIGSERIAL PRIMARY KEY,
    session_id              TEXT,
    -- Verified security identity. NULL for an anonymous storefront turn;
    -- deliberately separate from any demo persona id, which is never an
    -- authorization principal.
    principal_sub           TEXT,
    -- SHA-256 of the normalized query text. Stored instead of the raw
    -- query so receipts can be grouped and compared without retaining
    -- shopper phrasing indefinitely.
    query_hash              TEXT NOT NULL,
    query_preview           TEXT,
    -- The typed plan that ran, as produced by services/search_plan.py.
    search_plan             JSONB NOT NULL,
    hard_constraints        JSONB NOT NULL DEFAULT '{}'::jsonb,
    soft_preferences        JSONB NOT NULL DEFAULT '{}'::jsonb,
    exclusions              JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Widening steps actually applied. An empty array means the strict
    -- plan was served as written.
    relaxations             JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Provenance of the scoring stack, so a receipt stays interpretable
    -- after a model or index change.
    embedding_model         TEXT,
    rerank_model            TEXT,
    retrieval_config        JSONB NOT NULL DEFAULT '{}'::jsonb,
    index_parameters        JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Per-stage evidence: which candidates existed and how each stage
    -- ranked them.
    candidate_product_ids   JSONB NOT NULL DEFAULT '[]'::jsonb,
    vector_ranks            JSONB NOT NULL DEFAULT '{}'::jsonb,
    lexical_ranks           JSONB NOT NULL DEFAULT '{}'::jsonb,
    rrf_scores              JSONB NOT NULL DEFAULT '{}'::jsonb,
    rerank_scores           JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Ranking signals other than relevance, e.g. a curated merchandising
    -- hero. Recorded so relevance evaluation can subtract them.
    merchandising_rules     JSONB NOT NULL DEFAULT '[]'::jsonb,
    memory_record_ids_used  JSONB NOT NULL DEFAULT '[]'::jsonb,
    citation_ids            JSONB NOT NULL DEFAULT '[]'::jsonb,
    latency_breakdown       JSONB NOT NULL DEFAULT '{}'::jsonb,
    modeled_cost_usd        NUMERIC(12, 6),
    -- Correlates this receipt with the managed trace and the execution
    -- ledger row for the same turn.
    trace_id                TEXT,
    rail                    TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS retrieval_receipts_session_idx
    ON pellier.retrieval_receipts (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS retrieval_receipts_query_hash_idx
    ON pellier.retrieval_receipts (query_hash);

CREATE INDEX IF NOT EXISTS retrieval_receipts_created_at_idx
    ON pellier.retrieval_receipts (created_at DESC);

-- Trace correlation is sparse: only managed-rail turns carry a trace id.
CREATE INDEX IF NOT EXISTS retrieval_receipts_trace_idx
    ON pellier.retrieval_receipts (trace_id)
    WHERE trace_id IS NOT NULL;

COMMIT;
