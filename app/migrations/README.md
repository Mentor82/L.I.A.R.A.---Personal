# Superseded (issue #12)

These 5 SQL files are historical only - not authoritative, not run by any
deploy script, and not tracked by Alembic's `alembic_version`. They were
applied to production by hand, once each, outside any migration tool. All
of their schema is now captured in Alembic (the single authoritative
migration path for this project):

- `4d_memory_schema.sql`, `web_safety_schema.sql`, `location_privacy_schema.sql`
  -> `app/alembic/versions/646650e0d366_add_chat_session_tables.py`
  (its `upgrade()` was previously an empty no-op with the real `CREATE TABLE`
  statements sitting in `downgrade()` instead - fixed live, see that
  revision's own docstring)
- `004_web_safety_lists.sql`
  -> `app/alembic/versions/9ff1059e5ba1_add_web_safety_lists_table.py`
- `user_preferences_schema.sql`
  -> `app/alembic/versions/e24ab6a63a0a_add_user_preferences_table.py`

Do not run these files again and do not add new ones here - write a new
Alembic revision instead (`alembic revision -m "..."`, or autogenerate
against the models in `app/api/models/`). Kept in place for historical
reference only.
