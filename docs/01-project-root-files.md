# Project root files

The "project root" is the top folder, `expense-tracker-backend/`. The files that
live there are not Python code. They are small text files that tell **other
tools** (pip, git, the settings loader) how to treat the project. This document
explains four of them, word by word:

| File                   | Who reads it                            | Job                                                   |
| ---------------------- | --------------------------------------- | ----------------------------------------------------- |
| `requirements.txt`     | `pip`                                   | The libraries the app needs to run, with exact versions |
| `requirements-dev.txt` | `pip`                                   | The same list plus the two libraries only the tests need |
| `.env.example`         | you (copy it to `.env`), then `app/core/config.py` | Template for the secret settings: database, JWT, CORS |
| `.gitignore`           | `git`                                   | Files that must never be committed (`.env`, caches, venv) |

Two other root files are mentioned here only once each, as the reader asked:

- `README.md` is the human-facing front page of the project: what it is, the tech
  stack, the folder layout, how to set it up and the list of endpoints.
- `pytest.ini` tells the `pytest` tool where the tests live (`tests/`) and hides
  one SQLite-related warning; the tests themselves are not covered in these docs.

A quick word on the format of this document. Every file is shown in full first,
then cut into small blocks. For every block there is one bullet per word or
name, then **Why it is here** and **If you removed or changed it**. Where I
needed to be sure about a library's behaviour I opened the library's own source
code in the virtual environment or ran a tiny Python snippet; I say so when I do.

---

## File: requirements.txt

### What this file is for

`requirements.txt` is the shopping list for `pip`, Python's package installer.
Each line names one library and the exact version to install. When somebody
(you, a teammate, a hosting server) runs `pip install -r requirements.txt`,
pip downloads these ten libraries plus everything *they* depend on. Without
this file, a fresh computer would have no FastAPI, no SQLAlchemy, and
`from fastapi import FastAPI` in `app/main.py` would fail with
`ModuleNotFoundError: No module named 'fastapi'`.

Nothing in the Python code imports this file. It is read by **pip** only. It is
*included* by `requirements-dev.txt` (explained next), so you never have to
install the two lists separately.

I checked the virtual environment with `pip list`: every version written here is
exactly the version that is installed, so the pins match reality.

### The whole file

```text
# Runtime dependencies for the Expense Tracker API.
# Install with:  pip install -r requirements.txt

# Web framework and ASGI server
fastapi==0.141.1
uvicorn==0.53.0

# Database: ORM, migrations and the PostgreSQL driver
SQLAlchemy==2.0.54
alembic==1.20.0
psycopg2-binary==2.9.13

# Settings loaded from environment variables / .env
pydantic-settings==2.15.0

# Authentication: JWT tokens and password hashing
python-jose[cryptography]==3.5.0
pwdlib[argon2,bcrypt]==0.3.1

# Request validation helpers (EmailStr and the OAuth2 login form)
email-validator==2.3.0
python-multipart==0.0.32
```

### Walkthrough, block by block

Before the blocks, the three pieces of syntax that appear on every line:

- `name==1.2.3` means "install exactly version 1.2.3 of the library called
  `name`". The two equals signs are pip's way of saying *exactly this one*.
  Other forms exist (`>=` "at least", `~=` "compatible with"), but this project
  uses only `==`.
- A version number like `0.141.1` has three parts: **major.minor.patch**.
  Libraries usually change the first number for big breaking changes, the
  middle number for new features, and the last number for bug fixes. This is a
  convention (called "semantic versioning"), not a law; libraries with a `0.`
  major number, like FastAPI and uvicorn, sometimes make breaking changes in a
  minor release.
- `name[extra]` means "also install the optional add-on called `extra`". More on
  this when we reach `python-jose[cryptography]`.

### Block 1: the header comments

```text
# Runtime dependencies for the Expense Tracker API.
# Install with:  pip install -r requirements.txt
```

- `#` - in a requirements file, as in Python, everything after `#` on a line is
  a comment. pip ignores it. Comments are for the human reading the file.
- `Runtime dependencies` - "runtime" means *while the app is running*. These are
  the libraries the API itself needs. Libraries used only to test the code are
  kept out of this file (they go in `requirements-dev.txt`).
- `Expense Tracker API` - the name of this project, the same name that
  `APP_NAME` in `app/core/config.py` holds.
- `pip install -r requirements.txt` - the command this file is written for.
  `pip` is the installer, `install` is the sub-command, `-r` means "read the
  list of packages from the file that follows" (`r` for *requirements*).

**Why it is here.** The two comment lines are documentation: someone who opens
the file knows what it is and how to use it without reading the README.

**If you removed or changed it.** Nothing would break; pip skips comments. The
file would just be less friendly.

### Block 2: web framework and server

```text
# Web framework and ASGI server
fastapi==0.141.1
uvicorn==0.53.0
```

- `# Web framework and ASGI server` - a comment that labels the group. A *web
  framework* is a library that turns a Python function into an HTTP endpoint.
  *ASGI* is explained three bullets down.
- `fastapi` - the name of the library on PyPI (the public package index pip
  downloads from). This is the framework the whole project is built on. Inside
  this project it provides:
  - `FastAPI` (the app object) in `app/main.py`;
  - `APIRouter`, `Depends`, `HTTPException`, `Query`, `Response`, `status` in
    every file under `app/routers/` and in `app/core/dependencies.py`;
  - `fastapi.security.OAuth2PasswordBearer` (reads the `Authorization: Bearer`
    header) in `app/core/dependencies.py` and `OAuth2PasswordRequestForm` (reads
    the login form) in `app/routers/auth.py`;
  - `fastapi.middleware.cors.CORSMiddleware` in `app/main.py`.
- `==0.141.1` - install exactly that version.
- `uvicorn` - the **server program**. FastAPI alone cannot listen on a network
  port; it only knows how to answer a request once it has one. Uvicorn is the
  program that opens the port, reads the raw bytes from the browser, turns them
  into a request, hands the request to the FastAPI app, and sends the answer
  back. It is never imported in the code; it is started from the command line
  (the README shows the command).
- `ASGI` - *Asynchronous Server Gateway Interface*. It is the agreed "contract"
  between a Python server (uvicorn) and a Python web app (FastAPI). Because both
  follow the same contract, any ASGI server can run any ASGI app. "Asynchronous"
  means it can handle many connections at the same time without one blocking
  the others.
- `==0.53.0` - exact version of uvicorn.

Two libraries you use every day are **not** in this file, on purpose:
**pydantic** (the `BaseModel`, `EmailStr`, `Field`, `ConfigDict`,
`model_validator` you import in `app/schemas/`) and **starlette** (the engine
under FastAPI that does the HTTP work, the CORS middleware and the test client).
I opened FastAPI's package metadata in the venv: FastAPI declares
`pydantic>=2.9.0` and `starlette>=0.46.0` as its own dependencies, so pip
installs them automatically when it installs FastAPI. In this venv that gave
pydantic 2.13.5 and starlette 1.7.0. These are called **transitive
dependencies**: you did not ask for them, they came along with something you
asked for.

**Why it is here.** Without `fastapi` there is no app. Without `uvicorn` there
is no way to serve it over HTTP.

**If you removed or changed it.** Remove `fastapi` and every file under `app/`
fails at the first `from fastapi import ...` line with
`ModuleNotFoundError: No module named 'fastapi'`. Remove `uvicorn` and the code
still imports fine, but the server command does not exist
(`'uvicorn' is not recognized...` on Windows). Change the pinned version of
FastAPI and you may get a different pydantic/starlette along with it, which can
change validation messages or break an import; this is exactly why the version
is pinned (see "Why the versions are pinned" below).

### Block 3: database libraries

```text
# Database: ORM, migrations and the PostgreSQL driver
SQLAlchemy==2.0.54
alembic==1.20.0
psycopg2-binary==2.9.13
```

