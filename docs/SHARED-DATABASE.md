# Sharing a Supabase project with another application

These tables can live in a project that already hosts something else, such
as ALIMS2, without the two interfering. Same project, same connection
string, no extra cost.

---

## Why this needs care

Eleven tables are created. Five of the names are ones almost any
application uses:

```
users   notifications   attachments   responses   alembic_version
```

Put them in `public` alongside another system and three things go wrong:

1. **`CREATE TABLE users` fails**, because it already exists. The
   migration stops half way, leaving some tables created and some not.
2. **Worse, if it does not fail**, two applications write different
   shapes to one table and both sets of data become unreliable.
3. **Worst, `alembic_version` is shared.** Our migrations read the other
   application's revision id, do not recognise it, and a later
   autogenerate treats that application's tables as unexpected and
   proposes dropping them.

The third is the one that destroys data rather than merely failing.

---

## The approach

Everything goes in a PostgreSQL schema of its own.

```
resolve.users              ours
resolve.complaints         ours
resolve.alembic_version    our migration history, only ours

public.users               ALIMS2's, untouched
public.alembic_version     ALIMS2's, untouched
```

Set one variable:

```bash
DB_SCHEMA=resolve
```

The migration then creates the schema, puts every table, index and
foreign key inside it, and keeps its version table there too. Alembic is
also told to ignore anything outside the schema, so ALIMS2's tables are
invisible to it and can never appear in a generated migration.

Leave `DB_SCHEMA` unset and everything goes in `public` as normal, which
is right for a database of its own.

---

## What you need to give me, or run yourself

The key in the shared document is `sb_secret_…`, which is a **project API
key**. It reaches PostgREST, Storage and Auth, but it **cannot create
tables** — DDL is not exposed over the REST API at all.

Creating tables needs one of these:

### Option A — run it yourself, nothing to share

In the ALIMS2 dashboard, **Connect → Session pooler**, copy the string,
then from a machine with this repository:

```bash
cd backend
export DATABASE_URL='postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres'
export DB_SCHEMA=resolve
flask db upgrade
```

That is the whole setup. Roughly ten seconds.

### Option B — review the SQL first, then paste it in

Generate the exact statements without connecting to anything:

```bash
cd backend
DB_SCHEMA=resolve DATABASE_URL='postgresql://u:p@h:5432/d' \
  flask db upgrade base:head --sql > resolve-schema.sql
```

Read it, then paste it into the Supabase **SQL Editor** and run. Nothing
in the file touches `public`.

### Option C — send me the connection string and I run it

If you would rather I did it, the **session pooler** connection string is
what I need. Treat it as a password: it grants full access to the whole
project, including ALIMS2's data.

> Whichever you choose, the `sb_secret_…` key is still needed by the
> running application for Storage, so keep it. It is only DDL it cannot
> do.

---

## After the tables exist

```bash
flask seed          # creates the first administrator
```

Set `PLATFORM_ADMIN_EMAIL` and `PLATFORM_ADMIN_PASSWORD` first, and change
the password after signing in.

Then set the same two variables on Render:

```bash
DATABASE_URL=<the session pooler string>
DB_SCHEMA=resolve
```

---

## Checking it worked

In the Supabase SQL Editor:

```sql
-- Ours: expect 11 tables plus alembic_version
select table_name from information_schema.tables
where table_schema = 'resolve' order by table_name;

-- ALIMS2's: expect exactly what was there before
select count(*) from information_schema.tables
where table_schema = 'public';
```

The second query is the one that matters. Run it **before** the migration
as well and compare; the number must not change.

---

## Things worth knowing

**The Table Editor defaults to `public`.** To see these tables, change the
schema selector at the top left to `resolve`. They are not missing.

**PostgREST does not expose the schema by default.** This application
connects over Postgres directly, so it is unaffected. If you later want
the REST API to reach these tables, add `resolve` to Settings → API →
Exposed schemas. Do not do it unless something needs it.

**Backups cover the whole database**, so ALIMS2 and this are backed up
together. That is usually convenient, but it also means a restore returns
both to the same moment. If they need independent recovery, use separate
projects.

**Moving out later is straightforward.** `pg_dump --schema=resolve` into a
project of its own, then drop `DB_SCHEMA`.

---

## A note on the key that was shared

The `sb_secret_…` value was pasted into a shared document and appeared in
plain text in a terminal here. It grants full access to the project,
bypassing row level security.

**Rotate it** in Settings → API once the setup is done, and put the new
value only into Render's environment variables. A shared document is not
a secret store.
