-- Migration 014: immutable, participant-facing governed turn receipts.
--
-- ``governed_receipts`` records a Gateway/Cedar decision for one mutation and
-- ``retrieval_receipts`` records why a retrieval result ranked. Neither can
-- reconstruct one shopper turn across identity, retrieval, policy, audit, and
-- managed Runtime trace evidence. This table is the durable join record.

\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE pellier.retrieval_receipts
    ADD COLUMN IF NOT EXISTS turn_id TEXT;

CREATE INDEX IF NOT EXISTS retrieval_receipts_turn_idx
    ON pellier.retrieval_receipts (turn_id, created_at DESC)
    WHERE turn_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS pellier.governed_turn_receipts (
    turn_id                 TEXT PRIMARY KEY,
    session_id              TEXT,
    principal_sub           TEXT,
    principal_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    rail                    TEXT NOT NULL,
    model_config            JSONB NOT NULL DEFAULT '{}'::jsonb,
    retrieval_receipt_id    BIGINT REFERENCES pellier.retrieval_receipts(receipt_id)
                            ON DELETE SET NULL,
    citations               JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_audit_ids          JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_events           JSONB NOT NULL DEFAULT '[]'::jsonb,
    trace                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    terminal_outcome        JSONB NOT NULL DEFAULT '{}'::jsonb,
    terminal_status         TEXT NOT NULL
                            CHECK (
                                terminal_status IN (
                                    'complete',
                                    'denied-before-execution',
                                    'evidence-unavailable',
                                    'trace-pending',
                                    'failed'
                                )
                            ),
    latency_ms              INTEGER,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        (principal_verified AND principal_sub IS NOT NULL)
        OR NOT principal_verified
    )
);

CREATE INDEX IF NOT EXISTS governed_turn_receipts_principal_idx
    ON pellier.governed_turn_receipts (principal_sub, created_at DESC)
    WHERE principal_sub IS NOT NULL;

CREATE INDEX IF NOT EXISTS governed_turn_receipts_session_idx
    ON pellier.governed_turn_receipts (session_id, created_at DESC);

CREATE OR REPLACE FUNCTION pellier.reject_governed_turn_receipt_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'governed_turn_receipts are append-only';
END;
$$;

DROP TRIGGER IF EXISTS governed_turn_receipts_append_only
    ON pellier.governed_turn_receipts;

CREATE TRIGGER governed_turn_receipts_append_only
    BEFORE UPDATE OR DELETE ON pellier.governed_turn_receipts
    FOR EACH ROW
    EXECUTE FUNCTION pellier.reject_governed_turn_receipt_mutation();

COMMIT;
