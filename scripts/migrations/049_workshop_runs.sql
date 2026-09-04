-- Migration 049: one run id on every evidence row a participant leaves.
--
-- A participant's workshop is one run. Before this migration, telling that
-- run's rows apart from the seeded forensic incident, a facilitator's
-- rehearsal, or a previous participant on the same cluster meant guessing
-- from timestamps. Now the application binds the session setting
-- `pellier.run_id` on every pooled connection (services/database.py reads it
-- from services/workshop_run.py), and each evidence table stamps the value
-- through a column DEFAULT. No writer names the column, so no INSERT in the
-- backend, the SQL functions, or the seeders changes.
--
-- Rows written outside the application's pool (the Lambda's Data API path,
-- a psql session, a direct psycopg script) carry NULL unless that session
-- binds the setting itself. The receipt and the doctor treat NULL as "not
-- attributed to a run", never as "did not happen".
--
-- The column is added and its DEFAULT set in two statements on purpose:
-- current_setting() is STABLE, so a single ADD COLUMN ... DEFAULT would
-- evaluate it once at migration time and stamp every pre-existing row with
-- whatever the migrating session happened to have bound. Pre-existing rows
-- must stay NULL.

\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS pellier.workshop_runs (
    run_id      TEXT PRIMARY KEY CHECK (run_id ~ '^run-[0-9a-f]{12}$'),
    persona     TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes       JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE pellier.workshop_runs IS
    'One row per participant workshop run; run_id is the value bound as pellier.run_id.';
COMMENT ON COLUMN pellier.workshop_runs.started_at IS
    'When workshop-start minted the run; rows written outside the pool are scoped by this.';

ALTER TABLE pellier.tool_audit
    ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE pellier.tool_audit
    ALTER COLUMN run_id SET DEFAULT current_setting('pellier.run_id', true);

ALTER TABLE pellier.retrieval_receipts
    ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE pellier.retrieval_receipts
    ALTER COLUMN run_id SET DEFAULT current_setting('pellier.run_id', true);

ALTER TABLE pellier.governed_turn_receipts
    ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE pellier.governed_turn_receipts
    ALTER COLUMN run_id SET DEFAULT current_setting('pellier.run_id', true);

ALTER TABLE pellier.execution_receipts
    ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE pellier.execution_receipts
    ALTER COLUMN run_id SET DEFAULT current_setting('pellier.run_id', true);

ALTER TABLE pellier.write_operations
    ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE pellier.write_operations
    ALTER COLUMN run_id SET DEFAULT current_setting('pellier.run_id', true);

ALTER TABLE pellier.governed_receipts
    ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE pellier.governed_receipts
    ALTER COLUMN run_id SET DEFAULT current_setting('pellier.run_id', true);

-- pellier.policy_decisions is created by migration 048. Guarded so this file
-- also applies cleanly to a cluster where 048 has not run yet; re-running 049
-- after 048 lands adds the column then.
DO $$
BEGIN
    IF to_regclass('pellier.policy_decisions') IS NOT NULL THEN
        ALTER TABLE pellier.policy_decisions
            ADD COLUMN IF NOT EXISTS run_id TEXT;
        ALTER TABLE pellier.policy_decisions
            ALTER COLUMN run_id SET DEFAULT current_setting('pellier.run_id', true);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS tool_audit_run_idx ON pellier.tool_audit (run_id);

GRANT SELECT, INSERT ON pellier.workshop_runs TO pellier_agent;

COMMIT;
