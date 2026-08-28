-- Migration 027: converge the span table onto its canonical name.
--
-- WHY THIS EXISTS
--
-- The repository contract is explicit: Observatory is the single name for the inspection
-- surface, and `Agent Trace` is retired "in every casing and separator ... No component,
-- module, file, route, class, test id, API path, CSS variable, or database object carries
-- either." `tests/test_surface_naming.py` enforces it across the repository.
--
-- The live cluster on 2026-08-27 still had `pellier.agent_trace_spans` and no
-- `pellier.observatory_spans`. A DATABASE OBJECT carried the retired name, which is
-- precisely what the contract forbids.
--
-- WHY NOT JUST RE-RUN 002
--
-- Migration 002 already contains the correct rename and the canonical CREATE, so a FRESH
-- chain has never been wrong: 002 creates `observatory_spans`, and its rename block is a
-- no-op. This cluster is simply stale — it ran 002 before that block existed and has not
-- run it since. Re-running 002 out of order would replay a large telemetry migration
-- including a `public` -> `pellier` relocation loop, to fix one empty table. A narrow
-- forward migration is the smaller and more predictable change.
--
-- WHAT IT DOES, in the only three states a cluster can be in
--
--   only agent_trace_spans      rename it, and its indexes, in place
--   both tables                 the retired one is a leftover: drop it IF EMPTY,
--                               and refuse loudly if it is not, because silently
--                               discarding span rows is worse than stopping
--   only observatory_spans      no-op
--
-- Forward-only, idempotent, fresh-stack safe and stale-stack convergent. No data is
-- moved and none is discarded without being empty first.

\set ON_ERROR_STOP on

DO $$
DECLARE
    v_retired  BOOLEAN;
    v_canonical BOOLEAN;
    v_rows     BIGINT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'pellier' AND table_name = 'agent_trace_spans'
    ) INTO v_retired;
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'pellier' AND table_name = 'observatory_spans'
    ) INTO v_canonical;

    IF NOT v_retired THEN
        RAISE NOTICE 'migration 027: no retired span table; nothing to converge';
        RETURN;
    END IF;

    IF NOT v_canonical THEN
        -- Stale cluster: rename in place. The index names carry the old table name too,
        -- including the primary key's implicit one, so a converged cluster and a fresh
        -- one agree on every identifier rather than differing by three index names.
        ALTER TABLE pellier.agent_trace_spans RENAME TO observatory_spans;
        ALTER INDEX IF EXISTS pellier.agent_trace_spans_session_idx
            RENAME TO observatory_spans_session_idx;
        ALTER INDEX IF EXISTS pellier.agent_trace_spans_created_idx
            RENAME TO observatory_spans_created_idx;
        ALTER INDEX IF EXISTS pellier.agent_trace_spans_pkey
            RENAME TO observatory_spans_pkey;
        RAISE NOTICE
            'migration 027: renamed pellier.agent_trace_spans to observatory_spans';
        RETURN;
    END IF;

    -- Both exist. The retired one is a leftover from a partial convergence.
    EXECUTE 'SELECT count(*) FROM pellier.agent_trace_spans' INTO v_rows;
    IF v_rows > 0 THEN
        RAISE EXCEPTION
            'migration 027: pellier.agent_trace_spans holds % row(s) and '
            'pellier.observatory_spans already exists. Refusing to drop span data. '
            'Merge or archive the rows, then re-run.', v_rows;
    END IF;
    DROP TABLE pellier.agent_trace_spans;
    RAISE NOTICE
        'migration 027: dropped the empty retired pellier.agent_trace_spans';
END $$;

-- ---------------------------------------------------------------------
-- Post-condition: the retired object is gone and the canonical one is here
-- ---------------------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'pellier' AND table_name = 'agent_trace_spans'
    ) THEN
        RAISE EXCEPTION
            'migration 027: pellier.agent_trace_spans still exists after convergence';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'pellier' AND table_name = 'observatory_spans'
    ) THEN
        RAISE EXCEPTION
            'migration 027: pellier.observatory_spans is absent after convergence';
    END IF;
    -- The index names must match a fresh cluster's, or two deployments of the same
    -- application diff on identifiers nobody thinks to check.
    IF EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname = 'pellier' AND indexname LIKE 'agent_trace_spans%'
    ) THEN
        RAISE EXCEPTION
            'migration 027: an index still carries the retired table name';
    END IF;
    RAISE NOTICE 'migration 027: span table is canonical';
END $$;
