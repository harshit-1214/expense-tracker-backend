# alembic/versions/ - migration scripts

One file per schema change. File names start with the date they were created
so they sort in the order they are applied.

- `upgrade()` applies the change, `downgrade()` reverses it.
- Never edit a migration that has already run on a shared or production
  database. Create a new migration instead.
