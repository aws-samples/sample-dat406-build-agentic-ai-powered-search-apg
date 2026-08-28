-- Migration 026: bind an episode to the reviewed execution that produced it.
--
-- WHY THIS EXISTS
--
-- Migration 024 created `pellier.operator_episodes` and nothing in the application ever
-- wrote to it or read from it. The three rows it holds on 2026-08-27 were written by a
-- one-off capture script during the Phase 6B proof, which is the exact failure the
-- module's own docstring warns about: a seeded "successful past resolution" is a story,
-- not a record.
--
-- The production writer now runs inside `execute_confirmed_review`, and it needs one
-- thing 024 did not provide: a durable key for the LOGICAL OUTCOME, so a replay cannot
-- append a second episode for the same resolution.
--
-- WHY NOT THE EXISTING KEY
--
-- 024's partial unique index is on `(source_turn_id, episode_type)`, and
-- `source_turn_id` means the SHOPPER turn that started the story. That is the right
-- meaning to keep — it is how the Observatory reaches an episode from a shopper turn —
-- but it is the wrong uniqueness key:
--
--   * two different reviews can descend from one shopper turn;
--   * an episode recorded by a background reconciliation has no shopper turn at all;
--   * and overloading the column with an execution turn would make the lineage
--     ambiguous in precisely the place an auditor needs it exact.
--
-- So the reviewed execution gets its own two columns and its own index. Neither is a
-- new identifier family: `review_id` is `pellier.approvals.id` and `execution_turn_id`
-- is the assign-once value migration 021 added to the same row.
--
-- THE UNIQUENESS CONTRACT
--
--   one reviewed execution outcome  ->  one episode of that kind
--   a tool replay                   ->  another execution receipt, NO second episode
--
-- `execution_turn_id` is assigned once per review and reused by every retry (021), so
-- keying on `review_id` and keying on `execution_turn_id` are the same contract stated
-- two ways. The index uses `review_id` because it is the narrower, non-null-when-present
-- column and it is what the reader joins on.
--
-- Forward-only and idempotent: two nullable columns, one partial unique index, one
-- CHECK. No changes to existing rows and no seed data.

\set ON_ERROR_STOP on

BEGIN;

ALTER TABLE pellier.operator_episodes
    ADD COLUMN IF NOT EXISTS review_id BIGINT,
    ADD COLUMN IF NOT EXISTS execution_turn_id TEXT;

-- CASCADE, matching `pellier.execution_receipts`: an episode whose review is gone
-- cannot be reconstructed, and the deterministic workshop reset stays a single delete
-- on `pellier.approvals` rather than an ordered sequence across four tables.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'operator_episodes_review_fkey'
    ) THEN
        ALTER TABLE pellier.operator_episodes
            ADD CONSTRAINT operator_episodes_review_fkey
            FOREIGN KEY (review_id) REFERENCES pellier.approvals(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Same format gate as migration 021. A free-form string here would let a caller write
-- a correlation value the evidence chain cannot resolve.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'operator_episodes_execution_turn_format_check'
    ) THEN
        ALTER TABLE pellier.operator_episodes
            ADD CONSTRAINT operator_episodes_execution_turn_format_check
            CHECK (
                execution_turn_id IS NULL
                OR execution_turn_id ~ '^turn-[0-9a-f]{32}$'
            );
    END IF;
END $$;

-- THE IDEMPOTENCY CONTRACT, at the storage layer rather than in the caller.
CREATE UNIQUE INDEX IF NOT EXISTS operator_episodes_outcome_idx
    ON pellier.operator_episodes (review_id, episode_type)
    WHERE review_id IS NOT NULL;

-- And 024's index has to give up the reviewed rows, or the two contracts fight.
--
-- Measured on 2026-08-27: with `operator_episodes_turn_idx` still covering every row on
-- `(source_turn_id, episode_type)`, all three governed executions failed to record an
-- episode with `duplicate key value violates unique constraint
-- "operator_episodes_turn_idx"`. The insert names `ON CONFLICT (review_id, ...)`, so a
-- violation of the OTHER index is not absorbed — it raises, and the best-effort handler
-- swallowed it. Three executions, three warnings, zero memories.
--
-- The shopper turn is the wrong uniqueness key for a reviewed outcome anyway, for the
-- reason in this file's header: two reviews can descend from one shopper turn, and both
-- can legitimately resolve. So the old index is rebuilt as a partial one that still
-- guards the rows it was written for — episodes with no review, such as a background
-- reconciliation — and stops constraining the ones migration 026 now owns.
DROP INDEX IF EXISTS pellier.operator_episodes_turn_idx;

CREATE UNIQUE INDEX IF NOT EXISTS operator_episodes_turn_idx
    ON pellier.operator_episodes (source_turn_id, episode_type)
    WHERE source_turn_id IS NOT NULL AND review_id IS NULL;

-- The reader's other access path: from an execution turn found in a log or a URL.
CREATE INDEX IF NOT EXISTS operator_episodes_execution_turn_idx
    ON pellier.operator_episodes (execution_turn_id)
    WHERE execution_turn_id IS NOT NULL;

COMMENT ON COLUMN pellier.operator_episodes.review_id IS
    'The human decision this outcome ran under. Unique per episode_type: one reviewed execution outcome, one episode, however many times the tool was replayed.';

COMMENT ON COLUMN pellier.operator_episodes.execution_turn_id IS
    'The governed execution attempt that produced this outcome. Assign-once per review (migration 021), so it is stable across replays.';

COMMIT;

-- ---------------------------------------------------------------------
-- Self-probe: prove the idempotency contract before anything depends on it
-- ---------------------------------------------------------------------

