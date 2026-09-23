# Deprecated: Render Shell recovery instructions

Do not use this document for the current FUW production setup. Render Shell
seeding, local application setup, public emergency seed routes, migration
stamping, and unscoped deletes are prohibited for this workflow.

The supported path is:

1. deploy application changes through the repository's normal production
   deployment;
2. use the live Vercel/production API for authenticated workflow actions;
3. use the Supabase Management API for narrowly scoped production SQL when
   an administrative data operation is required; and
4. keep all passwords, JWTs, database credentials, and provider tokens out of
   source files, logs, chat, and workspace documents.

See `docs/DEPLOYMENT-STATUS.md` for the current production state and the
scoped FUW pilot cleanup selectors. This file is retained only as a guard
against accidentally following the old recovery path.
