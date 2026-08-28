-- Migration 021: governed execution of a confirmed operator review.
--
-- Prompt 3 ended with a human decision and nothing else: Policy PENDING, Aurora
-- NOT EVALUATED. This migration adds the one piece of durable state the
-- execution attempt needs, and nothing more.
--
-- WHAT THIS DOES NOT DO, deliberately:
--
--   * It does NOT widen `approvals.status`. That column is the HUMAN axis:
--     pending | approved | rejected. Adding `executed`, `policy_denied`, or
--     `rls_denied` would fold three independent controls into one, which is the
--     exact conflation this arc exists to dismantle. Execution and governance
--     state are hydrated from their own artifacts: the policy decision, the
--     `tool_audit` receipt, `write_operations`, and the domain rows.
--
--   * It does NOT copy business truth onto the review. Still no membership, no
--     order state, no inventory, no verdict.
--
-- WHAT IT ADDS: one nullable reference, `execution_turn_id`.
--
-- Theo's shopper turn and the operator's execution attempt are two different
-- logical turns, and reusing one id for both would collapse the lineage the
-- Observatory needs:
--
--     source_turn_id      the Pellier shopper turn that prepared the request
--          ↓
--     review id           human workflow identity
--          ↓
--     execution_turn_id   the governed execution attempt
--          ↓
--     policy decision → tool receipt → Aurora effect
--
-- `execution_turn_id` uses the existing `turn-<32 hex>` format from
-- `services/turn_identity.py::new_turn_id`. It is not a new identifier family.
--
-- It is assigned ONCE, when execution first begins, and reused for every retry
-- of that same logical execution. A new turn id per HTTP retry would make the
-- lineage non-deterministic and would make one confirmed action look like
-- several attempts.
--
-- Idempotent: guarded ALTER plus IF NOT EXISTS.

\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE pellier.approvals
    ADD COLUMN IF NOT EXISTS execution_turn_id TEXT;

-- Observatory resolves an execution attempt back to its review, and the
-- reconciliation path resolves "did this confirmed action already start?".
CREATE INDEX IF NOT EXISTS approvals_execution_turn_idx
    ON pellier.approvals (execution_turn_id)
    WHERE execution_turn_id IS NOT NULL;

-- One execution turn belongs to at most one review. Two reviews sharing an
-- execution turn would make the lineage ambiguous in exactly the place an
-- auditor needs it to be exact.
CREATE UNIQUE INDEX IF NOT EXISTS approvals_execution_turn_unique_idx
    ON pellier.approvals (execution_turn_id)
    WHERE execution_turn_id IS NOT NULL;

-- Execution may only begin after a human said yes. A pending or declined review
-- holding an execution turn means something started without confirmation, and
-- that must be impossible at the storage layer rather than merely unlikely in
-- the route.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'approvals_execution_requires_confirmation_check'
    ) THEN
        ALTER TABLE pellier.approvals
            ADD CONSTRAINT approvals_execution_requires_confirmation_check
            CHECK (execution_turn_id IS NULL OR status = 'approved');
    END IF;
END $$;

-- The execution turn must look like a turn id. A free-form string here would let
-- a caller write a correlation value the evidence chain cannot resolve.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'approvals_execution_turn_format_check'
    ) THEN
        ALTER TABLE pellier.approvals
            ADD CONSTRAINT approvals_execution_turn_format_check
            CHECK (
                execution_turn_id IS NULL
                OR execution_turn_id ~ '^turn-[0-9a-f]{32}$'
            );
    END IF;
END $$;

COMMIT;

-- ---------------------------------------------------------------------
-- Self-probe: prove the constraints before anything depends on them
-- ---------------------------------------------------------------------

DO $$
DECLARE
    v_turn   TEXT := 'migration-021-probe';
    v_exec   TEXT := 'turn-' || repeat('a', 32);
    v_cust   TEXT;
    v_hash   TEXT := repeat('b', 64);
    v_id     BIGINT;
    v_failed BOOLEAN;
BEGIN
    SELECT id INTO v_cust FROM pellier.customers ORDER BY id LIMIT 1;
    IF v_cust IS NULL THEN
        RAISE NOTICE 'migration 021: no customers seeded, skipping self-probe';
        RETURN;
    END IF;

    INSERT INTO pellier.approvals
        (customer_id, tool, args, status, source_turn_id, issue, action_hash)
    VALUES
        (v_cust, 'initiate_return', '{"reason":"damaged"}'::jsonb, 'pending',
         v_turn, 'probe', v_hash)
    RETURNING id INTO v_id;

    -- 1. a pending review may not carry an execution turn
    v_failed := FALSE;
    BEGIN
        UPDATE pellier.approvals SET execution_turn_id = v_exec WHERE id = v_id;
    EXCEPTION WHEN check_violation THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION
            'migration 021: execution began on a review no human had confirmed';
    END IF;

    -- 2. confirm, then the execution turn is accepted
    UPDATE pellier.approvals
       SET status = 'approved', decided_at = now(), decided_by = 'probe-operator'
     WHERE id = v_id;
    UPDATE pellier.approvals SET execution_turn_id = v_exec WHERE id = v_id;

    -- 3. a malformed execution turn must be refused
    v_failed := FALSE;
    BEGIN
        UPDATE pellier.approvals SET execution_turn_id = 'not-a-turn' WHERE id = v_id;
    EXCEPTION WHEN check_violation THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 021: accepted a malformed execution turn id';
    END IF;

    DELETE FROM pellier.approvals WHERE source_turn_id = v_turn;
    RAISE NOTICE 'migration 021: execution-turn constraints verified';
END $$;
