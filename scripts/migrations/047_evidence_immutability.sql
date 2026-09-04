-- Migration 047: evidence tables become immutable at the database boundary.
--
-- Runs after: 010 (governed_receipts), 011/019/022/023/039 (write_operations and
--             its writer functions), 016 (pellier_agent grants), 025
--             (execution_receipts).
--
-- Why
-- ---
--
-- Four tables are presented to participants as evidence: what the policy engine
-- decided, what ran, what applied exactly once, and what each governance layer
-- concluded. Until now only 046's retrieval_receipts and 014's governed turn
-- receipts refused mutation. The rest relied on grants, and the owner role that
-- runs the application bypasses grants entirely. A row that the application
-- could rewrite after the fact is a claim, not evidence.
--
-- What changes
-- ------------
--
--   governed_receipts     append-only. UPDATE and DELETE raise.
--   execution_receipts    append-only. UPDATE and DELETE raise.
--   tool_audit            fill-once. The writer INSERTs a row before the tool
--                         runs and completes `result` and `latency_ms` after it
--                         returns (services/tool_audit_writer.py). That single
--                         completion stays legal; a second UPDATE, any change to
--                         the identity columns, and DELETE raise.
--   write_operations      fill-once. The idempotent write functions claim a key
--                         with an INSERT and finalise it with one UPDATE of
--                         `result` and `completed_at`. That transition stays
--                         legal. A completed row is frozen: no UPDATE, no
--                         DELETE. Migration 023 releases a failed claim by
--                         leaving it UNFILLED (result and completed_at NULL);
--                         deleting such an unfilled claim remains permitted so
--                         that path keeps working.
--
-- The write functions from 011, 019, 023 and 039 were read before this was
-- written. Every UPDATE they perform runs after the replay guard
-- `IF NOT v_claimed AND v_existing.result IS NOT NULL THEN RETURN`, so the row
-- they finalise always has `result IS NULL`, which is exactly the transition
-- the trigger admits.
--
-- The grant on write_operations is narrowed to match: 016 granted table-wide
-- UPDATE to pellier_agent; only `result` and `completed_at` remain updatable.
-- `SELECT ... FOR UPDATE` inside the write functions needs UPDATE on at least
-- one column, which the column grant satisfies.
--
-- Consequence for re-application
-- -------------------------------
--
-- Migrations 019, 022 and 023 clean up their self-tests with a DELETE of a
-- COMPLETED write_operations row, and 025's self-test deletes a probe approval
-- whose cascade removes execution_receipts rows. Those statements were legal
-- when the migrations first ran. Once this migration is installed they raise,
-- so re-applying any of those four migrations on a cluster that already has
-- these triggers fails at its own cleanup. A reset that re-applies them must
-- drop the affected trigger first and re-apply this migration afterwards; it
-- is idempotent.
--
-- The self-probe at the bottom proves each rule and then rolls its own rows
-- back, because after this migration nothing can delete them.

\set ON_ERROR_STOP on

BEGIN;

-- governed_receipts + execution_receipts: append-only
CREATE OR REPLACE FUNCTION pellier.reject_evidence_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'pellier.% is append-only evidence; % is not permitted', TG_TABLE_NAME, TG_OP
    USING ERRCODE = 'insufficient_privilege';
END $$;
DROP TRIGGER IF EXISTS governed_receipts_append_only ON pellier.governed_receipts;
CREATE TRIGGER governed_receipts_append_only BEFORE UPDATE OR DELETE ON pellier.governed_receipts
  FOR EACH ROW EXECUTE FUNCTION pellier.reject_evidence_mutation();
DROP TRIGGER IF EXISTS execution_receipts_append_only ON pellier.execution_receipts;
CREATE TRIGGER execution_receipts_append_only BEFORE UPDATE OR DELETE ON pellier.execution_receipts
  FOR EACH ROW EXECUTE FUNCTION pellier.reject_evidence_mutation();