- `# Database: ORM, migrations and the PostgreSQL driver` - comment labelling
  the three database libraries. Each of the three words is explained below.
- `SQLAlchemy` - the **ORM**. ORM stands for *Object Relational Mapper*: it
  lets you describe a table as a Python class and a row as a Python object, and
  it writes the SQL for you. In this project SQLAlchemy is used in:
  - `app/database/base.py` (`DeclarativeBase`, `MetaData` - the parent class of
    every model);
  - `app/database/session.py` (`create_engine`, `sessionmaker`, `Session`,
    `text` - the connection pool and the per-request session);
  - `app/models/*.py` (`Mapped`, `mapped_column`, `relationship`, `String`,
    `DateTime`, `ForeignKey`, `UniqueConstraint`, `func` - the table
    definitions);
  - `app/routers/*.py` (`select`, `func`, `extract`, `selectinload` - the
    queries);
  - `app/core/config.py` (`sqlalchemy.engine.URL` - building the connection
    string safely);
  - `alembic/env.py` (`create_engine`, `pool`).
- `==2.0.54` - exact version. The `2.0` matters a lot: SQLAlchemy 2.0 introduced
  the "2.0 style" API (`Mapped[...]`, `mapped_column(...)`, `select(...)`,
  `db.scalars(...)`). The whole project is written in that style. SQLAlchemy
  1.4 would not understand `DeclarativeBase` and `Mapped` the same way, and
  many lines would fail.
- `alembic` - the **migration** tool, made by the same people as SQLAlchemy. A
  *migration* is a small, numbered Python script that changes the database
  structure (create a table, add a column...) in a way you can apply, undo and
  commit to git. Alembic reads `alembic.ini`, runs `alembic/env.py`, and runs
  the scripts in `alembic/versions/`. Its own metadata says it needs
  `SQLAlchemy>=2.0` and `Mako` (a template engine it uses to generate new
  migration files), so those come along automatically.
- `==1.20.0` - exact version.
- `psycopg2-binary` - the **driver**. SQLAlchemy knows how to *write* SQL for
  PostgreSQL, but it does not know how to *talk* to a PostgreSQL server over the
  network. That is the driver's job. The Python module it installs is called
  `psycopg2` (without `-binary`). The project never imports it directly; it is
  chosen through the driver name `"postgresql+psycopg2"` that
  `app/core/config.py` puts in the connection URL. SQLAlchemy then imports
  `psycopg2` for you.
- `-binary` - the suffix means "pre-built package". The plain `psycopg2` package
  has to be compiled on your machine and needs a C compiler and the PostgreSQL
  development files, which is painful on Windows. The `-binary` package ships
  already compiled, together with the PostgreSQL client library it needs.
- `==2.9.13` - exact version.

**Why it is here.** This is the complete chain from Python to PostgreSQL:
SQLAlchemy (write SQL, map rows to objects) -> psycopg2 (send it over the
network) -> PostgreSQL. Alembic is there so that the tables are created and
changed by versioned scripts instead of `Base.metadata.create_all()`.

**If you removed or changed it.** Remove `SQLAlchemy`: `app/database/base.py`
fails at `from sqlalchemy import MetaData`, and because almost every file
imports a model or a session, nothing starts. Remove `psycopg2-binary`: the
import works, but the moment `create_engine(settings.database_url)` runs in
`app/database/session.py` (which happens on import), SQLAlchemy raises
`ModuleNotFoundError: No module named 'psycopg2'`. Remove `alembic`: the app
runs, but `alembic upgrade head` does not exist, so you have no way to create
the tables; every endpoint that touches the database would fail with a
PostgreSQL "relation does not exist" error. Downgrade SQLAlchemy to 1.x: the 2.0
style imports (`DeclarativeBase`, `Mapped`) raise `ImportError`.

### Block 4: settings loader

```text
# Settings loaded from environment variables / .env
pydantic-settings==2.15.0
```

- `# Settings loaded from environment variables / .env` - comment. An
  *environment variable* is a named value that lives in the operating system
  (like `PATH`); a `.env` file is a text file with `NAME=value` lines that
  pretends to be environment variables. Both are explained fully in the
  `.env.example` section.
- `pydantic-settings` - a small add-on for pydantic. It gives you the
  `BaseSettings` class and `SettingsConfigDict`, which `app/core/config.py`
  uses to turn environment variables and the `.env` file into one typed
  `settings` object. That is the **only** file in the project that imports it;
  every other file gets its values through `from app.core.config import settings`.
  I opened its package metadata: it depends on `pydantic` and on
  `python-dotenv`, the library that actually parses the `.env` file. So
  `python-dotenv` is installed too, without being listed here.
- `==2.15.0` - exact version.

**Why it is here.** It is the bridge between `.env` and the code. Without it the
database password and the JWT secret would have to be typed into Python files,
and those files would end up in git.

**If you removed or changed it.** `app/core/config.py` fails at
`from pydantic_settings import BaseSettings, SettingsConfigDict` with
`ModuleNotFoundError`, and since `main.py`, `session.py`, `security.py`,
`dependencies.py` and `alembic/env.py` all import `settings`, nothing at all
starts, not even Alembic.

### Block 5: authentication libraries

```text
# Authentication: JWT tokens and password hashing
python-jose[cryptography]==3.5.0
pwdlib[argon2,bcrypt]==0.3.1
```

- `# Authentication: JWT tokens and password hashing` - comment. *JWT* and
  *hashing* are explained in the next bullets.
- `python-jose` - the library that creates and checks **JWT**s. JWT means *JSON
  Web Token*. It is a string with three parts separated by dots
  (`header.payload.signature`). The payload holds small facts, called *claims*,
  such as "user id 7" and "expires at 14:30". The signature is computed from the
  payload plus your `SECRET_KEY`, so if anyone edits the payload the signature
  no longer matches and the server rejects the token. The PyPI name is
  `python-jose` but the module you import is `jose`:
  `app/core/security.py` does `from jose import JWTError, jwt` and calls
  `jwt.encode(...)` in `create_access_token` and `jwt.decode(...)` in
  `decode_access_token`. No other file uses it.
- `[cryptography]` - an **extra**. Square brackets after a package name list
  optional add-ons the package author defined. An extra is just "also install
  these other packages". For python-jose, the `cryptography` extra installs the
  `cryptography` library, which is the standard, well-maintained Python crypto
  library. I opened `jose/backends/__init__.py` in the venv: when
  `cryptography` is importable, jose uses it for signing (`CryptographyHMACKey`
  for the `HS256` algorithm this project uses); when it is not, jose falls
  back to its own pure-Python code for HS256. So the app would still work
  without the extra for HS256, but the extra gives the maintained backend and
  it would be *required* if you ever switched `ALGORITHM` to an RSA or EC
  algorithm such as `RS256`.
- `==3.5.0` - exact version.
- `pwdlib` - the **password hashing** library. *Hashing* turns a password into
  a long scrambled string in a way that cannot be reversed. The database stores
  only the hash; at login the typed password is hashed again and the two hashes
  are compared. Even if the database leaks, the real passwords do not. Used in
  `app/core/security.py`: `PasswordHash.recommended()` creates the hasher,
  `hash_password` and `verify_password` wrap it.
- `[argon2,bcrypt]` - two extras, separated by a comma. I read
  `pwdlib/_hash.py` in the venv: `PasswordHash.recommended()` returns a hasher
  that uses **Argon2** only (the hashes it makes start with `$argon2id$`; I
  checked by running it). Argon2 is implemented by the `argon2-cffi` package,
  and that is what the `argon2` extra installs, so this extra is essential. The
  `bcrypt` extra installs the `bcrypt` package. **No code in this project uses
  bcrypt at the moment**; it is there so that, if you ever had old bcrypt
  hashes to verify, you could add `BcryptHasher` to the hasher list without
  installing anything new. Removing `,bcrypt` would not break anything today.
- `==0.3.1` - exact version.

