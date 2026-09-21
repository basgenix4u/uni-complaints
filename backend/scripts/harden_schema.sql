-- Re-assert the security posture of the resolve schema.
--
-- Alembic revisions create tables; they do not carry row level security
-- or grant state. So every migration that adds a table silently leaves
-- it less protected than the ones around it. Applying the 0002-0006
-- revisions to the live project produced exactly that: eight new tables
-- with RLS off, sitting beside twelve with it on.
--
-- Run this after every migration against a shared database. It is
-- idempotent and safe to repeat.
--
--   psql "$DATABASE_URL" -f scripts/harden_schema.sql
--
-- The application connects as the schema owner, which bypasses RLS, so
-- this costs nothing operationally. It is defence in depth: if a grant
-- to anon or authenticated is ever added by accident, or the schema is
-- exposed through PostgREST, the tables are not readable by default.

DO $$
DECLARE t record;
BEGIN
  FOR t IN
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'resolve'
      AND c.relkind = 'r'
      AND NOT c.relrowsecurity
  LOOP
    EXECUTE format('ALTER TABLE resolve.%I ENABLE ROW LEVEL SECURITY', t.relname);
    RAISE NOTICE 'enabled RLS on resolve.%', t.relname;
  END LOOP;
END $$;

-- The API roles must hold nothing in this schema. Repeated after every
-- migration because a new table inherits whatever default privileges
-- happen to be in force.
REVOKE ALL ON ALL TABLES IN SCHEMA resolve FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA resolve FROM anon, authenticated;
REVOKE ALL ON SCHEMA resolve FROM anon, authenticated;

-- Verification. Both must return zero.
SELECT count(*) AS tables_without_rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'resolve' AND c.relkind = 'r' AND NOT c.relrowsecurity;

SELECT count(*) AS grants_to_api_roles
FROM information_schema.role_table_grants
WHERE table_schema = 'resolve' AND grantee IN ('anon', 'authenticated');
