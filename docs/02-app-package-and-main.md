# app/__init__.py and app/main.py

This document explains two files:

- `app/__init__.py` - the tiny file that turns the `app/` folder into a Python *package*.
- `app/main.py` - the file that creates the FastAPI application and connects all the parts together.

Everything here was checked against the real libraries installed in this project
(Python 3.14, FastAPI 0.141.1, Starlette 1.7.0, SQLAlchemy 2.0.54). Where I show
output, it is real output that I captured, not something I guessed.

A few Python ideas appear in these files that your old project did not use much.
I explain each one at the exact place where it first appears, so you do not need to
read anything else first. Take the blocks one at a time.

---

## File: app/__init__.py

### 1. What this file is for

In Python, a folder is just a folder. Python will not let you write
`from app.core.config import settings` unless it knows that `app` is a *package*.
A **package** is a folder that Python treats as a group of modules
(a **module** is simply one `.py` file). The classic way to mark a folder as a
package is to put a file named `__init__.py` inside it.

So this file has one real job: it says "the `app/` folder is a package".
It contains no code, only a **docstring** (a text description inside triple quotes).
That docstring is a small map of the project, so anyone opening the folder for the
first time knows where to look.

Who imports it: Python runs this file automatically the first time anything does
`import app` or `from app.something import ...`. Nothing imports it on purpose, and it
imports nothing itself.

### 2. The whole file

```python
"""
app/ - The Expense Tracker backend application package.

Folder map:
    core/      -> settings, security (passwords + JWT) and shared dependencies
    database/  -> SQLAlchemy engine, session and declarative Base
    models/    -> database tables (SQLAlchemy ORM models)
    schemas/   -> request / response shapes (Pydantic models)
    routers/   -> API endpoints, one file per resource
    main.py    -> creates the FastAPI app and wires everything together
"""
```

### 3. Walkthrough, block by block

### Block 1: the docstring opens

```python
"""
app/ - The Expense Tracker backend application package.
```

- `"""` - three double quotes. In Python this starts a string that may span many lines. When such a string is the very first thing in a file, Python stores it as the file's **docstring**: a description of the file. It is not a comment (`#`); it is a real string object that Python keeps. You can read it from code with `app.__doc__`. I checked: `import app; print(app.__doc__)` prints exactly this text.
- `app/` - the name of the folder this file lives in. The trailing `/` is a common way to write "this is a folder".
- `-` - a plain dash, used as "means".
- `The Expense Tracker backend application package.` - a one-sentence description. "backend" = the server side, the part that talks to the database. "package" = the Python word for a folder of modules.

**Why it is here**

A reader who opens `app/` sees in one line what the whole folder is. Tools such as
editors and `help(app)` show this text too.

**If you removed or changed it**

Nothing would break. The folder is still a package as long as the file exists, even
if the file is empty (that is exactly what your old project had). You would only lose
the description. If you removed the *whole file*, the folder would still be
importable in modern Python (it becomes a so-called "namespace package"), but
some tools expect `__init__.py` to exist, and it is the clear, standard way to say
"this is a package". Keep the file.

### Block 2: the folder map, first half

```python
Folder map:
    core/      -> settings, security (passwords + JWT) and shared dependencies
    database/  -> SQLAlchemy engine, session and declarative Base
    models/    -> database tables (SQLAlchemy ORM models)
```

- `Folder map:` - a small heading inside the text. It says: "the lines below list the sub-folders".
- `core/` - the sub-folder `app/core/`. It holds the things every other part needs.
- `->` - here it is just an arrow drawn with two characters, meaning "contains". (In real Python code `->` has a different meaning: it marks the return type of a function. You will see that in `main.py` Block 8. Inside a docstring it is only text.)
- `settings` - the `settings` object from `app/core/config.py`. It reads values such as the database password from the `.env` file.
- `security (passwords + JWT)` - `app/core/security.py`: password hashing and JWT tokens. **JWT** = JSON Web Token, the signed string a user gets after login and sends back on every request. Your old project called this file `oauth2.py` and `utils.py`.
- `shared dependencies` - `app/core/dependencies.py`: the functions you plug in with `Depends(...)`, such as "give me the logged-in user".
- `database/` - the sub-folder with the SQLAlchemy connection code.
- `SQLAlchemy engine` - the object that owns the pool of connections to PostgreSQL. **SQLAlchemy** is the library that turns Python objects into SQL.
- `session` - a `Session` is one unit of work with the database: you add objects, query, commit. `get_db` hands one session to each request.
- `declarative Base` - the class all table classes inherit from. Your old project had `Base = declarative_base()` in `database.py`; the new one has it in `app/database/base.py`.
- `models/` - the sub-folder with one file per table.
- `database tables (SQLAlchemy ORM models)` - **ORM** = Object Relational Mapper: a Python class stands for a table, an object stands for a row. "models" here means those classes, the same idea as your old `model.py`.

**Why it is here**

New readers (including you in six months) find the right folder without opening
every file.

**If you removed or changed it**

Nothing in the program changes. It is documentation only. If you rename a folder
later, update this map so it does not lie.

### Block 3: the folder map, second half, and the docstring closes

```python
    schemas/   -> request / response shapes (Pydantic models)
    routers/   -> API endpoints, one file per resource
    main.py    -> creates the FastAPI app and wires everything together
"""
```

- `schemas/` - the sub-folder with the Pydantic classes.
- `request / response shapes` - what JSON the client may send in, and what JSON the API sends back. Your old `schema.py` had these as one file; the new project has one file per topic.
- `(Pydantic models)` - **Pydantic** is the library behind `BaseModel`. Confusingly, Pydantic also calls its classes "models". So: *SQLAlchemy model* = a database table; *Pydantic model* = a JSON shape with validation. The docstring tells you which one each folder means.
- `routers/` - the sub-folder with the endpoints.
- `API endpoints, one file per resource` - an **endpoint** is one URL + method, such as `GET /health`. A **resource** is one kind of thing the API manages: users, categories, expenses. One file each.
- `main.py` - the file explained in the second half of this document.
- `creates the FastAPI app and wires everything together` - builds the `app` object and plugs the routers, settings and startup check into it.
- `"""` - closes the docstring that Block 1 opened.

**Why it is here**