**Why it is here.** Login needs both halves: a safe way to store passwords
(pwdlib) and a safe way to prove "I am logged in" on later requests without
sending the password every time (python-jose).

**If you removed or changed it.** Remove `python-jose`: `app/core/security.py`
fails at `from jose import JWTError, jwt`, and because `dependencies.py` imports
`security.py`, the whole app fails to start. Remove `pwdlib`: same file, same
result (`ModuleNotFoundError: No module named 'pwdlib'`). Remove only the
`[argon2]` extra: the import works, but `PasswordHash.recommended()` at the top
of `security.py` tries to import `argon2` and raises pwdlib's own
`HasherNotAvailable("argon2")` error (I read `pwdlib/hashers/argon2.py`: it
catches the `ImportError` and re-raises it under that name), again at startup.

### Block 6: validation helpers

```text
# Request validation helpers (EmailStr and the OAuth2 login form)
email-validator==2.3.0
python-multipart==0.0.32
```

- `# Request validation helpers (EmailStr and the OAuth2 login form)` - comment
  naming the two places these libraries matter.
- `email-validator` - checks that a string really looks like an email address.
  You never import it yourself. Pydantic's `EmailStr` type, used in
  `app/schemas/user.py` for the register endpoint, needs it. I opened
  `pydantic/networks.py`: if the library is missing, pydantic raises
  `ImportError: email-validator is not installed, run pip install 'pydantic[email]'`
  the moment Python builds a model class that uses `EmailStr`, which is when
  `app/schemas/user.py` is imported, so at startup. Its own metadata says it
  needs `dnspython` and `idna`, which come along automatically.
- `==2.3.0` - exact version (pydantic specifically checks that the major version
  is 2, so an old 1.x would be rejected).
- `python-multipart` - parses **form** bodies. Most of this API speaks JSON, but
  the OAuth2 standard says the login request must be a *form*
  (`application/x-www-form-urlencoded`, the same format an HTML `<form>` sends),
  with fields named `username` and `password`. The `OAuth2PasswordRequestForm`
  in `app/routers/auth.py` reads such a form, and the **Authorize** button in
  `/docs` sends one. FastAPI does not parse forms itself; it needs this
  library. The module it installs is `python_multipart`.
- `==0.0.32` - exact version.

**Why it is here.** Without these two, the two most basic things a user does,
register (needs `EmailStr`) and log in (needs the form parser), do not work.

**If you removed or changed it.** Remove `email-validator`: startup fails with
the `ImportError` quoted above, pointing at `UserCreate` in
`app/schemas/user.py`. Remove `python-multipart`: I checked
`fastapi/dependencies/utils.py`; FastAPI calls a check named
`ensure_multipart_is_installed` while it builds the login endpoint, and raises
`RuntimeError: Form data requires "python-multipart" to be installed.` with
the install command in the message.

### Why the versions are pinned with `==`

Every line uses `==`, "exactly this version". Here is the reasoning:

1. **The same code everywhere.** With pins, your laptop, a teammate's laptop and
   the hosting server all get identical libraries. Without pins (`fastapi` on
   its own), pip installs whatever is newest *that day*. Two people installing a
   month apart can get different versions and see different behaviour, and
   "works on my machine" bugs appear.
2. **No surprise upgrades.** Libraries change. SQLAlchemy 1.4 and 2.0 are very
   different; pydantic 1 and 2 are very different; FastAPI and uvicorn are still
   on `0.x` versions, where even a minor release may change something. A pin
   means an upgrade is a decision you make on purpose, test, and commit, not
   something that happens silently during `pip install`.
3. **Matching the old project.** These are exactly the versions your old project
   already used (see the comparison below), so nothing had to be re-learned.

One honest limitation: only the ten *direct* libraries are pinned. The
transitive ones (pydantic, starlette, python-dotenv, argon2-cffi, cryptography
and so on) are chosen by pip within the ranges the ten libraries allow. Today
that gives pydantic 2.13.5 and starlette 1.7.0, but a fresh install next year
could pick newer ones. The usual fix, when a project becomes serious, is to run
`pip freeze > requirements.txt` in a working venv, which writes *every*
installed package with its exact version.

### Compared to your old code

Your old project has a file with the same purpose at
`C:\Users\hp\Desktop\zip\reqiurements.txt`:

```text
fastapi==0.141.1
uvicorn==0.53.0
SQLAlchemy==2.0.54
alembic==1.20.0
psycopg2-binary==2.9.13
pydantic-settings==2.15.0
python-jose[cryptography]==3.5.0
pwdlib[argon2,bcrypt]==0.3.1
email-validator==2.3.0
python-multipart==0.0.32
```

What is the same: the ten libraries and the ten versions are **identical**, in
the same order. You already made good choices here: `pwdlib` instead of the
older `passlib`, and `psycopg2-binary` so nothing has to be compiled. The new
project did not need to change a single pin.

What is different:

1. **The file name has a typo: `reqiurements.txt`** (the `i` and `u` are
   swapped). This is a small thing with a real effect. The standard command
   everyone types, `pip install -r requirements.txt`, fails in your old folder
   with `ERROR: Could not open requirements file: [Errno 2] No such file or
   directory: 'requirements.txt'`. Anyone who clones the project has to notice
   the typo first. The new file is named `requirements.txt`, which is the name
   every tutorial, hosting provider and editor expects.
2. **No comments or grouping.** The old file is a flat list. The new one groups
   the libraries by job (web, database, settings, auth, validation) with a
   comment on each group, so a reader can see *why* each library is there
   without opening the code.
3. **No separation of test libraries.** The old project had no tests, so it had
   no test libraries. The new project keeps the runtime list here and puts the
   test-only libraries in `requirements-dev.txt`, so a production server does
   not install pytest.

### Key terms in this file

| Term                    | One-line meaning                                                                 |
| ----------------------- | -------------------------------------------------------------------------------- |
| pip                     | Python's package installer; reads this file with `-r`                            |
| PyPI                    | The public index of Python packages that pip downloads from                     |
| `==`                    | "Exactly this version"                                                           |
| pin / pinned version    | A dependency written with an exact version so every install is identical         |
| major.minor.patch       | The three numbers of a version; big change / new feature / bug fix (convention)  |
| extra (`name[extra]`)   | An optional add-on set of packages defined by the library author                 |
| transitive dependency   | A library you did not list but pip installed because something you listed needs it |
| ASGI                    | The contract between a Python web server (uvicorn) and a web app (FastAPI)       |
| ORM                     | Object Relational Mapper: tables as classes, rows as objects (SQLAlchemy)        |
| migration               | A numbered script that changes the database structure (Alembic)                  |
| driver                  | The piece that speaks the database's network protocol (psycopg2)                 |
| JWT                     | JSON Web Token: a signed `header.payload.signature` string proving who you are   |
| claim                   | One fact stored inside a JWT payload, such as `sub` (the user id) or `exp`       |
| hashing                 | One-way scrambling of a password so it can be checked but not read back          |
| Argon2                  | The password hashing algorithm pwdlib uses by default                            |
| form body               | Request data sent as `field=value&field2=value2`, like an HTML form              |

---

## File: requirements-dev.txt

### What this file is for

This is the second shopping list for pip. "dev" is short for *development*: the
libraries a developer needs on their own computer that the running API does not
need. There are only two of them, and both exist for the automated tests. The
file starts by pulling in the whole of `requirements.txt`, so installing this
one file gives you everything.

The idea is simple: on your laptop you install `requirements-dev.txt`; a
production server installs `requirements.txt` and never downloads pytest. Like
the other list, only pip reads this file; no Python code imports it.

### The whole file

```text
# Development-only dependencies (running the test suite).
# Install with:  pip install -r requirements-dev.txt

-r requirements.txt

pytest
# HTTP client that FastAPI's TestClient is built on
httpx2
```

### Walkthrough, block by block

### Block 1: the header comments

