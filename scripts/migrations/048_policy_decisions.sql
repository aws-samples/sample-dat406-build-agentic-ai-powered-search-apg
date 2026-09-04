-- Migration 048: pellier.policy_decisions, the observed policy decision ledger.
--
-- Runs after: 010 (governed_receipts), 025 (execution_receipts),
--             047 (pellier.reject_evidence_mutation and the immutability triggers).
--
-- Why
-- ---
--
-- The managed AgentCore Policy engine decides at the Gateway. Before this table,
-- the application could persist two things about that decision: the Gateway's
-- own response (a deny marker, or a call that returned) and a substring match of
-- the action id against each policy's Cedar text. The second was presented as a
-- verdict, WOULD_DENY, under a LOG_ONLY gateway. Text that names an action is
-- not a decision about a call, so that reading is now labeled POLICY_INFERRED
-- and the real LOG_ONLY signals are read from where the service reports them:
-- the gateway's policy-evaluation trace spans (CloudWatch Transaction Search,
-- log group aws/spans) and the LogOnlyMatches / LogOnlyDecisionFlips /
-- LogOnlyEvalIncomplete metrics in the AWS/Bedrock-AgentCore namespace.
--
-- One row per observation, from one of four sources:
--
--   gateway-span        a policy-evaluation span for this action in the window
--   cloudwatch-metric   a LOG_ONLY flip or incomplete-evaluation metric datapoint
--   governed-receipt    the Gateway's own response to the governed call
--   policy-text         the Cedar substring scan; always POLICY_INFERRED
--
-- Five states, and only two sources can produce WOULD_DENY:
--
--   ALLOW / DENY            an enforced decision
--   WOULD_DENY              a real LOG_ONLY deny event (span or metric)
--   EVALUATION_INCOMPLETE   telemetry unreadable, absent, or partial
--   POLICY_INFERRED         text scan only; never a decision
--
-- `flip_of` links a later terminal observation to the newest prior one for the
-- same principal / action / resource when the two disagree (ALLOW against DENY
-- or WOULD_DENY). `raw` keeps whatever the source carried, because span
-- attribute names are not documented and a normalized column must never be the
-- only copy.
--
-- The existing receipt domains widen to the same five states. execution_receipts
-- keeps NOT_EVALUATED as well: the in-process rail consults no engine, and
-- "nothing was asked" is a different fact from "the answer could not be read".
-- execution_receipts.rail gains 'refused' for a governed execution that was
-- declined before any rail ran because the managed rail was not usable.
--
-- Forward-only and idempotent. No seed rows: a decision row exists only where
-- something was observed. `run_id` is deliberately absent; migration 049 adds it.

