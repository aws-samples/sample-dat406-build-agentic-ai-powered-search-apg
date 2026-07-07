-- Pellier governed workshop - optional RLS rail (reference setup)
--
-- Third gate in the defense-in-depth ladder:
--   Cedar (Gateway)      denies before the tool executes
--   BusinessLogic (tool) rejects returns for products the customer never bought
--   RLS (Aurora)         refuses the write inside the database engine itself
--
-- The rail is opt-in and zero blast radius: RLS binds only to the
-- pellier_agent_rls role created here. The backend and every required
-- exercise connect as the cluster master user (the table owner), which
-- Postgres exempts from RLS unless FORCE ROW LEVEL SECURITY is set — and
-- this rail deliberately does not set it.
--
-- Idempotent. Reverse with rls_rail_reset.sql.
-- Run: psql -f solutions/the-ledger/sql/rls_rail_setup.sql

\set ON_ERROR_STOP on
BEGIN;

-- 1. The constrained identity the agent's write path WOULD use in
--    production (instead of the master user the workshop box uses).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pellier_agent_rls') THEN
        CREATE ROLE pellier_agent_rls NOLOGIN;
    END IF;
END $$;

-- Membership so the workshop session can SET ROLE into it.
GRANT pellier_agent_rls TO CURRENT_USER;

-- 2. Least privilege: the returns write path needs exactly this much.
GRANT USAGE ON SCHEMA pellier TO pellier_agent_rls;
GRANT SELECT, INSERT ON pellier.returns TO pellier_agent_rls;
-- Resolve the id sequence by lookup: migration 005 may have relocated the
-- table from public, and the owned sequence keeps its original name.
DO $$
DECLARE
    seq text := pg_get_serial_sequence('pellier.returns', 'id');
BEGIN
    IF seq IS NOT NULL THEN
        EXECUTE format(
            'GRANT USAGE, SELECT ON SEQUENCE %s TO pellier_agent_rls', seq
        );
    END IF;
END $$;
-- Product lookup for the INSERT subquery; FK validation itself runs with
-- the table owner's privileges and needs no grant.
GRANT SELECT ON pellier.product_catalog TO pellier_agent_rls;

-- 3. Bind RLS to the table. Owner (the app) is unaffected: no FORCE.
ALTER TABLE pellier.returns ENABLE ROW LEVEL SECURITY;

-- 4. The participant-authored policy. current_setting(..., true) returns
--    NULL when the GUC is unset, so an unclaimed session matches nothing:
--    fail closed by default.
DROP POLICY IF EXISTS returns_self_only ON pellier.returns;
CREATE POLICY returns_self_only ON pellier.returns
    FOR ALL
    TO pellier_agent_rls
    USING (customer_id = current_setting('pellier.customer_id', true))
    WITH CHECK (customer_id = current_setting('pellier.customer_id', true));

COMMIT;

\echo 'RLS rail ready: SET ROLE pellier_agent_rls; SET pellier.customer_id = ''theo'';'
