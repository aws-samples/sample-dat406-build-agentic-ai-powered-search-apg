-- ---------------------------------------------------------------------
-- 017_governed_query_receipts.sql — evidence for generated-SQL execution
--
-- Two things, both about model-generated SQL:
--
--   1. A durable receipt per governed query. Structural validation happens in
--      the application, but "the query was refused" is a claim that needs an
--      artifact, not a log line that rotates away.
--   2. EXECUTE hygiene for `pellier_query`.
--
-- ON EXECUTE PRIVILEGES
--
-- Structural validation proves a statement is a read-only SELECT. It cannot
-- prove the statement has no side effects, because a SELECT may call a
-- function, and a function may do anything its own privileges allow. So the
-- role's EXECUTE grants are an independent boundary rather than a formality.
--
-- PostgreSQL grants EXECUTE on new functions to PUBLIC by default, which means
-- `pellier_query` inherits execute rights on every application function unless
-- something revokes them. That includes `process_return_idempotent` and
-- `restock_shelf_idempotent`: they are SECURITY INVOKER, so a call would run
-- with `pellier_query`'s own (write-less) privileges inside a READ ONLY
-- transaction and fail — but relying on that is relying on two other controls
-- holding. Revoking is the direct statement of intent.
--
-- Idempotent and additive.
-- ---------------------------------------------------------------------

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Governed query receipts
--
-- The generated SQL lives here, and only here. It is deliberately not copied
-- onto spans: a span is broadly readable telemetry, while this table is
-- access-controlled evidence an operator reads on purpose.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pellier.governed_query_receipts (
    receipt_id          BIGSERIAL PRIMARY KEY,
    turn_id             TEXT,
    session_id          TEXT,
    principal_sub       TEXT,
    caller              TEXT        NOT NULL,
    accepted            BOOLEAN     NOT NULL,
    validation          TEXT        NOT NULL,
    rejection_reason    TEXT,
    role_used           TEXT        NOT NULL,
    statement_timeout   TEXT        NOT NULL,
    result_limit        INTEGER     NOT NULL,
    row_count           INTEGER,
    execution_outcome   TEXT        NOT NULL,
    latency_ms          INTEGER,
    schemas_read        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    generated_sql       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A rejected query cannot claim an execution outcome, and an accepted one
    -- must not claim it was refused. The constraint keeps the two evidence
    -- states from blurring into each other.
    CONSTRAINT governed_query_receipts_outcome_agrees CHECK (
        (accepted AND execution_outcome IN ('success', 'error'))
        OR ((NOT accepted) AND execution_outcome = 'not_executed')
    )
);

COMMENT ON TABLE pellier.governed_query_receipts IS
    'One row per model-generated query: whether it was allowed to run, under '
    'which role and limits, and what it returned. The generated SQL lives '
    'here rather than on a span.';

CREATE INDEX IF NOT EXISTS governed_query_receipts_turn_idx
    ON pellier.governed_query_receipts (turn_id, created_at DESC)
    WHERE turn_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS governed_query_receipts_rejected_idx
    ON pellier.governed_query_receipts (created_at DESC)
    WHERE NOT accepted;

-- The agent appends receipts; it does not revise them.
GRANT INSERT ON pellier.governed_query_receipts TO pellier_agent;
GRANT USAGE, SELECT ON SEQUENCE pellier.governed_query_receipts_receipt_id_seq
    TO pellier_agent;
GRANT SELECT (receipt_id) ON pellier.governed_query_receipts TO pellier_agent;

-- Generated SQL must not be able to read, write, or infer the receipt trail,
-- for the same reason it cannot see `tool_audit`: evidence about the query is
-- not the query's business.
REVOKE ALL ON pellier.governed_query_receipts FROM pellier_query;

-- ---------------------------------------------------------------------
-- 2. EXECUTE hygiene for the generated-SQL role
--
-- Revoke the default PUBLIC grant on the application's own functions, then
-- take it away from the role explicitly. Both are needed: revoking from
-- PUBLIC does not remove a grant made directly to the role, and revoking from
-- the role does not remove what it inherits through PUBLIC.
-- ---------------------------------------------------------------------

DO $$
DECLARE
    fn RECORD;
BEGIN
    FOR fn IN
        SELECT p.oid::regprocedure AS signature
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'pellier'
           -- The RLS scope resolver is the one function the read role needs;
           -- policies call it on every scoped read.
           AND p.proname <> 'current_principal_customers'
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', fn.signature);
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM pellier_query', fn.signature);
    END LOOP;
END
$$;

-- Re-grant what the agent legitimately calls. The loop above stripped PUBLIC,
-- which the agent was also relying on.
GRANT EXECUTE ON FUNCTION
    pellier.process_return_idempotent(text, text, text, text, text)
    TO pellier_agent;
GRANT EXECUTE ON FUNCTION
    pellier.restock_shelf_idempotent(text, text, text, integer, text)
    TO pellier_agent;
GRANT EXECUTE ON FUNCTION pellier.current_principal_customers()
    TO pellier_agent, pellier_query;

COMMIT;