Same reason as Block 2: a map. The last line also tells you where to start reading.

**If you removed or changed it**

No change in behaviour. Only the description gets shorter. Do not forget the closing
`"""` though: without it Python sees an unfinished string and the whole `app` package
fails to import with `SyntaxError: unterminated triple-quoted string literal`.

### 4. Compared to your old code

Your old project also had `app/__init__.py`, but it was **empty** (0 bytes). That is
completely valid Python. It did its one job: it made `app` a package so that
`from app.database import get_db` worked.

Your old `app/routers/` folder had **no** `__init__.py` at all. Your imports such as
`from app.routers import post, user, auth` still worked, because modern Python can
treat a folder without `__init__.py` as a "namespace package". So this was not a bug.
It is, however, a small inconsistency: one folder marked as a package, one not. The new
project puts an `__init__.py` with a docstring in every folder (`app/`, `app/core/`,
`app/database/`, `app/models/`, `app/schemas/`, `app/routers/`). Two reasons:

1. **Consistency.** Every folder is marked the same way. Nobody has to wonder why one folder is different.
2. **Documentation.** Each `__init__.py` describes its folder. In a project with 20+ files this saves time.

In short: your empty file was correct. The new file is the same thing plus a map.

### 5. Key terms in this file

| Term | One-line meaning |
| --- | --- |
| module | One `.py` file. |
| package | A folder of modules that Python can import from; marked by `__init__.py`. |
| `__init__.py` | The file that marks a folder as a package; runs when the package is first imported. |
| docstring | A string in triple quotes at the top of a file, class or function; it describes the thing and is stored as `__doc__`. |
| namespace package | A folder without `__init__.py` that Python can still import; works, but less explicit. |
| SQLAlchemy model | A Python class that stands for a database table. |
| Pydantic model | A Python class that describes a JSON shape and validates it. |
| endpoint | One URL and one HTTP method handled by one function. |
| resource | One kind of thing the API manages (users, categories, expenses). |
| JWT | JSON Web Token: the signed token a client sends to prove who it is. |

---

## File: app/main.py

### 1. What this file is for

This is the entry point of the backend. It builds the one `app` object that the web
server (uvicorn) runs. Building the app means four things:

1. set up logging, so messages from the app are printed with a time and a level;
2. define what happens at startup (check that the database answers) and at shutdown;
3. create the `FastAPI` object with a title, version and description;
4. attach CORS (so a browser frontend may call the API) and attach every router under
   the `/api/v1` prefix (except `/health`, which stays at the root).

Who imports it: uvicorn loads it when you start the server (`app.main:app` means
"module `app.main`, variable `app`"). The tests also import `app` from here.

What it imports: `settings` from `app/core/config.py`, `check_database_connection`
from `app/database/session.py`, and the six router modules from `app/routers/`.
Nothing inside `app/` imports `main.py`; it sits at the top of the import tree.

### 2. The whole file

```python
"""
Application entry point: creates the FastAPI app and wires everything together.

Run locally with:
    uvicorn app.main:app --reload

Interactive API docs: http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import check_database_connection
from app.routers import auth, categories, expenses, health, reports, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: fail fast if the database is unreachable instead
    # of starting an API where every request would error.
    check_database_connection()
    logger.info("Database connection established")
    yield
    # Code after `yield` runs once at shutdown.


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Track your expenses, organise them by category and see where your money goes.",
    lifespan=lifespan,
)

# Lets browser frontends on the listed origins call this API.
# Tables are created by Alembic migrations (`alembic upgrade head`), not here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# /health stays unversioned; everything else lives under /api/v1.
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(categories.router, prefix=settings.API_V1_PREFIX)
app.include_router(expenses.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
```

### 3. Walkthrough, block by block

### Block 1: the docstring opens

```python
"""
Application entry point: creates the FastAPI app and wires everything together.
```

- `"""` - opens the module docstring, the same idea as in `app/__init__.py`. Python stores this text as `app.main.__doc__`.
- `Application entry point` - the place where the program starts. For a web app, "starts" means: the file the server loads to get the `app` object.
- `creates the FastAPI app` - the `app = FastAPI(...)` line further down.
- `wires everything together` - plugs in the startup check, CORS and the routers. "Wiring" is a common word for connecting parts that were written separately.

**Why it is here**

Tells a new reader "start here" and sums up the file in one sentence.

**If you removed or changed it**

No behaviour change. Only the description disappears.

### Block 2: the docstring continues and closes

```python
Run locally with:
    uvicorn app.main:app --reload

Interactive API docs: http://127.0.0.1:8000/docs
"""
```

- `Run locally with:` - introduces the command below. ("locally" = on your own machine.)
- `uvicorn` - the name of the web server program. FastAPI itself does not listen on a port; uvicorn does, and it hands each request to the `app` object.
- `app.main:app` - the thing uvicorn should load. Before the colon: the module path `app.main` (folder `app`, file `main.py`). After the colon: the variable name `app` inside that file. This is why the variable is called `app` and why it must be at the top level of the file.
- `--reload` - a uvicorn option: restart automatically when a source file changes. For development only.
- `Interactive API docs:` - FastAPI builds a web page that lists every endpoint and lets you try them.
- `http://127.0.0.1:8000/docs` - the address of that page. `127.0.0.1` is "this computer", `8000` is uvicorn's default port, `/docs` is the route FastAPI adds for the Swagger UI page. I checked: the app really registers `/docs`, `/redoc` and `/openapi.json` on its own.
- `"""` - closes the docstring.

**Why it is here**