```text
# Development-only dependencies (running the test suite).
# Install with:  pip install -r requirements-dev.txt
```

- `#` - comment, ignored by pip.
- `Development-only dependencies` - libraries needed to *develop* the project
  (run tests), not to run the API.
- `running the test suite` - a *test suite* is the collection of automated tests
  in the `tests/` folder. These docs do not go into them.
- `pip install -r requirements-dev.txt` - the command for this file; same `-r`
  flag as before, different file name.

**Why it is here.** Tells the reader which of the two files to install.

**If you removed or changed it.** Nothing breaks; pip ignores comments.

### Block 2: include the runtime list

```text
-r requirements.txt
```

- `-r` - the same flag you pass to pip on the command line, but written *inside*
  a requirements file. It means "also read every line of this other file, as if
  it were pasted here".
- `requirements.txt` - the file to include. pip looks for it in the same folder
  as the file that contains the `-r` line, so both files must stay next to each
  other in the project root.

**Why it is here.** It keeps the runtime list in one place. If a new library is
added to `requirements.txt`, the dev list gets it automatically; nobody has to
remember to update two files, and the two can never disagree about a version.

**If you removed or changed it.** `pip install -r requirements-dev.txt` would
install only pytest and httpx2. FastAPI, SQLAlchemy and the rest would be
missing, so the tests (and the app) would fail at the first
`from fastapi import ...` with `ModuleNotFoundError`. If you instead copied the
ten lines by hand into this file, it would work, but you would now maintain two
copies that can drift apart.

### Block 3: pytest

```text
pytest
```

- `pytest` - the test runner. It is a command-line program that looks for files
  named `test_*.py`, runs every function in them whose name starts with `test_`,
  and prints a green/red report. `pytest.ini` in the project root tells it that
  the tests live in `tests/`. The app code never imports pytest.
- There is **no `==version`** on this line. That means "install the newest
  pytest available". In this venv that gave pytest 9.1.1.

**Why it is here.** It is the one tool needed to run the tests.

**If you removed or changed it.** The app is unaffected. The `pytest` command
would not exist, so the tests could not be run. Because the version is not
pinned, a fresh install in a year may bring a newer pytest with slightly
different output or rules; this is less dangerous than an unpinned FastAPI
because pytest only affects the tests, not the API, but for full consistency
you could pin it to `pytest==9.1.1`, the version installed today.

### Block 4: httpx2

```text
# HTTP client that FastAPI's TestClient is built on
httpx2
```

- `# HTTP client that FastAPI's TestClient is built on` - comment explaining why
  a second library is needed. An *HTTP client* is a library for **sending**
  requests (the opposite of a server, which receives them); the well-known
  `requests` library is an HTTP client.