\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS pellier.policy_decisions (
  decision_id       BIGSERIAL PRIMARY KEY,
  session_id        TEXT,
  turn_id           TEXT,
  audit_id          BIGINT REFERENCES pellier.tool_audit(audit_id) ON DELETE SET NULL,
  principal_id      TEXT,
  action_id         TEXT NOT NULL,
  resource          TEXT,
  policy_engine_id  TEXT,
  policy_id         TEXT,
  policy_name       TEXT,
  policy_mode       TEXT CHECK (policy_mode IN ('ACTIVE','LOG_ONLY')),
  engine_mode       TEXT CHECK (engine_mode IN ('ENFORCE','LOG_ONLY')),
  state             TEXT NOT NULL CHECK (state IN
                    ('ALLOW','DENY','WOULD_DENY','EVALUATION_INCOMPLETE','POLICY_INFERRED')),
  source            TEXT NOT NULL CHECK (source IN
                    ('gateway-span','cloudwatch-metric','governed-receipt','policy-text')),
  flip_of           BIGINT REFERENCES pellier.policy_decisions(decision_id),
  observed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw               JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS policy_decisions_turn_idx ON pellier.policy_decisions (turn_id, observed_at);
DROP TRIGGER IF EXISTS policy_decisions_append_only ON pellier.policy_decisions;
CREATE TRIGGER policy_decisions_append_only BEFORE UPDATE OR DELETE ON pellier.policy_decisions
  FOR EACH ROW EXECUTE FUNCTION pellier.reject_evidence_mutation();
GRANT SELECT, INSERT ON pellier.policy_decisions TO pellier_agent;
GRANT USAGE, SELECT ON SEQUENCE pellier.policy_decisions_decision_id_seq TO pellier_agent;
-- widen existing domains
ALTER TABLE pellier.governed_receipts DROP CONSTRAINT IF EXISTS governed_receipts_decision_check;
ALTER TABLE pellier.governed_receipts ADD CONSTRAINT governed_receipts_decision_check
  CHECK (decision IN ('ALLOW','DENY','WOULD_DENY','EVALUATION_INCOMPLETE','POLICY_INFERRED'));

-- The flip index: "which decisions reversed an earlier one?" is the audit read.
CREATE INDEX IF NOT EXISTS policy_decisions_flip_idx
    ON pellier.policy_decisions (flip_of)
    WHERE flip_of IS NOT NULL;

-- The flip detector's read: newest terminal observation for one triple.
CREATE INDEX IF NOT EXISTS policy_decisions_triple_idx
    ON pellier.policy_decisions (principal_id, action_id, resource, observed_at DESC);

COMMENT ON TABLE pellier.policy_decisions IS
    'Observed AgentCore Policy decisions, one row per observation. Append-only. '
    'WOULD_DENY comes only from a real LOG_ONLY span or metric; POLICY_INFERRED '
    'is the Cedar text scan and is never a decision.';
COMMENT ON COLUMN pellier.policy_decisions.flip_of IS
    'The newest prior terminal observation for the same principal, action and '
    'resource that this observation reverses.';
COMMENT ON COLUMN pellier.policy_decisions.raw IS
    'The source payload as received. Span attribute names are undocumented, so the '
    'normalized columns are a reading of this, never a replacement for it.';

-- execution_receipts: widen policy_outcome and rail.
--
-- Both CHECKs were declared inline in migration 025, so their names were chosen
-- by the server: PostgreSQL names a column check <table>_<column>_check, which
-- is also the canonical name recreated below, and numbers a second one. The
-- catalog lookup covers both spellings rather than assuming either.
--
-- Two constraints are dropped here and exactly two are put back, so the lookup
-- must not match anything else. DISTINCT because the pg_attribute join yields
-- one row per constrained column: a CHECK over both columns would otherwise be
-- returned twice and its second DROP would fail. Single-column and
-- name-matched because this migration has no replacement for any other CHECK
-- on those columns, and dropping one would remove an enforced rule for good.
-- Anything left behind is reported, and the probe below fails loudly if a
-- surviving CHECK still refuses the widened vocabulary.
DO $$
DECLARE
    v_name TEXT;
    v_kept TEXT[];
BEGIN
    FOR v_name IN
        SELECT DISTINCT c.conname
          FROM pg_constraint c
          JOIN pg_attribute a
            ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
         WHERE c.conrelid = 'pellier.execution_receipts'::regclass
           AND c.contype = 'c'
           AND cardinality(c.conkey) = 1
           AND a.attname IN ('policy_outcome', 'rail')
           AND c.conname ~ ('^execution_receipts_' || a.attname || '_check[0-9]*$')
    LOOP
        EXECUTE format(
            'ALTER TABLE pellier.execution_receipts DROP CONSTRAINT %I', v_name
        );
    END LOOP;

    SELECT array_agg(DISTINCT c.conname) INTO v_kept
      FROM pg_constraint c
      JOIN pg_attribute a
        ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
     WHERE c.conrelid = 'pellier.execution_receipts'::regclass
       AND c.contype = 'c'
       AND a.attname IN ('policy_outcome', 'rail');
    IF v_kept IS NOT NULL THEN
        RAISE NOTICE
            'migration 048: left % in place on policy_outcome/rail; this '
            'migration replaces only its own two checks', v_kept;
    END IF;
END $$;

ALTER TABLE pellier.execution_receipts ADD CONSTRAINT execution_receipts_policy_outcome_check
  CHECK (policy_outcome IN
    ('ALLOW','DENY','WOULD_DENY','NOT_EVALUATED','EVALUATION_INCOMPLETE','POLICY_INFERRED'));
ALTER TABLE pellier.execution_receipts ADD CONSTRAINT execution_receipts_rail_check
  CHECK (rail IN ('gateway-mcp','in-process','refused'));

COMMENT ON COLUMN pellier.execution_receipts.policy_outcome IS
    'The AgentCore Policy reading for this attempt. ALLOW, DENY and WOULD_DENY come '
    'from real decision events; POLICY_INFERRED is the Cedar text scan; '
    'EVALUATION_INCOMPLETE means no decision could be read; NOT_EVALUATED means '
    'no engine was consulted (in-process rail).';
COMMENT ON COLUMN pellier.execution_receipts.rail IS
    'gateway-mcp, in-process, or refused. A refused receipt records that the managed '
    'rail was required and not usable, so nothing ran.';

COMMIT;

-- ---------------------------------------------------------------------
-- Self-probe: the widened domains admit the new states, the table refuses
-- mutation, and every probe row is rolled back (private SQLSTATE P0048).
-- ---------------------------------------------------------------------

DO $$
DECLARE
    v_probe    TEXT := 'migration-048-probe';
    v_exec     TEXT := 'turn-' || repeat('0', 31) || '8';
    v_cust     TEXT;
    v_review   BIGINT;
    v_first    BIGINT;
    v_second   BIGINT;
    v_failed   BOOLEAN;
BEGIN
  BEGIN
    INSERT INTO pellier.policy_decisions
        (session_id, turn_id, principal_id, action_id, resource, state, source, raw)
    VALUES
        (v_probe, v_exec, 'probe', 'probe-target___initiate_return', 'probe',
         'ALLOW', 'governed-receipt', '{"probe":true}'::jsonb)
    RETURNING decision_id INTO v_first;
    INSERT INTO pellier.policy_decisions
        (session_id, turn_id, principal_id, action_id, resource, state, source,
         policy_mode, engine_mode, flip_of, raw)
    VALUES
        (v_probe, v_exec, 'probe', 'probe-target___initiate_return', 'probe',
         'WOULD_DENY', 'cloudwatch-metric', 'LOG_ONLY', 'ENFORCE', v_first,
         '{"probe":true}'::jsonb)
    RETURNING decision_id INTO v_second;
    IF v_second IS NULL OR v_first IS NULL THEN
        RAISE EXCEPTION 'migration 048: decision rows were not written';
    END IF;

    v_failed := FALSE;
    BEGIN
        INSERT INTO pellier.policy_decisions (action_id, state, source)
        VALUES ('probe', 'MAYBE', 'gateway-span');
    EXCEPTION WHEN check_violation THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 048: accepted a state outside the vocabulary';
    END IF;

    v_failed := FALSE;
    BEGIN
        UPDATE pellier.policy_decisions SET state = 'DENY' WHERE decision_id = v_first;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 048: policy_decisions accepted an UPDATE';
    END IF;
    v_failed := FALSE;
    BEGIN
        DELETE FROM pellier.policy_decisions WHERE decision_id = v_second;
    EXCEPTION WHEN insufficient_privilege THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 048: policy_decisions accepted a DELETE';
    END IF;

    -- governed_receipts now admits the LOG_ONLY reading.
    INSERT INTO pellier.governed_receipts
        (session_id, principal_id, principal_label, tool, caller, decision)
    VALUES (v_probe, 'probe', 'probe', 'probe', 'gateway', 'WOULD_DENY');

    -- execution_receipts admits the refused rail and the incomplete reading.
    SELECT id INTO v_cust FROM pellier.customers ORDER BY id LIMIT 1;
    IF v_cust IS NULL THEN
        RAISE NOTICE 'migration 048: no customers seeded, skipping the execution_receipts probe';
    ELSE
        INSERT INTO pellier.approvals
            (customer_id, tool, args, status, source_turn_id, issue, action_hash,
             decided_at, decided_by, execution_turn_id)
        VALUES
            (v_cust, 'initiate_return', '{"reason":"damaged"}'::jsonb, 'approved',
             v_probe, 'probe', repeat('8', 64), now(), 'probe-operator', v_exec)
        RETURNING id INTO v_review;
        INSERT INTO pellier.execution_receipts
            (execution_turn_id, review_id, tool, rail, actor_principal,
             policy_outcome, aurora_outcome, evidence_outcome, idempotency_key)
        VALUES
            (v_exec, v_review, 'initiate_return', 'refused', 'probe',
             'EVALUATION_INCOMPLETE', 'NOT_REACHED', 'NO_EXECUTION', v_probe),
            (v_exec, v_review, 'initiate_return', 'in-process', 'probe',
             'NOT_EVALUATED', 'PERMITTED', 'RECEIPTED', v_probe),
            (v_exec, v_review, 'initiate_return', 'gateway-mcp', 'probe',
             'POLICY_INFERRED', 'PERMITTED', 'RECEIPTED', v_probe);
        v_failed := FALSE;
        BEGIN
            INSERT INTO pellier.execution_receipts
                (execution_turn_id, review_id, tool, rail, actor_principal,
                 policy_outcome, aurora_outcome, evidence_outcome, idempotency_key)
            VALUES
                (v_exec, v_review, 'initiate_return', 'elsewhere', 'probe',
                 'ALLOW', 'PERMITTED', 'RECEIPTED', v_probe);
        EXCEPTION WHEN check_violation THEN
            v_failed := TRUE;
        END;
        IF NOT v_failed THEN
            RAISE EXCEPTION 'migration 048: execution_receipts accepted an unknown rail';
        END IF;
    END IF;

    RAISE EXCEPTION 'migration 048 probe complete' USING ERRCODE = 'P0048';
  EXCEPTION WHEN SQLSTATE 'P0048' THEN
    RAISE NOTICE
        'migration 048: policy_decisions ready; receipt domains widened; '
        'probe rows rolled back';
  END;
END $$;
