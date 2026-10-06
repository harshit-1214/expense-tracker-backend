# Alembic migrations (alembic.ini, env.py, versions/)

This document explains the files that manage the **shape of the database**: which tables exist, which columns they have, which rules (primary keys, foreign keys, unique rules, checks) they follow.

## What Alembic is for, in plain words

Your Python models (`app/models/*.py`) describe tables. But a model is only a *description*. Somebody has to actually run `CREATE TABLE ...` in PostgreSQL. And later, when you add a column to a model, somebody has to run `ALTER TABLE ... ADD COLUMN ...` on every database that already exists: your laptop, a teammate's laptop, the production server.

Alembic is that somebody. It works like this:

1. Every change to the database is written as a small Python file, called a **migration** (or a **revision**). It lives in `alembic/versions/`. Each file has an `upgrade()` function (apply the change) and a `downgrade()` function (undo it).
2. Each migration has a random id (like `fb8fc28ab769`) and remembers the id of the migration before it. Together they form a chain, oldest to newest.
3. Alembic keeps a tiny table in your database called `alembic_version`. It holds one value: the id of the last migration that was applied. So Alembic always knows where a database is in the chain and what is still missing.
4. `alembic upgrade head` means "walk the chain from where this database is, to the newest migration, running `upgrade()` of each file on the way".
5. `alembic revision --autogenerate -m "..."` means "compare my models with the real database and write the difference into a new migration file for me".

Without Alembic you would have to write and remember every `ALTER TABLE` by hand and hope every database got the same ones in the same order. With Alembic the history of the schema is just files in git.