- `FastAPI's TestClient` - a helper class FastAPI provides (it actually lives in
  starlette, FastAPI's base). It lets the tests call the API *in memory*: no
  uvicorn, no network port, no running server. `client.post("/api/v1/auth/login", ...)`
  goes straight into the app and returns the response object.
- `httpx2` - the library that `TestClient` is built on. I opened
  `starlette/testclient.py` in the venv: it starts with `import httpx2 as httpx`.
  If `httpx2` is missing it tries the older `httpx` library and prints a
  deprecation warning saying to install `httpx2` instead; if neither is
  installed it raises an error that begins
  `The starlette.testclient module requires the httpx2 package to be installed.`
  `httpx2` is the successor of `httpx`, by the same author; version 2.13.1 is
  installed here. Again no `==`, so pip takes the newest.

**Why it is here.** Without it `from fastapi.testclient import TestClient` in
the test setup fails, and not one test can run. It is a dev-only dependency
because the API itself never *sends* HTTP requests; it only receives them.

**If you removed or changed it.** The app runs exactly as before. The tests
fail at import time with the starlette error quoted above. If you replaced it
with the older `httpx`, the tests would still run, but with a deprecation
warning on every run telling you to switch back to `httpx2`.

### Compared to your old code

There is **no equivalent** in the old project. It had a single `reqiurements.txt`
and no tests, so there was nothing to separate.

The new project splits the lists for two reasons. First, a production server
should install only what it needs; pytest and httpx2 are useless there. Second,
the split documents intent: a reader sees at once that these two libraries are
for testing and that the app does not depend on them. The `-r` include line is
the standard trick that makes the split cost nothing to maintain.

### Key terms in this file

| Term               | One-line meaning                                                                       |
| ------------------ | -------------------------------------------------------------------------------------- |
| dev dependency     | A library needed to develop or test the project, not to run it                         |
| `-r file`          | Inside a requirements file: "also read every line of that file"                        |
| pytest             | The test runner: finds `test_*.py` files and runs the `test_*` functions in them       |
| test suite         | All the automated tests of a project, here the `tests/` folder                         |
| HTTP client        | A library that sends HTTP requests (as opposed to a server, which receives them)       |
| TestClient         | FastAPI/starlette helper that calls the app in memory, without a server                |
| httpx2             | The HTTP client library TestClient is built on; successor of `httpx`                   |
| unpinned           | A dependency line without `==`, so pip installs the newest version                     |

---

## File: .env.example

### What this file is for

First, two words. An **environment variable** is a named text value that the
operating system keeps for a running program, for example `PATH`. Python can
read them through `os.environ`. They are the standard way to give a program
secrets (passwords, keys) without writing the secrets into the code. Typing
them into Windows every time is annoying, so there is a convention: a text file
named `.env` ("environment file") with one `NAME=value` per line. A small
library reads that file and treats each line as if it were a real environment
variable.

`.env.example` is the **template** for that `.env` file. The app never reads
`.env.example`. You copy it to `.env`, replace the placeholder values with your
own, and the app reads `.env`. The template is committed to git so every
teammate sees which settings exist; the real `.env` is in `.gitignore` so the
passwords never leave your computer.

The one file that reads `.env` is `app/core/config.py`. Its `Settings` class
(built on `pydantic_settings.BaseSettings`, pinned in `requirements.txt`) has
one field per variable; the line `settings = Settings()` at the bottom of that
file does the reading once, when the file is first imported. Every other file
then does `from app.core.config import settings`. The table shows where each
variable travels:

| Variable in `.env`            | Field in `app/core/config.py`                  | Where the value is finally used                                                                 |
| ----------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `DATABASE_HOSTNAME`           | `DATABASE_HOSTNAME: str = "localhost"`         | `database_url` property -> `create_engine(...)` in `app/database/session.py` and `alembic/env.py` |
| `DATABASE_PORT`               | `DATABASE_PORT: int = 5432`                    | same                                                                                            |
| `DATABASE_NAME`               | `DATABASE_NAME: str = "expense_tracker"`       | same                                                                                            |
| `DATABASE_USERNAME`           | `DATABASE_USERNAME: str = "postgres"`          | same                                                                                            |
| `DATABASE_PASSWORD`           | `DATABASE_PASSWORD: str = ""`                  | same                                                                                            |
| `DATABASE_URL` (optional)     | `DATABASE_URL: str \| None = None`             | same; when set, it replaces the five values above                                               |
| `SECRET_KEY`                  | `SECRET_KEY: str` (no default: required)       | `jwt.encode(...)` and `jwt.decode(...)` in `app/core/security.py`                               |
| `ALGORITHM`                   | `ALGORITHM: str = "HS256"`                     | same two calls                                                                                  |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `ACCESS_TOKEN_EXPIRE_MINUTES: int = 60`        | `create_access_token` in `app/core/security.py`                                                 |
| `CORS_ALLOWED_ORIGINS`        | `CORS_ALLOWED_ORIGINS: str = ""`               | `cors_allowed_origins_list` property -> `CORSMiddleware` in `app/main.py`                       |

Three rules about *how* the values are read. I confirmed each one by running a
small script against the real `Settings` class:

1. **Order of priority.** A real environment variable beats the `.env` file,
   and the `.env` file beats the default written in `config.py`. (I set
   `SECRET_KEY=from-dotenv` in `.env` and `SECRET_KEY=from-environment` in the
   environment; the app saw `from-environment`.) This is also what
   `pydantic_settings/main.py` says in `settings_customise_sources`: the order
   is init values, environment, dotenv, secret files.
2. **Unknown keys are ignored.** `config.py` sets `extra="ignore"`, so an extra
   line such as `UNKNOWN_KEY=hello` in `.env` is simply skipped. (Without that
   setting, pydantic-settings' default is `extra='forbid'`; see the comparison
   with your old code.)
3. **`.env` is looked for in the folder you run the command from.** The path
   `".env"` in `config.py` is relative to the *current working directory*, not
   to the project. I ran the script from a different folder that had its own
   `.env`, and that one was read. So commands (`uvicorn`, `alembic`, `pytest`)
   are run from the project root, where `.env` lives.

### The whole file

```text
# Copy this file to ".env" and fill in your own values.
# The real .env is listed in .gitignore - never commit it.

# --- PostgreSQL connection ---
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_NAME=expense_tracker
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_postgres_password

# Optional: a full connection URL. If set, it is used instead of the five
# values above (hosting providers usually give you one).
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# --- JWT authentication ---
# Generate your own long random key with:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=replace_this_with_a_long_random_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# --- CORS ---
# Comma-separated frontend URLs that may call this API from a browser.
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Walkthrough, block by block

The syntax of a `.env` file, once, so the blocks can focus on meaning:

- One `NAME=value` per line. No spaces around `=`. No quotes needed.
- Every value arrives in Python as **text**. `config.py` converts it where the
  field says so (`DATABASE_PORT: int` turns `"5432"` into `5432`).
- `#` starts a comment. A line that *starts* with `#` is not read at all; that
  is how the `DATABASE_URL` line is "switched off" below.
- The names are matched to the fields in `config.py`. pydantic-settings ignores
  upper/lower case when matching (I saw it report a key in lower case in an
  error message), but keep them identical to avoid confusion.

### Block 1: the header comments

```text
# Copy this file to ".env" and fill in your own values.
# The real .env is listed in .gitignore - never commit it.
```

- `#` - comment; the loader skips the line.
- `Copy this file to ".env"` - the instruction. The copy is what the app reads.
- `fill in your own values` - the values below are placeholders or safe local
  defaults, not real secrets.
- `The real .env is listed in .gitignore` - points to the fourth file in this
  document, where the line `.env` keeps the copy out of git.
- `never commit it` - a reminder: a password that is pushed to a repository is
  in the history forever, even if you delete it later.

**Why it is here.** It tells a new developer the one step they must do before
anything works, and warns about the single most common security mistake.

**If you removed or changed it.** Nothing breaks. Someone might edit
`.env.example` itself and wonder why the app ignores it.

### Block 2: database host and port

```text
# --- PostgreSQL connection ---
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
```

- `# --- PostgreSQL connection ---` - a comment that opens the group of five
  values that together say *where* the database is and *how to log in*.
- `DATABASE_HOSTNAME` - the name of the computer where PostgreSQL runs. It fills
  this field in `config.py`:

  ```python
  DATABASE_HOSTNAME: str = "localhost"
  ```

  `str` says "text"; `= "localhost"` is the default used when the line is
  missing.
- `=` - separates name from value.
- `localhost` - a special name that always means "this same computer"
  (it resolves to the address `127.0.0.1`). If PostgreSQL ran on another
  machine, or in Docker, this would be that machine's name or IP address.
- `DATABASE_PORT` - the network port PostgreSQL listens on. Field:

  ```python
  DATABASE_PORT: int = 5432
  ```

  `int` makes pydantic convert the text `"5432"` into the number `5432`.
- `5432` - PostgreSQL's default port, the one a normal installation uses.

Both values are consumed inside the `database_url` property of `config.py`:

```python
return URL.create(
    drivername="postgresql+psycopg2",
    username=self.DATABASE_USERNAME,
    password=self.DATABASE_PASSWORD,
    host=self.DATABASE_HOSTNAME,
    port=self.DATABASE_PORT,
    database=self.DATABASE_NAME,
).render_as_string(hide_password=False)
```

which produces a connection URL such as
`postgresql+psycopg2://postgres:...@localhost:5432/expense_tracker`. That
string is handed to `create_engine(...)` in `app/database/session.py` (the
app's connection pool) and in `alembic/env.py` (migrations).

**Why it is here.** So the same code can point at a local PostgreSQL today and
a remote one tomorrow by editing a text file, not Python.

**If you removed or changed it.** Remove either line: the default kicks in,
which for local development is the same value, so nothing changes. Set
`DATABASE_PORT=abc`: the app refuses to start; I tried it and got
`ValidationError: DATABASE_PORT Input should be a valid integer, unable to parse string as an integer`.
Set a wrong host or port: imports succeed, but `check_database_connection()`
in the `lifespan` function of `app/main.py` runs at startup, psycopg2 raises an
`OperationalError` ("could not connect to server" or "connection refused"),
uvicorn prints `Application startup failed. Exiting.` and no request is ever
served. That is on purpose: better to fail at startup than to answer every
request with a 500.

### Block 3: database name, user and password

```text
DATABASE_NAME=expense_tracker
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_postgres_password
```

- `DATABASE_NAME` - which database to use. One PostgreSQL server can hold many
  databases; this one must already exist (the README's setup step creates it
  with `CREATE DATABASE expense_tracker;`). Field:

  ```python
  DATABASE_NAME: str = "expense_tracker"
  ```

- `expense_tracker` - the default name, matching the project.
- `DATABASE_USERNAME` - the PostgreSQL user (PostgreSQL calls it a *role*) to
  log in as. Field: `DATABASE_USERNAME: str = "postgres"`.
- `postgres` - the administrator user that every PostgreSQL installation
  creates. Fine for local development.
- `DATABASE_PASSWORD` - that user's password. Field:

  ```python
  DATABASE_PASSWORD: str = ""
  ```

  The default is empty text, which only works if PostgreSQL is set up without
  a password, so in practice this line is always filled in.
- `your_postgres_password` - a placeholder you replace. It is deliberately
  obvious so nobody mistakes it for a real value.

A detail worth knowing: because `config.py` builds the URL with
`URL.create(...)`, the password may contain characters that are special inside
a URL. I tested the password `p@ss:word/1`; the URL came out as
`...postgres:p%40ss%3Aword%2F1@localhost:5432/...`, with `@`, `:` and `/`
safely escaped. The old project's f-string would have broken on that `@`.

**Why it is here.** These three complete the login to PostgreSQL. All five
values are separate so that each can be changed alone, and so that hosting
dashboards, which usually show them separately, map one-to-one.

**If you removed or changed it.** Leave the placeholder password or type a
wrong one: startup fails with psycopg2's
`OperationalError: ... password authentication failed for user "postgres"`.
Point `DATABASE_NAME` at a database that does not exist: startup fails with
`FATAL: database "..." does not exist`. Remove `DATABASE_NAME` or
`DATABASE_USERNAME`: the defaults apply, so nothing changes for a standard
local setup.

### Block 4: the optional full URL

```text
# Optional: a full connection URL. If set, it is used instead of the five
# values above (hosting providers usually give you one).
# DATABASE_URL=postgresql://user:password@host:5432/dbname
```

- `# Optional: ...` - two comment lines explaining the feature.
- `# DATABASE_URL=...` - the third line is **also a comment**. Because it
  starts with `#`, the loader never sees it, and the field keeps its default:

  ```python
  DATABASE_URL: str | None = None
  ```

  `str | None` means "either text or the special value `None`" (`None` is
  Python's "nothing"); `= None` is the default: not set.
- `postgresql://user:password@host:5432/dbname` - the shape of a connection
  URL, every part of the five separate values packed into one string:
  `postgresql://` (which kind of database), `user:password@` (login),
  `host:5432` (where), `/dbname` (which database).

The `database_url` property in `config.py` checks this field first:

```python
if self.DATABASE_URL:
    # Some providers still hand out the old "postgres://" scheme,
    # which SQLAlchemy no longer accepts.
    return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
```

`if self.DATABASE_URL:` is true for any non-empty text, so when the variable is
set the five separate values are ignored. The `.replace(..., 1)` swaps a
leading `postgres://` for `postgresql://` at most once; I tested
`postgres://u:p@h:5432/d` and got `postgresql://u:p@h:5432/d`. With no
`+psycopg2` in the scheme, SQLAlchemy uses psycopg2 anyway, because it is the
default driver for `postgresql://`.

**Why it is here.** Hosting providers (Render, Railway, Heroku and others) give
you one `DATABASE_URL` variable, not five. This lets you paste it and go. The
`postgres://` fix is there because some of them still use that older spelling,
which SQLAlchemy 2.0 rejects.

**If you removed or changed it.** Remove the three lines: nothing changes, the
field is optional. Uncomment the line as it is: the app tries to reach a
machine literally named `host` and fails at startup. Set it to a real URL: it
works, and from then on edits to `DATABASE_PASSWORD` and friends have **no
effect**, which is the one thing to remember when "changing the password does
nothing".

### Block 5: the JWT header and the key generator

```text
# --- JWT authentication ---
# Generate your own long random key with:
#   python -c "import secrets; print(secrets.token_hex(32))"
```

- `# --- JWT authentication ---` - comment opening the group of three values
  that control login tokens. JWT was explained under `requirements.txt`
  (block 5): a signed `header.payload.signature` string.
- `# Generate your own long random key with:` - comment introducing a command.
- `python -c "..."` - runs the quoted text as a one-line Python program.
- `import secrets` - loads Python's built-in `secrets` module, which produces
  random values suitable for security (unlike the `random` module, whose
  output can be predicted).
- `;` - lets two statements share one line.
- `secrets.token_hex(32)` - produces 32 random bytes and writes them as
  hexadecimal text (digits `0-9` and letters `a-f`). Each byte becomes two
  characters, so the result is 64 characters long (I ran it to confirm).
- `print(...)` - shows the result so you can copy it.

**Why it is here.** People invent keys like `secret123`. A key that short can be
guessed, and a guessed key lets an attacker sign a token for any user id. The
command gives a key that cannot be guessed.

**If you removed or changed it.** Nothing breaks; these are comments. The next
developer would be more likely to type a weak key.

### Block 6: SECRET_KEY

```text
SECRET_KEY=replace_this_with_a_long_random_string
```

- `SECRET_KEY` - the private key used to sign every JWT. Field:

  ```python
  SECRET_KEY: str  # required: no default so the app refuses to start without it
  ```

  There is no `= ...` after `str`, so the field has **no default** and is
  **required**.
- `replace_this_with_a_long_random_string` - a placeholder that says what to
  do. It is deliberately not a usable-looking key.

It is used twice in `app/core/security.py`:

```python
return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

when a user logs in (sign the token), and

```python
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

on every protected request (check the signature). The signature is computed
from the token's payload *and* this key. Only someone who knows the key can
produce a valid signature, so the server trusts the user id inside a token
whose signature checks out.

**Why it is here.** This single value is the whole security of login. It must
be secret (hence `.env`, not code) and unique per installation (hence the
generator command, not a shared default).

**If you removed or changed it.** Remove the line (and have no `SECRET_KEY`
environment variable): `settings = Settings()` at the bottom of `config.py`
raises, I confirmed, `ValidationError: 1 validation error for Settings  SECRET_KEY  Field required`.
Because that line runs at import, nothing starts: not uvicorn, not Alembic.
This is intentional: an app with no secret must not run. Change the value
while tokens are in use: every token signed with the old key now fails
`jwt.decode` with `JWTError: Signature verification failed` (I tested signing
with one key and decoding with another), `decode_access_token` returns `None`,
`get_current_user` in `app/core/dependencies.py` raises
`401 Could not validate credentials`, and every user has to log in again.
Leave the placeholder: everything works, but anyone who has read this public
template knows your key and can forge tokens.

### Block 7: ALGORITHM

```text
ALGORITHM=HS256
```

- `ALGORITHM` - which signing method the JWT uses. Field:
  `ALGORITHM: str = "HS256"`.
- `HS256` - short for *HMAC using SHA-256*. SHA-256 is a hash function; HMAC is
  a standard way of mixing a message with a secret key through a hash function
  to get a signature. It is *symmetric*: the same key signs and verifies. That
  is fine here because the same server does both. (The alternative family,
  `RS256`, uses a private/public key pair and is for cases where other services
  must verify tokens without being able to create them.)

It is passed to both calls shown in block 6 (`algorithm=settings.ALGORITHM` when
signing, `algorithms=[settings.ALGORITHM]` when checking). The list form on
decode is jose's protection against a known trick where an attacker changes the
algorithm named inside the token header; only the listed algorithm is accepted.

**Why it is here.** So the algorithm is a setting, not a string repeated in two
places in the code.

**If you removed or changed it.** Remove it: default `HS256`, no change. Set an
unsupported name such as `HS999`: `jwt.encode` raises
`jose.exceptions.JWSError: Algorithm HS999 not supported.` (I ran it). That
happens inside `create_access_token` during login, and I checked that
`JWSError` is **not** a subclass of `JWTError`, so nothing in the login endpoint
catches it: `POST /api/v1/auth/login` answers `500 Internal Server Error`.
Set `RS256`: it also fails, because the text in `SECRET_KEY` is not an RSA key;
I am not 100% sure of the exact exception name in that case. Change the
algorithm while tokens are in use: old tokens were signed with a different
algorithm than the one in the `algorithms=[...]` list, so decoding fails with a
`JWTError`, and users get 401 until they log in again.

### Block 8: ACCESS_TOKEN_EXPIRE_MINUTES

```text
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

- `ACCESS_TOKEN_EXPIRE_MINUTES` - how long a login token stays valid, in
  minutes. Field: `ACCESS_TOKEN_EXPIRE_MINUTES: int = 60`; the text `"60"`
  becomes the number `60`.
- `60` - one hour.

Used once, in `create_access_token` in `app/core/security.py`:

```python
expires_at = datetime.now(timezone.utc) + timedelta(
    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
)
payload = {
    "sub": str(user_id),
    "exp": expires_at,
}
```

The expiry time is written into the token as the `exp` claim. When
`jwt.decode` runs later it compares `exp` with the current time and raises
`ExpiredSignatureError` (a kind of `JWTError`) if the moment has passed, which
`decode_access_token` turns into `None`, which becomes a 401.

**Why it is here.** A stolen token is only useful until it expires. One hour is
a common compromise between safety and not making users log in all day.

**If you removed or changed it.** Remove it: default 60. Set `0`: every token is
already expired when created, so the first protected request after login gets
`401 Could not validate credentials`. Set `abc`: startup fails with the same
`int_parsing` validation error shown for `DATABASE_PORT`. Set `525600` (a
year): tokens never seem to expire, which is convenient and risky.

### Block 9: CORS

```text
# --- CORS ---
# Comma-separated frontend URLs that may call this API from a browser.
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

- `# --- CORS ---` - comment opening the last group. CORS is *Cross-Origin
  Resource Sharing*. An *origin* is scheme + host + port, for example
  `http://localhost:3000`. Browsers have a safety rule: JavaScript running on
  one origin may not read responses from another origin unless that other
  server explicitly says it is allowed. CORS is the set of HTTP headers the
  server uses to say so.
- `# Comma-separated frontend URLs ...` - comment: the value is one piece of
  text holding several URLs with commas between them, because environment
  variables can only hold text, not lists.
- `CORS_ALLOWED_ORIGINS` - field: `CORS_ALLOWED_ORIGINS: str = ""` (empty by
  default: no browser origin allowed).
- `http://localhost:3000` - the default address of a React development server
  (Create React App, Next.js).
- `,` - the separator.
- `http://localhost:5173` - the default address of a Vite development server
  (used by modern React, Vue and Svelte setups).

`config.py` turns the text into a list with this property:

```python
@property
def cors_allowed_origins_list(self) -> list[str]:
    return [
        origin.strip()
        for origin in self.CORS_ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
```

`.split(",")` cuts at commas, `.strip()` removes spaces around each piece, and
`if origin.strip()` drops empty pieces. I tested
`"http://localhost:3000, http://localhost:5173 ,"` and got exactly
`['http://localhost:3000', 'http://localhost:5173']`; an empty value gives `[]`.
`app/main.py` hands that list to the middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    ...
)
```

**Why it is here.** The API will be used by a browser frontend served from a
different port than the API. Without this header the browser would block every
response, and the frontend developer would see the famous
"blocked by CORS policy" error in the console.

**If you removed or changed it.** Remove the line or leave it empty: the list is
`[]`, the middleware adds no `Access-Control-Allow-Origin` header, and browser
frontends on other origins are blocked. Everything that is *not* a cross-origin
browser call still works: `/docs` (same origin as the API), Postman, curl, the
tests. Add a frontend's real address and it starts working. Matching is exact
text: `http://localhost:3000` does not cover `http://127.0.0.1:3000` or
`https://localhost:3000`; add each one you use.

### Compared to your old code

The old project had **no `.env.example`**, only a real `.env` next to a
`config.py`. (I looked only at the variable *names* in your old `.env`, not the
values.) The names were the same eight that the old settings class declares:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_HOSTNAME: str
    DATABASE_PORT: str
    DATABASE_NAME: str
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: int
    SECRET_KEY : str
    ALGORITHM : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int

    class Config:
        env_file = ".env"

settings = Settings()
```

and the URL was built in the old `database.py` like this:

```python
Database_URL = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}/{settings.DATABASE_NAME}"
```

What is the same: the idea (secrets in `.env`, read by a pydantic-settings
class), and the names `DATABASE_HOSTNAME`, `DATABASE_PORT`, `DATABASE_NAME`,
`DATABASE_USERNAME`, `DATABASE_PASSWORD`, `SECRET_KEY`, `ALGORITHM`,
`ACCESS_TOKEN_EXPIRE_MINUTES` are kept exactly, so your old `.env` values would
still be understood.

What is different, and why:

1. **There is now a template.** With only a real `.env` (which must not be
   committed), a teammate cloning the repository has no way to know which
   variables exist except by reading `config.py`. `.env.example` is the
   committed, password-free copy that documents them.
2. **`DATABASE_PASSWORD: int` was a bug.** The old class declared the password
   as a whole number. It worked only because the password happened to be made
   of digits. I built the same class and gave it the password `abc123`; the
   result was `ValidationError: DATABASE_PASSWORD Input should be a valid integer`
   at startup. Any normal password would have stopped the app. The new field
   is `str`.
3. **`DATABASE_PORT` was declared but never used.** The old class read it as
   text, and the old URL f-string does not include a port at all, so changing
   `DATABASE_PORT` in the old `.env` did nothing. The new project reads it as
   `int` and passes it to `URL.create(port=...)`.
4. **The URL was built by hand.** An f-string pastes the password straight into
   the URL. A password with `@`, `:` or `/` in it would produce a URL that
   SQLAlchemy reads wrongly. The new `URL.create(...)` escapes those characters
   (shown in block 3).
5. **Every old field was required.** No defaults, so all eight lines had to be
   present or the app crashed. The new class gives sensible local defaults to
   everything except `SECRET_KEY`, so a minimal `.env` needs just the password
   and the key.
6. **`class Config:` is the old pydantic style.** It still works, but when I
   built the old class pydantic printed the warning
   `Support for class-based 'config' is deprecated, use ConfigDict instead`.
   The new file uses `model_config = SettingsConfigDict(...)`, the pydantic v2
   way; it is explained word by word in the `core: config` document.
7. **Unknown keys crashed the old app.** pydantic-settings' default is
   `extra='forbid'` (I checked `pydantic_settings/main.py`). I added one extra
   line to a `.env` read by the old class and got
   `ValidationError: Extra inputs are not permitted`. The new class sets
   `extra="ignore"`, so a stray line is harmless.
8. **Two new variables.** `DATABASE_URL` (one-line URL for hosting providers)
   and `CORS_ALLOWED_ORIGINS` (browser frontends) did not exist in the old
   project because it had no deployment story and no frontend.
9. **Spaces before the colons** (`SECRET_KEY : str`) are legal Python but not
   the usual style; the new file writes `SECRET_KEY: str`.

### Key terms in this file

| Term                    | One-line meaning                                                                        |
| ----------------------- | --------------------------------------------------------------------------------------- |
| environment variable    | A named text value the operating system gives to a running program                      |
| `.env` file             | A text file of `NAME=value` lines that the app reads as if they were environment variables |
| template (`.example`)   | A committed, secret-free copy that shows which variables exist                          |
| pydantic-settings       | The library that reads environment variables and `.env` into the typed `Settings` class |
| priority                | Real environment variable > `.env` > default in `config.py`                             |
| `extra="ignore"`        | Unknown keys in `.env` are skipped instead of crashing                                  |
| current working directory | The folder you run a command from; `.env` is looked for there                         |
| `localhost`             | "This computer"; the address `127.0.0.1`                                                |
| port                    | A number identifying one service on a machine; PostgreSQL uses 5432                     |
| connection URL          | `postgresql://user:password@host:port/dbname`, all database settings in one string      |
| `URL.create`            | SQLAlchemy helper that builds a connection URL and escapes special characters            |
| `secrets.token_hex(32)` | 32 random bytes as 64 hex characters; a good secret key                                 |
| `SECRET_KEY`            | The private key that signs and checks every JWT                                         |
| HS256                   | HMAC with SHA-256; a symmetric signing algorithm (same key signs and checks)            |
| claim (`sub`, `exp`)    | A fact inside a JWT: `sub` = the user id, `exp` = expiry time                            |
| CORS                    | Browser rule: a page on one origin may call another origin only if that server allows it |
| origin                  | scheme + host + port, e.g. `http://localhost:3000`                                      |
| f-string                | `f"...{value}..."`: Python text with values pasted in; no escaping is done               |

---

## File: .gitignore

### What this file is for

`.gitignore` is read by **git**, nothing else. It is a list of name patterns;
any file or folder whose name matches a pattern is invisible to `git add` and
`git status`. It exists because `git add .` means "add everything", and
"everything" in a Python project includes things that must never go into the
repository: the real `.env` with your passwords, the `venv/` folder with
thousands of library files, and caches that Python and pytest create on their
own. No Python code imports this file.

### The whole file

```text
# Secrets - never commit real credentials
.env

# Python
__pycache__/
*.py[cod]

# Virtual environments
venv/
.venv/
env/

# Test and tool caches
.pytest_cache/
.coverage
htmlcov/

# Local databases
*.db
*.sqlite3

# Editors / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

### Walkthrough, block by block

The pattern language, once:

- One pattern per line. `#` starts a comment.
- A plain name with no `/` (like `.env`) matches a file **or** folder with that
  exact name in **any** folder of the project, however deep.
- A name ending in `/` (like `venv/`) matches **only folders**.
- `*` matches any run of characters. `[cod]` matches **one** character that is
  `c`, `o` or `d`.
- Only the whole name counts: the pattern `.env` matches a file called `.env`,
  not `.env.example`, which is why the template still gets committed.

### Block 1: secrets

```text
# Secrets - never commit real credentials
.env
```

- `# Secrets - never commit real credentials` - comment; *credentials* means
  usernames, passwords and keys.
- `.env` - the real settings file you create by copying `.env.example`. It
  holds `DATABASE_PASSWORD` and `SECRET_KEY`.

**Why it is here.** This is the most important line in the file. A password
pushed to GitHub, even to a private repository, even if deleted a minute later,
stays in the git history and must be considered leaked.

**If you removed or changed it.** `git status` would list `.env` as a new file,
and the next `git add .` would stage it. Nothing would warn you.

### Block 2: Python's own files

```text
# Python
__pycache__/
*.py[cod]
```

- `# Python` - comment: files Python creates by itself.
- `__pycache__/` - the folder Python creates next to every module it imports,
  to store a pre-compiled copy so the next import is faster. The trailing `/`
  limits the pattern to folders. You can see one in your old project root.
- `*.py[cod]` - the compiled files themselves: `*` any name, `.py` then one of
  `c`, `o`, `d`, so `.pyc` (compiled), `.pyo` (old optimised form) and `.pyd`
  (Windows extension modules). This catches compiled files that end up outside
  a `__pycache__` folder.

**Why it is here.** These files are generated, machine-specific and rebuilt
automatically. Committing them only creates noise in every diff.

**If you removed or changed it.** Every `__pycache__` folder under `app/`,
`alembic/` and `tests/` would show up in `git status`, and each run of the app
would modify committed files.

### Block 3: virtual environments

```text
# Virtual environments
venv/
.venv/
env/
```

- `# Virtual environments` - comment. A *virtual environment* is the private
  folder where pip installs this project's libraries so they do not mix with
  other projects.
- `venv/` - the name the README uses (`python -m venv venv`).
- `.venv/` - another very common name (some editors create it by default).
- `env/` - a third common name.

**Why it is here.** The venv contains tens of thousands of files that belong to
the libraries, not to you, and it is rebuilt in seconds from
`requirements.txt`. It is also tied to your machine and Python version, so it
is useless to anyone else. Listing three names covers the usual conventions so
a teammate who prefers `.venv` is protected too.

**If you removed or changed it.** `git add .` would try to add the whole
`venv/` folder. The commit would be enormous and slow, and the libraries would
be duplicated in the repository.

### Block 4: test and tool caches

```text
# Test and tool caches
.pytest_cache/
.coverage
htmlcov/
```

- `# Test and tool caches` - comment: files that testing tools create.
- `.pytest_cache/` - a folder pytest creates in the project root to remember
  which tests failed last time (so you can re-run only those).
- `.coverage` - the data file written by the `coverage` tool, which measures
  which lines of code the tests executed.
- `htmlcov/` - the folder of HTML reports that the same tool can produce.

The `coverage` tool is **not** installed in this project (it is not in
`requirements-dev.txt`), so the last two lines do nothing today. They are
there so that the moment someone adds `pytest-cov`, its output stays out of
git without anyone remembering to edit this file.

**Why it is here.** Caches and reports are regenerated on every run and differ
from machine to machine.

**If you removed or changed it.** After the first `pytest` run, `.pytest_cache/`
would appear in `git status` and change on every run.

### Block 5: local databases

```text
# Local databases
*.db
*.sqlite3
```

- `# Local databases` - comment.
- `*.db` - any file ending in `.db`.
- `*.sqlite3` - any file ending in `.sqlite3`. Both are the usual extensions
  for **SQLite** databases, which live in a single file on disk (unlike
  PostgreSQL, which is a separate server).

**Why it is here.** The tests use an *in-memory* SQLite database, which never
touches the disk, so normally no such file is created. But `DATABASE_URL` can
point at a file-based SQLite database (`sqlite:///expenses.db`) for a quick
experiment, and that file would contain real data. This rule keeps it out of
git in advance.

**If you removed or changed it.** Nothing changes unless such a file exists; if
one did, it would be offered for commit.

### Block 6: editors and operating systems

```text
# Editors / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

- `# Editors / OS` - comment: files created by your editor or your operating
  system, not by the project.
- `.vscode/` - the settings folder Visual Studio Code creates in a project.
- `.idea/` - the settings folder PyCharm (and other JetBrains editors) creates.
- `.DS_Store` - a hidden file macOS writes into every folder you open in Finder
  to remember icon positions.
- `Thumbs.db` - a hidden file Windows Explorer writes into folders with images
  to cache thumbnails.

**Why it is here.** These are personal to one developer and one machine. A
teammate on a Mac with PyCharm should not receive your Windows and VS Code
leftovers, and vice versa.

**If you removed or changed it.** They would appear in `git status` the first
time the editor or the OS creates them, and would end up in commits by
accident.

### Compared to your old code

The old project at `C:\Users\hp\Desktop\zip` has **no `.gitignore` at all**. I
listed the folder: beside `app/` and `alembic/` it contains a real `.env`, a
`__pycache__/` folder, `alembic.ini`, `reqiurements.txt` and one git-related
file, `.gitattributes`, whose whole content is:

```text
# Auto detect text files and perform LF normalization
* text=auto
```

That file does a different job: it tells git to store text files with Unix
line endings (`LF`) even when Windows editors save them with `CRLF`, so diffs
do not fill up with line-ending changes. It is useful, but it does not ignore
anything. The new project does not have one; that is fine, it is optional.

The consequence of the missing `.gitignore` is important and worth saying
plainly, without blame: if you ran `git add .` in that folder, your PostgreSQL
password and your JWT `SECRET_KEY` from `.env` would have been committed,
together with every `__pycache__` folder. Deleting them in a later commit does
not help; git keeps the full history. If that repository was ever pushed, the
safe move is to change the PostgreSQL password and generate a new
`SECRET_KEY`.

The new `.gitignore` fixes this with its very first pattern and adds the
standard Python, venv, cache, database and editor rules so the problem cannot
come back in a different shape.

### Key terms in this file

| Term                 | One-line meaning                                                                 |
| -------------------- | -------------------------------------------------------------------------------- |
| `.gitignore`         | Git's list of name patterns that `git add` must skip                             |
| pattern              | One line of the file; a name, optionally with `*`, `[...]` or a trailing `/`     |
| trailing `/`         | The pattern matches folders only                                                 |
| `*`                  | Any run of characters                                                            |
| `[cod]`              | Exactly one character out of `c`, `o`, `d`                                       |
| `__pycache__`        | Folder of compiled modules Python creates automatically                          |
| virtual environment  | The private folder (`venv/`) where pip installs the project's libraries          |
| `.pytest_cache`      | Folder where pytest remembers the last run                                       |
| coverage             | A tool that measures which lines the tests ran; not installed here               |
| SQLite               | A database stored in one file (`.db`, `.sqlite3`); the tests use it in memory    |
| `.gitattributes`     | A different git file that controls line endings; not a replacement for `.gitignore` |

---

## Summary of this folder

The four root files form the "outer shell" of the project: none of them is
Python, and none is imported by the app, yet without them the app cannot be
installed, configured or safely shared. `requirements.txt` names the ten
libraries the API needs, each pinned with `==` to the exact version that is
installed in the venv, so every machine runs the same code; its comments
explain which library does which job (FastAPI and uvicorn to serve, SQLAlchemy,
Alembic and psycopg2 to talk to PostgreSQL, pydantic-settings to read settings,
python-jose and pwdlib for login, email-validator and python-multipart for
registration and the login form). `requirements-dev.txt` includes that list
with `-r` and adds pytest and httpx2, which only the tests need, so a server
installs less than a developer. `.env.example` documents the ten settings the
app reads; you copy it to `.env`, and `app/core/config.py` turns those lines
into the `settings` object that `session.py`, `security.py`, `main.py`,
`dependencies.py` and `alembic/env.py` all import. `.gitignore` then makes sure
that the real `.env`, the venv and the caches never reach git. Compared with
the old project, the same libraries are kept, but the requirements file name is
fixed, the settings have a committed template with defaults and correct types,
and the missing `.gitignore`, which would have leaked the old `.env`, is in
place.
