-- Migration 022: converge write_operations.operation on the current vocabulary.
--
-- WHY THIS EXISTS
--
-- Migration 019 widened `write_operations_operation_check` to the renamed
-- vocabulary (`initiate_return`, `restock_inventory`, `issue_credit`) while the
-- live `pellier.process_return_idempotent` body still inserted the retired
-- `'process_return'`. Nothing noticed, because no governed write had run since.
-- The first real one failed with:
--
--   new row for relation "write_operations" violates check constraint
--   "write_operations_operation_check"
--
-- Re-applying 011 by hand fixes it, but an account provisioned from scratch runs
-- the migrations in order and would land in the same split the moment 019 runs
-- after an older 011. This migration closes that permanently: it is forward-only,
-- idempotent, and it asserts the two halves agree before it finishes.
--
-- WHAT IS AND IS NOT RENAMED
--
--   public tool          initiate_return          the participant-facing name
--   DB function          process_return_idempotent UNCHANGED — migration 016
--                                                 grants EXECUTE on this exact
--                                                 identifier, and renaming it
--                                                 revokes permission on every
--                                                 deployed cluster
--   operation value      initiate_return          what new rows carry
--   historical rows      process_return           left exactly as written
--
-- Historical rows are NOT rewritten. A `write_operations` row is a durable record
-- of a write that actually happened under the vocabulary in force at the time;
-- editing it would falsify evidence to make a report tidier. The constraint
-- therefore continues to admit the retired value so those rows stay valid, while
-- new rows use the current one.

\set ON_ERROR_STOP on

BEGIN;

-- ---------------------------------------------------------------------
-- The constraint admits current values AND the historical one
-- ---------------------------------------------------------------------

ALTER TABLE pellier.write_operations
    DROP CONSTRAINT IF EXISTS write_operations_operation_check;

ALTER TABLE pellier.write_operations
    ADD CONSTRAINT write_operations_operation_check
    CHECK (operation IN (
        -- current vocabulary
        'initiate_return',
        'restock_inventory',
        'issue_credit',
        -- historical, retained so pre-rename evidence rows remain valid
        'process_return',
        'restock_shelf'
    ));

COMMIT;

-- ---------------------------------------------------------------------
-- Assert the function body and the constraint agree
-- ---------------------------------------------------------------------
--
-- This is the check that would have caught the original split. It reads what the
-- deployed function actually inserts rather than trusting that some earlier
-- migration was re-applied.

DO $$
DECLARE
    v_src      TEXT;
    v_inserted TEXT;
    v_allowed  TEXT;
BEGIN
    SELECT pg_get_functiondef(p.oid) INTO v_src
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'pellier'
       AND p.proname = 'process_return_idempotent'
     LIMIT 1;

    IF v_src IS NULL THEN
        RAISE EXCEPTION
            'migration 022: pellier.process_return_idempotent is missing; '
            'apply 011_governed_write_integrity.sql first';
    END IF;

    -- The literal this function writes into write_operations.operation.
    v_inserted := substring(
        v_src
        from 'INSERT INTO pellier\.write_operations\s*\([^)]*\)\s*VALUES\s*\(\s*p_idempotency_key,\s*''([a-z_]+)'''
    );

    IF v_inserted IS NULL THEN
        RAISE EXCEPTION
            'migration 022: could not read the operation literal from '
            'pellier.process_return_idempotent; the function body changed shape';
    END IF;

    SELECT pg_get_constraintdef(oid) INTO v_allowed
      FROM pg_constraint WHERE conname = 'write_operations_operation_check';

    IF position(v_inserted IN v_allowed) = 0 THEN
        RAISE EXCEPTION
            'migration 022: pellier.process_return_idempotent inserts operation '
            '%, which write_operations_operation_check does not admit (%). '
            'Re-apply 011_governed_write_integrity.sql so the function body '
            'matches the current vocabulary.',
            v_inserted, v_allowed;
    END IF;

    IF v_inserted <> 'initiate_return' THEN
        RAISE WARNING
            'migration 022: the return function still inserts %, not '
            'initiate_return. The constraint admits it, so writes will succeed, '
            'but new evidence rows will carry the retired vocabulary. Re-apply '
            '011_governed_write_integrity.sql to converge.',
            v_inserted;
    END IF;

    RAISE NOTICE
        'migration 022: write vocabulary converged (function inserts %, '
        'constraint admits current + historical values)', v_inserted;
END $$;

-- ---------------------------------------------------------------------
-- Self-probe: a current-vocabulary row is accepted, a bogus one is not
-- ---------------------------------------------------------------------

DO $$
DECLARE
    v_key    TEXT := 'migration-022-probe';
    v_failed BOOLEAN;
BEGIN
    INSERT INTO pellier.write_operations (idempotency_key, operation, request_hash)
    VALUES (v_key, 'initiate_return', repeat('a', 64));

    -- A historical value must still be insertable, or old rows could not be
    -- restored from a backup.
    INSERT INTO pellier.write_operations (idempotency_key, operation, request_hash)
    VALUES (v_key || '-historical', 'process_return', repeat('b', 64));

    v_failed := FALSE;
    BEGIN
        INSERT INTO pellier.write_operations (idempotency_key, operation, request_hash)
        VALUES (v_key || '-bogus', 'delete_everything', repeat('c', 64));
    EXCEPTION WHEN check_violation THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 022: the constraint accepted an unknown operation';
    END IF;

    DELETE FROM pellier.write_operations WHERE idempotency_key LIKE v_key || '%';
    RAISE NOTICE 'migration 022: constraint verified (current + historical accepted, unknown rejected)';
END $$;
