-- Migration 044: project the durable Operator lifecycle into the Evidence Ledger.
--
-- A shopper turn may prepare a governed mutation, but that mutation is not
-- performed on the shopper rail. The later lifecycle is owned by existing
-- durable authorities:
--
--   approvals          proposal, human confirmation, or human decline
--   execution_receipts every governed execution attempt and its four axes
--
-- This migration adds those facts to the read-only Ledger projection. It does
-- not introduce another event table and it does not expose stored action
-- arguments, customer subject mappings, idempotency keys, or operator subject
-- identifiers to the shopper-scoped replay.

\set ON_ERROR_STOP on

BEGIN;

-- Keep migration 043's projection intact as the base relation. The wrapper
-- view below appends the lifecycle facts without duplicating the long, stable
-- canonical-source definition. The conditional makes this migration safe to
-- apply repeatedly on a fresh workshop cluster.
DO $$
BEGIN
    IF to_regclass('pellier.evidence_ledger_base_event_refs') IS NULL THEN
        EXECUTE
            'ALTER VIEW pellier.evidence_ledger_event_refs '
            'RENAME TO evidence_ledger_base_event_refs';
    END IF;
END
$$;

CREATE OR REPLACE VIEW pellier.evidence_ledger_event_refs AS
SELECT
    base.turn_id,
    base.session_id,
    base.principal_sub,
    base.event_kind,
    base.phase,
    base.status,
    base.provenance,
    base.source_kind,
    base.source_id,
    base.occurred_at,
    base.duration_ms,
    base.summary
  FROM pellier.evidence_ledger_base_event_refs base

UNION ALL

-- A review opens after a managed shopper-rail refusal. `planned` says exactly
-- what has happened: the action is prepared, but no human decision or governed
-- attempt exists yet.
SELECT
    gtr.turn_id,
    gtr.session_id,
    gtr.principal_sub,
    'operator_review'::TEXT AS event_kind,
    'follow_up'::TEXT AS phase,
    'planned'::TEXT AS status,
    'aurora-receipt'::TEXT AS provenance,
    'operator_review'::TEXT AS source_kind,
    a.id::TEXT AS source_id,
    a.requested_at AS occurred_at,
    NULL::INTEGER AS duration_ms,
    jsonb_build_object(
        'lifecycle', 'review_opened',
        'review_id', a.id,
        'action', a.tool
    ) AS summary
  FROM pellier.approvals a
  JOIN pellier.governed_turn_receipts gtr
    ON gtr.turn_id = a.source_turn_id
 WHERE a.source_turn_id IS NOT NULL

UNION ALL

-- A human decision is independent from governed execution. Confirmed means
-- the exact proposal was approved; declined means the execution path was not
-- entered. Neither outcome manufactures a policy or Aurora verdict.
SELECT
    gtr.turn_id,
    gtr.session_id,
    gtr.principal_sub,
    'operator_review'::TEXT,
    'follow_up'::TEXT,
    CASE a.status
        WHEN 'approved' THEN 'succeeded'
        WHEN 'rejected' THEN 'denied'
        ELSE 'unavailable'
    END,
    'aurora-receipt'::TEXT,
    'operator_review_decision'::TEXT,
    a.id::TEXT || ':decision',
    a.decided_at,
    NULL::INTEGER,
    jsonb_build_object(
        'lifecycle',
        CASE a.status
            WHEN 'approved' THEN 'confirmed'
            WHEN 'rejected' THEN 'declined'
            ELSE 'decision_unavailable'
        END,
        'review_id', a.id,
        'action', a.tool
    )
  FROM pellier.approvals a
  JOIN pellier.governed_turn_receipts gtr
    ON gtr.turn_id = a.source_turn_id
 WHERE a.source_turn_id IS NOT NULL
   AND a.status IN ('approved', 'rejected')
   AND a.decided_at IS NOT NULL

UNION ALL

-- `execution_receipts` is append-only, so retries remain visible as distinct
-- attempts. A Cedar or RLS denial is still an execution receipt: it proves the
-- governed boundary was entered while an absent downstream tool row proves the
-- action did not continue.
SELECT
    gtr.turn_id,
    gtr.session_id,
    gtr.principal_sub,
    'operator_review'::TEXT,
    'follow_up'::TEXT,
    CASE
        WHEN er.policy_outcome = 'DENY' THEN 'denied'
        WHEN er.aurora_outcome = 'DENIED' THEN 'denied'
        WHEN er.aurora_outcome = 'PERMITTED'
             AND er.evidence_outcome = 'RECEIPTED' THEN 'succeeded'
        WHEN er.evidence_outcome = 'NO_EXECUTION' THEN 'not_reached'
        ELSE 'failed'
    END,
    'aurora-receipt'::TEXT,
    'operator_execution_receipt'::TEXT,
    er.receipt_id::TEXT,
    er.created_at,
    NULL::INTEGER,
    jsonb_build_object(
        'lifecycle', 'execution_recorded',
        'review_id', a.id,
        'action', a.tool,
        'rail', er.rail,
        'execution_turn_id', er.execution_turn_id,
        'policy_outcome', er.policy_outcome,
        'aurora_outcome', er.aurora_outcome,
        'evidence_outcome', er.evidence_outcome,
        'gateway_mode', er.gateway_mode,
        'matching_forbids', er.matching_forbids
    )
  FROM pellier.execution_receipts er
  JOIN pellier.approvals a
    ON a.id = er.review_id
  JOIN pellier.governed_turn_receipts gtr
    ON gtr.turn_id = a.source_turn_id
 WHERE a.source_turn_id IS NOT NULL;

COMMENT ON VIEW pellier.evidence_ledger_event_refs IS
    'Principal-scoped, metadata-only projection over canonical shopper and '
    'Operator evidence. Operator lifecycle rows are post-turn follow-ups, not '
    'events claimed to have happened on the shopper rail.';

REVOKE ALL ON pellier.evidence_ledger_event_refs
    FROM PUBLIC, pellier_agent, pellier_query;

COMMIT;