The two things a new developer asks first ("how do I start it?" and "where do I see
the endpoints?") are answered at the top of the entry file.

**If you removed or changed it**

No behaviour change. As in Block 3 of `__init__.py`: keep the closing `"""`, or the
file fails with a `SyntaxError` and uvicorn cannot start.

### Block 3: standard-library imports

```python
import logging
from contextlib import asynccontextmanager
```

- `import` - the Python keyword that loads a module and gives you a name for it.
- `logging` - a module from Python's standard library (nothing to install). It is the official way to print messages with a time stamp, a level (INFO, WARNING, ERROR...) and the name of the file that sent them. Think of it as `print()` with structure and an on/off switch.
- `from ... import ...` - loads one specific name out of a module, so you can write `asynccontextmanager` instead of `contextlib.asynccontextmanager`.
- `contextlib` - another standard-library module. It holds helpers for **context managers**. A context manager is any object you can use with the `with` keyword: `with open("f.txt") as f:` is the one everybody knows. `with` means "do some setup, run my block, then always do the cleanup, even if my block crashed".
- `asynccontextmanager` - a **decorator** (explained at Block 8) from `contextlib` that turns a simple function containing `yield` into an *async* context manager. "async" means it works inside `async with`, which is what FastAPI needs for startup/shutdown. We will see exactly how in Block 8.

**Why it is here**

`logging` is needed for `basicConfig` and `getLogger` in Blocks 6-7.
`asynccontextmanager` is needed for the `lifespan` function in Block 8.

**If you removed or changed it**

Remove `import logging` and the file dies at Block 6 with
`NameError: name 'logging' is not defined`. Remove the `contextlib` import and it dies
at Block 8 with `NameError: name 'asynccontextmanager' is not defined`. Both errors
happen while uvicorn is importing the file, so the server never starts.

### Block 4: FastAPI imports

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
```

- `fastapi` - the web framework. Installed from `requirements.txt`.
- `FastAPI` - the class you create the application from. `app = FastAPI(...)` gives you the object that knows all the routes. You used the same import in your old `main.py`.
- `fastapi.middleware.cors` - a sub-module of FastAPI. **Middleware** is code that sits between the server and your endpoint functions. Every request passes through it on the way in, and every response passes through it on the way out. "cors" is one specific middleware for browsers (explained fully at Block 14).
- `CORSMiddleware` - the class for that middleware. (Small fact: FastAPI only re-exports it; the real code lives in the Starlette library that FastAPI is built on. I read that code to write Block 14.)

**Why it is here**

`FastAPI` is used at Block 11; `CORSMiddleware` at Block 14.

**If you removed or changed it**

`NameError` at the first use, at import time. No server.

### Block 5: imports from this project

```python
from app.core.config import settings
from app.database.session import check_database_connection
from app.routers import auth, categories, expenses, health, reports, users
```

- `app.core.config` - the file `app/core/config.py`. The dots walk the folders: package `app`, sub-package `core`, module `config`.
- `settings` - the one ready-made `Settings()` object created at the bottom of that file. It holds `APP_NAME`, `APP_VERSION`, `API_V1_PREFIX`, the CORS list and so on, read from your `.env` file. (Doc 03 explains that file word by word.) Importing it here also *runs* `config.py` once, which is when the `.env` file is read. If `SECRET_KEY` is missing, that import raises a Pydantic `ValidationError` and this file never gets past this line. I confirmed that by importing with `SECRET_KEY` unset.
- `app.database.session` - the file `app/database/session.py`. Importing it creates the SQLAlchemy `engine` (the connection pool). Note: creating the engine does **not** open a connection yet; SQLAlchemy connects lazily, on first use.
- `check_database_connection` - a small function from that file. It opens a connection and runs `SELECT 1`. If PostgreSQL is unreachable it raises an exception. Used at Block 9.
- `app.routers` - the package `app/routers/`. Because that folder has an `__init__.py`, Python knows it is a package and lets you import modules out of it.
- `auth, categories, expenses, health, reports, users` - six *modules*: `auth.py`, `categories.py`, and so on. Each one defines a variable named `router` (an `APIRouter`). We attach those routers at Blocks 16-18. The names are in alphabetical order simply for tidiness.

**Why it is here**

These are the three kinds of things `main.py` needs: configuration values, the
startup check, and the endpoints to publish.

**If you removed or changed it**

- Without `settings`: `NameError` at Block 11.
- Without `check_database_connection`: `NameError` at Block 9, but only *when the lifespan runs*, so uvicorn would load the file and then fail at startup with "Application startup failed. Exiting."
- Without one router module, say `reports`: `NameError` at Block 18. If you kept the import but forgot the `include_router` line, there would be no error at all; the `/api/v1/reports/...` URLs would simply not exist and return `404 Not Found`. That silent failure is why each router gets its own clear line.

### Block 6: logging.basicConfig

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
```

- `logging.basicConfig(...)` - a function in the `logging` module that sets up the **root logger** in one call. Loggers form a tree: every logger you create (such as `app.main`) has the root logger as its ancestor, and by default passes its messages up to the root. So configuring the root once configures printing for the whole program. The call does two things: it sets the root level, and it attaches a **handler** (the thing that actually writes text) that prints to **stderr** (the terminal's error stream; it looks like normal terminal output). I checked: after this call `logging.getLogger().handlers` is `[<StreamHandler <stderr>>]`.
- `level=logging.INFO` - the **level** is the minimum importance that gets printed. The levels, lowest to highest, with their numbers: `DEBUG`=10, `INFO`=20, `WARNING`=30, `ERROR`=40, `CRITICAL`=50. Setting `INFO` means: print INFO and everything above it, hide DEBUG. `logging.INFO` is just the constant `20`.
- `format=` - a template for every printed line. The `%(...)s` pieces are placeholders that `logging` fills in:
  - `%(asctime)s` - the date and time, e.g. `2026-10-06 17:08:20,069` (the number after the comma is milliseconds).
  - `%(levelname)s` - the level as a word: `INFO`, `WARNING`...
  - `%(name)s` - the name of the logger that sent the message, e.g. `app.main`. This tells you which file the line came from.
  - `%(message)s` - the text you passed, e.g. `Database connection established`.
  - ` | ` - plain separators to keep the columns readable.
- A real line produced by this format (I captured it):
  `2026-10-06 17:08:20,069 | INFO | app.main | Database connection established`

Two facts about `basicConfig` that matter:

1. **It only works once.** If the root logger already has handlers, `basicConfig` does nothing and returns silently. I tested calling it a second time with a different level and format: ignored. So whoever calls it first wins. In this project that is `main.py`, which is imported before anything else runs.
2. **It does not touch uvicorn's own lines.** Uvicorn configures its loggers `uvicorn` and `uvicorn.access` with `propagate: False` (I read this in uvicorn's `config.py`), meaning their messages are *not* passed up to the root. So you will see uvicorn's lines in uvicorn's style and your app's lines in this style, with no duplicates.

**Why it is here**

So that `logger.info(...)` lines from any file in the project are actually printed,
with a time stamp and the file name. It replaces `print()` with something you can
turn down to `WARNING` in production without deleting lines.

**If you removed or changed it**

- Removed: the root logger keeps its default level, `WARNING`, and has no handler. Then `logger.info("Database connection established")` prints **nothing**. I tested this. `logger.warning(...)` would still print, but as bare text with no time, because Python has a "last resort" handler for WARNING and above.
- `level=logging.DEBUG`: you would also see DEBUG lines from every library (SQLAlchemy, httpx...). Noisy, but useful for a day of debugging.
- Different `format`: only the look of each line changes.

### Block 7: the module's logger

```python
logger = logging.getLogger(__name__)
```

- `logger` - a module-level variable, our handle for writing log lines from this file.
- `logging.getLogger(...)` - asks the `logging` module for the logger with the given name. If it does not exist yet, it is created; if it exists, the same object is returned. So two files that use the same name share one logger.
- `__name__` - a variable Python sets automatically in every module: the module's full dotted name. In this file it is the string `"app.main"` (I printed it to be sure). That name is what appears in the `%(name)s` column. Using `__name__` instead of typing `"app.main"` means the name stays correct if you ever rename the file.

**Why it is here**

Every file in the project does the same two lines (`getLogger(__name__)`), so each
log line tells you where it came from.

**If you removed or changed it**

Block 9 would fail with `NameError: name 'logger' is not defined` at startup. If you
replaced `__name__` with a fixed string, logging would still work, only the label
would differ. If you used `print()` instead, you would lose the time stamp and the
level, and you could not silence it later.

### Block 8: the lifespan function begins

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
```

This block uses three Python ideas you may not have met: decorators, `async`, and
type hints on parameters. One at a time.

- `@` - the **decorator** symbol. A decorator is a function that takes the function written right below it, and gives back a changed version. `@something` on the line above `def f` means exactly `f = something(f)`. Nothing more magical than that. You already used decorators: `@router.get("/")` is one.
- `asynccontextmanager` - the decorator imported at Block 3. It takes a function that contains a `yield` and returns a function that, when called, gives you an *async context manager*: an object usable with `async with`. FastAPI will do `async with lifespan(app):` for us. Everything **before** `yield` runs when the `with` block is entered (startup). Everything **after** `yield` runs when the `with` block is left (shutdown).
- `async def` - defines an **asynchronous** function (a "coroutine"). FastAPI and uvicorn are built on `asyncio`, Python's system for handling many connections at once without threads. An `async def` function can pause (`await ...`) and let other work run while it waits. FastAPI requires the lifespan function to be `async def`; a plain `def` here would not be accepted as an async context manager.
- `lifespan` - the function name. "Lifespan" is the ASGI word for "the life of the server process: startup, then serving, then shutdown". Any name would work; `lifespan` matches the FastAPI argument name at Block 12.
- `(app: FastAPI)` - one parameter named `app`. FastAPI calls `lifespan(app)` and passes in the application object (I checked this in Starlette's `routing.py`: `async with self.lifespan_context(app)`). The function does not use it, but the parameter must be there because FastAPI always passes it.
- `: FastAPI` - a **type hint**. The colon after a parameter name, followed by a type, tells readers and tools "this is a `FastAPI` object". Python does not enforce it at run time; it is documentation that editors can check. You will see `name: type` on parameters and `-> type` for return values all over the new project.
- `:` at the end of the line - starts the function body, as always.

**Why it is here**

This is where the project says "before you accept any request, do X; after the last
request, do Y". It replaces the older `@app.on_event("startup")` style, which FastAPI
has deprecated.

**If you removed or changed it**

- No `@asynccontextmanager`: in the installed FastAPI version this still works and prints no warning, because FastAPI quietly wraps a plain `async` generator for you. But Starlette's own source calls this form deprecated, so a future version may refuse it. Keep the decorator; it is the documented form.
- `def` instead of `async def` (keeping the decorator): startup fails with `TypeError: 'generator' object is not an async iterator`, because `asynccontextmanager` expects an *async* generator. I tested this. The documented contract is `async def`.
- Drop the `app` parameter: `TypeError: lifespan() takes 0 positional arguments but 1 was given` at startup, and uvicorn exits.

### Block 9: startup work

```python
    # Runs once at startup: fail fast if the database is unreachable instead
    # of starting an API where every request would error.
    check_database_connection()
    logger.info("Database connection established")
```

- `# Runs once at startup: ...` - the two comment lines tell you *when* this code runs (once, at startup) and *why* (to fail fast). "Fail fast" means: if something is wrong, stop immediately with a clear error, rather than starting and failing on every request later.
- `check_database_connection()` - calls the function imported at Block 5. It opens a real connection and runs `SELECT 1`. If PostgreSQL is down, the password is wrong, or the host is unreachable, it raises `sqlalchemy.exc.OperationalError`. I tested with a port where nothing listens: the exception message starts with `(psycopg2.OperationalError) connection to server at "127.0.0.1", port 1 failed: Connection refused`. Because this happens *inside* `lifespan` before `yield`, FastAPI reports "startup failed" and uvicorn logs `Application startup failed. Exiting.` and stops. No half-working server.
- `logger.info(...)` - sends an INFO-level message through our logger from Block 7. Because of Block 6 it is printed as `... | INFO | app.main | Database connection established`.
- `"Database connection established"` - the message text.

**Why it is here**

With a bad `.env` you find out in the first second, with a readable error, instead of
seeing a `500` on every endpoint and digging through request logs.

**If you removed or changed it**

- Remove `check_database_connection()`: the server starts even with a dead database. Every endpoint that touches the DB returns `500 Internal Server Error`. Only `/health` would tell you the truth, because it runs its own check.
- Remove the `logger.info` line: no behaviour change; you just lose the reassuring line in the terminal.

### Block 10: the yield, and shutdown

```python
    yield
    # Code after `yield` runs once at shutdown.
```

- `yield` - the keyword that makes this function a **generator**. A normal function runs to the end and `return`s once. A generator function pauses at `yield`, hands control back to the caller, and later *resumes from the same spot* when the caller asks for the next step. With `@asynccontextmanager`, FastAPI uses that pause like this:
  1. call `lifespan(app)` and run it until `yield` - this is **startup** (Block 9);
  2. while paused, serve all HTTP requests, for hours or days;
  3. when the server is told to stop (Ctrl+C, or a deploy), resume after `yield` - this is **shutdown**;
  4. when the function reaches its end, shutdown is complete.
  Exactly one `yield` must exist; two would raise `RuntimeError: generator didn't stop`.
- `# Code after `yield` runs once at shutdown.` - a comment pointing out that this project currently has nothing to do at shutdown. If one day you need to close a cache or a message queue, that code goes under this comment.

A timeline of the whole lifespan, as I verified it with a test client that enters
and leaves the app:

```
server starts
  -> lifespan() runs up to `yield`      (check_database_connection, log line)
  -> "Application startup complete."
  -> requests are served ...
server is asked to stop
  -> lifespan() resumes after `yield`   (currently nothing)
  -> "Application shutdown complete."
```

One subtle point you will meet in `tests/conftest.py`: the lifespan only runs when
the server (or a `TestClient`) *enters* the app, as in `with TestClient(app)`. Simply
creating `TestClient(app)` without `with` does not run it. That is why no startup
check against PostgreSQL happens during tests.

**Why it is here**

`yield` is the dividing line between "before serving" and "after serving".

**If you removed or changed it**

Without `yield`, the function is no longer a generator; it is an ordinary coroutine.
Startup then fails with `TypeError: 'coroutine' object is not an async iterator`
(I tested it). With two `yield`s, startup works but shutdown fails with
`RuntimeError: generator didn't stop`. Either way: exactly one `yield`.

### Block 11: creating the app, first half

```python
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
```

- `app` - the module-level variable that uvicorn looks for (`app.main:app`). It must be called `app` *because* the start command names it so.
- `FastAPI(` - creates the application object. Note: all of its arguments are **keyword-only**. I checked: `FastAPI("Post")` raises `TypeError: FastAPI.__init__() takes 1 positional argument but 2 were given`. You must write `title="..."`.
- `title=` - the name shown at the top of the `/docs` page and in the OpenAPI schema. The **OpenAPI schema** is the JSON description of the API (at `/openapi.json`) that the docs page is built from.
- `settings.APP_NAME` - read from the settings object. Its default is `"Expense Tracker API"`; you can override it in `.env` with `APP_NAME=...`. I printed `app.title` and got `Expense Tracker API`.
- `version=` - the API version string shown next to the title in the docs.
- `settings.APP_VERSION` - default `"1.0.0"`.

**Why it is here**

Title and version come from `settings` so that they live in one place, next to every
other configurable value, instead of being typed into `main.py`.

**If you removed or changed it**

- Rename the variable from `app` to anything else: uvicorn fails with `Attribute "app" not found in module "app.main"`.
- Drop `title`: FastAPI uses the default title `"FastAPI"`. Only cosmetics.
- Drop `version`: default `"0.1.0"`. Only cosmetics.

### Block 12: creating the app, second half

```python
    description="Track your expenses, organise them by category and see where your money goes.",
    lifespan=lifespan,
)
```

- `description=` - a paragraph shown under the title on the `/docs` page. Plain text (Markdown is allowed).
- `"Track your expenses, ..."` - the text itself. It is hard-coded here instead of in settings because nobody needs to change it per environment.
- `lifespan=` - the argument that tells FastAPI which function to run at startup and shutdown.
- `lifespan` (the value) - the function defined at Block 8. Note: no parentheses. We pass the function itself, not the result of calling it. FastAPI calls it later, at the right moment, with the app as argument.
- `)` - closes the `FastAPI(` call that started at Block 11.

**Why it is here**

`description` makes the docs page self-explaining. `lifespan` is what connects the
startup check to the app; without this line Block 8-10 would be dead code.

**If you removed or changed it**

- Remove `lifespan=lifespan`: the function is never called. No database check at startup; the app starts even with a wrong password.
- Write `lifespan=lifespan()` by mistake: you would pass the *result* of calling it with no argument, which raises `TypeError: lifespan() missing 1 required positional argument: 'app'` at import time.

### Block 13: two explanatory comments

```python
# Lets browser frontends on the listed origins call this API.
# Tables are created by Alembic migrations (`alembic upgrade head`), not here.
```

- `# Lets browser frontends on the listed origins call this API.` - explains the purpose of the middleware block below. "Browser frontends" = a React, Vue or plain-JavaScript site running in a browser. "Origins" = a scheme + host + port, such as `http://localhost:3000` (explained in Block 14). "Listed" = the ones you put in `CORS_ALLOWED_ORIGINS` in `.env`.
- `# Tables are created by Alembic migrations ..., not here.` - a note for people who, like your old `main.py`, expect to see `Base.metadata.create_all(bind=engine)` in this file. In the new project, tables are created and changed by **Alembic**, the migration tool (doc 10 explains it). `alembic upgrade head` is the command that applies all migrations. This comment prevents someone from "helpfully" adding `create_all` back.

**Why it is here**

Both comments answer questions a reader would otherwise ask: "why is there CORS?" and
"where are the tables created?".

**If you removed or changed it**

Nothing changes in behaviour. Comments are ignored by Python.

### Block 14: CORS middleware, first half

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
```

Before the bullets, the idea behind CORS in plain words.

A browser enforces a rule called the **same-origin policy**: JavaScript running on
page A may not read responses from server B unless B says it is fine. An **origin** is
the trio *scheme + host + port*: `http://localhost:3000` and `http://localhost:8000`
are two *different* origins because the port differs. So a React dev server on port
3000 calling your API on port 8000 is a cross-origin call, and the browser blocks the
response by default.

**CORS** (Cross-Origin Resource Sharing) is the mechanism by which server B says "I
allow origin A". It works with HTTP headers:

- For "simple" requests (a plain `GET`, for example), the browser sends the request with an `Origin` header; the server answers normally but adds `Access-Control-Allow-Origin: <origin>` if it allows it. The browser then lets the page read the response.
- For anything else (a `POST` with JSON, a `PATCH`, a request with an `Authorization` header), the browser first sends a **preflight**: an `OPTIONS` request asking "may I send a `POST` with these headers from this origin?". The server answers with `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers` and so on. Only if the answer is good does the browser send the real request.

Important: this only concerns **browsers**. Postman, `curl`, the Swagger page at
`/docs` (same origin as the API) and the tests are not affected. I confirmed that a
request with no `Origin` header gets no CORS headers at all and is served normally.

Now the words:

- `app.add_middleware(` - a method of the app that registers a middleware class. The middleware wraps the whole application, so every request and response goes through it. Note that FastAPI raises `RuntimeError: Cannot add middleware after an application has started`, so this must be done at import time, as here.
- `CORSMiddleware` - the class from Block 4. You pass the class, not an instance; FastAPI creates the instance with the keyword arguments that follow.
- `allow_origins=` - the list of origins that are allowed to call the API from a browser. Matching is exact string matching (`origin in self.allow_origins` in Starlette's code), so `http://localhost:3000` does not match `http://localhost:3000/` or `https://localhost:3000`.
- `settings.cors_allowed_origins_list` - a `@property` on `Settings` (doc 03) that takes the comma-separated `CORS_ALLOWED_ORIGINS` string from `.env` and turns it into a clean Python list, with spaces stripped and empty items dropped. With `.env.example`'s value it becomes `['http://localhost:3000', 'http://localhost:5173']` (I printed it). With the default empty string it becomes `[]`, which means "no browser origin is allowed".

**Why it is here**

Without it, any frontend served from a different origin would get its requests
blocked by the browser (the classic red "CORS policy" error in the console). Reading
the list from `.env` means production can allow `https://myapp.com` and development
can allow `http://localhost:3000` without changing code.

**If you removed or changed it**

- Remove the whole middleware: no `Access-Control-*` headers ever. Postman keeps working; every browser frontend on another origin breaks.
- `allow_origins=["*"]` (allow everyone): works, but combined with `allow_credentials=True` (next block) Starlette must echo back the exact origin instead of `*`, and you have effectively told every website in the world it may send credentialed requests to your API. Do not do this in production.
- Leave `CORS_ALLOWED_ORIGINS` empty: I tested it. A browser preflight from `http://localhost:3000` gets `400 Disallowed CORS origin`; the API is still fine for non-browser clients.

### Block 15: CORS middleware, second half

```python
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- `allow_credentials=` - whether the browser may include **credentials** (cookies, or the `Authorization` header when the frontend uses `credentials: "include"`) in cross-origin requests. Starlette's default is `False`.
- `True` - yes. The middleware then adds `Access-Control-Allow-Credentials: true` to responses, and in preflight answers it echoes the *exact* requesting origin in `Access-Control-Allow-Origin` (the browser refuses `*` when credentials are on). This project uses the `Authorization: Bearer <token>` header for login, so this is needed for the common frontend setups.
- `allow_methods=` - which HTTP methods a browser may use cross-origin. Starlette's default is only `("GET",)`.
- `["*"]` - a list with the single string `"*"`, meaning "all". I read in Starlette's code: if `"*"` is in the list it is replaced by the full set `DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, QUERY`. Our API uses `GET`, `POST`, `PATCH` and `DELETE`, so anything narrower than that would break some endpoints from a browser.
- `allow_headers=` - which request headers a browser may send cross-origin, beyond the few that are always allowed (`Accept`, `Accept-Language`, `Content-Language`, `Content-Type`). Starlette's default is `()` (none extra).
- `["*"]` - all. In practice, with `"*"` Starlette mirrors back whatever the browser asked for in `Access-Control-Request-Headers`. The one header we really need is `Authorization`, which is *not* in the always-allowed set, so without this a logged-in frontend could not call any protected endpoint.
- `)` - closes `add_middleware(`.

Here is what the middleware really answered when I sent a preflight from an allowed
origin (`Origin: http://localhost:3000`, asking for `POST` with
`authorization,content-type`):

```
200 OK
access-control-allow-origin: http://localhost:3000
access-control-allow-credentials: true
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, QUERY
access-control-allow-headers: authorization,content-type
access-control-max-age: 600
```

and from a not-allowed origin (`Origin: http://evil.com`):

```
400 Disallowed CORS origin
```

`max-age: 600` means the browser may remember this preflight answer for 600 seconds
(10 minutes) and skip asking again; it is Starlette's default.

**Why it is here**

These three lines are what a token-based JSON API needs for a browser frontend:
credentials on, every method, every header. Origins are the part that is kept strict.

**If you removed or changed it**

- `allow_credentials=False`: frontends that send cookies or use `credentials: "include"` get blocked; plain `fetch` with an `Authorization` header and no `credentials` option would still pass, because that header is covered by `allow_headers`.
- `allow_methods=["GET", "POST"]`: `PATCH /api/v1/expenses/{id}` and `DELETE` would fail their preflight with `400 Disallowed CORS method` in browsers.
- `allow_headers=[]`: a browser sending `Authorization` would fail preflight with `400 Disallowed CORS headers`; every protected endpoint becomes unusable from a frontend.

### Block 16: the health router, with no prefix

```python
# /health stays unversioned; everything else lives under /api/v1.
app.include_router(health.router)
```

- `# /health stays unversioned; ...` - a comment that explains the odd one out: why the next line has no `prefix` while the five after it do. "Unversioned" = not under `/api/v1`.
- `app.include_router(` - a method of the app that takes an `APIRouter` and copies all of its routes into the app. You used this in your old `main.py` too.
- `health` - the module `app/routers/health.py`, imported at Block 5.
- `.router` - the `APIRouter` object defined inside that module (`router = APIRouter(tags=["Health"])`). The dot reaches into the module to get the variable.
- no `prefix=` argument - so the router's own paths are used as they are. `health.py` declares `@router.get("/health")`, and the router itself has no prefix, so the final URL is exactly `/health`.
- `)` - closes the call.

**Why it is here**

Uptime monitors, load balancers and container platforms are usually configured once
with a fixed URL such as `/health`. If the API moves from `v1` to `v2` one day, that
URL should not move with it. So it is deliberately kept outside the versioned prefix.

**If you removed or changed it**

- Remove the line: `GET /health` returns `404 Not Found`. Any monitor pointed at it starts reporting the API as down.
- Add `prefix=settings.API_V1_PREFIX`: the URL becomes `/api/v1/health`. Works, but every external check must be reconfigured.

### Block 17: auth and users routers, under /api/v1

```python
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
```

- `auth.router` - the `APIRouter(prefix="/auth", tags=["Authentication"])` from `app/routers/auth.py`.
- `users.router` - the `APIRouter(prefix="/users", tags=["Users"])` from `app/routers/users.py`.
- `prefix=` - an argument of `include_router`: a string put in front of every path in that router.
- `settings.API_V1_PREFIX` - from settings, default `"/api/v1"` (I printed it). The `v1` is an **API version**: if the API ever changes in a way that breaks old clients, a new set of routers can be mounted under `/api/v2` while `/api/v1` keeps serving the old clients.

**How the final URL is built**

There are three pieces of path, and FastAPI simply joins them with string
concatenation (in FastAPI's `routing.py` it is literally `self.prefix + route.path`):

```
include_router prefix  +  APIRouter prefix  +  path in the decorator  =  final URL
"/api/v1"              +  "/auth"           +  "/register"            =  "/api/v1/auth/register"
"/api/v1"              +  "/auth"           +  "/login"               =  "/api/v1/auth/login"
"/api/v1"              +  "/users"          +  "/me"                  =  "/api/v1/users/me"
```

Because it is plain concatenation, FastAPI enforces two rules on each prefix, and I
triggered both to see the exact messages:

- it must start with `/`: `prefix="api/v1"` raises `AssertionError: A path prefix must start with '/'`;
- it must not end with `/`: `prefix="/api/v1/"` raises `AssertionError: A path prefix must not end with '/', as the routes will start with '/'`.

Both errors happen at import time, so uvicorn refuses to start, which is what you
want: a wrong prefix is found in one second, not after a deploy.

`tags` (`"Authentication"`, `"Users"`) are not part of the URL. They only group the
endpoints under headings on the `/docs` page.

**Why it is here**

Putting the prefix in `include_router` (instead of writing `/api/v1/auth` inside each
router file) means the router files do not know or care where they are mounted. The
prefix is written once, in settings, and applied here.

**If you removed or changed it**

- Remove `prefix=...` on one line: that router's URLs move to the root, e.g. `/auth/login` instead of `/api/v1/auth/login`. Every client that uses the documented URL gets `404`.
- Change `API_V1_PREFIX` in `.env` to `/api`: every URL moves at once, which is exactly the point of keeping it in one place.
- Swap the order of the two lines: no effect here, because no two routes have the same path. (FastAPI matches routes in the order they were added, so order would matter only if two routers claimed the same URL.)

### Block 18: categories, expenses and reports routers

```python
app.include_router(categories.router, prefix=settings.API_V1_PREFIX)
app.include_router(expenses.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
```

- `categories.router` - `APIRouter(prefix="/categories", tags=["Categories"])`.
- `expenses.router` - `APIRouter(prefix="/expenses", tags=["Expenses"])`.
- `reports.router` - `APIRouter(prefix="/reports", tags=["Reports"])`.
- `prefix=settings.API_V1_PREFIX` - the same `/api/v1` as in Block 17.

One detail you will notice in the table below: `/api/v1/categories` has **no trailing
slash**. That is because `categories.py` declares its list endpoint with the path
`""` (empty), not `"/"`. `"/api/v1" + "/categories" + ""` gives `/api/v1/categories`.
Doc 08 explains each router file; here it is enough to know that the final URL is
always the three pieces glued together.

**The full URL table, as the app really registers it**

I generated this from the app's own OpenAPI schema (`app.openapi()["paths"]`), so it
is the truth, not a guess:

| Final URL | Methods | Tag (docs heading) | Comes from |
| --- | --- | --- | --- |
| `/health` | GET | Health | Block 16, no prefix |
| `/api/v1/auth/register` | POST | Authentication | Block 17 |
| `/api/v1/auth/login` | POST | Authentication | Block 17 |
| `/api/v1/users/me` | GET | Users | Block 17 |
| `/api/v1/categories` | GET, POST | Categories | Block 18 |
| `/api/v1/categories/{category_id}` | GET, PATCH, DELETE | Categories | Block 18 |
| `/api/v1/expenses` | GET, POST | Expenses | Block 18 |
| `/api/v1/expenses/{expense_id}` | GET, PATCH, DELETE | Expenses | Block 18 |
| `/api/v1/reports/summary` | GET | Reports | Block 18 |
| `/api/v1/reports/by-category` | GET | Reports | Block 18 |
| `/api/v1/reports/monthly` | GET | Reports | Block 18 |

Plus the three pages FastAPI adds by itself: `/docs`, `/redoc` and `/openapi.json`.

**Why it is here**

These three lines publish the rest of the API. One line per router keeps it obvious
which resources exist; adding a resource later is one import plus one line.

**If you removed or changed it**

Remove any one line and that whole resource disappears with `404`s, silently: no
error at startup. If you included the same router twice, the app would hold duplicate
route objects (I tried it: the route list doubled), the first one wins for matching,
and the `/docs` page still shows each path once because the OpenAPI schema is keyed
by path. Harmless, but pointless.

### 4. Compared to your old code

Here is your old `app/main.py` in full:

```python
from fastapi import FastAPI

from contextlib import asynccontextmanager
from app.database import connect_database


from app import model
from app.database import engine
from app.routers import post, user, auth


# model.Base.metadata.create_all(bind = engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_database()
    yield

app = FastAPI(lifespan=lifespan,title="Post")

app.include_router(post.router)
app.include_router(user.router)
app.include_router(auth.router)
```

First the good news: the shape is the same. You already had an `asynccontextmanager`
lifespan with a database check before `yield`, a `FastAPI(...)` call, and
`include_router` lines. The new file is your file, grown up. Now the differences, one
by one.

**1. Imports**

Old:

```python
from app.database import connect_database
from app import model
from app.database import engine
```

- `from app.database import ...` appears twice, on two separate lines. Not an error, just untidy; one line `from app.database import connect_database, engine` would do.
- `model` and `engine` are imported but never used, because the only line that used them (`create_all`) is commented out. Python does not complain about unused imports, but a reader wonders "what is `engine` for here?" and has to search. The new file imports only what it uses.
- The new file groups imports in the standard order: standard library, third-party, then this project, with a blank line between groups. That makes it easy to see at a glance what comes from where.

**2. The commented-out `create_all`**

```python
# model.Base.metadata.create_all(bind = engine)
```

`create_all` creates any table that does not exist yet. It never *changes* an
existing table: if you add a column to a model, `create_all` does nothing, and you
get `column does not exist` errors. That is why you commented it out once you started
using Alembic. The new project does the same, but says so explicitly in a comment
(Block 13) so nobody adds it back.

**3. Startup check: `print` versus `logger`**

Old `connect_database()` in `app/database.py` ended with
`print("Database Connecting Successfully")`. The new `check_database_connection()`
prints nothing; the log line lives in `main.py` (Block 9) and goes through `logging`.
Two reasons:

- A function in `database/session.py` is also used by the `/health` endpoint. If it printed, every health check would spam the terminal. Keeping the function silent and logging at the call site gives you control.
- `logging` adds the time and the source file, and can be turned down in production. `print` cannot.

**4. `FastAPI(...)` arguments**

Old: `FastAPI(lifespan=lifespan, title="Post")`. New: `title`, `version`,
`description` from settings or a sentence, and `lifespan`. Same call, more
information on the `/docs` page, and the title lives in settings so it is not typed
into code.

**5. CORS was missing**

The old file had no `CORSMiddleware`. That was invisible as long as you tested with
Swagger (`/docs`, same origin) or Postman (no browser). The moment a React or Vue
frontend on `localhost:3000` tried to call `localhost:8000`, every request would have
been blocked by the browser with a CORS error. The new file adds it (Blocks 14-15)
and reads the allowed origins from `.env`.

**6. No URL prefix, and a trailing-slash surprise**

Old URLs were `/posts`, `/user`, `/login/`. Note the last one: the router had
`prefix="/login"` and the endpoint was `@router.post("/")`, so the final path is
`/login/` with a slash. I checked what happens to a `POST /login` without the slash:
FastAPI answers `307 Temporary Redirect` to `/login/`. A `307` tells the client to
repeat the same method and body at the new address, and browsers and most libraries
do that, so it "works". But it costs an extra round trip on every login, your docs
show the odd-looking `/login/`, and a client that does not follow redirects just sees
a `307` with no token. The new project avoids this by never using `"/"` as an
endpoint path under a prefix: it writes `"/register"`, `"/me"`, or `""`.
It also puts everything under `/api/v1`, so the API can be versioned later.

**7. No logging setup, no docstring**

The old file had no `logging.basicConfig` (nothing to configure, since it used
`print`) and no module docstring. Both are small, but together they are the
difference between a file you can hand to a colleague and one you must explain in
person.

None of these were crashes. Your old `main.py` ran. The new one does the same job
with fewer surprises for a browser frontend, for a second developer, and for
future-you.

### 5. Key terms in this file

| Term | One-line meaning |
| --- | --- |
| entry point | The file the server loads first; here, the one that owns the `app` variable. |
| uvicorn | The ASGI web server that listens on a port and hands requests to the FastAPI app. |
| `app.main:app` | uvicorn's "module:variable" notation for finding the app object. |
| logging | Python's standard module for printing messages with time, level and source name. |
| root logger | The top of the logger tree; `basicConfig` configures it once for the whole program. |
| handler | The part of logging that actually writes a line somewhere (here: the terminal). |
| level | Minimum importance to print: DEBUG < INFO < WARNING < ERROR < CRITICAL. |
| `__name__` | Automatic variable holding the module's dotted name, e.g. `app.main`. |
| decorator (`@`) | A function applied to the function below it: `@d` over `def f` means `f = d(f)`. |
| `async def` | Defines a coroutine: a function that can pause with `await` and let other work run. |
| generator / `yield` | A function that pauses at `yield` and resumes later from the same spot. |
| context manager / `with` | Setup, run a block, then guaranteed cleanup; `async with` is the async version. |
| `asynccontextmanager` | Decorator that turns an `async` generator function into an async context manager. |
| lifespan | FastAPI's startup/shutdown hook: code before `yield` runs at startup, after it at shutdown. |
| fail fast | Stop immediately with a clear error instead of running in a broken state. |
| type hint (`name: Type`) | A note about the expected type; not enforced by Python, checked by tools. |
| keyword-only argument | An argument you must pass by name (`title="..."`), not by position. |
| OpenAPI schema | The JSON description of the API that the `/docs` page is built from. |
| middleware | Code that wraps the app; every request and response passes through it. |
| origin | scheme + host + port, e.g. `http://localhost:3000`. Different port = different origin. |
| CORS | The header-based mechanism by which a server allows browsers on other origins to call it. |
| preflight | The browser's `OPTIONS` request asking permission before a non-simple cross-origin request. |
| `Authorization` header | Where the JWT travels (`Bearer <token>`); needs `allow_headers` to pass CORS. |
| `include_router` | Copies an `APIRouter`'s routes into the app, optionally under a prefix. |
| prefix | A string glued in front of every path of a router; must start with `/`, must not end with `/`. |
| API version (`/api/v1`) | A URL segment that lets old and new API versions coexist. |
| tag | A label that groups endpoints on the `/docs` page; not part of the URL. |
| Alembic migration | A versioned script that creates or alters database tables; replaces `create_all`. |

---

## Summary of this folder

`app/__init__.py` makes the `app/` folder a Python package and carries a short map of
the sub-folders, so that `from app.core.config import settings` works and a newcomer
knows where to look. `app/main.py` is the only file that pulls all of those
sub-folders together. It first configures `logging` so every file's `logger.info`
lines are printed with a time stamp and a source name. It then defines `lifespan`,
whose code before `yield` runs once at startup (the `SELECT 1` database check, which
stops the server with a clear error if PostgreSQL is unreachable) and whose code after
`yield` would run once at shutdown. It creates the `FastAPI` object with a title,
version and description taken from `settings`, and hands it the `lifespan` function.
It wraps the app in `CORSMiddleware`, reading the allowed browser origins from `.env`,
so a frontend on another port can call the API with its `Authorization` header. Finally
it publishes the routers: `/health` at the root, and `auth`, `users`, `categories`,
`expenses` and `reports` under `/api/v1`, where each final URL is simply
include-prefix + router-prefix + endpoint-path. Uvicorn loads this file by the name
`app.main:app`, so everything above runs once at import, and from then on every HTTP
request flows through the CORS middleware into the matching router function.
