#!/usr/bin/env python3
"""Deprecated production path.

This file is intentionally non-operational. FUW setup must not use Render
Shell, local application/database state, emergency seed routes, migration
stamping, or unscoped deletes. Use the live production API for workflow
actions and the Supabase Management API for narrowly scoped production SQL.
See docs/DEPLOYMENT-STATUS.md.
"""

raise SystemExit(
    "Deprecated: do not seed production through Render Shell. "
    "Use the production-only workflow documented in docs/DEPLOYMENT-STATUS.md."
)
