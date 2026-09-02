-- Migration 043: typed Evidence Ledger projection and redacted model receipts.
--
-- The governed workshop already has several append-only evidence authorities:
--
--   * retrieval_receipts       why a ranked result appeared
--   * governed_query_receipts  whether generated SQL was accepted and executed
--   * tool_audit               which tool target actually ran
--   * governed_receipts        explicit Gateway/Cedar ALLOW or DENY
--   * governed_turn_receipts   the immutable terminal join for one shopper turn
--   * execution_receipts       the independent operator policy/Aurora/evidence axes
--
-- This migration does not replace or duplicate those authorities. It adds:
--
--   1. model_invocation_receipts: metadata-only model usage evidence. Prompts,
--      completions, tool arguments, and tool results are structurally absent.
--   2. evidence_ledger_event_refs: a safe, read-only index over the canonical
--      sources. The API still applies verified-principal scope before returning
--      a replay and expands details from their source table.
--
-- Retention and scale:
--   Workshop deployments are small enough for ordinary B-tree indexes. A
--   production deployment should partition append-heavy receipt tables by
--   created_at and attach a retention policy before volume requires it.

\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS pellier.model_invocation_receipts (
    invocation_id          BIGSERIAL PRIMARY KEY,
    invocation_key         TEXT NOT NULL UNIQUE,
    turn_id                TEXT NOT NULL
                           REFERENCES pellier.governed_turn_receipts(turn_id),
    session_id             TEXT,
    principal_sub          TEXT,
    model_id               TEXT,
    inference_profile_id   TEXT,
    purpose                TEXT NOT NULL,
    input_tokens           INTEGER
                           CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens          INTEGER
                           CHECK (output_tokens IS NULL OR output_tokens >= 0),
    total_tokens           INTEGER
                           CHECK (total_tokens IS NULL OR total_tokens >= 0),
    stop_reason            TEXT,
    latency_ms             INTEGER
                           CHECK (latency_ms IS NULL OR latency_ms >= 0),
    outcome                TEXT NOT NULL
                           CHECK (
                               outcome IN (
                                   'succeeded',
                                   'failed',
                                   'unavailable'
                               )
                           ),
    trace_id               TEXT,
    span_id                TEXT,
    source                 TEXT NOT NULL
                           CHECK (
                               source IN (
                                   'otel',
                                   'agentcore-service-telemetry',
                                   'runtime-summary'
                               )
                           ),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE pellier.model_invocation_receipts IS
    'Append-only, metadata-only model invocation evidence. Prompt, completion, '
    'tool argument, and tool result content are intentionally absent.';

CREATE INDEX IF NOT EXISTS model_invocation_receipts_turn_idx
    ON pellier.model_invocation_receipts (turn_id, created_at, invocation_id);

CREATE INDEX IF NOT EXISTS model_invocation_receipts_principal_idx
    ON pellier.model_invocation_receipts (principal_sub, created_at DESC)
    WHERE principal_sub IS NOT NULL;

CREATE INDEX IF NOT EXISTS model_invocation_receipts_trace_idx
    ON pellier.model_invocation_receipts (trace_id)
    WHERE trace_id IS NOT NULL;

CREATE OR REPLACE FUNCTION pellier.reject_model_invocation_receipt_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'model_invocation_receipts are append-only';
END;
$$;

DROP TRIGGER IF EXISTS model_invocation_receipts_append_only
    ON pellier.model_invocation_receipts;

CREATE TRIGGER model_invocation_receipts_append_only
    BEFORE UPDATE OR DELETE ON pellier.model_invocation_receipts
    FOR EACH ROW
    EXECUTE FUNCTION pellier.reject_model_invocation_receipt_mutation();

GRANT INSERT ON pellier.model_invocation_receipts TO pellier_agent;
GRANT USAGE, SELECT ON SEQUENCE
    pellier.model_invocation_receipts_invocation_id_seq TO pellier_agent;
GRANT SELECT (invocation_id)
    ON pellier.model_invocation_receipts TO pellier_agent;
REVOKE ALL ON pellier.model_invocation_receipts FROM pellier_query;

CREATE OR REPLACE VIEW pellier.evidence_ledger_event_refs AS
SELECT
    gtr.turn_id,
    gtr.session_id,
    gtr.principal_sub,
    'route'::TEXT AS event_kind,
    'routing'::TEXT AS phase,
    'succeeded'::TEXT AS status,
    'aurora-receipt'::TEXT AS provenance,
    'governed_turn_receipt'::TEXT AS source_kind,
    gtr.turn_id::TEXT AS source_id,
    gtr.created_at AS occurred_at,
    NULL::INTEGER AS duration_ms,
    jsonb_build_object(
        'rail', gtr.rail,
        'model_config', gtr.model_config
    ) AS summary
  FROM pellier.governed_turn_receipts gtr

UNION ALL

SELECT
    rr.turn_id,
    rr.session_id,
    rr.principal_sub,
    'retrieval',
    'evidence',
    CASE
        WHEN jsonb_array_length(rr.citation_ids) > 0 THEN 'succeeded'
        ELSE 'unavailable'
    END,
    'aurora-receipt',
    'retrieval_receipt',
    rr.receipt_id::TEXT,
    rr.created_at,
    COALESCE(
        NULLIF(rr.latency_breakdown->>'total_ms', '')::INTEGER,
        NULLIF(rr.latency_breakdown->>'total', '')::INTEGER
    ),
    jsonb_build_object(
        'hard_constraints', rr.hard_constraints,
        'soft_preferences', rr.soft_preferences,
        'relaxations', rr.relaxations,
        'retrieval_config', rr.retrieval_config,
        'candidate_count', jsonb_array_length(rr.candidate_product_ids),
        'citation_ids', rr.citation_ids,
        'embedding_model', rr.embedding_model,
        'rerank_model', rr.rerank_model,
        'rail', rr.rail,
        'trace_id', rr.trace_id
    )
  FROM pellier.retrieval_receipts rr
 WHERE rr.turn_id IS NOT NULL

UNION ALL

SELECT
    gqr.turn_id,
    gqr.session_id,
    gqr.principal_sub,
    'aurora',
    'execution',
    CASE
        WHEN NOT gqr.accepted THEN 'denied'
        WHEN gqr.execution_outcome = 'success' THEN 'succeeded'
        ELSE 'failed'
    END,
    'aurora-receipt',
    'governed_query_receipt',
    gqr.receipt_id::TEXT,
    gqr.created_at,
    gqr.latency_ms,
    jsonb_build_object(
        'accepted', gqr.accepted,
        'validation', gqr.validation,
        'rejection_reason', gqr.rejection_reason,
        'role_used', gqr.role_used,
        'statement_timeout', gqr.statement_timeout,
        'result_limit', gqr.result_limit,
        'row_count', gqr.row_count,
        'execution_outcome', gqr.execution_outcome,
        'schemas_read', gqr.schemas_read
    )
  FROM pellier.governed_query_receipts gqr
 WHERE gqr.turn_id IS NOT NULL

UNION ALL

SELECT
    mir.turn_id,
    mir.session_id,
    mir.principal_sub,
    'model',
    'reasoning',
    mir.outcome,
    CASE
        WHEN mir.source = 'agentcore-service-telemetry'
            THEN 'agentcore-service-telemetry'
        ELSE 'aurora-receipt'
    END,
    'model_invocation_receipt',
    mir.invocation_id::TEXT,
    mir.created_at,
    mir.latency_ms,
    jsonb_build_object(
        'model_id', mir.model_id,
        'inference_profile_id', mir.inference_profile_id,
        'purpose', mir.purpose,
        'input_tokens', mir.input_tokens,
        'output_tokens', mir.output_tokens,
        'total_tokens', mir.total_tokens,
        'stop_reason', mir.stop_reason,
        'trace_id', mir.trace_id,
        'span_id', mir.span_id,
        'source', mir.source
    )
  FROM pellier.model_invocation_receipts mir

UNION ALL

SELECT
    gtr.turn_id,
    ta.session_id,
    gtr.principal_sub,
    'tool',
    'execution',
    CASE WHEN ta.result IS NULL THEN 'unavailable' ELSE 'succeeded' END,
    'aurora-receipt',
    'tool_audit',
    ta.audit_id::TEXT,
    ta.created_at,
    ta.latency_ms,
    jsonb_build_object(
        'tool', ta.tool,
        'caller', ta.caller
    )
  FROM pellier.tool_audit ta
  JOIN pellier.governed_turn_receipts gtr
    ON gtr.turn_id = ta.args->>'turn_id'

UNION ALL

SELECT
    gtr.turn_id,
    gtr.session_id,
    gtr.principal_sub,
    'policy',
    'governance',
    CASE upper(COALESCE(policy_event->>'decision', ''))
        WHEN 'ALLOW' THEN 'succeeded'
        WHEN 'DENY' THEN 'denied'
        WHEN 'WOULD_DENY' THEN 'not_enforced'
        ELSE 'not_enforced'
    END,
    CASE
        WHEN policy_event->>'source' = 'managed_runtime_error'
            THEN 'agentcore-service-telemetry'
        ELSE 'aurora-receipt'
    END,
    'governed_turn_receipt_policy',
    gtr.turn_id || ':' || policy.ordinality::TEXT,
    COALESCE(
        NULLIF(policy_event->>'created_at', '')::TIMESTAMPTZ,
        gtr.created_at
    ),
    NULL::INTEGER,
    policy_event
  FROM pellier.governed_turn_receipts gtr
 CROSS JOIN LATERAL jsonb_array_elements(gtr.policy_events)
    WITH ORDINALITY AS policy(policy_event, ordinality)

UNION ALL

SELECT
    gtr.turn_id,
    gtr.session_id,
    gtr.principal_sub,
    'response',
    'terminal',
    CASE gtr.terminal_status
        WHEN 'complete' THEN 'succeeded'
        WHEN 'denied-before-execution' THEN 'denied'
        WHEN 'evidence-unavailable' THEN 'unavailable'
        WHEN 'trace-pending' THEN 'unavailable'
        ELSE 'failed'
    END,
    'aurora-receipt',
    'governed_turn_receipt',
    gtr.turn_id,
    gtr.created_at,
    gtr.latency_ms,
    jsonb_build_object(
        'rail', gtr.rail,
        'terminal_status', gtr.terminal_status,
        'citation_count', jsonb_array_length(gtr.citations),
        'tool_count', jsonb_array_length(gtr.tool_audit_ids),
        'trace', gtr.trace
    )
  FROM pellier.governed_turn_receipts gtr;

COMMENT ON VIEW pellier.evidence_ledger_event_refs IS
    'Safe metadata-only index over canonical evidence sources. API reads must '
    'filter by verified principal_sub; source tables remain authoritative.';

REVOKE ALL ON pellier.evidence_ledger_event_refs
    FROM PUBLIC, pellier_agent, pellier_query;

COMMIT;