DO $$
DECLARE
    v_turn   TEXT := 'migration-026-probe';
    v_exec   TEXT := 'turn-' || repeat('e', 32);
    v_cust   TEXT;
    v_hash   TEXT := repeat('f', 64);
    v_review BIGINT;
    v_second BIGINT;
    v_failed BOOLEAN;
    v_count  INTEGER;
BEGIN
    SELECT id INTO v_cust FROM pellier.customers ORDER BY id LIMIT 1;
    IF v_cust IS NULL THEN
        RAISE NOTICE 'migration 026: no customers seeded, skipping self-probe';
        RETURN;
    END IF;

    INSERT INTO pellier.approvals
        (customer_id, tool, args, status, source_turn_id, issue, action_hash,
         decided_at, decided_by, execution_turn_id)
    VALUES
        (v_cust, 'initiate_return', '{"reason":"damaged"}'::jsonb, 'approved',
         v_turn, 'probe', v_hash, now(), 'probe-operator', v_exec)
    RETURNING id INTO v_review;

    -- 1. the first episode for this reviewed outcome is accepted
    INSERT INTO pellier.operator_episodes
        (customer_id, source_turn_id, review_id, execution_turn_id, episode_type,
         situation, human_outcome, policy_outcome, aurora_outcome)
    VALUES
        (v_cust, v_turn, v_review, v_exec, 'return_resolution',
         'probe situation', 'confirmed', 'allow', 'applied');

    -- 2. a REPLAY of the same reviewed outcome must be refused. This is the whole
    --    contract: a retried execution writes another receipt, never another episode.
    v_failed := FALSE;
    BEGIN
        INSERT INTO pellier.operator_episodes
            (customer_id, source_turn_id, review_id, execution_turn_id, episode_type,
             situation, human_outcome, policy_outcome, aurora_outcome)
        VALUES
            (v_cust, v_turn, v_review, v_exec, 'return_resolution',
             'probe situation replayed', 'confirmed', 'allow', 'applied');
    EXCEPTION WHEN unique_violation THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION
            'migration 026: a replayed execution appended a second episode';
    END IF;

    -- 3. a DIFFERENT kind of outcome on the same review is still allowed. A return
    --    resolution and a credit issued against one review are two outcomes.
    INSERT INTO pellier.operator_episodes
        (customer_id, source_turn_id, review_id, execution_turn_id, episode_type,
         situation, human_outcome, policy_outcome, aurora_outcome)
    VALUES
        (v_cust, v_turn, v_review, v_exec, 'credit_issued',
         'probe credit', 'confirmed', 'allow', 'applied');

    -- 3b. A SECOND review descending from the same shopper turn may also resolve.
    --     024's index forbade this, which is what broke all three live executions:
    --     it constrained the shopper turn, and a shopper turn is not an outcome.
    INSERT INTO pellier.approvals
        (customer_id, tool, args, status, source_turn_id, issue, action_hash,
         decided_at, decided_by, execution_turn_id)
    VALUES
        (v_cust, 'initiate_return', '{"reason":"wrong_size"}'::jsonb, 'approved',
         v_turn, 'probe two', repeat('a', 64), now(), 'probe-operator',
         'turn-' || repeat('d', 32))
    RETURNING id INTO v_second;

    INSERT INTO pellier.operator_episodes
        (customer_id, source_turn_id, review_id, execution_turn_id, episode_type,
         situation, human_outcome, policy_outcome, aurora_outcome)
    VALUES
        (v_cust, v_turn, v_second, 'turn-' || repeat('d', 32), 'return_resolution',
         'probe second review', 'confirmed', 'deny', 'not_attempted');

    -- 3c. But an episode with NO review is still one per shopper turn and kind, which
    --     is the contract 024's index was written for and this keeps.
    v_failed := FALSE;
    BEGIN
        INSERT INTO pellier.operator_episodes
            (customer_id, source_turn_id, episode_type, situation,
             human_outcome, policy_outcome, aurora_outcome)
        VALUES
            (v_cust, v_turn || '-noreview', 'return_resolution', 'probe no review',
             'not_required', 'not_evaluated', 'not_attempted'),
            (v_cust, v_turn || '-noreview', 'return_resolution', 'probe no review two',
             'not_required', 'not_evaluated', 'not_attempted');
    EXCEPTION WHEN unique_violation THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION
            'migration 026: two review-less episodes shared a shopper turn and kind';
    END IF;

    -- 4. a malformed execution turn is refused
    v_failed := FALSE;
    BEGIN
        INSERT INTO pellier.operator_episodes
            (customer_id, review_id, execution_turn_id, episode_type, situation,
             human_outcome, policy_outcome, aurora_outcome)
        VALUES
            (v_cust, v_review, 'not-a-turn', 'escalation', 'probe',
             'confirmed', 'allow', 'applied');
    EXCEPTION WHEN check_violation THEN
        v_failed := TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'migration 026: accepted a malformed execution turn id';
    END IF;

    -- 5. deleting the review takes its episodes with it, so the reset stays one delete.
    --    The review-less probe rows have no review to cascade from and are removed by
    --    hand, which is exactly the asymmetry the CASCADE exists to avoid in production.
    DELETE FROM pellier.operator_episodes WHERE source_turn_id = v_turn || '-noreview';
    DELETE FROM pellier.approvals WHERE source_turn_id = v_turn;
    SELECT count(*) INTO v_count
      FROM pellier.operator_episodes WHERE execution_turn_id = v_exec;
    IF v_count <> 0 THEN
        RAISE EXCEPTION
            'migration 026: % episode(s) survived their review; reset would orphan them',
            v_count;
    END IF;

    RAISE NOTICE 'migration 026: episode idempotency contract verified';
END $$;
