-- tool_audit_recap.sql – Act II: Exercise 4 (Aurora ledger proof)
--
-- Drops in for the in-room SQL proof when a participant runs out of time.
-- In the governed format, an allowed managed write records caller='gateway';
-- a Cedar DENY stops before Lambda execution and writes no tool_audit row.
-- The builders format retains caller='agent' for its in-process path. This
-- script pulls the most recent executed initiate_return for 'theo' and prints:
--
--   1) raw row              – tool, caller, args, result, latency_ms
--   2) JSONB extraction     – args->>'reason', result->>'return_id', etc.
--   3) rail label           – caller identifies managed vs in-process execution
--   4) recent trail         – last few initiate_return rows for the customer
--   5) rail/reason aggregate – compares managed and builders-format evidence
--   6) Gateway no-row check – only meaningful after an attempted Gateway DENY
--
-- Run (bare psql picks up the PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE
-- vars bootstrap exports – no connection string needed):
--   psql -f solutions/the-ledger/sql/tool_audit_recap.sql
--
-- Optional: override the customer (defaults to 'theo'):
--   psql -v customer=theo -f solutions/the-ledger/sql/tool_audit_recap.sql

\if :{?customer}
\else
\set customer theo
\endif

\echo ''
\echo '== Most recent executed initiate_return (customer-keyed) ========='
\echo ''

SELECT :'customer' AS customer, MAX(created_at) AS last_seen
  FROM pellier.tool_audit
 WHERE tool = 'initiate_return'
   AND args->>'customer_id' = :'customer';

\echo ''
\echo '== Raw row ====================================================='
\echo ''

SELECT tool,
       caller,
       args,
       result,
       latency_ms,
       created_at
  FROM pellier.tool_audit
 WHERE tool = 'initiate_return'
   AND args->>'customer_id' = :'customer'
 ORDER BY created_at DESC
 LIMIT 1;

\echo ''
\echo '== JSONB-extracted view ========================================'
\echo ''

SELECT tool,
       args->>'customer_id'  AS customer,
       args->>'product_id'   AS product_id,
       args->>'reason'       AS reason,
       result->>'return_id'  AS return_id,
       result->>'status'     AS status,
       latency_ms
  FROM pellier.tool_audit
 WHERE tool = 'initiate_return'
   AND args->>'customer_id' = :'customer'
 ORDER BY created_at DESC
 LIMIT 1;

\echo ''
\echo '== Rail label for latest row ==================================='
\echo ''

SELECT caller,
       args->>'reason' AS return_reason,
       CASE caller
         WHEN 'agent' THEN 'in-process storefront rail'
         WHEN 'gateway' THEN 'managed Gateway rail'
         ELSE 'unknown rail'
       END AS rail,
       created_at
  FROM pellier.tool_audit
 WHERE tool = 'initiate_return'
   AND args->>'customer_id' = :'customer'
 ORDER BY created_at DESC
 LIMIT 1;

\echo ''
\echo '== Recent initiate_return trail ================================='
\echo ''

SELECT created_at,
       caller,
       args->>'reason'       AS reason,
       result->>'status'     AS status,
       result->>'return_id'  AS return_id,
       latency_ms
  FROM pellier.tool_audit
 WHERE tool = 'initiate_return'
   AND args->>'customer_id' = :'customer'
 ORDER BY created_at DESC
 LIMIT 5;

\echo ''
\echo '== Rail/reason aggregate ======================================='
\echo ''

SELECT caller,
       args->>'reason' AS reason,
       count(*)        AS calls
  FROM pellier.tool_audit
 WHERE tool = 'initiate_return'
   AND args->>'customer_id' = :'customer'
 GROUP BY caller, args->>'reason'
 ORDER BY caller, calls DESC;

\echo ''
\echo '== Gateway changed_mind no-row check ==========================='
\echo ''

SELECT count(*) AS gateway_changed_mind_rows
  FROM pellier.tool_audit
 WHERE tool = 'initiate_return'
   AND caller = 'gateway'
   AND args->>'customer_id' = :'customer'
   AND args->>'reason' = 'changed_mind';

\echo ''
\echo 'Notes:'
\echo '  - args / result are JSONB. ->> returns text; -> returns JSONB.'
\echo '  - Governed path: allowed Lambda-backed calls write caller=gateway.'
\echo '  - Builders path: in-process tools write caller=agent.'
\echo '  - A zero gateway_changed_mind_rows count is a DENY signal only if you'
\echo '    actually attempted that call through Gateway. It is not proof on the'
\echo '    builders in-process rail.'
\echo '  - In-process changed_mind is valid and would write caller=agent.'
\echo '  - latency_ms is the tool round-trip measured by the active rail, not'
\echo '    the LLM call.'
