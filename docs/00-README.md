# Code explanation docs

These documents explain the Expense Tracker backend **file by file, line by line**.
They are written for the developer who built the earlier posts API and wants to
understand every word of the new code: what each line is, why it is there, and
what would break if it were removed.

Read them in order the first time. After that, jump to the folder you are working in.

| #  | Document                                              | What it explains                                                           |
| -- | ----------------------------------------------------- | -------------------------------------------------------------------------- |
| 01 | [Project root files](01-project-root-files.md)        | `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`   |
| 02 | [app package and main](02-app-package-and-main.md)    | `app/__init__.py`, `app/main.py` (app creation, lifespan, CORS, routers)   |
| 03 | [core: config](03-core-config.md)                     | `app/core/config.py` (settings, `model_config`, `.env`, database URL)      |
| 04 | [core: security and dependencies](04-core-security-and-dependencies.md) | `app/core/security.py` (hashing, JWT), `app/core/dependencies.py` (`Depends`, current user, date range) |
| 05 | [database](05-database.md)                            | `app/database/base.py`, `app/database/session.py`                         |
| 06 | [models](06-models.md)                                | `app/models/user.py`, `category.py`, `expense.py` (tables, relationships)  |
| 07 | [schemas](07-schemas.md)                              | `app/schemas/*` (request and response shapes, validators)                  |
| 08 | [routers part 1](08-routers-health-auth-users-categories.md) | `health.py`, `auth.py`, `users.py`, `categories.py`                 |
| 09 | [routers part 2](09-routers-expenses-reports.md)      | `expenses.py`, `reports.py`                                                |
| 10 | [alembic migrations](10-alembic-migrations.md)        | `alembic.ini`, `alembic/env.py`, the migration file                        |
| 11 | [request flow part 1](11-request-flow-startup-auth-users-categories.md) | Deep trace of startup, `/health`, `/auth`, `/users`, `/categories` |
| 12 | [request flow part 2](12-request-flow-expenses-reports.md) | Deep trace of `/expenses` and `/reports`, with the real SQL           |

## How each file-explanation doc is laid out

For every source file:

1. **What this file is for** - its job and its place in the project.
2. **The whole file** - the complete code in one block.
3. **Walkthrough, block by block** - the file in small pieces. Each piece has:
   the code, one bullet per word or name, *why it is here*, and
   *if you removed or changed it*.
4. **Compared to your old code** - the matching part of the earlier posts API and
   what changed, and why.
5. **Key terms in this file** - a short glossary.

The two **request flow** docs are different: they follow one HTTP request at a
time through routing, dependencies, validation, the function body, the SQL that
SQLAlchemy sends to PostgreSQL, and the response, including every error path.

The `tests/` folder is intentionally not covered here.

## Status (2026-10-06)

- Complete: 01, 02, 03, 04, 05, 06, 07, 08, 09.
- Partly written, stop at a `<!-- CONTINUE -->` marker and will be finished next: 10 (ends inside the migration file walkthrough), 11 (ends after the first endpoints), 12 (only the intro and shared machinery so far).
- The independent review pass has not run yet on any document.
