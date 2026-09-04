-- Migration 046: preserve the catalog evidence a retrieval turn actually used.
--
-- A governed turn receipt used to resolve its citation product IDs back through
-- pellier.product_catalog at terminal persistence time. That meant a later
-- catalog edit could change the quote/revision attached to a prior turn. The
-- retrieval receipt now carries a compact, ordered snapshot and its SHA-256
-- hash; governed receipts use only that evidence.

\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE pellier.retrieval_receipts
    ADD COLUMN IF NOT EXISTS citation_snapshots JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS citation_snapshot_hash TEXT;

COMMENT ON COLUMN pellier.retrieval_receipts.citation_snapshots IS
    'Bounded catalog citation evidence captured at retrieval time, in returned result order.';

COMMENT ON COLUMN pellier.retrieval_receipts.citation_snapshot_hash IS
    'SHA-256 of canonical citation_snapshots JSON; a mismatch suppresses citations rather than reading mutable catalog rows.';

CREATE OR REPLACE FUNCTION pellier.reject_retrieval_receipt_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'retrieval_receipts are append-only';
END;
$$;

DROP TRIGGER IF EXISTS retrieval_receipts_append_only
    ON pellier.retrieval_receipts;

CREATE TRIGGER retrieval_receipts_append_only
    BEFORE UPDATE OR DELETE ON pellier.retrieval_receipts
    FOR EACH ROW
    EXECUTE FUNCTION pellier.reject_retrieval_receipt_mutation();

COMMIT;