Versions used while writing this (every claim below was checked against them with the project's own Python environment): Alembic 1.20.0, SQLAlchemy 2.0.54, Python 3.14. Where I show SQL, it is the real SQL Alembic printed for this project (`alembic upgrade head --sql`), not something I typed from memory.

The files in this document:

| File                                                                               | Job                                                                       |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `alembic.ini`                                                                      | Alembic's settings file: where the migrations live, how files are named, how logging looks. |
| `alembic/env.py`                                                                   | The Python script Alembic runs for every command. It connects Alembic to *your* database URL and *your* models. |
| `alembic/script.py.mako`                                                           | The template used to write a new migration file. **Note: this file is missing in the new project** (see its section). |
| `alembic/versions/2026_10_05_fb8fc28ab769_create_users_categories_and_expenses_tables.py` | The one migration that exists: it creates all three tables. |

There are also two small `README.md` files (`alembic/README.md`, `alembic/versions/README.md`). They are plain notes for humans and contain no code, so they are not walked through here.

---

## File: alembic.ini

### What this file is for

This is Alembic's configuration file. It is not Python. It is an **INI file**: a plain text format made of `[sections]` and `key = value` lines. Python reads it with its built-in `configparser` module.

The `alembic` command looks for this file in the folder you run it from (that is why you always run `alembic ...` from the project root). From it Alembic learns: where the `env.py` and `versions/` folder are, how to name new migration files, and how to set up logging. The database URL is **not** in this file on purpose; it comes from `.env` through `app/core/config.py` (see the `NOTE` block below).

Who reads it: the `alembic` command line tool, which turns it into a `Config` object; `alembic/env.py` then receives that object as `context.config` and passes the file name to Python's logging setup. Nothing in `app/` reads this file. It imports nothing (it is not code).

### The whole file

```ini
# Alembic configuration (database migrations).
#
# Common commands (run from the project root):
#   alembic upgrade head                              apply all pending migrations
#   alembic revision --autogenerate -m "add x table"  create a migration from model changes
#   alembic downgrade -1                              undo the last migration
#   alembic history                                   list all migrations

[alembic]
# Folder that holds env.py and the versions/ directory.
script_location = %(here)s/alembic

# Migration file names start with the date so they sort in the order they
# were created, e.g. 2026_10_05_1f2e3d4c5b6a_create_users_table.py
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s

# Adds the project root to sys.path so env.py can `import app`.
prepend_sys_path = .

# How lists of paths in this file are separated (os = the OS default).
path_separator = os

# NOTE: there is no `sqlalchemy.url` here on purpose. The database URL is
# built from the .env file by app/core/config.py and used in alembic/env.py,
# so the password never has to be written in this file.


# ---------------------------------------------------------------------------
# Logging configuration (used by alembic/env.py)
# ---------------------------------------------------------------------------
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### Walkthrough, block by block

(The code blocks below are marked `ini`, not `python`, because this file is not Python.)

### Block 1: the header comment

```ini
# Alembic configuration (database migrations).
#
# Common commands (run from the project root):
#   alembic upgrade head                              apply all pending migrations
#   alembic revision --autogenerate -m "add x table"  create a migration from model changes
#   alembic downgrade -1                              undo the last migration
#   alembic history                                   list all migrations
```

- `#` - in an INI file a line that starts with `#` is a comment. `configparser` skips it completely. (A `;` also starts a comment, but this file only uses `#`.)
- `Alembic configuration (database migrations).` - the title line: tells you what this file is.
- `Common commands (run from the project root):` - reminds you that every `alembic` command must be run from the folder that contains this file, because Alembic looks for `alembic.ini` in the current folder.
- `alembic upgrade head` - `upgrade` = move forward through the migration chain; `head` = "the newest migration". Together: apply everything that is not applied yet.
- `alembic revision --autogenerate -m "add x table"` - `revision` = create a new migration file; `--autogenerate` = fill it in by comparing the models with the real database; `-m "..."` = the message, which becomes the docstring and the end of the file name.
- `alembic downgrade -1` - `downgrade` = move backward; `-1` = one step back, i.e. run `downgrade()` of the last applied migration.
- `alembic history` - print the chain of migrations, newest first.

**Why it is here:** these four commands are the ones you run every week. Having them at the top of the file you open anyway saves a trip to the documentation.

**If you removed or changed it:** nothing would change for Alembic; comments are ignored. You would only lose the reminder.

### Block 2: the `[alembic]` section header

```ini
[alembic]
```

- `[` and `]` - in an INI file, a name in square brackets on its own line starts a **section**. Every `key = value` line below it belongs to that section, until the next `[...]` header.
- `alembic` - the section name. Alembic reads its main settings from the section with this exact name. (Internally the `Config` object calls it `config_ini_section`, and its default value is the string `"alembic"`.)

**Why it is here:** `configparser` requires every key to live inside a section. Alembic looks only in `[alembic]` for `script_location`, `file_template` and the other keys below.

**If you removed or changed it:** if you renamed it (say `[migrations]`) every key under it would become invisible to Alembic. The very next command would fail with `FAILED: No 'script_location' key found in configuration.` because that key is the first thing Alembic needs.

### Block 3: `script_location`

```ini
# Folder that holds env.py and the versions/ directory.
script_location = %(here)s/alembic
```

- `# Folder that holds env.py and the versions/ directory.` - comment saying what the next key means.
- `script_location` - the key. Alembic reads it to find the folder that contains `env.py`, `script.py.mako` and the `versions/` folder. It is the only setting Alembic refuses to work without.
- `=` - in an INI file the equals sign separates the key (left) from the value (right). Spaces around it are ignored.
- `%(here)s` - this is **configparser interpolation**. `configparser` has a small template language: `%(name)s` means "insert the value called `name` here". The `s` at the end means "as a string". Alembic sets `here` to the absolute path of the folder that contains `alembic.ini`, written with forward slashes (I checked the source: `self.config_args["here"] = here.as_posix()`). So on your machine this becomes `C:/Users/hp/Desktop/zip/expense-tracker-backend/alembic`.
- `/alembic` - the sub-folder name added after the project folder.

**Why it is here:** using `%(here)s` instead of a plain `alembic` means the setting works no matter which folder the command is run from, because it is relative to the ini file, not to the current folder.

**If you removed or changed it:** removing it: every command fails at once with `FAILED: No 'script_location' key found in configuration.` (that is the exact message in Alembic's source). Pointing it at a folder that does not exist: `FAILED: Path doesn't exist: ...  Please use the 'init' command to create a new scripts folder.`

### Block 4: `file_template`

```ini
# Migration file names start with the date so they sort in the order they
# were created, e.g. 2026_10_05_1f2e3d4c5b6a_create_users_table.py
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s
```

- The two comment lines explain the goal: file names begin with the date so that listing the folder shows the migrations in the order they were made.
- `file_template` - the key Alembic reads when it names a new migration file (`alembic revision ...`). The `.py` is added automatically.
- `%%` - a **doubled percent sign**. Remember from the previous block that `configparser` treats `%(...)s` as its own template. But here we want Alembic, not configparser, to fill in the names. Writing `%%` tells configparser "this is a literal percent sign, leave it alone". After configparser is done, the value Alembic receives is `%(year)d_%(month).2d_%(day).2d_%(rev)s_%(slug)s` with single `%` signs (I ran this through `configparser` to confirm).
- `%(year)d` - this is **Python old-style string formatting**, the same `%` language Python uses in `"hello %s" % name`. `%(year)` means "take the value named `year`"; the `d` means "format it as a whole number" (d = decimal integer). Gives `2026`.
- `_` - a literal underscore, copied as-is.
- `%(month).2d` - the month as an integer; `.2` means "at least 2 digits, pad with zeros". So October gives `10` and March would give `03`. This padding is what makes the names sort correctly as text.
- `%(day).2d` - the day, also padded to two digits: `05`.
- `%(rev)s` - the random 12-character revision id (`s` = as a string): `fb8fc28ab769`.
- `%(slug)s` - the "slug" built from your `-m` message: every word is kept, joined with underscores, lower-cased. `"create users, categories and expenses tables"` becomes `create_users_categories_and_expenses_tables`.

The full list of names Alembic offers to this template (from its source, `alembic/script/base.py`): `rev`, `slug`, `epoch`, `year`, `month`, `day`, `hour`, `minute`, `second`.

One honest detail: Alembic cuts the slug at 40 characters by default (setting `truncate_slug_length`). The slug above is 43 characters, so Alembic would have produced `2026_10_05_fb8fc28ab769_create_users_categories_and_expenses_.py` (I generated one with the same message to check). The file in the project has the full word `tables`, so it was renamed by hand after it was generated. That is fine: Alembic identifies a migration by the `revision` value *inside* the file, not by the file name.

**Why it is here:** Alembic's default template is `%(rev)s_%(slug)s`, which puts the random id first. Random ids do not sort, so with the default you cannot tell from the folder listing which migration came first. The date prefix fixes that.

**If you removed or changed it:** removing it only changes the names of *future* files (back to `fb8fc28ab769_create_....py` style); existing files keep working. Writing a single `%` instead of `%%` would make configparser try to interpolate `%(year)d` itself; `d` is not a valid ending for configparser (it only knows `s`), so reading the key crashes with `configparser.InterpolationSyntaxError: bad interpolation variable reference '%(year)d_...'` (I reproduced this).

### Block 5: `prepend_sys_path`

```ini
# Adds the project root to sys.path so env.py can `import app`.
prepend_sys_path = .
```

- The comment says what the key is for.
- `prepend_sys_path` - the key. Alembic reads it before it runs `env.py` and puts each listed path at the *front* of `sys.path`. In the source it is literally `sys.path[:0] = prepend_sys_path`.
- `sys.path` - the Python list of folders where `import` looks for modules. If a folder is not in that list, `import` cannot find packages inside it.
- `.` - one path: the current folder (a single dot always means "the folder I am in"). Because you run `alembic` from the project root, `.` is the project root, which is where the `app/` package lives.

**Why it is here:** `alembic/env.py` does `import app.models`, `from app.core.config import settings` and `from app.database.base import Base`. The `alembic` command is a separate program; it does not know about your project. This line is what makes `import app` succeed.

**If you removed or changed it:** `alembic upgrade head` (and every other command that runs `env.py`) would stop with `ModuleNotFoundError: No module named 'app'` on line 15 of `env.py`. Technically Alembic falls back to the current working directory when the key is absent, so in practice it would still work if you run from the project root, but the explicit `.` makes that intention visible and does not rely on a fallback.

### Block 6: `path_separator`

```ini
# How lists of paths in this file are separated (os = the OS default).
path_separator = os
```

- The comment explains the key.
- `path_separator` - the key. Some settings (like `prepend_sys_path` above, or `version_locations`, which this project does not use) can hold a *list* of paths. This key says which character separates the items.
- `os` - a special word meaning "use the operating system's own separator", which Python exposes as `os.pathsep`. On Windows that is `;`, on Linux and macOS it is `:`. The other allowed values are `:`, `;`, `space` and `newline` (a wrong value raises `ValueError: '...' is not a valid value for path_separator; expected 'space', 'newline', 'os', ':', ';'`).

**Why it is here:** the project has only one path in `prepend_sys_path`, so the separator never actually splits anything. It is here because recent Alembic versions print a deprecation warning when the key is missing ("No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons ..."). Setting it keeps the output clean and makes future multi-path settings unambiguous.

**If you removed or changed it:** you would see that deprecation warning on every command, and Alembic would split paths on spaces, commas *and* colons (the old behaviour). With a Windows path like `C:/x` in a list, splitting on `:` would break it into `C` and `/x`.

### Block 7: the `NOTE` about `sqlalchemy.url`

```ini
# NOTE: there is no `sqlalchemy.url` here on purpose. The database URL is
# built from the .env file by app/core/config.py and used in alembic/env.py,
# so the password never has to be written in this file.
```

- These are comment lines, so they change nothing. They exist to stop you (or a teammate) from "fixing" the file by adding the key back.
- `sqlalchemy.url` - the key that Alembic's default `alembic.ini` contains, holding the full database URL (`postgresql://user:password@host/dbname`). Your old project had it, with a placeholder value.
- `app/core/config.py` - the file that reads `.env` and builds `settings.database_url` (explained in document 03).
- `alembic/env.py` - the file that hands that URL to Alembic (next section).

**Why it is here:** two reasons. First, **security**: `alembic.ini` is committed to git, `.env` is not. A password in `alembic.ini` would be in the repository forever. Second, **one source of truth**: the app and Alembic now read the very same URL, so they can never point at different databases by accident.

**If you removed or changed it:** removing the comment changes nothing. Adding a real `sqlalchemy.url` line would also change nothing, because the new `env.py` never reads that key; it would just be a password sitting in git for no reason.

### Block 8: the logging banner

```ini
# ---------------------------------------------------------------------------
# Logging configuration (used by alembic/env.py)
# ---------------------------------------------------------------------------
```

- Three comment lines: a visual divider and a title for the second half of the file.
- `Logging` - Python's built-in `logging` module. It is the standard way programs print status messages (`INFO`, `WARNING`, `ERROR`) with control over which ones are shown and where they go.
- `(used by alembic/env.py)` - Alembic itself does not apply these sections. `env.py` does, by calling `fileConfig(config.config_file_name)` (Block 9 of `env.py`).

**Why it is here:** everything below follows the fixed format that Python's `logging.config.fileConfig()` expects. The banner tells you that you have entered that part of the file.

**If you removed or changed it:** no effect; comments only.

### Block 9: `[loggers]`

```ini
[loggers]
keys = root,sqlalchemy,alembic
```

- `[loggers]` - a section with a name that `fileConfig()` requires. It lists which loggers the file configures.
- `keys` - the one key `fileConfig()` reads in this section.
- `root,sqlalchemy,alembic` - a comma-separated list of short names. For each name `X` here, `fileConfig()` then looks for a section called `[logger_X]`. So this line promises that `[logger_root]`, `[logger_sqlalchemy]` and `[logger_alembic]` exist below.
- `root` - the top-level logger that every other logger reports to. It must always be listed.

**Why it is here:** it is the table of contents for the logger sections. Without it `fileConfig()` does not know which `[logger_...]` sections to read.

**If you removed or changed it:** `fileConfig()` raises `KeyError: 'loggers'` (I reproduced every error in this logging part by deleting the lines and calling `fileConfig()`), which stops `env.py` on line 24 before any migration runs. Removing a name from the list (say `alembic`) would make `[logger_alembic]` ignored, and Alembic's `INFO` lines would then follow the root level, `WARNING`, so you would no longer see the "Running upgrade ..." messages.

### Block 10: `[handlers]`

```ini
[handlers]
keys = console
```

- `[handlers]` - required section listing the **handlers**. A handler is the thing that actually writes a log line somewhere: to the screen, to a file, over the network.
- `keys = console` - one handler, nicknamed `console`, described in `[handler_console]` below.

**Why it is here:** same role as `[loggers]`: a table of contents for handler sections.

**If you removed or changed it:** `fileConfig()` raises `KeyError: 'handlers'` and the command stops.

### Block 11: `[formatters]`

```ini
[formatters]
keys = generic
```

- `[formatters]` - required section listing the **formatters**. A formatter decides how one log line looks (which fields, in what order).
- `keys = generic` - one formatter, nicknamed `generic`, described in `[formatter_generic]` below.

**Why it is here:** table of contents for formatter sections.

**If you removed or changed it:** `fileConfig()` raises `KeyError: 'formatters'` and the command stops.

### Block 12: `[logger_root]`

```ini
[logger_root]
level = WARNING
handlers = console
qualname =
```

- `[logger_root]` - the section for the `root` logger promised in `[loggers]`.
- `level = WARNING` - the minimum importance a message needs to be shown. The levels, from low to high, are `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. `WARNING` means: hide `DEBUG` and `INFO` messages from any library that has no logger section of its own, show warnings and worse.
- `handlers = console` - attach the `console` handler, so messages that reach the root logger are written to the screen.
- `qualname =` - the "qualified name" of the logger, i.e. the name used in the code (`logging.getLogger("that.name")`). For the root logger it is empty, because root has no name.

**Why it is here:** the root logger is the safety net. Every message from every library ends up here unless a more specific logger handles it. Setting `WARNING` keeps unrelated libraries quiet.

**If you removed or changed it:** removing the section raises `KeyError: 'logger_root'`. Changing `level` to `DEBUG` would flood the screen with internal messages from every library. Removing `handlers = console` would mean no handler anywhere, so Alembic's own messages (which only *propagate* to root, see next blocks) would be printed by nothing; you would see no "Running upgrade" lines at all.

### Block 13: `[logger_sqlalchemy]`

```ini
[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine
```

- `[logger_sqlalchemy]` - the section for the nickname `sqlalchemy` from `[loggers]`.
- `level = WARNING` - show only warnings and errors from this logger.
- `handlers =` - an **empty** value: this logger has no handler of its own. Messages that pass its level are passed *up* to the root logger (this passing-up is called *propagation*), and root's `console` handler prints them.
- `qualname = sqlalchemy.engine` - the real logger name. `sqlalchemy.engine` is the logger SQLAlchemy uses to print **every SQL statement it sends** (at `INFO` level). This is the same logger that `create_engine(..., echo=True)` switches on.

**Why it is here:** so you can decide whether to see the SQL of each migration. At `WARNING` you do not. Change this one line to `INFO` and every `CREATE TABLE`, `INSERT` and `ALTER` that a migration runs is printed as it happens. That is a very handy debugging switch.

**If you removed or changed it:** removing the section (and its name from `[loggers]`) just means `sqlalchemy.engine` falls back to root's `WARNING`, so no visible change. Setting `level = INFO` shows all SQL. If you removed only the `qualname` line, `fileConfig()` would raise `KeyError: 'qualname'`.

### Block 14: `[logger_alembic]`

```ini
[logger_alembic]
level = INFO
handlers =
qualname = alembic
```

- `[logger_alembic]` - the section for the nickname `alembic`.
- `level = INFO` - show informational messages and up. Alembic reports its progress at `INFO`.
- `handlers =` - empty again: rely on propagation to root's console handler.
- `qualname = alembic` - the real logger name. Every Alembic logger is named `alembic.something` (for example `alembic.runtime.migration`), and in Python's logging a logger named `alembic.runtime.migration` is a *child* of `alembic`, so this one setting covers them all.

**Why it is here:** this is what gives you the familiar lines when you run a command:

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> fb8fc28ab769, create users, categories and expenses tables
```

**If you removed or changed it:** set `level = WARNING` and those three lines disappear; `alembic upgrade head` would print nothing on success, which is unsettling. Removing the section while leaving `alembic` in `[loggers]` raises `KeyError: 'logger_alembic'`.

### Block 15: `[handler_console]`

```ini
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
```

- `[handler_console]` - the section for the handler nicknamed `console`.
- `class = StreamHandler` - which Python class to build. `StreamHandler` is `logging.StreamHandler`, the handler that writes to a text stream (a file-like object). `fileConfig()` evaluates this name inside the `logging` module, so the `logging.` prefix is not needed.
- `args = (sys.stderr,)` - the arguments passed to that class when it is built. This value is **Python code** that `fileConfig()` runs with `eval()` (I checked: `args = eval(args, vars(logging))`). `(sys.stderr,)` is a tuple with one item: `sys.stderr`, the standard error stream, i.e. the terminal. The trailing comma is what makes it a one-item tuple instead of just a value in parentheses. `sys` is available because the `logging` module itself imports `sys`.
- `level = NOTSET` - the handler's own filter. `NOTSET` (level 0) means "do not filter here; whatever the loggers let through, print". The loggers above already decide the levels.
- `formatter = generic` - use the formatter nicknamed `generic` (next block) to turn each record into text.

**Why it is here:** this is the one place where log lines become visible. Writing to `stderr` rather than `stdout` is deliberate: when you run `alembic upgrade head --sql > schema.sql`, the SQL goes to the file (`stdout`) and the INFO lines still show on screen (`stderr`) instead of polluting the file. The SQL I captured for this document was produced exactly that way.

**If you removed or changed it:** removing the section raises `KeyError: 'handler_console'`. Changing `args` to `(sys.stdout,)` would mix log lines into `--sql` output files. A typo in `args` is a Python error at `eval` time; for example `(sys.stder,)` gives `AttributeError: module 'sys' has no attribute 'stder'`.

### Block 16: `[formatter_generic]`

```ini
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- `[formatter_generic]` - the section for the formatter nicknamed `generic`.
- `format = ...` - the template for one log line. It uses the same `%(name)s` Python formatting seen in `file_template`. (`configparser` does not choke on these because `fileConfig()` reads the raw value without interpolation.)
- `%(levelname)-5.5s` - the level name (`INFO`, `WARNING`...) formatted as a string (`s`) with width rules: `-` = left-align, `5` = pad to at least 5 characters, `.5` = cut to at most 5 characters. So `INFO` becomes `INFO ` (with a trailing space) and `WARNING` becomes `WARNI`. I ran the formatter to confirm: `'INFO  [alembic.runtime.migration] Running upgrade -> fb8fc28ab769'` and `'WARNI [alembic.runtime.migration] hello'`. The fixed width keeps the columns aligned.
- `[%(name)s]` - the logger name in square brackets, for example `[alembic.runtime.migration]`. The brackets are literal characters.
- `%(message)s` - the message text itself.
- `datefmt = %H:%M:%S` - how to format a timestamp (`%H` hours, `%M` minutes, `%S` seconds), **only used if the format contains `%(asctime)s`**. It does not, so this line currently has no visible effect. It is kept so that adding `%(asctime)s` to the format later gives a tidy time.

**Why it is here:** without a formatter the handler would print only the bare message, and you would not know whether a line came from Alembic or from SQLAlchemy.

**If you removed or changed it:** removing the section raises `KeyError: 'formatter_generic'`. Removing just the `format` line does not crash (I checked): Python falls back to the default `%(message)s`, so lines lose the `INFO [name]` prefix.

### Compared to your old code

Your old `alembic.ini` was the untouched file that `alembic init` generates. It is about 120 lines, most of them commented-out options. The parts that actually did something were:

```ini
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .
path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
# (everything commented out)

[loggers] ... (identical logging sections)
```

What changed and why:

1. **`file_template` is now switched on.** In the old file it was a commented-out example, so your migration files were named `a2ea52613b30_add_user_table.py`, `3317c4ec97be_add_content_column_to_post.py` and so on. Look at your old `versions/` folder: the files are in random order, and you cannot tell from the names that "add user table" came *after* "add content column to post". The new date prefix fixes that.
2. **`sqlalchemy.url` is gone.** In the old file it held the placeholder `driver://user:pass@localhost/dbname`, and your old `env.py` then *overwrote* it at runtime with the real URL from `app/database.py`. That worked, but the line in the ini was misleading (it looked like the place to put the password), and the overwrite step had its own pitfall (explained in the `env.py` comparison). The new project removes the key and the comment explains why.
3. **The `[post_write_hooks]` section is gone.** It was entirely comments (how to run `black` or `ruff` on new migration files). The project does not use it, so it was dropped.
4. **All the commented-out options are gone** (`timezone`, `truncate_slug_length`, `revision_environment`, `sourceless`, `version_locations`, `recursive_version_locations`, `output_encoding`). None were in use. If you ever need one, the Alembic documentation lists them; keeping 80 lines of comments in the project made the file hard to read.
5. **A short header with the four everyday commands was added.**
6. **The logging sections are byte-for-byte the same.** They are Alembic's standard setup and there was no reason to change them.

Nothing in the old file was a bug; it simply carried the generator's boilerplate.

### Key terms in this file

| Term               | One-line meaning                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| INI file           | Plain-text settings file made of `[section]` headers and `key = value` lines; read by `configparser`.  |
| `configparser`     | Python's built-in module for reading INI files.                                                        |
| interpolation      | `configparser`'s `%(name)s` feature that inserts another value; `%%` means a literal `%`.              |
| `%(here)s`         | Alembic-provided value: the absolute folder that contains `alembic.ini`.                               |
| `script_location`  | The folder with `env.py`, `script.py.mako` and `versions/`.                                            |
| `file_template`    | Pattern for new migration file names; tokens: `rev`, `slug`, `epoch`, `year`, `month`, `day`, `hour`, `minute`, `second`. |
| slug               | The `-m` message turned into `lower_case_words_with_underscores`, cut at 40 characters.                 |
| `prepend_sys_path` | Folders to put at the front of `sys.path` so `env.py` can `import app`.                               |
| `path_separator`   | Character used to split path lists in this file; `os` = `;` on Windows, `:` elsewhere.                 |
| logger             | A named channel for log messages (`alembic`, `sqlalchemy.engine`, root).                               |
| handler            | The object that writes log lines somewhere (here: `StreamHandler` to `stderr`).                        |
| formatter          | The template that turns one log record into one line of text.                                          |
| level              | Minimum importance to pass: `DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`; `NOTSET` = no filter.   |
| propagation        | A logger with no handler passes its messages up to its parent, ending at root.                         |
| `qualname`         | The logger's real name as used in code, e.g. `sqlalchemy.engine`.                                      |
| `stderr`           | The "error" output stream of a program; kept separate from `stdout` so `--sql` output stays clean.      |

---

## File: alembic/env.py

### What this file is for

`env.py` is the glue between Alembic and *your* project. Alembic itself does not know what database you use or which tables you want. This file tells it both: the database URL (taken from `settings.database_url`, which comes from `.env`) and the list of tables (taken from `Base.metadata`, which the models fill in).

Alembic runs this file **itself**, as a script, every time you run a command that touches the database or the models (`alembic upgrade`, `alembic downgrade`, `alembic current`, `alembic revision --autogenerate`...). You never run it, and nothing in `app/` imports it. If you try `python alembic/env.py` by hand it stops on its first real line with `AttributeError: module 'alembic.context' has no attribute 'config'` (I tried), because the `context` object only exists while Alembic is driving.

What it imports: Python's `logging.config`, SQLAlchemy's `create_engine` and `pool`, Alembic's `context`, and three things from the project: the `app.models` package (for its side effect of registering tables), `settings` from `app/core/config.py`, and `Base` from `app/database/base.py`.

### The whole file

```python
"""
Alembic environment: tells Alembic which database to connect to and which
tables the application expects.

You normally never edit this file. Alembic runs it for every command
(`alembic upgrade head`, `alembic revision --autogenerate`, ...).
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

import app.models  # noqa: F401  (importing registers every table on Base.metadata)
from app.core.config import settings
from app.database.base import Base

# The Alembic Config object: gives access to the values in alembic.ini.
config = context.config

# Set up Python logging from the [loggers] sections of alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# What the database SHOULD look like. `--autogenerate` compares this with
# the real database and writes the difference into a new migration.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    'Offline' mode: print the SQL instead of running it.

    Used by `alembic upgrade head --sql`, e.g. to hand a script to a DBA.
    """
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """'Online' mode (the normal one): connect to the database and run the migrations."""
    # NullPool: a migration is a short one-off script, no connection pool needed.
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""
Alembic environment: tells Alembic which database to connect to and which
tables the application expects.

You normally never edit this file. Alembic runs it for every command
(`alembic upgrade head`, `alembic revision --autogenerate`, ...).
"""
```

- `"""` ... `"""` - a **docstring**: a string at the very top of the file. Python stores it as the module's `__doc__` and otherwise ignores it. It is documentation, not code.
- `Alembic environment` - Alembic's own name for this file ("the migration environment").
- `tells Alembic which database to connect to and which tables the application expects` - the two jobs of the file, in one sentence.
- `You normally never edit this file.` - once it is set up, it stays the same for the life of the project. New tables are added in `app/models/`, not here.
- `Alembic runs it for every command` - the key fact: this is a script Alembic executes, not a module you import.

**Why it is here:** so that someone opening the file knows at once what it is and that they do not need to touch it.

**If you removed or changed it:** nothing changes for Alembic; only the explanation is lost.

### Block 2: importing `fileConfig`

```python
from logging.config import fileConfig
```

- `from ... import ...` - Python's way to bring one name from a module into this file.
- `logging` - Python's built-in logging package (the same one described in the `alembic.ini` section).
- `logging.config` - a sub-module of `logging` that knows how to *configure* logging from a file or a dictionary.
- `fileConfig` - the function that reads an INI-style file (with `[loggers]`, `[handlers]`, `[formatters]` sections) and sets up logging from it.

**Why it is here:** it is used once, in Block 9, to apply the logging sections of `alembic.ini`.

**If you removed or changed it:** line 24 would fail with `NameError: name 'fileConfig' is not defined` and no command would run.

### Block 3: importing `create_engine` and `pool`

```python
from sqlalchemy import create_engine, pool
```

- `sqlalchemy` - the SQLAlchemy library.
- `create_engine` - the function that builds an **Engine**. An Engine knows the database URL and the dialect (PostgreSQL, SQLite...) and hands out connections. Your old `app/database.py` used the same function.
- `pool` - the sub-module `sqlalchemy.pool`, which contains the **connection pool** classes. A pool is a small set of open database connections that an application reuses instead of opening a new one for every query. We only need one class from it, `pool.NullPool`, used in Block 15.

**Why it is here:** the online mode (Block 15) needs to open a real connection to PostgreSQL, and `create_engine` is how SQLAlchemy does that.

**If you removed or changed it:** `NameError: name 'create_engine' is not defined` (or `'pool'`) in `run_migrations_online`, i.e. on every normal `alembic upgrade head`.

### Block 4: importing `context`

```python
from alembic import context
```

- `alembic` - the Alembic library.
- `context` - a special module, `alembic.context`. Its functions (`configure`, `begin_transaction`, `run_migrations`, `is_offline_mode`) and its attribute `config` are **proxies**: thin forwarding functions that only work while Alembic is running this file. Alembic creates the real object (an `EnvironmentContext`) just before it executes `env.py`, and plugs it in behind the proxies. That is why running `env.py` by hand gives `AttributeError: module 'alembic.context' has no attribute 'config'`.

**Why it is here:** `context` is the only channel between this file and the Alembic engine that is running it. Everything this file does, it does by calling `context.something`.

**If you removed or changed it:** `NameError: name 'context' is not defined` on line 20, immediately.

### Block 5: importing the models for their side effect

```python
import app.models  # noqa: F401  (importing registers every table on Base.metadata)
```

- `import app.models` - loads the package `app/models/__init__.py`, which in turn imports `User`, `Category` and `Expense`. The name `app.models` is never used again in this file. The import is here **only for what happens when the file loads**: each model class inherits from `Base`, and the moment a class that inherits from `Base` is created, SQLAlchemy builds a `Table` for it and stores it in `Base.metadata`. So after this line, `Base.metadata` knows about three tables. Before it, `Base.metadata` is empty.
- `# noqa: F401` - a comment aimed at code-checking tools (linters such as `ruff` or `flake8`). `noqa` means "no quality assurance warning here"; `F401` is the rule number for "imported but unused". Without the comment the linter would complain about this line, and a helpful editor might even delete the import "for you".
- `(importing registers every table on Base.metadata)` - the human explanation of why an unused import is kept.

**Why it is here:** `--autogenerate` works by comparing `target_metadata` (Block 10) with the real database. That comparison is only meaningful if `target_metadata` contains all your tables. This line is what fills it.

**If you removed or changed it:** `alembic upgrade head` would still work (it only runs the migration files). But `alembic revision --autogenerate` would see an **empty** `Base.metadata`, conclude that you have deleted every model, and write a migration containing `op.drop_table('expenses')`, `op.drop_table('categories')`, `op.drop_table('users')`. If you applied that without reading it, you would lose all your data. This is the most dangerous single line to remove in the whole folder, which is why it has the loud comment.

### Block 6: importing `settings`

```python
from app.core.config import settings
```

- `app.core.config` - the project's settings module (document 03).
- `settings` - the ready-made `Settings` object. Importing it runs `Settings()`, which reads the environment and the `.env` file. The property we use here is `settings.database_url`, the full PostgreSQL URL.

**Why it is here:** this is how the database URL gets into Alembic without ever being written in `alembic.ini`. One `.env`, one URL, used by both the app and the migrations.

**If you removed or changed it:** `NameError: name 'settings' is not defined` in both `run_migrations_*` functions. Also note a side effect of *keeping* it: because `Settings()` runs at import time, Alembic now refuses to start if `.env` is missing a required value. With no `SECRET_KEY` anywhere you get `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings / SECRET_KEY / Field required` (I reproduced it). That is on purpose: a misconfigured project should fail loudly.

### Block 7: importing `Base`

```python
from app.database.base import Base
```

- `app.database.base` - the file that defines the declarative base (document 05).
- `Base` - the parent class of every model. Its attribute `Base.metadata` is the `MetaData` object holding every `Table` plus the **naming convention** (`pk_%(table_name)s`, `fk_...`, and so on).

**Why it is here:** `Base.metadata` is handed to Alembic as `target_metadata` in Block 10.

**If you removed or changed it:** `NameError: name 'Base' is not defined` on line 28.

### Block 8: `config = context.config`

```python
# The Alembic Config object: gives access to the values in alembic.ini.
config = context.config
```

- The comment says what `config` is.
- `config` - a new variable in this file.
- `=` - assignment.
- `context.config` - the `Config` object Alembic built from `alembic.ini` (plus any `-x` command-line options). It has methods like `get_main_option("script_location")` and the attribute `config_file_name`.

**Why it is here:** the only thing this file needs from the ini is its *file name*, for the logging setup in the next block. Keeping it in a short variable named `config` matches every Alembic example you will find online.

**If you removed or changed it:** `NameError: name 'config' is not defined` on line 23.

### Block 9: logging setup

```python
# Set up Python logging from the [loggers] sections of alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
```

- The comment explains the purpose.
- `if` - run the indented line only when the condition is true.
- `config.config_file_name` - the path of the ini file that Alembic loaded (by default `alembic.ini` in the current folder). It is `None` when Alembic is driven from Python code with a `Config()` that was built without a file.
- `is not None` - "has a value". `is` compares identity; `None` is Python's "nothing" value.
- `:` - ends the `if` line; the indented block follows.
- `fileConfig(config.config_file_name)` - call the function from Block 2 with that path. It reads the `[loggers]`, `[handlers]`, `[formatters]` and related sections and installs them. From this moment on, `INFO [alembic.runtime.migration] ...` lines appear on the screen.

One detail worth knowing: `fileConfig()` has a parameter `disable_existing_loggers` whose default is `True`. It switches off loggers that were created *before* this call and are not named in the ini. In this file the imports above run first, so any logger the app created during import is silenced. For this project that is harmless (nothing above needs to log), but it is why the Alembic template puts this call right after the imports.

**Why it is here:** without it you would see no progress messages at all, and SQLAlchemy would not be told to stay quiet.

**If you removed or changed it:** every `alembic` command would run silently; errors would still be shown (they are raised as exceptions, not logged). Removing only the `if` guard works as long as the file exists; it only matters for programmatic use.

### Block 10: `target_metadata`

```python
# What the database SHOULD look like. `--autogenerate` compares this with
# the real database and writes the difference into a new migration.
target_metadata = Base.metadata
```

- The comment explains the role in one sentence: this is the *desired* state.
- `target_metadata` - the name Alembic expects (it is what the two `context.configure(...)` calls pass on).
- `Base.metadata` - the `MetaData` object with the three tables (thanks to Block 5) and the naming convention.

**Why it is here:** two reasons. (1) `--autogenerate` compares this with the real database. (2) Less known: when a migration calls `op.create_table(...)`, Alembic builds a temporary `MetaData` for it and **copies the naming convention from `target_metadata`** into it (I checked the source, `alembic/operations/schemaobj.py`, method `metadata()`). That is why the migration file needs `op.f()`, explained in the migration section.

**If you removed or changed it:** setting it to `None` would make `--autogenerate` fail with `Can't proceed with --autogenerate option; environment script ... does not provide a MetaData object or sequence of objects to the context.` Plain `alembic upgrade head` would still run.

### Block 11: defining `run_migrations_offline`

```python
def run_migrations_offline() -> None:
    """
    'Offline' mode: print the SQL instead of running it.

    Used by `alembic upgrade head --sql`, e.g. to hand a script to a DBA.
    """
```

- `def` - defines a function.
- `run_migrations_offline` - its name; Alembic's standard name for this helper.
- `()` - it takes no arguments.
- `-> None` - a **return annotation**: a note (not enforced) that the function returns nothing. `None` is Python's "no value".
- `:` - starts the function body.
- The docstring explains the mode: in **offline mode** Alembic does not connect to any database. It *prints* the SQL that the migrations would run. You get this mode by adding `--sql` to a command.
- `DBA` - database administrator. In some companies developers may not run DDL on production themselves; they hand a `.sql` file to a DBA who reviews and runs it. Offline mode produces that file.

**Why it is here:** Alembic's `context.is_offline_mode()` check at the bottom (Block 18) needs a function to call. Even if you never use `--sql`, keeping the standard structure means any Alembic tutorial still matches your file.

**If you removed or changed it:** `alembic upgrade head --sql` would fail with `NameError` at line 61. Normal commands would be unaffected.

### Block 12: configuring the offline context

```python
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
```

- `context.configure(...)` - tells Alembic everything it needs to know before running migrations. Each argument is a keyword argument (`name=value`).
- `url=settings.database_url` - the database URL as a string. In offline mode Alembic does **not** connect; it only reads the URL to learn the *dialect* (the part before `://`, here `postgresql`), so it knows PostgreSQL's SQL flavour. That is why the SQL I captured says `SERIAL`, `TIMESTAMP WITH TIME ZONE` and `now()`, which are PostgreSQL spellings.
- `target_metadata=target_metadata` - the `MetaData` from Block 10 (same name on both sides of `=`: the left is the parameter name, the right is our variable).
- `literal_binds=True` - normally SQLAlchemy sends values separately from the SQL text, as *bound parameters* (placeholders). A `.sql` file cannot carry separate values, so `literal_binds=True` asks the compiler to write the values *into* the SQL text. In the captured output you can see it: `INSERT INTO alembic_version (version_num) VALUES ('fb8fc28ab769')`, with the real string instead of a placeholder.
- `dialect_opts={"paramstyle": "named"}` - a dictionary (`{key: value}`) of extra options for the dialect object. `paramstyle` is how placeholders are spelled when a statement still has any; `"named"` means the `:name` style. With `literal_binds=True` this rarely matters, but Alembic's template sets both, and so does this file.

**Why it is here:** these four values are exactly what Alembic's own generated `env.py` uses for offline mode; the only change is where the URL comes from.

**If you removed or changed it:** without `url` Alembic has no dialect and `--sql` fails with `Can't proceed without a connection or URL` (wording approximate). Without `literal_binds=True` the printed SQL would contain placeholders like `%(version_num)s` instead of values, so the file could not be run as-is.

### Block 13: running the migrations (offline)

```python
    with context.begin_transaction():
        context.run_migrations()
```

- `with` - starts a **context manager** block. A context manager is an object that does something at the start of the block and something else at the end, *even if an error happens in between*. Think "setup ... cleanup, guaranteed".
- `context.begin_transaction()` - returns such a context manager representing a **transaction** (a group of SQL statements that either all succeed or all get undone). In offline mode, entering it prints `BEGIN;` and leaving it prints `COMMIT;`. You can see both in the captured SQL at the start and end.
- `:` - starts the block.
- `context.run_migrations()` - the real work: Alembic looks at the current revision (in offline mode it assumes the starting point you gave, or "nothing applied"), walks the chain to the target, and calls `upgrade()` or `downgrade()` of each migration file. In offline mode every `op.*` call inside those files prints SQL instead of executing it.

**Why it is here:** this pair of lines is the heart of every `env.py`. Wrapping the migrations in a transaction means a failed migration leaves the database untouched. PostgreSQL supports this even for `CREATE TABLE` / `ALTER TABLE` ("transactional DDL"); Alembic logs `Will assume transactional DDL.` because of that.

**If you removed or changed it:** without the `with` line the SQL would be printed without `BEGIN;`/`COMMIT;`, so a DBA running it would have no all-or-nothing guarantee. Without `run_migrations()` nothing would be printed at all.

### Block 14: defining `run_migrations_online`

```python
def run_migrations_online() -> None:
    """'Online' mode (the normal one): connect to the database and run the migrations."""
```

- `def run_migrations_online() -> None:` - same shape as Block 11: a function, no arguments, returns nothing.
- The docstring says this is the mode you use 99% of the time: a real connection, real SQL executed.

**Why it is here:** called from Block 18 whenever `--sql` is *not* given.

**If you removed or changed it:** `NameError: name 'run_migrations_online' is not defined` on line 63, which is every normal command.

### Block 15: creating the engine

```python
    # NullPool: a migration is a short one-off script, no connection pool needed.
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)
```

- The comment explains the pool choice.
- `connectable` - Alembic's traditional name for "something we can call `.connect()` on". Here it is an `Engine`.
- `create_engine(...)` - builds the Engine (Block 3). It does **not** open a connection yet; that happens in the next block.
- `settings.database_url` - the URL from `.env`, exactly the same string the application uses in `app/database/session.py`.
- `poolclass=pool.NullPool` - which pool class the Engine should use. `NullPool` is, in SQLAlchemy's own words, "a Pool which does not pool connections. Instead it literally opens and closes the underlying DB-API connection per each connection open/close." In other words: no pool at all.

**Why it is here:** the application keeps connections open and reuses them because it answers thousands of requests. A migration run is one script that opens one connection, does its work, and exits. Keeping a pool of idle connections around for that would be pointless, and `NullPool` guarantees the connection is really closed when the `with` block ends.

**If you removed or changed it:** removing `poolclass=pool.NullPool` would still work; you would just get the default `QueuePool`, which holds the connection until the process ends (a few milliseconds later). Removing the whole line gives `NameError: name 'connectable' is not defined`. A wrong URL (bad password, server down) surfaces here as `sqlalchemy.exc.OperationalError` when `.connect()` is called in the next block.

### Block 16: opening the connection and configuring

```python
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
```

- `with ... as ...:` - a context manager again (see Block 13). `connectable.connect()` opens a real database connection; `as connection` names it; when the block ends the connection is closed automatically, even on error.
- `connectable.connect()` - the Engine method that returns a `Connection`.
- `context.configure(connection=connection, target_metadata=target_metadata)` - the online version of Block 12. Instead of a `url`, Alembic receives the live `connection`, from which it learns the dialect *and* through which it will execute SQL. `target_metadata` is the same `Base.metadata`.

**Why it is here:** Alembic executes every migration statement through this single connection, so `run_migrations()` and the transaction below all happen on it.

**If you removed or changed it:** without `context.configure(...)`, `run_migrations()` raises an error saying the context is not configured. Without the `with`, the connection would stay open until garbage collection.

### Block 17: running the migrations (online)

```python
        with context.begin_transaction():
            context.run_migrations()
```

- Identical text to Block 13, but now `begin_transaction()` calls `connection.begin()` on the real connection. On success the transaction is committed when the block ends; if any migration raises an exception, it is rolled back.
- `context.run_migrations()` - reads the `alembic_version` table to find where the database is, loads the migration files from `versions/`, runs the needed `upgrade()` / `downgrade()` functions, and updates `alembic_version` (`INSERT`/`UPDATE`/`DELETE` of the one row, as seen in the captured SQL).

**Why it is here:** this is where `CREATE TABLE users (...)` and friends are actually sent to PostgreSQL.

**If you removed or changed it:** without the transaction wrapper, a migration that fails halfway (say the second `create_table` has a typo) would leave the first table created and the version table untouched; re-running would then fail with `relation "users" already exists`. With the wrapper, PostgreSQL throws everything away and you can simply fix the typo and run again.

### Block 18: choosing the mode

```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- `if` / `else` - run one branch or the other.
- `context.is_offline_mode()` - returns `True` exactly when the command was given the `--sql` flag (in the source: `return self.context_opts.get("as_sql", False)`).
- `run_migrations_offline()` / `run_migrations_online()` - call the function defined in Block 11 or Block 14.

**Why it is here:** this is the entry point of the script. Everything above only *defined* things; these four lines make something happen. Because Alembic runs the file top to bottom, this block runs last, after all imports and both function definitions exist.

**If you removed or changed it:** every command would finish instantly and silently without doing anything, because the two functions would never be called. `alembic upgrade head` would report nothing and the tables would never be created.

### Compared to your old code

Your old `alembic/env.py` was the file `alembic init` generates, with three lines added. Here are the parts that differ.

**1. How the URL reaches Alembic.** Old:

```python
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.model import Base
from app.database import Database_URL

config = context.config
config.set_main_option("sqlalchemy.url", Database_URL)
...
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
```

The old file took a detour: it *wrote* the URL into the config object (`set_main_option("sqlalchemy.url", ...)`, replacing the placeholder from `alembic.ini`), and then `engine_from_config` *read it back* from the `[alembic]` section: it takes every key that starts with `sqlalchemy.`, strips the prefix, and passes the rest to `create_engine`. So `sqlalchemy.url` became `create_engine(url=...)`. Two steps to do what one `create_engine(settings.database_url, ...)` does.

It also had a hidden trap. `set_main_option` passes the value to `configparser`, and `configparser` treats `%` as special (the same `%(name)s` interpolation from the ini section). Alembic's own docstring for `set_main_option` warns: "A raw percent sign not part of an interpolation symbol must therefore be escaped, e.g. `%%`." A password containing `%` (or one that `URL.create` escaped into `%40` for `@`) would have made the old `env.py` crash with `configparser.InterpolationSyntaxError`. The new file never puts the URL through `configparser`, so there is nothing to escape.

**2. Where `Base` and the models come from.** Old: `from app.model import Base`. Your old project had one file, `app/model.py`, with `Base` *and* all model classes in it, so importing `Base` also registered every table by accident. The new project keeps `Base` in `app/database/base.py` and the models in separate files, so the registration has to be explicit: `import app.models  # noqa: F401`. The new way is more work for one line but it makes the dependency visible, and it means `base.py` can be imported anywhere without dragging in the models.

**3. Offline mode.** Old: `url = config.get_main_option("sqlalchemy.url")` then `context.configure(url=url, ...)`. New: `context.configure(url=settings.database_url, ...)`. Same effect, one less step, and it no longer depends on the config detour from point 1.

**4. Comments.** The old file kept the template's long comments (`# add your model's MetaData object here / for 'autogenerate' support / # from myapp import mymodel ...`). They were written for a stranger; the new comments are written for you and say what *this* project does.

**5. Everything else is the same**: `fileConfig`, `target_metadata = Base.metadata`, `pool.NullPool`, the two `with` blocks, and the `is_offline_mode()` switch at the bottom. Your old file was correct in all of those.

### Key terms in this file

| Term                    | One-line meaning                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| `alembic.context`       | Proxy module through which `env.py` talks to the running Alembic; works only while Alembic runs the file. |
| `Config`                | Object holding the values of `alembic.ini`; `config.config_file_name` is the ini path.                 |
| `fileConfig`            | `logging.config` function that installs the logging setup from an INI file.                            |
| side-effect import      | An `import` kept for what happens when the module loads (here: tables registering on `Base.metadata`). |
| `# noqa: F401`          | Tells linters to ignore "imported but unused" on this line.                                            |
| `target_metadata`       | The `MetaData` describing the desired tables; used by `--autogenerate` and for the naming convention.  |
| offline mode            | `--sql` flag: print SQL, never connect.                                                                |
| online mode             | Normal run: connect and execute.                                                                       |
| `literal_binds`         | Write values into the SQL text instead of separate placeholders (needed for `.sql` files).             |
| `paramstyle`            | How placeholders are spelled; `named` = `:name`.                                                       |
| Engine                  | SQLAlchemy object that knows the URL and dialect and hands out connections.                            |
| `NullPool`              | A pool that does not pool: open on demand, close immediately.                                          |
| `with` / context manager | Block with guaranteed setup and cleanup (`__enter__` / `__exit__`), even when an error happens.         |
| transaction             | A group of statements that all succeed or are all undone; PostgreSQL supports it for DDL too.          |
| `-> None`               | Return annotation meaning "returns nothing"; not enforced by Python.                                  |
| `alembic_version`       | The one-row table Alembic keeps in your database to remember the current revision id.                  |

---

## File: alembic/script.py.mako

### What this file is for

**First, an honest finding: this file does not exist in the new project.** The folder `alembic/` contains only `README.md`, `env.py` and `versions/`. The `README.md` in that folder lists `script.py.mako` as if it were there, but it is not. I checked by listing the folder and by searching the whole project for `*.mako`.

What the file is for: when you run `alembic revision -m "..."`, Alembic has to write a brand-new Python file into `versions/`. It does not have that file's text hard-coded; it reads a **template** named `script.py.mako` from the `script_location` folder, fills in the blanks (the message, the new id, the parent id, the date, and with `--autogenerate` the `op.*` lines), and saves the result. **Mako** is the template library Alembic uses (it is installed with Alembic). A Mako template is ordinary text with `${...}` holes in it; whatever Python expression is inside the braces is evaluated and its value is pasted in.

What this means for the project today: `alembic upgrade head` and `alembic downgrade` work fine, because they only *read* the existing migration file. But creating a new migration fails. I copied `alembic.ini`, `env.py` and `versions/` into a scratch folder and ran `alembic revision -m "test"` there; it stopped with:

```
FileNotFoundError: [Errno 2] No such file or directory: '...\\alembic\\script.py.mako'
  FAILED
```

The fix is simple and safe: copy the standard template into `alembic/script.py.mako`. Your old project has exactly that file (`C:\Users\hp\Desktop\zip\alembic\script.py.mako`), and I compared it to the one shipped inside Alembic 1.20.0 (`site-packages/alembic/templates/generic/script.py.mako`): they are identical, byte for byte. After copying it in, `alembic revision -m "add phone column"` in my scratch copy produced `2026_10_06_0ee97efa85a5_add_phone_column.py`, which shows the `file_template` from `alembic.ini` at work. (I did not add the file to the project myself, because this document only explains code; it does not change it.)

Below I explain that standard template, since it is the one the project should contain. Who reads it: only Alembic's `revision` command. It imports nothing; it is a text template, not a module.

### The whole file

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
```

### Walkthrough, block by block

The task for this file is to explain it briefly, so the blocks are a little larger and focus on the `${...}` placeholders. Everything that is *not* a placeholder is copied into the new migration file exactly as written, and those lines are explained word by word in the migration section that follows (they are the same lines).

### Block 1: the docstring with four placeholders

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
```

- `"""` - becomes the opening of the migration's docstring.
- `${message}` - a Mako placeholder. `$` + `{` ... `}` means "evaluate the Python expression inside and paste the result here". `message` is the text you gave with `-m`. Example result: `create users, categories and expenses tables`.
- `Revision ID:` - literal text, copied as-is.
- `${up_revision}` - the new random 12-character id, for example `fb8fc28ab769`.
- `Revises:` - literal text.
- `${down_revision | comma,n}` - the parent id. The `|` inside a Mako placeholder applies **filters** to the value, left to right. `comma` is a small Alembic-provided filter that joins a list with commas (needed when a migration has *two* parents, which happens when two branches are merged); `n` is Mako's built-in filter meaning "do not apply the default escaping". For a first migration `down_revision` is `None`, and the `comma` filter turns that into an empty string, which is why the real file shows `Revises:` followed by nothing.
- `${create_date}` - the current date and time, for example `2026-10-05 17:28:12.663537`.
- `"""` - closes the docstring.

**Why it is here:** so every migration starts with a human-readable header. `alembic history` and your own eyes rely on it.

**If you removed or changed it:** the generated file would have no docstring. Alembic would still work, because it reads `revision` and `down_revision` from the variables below, not from the docstring. You would just lose the readable header.

### Block 2: the imports and the `imports` placeholder

```mako
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}
```

- The first three lines are literal and appear in every migration (explained in the migration section).
- `${imports if imports else ""}` - a Python **conditional expression** inside a placeholder: "if `imports` is non-empty, paste `imports`; otherwise paste an empty string". `imports` is a string that `--autogenerate` fills with extra import lines when a migration needs them, for example `from sqlalchemy.dialects import postgresql` when a PostgreSQL-only column type is used. For this project's migration it was empty, which is why there is a blank line there in the real file.

**Why it is here:** autogenerate cannot know in advance which dialect-specific types it will have to mention, so the template leaves a hole for extra imports.

**If you removed or changed it:** a migration that needed a dialect import would be generated without it and fail with `NameError` when applied. Migrations that need no extra imports would be fine.

### Block 3: the revision identifiers with `repr()`

```mako
# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}
```

- `repr(...)` - Python's built-in "representation" function. It returns a string that is **valid Python source** for the value: for the string `fb8fc28ab769` it returns `'fb8fc28ab769'` *with the quotes*; for `None` it returns `None` *without* quotes. That is exactly what is needed here, because the pasted text must be a correct Python literal. Block 1 did not use `repr` because there the values go inside a docstring, where quotes would look wrong.
- `${repr(up_revision)}` - becomes `'fb8fc28ab769'`.
- `${repr(down_revision)}` - becomes `None` for the first migration, or `'fb8fc28ab769'` for the next one (I generated a second migration in my scratch copy and it showed exactly `down_revision: Union[str, Sequence[str], None] = 'fb8fc28ab769'`).
- `${repr(branch_labels)}`, `${repr(depends_on)}` - almost always `None`.

**Why it is here:** these four variables are what Alembic actually reads from each migration module to build the chain. Everything else in the file is for humans.

**If you removed or changed it:** a generated file without `revision` would be rejected by Alembic when it scans `versions/` (`Could not determine revision id from filename ...` style errors), and every command would stop.

### Block 4: the `upgrade` function

```mako
def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}
```

- `def upgrade() -> None:` and the docstring are literal.
- `${upgrades if upgrades else "pass"}` - same conditional pattern as Block 2. With `--autogenerate`, `upgrades` is the block of `op.create_table(...)`, `op.add_column(...)` lines; it is pasted here, with Mako keeping the indentation of the placeholder for every line. Without `--autogenerate`, it is empty and the word `pass` is pasted instead, so the function is still valid Python (a function body cannot be empty).

**Why it is here:** so that a plain `alembic revision -m "..."` gives you an empty but runnable skeleton to fill in by hand, and an `--autogenerate` run gives you the detected changes.

**If you removed or changed it:** without the `else "pass"`, a hand-written migration would be generated with an empty function body, which is a `SyntaxError` the moment Alembic imports it.

### Block 5: the `downgrade` function

```mako
def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
```

- Same as Block 4, but `downgrades` holds the reverse operations (`op.drop_table(...)` etc.) that autogenerate produced.

**Why it is here:** every migration should know how to undo itself; the template makes that function always present.

**If you removed or changed it:** Alembic would fail on `alembic downgrade` with `AttributeError: module ... has no attribute 'downgrade'` (wording approximate) for files generated afterwards.

### Compared to your old code

Your old project **has** this file, at `C:\Users\hp\Desktop\zip\alembic\script.py.mako`, and it is the untouched template from `alembic init`. I compared it with Alembic 1.20.0's own copy in `site-packages`: identical. So the comparison here is one-sided: the old project is correct and the new project is missing the file. Copy the old one over (or run `alembic init` in a temporary folder and take its `script.py.mako`) and the new project is complete. No edits inside the template are needed.

### Key terms in this file

| Term              | One-line meaning                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------------------- |
| Mako              | The template library Alembic uses to write new migration files.                                   |
| template          | Text with `${...}` holes that are filled in when a file is generated.                             |
| `${expr}`         | Mako placeholder: evaluate the Python expression `expr` and paste its value.                      |
| `| comma,n`       | Mako filters applied to a value: `comma` joins a list with commas, `n` disables default escaping. |
| `repr()`          | Python built-in that returns a value as valid Python source (`'abc'` with quotes, `None` bare).   |
| `x if c else y`   | Python conditional expression: `x` when `c` is true, otherwise `y`.                               |
| `pass`            | Python statement that does nothing; used so a function body is not empty.                         |
| `up_revision`     | The new migration's id.                                                                           |
| `down_revision`   | The id of the parent migration (`None` for the first one).                                        |

---

## File: alembic/versions/2026_10_05_fb8fc28ab769_create_users_categories_and_expenses_tables.py

### What this file is for

This is the one and only migration of the project. Its `upgrade()` creates the three tables `users`, `categories` and `expenses` with every column, primary key, foreign key, unique rule, check rule and index that the models in `app/models/` describe. Its `downgrade()` removes all of that again, in the reverse order.

It was generated by `alembic revision --autogenerate` from the models, then tidied by hand: comments were added, and the file was renamed (see the `file_template` block of `alembic.ini`). The SQL it produces on PostgreSQL is shown in full after the walkthrough.

Who runs it: Alembic, through `context.run_migrations()` in `env.py`. Alembic imports the file as a module, reads `revision` and `down_revision` to place it in the chain, and calls `upgrade()` or `downgrade()`. Nothing in `app/` imports it. What it imports: `Sequence` and `Union` from `typing`, `op` from Alembic, and `sqlalchemy` under the alias `sa`.

### The whole file

```python
"""create users, categories and expenses tables

The first migration: builds the whole initial schema.

Revision ID: fb8fc28ab769
Revises:
Create Date: 2026-10-05 17:28:12.663537

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb8fc28ab769'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # users: accounts that can log in. Created first because the other
    # two tables point at it with foreign keys.
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    )
    # Unique index: no two accounts with the same email, and fast login lookups.
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # categories: each user's own labels (Food, Rent...).
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Deleting a user deletes their categories.
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_categories_owner_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
        # A user cannot have two categories with the same name.
        sa.UniqueConstraint('owner_id', 'name', name='uq_categories_owner_id_name'),
    )
    op.create_index(op.f('ix_categories_owner_id'), 'categories', ['owner_id'], unique=False)

    # expenses: one row for each time a user spent money.
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('amount > 0', name=op.f('ck_expenses_amount_positive')),
        # Deleting a category keeps its expenses as "uncategorized".
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_expenses_category_id_categories'), ondelete='SET NULL'),
        # Deleting a user deletes their expenses.
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_expenses_owner_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_expenses')),
    )
    op.create_index(op.f('ix_expenses_category_id'), 'expenses', ['category_id'], unique=False)
    # Speeds up "this user's expenses in a date range" (lists and reports).
    op.create_index('ix_expenses_owner_id_expense_date', 'expenses', ['owner_id', 'expense_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse order of upgrade(): tables with foreign keys are dropped first.
    op.drop_index('ix_expenses_owner_id_expense_date', table_name='expenses')
    op.drop_index(op.f('ix_expenses_category_id'), table_name='expenses')
    op.drop_table('expenses')
    op.drop_index(op.f('ix_categories_owner_id'), table_name='categories')
    op.drop_table('categories')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
```

### Walkthrough, block by block

### Block 1: the docstring

```python
"""create users, categories and expenses tables

The first migration: builds the whole initial schema.

Revision ID: fb8fc28ab769
Revises:
Create Date: 2026-10-05 17:28:12.663537

"""
```

- `"""` ... `"""` - the module docstring, filled in from the Mako template (Block 1 of the template section).
- `create users, categories and expenses tables` - the `-m` message that was given when the file was generated. It is also what `alembic history` prints next to the id.
- `The first migration: builds the whole initial schema.` - a line added by hand after generation. "Schema" means the structure of the database: all its tables, columns and rules.
- `Revision ID: fb8fc28ab769` - this file's id, repeated for humans. The value Alembic actually uses is the `revision` variable below.
- `Revises:` - empty. It would hold the parent's id. Empty means "this is the first migration; there is nothing before it".
- `Create Date: 2026-10-05 17:28:12.663537` - when the file was generated (local time, with microseconds).

**Why it is here:** the header makes a migration self-describing. When you have twenty of them, the first line of each file is what tells them apart.

**If you removed or changed it:** nothing functional changes; Alembic reads the variables, not the docstring. But `alembic history` would show the message from the docstring's first line as empty, and you would have to open each file to know what it does.

### Block 2: importing `Sequence` and `Union`

```python
from typing import Sequence, Union
```

- `typing` - Python's built-in module for **type hints**: notes that say what kind of value a variable holds. Python does not enforce them; editors and type checkers use them.
- `Sequence` - a hint meaning "an ordered collection you can index and loop over", like a list or a tuple. `Sequence[str]` means "a sequence of strings".
- `Union` - a hint meaning "one of several types". `Union[str, Sequence[str], None]` means "either a string, or a sequence of strings, or `None`". In modern Python you could write the same as `str | Sequence[str] | None`; Alembic's template uses the older `Union` spelling so that it also works on older Python versions.

**Why it is here:** the four revision variables below are annotated with these hints (Block 6 and 7). Why would `down_revision` ever be a *sequence*? Because Alembic supports **merge migrations**: when two developers each created a migration from the same parent, a merge migration has *two* parents, and `down_revision` becomes a tuple of two ids.

**If you removed or changed it:** `NameError: name 'Union' is not defined` the moment Alembic imports the file, which means every command that scans `versions/` fails.

### Block 3: importing `op`

```python
from alembic import op
```

- `op` - short for "operations". `alembic.op` is a module of functions that each stand for one schema change: `create_table`, `drop_table`, `add_column`, `create_index`, `create_foreign_key`, and so on. Like `alembic.context` in `env.py`, it is a **proxy**: it only works while Alembic is running a migration. I tried calling `op.f("x")` from a plain Python script and got `NameError: Can't invoke function 'f', as the proxy object has not yet been established for the Alembic 'Operations' class.`

**Why it is here:** every statement in `upgrade()` and `downgrade()` starts with `op.`.

**If you removed or changed it:** `NameError: name 'op' is not defined` when `upgrade()` runs.

### Block 4: importing SQLAlchemy as `sa`

```python
import sqlalchemy as sa
```

- `import sqlalchemy` - load the SQLAlchemy library.
- `as sa` - give it the short alias `sa` in this file, so that `sa.Column`, `sa.Integer`, `sa.String` are easy to type. It is the same library; `sa.Column` is `sqlalchemy.Column`.

**Why it is here:** `op.create_table` needs the column and constraint objects, and those come from SQLAlchemy. The `sa` alias is Alembic's convention and autogenerate writes code with it.

**If you removed or changed it:** `NameError: name 'sa' is not defined` at the first `sa.Column`.

### Block 5: `revision`

```python
# revision identifiers, used by Alembic.
revision: str = 'fb8fc28ab769'
```

- The comment says these variables are for Alembic, not for you.
- `revision` - the variable name Alembic looks for.
- `: str` - a type hint: this variable holds a string. The colon separates the name from the hint.
- `=` - assignment.
- `'fb8fc28ab769'` - the id: 12 random hexadecimal characters (digits `0-9` and letters `a-f`), generated by Alembic when the file was created. It is unique within the project. The file name contains the same id so you can find the file from the id.

**Why it is here:** this id is what gets stored in the `alembic_version` table once the migration has run (`INSERT INTO alembic_version (version_num) VALUES ('fb8fc28ab769')` in the captured SQL). It is how Alembic knows this migration is done.

**If you removed or changed it:** removing it makes Alembic reject the file when scanning `versions/`. Changing the id *after* it has been applied somewhere would make that database's `alembic_version` point at an id that no longer exists, and the next command fails with `Can't locate revision identified by 'fb8fc28ab769'`.

### Block 6: `down_revision`

```python
down_revision: Union[str, Sequence[str], None] = None
```

- `down_revision` - the id of the **parent** migration: the one that must be applied before this one.
- `: Union[str, Sequence[str], None]` - type hint from Block 2: a string (one parent), a sequence (several parents, merge case), or `None`.
- `= None` - no parent. This is the first migration, the "base".

**Why it is here:** the chain of `down_revision` values is the whole ordering system of Alembic. `upgrade head` follows the chain forward from `None`; `downgrade` follows it backward.

**If you removed or changed it:** if a second migration pointed here and you changed this to some other id, Alembic would report a broken chain (`Revision ... referenced from ... is not present`). With only one migration, setting it to a nonsense string gives that same error immediately.

### Block 7: `branch_labels` and `depends_on`

```python
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

- `branch_labels` - optional names for a **branch** of the migration chain. Used in large projects that keep several independent chains (for example one per plugin). `None` = no label.
- `depends_on` - optional ids of migrations in *other* branches that must be applied first, without being this migration's parent. `None` = no such dependency.
- Both carry the same type hint as `down_revision`.

**Why it is here:** the template always writes them, so that every migration file has the same shape. This project has a single straight chain and never sets them.

**If you removed or changed it:** removing them is harmless (Alembic treats a missing attribute as `None`). Setting `depends_on` to an id that does not exist breaks the chain like a bad `down_revision`.

### Block 8: the `upgrade` function and the `users` comment

```python
def upgrade() -> None:
    """Upgrade schema."""
    # users: accounts that can log in. Created first because the other
    # two tables point at it with foreign keys.
```

- `def upgrade() -> None:` - the function Alembic calls to apply this migration. No arguments; returns nothing. The name `upgrade` is fixed; Alembic looks for exactly that.
- `"""Upgrade schema."""` - a one-line docstring from the template.
- The two comment lines explain the order of the tables: `users` has to exist before `categories` and `expenses`, because those two will declare foreign keys pointing at `users.id`, and PostgreSQL refuses a foreign key to a table that does not exist yet.

**Why it is here:** Alembic's whole contract with a migration file is "give me an `upgrade()` and a `downgrade()`".

**If you removed or changed it:** renaming the function to anything else makes `alembic upgrade head` fail with `AttributeError: module '...' has no attribute 'upgrade'` (wording approximate; the point is Alembic looks the name up on the module).

### Block 9: starting the `users` table

```python
    op.create_table(
        'users',
```

- `op.create_table(` - the Alembic operation that issues `CREATE TABLE`. Its signature is `create_table(table_name, *columns, **kw)`: the first argument is the name, and every following positional argument is a column or a constraint object.
- `'users',` - the table name. Plural, lower case, matching `__tablename__ = "users"` in `app/models/user.py`.

**Why it is here:** this starts the SQL `CREATE TABLE users (`.

**If you removed or changed it:** change the name to `'user'` and the migration still runs (SQLAlchemy would quote it as `"user"`, since `user` is a reserved word in PostgreSQL), but the model says `users`, so every query the app sends would fail with `relation "users" does not exist`.

### Block 10: the `id` column

```python
        sa.Column('id', sa.Integer(), nullable=False),
```

- `sa.Column(` - describes one column. The first two arguments are always *name* and *type*; the rest are keyword options.
- `'id'` - the column name.
- `sa.Integer()` - the type: a whole number. The parentheses create an instance of the type class (SQLAlchemy accepts the bare class too, but autogenerate always writes the call form). On PostgreSQL, because this column is also the primary key (Block 14), SQLAlchemy renders it as `SERIAL`: an integer that the database fills in automatically with 1, 2, 3, ... (you can see `id SERIAL NOT NULL` in the captured SQL).
- `nullable=False` - `NOT NULL`: the column must always have a value. `nullable` is the keyword, `False` is Python's "no".

**Why it is here:** every table needs a primary key; an auto-incrementing integer is the simplest.

**If you removed or changed it:** without the column, the `PrimaryKeyConstraint('id', ...)` below would fail because it names a column that does not exist (`KeyError`/`ArgumentError` from SQLAlchemy while building the table). With `nullable=True` PostgreSQL would still force `NOT NULL` because it is a primary key.

### Block 11: `email`, `full_name`, `hashed_password`

```python
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
```

- `sa.String(length=255)` - a text column with a maximum length. On PostgreSQL this is `VARCHAR(255)` ("varying characters, up to 255"). `length` is the keyword argument name; autogenerate writes it explicitly.
- `'email'` ... `255` - 255 is a common upper bound for email addresses.
- `'full_name'` ... `100` - a display name; 100 characters is plenty.
- `'hashed_password'` ... `255` - stores the **hash** of the password, never the password. The name says so, which prevents the mistake of ever writing a plain password here. Argon2 hashes (the algorithm used in `app/core/security.py`) are under 255 characters.
- `nullable=False` on all three - every account must have all three values.

**Why it is here:** these are the three pieces of information the `User` model declares (`String(255)`, `String(100)`, `String(255)` in `app/models/user.py`). The lengths match the limits that the Pydantic schemas enforce on input, so the database can never receive a value longer than it can store.

**If you removed or changed it:** removing any of them makes the app's first `INSERT INTO users` fail with `psycopg2.errors.UndefinedColumn: column "full_name" of relation "users" does not exist`. Making a length shorter than the schema allows would give `psycopg2.errors.StringDataRightTruncation: value too long for type character varying(50)` on long input.

### Block 12: `is_active`

```python
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
```

- `sa.Boolean()` - a true/false column; `BOOLEAN` on PostgreSQL.
- `server_default=sa.true()` - a **server default**: a default value that the *database itself* applies when an `INSERT` does not mention the column. ("Server" here means the database server, as opposed to a Python-side default.) `sa.true()` is SQLAlchemy's portable way to write the SQL constant true; it renders as `true` on PostgreSQL and as `1` on SQLite (I compiled both). The captured SQL shows `is_active BOOLEAN DEFAULT true NOT NULL`.
- `nullable=False` - never NULL; thanks to the default, an insert that omits the column still satisfies this.

**Why it is here:** it lets an admin block an account (set `is_active = false`) without deleting the user's data. New accounts are active by default.

**If you removed or changed it:** without `server_default`, any `INSERT` that does not supply `is_active` fails with `psycopg2.errors.NotNullViolation: null value in column "is_active" ... violates not-null constraint` (the model also has a Python-side `default=True`, so the app's own inserts would still work; raw SQL inserts would not).

### Block 13: `created_at`

```python
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
```

- `sa.DateTime(timezone=True)` - a date-and-time column that **stores the time zone**. On PostgreSQL this is `TIMESTAMP WITH TIME ZONE` (`DateTime()` without the flag would be `TIMESTAMP WITHOUT TIME ZONE`; I compiled both). With the zone stored, a value written by a server in India and read in Germany still means the same instant.
- `server_default=sa.func.now()` - the database fills in the current time on insert. `sa.func` is a special object: `sa.func.<anything>(...)` produces a call to the SQL function of that name. `sa.func.now()` renders as `now()` on PostgreSQL. SQLAlchemy also *knows* this particular function, so on other databases it renders the right spelling (`CURRENT_TIMESTAMP` on SQLite; I checked). The captured SQL shows `created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL`.
- `nullable=False` - always present, guaranteed by the default.

**Why it is here:** a creation timestamp on every table is almost free and very useful (sorting, auditing, "member since").

**If you removed or changed it:** without the default, inserts that omit `created_at` fail with a not-null violation. Using `sa.DateTime()` without `timezone=True` would store "naive" times that silently lose their zone.

### Block 14: the primary key and the closing parenthesis

```python
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    )
```

- `sa.PrimaryKeyConstraint(` - declares the primary key: the column (or columns) that uniquely identify a row. The database also builds an index for it automatically.
- `'id'` - the column that is the key.
- `name=op.f('pk_users')` - the constraint's name in the database. In the captured SQL: `CONSTRAINT pk_users PRIMARY KEY (id)`.
- `op.f(...)` - explained fully in the next paragraph.
- `)` - closes the `op.create_table(` call that started in Block 9. At this point Alembic sends the complete `CREATE TABLE users (...)` statement.

**What `op.f()` is and why it exists.** `op.f(name)` returns the same string wrapped in a tiny marker class, `sqlalchemy.sql.elements.conv` (a subclass of `str`), that means: "this name is **final**; a naming convention has already been applied to it, do not apply it again." Here is why that matters. `app/database/base.py` gives `Base.metadata` a naming convention, for example `"ck": "ck_%(table_name)s_%(constraint_name)s"`. When `env.py` passes `Base.metadata` as `target_metadata`, Alembic copies that convention into the temporary `MetaData` it uses inside `op.create_table` (I verified this in `alembic/operations/schemaobj.py`). Now look at the check constraint in Block 26: the model names it `"amount_positive"`, and the convention turns that into `ck_expenses_amount_positive`. Autogenerate writes that *final* name into the migration. If the migration then passed it back as a plain string, the convention, which contains the `%(constraint_name)s` token, would run **again** on it and produce `ck_expenses_ck_expenses_amount_positive`. I reproduced this exact doubled name with a plain string, and the correct `ck_expenses_amount_positive` with `conv(...)`. `op.f()` is what stops the doubling. For `pk`, `fk`, `uq` and `ix` the project's conventions have no `%(constraint_name)s` token, so a plain string would survive unchanged, but autogenerate wraps every convention-made name in `op.f()` regardless, so the file is consistent and safe. Names that a model gave *by hand* (`uq_categories_owner_id_name` in Block 19, `ix_expenses_owner_id_expense_date` in Block 31) are written as plain strings, because the convention never produced them.

**Why it is here:** an explicit, predictable constraint name. Without a name PostgreSQL would invent `users_pkey`; with the convention it is `pk_users`, and any later migration that needs to drop or alter it can refer to it with confidence.

**If you removed or changed it:** without the `PrimaryKeyConstraint`, the table would have no primary key and `id` would be a plain `INTEGER` (no `SERIAL`), so every insert would have to supply an id; the app does not, so inserts would fail with a not-null violation. Without `op.f()` around `'pk_users'` nothing would change here (no `constraint_name` token in the `pk` convention), but the file would no longer match what autogenerate writes.

### Block 15: the unique index on `email`

```python
    # Unique index: no two accounts with the same email, and fast login lookups.
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
```

- The comment gives the two reasons for the index.
- `op.create_index(` - the operation that issues `CREATE INDEX`. Signature: `create_index(index_name, table_name, columns, *, unique=False, ...)`.
- `op.f('ix_users_email')` - the index name, final (see Block 14). It comes from the convention `"ix": "ix_%(column_0_label)s"`; `column_0_label` is the first column's *label*, which SQLAlchemy builds as `tablename_columnname`, hence `users_email`.
- `'users'` - the table.
- `['email']` - a Python list of column names to index. A list because an index can cover several columns (Block 31 does that).
- `unique=True` - make it a **unique** index: the database refuses a second row with the same email. In the captured SQL: `CREATE UNIQUE INDEX ix_users_email ON users (email)`.

**Why it is here:** the model declares `email: Mapped[str] = mapped_column(String(255), unique=True, index=True)`. Those two flags together become one unique index. Login looks users up by email on every request, so the index makes that fast, and uniqueness is what makes email usable as the login name at all.

**If you removed or changed it:** two users could register with the same email, and the login code, which expects at most one match, would behave unpredictably. Lookups would also scan the whole table. The `POST /api/v1/auth/register` endpoint relies on the database raising `psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "ix_users_email"` to detect duplicates (the router also checks first, but the index is the guarantee under concurrent requests).

### Block 16: starting the `categories` table with its first columns

```python
    # categories: each user's own labels (Food, Rent...).
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
```

- The comment says what a category is.
- `op.create_table('categories',` - second table.
- `sa.Column('id', sa.Integer(), nullable=False)` - same auto-increment id pattern as Block 10.
- `sa.Column('name', sa.String(length=50), nullable=False)` - the label, up to 50 characters, required.
- `sa.Column('description', sa.String(length=255), nullable=True)` - an optional longer text. `nullable=True` means NULL is allowed, so the captured SQL has just `description VARCHAR(255)` with no `NOT NULL`. This matches `Mapped[str | None]` in the model.

**Why it is here:** categories are per-user labels for expenses; the user picks the name, the description is optional.

**If you removed or changed it:** removing `description` makes `POST /api/v1/categories` fail at insert time with `UndefinedColumn`. Changing `nullable=True` to `False` would make every category without a description fail with a not-null violation.

### Block 17: `owner_id` and `created_at` in `categories`

```python
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
```

- `sa.Column('owner_id', sa.Integer(), nullable=False)` - an integer that will hold a `users.id`. Note that the *column* is declared here as a plain integer; the fact that it points at another table is declared separately by the `ForeignKeyConstraint` in the next block. Required: every category belongs to someone.
- `created_at` - identical to Block 13.

**Why it is here:** `owner_id` is how the app knows whose category this is; every query in `app/routers/categories.py` filters on it.

**If you removed or changed it:** without `owner_id` the foreign key below fails to build, and the app could not tell users' categories apart.

### Block 18: the foreign key to `users`

```python
        # Deleting a user deletes their categories.
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_categories_owner_id_users'), ondelete='CASCADE'),
```

- The comment states the delete rule in plain words.
- `sa.ForeignKeyConstraint(` - declares a **foreign key**: a rule that the value in this table's column must exist in another table's column.
- `['owner_id']` - list of local columns (a list because a foreign key may span several columns).
- `['users.id']` - list of target columns, written as `table.column`.
- `name=op.f('fk_categories_owner_id_users')` - final name from the convention `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`.
- `ondelete='CASCADE'` - what the database does when the *referenced* row (the user) is deleted. `CASCADE` = delete the referencing rows too. The other possible values are `'SET NULL'` (used in Block 27), `'RESTRICT'` and `'NO ACTION'` (refuse the delete while references exist; `NO ACTION` is the default) and `'SET DEFAULT'`.

In the captured SQL: `CONSTRAINT fk_categories_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE`.

**Why it is here:** it makes an orphan category impossible: `owner_id` must be a real user, and when the user goes, their categories go with them, inside the database, in one statement. The `User` model's `relationship(..., passive_deletes=True)` relies on exactly this rule instead of deleting rows one by one from Python.

**If you removed or changed it:** without the constraint you could insert a category with `owner_id = 999` for a user that does not exist, and deleting a user would leave its categories behind as garbage. With `ondelete='RESTRICT'`, `DELETE /api/v1/users/me` would fail with `psycopg2.errors.ForeignKeyViolation` as soon as the user has one category.

### Block 19: the primary key, the unique rule, and the closing parenthesis

```python
        sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
        # A user cannot have two categories with the same name.
        sa.UniqueConstraint('owner_id', 'name', name='uq_categories_owner_id_name'),
    )
```

- `sa.PrimaryKeyConstraint('id', name=op.f('pk_categories'))` - same as Block 14 for this table.
- The comment states the business rule.
- `sa.UniqueConstraint(` - a rule that a *combination* of columns must be unique across the table.
- `'owner_id', 'name'` - the two columns, passed as separate arguments. Unique *together*: user 1 can have "Food" and user 2 can have "Food", but user 1 cannot have "Food" twice.
- `name='uq_categories_owner_id_name'` - a plain string, **not** `op.f()`. The model wrote this name by hand (`UniqueConstraint("owner_id", "name", name="uq_categories_owner_id_name")` in `app/models/category.py`), because the convention `uq_%(table_name)s_%(column_0_name)s` would only have produced `uq_categories_owner_id` (I checked), which does not mention `name` and would be confusing. Since the `uq` convention has no `%(constraint_name)s` token, a plain string passes through untouched, so `op.f()` is not needed.
- `)` - closes `op.create_table('categories', ...)`.

In the captured SQL: `CONSTRAINT uq_categories_owner_id_name UNIQUE (owner_id, name)`.

**Why it is here:** the API returns `409 Conflict` when you create a category whose name you already use. The router checks first, but this constraint is the real guarantee, including when two requests race.

**If you removed or changed it:** duplicates would be possible, and the "find my category called Food" logic in the router could return two rows. If you wrote `UniqueConstraint('name', ...)` alone, two different users could not both have "Food", which is wrong for a multi-user app.

### Block 20: the index on `categories.owner_id`

```python
    op.create_index(op.f('ix_categories_owner_id'), 'categories', ['owner_id'], unique=False)
```

- Same shape as Block 15, with `unique=False` (autogenerate always writes the flag). Name from the convention: `ix_` + label `categories_owner_id`. The model asked for it with `index=True` on `owner_id`.

In the captured SQL: `CREATE INDEX ix_categories_owner_id ON categories (owner_id)`.

**Why it is here:** `GET /api/v1/categories` is always "all categories where owner_id = me". With the index PostgreSQL jumps straight to those rows instead of scanning the whole table. (PostgreSQL does not index foreign-key columns automatically; that is a common surprise.)

**If you removed or changed it:** everything would still work, just slower as the table grows. Note that the unique constraint from Block 19 already creates an index on `(owner_id, name)` whose first column is `owner_id`, so PostgreSQL could use that one too; the explicit index is simpler and matches the model.

<!-- CONTINUE -->
