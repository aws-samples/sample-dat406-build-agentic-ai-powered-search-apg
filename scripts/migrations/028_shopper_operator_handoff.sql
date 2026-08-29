-- Migration 028: immutable shopper-to-operator handoff context.
--
-- A prepared action already has durable lineage:
--
--   governed_turn_receipts.turn_id -> approvals.source_turn_id
--
-- What it did not preserve was the bounded context the operator needs to
-- understand why that review exists. Storing that context on the append-only
-- shopper receipt keeps it tied to the original turn instead of backfilling a
-- mutable summary later.

\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE pellier.governed_turn_receipts
    ADD COLUMN IF NOT EXISTS handoff_context JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'governed_turn_receipts_handoff_object_check'
    ) THEN
        ALTER TABLE pellier.governed_turn_receipts
            ADD CONSTRAINT governed_turn_receipts_handoff_object_check
            CHECK (jsonb_typeof(handoff_context) = 'object');
    END IF;
END $$;

COMMENT ON COLUMN pellier.governed_turn_receipts.handoff_context IS
    'Bounded, explicitly untrusted shopper context captured with the original append-only receipt when a turn prepares an operator review.';

COMMIT;
