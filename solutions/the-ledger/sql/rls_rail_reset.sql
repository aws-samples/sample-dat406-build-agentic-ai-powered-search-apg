-- Pellier governed workshop - optional RLS rail (reset)
--
-- Removes everything rls_rail_setup.sql created: the policy, the RLS bind
-- on pellier.returns, and the pellier_agent_rls role with its grants.
-- Safe to run whether or not the rail was ever applied.
-- Run: psql -f solutions/the-ledger/sql/rls_rail_reset.sql

\set ON_ERROR_STOP on
BEGIN;

DROP POLICY IF EXISTS returns_self_only ON pellier.returns;
ALTER TABLE pellier.returns DISABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pellier_agent_rls') THEN
        -- Revokes every privilege granted to the role (it owns no objects),
        -- freeing it for DROP.
        DROP OWNED BY pellier_agent_rls;
        DROP ROLE pellier_agent_rls;
    END IF;
END $$;

COMMIT;

\echo 'RLS rail removed: pellier.returns back to shipped state.'