-- tool_audit: fill-once (result/latency may be set exactly once while NULL)
CREATE OR REPLACE FUNCTION pellier.tool_audit_fill_once() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'pellier.tool_audit is append-only evidence; DELETE is not permitted'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF OLD.result IS NOT NULL OR OLD.latency_ms IS NOT NULL THEN
    RAISE EXCEPTION 'pellier.tool_audit row % already finalized', OLD.audit_id
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF NEW.audit_id IS DISTINCT FROM OLD.audit_id OR NEW.session_id IS DISTINCT FROM OLD.session_id
     OR NEW.tool IS DISTINCT FROM OLD.tool OR NEW.caller IS DISTINCT FROM OLD.caller
     OR NEW.args IS DISTINCT FROM OLD.args OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'pellier.tool_audit identity columns are immutable'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS tool_audit_fill_once ON pellier.tool_audit;
CREATE TRIGGER tool_audit_fill_once BEFORE UPDATE OR DELETE ON pellier.tool_audit
  FOR EACH ROW EXECUTE FUNCTION pellier.tool_audit_fill_once();

-- write_operations: only the claim -> completed transition
CREATE OR REPLACE FUNCTION pellier.write_operations_fill_once() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    -- migration 023 releases a failed claim by DELETE inside process_return_idempotent;
    -- keep that path: allow DELETE only while the claim is unfilled.
    IF OLD.completed_at IS NOT NULL THEN
      RAISE EXCEPTION 'pellier.write_operations % is completed evidence; DELETE is not permitted',
        OLD.idempotency_key USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN OLD;
  END IF;
  IF OLD.completed_at IS NOT NULL THEN
    RAISE EXCEPTION 'pellier.write_operations % already completed', OLD.idempotency_key
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key OR NEW.operation IS DISTINCT FROM OLD.operation
     OR NEW.request_hash IS DISTINCT FROM OLD.request_hash OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'pellier.write_operations identity columns are immutable'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS write_operations_fill_once ON pellier.write_operations;
CREATE TRIGGER write_operations_fill_once BEFORE UPDATE OR DELETE ON pellier.write_operations
  FOR EACH ROW EXECUTE FUNCTION pellier.write_operations_fill_once();
REVOKE UPDATE ON pellier.write_operations FROM pellier_agent;
GRANT UPDATE (result, completed_at) ON pellier.write_operations TO pellier_agent;

COMMENT ON FUNCTION pellier.reject_evidence_mutation() IS
    'Append-only guard for governed_receipts, execution_receipts and policy_decisions.';
COMMENT ON FUNCTION pellier.tool_audit_fill_once() IS
    'tool_audit rows are completed once (result, latency_ms) and never rewritten or deleted.';
COMMENT ON FUNCTION pellier.write_operations_fill_once() IS
    'write_operations rows move from claim to completed once; unfilled claims may be released.';

COMMIT;

-- ---------------------------------------------------------------------
-- Self-probe: prove every rule, then roll the probe rows back.
--
-- The probe runs inside one plpgsql block and ends by raising a private
-- SQLSTATE (P0047) that the same block catches. That discards every row the
-- probe inserted, which matters here more than anywhere else: after this
-- migration no statement can delete them.
-- ---------------------------------------------------------------------

DO $$
DECLARE
    v_audit    BIGINT;
    v_cust     TEXT;
    v_review   BIGINT;
    v_failed   BOOLEAN;
    v_probe    TEXT := 'migration-047-probe';
    v_exec     TEXT := 'turn-' || repeat('0', 31) || '4';
BEGIN
  BEGIN
    -- tool_audit: one completion, then frozen
    INSERT INTO pellier.tool_audit (session_id, tool, caller, args)
    VALUES (v_probe, 'probe', 'probe', '{}'::jsonb)
    RETURNING audit_id INTO v_audit;
    UPDATE pellier.tool_audit
       SET result = '{"status":"probe"}'::jsonb, latency_ms = 1
     WHERE audit_id = v_audit;

    v_failed := FALSE;
    BEGIN
        UPDATE pellier.tool_audit SET result = '{}'::jsonb WHERE audit_id = v_audit;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: tool_audit accepted a second completion';
    END IF;

    v_failed := FALSE;
    BEGIN
        DELETE FROM pellier.tool_audit WHERE audit_id = v_audit;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: tool_audit accepted a DELETE';
    END IF;

    INSERT INTO pellier.tool_audit (session_id, tool, caller, args)
    VALUES (v_probe, 'probe', 'probe', '{}'::jsonb)
    RETURNING audit_id INTO v_audit;
    v_failed := FALSE;
    BEGIN
        UPDATE pellier.tool_audit SET tool = 'rewritten' WHERE audit_id = v_audit;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: tool_audit accepted an identity rewrite';
    END IF;

    -- write_operations: claim -> completed, then frozen
    INSERT INTO pellier.write_operations (idempotency_key, operation, request_hash)
    VALUES (v_probe, 'initiate_return', repeat('a', 64));
    UPDATE pellier.write_operations
       SET result = '{"status":"success"}'::jsonb, completed_at = now()
     WHERE idempotency_key = v_probe;

    v_failed := FALSE;
    BEGIN
        UPDATE pellier.write_operations SET result = '{}'::jsonb
         WHERE idempotency_key = v_probe;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: write_operations accepted a second completion';
    END IF;

    v_failed := FALSE;
    BEGIN
        DELETE FROM pellier.write_operations WHERE idempotency_key = v_probe;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: write_operations accepted a DELETE of completed evidence';
    END IF;

    -- an unfilled claim may still be released (migration 023's contract)
    INSERT INTO pellier.write_operations (idempotency_key, operation, request_hash)
    VALUES (v_probe || '-unfilled', 'initiate_return', repeat('b', 64));
    v_failed := FALSE;
    BEGIN
        UPDATE pellier.write_operations SET request_hash = repeat('c', 64)
         WHERE idempotency_key = v_probe || '-unfilled';
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: write_operations accepted an identity rewrite';
    END IF;
    DELETE FROM pellier.write_operations WHERE idempotency_key = v_probe || '-unfilled';

    -- governed_receipts: append-only
    INSERT INTO pellier.governed_receipts
        (session_id, principal_id, principal_label, tool, caller, decision)
    VALUES (v_probe, 'probe', 'probe', 'probe', 'gateway', 'ALLOW');
    v_failed := FALSE;
    BEGIN
        UPDATE pellier.governed_receipts SET decision = 'DENY' WHERE session_id = v_probe;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: governed_receipts accepted an UPDATE';
    END IF;
    v_failed := FALSE;
    BEGIN
        DELETE FROM pellier.governed_receipts WHERE session_id = v_probe;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 047: governed_receipts accepted a DELETE';
    END IF;

    -- execution_receipts: append-only (needs a review to reference)
    SELECT id INTO v_cust FROM pellier.customers ORDER BY id LIMIT 1;
    IF v_cust IS NULL THEN
        RAISE NOTICE 'migration 047: no customers seeded, skipping the execution_receipts probe';
    ELSE
        INSERT INTO pellier.approvals
            (customer_id, tool, args, status, source_turn_id, issue, action_hash,
             decided_at, decided_by, execution_turn_id)
        VALUES
            (v_cust, 'initiate_return', '{"reason":"damaged"}'::jsonb, 'approved',
             v_probe, 'probe', repeat('d', 64), now(), 'probe-operator', v_exec)
        RETURNING id INTO v_review;
        INSERT INTO pellier.execution_receipts
            (execution_turn_id, review_id, tool, rail, actor_principal,
             policy_outcome, aurora_outcome, evidence_outcome, idempotency_key)
        VALUES
            (v_exec, v_review, 'initiate_return', 'gateway-mcp', 'probe',
             'DENY', 'NOT_REACHED', 'POLICY_PROOF', v_probe);
        v_failed := FALSE;
        BEGIN
            UPDATE pellier.execution_receipts SET policy_outcome = 'ALLOW'
             WHERE review_id = v_review;
        EXCEPTION WHEN insufficient_privilege THEN
            v_failed := TRUE;
        END;
        IF NOT v_failed THEN
            RAISE EXCEPTION 'migration 047: execution_receipts accepted an UPDATE';
        END IF;
        v_failed := FALSE;
        BEGIN
            DELETE FROM pellier.execution_receipts WHERE review_id = v_review;
        EXCEPTION WHEN insufficient_privilege THEN
            v_failed := TRUE;
        END;
        IF NOT v_failed THEN
            RAISE EXCEPTION 'migration 047: execution_receipts accepted a DELETE';
        END IF;
    END IF;

    RAISE EXCEPTION 'migration 047 probe complete' USING ERRCODE = 'P0047';
  EXCEPTION WHEN SQLSTATE 'P0047' THEN
    RAISE NOTICE
        'migration 047: evidence immutability verified on tool_audit, write_operations, '
        'governed_receipts and execution_receipts; probe rows rolled back';
  END;
END $$;
