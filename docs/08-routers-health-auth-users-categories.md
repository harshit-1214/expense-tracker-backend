# app/routers/ part 1: health, auth, users, categories

The `app/routers/` folder holds the **endpoints**: the functions that run when an HTTP request arrives. Every file in it builds one `router` object and attaches a few endpoint functions to it. `app/main.py` then collects all the routers into the one FastAPI app (that wiring is explained in doc 02).

This document covers the first four router files. Doc 09 covers `expenses.py` and `reports.py`.

| File                         | Router prefix   | Endpoints it defines (final URL)                                                                                                                  |
| ---------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/routers/__init__.py`    | -               | none (it only makes the folder a package and documents it)                                                                                        |
| `app/routers/health.py`      | none            | `GET /health`                                                                                                                                     |
| `app/routers/auth.py`        | `/auth`         | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`                                                                                           |
| `app/routers/users.py`       | `/users`        | `GET /api/v1/users/me`                                                                                                                            |
| `app/routers/categories.py`  | `/categories`   | `POST /api/v1/categories`, `GET /api/v1/categories`, `GET /api/v1/categories/{id}`, `PATCH /api/v1/categories/{id}`, `DELETE /api/v1/categories/{id}` |

The `/api/v1` part is not written in these files. `app/main.py` adds it when it registers each router (`app.include_router(auth.router, prefix=settings.API_V1_PREFIX)`). `/health` is registered without that prefix on purpose, so monitoring tools can call a short, stable URL.

Everything below is explained word by word. Where I say "I checked this", I ran the real library code from the project's virtual environment (FastAPI 0.141, SQLAlchemy 2.0, Pydantic 2.13) and I am reporting what it did.

A few ideas come up in every router file. I explain each one fully the first time it appears, and later files point back to that place:

- `APIRouter(prefix=..., tags=...)` - **health.py Block 6** and **auth.py Block 12**.
- the decorator arguments `response_model`, `status_code`, `summary` - **auth.py Block 13**.
- `select(...)` + `db.scalar(...)` instead of the old `db.query(...).first()` - **auth.py Block 17**.
- `db.scalars(...)` for many rows - **categories.py Block 28**.
- `db.add` / `db.commit` / `db.refresh` - **auth.py Blocks 19 to 21**.
- `IntegrityError` and `db.rollback()` - **auth.py Block 20**.
- `OAuth2PasswordRequestForm` and the `username` field - **auth.py Block 23**.
- the 401 / 404 / 409 choices - **auth.py Blocks 15 and 27**, **categories.py Blocks 13 and 19**.
- `model_dump(exclude_unset=True)` and the `setattr` loop - **categories.py Blocks 36 and 38**.
- `db.delete` and `Response(status_code=204)` - **categories.py Blocks 44 and 45**.
- `logger.exception` - **health.py Block 10**.

## File: app/routers/__init__.py

### What this file is for

This file has no code, only a docstring. Its presence turns the `app/routers/` folder into a Python **package**, so that `app/main.py` can write `from app.routers import auth, categories, expenses, health, reports, users`. The docstring is a table of contents: it lists every router file and what it is for, so a new reader can open this one file and know where to look.

Nothing imports anything *from* this file. It imports nothing.

### The whole file

```python
"""
routers/ - The API endpoints, one file per resource.

    health.py      -> GET /health (is the API and database up?)
    auth.py        -> register and login
    users.py       -> the logged-in user's profile
    categories.py  -> CRUD for expense categories
    expenses.py    -> CRUD for expenses, with filtering and pagination
    reports.py     -> spending summaries (totals, by category, by month)

Each file exposes a `router` object that app/main.py registers.
"""
```

### Walkthrough, block by block

### Block 1: The opening line of the docstring

```python
"""
routers/ - The API endpoints, one file per resource.
```

**Word by word**

- `"""` - three double quotes open a string that may span many lines. Because it is the first thing in the file, Python stores it as the **module docstring**: documentation attached to the module object. It does nothing when the program runs.
- `routers/` - the folder name, with a slash to show it is a folder.
- `The API endpoints` - an **endpoint** is one URL + one HTTP method (for example `GET /health`) and the function that handles it.
- `one file per resource` - a **resource** is one kind of thing the API manages: users, categories, expenses. The rule of this folder is: one file for each.

**Why it is here.** It tells you the organising rule of the folder in one sentence.

**If you removed or changed it.** Nothing in the program changes. Only the explanation is lost.

### Block 2: The list of files

```python
    health.py      -> GET /health (is the API and database up?)
    auth.py        -> register and login
    users.py       -> the logged-in user's profile
    categories.py  -> CRUD for expense categories
    expenses.py    -> CRUD for expenses, with filtering and pagination
    reports.py     -> spending summaries (totals, by category, by month)
```

**Word by word**

- `health.py -> GET /health` - the file and the one endpoint it defines. `(is the API and database up?)` says what the endpoint answers.
- `auth.py -> register and login` - "auth" is short for **authentication**: proving who you are. This file creates accounts and hands out login tokens.
- `users.py -> the logged-in user's profile` - the endpoint that shows *your own* account details.
- `categories.py -> CRUD for expense categories` - **CRUD** is Create, Read, Update, Delete: the four basic operations on stored data. A category is a label like "Food" or "Rent".
- `expenses.py -> CRUD for expenses, with filtering and pagination` - **filtering** means "only show the rows that match"; **pagination** means "show the rows a page at a time". Covered in doc 09.
- `reports.py -> spending summaries (...)` - endpoints that add numbers up. Covered in doc 09.
- The `->` arrows and the aligned spacing are only formatting inside the text; they are not Python syntax here.

**Why it is here.** A map of the folder. When you want to change how login works, you know to open `auth.py` without opening every file.

**If you removed or changed it.** Nothing breaks. If you add a new router file later, you should add a line here so the map stays true.

### Block 3: The closing sentence

```python
Each file exposes a `router` object that app/main.py registers.
"""
```

**Word by word**

- `Each file exposes a router object` - "exposes" means "defines at the top level so others can import it". Every router file has a line `router = APIRouter(...)`. The name `router` is the same in every file on purpose, so `main.py` can treat them all the same way: `health.router`, `auth.router`, and so on.
- `that app/main.py registers` - **registers** means `app.include_router(...)`: telling the FastAPI app "here is a set of endpoints, add them".
- `"""` - closes the docstring.

**Why it is here.** It states the one contract every router file must follow: have a top-level `router`.

**If you removed or changed it.** Nothing breaks. If you **deleted the whole file** `__init__.py`: in modern Python (3.3 and later) the folder would still be importable as a "namespace package", so the app would most likely still start. But the folder would have no docstring, some tools would treat it differently, and it would be inconsistent with every other package in the project (`app/core`, `app/models`, ... all have one). Keep it.

### Compared to your old code

Your old `app/routers/` folder had no `__init__.py` file at all (I listed the folder: only `auth.py`, `post.py`, `user.py` and `__pycache__`). It worked because of the namespace-package rule above. The new project adds the file for two reasons: to be explicit that this folder is a package, and to give you the table of contents you just read.

### Key terms in this file

| Term              | One-line meaning                                                                 |
| ----------------- | -------------------------------------------------------------------------------- |
| package           | A folder that Python treats as a group of modules; `__init__.py` marks it.       |
| module docstring  | The string at the very top of a file; documentation, not code.                   |
| endpoint          | One URL + HTTP method and the function that answers it.                          |
| resource          | One kind of thing the API manages (users, categories, expenses).                 |
| CRUD              | Create, Read, Update, Delete.                                                    |
| router            | An `APIRouter` object: a bundle of endpoints that `main.py` adds to the app.     |

## File: app/routers/health.py

### What this file is for

This file defines one endpoint, `GET /health`. It answers the question "is the API running, and can it reach the database?". Uptime monitors (a service that calls your API every minute and alerts you when it fails) and load balancers (which decide whether to send traffic to this server) call it. It returns `{"status": "ok", "database": "connected"}` with HTTP 200 when all is well, and HTTP 503 when the database cannot be reached.

It imports `logging` (standard library), three names from FastAPI, and `check_database_connection` from `app/database/session.py`. `app/main.py` imports this file to register `health.router` (without the `/api/v1` prefix).

### The whole file

```python
"""Health check endpoint for uptime monitors and load balancers."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.database.session import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Check that the API and database are running")
def health_check() -> dict[str, str]:
    try:
        check_database_connection()
    except Exception:
        logger.exception("Health check failed: database is unreachable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        )
    return {"status": "ok", "database": "connected"}
```

### Walkthrough, block by block

### Block 1: The module docstring

```python
"""Health check endpoint for uptime monitors and load balancers."""
```

**Word by word**

- `"""..."""` - a one-line module docstring (see `__init__.py` Block 1).
- `Health check endpoint` - an endpoint whose only job is to report whether the service is healthy.
- `uptime monitors` - external services that call a URL on a schedule and alert you when it stops answering.
- `load balancers` - a machine in front of several copies of your API that spreads requests between them. It uses a health URL to notice when one copy is broken and stop sending it traffic.

**Why it is here.** It names the audience of this endpoint: machines, not people.

**If you removed or changed it.** Nothing breaks.

### Block 2: Importing the logging module

```python
import logging
```

**Word by word**

- `import` - keyword: load a module and make its name available in this file.
- `logging` - the standard-library module for writing log messages (text lines with a time, a level such as INFO or ERROR, and the message). It comes with Python; nothing to install.

**Why it is here.** When the health check fails we want a record of *why* (the real database error) in the server log, while the client only sees a short message.

**If you removed or changed it.** Line 9 (`logging.getLogger(...)`) would raise `NameError: name 'logging' is not defined` the moment `app.main` imports this file, so the whole app would fail to start.

### Block 3: Importing from FastAPI

```python
from fastapi import APIRouter, HTTPException, status
```

**Word by word**

- `from fastapi import` - take these names out of the `fastapi` package.
- `APIRouter` - the class that holds a group of endpoints. You create one per file, attach endpoints to it with decorators, and `main.py` adds it to the app. You already used it in the old project.
- `HTTPException` - the exception class you `raise` to stop the endpoint and send an error response with a status code and a `detail` message. FastAPI catches it and turns it into a JSON reply `{"detail": "..."}`. I checked: `fastapi.HTTPException` is a subclass of Starlette's `HTTPException`, which is a normal Python `Exception`.
- `status` - a module full of named constants for HTTP status codes, for example `status.HTTP_503_SERVICE_UNAVAILABLE` which is just the number `503`. I checked: `fastapi.status` *is* `starlette.status`, the same module object. The names exist so the code reads as words instead of bare numbers.

**Why it is here.** All three are needed below: `APIRouter` on line 11, `HTTPException` and `status` on lines 20 to 21.

**If you removed or changed it.** `NameError` at import time for whichever name is missing; the app would not start.

### Block 4: Importing the database check

```python
from app.database.session import check_database_connection
```

**Word by word**

- `app.database.session` - the project's own module `app/database/session.py` (doc 05). The dots are folder separators: `app/` then `database/` then `session.py`.
- `check_database_connection` - a function from that file. It opens a connection from the engine's pool and runs `SELECT 1`. If the database is down it raises an exception (the exact class depends on the driver, for PostgreSQL usually `sqlalchemy.exc.OperationalError`); if all is well it returns `None`. `main.py` calls the same function once at startup.

**Why it is here.** This is the actual test the endpoint performs. "Healthy" is defined as "this call does not raise".

**If you removed or changed it.** `NameError` on line 17 when the first `/health` request arrives (not at import time, because the name is only used inside the function). That request would get a 500 Internal Server Error.

### Block 5: Creating the logger

```python
logger = logging.getLogger(__name__)
```

**Word by word**

- `logger` - the variable name we choose for this file's logger.
- `=` - assignment.
- `logging.getLogger(...)` - a function from the `logging` module that returns a **logger** object: the thing you call `.info(...)`, `.error(...)`, `.exception(...)` on. Calling it twice with the same name returns the same object.
- `__name__` - a variable Python sets automatically in every module: the module's full dotted name. I checked: inside this file it is `"app.routers.health"`. So every log line from this file is tagged `app.routers.health`, and you can see at a glance which file wrote it. (When you run a file directly as a script, `__name__` is `"__main__"` instead; that never happens for a router.)

**Why it is here.** Standard Python logging practice: one logger per module, named after the module. `main.py` calls `logging.basicConfig(...)` once, which sets the format and level for the whole program; loggers in every file pass their messages up to that configuration.

**If you removed or changed it.** `NameError: name 'logger' is not defined` on line 19 when a health check fails. If you changed `__name__` to a fixed string like `"health"`, it would still work, but the log line would no longer say which module it came from.

### Block 6: Creating the router

```python
router = APIRouter(tags=["Health"])
```

**Word by word**

- `router` - the top-level name that `main.py` expects (see `__init__.py` Block 3).
- `APIRouter(...)` - creates the router object.
- `tags=` - a keyword argument. **Tags** are labels for the interactive docs at `/docs`: every endpoint on this router is shown under a heading with this name. I checked the generated OpenAPI: `GET /health` carries `tags: ["Health"]`.
- `["Health"]` - a Python list (square brackets) with one string. It is a list because an endpoint may have several tags.
- There is **no `prefix=`** here. The default prefix is the empty string, so the endpoint path below (`/health`) is used as-is. `main.py` also registers this router *without* `/api/v1`, so the final URL is simply `/health`.

**Why it is here.** The one router of this file. Tags keep `/docs` tidy.

**If you removed or changed it.** Without this line, the decorator on line 14 would fail with `NameError: name 'router' is not defined` at import. Without `tags`, the endpoint would appear under a "default" heading in `/docs`. If you added `prefix="/api/v1"`, the URL would become `/api/v1/health` and every monitor configured for `/health` would start getting 404.

### Block 7: The route decorator

```python
@router.get("/health", summary="Check that the API and database are running")
```

**Word by word**

- `@` - the **decorator** symbol. A decorator is a function that takes the function written right below it and registers or wraps it. `@router.get(...)` means "register the next function as the handler for GET requests on this path".
- `router.get` - the method on the router for the HTTP **GET** method (reading data, no body).
- `"/health"` - the path. Together with the empty router prefix and the empty `main.py` prefix, the full URL is `/health`.
- `summary=` - a keyword argument: a short human title for the endpoint, shown in `/docs` next to the path. I checked the OpenAPI output: `summary: "Check that the API and database are running"`. It changes nothing about how the endpoint behaves.
- There is no `response_model` and no `status_code` here. The default status for a successful response is 200, and the response shape comes from the return annotation in the next block.

**Why it is here.** This line is what turns a plain function into an endpoint.

**If you removed or changed it.** Without the decorator, `health_check` would be an ordinary function nobody calls; `GET /health` would return 404. Without `summary`, `/docs` would show the function name turned into words ("Health Check") instead.

### Block 8: The function header

```python
def health_check() -> dict[str, str]:
```

**Word by word**

- `def` - keyword that starts a function definition.
- `health_check` - the function name. FastAPI uses it to build the operation id in the docs; otherwise it is just a name.
- `()` - no parameters. This endpoint needs no input: no body, no path parameters, no login, no database session parameter (it uses the engine directly through `check_database_connection`).
- `->` - the **return annotation** arrow: "this function returns a value of the following type".
- `dict[str, str]` - a dictionary whose keys are strings and whose values are strings. `dict` is the built-in dictionary type; the square brackets add detail about what is inside (this is called a *generic* type). Python itself does not enforce annotations, but FastAPI reads this one.
- `:` - ends the header; the indented body follows.

**Why it is here.** Because there is no `response_model` in the decorator, FastAPI uses the return annotation as the response model. I checked the FastAPI source (`routing.py`): when `response_model` is not given, it reads the return annotation and uses it, unless the annotation is a `Response` type. The effect: `/docs` documents the response as an object with string values, and FastAPI **validates** the returned dictionary against it. I checked: an endpoint annotated `-> dict[str, str]` that returns `{"status": 1}` (a number) gets a 500 Internal Server Error, because the response fails validation.

**If you removed or changed it.** With no annotation the endpoint still works, but `/docs` would show an empty, untyped response and nothing would check the shape. Changing it to `-> dict[str, int]` would make the real response (all strings) fail validation: every `/health` call would be a 500.

### Block 9: Trying the database

```python
    try:
        check_database_connection()
```

**Word by word**

- `try:` - keyword that starts a block in which errors are expected and will be handled by an `except` below instead of crashing.
- `check_database_connection()` - calls the function imported in Block 4. `()` with nothing inside: it takes no arguments. Its return value (`None`) is ignored; what matters is whether it raises.

**Why it is here.** This is the health test itself.

**If you removed or changed it.** Without the `try`, a database failure would escape the function as an unhandled exception and FastAPI would answer 500 Internal Server Error with no useful JSON, and the error would not be logged by us. Without the call, the endpoint would always say "connected" even with the database down, which makes the health check useless.

### Block 10: Catching the failure and logging it

```python
    except Exception:
        logger.exception("Health check failed: database is unreachable")
```

**Word by word**

- `except` - keyword: "if the `try` block raised, run this instead".
- `Exception` - the base class of all "normal" errors in Python. Catching it catches any database error (`OperationalError`, `psycopg2.OperationalError`, connection timeouts, ...). It does **not** catch `KeyboardInterrupt` or `SystemExit`, which derive from `BaseException`, so pressing Ctrl+C still stops the server.
- `:` - starts the handler body.
- `logger.exception(...)` - a logger method. I checked the standard-library source: it is exactly `self.error(msg, exc_info=True)`. That means: log at level **ERROR**, and attach the full traceback of the exception currently being handled. I ran it: the output is the message line, then `Traceback (most recent call last):` and the real error, for example `RuntimeError: connection refused`. It must be called inside an `except` block; I checked that outside one it prints `NoneType: None` where the traceback should be.
- `"Health check failed: database is unreachable"` - the message string.

**Why it is here.** Operators need the real reason in the log (which host, which error), but that detail must not go to the client. Logging it here keeps the two separate.

**If you removed or changed it.** Without the log line, the endpoint still returns 503 but the log would be silent, and you would have to guess why. If you wrote `logger.error(...)` instead of `logger.exception(...)`, you would get the message but no traceback. If you changed `except Exception` to a specific class such as `except OperationalError`, any other error type would escape as a 500.

### Block 11: Answering 503

```python
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        )
```

**Word by word**

- `raise` - keyword: throw an exception now; the function stops here.
- `HTTPException(...)` - FastAPI's error (Block 3). FastAPI catches it and builds the JSON response.
- `status_code=` - keyword argument: the HTTP status to send.
- `status.HTTP_503_SERVICE_UNAVAILABLE` - the number 503. **503 Service Unavailable** means "the server is up but cannot do its job right now, try again later". It is the standard answer for a failed dependency such as a database, and monitors treat anything that is not 2xx as unhealthy.
- `detail=` - the message that goes into the JSON body as `{"detail": "..."}`.
- `"Database is unavailable"` - short and safe: it does not leak the database host, user name or error text.
- The trailing commas and the line breaks inside the parentheses are only formatting; Python allows a newline anywhere inside `(...)`.
- Because this `raise` happens inside an `except` block, Python links the new exception to the original one (you would see "During handling of the above exception, another exception occurred" in a traceback). That is normal and harmless here.

I checked the whole path: when `check_database_connection` raises, `GET /health` returns `503` with body `{"detail": "Database is unavailable"}`, and the log shows the ERROR line with the traceback.

**Why it is here.** It converts "an exception happened" into a clean, documented HTTP answer.

**If you removed or changed it.** Without the `raise`, the function would fall through to the `return` on line 24 and report "connected" even though the check just failed. If you changed 503 to 500, monitors would still see a failure but the meaning would be "bug in the server" rather than "dependency down". If you put the exception text into `detail`, you would leak internal details to anyone on the internet.

### Block 12: The healthy answer

```python
    return {"status": "ok", "database": "connected"}
```

**Word by word**

- `return` - keyword: give this value back as the function's result; FastAPI turns it into the JSON response.
- `{...}` - a dictionary literal (curly braces).
- `"status": "ok"` - key `status`, value `ok`.
- `,` - separates the two entries.
- `"database": "connected"` - key `database`, value `connected`.

I checked: `GET /health` with a working database returns `200` and exactly `{"status": "ok", "database": "connected"}`.

**Why it is here.** A small fixed JSON body is easy for monitors to check; many of them look for a specific word such as `ok`.

**If you removed or changed it.** With no `return`, the function returns `None`, which fails the `dict[str, str]` response validation from Block 8: every healthy call would become a 500. Changing the keys or values is safe for the code, but any monitor configured to look for `"ok"` would need updating.

### Compared to your old code

Your old project had no health endpoint. The nearest thing was `connect_database()` in your old `app/database.py`:

```python
def connect_database():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database Connecting Successfully")
```

and `main.py` called it once inside `lifespan`. That checks the database **once at startup** and prints to the console. It cannot tell you that the database went away an hour later, and nothing outside the process can ask.

The new project keeps the startup check (`check_database_connection()` in `main.py`'s `lifespan`, doc 02) and adds this endpoint so the same check can be run **at any time, from outside**, by a monitor or load balancer. Two other differences:

- The old function used `print(...)`. The new code uses `logging`, which adds the time, the level and the module name to every line and can be redirected to files or services without changing the code.
- The old function let any error crash startup (which is what you want at startup). The endpoint instead catches the error, logs it, and answers 503, because a running server should keep answering requests even when one of them fails.

### Key terms in this file

| Term                  | One-line meaning                                                                        |
| --------------------- | --------------------------------------------------------------------------------------- |
| health check          | An endpoint that reports whether the service and its dependencies work.                 |
| uptime monitor        | An external service that calls a URL on a schedule and alerts when it fails.            |
| load balancer         | A machine that spreads traffic over several servers and skips unhealthy ones.           |
| logger                | A `logging` object you call `.info()`, `.error()`, `.exception()` on.                   |
| `__name__`            | The module's dotted name, set by Python; here `app.routers.health`.                     |
| `logger.exception()`  | Log at ERROR level **with the traceback**; call it inside `except`.                     |
| decorator (`@`)       | A function applied to the function below it; `@router.get` registers an endpoint.      |
| return annotation     | `-> type` after the parameters; FastAPI uses it as the response model if none is given. |
| `try` / `except`      | Run code; if it raises, run the handler instead of crashing.                            |
| 503                   | Service Unavailable: the server runs but a dependency (the database) does not.          |
| `status`              | FastAPI/Starlette module of named status-code constants (`HTTP_503_...` is 503).        |

## File: app/routers/auth.py

### What this file is for

This file has the two endpoints that get a person into the system: `POST /api/v1/auth/register` creates an account, and `POST /api/v1/auth/login` checks an email and password and returns a **JWT access token** (a signed string the client sends back on every later request; see doc 04). It is the only router that touches passwords, and it never stores or returns a plain password: `register` stores a hash, `login` compares against the hash.

It imports `Annotated` (standard library), FastAPI's router, dependency and error tools, `OAuth2PasswordRequestForm` (FastAPI's login-form helper), `select` and `IntegrityError` from SQLAlchemy, and from the project: the `DatabaseSession` alias (doc 04), the three password/token helpers from `app/core/security.py` (doc 04), the `User` model (doc 06) and the `Token`, `UserCreate`, `UserResponse` schemas (doc 07). `app/main.py` imports it to register `auth.router` under `/api/v1`.

### The whole file

```python
"""Authentication endpoints: create an account and log in."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import DatabaseSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def register_user(user_in: UserCreate, db: DatabaseSession) -> User:
    email_already_registered = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="An account with this email already exists",
    )

    email = user_in.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise email_already_registered

    user = User(
        email=email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two requests registered the same email at the same moment;
        # the unique index on users.email caught the second one.
        db.rollback()
        raise email_already_registered
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Log in and get an access token")
def login(
    credentials: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DatabaseSession,
) -> Token:
    """
    Send the email in the `username` form field (OAuth2 standard) and the
    password in `password`. The Authorize button in /docs uses this endpoint.
    """
    user = db.scalar(select(User).where(User.email == credentials.username.lower()))

    # Same error for "no such email" and "wrong password", so an attacker
    # cannot use this endpoint to discover which emails are registered.
    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(user.id))
```

### Walkthrough, block by block

### Block 1: The module docstring

```python
"""Authentication endpoints: create an account and log in."""
```

**Word by word**

- `"""..."""` - module docstring.
- `Authentication` - proving who you are. (Not to be confused with *authorization*, which is deciding what you are allowed to do; that happens in the other routers through `CurrentUser` and the `owner_id` filters.)
- `create an account and log in` - the two endpoints.

**Why it is here.** States the scope of the file.

**If you removed or changed it.** Nothing breaks.

### Block 2: Importing Annotated

```python
from typing import Annotated
```

**Word by word**

- `typing` - the standard-library module for type hints.
- `Annotated` - a special typing tool. `Annotated[SomeType, extra]` means "the type is `SomeType`, and here is some extra information attached to it". Python itself ignores the extra part. FastAPI reads it: when the extra part is `Depends(...)`, FastAPI knows how to produce the value. In this file it is used once, in the `login` function: `Annotated[OAuth2PasswordRequestForm, Depends()]` (Block 23). Doc 04 explains `Annotated` in full, and the `DatabaseSession` alias imported below is itself built with it.

**Why it is here.** Needed for the `credentials` parameter of `login`.

**If you removed or changed it.** `NameError: name 'Annotated' is not defined` at import time, on the `login` definition; the app would not start.

### Block 3: Importing from FastAPI

```python
from fastapi import APIRouter, Depends, HTTPException, status
```

**Word by word**

- `APIRouter` - the router class (health.py Block 3).
- `Depends` - the function that marks a parameter as a **dependency**: "FastAPI, do not expect this value from the client; call this function (or class) and pass me the result". Doc 04 explains it in depth. Here it is used as `Depends()` with no argument (Block 23).
- `HTTPException` - the error you raise to send an error response (health.py Block 3).
- `status` - the status-code constants module (health.py Block 3). Used for 201, 409 and 401 below.

**Why it is here.** All four names are used in this file.

**If you removed or changed it.** `NameError` at import for the missing name; the app would not start.

### Block 4: Importing the login form helper

```python
from fastapi.security import OAuth2PasswordRequestForm
```

**Word by word**

- `fastapi.security` - the part of FastAPI that deals with authentication helpers. `OAuth2PasswordBearer`, used in `dependencies.py`, comes from the same place.
- `OAuth2PasswordRequestForm` - a class that describes a **login form** with the field names fixed by the OAuth2 standard. I opened its source: its `__init__` declares `grant_type`, `username`, `password`, `scope`, `client_id` and `client_secret`, every one of them marked as `Form(...)`. `username` and `password` are required; the rest are optional (`grant_type` must match the pattern `^password$` if sent; `scope` defaults to the empty string and is split into `self.scopes`, a list). `Form(...)` means "read this from a form-encoded body (`application/x-www-form-urlencoded`), the format an HTML `<form>` sends", not from JSON. Block 23 explains why the field is called `username`.

**Why it is here.** It lets `login` accept exactly the body that the "Authorize" button in `/docs` and standard OAuth2 clients send, without hand-writing the form fields.

**If you removed or changed it.** `NameError` at import on the `login` definition. If you replaced it with a Pydantic model (JSON body), the Authorize button in `/docs` would stop working, because Swagger UI always sends a form to the token URL.

### Block 5: Importing select

```python
from sqlalchemy import select
```

**Word by word**

- `sqlalchemy` - the database toolkit (doc 05).
- `select` - a function that builds a `SELECT` statement object. `select(User)` means "select rows of the users table and give me `User` objects". You add conditions with `.where(...)`, ordering with `.order_by(...)`, and then hand the statement to the session with `db.scalar(...)`, `db.scalars(...)` or `db.execute(...)`. This is the SQLAlchemy 2.0 style that replaces the old `db.query(User)`; Block 17 compares the two.

**Why it is here.** Both endpoints look up a user by email with `select(User).where(...)`.

**If you removed or changed it.** `NameError: name 'select' is not defined` on the first register or login request (the name is used inside the functions, so the failure is at request time, as a 500).

### Block 6: Importing IntegrityError

```python
from sqlalchemy.exc import IntegrityError
```

**Word by word**

- `sqlalchemy.exc` - the module that holds SQLAlchemy's exception classes (`exc` is short for exceptions).
- `IntegrityError` - the exception SQLAlchemy raises when the database **refuses a write because it would break a rule**: a `UNIQUE` constraint, a `NOT NULL` column, a foreign key or a `CHECK` constraint. I triggered it: inserting a second user with the same email raised `IntegrityError` wrapping the driver's error `UNIQUE constraint failed: users.email`. The `users.email` column is declared `unique=True` in the model (doc 06), so PostgreSQL has a unique index on it.

**Why it is here.** Block 20 catches it to turn a rare race condition into a clean 409 instead of a 500.

**If you removed or changed it.** `NameError` at request time inside the `except` clause, but only when a duplicate slips past the first check, which is rare, so the bug would hide for a long time. Python evaluates the name in `except IntegrityError:` only when an exception actually reaches that line.

### Block 7: Importing the database-session alias

```python
from app.core.dependencies import DatabaseSession
```

**Word by word**

- `app.core.dependencies` - the project file `app/core/dependencies.py` (doc 04).
- `DatabaseSession` - an alias defined there as `Annotated[Session, Depends(get_db)]`. Writing a parameter as `db: DatabaseSession` is the same as writing `db: Session = Depends(get_db)` in the old style: FastAPI calls `get_db()`, which opens one SQLAlchemy `Session` for this request, hands it to the function, and closes it when the request ends.

**Why it is here.** Both endpoints need the database.

**If you removed or changed it.** `NameError` at import time, because the alias is used in the function signatures.

### Block 8: Importing the password and token helpers

```python
from app.core.security import create_access_token, hash_password, verify_password
```

**Word by word**

- `app.core.security` - the project file `app/core/security.py` (doc 04).
- `create_access_token` - takes a user id, returns a signed JWT string that expires after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `hash_password` - takes the plain password, returns an Argon2 hash string safe to store.
- `verify_password` - takes the plain password and the stored hash, returns `True` or `False`.

**Why it is here.** `register` needs `hash_password`; `login` needs `verify_password` and `create_access_token`. Keeping them in `security.py` means the router never sees how hashing or signing works.

**If you removed or changed it.** `NameError` at request time (500) on the first register or login.

### Block 9: Importing the User model

```python
from app.models.user import User
```

**Word by word**

- `app.models.user` - the project file `app/models/user.py` (doc 06).
- `User` - the SQLAlchemy model class for the `users` table. `User(...)` makes a new row object; `User.email` at class level is a column you can compare in a `where(...)`.

**Why it is here.** Both endpoints query the `users` table and `register` inserts into it.

**If you removed or changed it.** `NameError` at import time (`-> User` in the function signature is evaluated when the file loads).

### Block 10: Importing the Token schema

```python
from app.schemas.auth import Token
```

**Word by word**

- `app.schemas.auth` - the project file `app/schemas/auth.py` (doc 07).
- `Token` - a Pydantic model with two fields: `access_token: str` and `token_type: str = "bearer"`. It is the response shape of `login`.

**Why it is here.** `login` returns a `Token`, and the decorator declares `response_model=Token`.

**If you removed or changed it.** `NameError` at import time.

### Block 11: Importing the user schemas

```python
from app.schemas.user import UserCreate, UserResponse
```

**Word by word**

- `app.schemas.user` - the project file `app/schemas/user.py` (doc 07).
- `UserCreate` - the request body of `register`: `email` (validated as an email address), `full_name` (1 to 100 characters, trimmed), `password` (8 to 128 characters).
- `UserResponse` - the response body: `id`, `email`, `full_name`, `created_at`. It has **no password field**, which is the whole point: whatever the function returns, only these four fields leave the server.

**Why it is here.** One schema validates what comes in; the other filters what goes out.

**If you removed or changed it.** `NameError` at import time.

### Block 12: Creating the router

```python
router = APIRouter(prefix="/auth", tags=["Authentication"])
```

**Word by word**

- `router = APIRouter(...)` - as in health.py Block 6.
- `prefix="/auth"` - a string put in front of every path on this router. `"/register"` becomes `"/auth/register"`. Then `main.py` adds its own prefix, giving `/api/v1/auth/register`. I checked the FastAPI source: `APIRouter.__init__` asserts that a prefix **starts with `/`** and **does not end with `/`**; `APIRouter(prefix="auth")` fails with `A path prefix must start with '/'`, and `APIRouter(prefix="/auth/")` fails with `A path prefix must not end with '/'`. When a route is added, FastAPI simply concatenates `self.prefix + path`.
- `tags=["Authentication"]` - the `/docs` heading for both endpoints.

**Why it is here.** It groups the two endpoints under one URL segment and one docs heading, and lets you write the short path (`/register`) in each decorator.

**If you removed or changed it.** Without the line, the decorators below would hit `NameError: name 'router' is not defined`. Changing the prefix changes every URL in this file, and also breaks the `tokenUrl` that `dependencies.py` tells Swagger to use (`/api/v1/auth/login`), so the Authorize button would post to a URL that no longer exists.

### Block 13: The register decorator

```python
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
```

**Word by word**

- `@router.post(...)` - register the next function for HTTP **POST** (sending data to create something) on this router.
- `"/register"` - the path; with the prefixes it becomes `/api/v1/auth/register`.
- `response_model=UserResponse` - tells FastAPI: "whatever this function returns, convert it to a `UserResponse` and send only those fields". The function returns a `User` ORM object that has a `hashed_password` attribute; because `UserResponse` has no such field, the hash never appears in the response. `UserResponse` has `model_config = ConfigDict(from_attributes=True)` (doc 07), which lets Pydantic read the fields from an object's attributes instead of from a dictionary. I checked the FastAPI source: when `response_model` is given it wins over the return annotation; the annotation is only used when `response_model` is left out (as in `health.py`). `response_model` also defines the response shape shown in `/docs`.
- `status_code=status.HTTP_201_CREATED` - the status for a successful call. **201 Created** is the standard answer when a POST made a new record. Without it FastAPI would send 200. I checked: a successful register returns 201, and the OpenAPI lists the `201` response.
- `summary="Create a new account"` - the docs title (health.py Block 7).
- The arguments are spread over several lines with a trailing comma after the last one; that is just formatting.

**Why it is here.** This single decorator sets the URL, the method, the output filter, the success code and the docs title.

**If you removed or changed it.** Without `response_model`, FastAPI would fall back to the return annotation `-> User`. A SQLAlchemy model is not a type Pydantic can build a schema from, so the app would fail **at import time**. I tried it: the decorator raises `FastAPIError: Invalid args for response field! Hint: check that <class 'app.models.user.User'> is a valid Pydantic field type`. If you set `response_model` to a schema that included `hashed_password`, every registration would leak the hash. Without `status_code`, clients would get 200 instead of 201, which is not wrong, just less precise, and the test suite would fail.

### Block 14: The register function header

```python
def register_user(user_in: UserCreate, db: DatabaseSession) -> User:
```

**Word by word**

- `def register_user(...)` - the endpoint function.
- `user_in: UserCreate` - the first parameter. The annotation is a Pydantic model, so FastAPI reads the **JSON request body**, validates it against `UserCreate`, and gives you an object with `.email`, `.full_name`, `.password`. If the body is missing a field, the email is not a valid address, or the password is shorter than 8 characters, FastAPI answers **422 Unprocessable Content** with details and this function never runs. The name `user_in` ("user, incoming") distinguishes it from the `user` database object created below.
- `,` - separates parameters.
- `db: DatabaseSession` - the database session for this request (Block 7). No default value is needed, because the `Depends` is inside the alias.
- `-> User` - the return annotation. The function returns a `User` ORM object. FastAPI ignores it for the response here because `response_model` is set (Block 13); it stays as documentation and for editors and type checkers.
- `:` - starts the body.

**Why it is here.** It declares the two things the endpoint needs: validated input and a database session.

**If you removed or changed it.** Changing `user_in: UserCreate` to `user_in: dict` would turn off validation: an empty password or a non-email would reach the database. Removing `db` would make the `db.scalar(...)` call fail with `NameError`.

### Block 15: Preparing the 409 error

```python
    email_already_registered = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="An account with this email already exists",
    )
```

**Word by word**

- `email_already_registered` - a variable holding an exception object. Creating an exception does **not** raise it; `raise` does that later. The same object is raised in two places (Blocks 17 and 20), so it is built once to keep the two identical.
- `HTTPException(...)` - FastAPI's error class.
- `status_code=status.HTTP_409_CONFLICT` - the number 409. **409 Conflict** means "your request is valid, but it clashes with the current state of the data". Registering an email that already exists is exactly that. It is not 400 (the request itself is fine), not 422 (the fields are valid), and not 401/403 (it is not about permissions).
- `detail="An account with this email already exists"` - the message in the JSON body. It does tell the caller that the email exists; for a registration form that is unavoidable, because the person must know they should log in instead. (The `login` endpoint is careful not to reveal the same thing; see Block 26.)

**Why it is here.** Build once, raise twice.

**If you removed or changed it.** `NameError` on `raise email_already_registered` in Block 17 (500 at request time). If you changed the code to 400, clients could not distinguish "bad input" from "already taken".

### Block 16: Normalising the email

```python
    email = user_in.email.lower()
```

**Word by word**

- `email` - a local variable.
- `user_in.email` - the validated email from the body. I checked: Pydantic's `EmailStr` gives back a plain `str`, and it lowercases **only the domain part** (`A@B.com` became `A@b.com`). The part before the `@` keeps its case.
- `.lower()` - the string method that returns a copy with every letter in lowercase. `A@b.com` becomes `a@b.com`.

**Why it is here.** The `users.email` column is stored lowercase (doc 06 says so), and `login` lowercases the typed email too (Block 25). This makes `Harshit@Example.com` and `harshit@example.com` the same account, which is what people expect. Doing it here means the stored value is always already lowercase, so the `UNIQUE` index also catches case-different duplicates.

**If you removed or changed it.** Someone could register `Me@x.com` and then `me@x.com` as two different accounts (the unique index compares exact bytes), and a user who typed their email with a capital letter at login would be told "Incorrect email or password" even with the right password, because `login` lowercases its side.

### Block 17: Checking for an existing account

```python
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise email_already_registered
```

**Word by word**

- `if` - keyword: run the next line only when the condition is true.
- `select(User)` - build a `SELECT` of all columns of the `users` table, mapped to `User` objects (Block 5).
- `.where(...)` - add a `WHERE` condition. It returns a **new** statement object; I checked that the original is unchanged and the new one has the `WHERE`. (That matters in `categories.py` Block 18, where the result must be assigned back.)
- `User.email == email` - this is **not** a Python comparison that gives `True`/`False`. At class level, `User.email` is a SQLAlchemy column object, and `==` on it builds a SQL expression `users.email = :email_1`. The value of `email` is sent separately as a **bound parameter**, so a crafted email string cannot inject SQL.
- `db.scalar(...)` - run the statement and return **the first column of the first row, or `None` if there are no rows** (that sentence is from SQLAlchemy's own doc, which I read). With `select(User)` the "first column" is the whole `User` object. I checked: with no matching row it returned `None`; with a match it returned a `User` instance.
- `is not None` - "a row was found". `is` compares identity; `None` is a single object, so `is not None` is the correct way to say "not nothing".
- `:` and the indented `raise email_already_registered` - raise the 409 prepared in Block 15.

The SQL that SQLAlchemy sends (I compiled it for PostgreSQL):

```sql
SELECT users.id, users.email, users.full_name, users.hashed_password, users.is_active, users.created_at
FROM users
WHERE users.email = %(email_1)s
```

**`select()` + `db.scalar()` versus your old `db.query().first()`.** Your old code wrote `db.query(user_table).filter(user_table.email == ...).first()`. It does the same job. The new style is SQLAlchemy 2.0's preferred way: you build a statement object first (`select(...).where(...)`), then the session runs it. The benefits are that the same `select` syntax works for plain SQL-level queries and ORM queries, the statement is a value you can pass around and extend (Block 18 of `categories.py` does exactly that), and SQLAlchemy's documentation and type hints are written for this style. `db.query()` still works in 2.0 but is considered "legacy".

**Why it is here.** A friendly 409 for the normal case of a duplicate email, before doing the expensive password hashing.

**If you removed or changed it.** The insert in Block 20 would still be rejected by the unique index, and the `except IntegrityError` there would still produce a 409, so the endpoint would stay correct. But the server would hash the password (Argon2 is deliberately slow) and open a failed transaction for every duplicate attempt, and you would rely on the rarer code path for the common case. If you wrote `== None` instead of `is not None` the logic would be reversed; if you forgot `is not None` altogether, `if db.scalar(...)` would also work (a `User` object is truthy) but is less explicit.

### Block 18: Building the new user

```python
    user = User(
        email=email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )
```

**Word by word**

- `user = User(...)` - create an instance of the model class. SQLAlchemy models accept each column as a keyword argument. At this point it is a plain Python object; nothing has touched the database.
- `email=email` - the lowercased email from Block 16.
- `full_name=user_in.full_name` - straight from the validated body (already trimmed of surrounding spaces by `StringConstraints(strip_whitespace=True)` in the schema).
- `hashed_password=hash_password(user_in.password)` - the plain password goes into `hash_password(...)` and only the hash string is stored. `user_in.password` is never assigned to the model. The column is deliberately named `hashed_password`, so nobody later mistakes it for the password.
- Not given: `id` (the database assigns it), `is_active` (model default `True`), `created_at` (database default `now()`).

**Why it is here.** Builds the row to insert, with the one security-critical transformation (hashing) done right here.

**If you removed or changed it.** Writing `hashed_password=user_in.password` would store plain passwords; anyone who reads the database would have every password. Leaving out `email` or `full_name` would make the `INSERT` fail with an `IntegrityError` (NOT NULL), which Block 20 would wrongly report as "email already exists".

### Block 19: Adding the user to the session

```python
    db.add(user)
```

**Word by word**

- `db.add(...)` - tells the session "this new object should be inserted". SQLAlchemy's doc calls this moving the object from *transient* (unknown to the session) to *pending* (waiting for the next flush). I checked: right after `db.add(user)`, no SQL has run yet, `user.id` is still `None`, and `user in db.new` is `True`.

**Why it is here.** The session only writes objects it knows about.

**If you removed or changed it.** `db.commit()` would commit an empty transaction, nothing would be inserted, and `db.refresh(user)` would raise `InvalidRequestError` because the object is not persistent. The client would get a 500.

### Block 20: Committing, and handling the race

```python
    try:
        db.commit()
    except IntegrityError:
        # Two requests registered the same email at the same moment;
        # the unique index on users.email caught the second one.
        db.rollback()
        raise email_already_registered
```

**Word by word**

- `try:` - errors inside will be handled below.
- `db.commit()` - **flush** then **commit**. Flush sends the pending `INSERT` to the database; commit ends the transaction and makes it permanent. I captured the SQL on SQLite: `INSERT INTO users (email, full_name, hashed_password, is_active) VALUES (?, ?, ?, ?) RETURNING id, created_at`. On PostgreSQL it is the same idea. After commit, SQLAlchemy **expires** every attribute of `user` (I checked: `id`, `email`, `created_at`, ... are all in the expired set), which is why Block 21 refreshes.
- `except IntegrityError:` - runs only if the database refused the insert (Block 6).
- The two comment lines explain the only realistic way to get here: Block 17 found no user, but between that `SELECT` and this `INSERT`, another request inserted the same email. This is a **race condition**: two things racing for the same slot. The unique index on `users.email` is the referee.
- `db.rollback()` - undo the failed transaction and put the session back into a usable state. I checked what happens without it: after the failed commit, any further query on the session raises `PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush. To begin a new transaction with this Session, first issue Session.rollback()`. After `rollback()`, the failed `user` object is removed from the session (`user in db` is `False`) and queries work again.
- `raise email_already_registered` - the same 409 as the normal path, so the client cannot tell the two cases apart and does not need to.

**Why it is here.** Without it, the race would surface as a raw `IntegrityError` escaping the function: FastAPI would answer **500 Internal Server Error**, the real error would be in the log, and the session returned to the pool would be in the broken "pending rollback" state until `get_db` closes it (closing does roll back, so the damage is limited to this request, but the client still sees a 500 for what is really a 409).

**If you removed or changed it.** Remove the whole `try/except` and the race gives a 500 instead of a 409. Remove only `db.rollback()` and the `raise` still works (the 409 is sent), because the session is closed at the end of the request anyway; but if any code after it tried to use `db`, it would hit `PendingRollbackError`. Catch `Exception` instead of `IntegrityError` and a real outage (database down during commit) would be reported as "email already exists", which is misleading.

### Block 21: Refreshing and returning

```python
    db.refresh(user)
    return user
```

**Word by word**

- `db.refresh(user)` - SQLAlchemy's doc: "Expire and refresh attributes on the given instance." It runs a `SELECT ... WHERE users.id = ?` and loads every column into the object. I captured it: `SELECT users.id, users.email, users.full_name, users.hashed_password, users.is_active, users.created_at FROM users WHERE users.id = ?`. After it, `user.id`, `user.created_at` (set by the database's `now()`) and `user.is_active` are all real values.
- `return user` - hand the ORM object to FastAPI, which converts it through `UserResponse` (Block 13) into JSON with `id`, `email`, `full_name`, `created_at`.

I checked the result: `201` with a body like `{"id": 2, "email": "new@x.com", "full_name": "N", "created_at": "2026-10-06T11:54:03"}`.

**Why it is here.** The response must include values the database chose (`id`, `created_at`). `refresh` loads them explicitly in one query, right after the commit.

**If you removed or changed it.** Honest answer: removing `db.refresh(user)` would **not** break this endpoint, because after commit the attributes are expired and SQLAlchemy reloads them automatically on first access; I checked that reading `user.created_at` after a commit triggers the same `SELECT`. So `refresh` here is about being explicit and predictable (one clear reload, now, inside the request) rather than relying on lazy reloading while FastAPI serialises the object. Removing `return user` would return `None`, which fails `UserResponse` validation: a 500.

### Block 22: The login decorator

```python
@router.post("/login", response_model=Token, summary="Log in and get an access token")
```

**Word by word**

- `@router.post(...)` - POST, because the client *sends* credentials.
- `"/login"` - with the prefixes: `/api/v1/auth/login`. This exact URL is also what `dependencies.py` passes to `OAuth2PasswordBearer(tokenUrl=...)`, so the Authorize button in `/docs` knows where to post the form. I checked the generated OpenAPI: the security scheme is `OAuth2PasswordBearer` with `tokenUrl: /api/v1/auth/login`.
- `response_model=Token` - the response is filtered and documented as `{"access_token": "...", "token_type": "bearer"}`.
- `summary=...` - the docs title.
- No `status_code`: a successful login answers the default **200 OK**. Logging in does not create a resource, so 201 would be wrong.

**Why it is here.** Registers the token endpoint at the URL the rest of the project expects.

**If you removed or changed it.** Renaming the path breaks the Authorize button (it would post to a 404) unless `dependencies.py` is changed to match. Without `response_model`, FastAPI would use the `-> Token` annotation, which is a Pydantic model, so it would still work and document the same shape.

### Block 23: The login function header

```python
def login(
    credentials: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DatabaseSession,
) -> Token:
```

**Word by word**

- `def login(...)` - the endpoint function. The parameters are spread over several lines, one per line, with a trailing comma; just formatting.
- `credentials` - the parameter name we chose.
- `Annotated[OAuth2PasswordRequestForm, Depends()]` - type `OAuth2PasswordRequestForm`, plus the extra information `Depends()`.
- `Depends()` with **nothing inside** - I checked the FastAPI source (`dependencies/utils.py`): when `Depends` has no argument, FastAPI copies it and uses the **type annotation itself** as the dependency. So this means `Depends(OAuth2PasswordRequestForm)`: FastAPI will call `OAuth2PasswordRequestForm(...)` to build the value. Because that class's `__init__` parameters are all `Form(...)` fields (Block 4), FastAPI reads them from a form-encoded body. I checked the OpenAPI: the login request body is `application/x-www-form-urlencoded`. I also checked that sending the same fields as JSON gives **422** with `Field required` for `username` and `password`, because they were not found in a form.
- `db: DatabaseSession` - the request's database session (Block 7).
- `-> Token` - the function returns a `Token` schema object.

**Why the field is called `username` when we use an email.** `OAuth2PasswordRequestForm` implements the OAuth2 "password grant" from the standard (RFC 6749, section 4.3). That standard fixes the parameter names: `grant_type`, `username`, `password`, `scope`. Swagger UI's Authorize button and every standard OAuth2 client send exactly those names. If the field were renamed to `email`, those clients would stop working. So the project keeps the standard name and simply puts the email *in* the `username` field; the endpoint's docstring (Block 24) tells the user that. In your old project you did the same thing (`user_credentials.username`), so this is not new, only now it is explained.

**Why `Annotated[..., Depends()]` instead of `= Depends()`.** Your old code wrote `user_credentials: OAuth2PasswordRequestForm = Depends()`. Both forms work in FastAPI. The `Annotated` form keeps the "default value" slot free (so the parameter has no fake default), can be reused as an alias (that is how `DatabaseSession` and `CurrentUser` are made), and is the form the FastAPI docs now recommend.

**If you removed or changed it.** Dropping `Depends()` and keeping the annotation would make FastAPI treat `credentials` as a request body model, which `OAuth2PasswordRequestForm` is not; the Authorize button would break. Replacing it with a Pydantic model would require JSON, with the same effect.

### Block 24: The login docstring

```python
    """
    Send the email in the `username` form field (OAuth2 standard) and the
    password in `password`. The Authorize button in /docs uses this endpoint.
    """
```

**Word by word**

- `"""..."""` - a **function docstring**: the first string inside a function body. FastAPI shows it in `/docs` as the endpoint's description, under the summary. So this text is seen by anyone using the interactive docs.
- `Send the email in the username form field (OAuth2 standard)` - the instruction that answers the question from Block 23.
- `and the password in password` - the second field.
- `The Authorize button in /docs uses this endpoint.` - a hint about why the form is shaped this way.

**Why it is here.** It is the one place where the "email goes in `username`" surprise is explained to API users.

**If you removed or changed it.** Nothing breaks; the description disappears from `/docs` and people would try sending `email` and get a 422.

### Block 25: Looking up the user

```python
    user = db.scalar(select(User).where(User.email == credentials.username.lower()))
```

**Word by word**

- `user =` - a local variable: a `User` object or `None`.
- `db.scalar(select(User).where(...))` - the same lookup as Block 17.
- `credentials.username` - the string from the `username` form field (the email).
- `.lower()` - lowercased, to match how `register` stored it (Block 16).

**Why it is here.** We need the stored hash and the `is_active` flag for this email.

**If you removed or changed it.** Without `.lower()`, a user who typed `Me@X.com` at login would not be found (stored as `me@x.com`) and would get 401 despite the right password.

### Block 26: Deciding whether the login is valid

```python
    # Same error for "no such email" and "wrong password", so an attacker
    # cannot use this endpoint to discover which emails are registered.
    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.hashed_password)
    ):
```

**Word by word**

- The two comment lines state the design rule: one combined check, one message. If the API said "no such email" for unknown emails and "wrong password" for known ones, an attacker could feed it a list of emails and learn which ones have accounts (called **user enumeration**).
- `if (` ... `):` - the condition is wrapped in parentheses so it can be split across lines.
- `user is None` - no account with that email.
- `or` - logical OR. Python's `or` **short-circuits**: it evaluates left to right and stops at the first true part. So if `user is None` is true, the next two parts are never evaluated, which is essential: `user.is_active` on `None` would crash with `AttributeError`.
- `not user.is_active` - the account exists but was deactivated (`is_active` is a boolean column, default `True`; an admin can set it to `False` to block someone without deleting their data). `not` flips a boolean.
- `not verify_password(credentials.password, user.hashed_password)` - `verify_password` returns `True` when the typed password matches the stored hash. `not` makes the condition true when it does not match. This is only reached when a user exists and is active.

**Why it is here.** Three ways a login can be wrong, one answer for all three.

**If you removed or changed it.** Remove `user is None` and an unknown email would crash on `user.is_active` (500). Remove `not user.is_active` and deactivated users could still log in (and their tokens would then be rejected by `get_current_user`, which also checks `is_active`, so they would get confusing 401s on every other request). Split the check into separate `if`s with different messages and you reintroduce user enumeration.

### Block 27: Answering 401

```python
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

**Word by word**

- `raise HTTPException(...)` - stop and send an error.
- `status_code=status.HTTP_401_UNAUTHORIZED` - the number 401. **401 Unauthorized** means "we do not know who you are; authenticate". Despite the word in its name, it is the code for *authentication* failures. **403 Forbidden** (which your old code used) means "we know who you are, and you are not allowed". A failed login is a 401 case.
- `detail="Incorrect email or password"` - one message for every failure (Block 26). I checked: a wrong password and an unknown email both give `401 {"detail": "Incorrect email or password"}`.
- `headers={"WWW-Authenticate": "Bearer"}` - extra response headers, as a dictionary. The HTTP standard (RFC 7235) says a 401 response **must** include a `WWW-Authenticate` header naming the scheme the client should use. `Bearer` is the scheme for "send a token in the `Authorization: Bearer <token>` header". I checked: the header is present on the 401 response. `dependencies.py` sends the same header on its 401s.

**Why it is here.** A correct, standard, non-leaking login failure.

**If you removed or changed it.** Without the header the response still works for most clients but is not standard-compliant; some HTTP libraries and browsers use it to decide how to prompt. Using 403 would mislabel the failure.

### Block 28: Returning the token

```python
    return Token(access_token=create_access_token(user.id))
```

**Word by word**

- `return` - the success result.
- `Token(...)` - build the response schema object (Block 10).
- `access_token=` - its first field.
- `create_access_token(user.id)` - from `security.py` (doc 04): builds a JWT whose `sub` claim is the user id as a string and whose `exp` claim is now plus `ACCESS_TOKEN_EXPIRE_MINUTES`, signed with `SECRET_KEY`.
- `user.id` - the integer primary key of the user found in Block 25.
- `token_type` is not passed, so it takes its default `"bearer"`. I checked: the response has exactly the keys `access_token` and `token_type`, and `token_type` is `bearer`.

**Why it is here.** This string is what the client stores and sends back as `Authorization: Bearer <token>` on every protected request. `token_type: "bearer"` is required by the OAuth2 token response format, and Swagger UI reads it.

**If you removed or changed it.** Returning a plain dict `{"access_token": ...}` would still work: FastAPI validates it against `Token`, and because `token_type` has a default, it is filled in as `"bearer"`. The real risk is in changing `create_access_token(user.id)` to put something else in the token (for example the email), which would break `get_current_user` in `dependencies.py`, which expects the integer id in the `sub` claim; every protected request would then get 401.

### Compared to your old code

**Login.** Your old `app/routers/auth.py`:

```python
router = APIRouter(prefix="/login",tags=['Auth'])

@router.post("/")
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db:Session = Depends(get_db)):
    user = db.query(user_table).filter(user_table.email == user_credentials.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    access_token = create_access_token(data = {"user_id": user.id})

    return {"access_token": access_token, "token_type":"bearer"}
```

What is the same: the idea is identical, and you already used `OAuth2PasswordRequestForm` with `Depends()` and already returned the same message for both failure cases. Good instincts. What changed, and why:

- **URL.** Old: prefix `/login` + path `/` = `POST /login/`. New: prefix `/auth` + path `/login`, under `/api/v1` = `POST /api/v1/auth/login`. Grouping register and login under `/auth` keeps related endpoints together, and the version prefix lets you add `/api/v2` later without breaking clients.
- **403 became 401 with `WWW-Authenticate`.** 403 means "known user, not allowed"; a bad login is "unknown user", which is 401, and 401 must carry the `WWW-Authenticate` header.
- **Email case.** Old: compared the typed email exactly. New: lowercases on both register and login.
- **Deactivated accounts.** Old: no such concept. New: `not user.is_active` blocks them.
- **Two `if`s became one combined condition.** Same behaviour, but the single condition with the comment makes the "same message on purpose" rule visible so nobody later splits it.
- **Token contents.** Old: `create_access_token(data={"user_id": user.id})`, a custom claim. New: `create_access_token(user.id)`, which uses the standard `sub` claim (doc 04).
- **Response.** Old: a hand-built dict. New: the `Token` model with `response_model=Token`, so the shape is validated and documented.
- **Query style.** Old: `db.query(...).filter(...).first()`. New: `db.scalar(select(...).where(...))` (Block 17).
- **Column name.** Old model stored the hash in a column called `password`; new model calls it `hashed_password` so its meaning is obvious.

**Register.** Your old `app/routers/user.py`:

```python
router = APIRouter(prefix="/user",tags=["User"])

@router.post("/", response_model=Create_User_Response )
def post_user(user : User , db:Session = Depends(get_db) ):
    hashed_password = utils.hash_password(user.password)
    create_user_table = user_table(email=user.email, password=hashed_password)

    db.add(create_user_table)
    db.commit()
    db.refresh(create_user_table)
    return create_user_table
```

What is the same: hash, build the row, `add` / `commit` / `refresh`, return the object through a response model that hides the password. All of that is kept. What changed, and why:

- **No duplicate check.** The old code went straight to `commit()`. On a duplicate email the unique constraint raised `IntegrityError`, which nobody caught, so the client got **500 Internal Server Error** and a traceback in the log. The new code checks first (409) and also catches the race (409).
- **Status code.** Old: default 200. New: 201 Created, the right code for "a record was made".
- **Validation.** Old `User` schema: any string was accepted as a password. New `UserCreate`: 8 to 128 characters, plus a required `full_name`.
- **Lowercasing** the email, as above.
- **Naming.** `post_user` / `create_user_table` became `register_user` / `user`, and the endpoint moved to `/auth/register` so that "create an account" sits next to "log in".
- One thing I noticed in the old model, mentioned kindly: `User.phone` was declared `nullable=False`, but `post_user` never set it. If the real table had that NOT NULL rule, every registration would have failed with an `IntegrityError`. I cannot see your old database, so I am not 100% sure what happened in practice; it may be that the table was created before that column was added.

The old `GET /user/{id}` endpoint from the same file has no equivalent in the new `auth.py`; it is discussed under `users.py` below.

### Key terms in this file

| Term                        | One-line meaning                                                                              |
| --------------------------- | --------------------------------------------------------------------------------------------- |
| authentication              | Proving who you are (login); authorization is deciding what you may do.                       |
| JWT / access token          | A signed string that identifies the user until it expires; sent as `Authorization: Bearer`.   |
| `Annotated[T, Depends()]`   | "Type `T`, produced by FastAPI by calling `T`"; `Depends()` with no argument uses the type.   |
| `OAuth2PasswordRequestForm` | FastAPI class for the standard login form: fields `username` and `password`, form-encoded.    |
| `username`                  | The OAuth2 standard field name; this project puts the email in it.                            |
| `select(Model).where(...)`  | Build a SELECT statement (SQLAlchemy 2.0 style); replaces `db.query(Model).filter(...)`.      |
| `db.scalar(stmt)`           | Run the statement; return the first column of the first row, or `None`.                       |
| bound parameter             | A value sent to the database separately from the SQL text; prevents SQL injection.            |
| `db.add` / `commit` / `refresh` | Stage a new row; write and finish the transaction; reload the row from the database.       |
| `IntegrityError`            | The database refused a write that would break a rule (UNIQUE, NOT NULL, foreign key, CHECK).  |
| `db.rollback()`             | Undo the failed transaction so the session can be used again.                                 |
| race condition              | Two requests doing the same thing at the same moment; the unique index decides the winner.    |
| `response_model`            | The schema FastAPI uses to filter, validate and document the response; beats the annotation.  |
| `status_code`               | The HTTP status for a successful response (201 for created).                                  |
| 401 / 403 / 409             | Not authenticated / authenticated but not allowed / conflicts with existing data.             |
| `WWW-Authenticate: Bearer`  | Header a 401 must carry; tells the client to use a Bearer token.                              |
| user enumeration            | Learning which emails have accounts from different error messages; avoided by one message.    |
| short-circuit (`or`)        | Python stops evaluating `or` at the first true part, so later parts are safe to skip.         |

## File: app/routers/users.py

### What this file is for

This file has one endpoint, `GET /api/v1/users/me`, which returns the profile of the person whose token is in the request. It is tiny because all the hard work (reading the token, loading the user, rejecting bad tokens with 401) is done by the `CurrentUser` dependency in `app/core/dependencies.py` (doc 04). The endpoint just hands that user back.

It imports `APIRouter` from FastAPI, the `CurrentUser` alias, the `User` model and the `UserResponse` schema. `app/main.py` registers `users.router` under `/api/v1`.

### The whole file

```python
"""Endpoints about the logged-in user's own account."""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, summary="Get my profile")
def get_my_profile(current_user: CurrentUser) -> User:
    return current_user
```

### Walkthrough, block by block

### Block 1: The module docstring

```python
"""Endpoints about the logged-in user's own account."""
```

**Word by word**

- `"""..."""` - module docstring.
- `the logged-in user's own account` - the key design decision: this file only ever talks about *you*, never about other users by id.

**Why it is here.** States the scope.

**If you removed or changed it.** Nothing breaks.

### Block 2: Importing APIRouter

```python
from fastapi import APIRouter
```

**Word by word**

- `APIRouter` - the router class (health.py Block 3). Nothing else from FastAPI is needed: no `HTTPException` (the dependency raises the 401), no `Depends` (it is inside the alias), no `status` (default 200 is right).

**Why it is here.** To create `router` below.

**If you removed or changed it.** `NameError` at import time.

### Block 3: Importing CurrentUser

```python
from app.core.dependencies import CurrentUser
```

**Word by word**

- `app.core.dependencies` - doc 04.
- `CurrentUser` - an alias defined there as `Annotated[User, Depends(get_current_user)]`. Declaring a parameter with this type means: FastAPI reads the `Authorization: Bearer <token>` header, decodes the token, loads the user from the database, checks `is_active`, and passes the `User` object in. If any step fails, the client gets **401** and the endpoint never runs. I checked: `GET /api/v1/users/me` without a token returns `401 {"detail": "Not authenticated"}` with `WWW-Authenticate: Bearer`.

**Why it is here.** This one import is the whole security of the endpoint.

**If you removed or changed it.** `NameError` at import time. If you replaced it with a plain `user_id: int` parameter, anyone could ask for any user.

### Block 4: Importing the User model

```python
from app.models.user import User
```

**Word by word**

- `User` - the model class (auth.py Block 9). Used only in the return annotation `-> User`.

**Why it is here.** For the annotation, which documents to readers and editors what the function returns.

**If you removed or changed it.** `NameError` at import time because the annotation is evaluated when the function is defined.

### Block 5: Importing the response schema

```python
from app.schemas.user import UserResponse
```

**Word by word**

- `UserResponse` - the public view of a user: `id`, `email`, `full_name`, `created_at`, and no password (auth.py Block 11).

**Why it is here.** For `response_model`, so the hash and `is_active` flag never leave the server.

**If you removed or changed it.** `NameError` at import time.

### Block 6: Creating the router

```python
router = APIRouter(prefix="/users", tags=["Users"])
```

**Word by word**

- `prefix="/users"` - all paths here start with `/users`; with `main.py`'s prefix, `/api/v1/users`.
- `tags=["Users"]` - the `/docs` heading.

**Why it is here.** Standard router setup (auth.py Block 12).

**If you removed or changed it.** `NameError` on the decorator below; changing the prefix changes the URL.

### Block 7: The route decorator

```python
@router.get("/me", response_model=UserResponse, summary="Get my profile")
```

**Word by word**

- `@router.get(...)` - GET, because it only reads.
- `"/me"` - a fixed word, not a `{user_id}` placeholder. The full URL is `/api/v1/users/me`. "me" is a common REST convention for "the caller". Because the user comes from the token, there is nothing to look up by id and nothing to get wrong.
- `response_model=UserResponse` - filters the `User` object down to the four public fields.
- `summary="Get my profile"` - the docs title.

**Why it is here.** Registers the endpoint.

**If you removed or changed it.** Without `response_model`, the `-> User` annotation would be used and the app would fail at import with `FastAPIError: Invalid args for response field!` (auth.py Block 13). Changing the path to `/{user_id}` would need a lookup and an ownership check, and would invite the bug discussed in the comparison below.

### Block 8: The function

```python
def get_my_profile(current_user: CurrentUser) -> User:
    return current_user
```

**Word by word**

- `def get_my_profile(...)` - the endpoint function.
- `current_user: CurrentUser` - the logged-in `User`, supplied by the dependency (Block 3). No session parameter is needed, because the dependency already loaded the object.
- `-> User` - return annotation; documentation only, since `response_model` is set.
- `return current_user` - send the object back; FastAPI converts it through `UserResponse`.

I checked: with a valid token, `GET /api/v1/users/me` returns `200` and `{"id": 2, "email": "new@x.com", "full_name": "N", "created_at": "..."}`.

**Why it is here.** The simplest possible protected endpoint: it exists so a frontend can show "logged in as ..." and so you can test that a token works.

**If you removed or changed it.** Remove the parameter and the endpoint becomes public and has nothing to return. Return something else and `UserResponse` validation decides whether it passes.

### Compared to your old code

The old `app/routers/user.py` had:

```python
@router.get("/{id}" ,response_model=Create_User_Response )
def get_user(id : int,db:Session = Depends(get_db)):
    get_user_id = db.query(user_table).filter(user_table.id == id).first()
    return get_user_id
```

Three problems, each fixed by the new design:

1. **No login required.** There is no `get_current_user` dependency, so anyone on the internet could call `GET /user/1`, `GET /user/2`, ... and collect every registered email. The new endpoint requires a token (`CurrentUser`).
2. **Any user could read any other user.** Even with a login check added, a `/{id}` design needs an extra rule "only if `id == current_user.id`". The `/me` design removes the id entirely, so the rule cannot be forgotten.
3. **A missing id returned `None`.** `.first()` gives `None` when there is no row, and the function returned it as-is. With `response_model=Create_User_Response`, FastAPI tries to validate `None` as that model and fails. I reproduced this with a tiny app: the client gets **500 Internal Server Error** instead of a 404.

The old file also contained the registration endpoint, which is now `register_user` in `auth.py` (see that file's comparison).

### Key terms in this file

| Term            | One-line meaning                                                                          |
| --------------- | ----------------------------------------------------------------------------------------- |
| `CurrentUser`   | Alias for `Annotated[User, Depends(get_current_user)]`: the logged-in user, or a 401.     |
| `/me`           | REST convention for "the caller"; avoids ids and ownership checks entirely.               |
| protected endpoint | An endpoint that needs a valid token; declared by taking a `CurrentUser` parameter.    |
| `response_model` | Here it strips `hashed_password` and `is_active` from the returned `User`.               |

## File: app/routers/categories.py

### What this file is for

This file is the full CRUD for categories: create one, list mine, get one, update one, delete one. Every endpoint requires a login (`CurrentUser`), and every database query includes `owner_id == current_user.id`, so a user can never see or touch another user's categories. Two small helper functions at the top (`get_owned_category_or_404` and `ensure_category_name_is_unique`) hold the two rules that several endpoints share, so the rules are written once.

It imports from FastAPI (`APIRouter`, `HTTPException`, `Response`, `status`), from SQLAlchemy (`func`, `select`, `Session`), and from the project: the `CurrentUser` and `DatabaseSession` aliases (doc 04), the `Category` model (doc 06) and the three category schemas (doc 07). `app/main.py` registers `categories.router` under `/api/v1`. `expenses.py` (doc 09) uses the same pattern and also looks up categories by owner.

### The whole file

```python
"""
Category endpoints.

Every query is filtered by `owner_id`, so users can only ever see and
change their own categories.
"""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_owned_category_or_404(db: Session, category_id: int, owner_id: int) -> Category:
    """
    Fetch a category that belongs to the user.

    Someone else's category gives the same 404 as a missing one, so the API
    never reveals which ids exist for other users.
    """
    category = db.scalar(
        select(Category).where(
            Category.id == category_id, Category.owner_id == owner_id
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


def ensure_category_name_is_unique(
    db: Session, owner_id: int, name: str, ignore_category_id: int | None = None
) -> None:
    """Respond 409 if the user already has a category with this name ("Food" == "food")."""
    query = select(Category.id).where(
        Category.owner_id == owner_id,
        func.lower(Category.name) == name.lower(),
    )
    if ignore_category_id is not None:
        # When renaming, the category must not conflict with itself.
        query = query.where(Category.id != ignore_category_id)

    if db.scalar(query) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have a category named '{name}'",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
def create_category(
    category_in: CategoryCreate, db: DatabaseSession, current_user: CurrentUser
) -> Category:
    ensure_category_name_is_unique(db, current_user.id, category_in.name)

    category = Category(**category_in.model_dump(), owner_id=current_user.id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryResponse], summary="List my categories")
def list_categories(db: DatabaseSession, current_user: CurrentUser) -> list[Category]:
    categories = db.scalars(
        select(Category)
        .where(Category.owner_id == current_user.id)
        .order_by(Category.name)
    )
    return list(categories)


@router.get("/{category_id}", response_model=CategoryResponse, summary="Get one category")
def get_category(
    category_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Category:
    return get_owned_category_or_404(db, category_id, current_user.id)


@router.patch("/{category_id}", response_model=CategoryResponse, summary="Update a category")
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Category:
    category = get_owned_category_or_404(db, category_id, current_user.id)

    # exclude_unset=True -> only the fields the client actually sent.
    changes = category_in.model_dump(exclude_unset=True)
    if "name" in changes:
        ensure_category_name_is_unique(
            db, current_user.id, changes["name"], ignore_category_id=category.id
        )

    for field_name, value in changes.items():
        setattr(category, field_name, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
def delete_category(
    category_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Response:
    """The category's expenses are kept and become uncategorized."""
    category = get_owned_category_or_404(db, category_id, current_user.id)
    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

### Walkthrough, block by block

### Block 1: The module docstring

```python
"""
Category endpoints.

Every query is filtered by `owner_id`, so users can only ever see and
change their own categories.
"""
```

**Word by word**

- `"""..."""` - module docstring.
- `Category endpoints.` - the subject.
- `Every query is filtered by owner_id` - the rule of the file: each `SELECT` has `WHERE categories.owner_id = <the logged-in user's id>`. `owner_id` is the foreign-key column in the `categories` table that points to `users.id` (doc 06).
- `so users can only ever see and change their own categories` - the consequence: data isolation between users.

**Why it is here.** It states the one security rule that every endpoint in the file must obey, so a future editor knows not to drop the `owner_id` filter.

**If you removed or changed it.** Nothing breaks.

### Block 2: Importing from FastAPI

```python
from fastapi import APIRouter, HTTPException, Response, status
```

**Word by word**

- `APIRouter`, `HTTPException`, `status` - as before (health.py Block 3).
- `Response` - the class for a raw HTTP response that you build yourself: a status code, optional headers, optional body. I checked: `fastapi.Response` **is** `starlette.responses.Response`, the same class. Used in `delete_category` (Block 45) to send an empty 204.

**Why it is here.** All four are used in this file.

**If you removed or changed it.** `NameError` for the missing name; `Response` is used in a return annotation, so even that one fails at import time.

### Block 3: Importing from SQLAlchemy

```python
from sqlalchemy import func, select
```

**Word by word**

- `func` - a special object: writing `func.anything(...)` builds a call to the SQL function named `anything`. `func.lower(Category.name)` becomes `lower(categories.name)` in SQL. `func.now()` in the models is the same idea. SQLAlchemy does not check the function name; the database does, when the query runs.
- `select` - the statement builder (auth.py Block 5).

**Why it is here.** `func.lower` for the case-insensitive name check (Block 17); `select` everywhere.

**If you removed or changed it.** `NameError` at request time (both names are used inside functions).

### Block 4: Importing Session

```python
from sqlalchemy.orm import Session
```

**Word by word**

- `sqlalchemy.orm` - the Object Relational Mapper part of SQLAlchemy (models, sessions, relationships).
- `Session` - the class of the database session object. It is imported here **only for type hints** on the helper functions (`db: Session` in Blocks 10 and 15). The endpoints use the `DatabaseSession` alias instead.

**Why `Session` here and `DatabaseSession` there?** The helpers are plain Python functions, called by the endpoints with `db` passed in as an ordinary argument. `Depends` only means something to FastAPI when it inspects an *endpoint's* parameters; it would be meaningless on a helper. So the helpers say "I take a `Session`", and the endpoints, which FastAPI does inspect, say "give me a `DatabaseSession`".

**Why it is here.** Correct type hints on the helpers, so editors can autocomplete `db.scalar(...)`.

**If you removed or changed it.** `NameError` at import time (annotations in a `def` line are evaluated when the file loads). Using `DatabaseSession` on the helpers instead would not break anything either (it is `Annotated[Session, ...]`, and plain Python ignores the extra part), but it would be misleading.

### Block 5: Importing the dependency aliases

```python
from app.core.dependencies import CurrentUser, DatabaseSession
```

**Word by word**

- `CurrentUser` - the logged-in user or a 401 (users.py Block 3).
- `DatabaseSession` - one session per request (auth.py Block 7).

**Why it is here.** Every endpoint in this file takes both.

**If you removed or changed it.** `NameError` at import time.

### Block 6: Importing the Category model

```python
from app.models.category import Category
```

**Word by word**

- `Category` - the model class for the `categories` table (doc 06): columns `id`, `name`, `description`, `owner_id`, `created_at`, plus a unique constraint on `(owner_id, name)` named `uq_categories_owner_id_name`.

**Why it is here.** Every query and insert in this file is about this table.

**If you removed or changed it.** `NameError` at import time (used in return annotations).

### Block 7: Importing the category schemas

```python
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
```

**Word by word**

- `CategoryCreate` - the body of POST: `name` (1 to 50 characters, trimmed) and optional `description` (up to 255 characters).
- `CategoryResponse` - the output: `id`, `name`, `description`, `created_at`. Note that `owner_id` is not included; the caller already knows it is theirs.
- `CategoryUpdate` - the body of PATCH: both fields optional, with a validator that rejects `"name": null` (doc 07).

**Why it is here.** Input validation and output shaping for the endpoints.

**If you removed or changed it.** `NameError` at import time.

### Block 8: Creating the router

```python
router = APIRouter(prefix="/categories", tags=["Categories"])
```

**Word by word**

- `prefix="/categories"` - with `main.py`'s prefix: `/api/v1/categories`.
- `tags=["Categories"]` - the `/docs` heading. I checked the OpenAPI: all five endpoints carry `tags: ["Categories"]`.

**Why it is here.** Standard router setup (auth.py Block 12).

**If you removed or changed it.** `NameError` on the decorators; changing the prefix changes every URL in the file.

### Block 9: The "Helpers" banner

```python
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
```

**Word by word**

- `#` - starts a comment; Python ignores the rest of the line.
- The dashes are a visual ruler. `Helpers` is the section title: the functions below are not endpoints, they are shared pieces the endpoints call.

**Why it is here.** It splits the file into "shared rules" and "endpoints" so you can find things fast.

**If you removed or changed it.** Nothing breaks.

### Block 10: The first helper's header

```python
def get_owned_category_or_404(db: Session, category_id: int, owner_id: int) -> Category:
```

**Word by word**

- `def get_owned_category_or_404(...)` - a plain function (no decorator, so it is not an endpoint). The name says exactly what it does: get a category the user owns, or respond 404.
- `db: Session` - the session, passed in by the caller (Block 4).
- `category_id: int` - which category.
- `owner_id: int` - whose category it must be.
- `-> Category` - it returns a `Category` object. When it cannot, it raises instead of returning `None`, so callers never need to check for `None`.

**Why it is here.** Three endpoints (get, update, delete) need "load this category, but only if it is mine, else 404". Writing it once means the ownership rule cannot be forgotten in one of them.

**If you removed or changed it.** The three endpoints would hit `NameError`. If you removed the `owner_id` parameter, every user could read, rename and delete every other user's categories.

### Block 11: The first helper's docstring

```python
    """
    Fetch a category that belongs to the user.

    Someone else's category gives the same 404 as a missing one, so the API
    never reveals which ids exist for other users.
    """
```

**Word by word**

- `"""..."""` - a function docstring. Because this is not an endpoint, FastAPI does not show it anywhere; it is for readers of the code.
- `Fetch a category that belongs to the user.` - the job.
- `Someone else's category gives the same 404 as a missing one` - the design decision. The query asks for `id = X AND owner_id = me`; if the row has a different owner, the query simply finds nothing, which is reported exactly like "no such id".
- `so the API never reveals which ids exist for other users` - the reason. If the API answered 403 ("exists, but not yours") for other people's ids and 404 for unused ids, a caller could scan ids and learn how many categories other users have and when they were created. Ids are sequential integers, so this is easy to probe.

**Why it is here.** It explains the one non-obvious choice in the helper.

**If you removed or changed it.** Nothing breaks.

### Block 12: The ownership query

```python
    category = db.scalar(
        select(Category).where(
            Category.id == category_id, Category.owner_id == owner_id
        )
    )
```

**Word by word**

- `category = db.scalar(...)` - the `Category` object or `None` (auth.py Block 17).
- `select(Category)` - all columns of `categories`, as `Category` objects.
- `.where(cond1, cond2)` - two conditions separated by a comma. SQLAlchemy joins several conditions given to one `where(...)` with `AND`.
- `Category.id == category_id` - the id the client asked for.
- `Category.owner_id == owner_id` - the ownership rule.
- The line breaks inside the parentheses are formatting.

The SQL (compiled for PostgreSQL):

```sql
SELECT categories.id, categories.name, categories.description, categories.owner_id, categories.created_at
FROM categories
WHERE categories.id = %(id_1)s AND categories.owner_id = %(owner_id_1)s
```

**Why it is here.** The ownership check is *inside the query*, not a separate `if` after loading the row. That is both faster (no row is loaded for someone else's category) and safer (there is no "load first, check later" step to forget).

**If you removed or changed it.** Drop the second condition and the helper would return other users' categories. Compare with `=` instead of `==` and you would get a Python `SyntaxError` (assignment is not allowed there).

### Block 13: The 404

```python
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
```

**Word by word**

- `if category is None:` - no row matched both conditions.
- `raise HTTPException(...)` - stop and send the error.
- `status.HTTP_404_NOT_FOUND` - the number 404. **404 Not Found** means "there is no resource at this address, for you". It is the right code both for an id that does not exist and for an id you may not see, as Block 11 explains.
- `detail="Category not found"` - a neutral message that does not say which of the two cases it was. I checked: asking for a deleted category gives `404 {"detail": "Category not found"}`.

**Why it is here.** It converts "nothing found" into a clean HTTP answer and stops the calling endpoint from continuing with `None`.

**If you removed or changed it.** Without the `if`, the helper would return `None`, and the callers would crash on `None.name` (500) or return `None` through `CategoryResponse` (500). Changing the code to 403 for other people's categories would reveal which ids exist.

### Block 14: Returning the category

```python
    return category
```

**Word by word**

- `return category` - the found object goes back to the endpoint.

**Why it is here.** After the `None` check, `category` is guaranteed to be a real `Category`; the `-> Category` annotation is honest.

**If you removed or changed it.** The function would return `None` for every found category; all three callers would break.

### Block 15: The second helper's header

```python
def ensure_category_name_is_unique(
    db: Session, owner_id: int, name: str, ignore_category_id: int | None = None
) -> None:
```

**Word by word**

- `def ensure_category_name_is_unique(...)` - a plain function whose name reads like a sentence: "ensure the category name is unique". It either returns quietly or raises 409.
- `db: Session`, `owner_id: int` - as in Block 10.
- `name: str` - the name the client wants to use.
- `ignore_category_id: int | None = None` - an optional parameter. `int | None` is Python's union syntax (3.10 and later): the value is either an `int` or `None`. `= None` is the default, so callers may leave it out. When renaming an existing category, the caller passes that category's own id here, so the category is not reported as clashing with itself (Block 18).
- `-> None` - the function returns nothing useful. Its effect is either "fine, carry on" or an exception.

**Why it is here.** Both create and update need "no other category of mine has this name". One function, two callers.

**If you removed or changed it.** `NameError` in `create_category` and `update_category`. Without the check altogether, a user could create "Food" twice, which would make reports by category confusing; the database constraint would stop *exact* duplicates with an `IntegrityError` (a 500), but not `Food` / `food`.

### Block 16: The second helper's docstring

```python
    """Respond 409 if the user already has a category with this name ("Food" == "food")."""
```

**Word by word**

- `Respond 409` - the outcome on a clash (Block 19).
- `if the user already has a category with this name` - scoped to one user; two different users may both have "Food".
- `("Food" == "food")` - the comparison ignores letter case.

**Why it is here.** One line that states the rule and the case-insensitivity.

**If you removed or changed it.** Nothing breaks.

### Block 17: The uniqueness query

```python
    query = select(Category.id).where(
        Category.owner_id == owner_id,
        func.lower(Category.name) == name.lower(),
    )
```

**Word by word**

- `query =` - a variable holding the statement. It is stored in a variable because Block 18 may add another condition to it before it runs.
- `select(Category.id)` - select **only the `id` column**, not the whole row. We only need to know whether a row exists, so loading `name`, `description` and the rest would be wasted work. `db.scalar` on this returns an `int` or `None`.
- `.where(cond1, cond2)` - two conditions, joined with `AND`.
- `Category.owner_id == owner_id` - only this user's categories.
- `func.lower(Category.name)` - the SQL function `lower(...)` applied to the column (Block 3): the stored name, in lowercase, computed by the database.
- `==` - SQL equality.
- `name.lower()` - the Python string method: the requested name, in lowercase, computed in Python. Both sides lowercase, so `Food` matches `food` and `FOOD`.

The SQL:

```sql
SELECT categories.id
FROM categories
WHERE categories.owner_id = %(owner_id_1)s AND lower(categories.name) = %(lower_1)s
```

I checked on real data: with a stored category `Food`, the query with `"FOOD".lower()` found it (id returned), while a plain `Category.name == "FOOD"` found nothing. So `func.lower` is what makes the rule case-insensitive. Note that the database's own unique constraint `(owner_id, name)` is case-sensitive, so this Python-level check is *stricter* than the constraint; the constraint is the backstop for exact duplicates.

**Why it is here.** People do not think of "food" and "Food" as two categories; the API should not either.

**If you removed or changed it.** Drop `func.lower(...)` / `.lower()` and `Food` and `food` could both be created. Drop the `owner_id` condition and you could not create "Food" if *any other user* already had it.

### Block 18: Excluding the category itself

```python
    if ignore_category_id is not None:
        # When renaming, the category must not conflict with itself.
        query = query.where(Category.id != ignore_category_id)
```

**Word by word**

- `if ignore_category_id is not None:` - only when the caller passed an id (the update case).
- The comment explains the case: a PATCH that sends the same name the category already has (`Food` -> `Food`, or `Food` -> `FOOD`) must not be rejected as a clash with itself.
- `query = query.where(...)` - **assignment back is required.** `.where()` returns a new statement and leaves the old one unchanged (I checked: the original has no `WHERE` added, the returned one does). Without the `query =` part, the extra condition would be built and thrown away.
- `Category.id != ignore_category_id` - SQL `!=`: any category except this one.

The SQL becomes:

```sql
... WHERE categories.owner_id = %(owner_id_1)s AND lower(categories.name) = %(lower_1)s AND categories.id != %(id_1)s
```

I checked the behaviour: renaming category `Food` to `FOOD` with PATCH returns `200`, not 409.

**Why it is here.** Without it, every PATCH that re-sent the current name (common for forms that send all fields) would fail with 409.

**If you removed or changed it.** Renaming a category to a different-case version of its own name would be impossible, and re-sending the same name would be a 409. If you wrote `query.where(...)` without `query =`, the condition would be silently lost and the same bug would appear.

### Block 19: The 409

```python
    if db.scalar(query) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have a category named '{name}'",
        )
```

**Word by word**

- `db.scalar(query)` - run the final statement; an `int` id if a clashing category exists, else `None`.
- `is not None` - "a clash exists".
- `status.HTTP_409_CONFLICT` - 409, the "clashes with existing data" code (auth.py Block 15).
- `detail=f"..."` - an **f-string**: a string with `f` before the opening quote, in which `{name}` is replaced by the value of the variable `name`. So the message names the clashing category, for example `You already have a category named 'food'`. I checked that exact response: creating `food` when `Food` exists gives `409`.
- Here it is fine to name the clash, because the clash is with the caller's *own* data.

**Why it is here.** A clear, specific error for the one business rule of categories.

**If you removed or changed it.** Without the `if`, duplicates would be allowed up to the database constraint (which then gives a 500 for exact duplicates). Using a plain string without `f` would literally send `{name}` in the message.

### Block 20: The "Endpoints" banner

```python
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
```

**Word by word**

- Comments forming a ruler and the title `Endpoints`: from here on, every function has a `@router...` decorator.

**Why it is here.** Navigation.

**If you removed or changed it.** Nothing breaks.

### Block 21: The create decorator

```python
@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
```

**Word by word**

- `@router.post(...)` - POST creates.
- `""` - the **empty string** as the path. The router prefix is `/categories` and the empty path adds nothing, so the URL is `/api/v1/categories` with **no trailing slash**. I checked the OpenAPI: the path is `/api/v1/categories`. (Your old code used `"/"`, which produced `/posts/` with a slash; see the comparison.) FastAPI also redirects the other spelling: I checked that `POST /api/v1/categories/` answers `307 Temporary Redirect` to `/api/v1/categories`, and most clients follow it.
- `response_model=CategoryResponse` - output shape (auth.py Block 13).
- `status_code=status.HTTP_201_CREATED` - 201 for "created". I checked: a successful create returns 201.
- `summary="Create a category"` - the docs title.

**Why it is here.** Registers `POST /api/v1/categories`.

**If you removed or changed it.** Without `response_model`, the `-> Category` annotation would cause the import-time `FastAPIError` seen in auth.py Block 13. Without `status_code`, clients would get 200.

### Block 22: The create function header

```python
def create_category(
    category_in: CategoryCreate, db: DatabaseSession, current_user: CurrentUser
) -> Category:
```

**Word by word**

- `category_in: CategoryCreate` - the JSON body, validated: a non-empty `name` up to 50 characters (surrounding spaces removed) and an optional `description`. A bad body is a 422 before this function runs.
- `db: DatabaseSession` - the session.
- `current_user: CurrentUser` - the logged-in user, or a 401 before this function runs.
- `-> Category` - documentation; `response_model` decides the real output.

**Why it is here.** Input, database, identity: the three things every write endpoint needs.

**If you removed or changed it.** Drop `current_user` and the endpoint becomes public and has no owner to assign; the insert would fail on the NOT NULL `owner_id` (500).

### Block 23: Checking the name

```python
    ensure_category_name_is_unique(db, current_user.id, category_in.name)
```

**Word by word**

- `ensure_category_name_is_unique(...)` - the helper from Block 15, called with positional arguments: the session, `current_user.id` (the owner), and `category_in.name` (the requested name). `ignore_category_id` is left at its default `None`, because a new category has no id yet.
- The return value is ignored; the call either passes silently or raises 409.

**Why it is here.** The uniqueness rule, applied before anything is written.

**If you removed or changed it.** A user could create `Food` and `food`; an exact duplicate `Food` / `Food` would reach the database constraint and come back as a 500.

### Block 24: Building the category

```python
    category = Category(**category_in.model_dump(), owner_id=current_user.id)
```

**Word by word**

- `category = Category(...)` - a new model instance (auth.py Block 18).
- `category_in.model_dump()` - the Pydantic method that turns the schema object into a plain dictionary. I checked: `CategoryCreate(name="Food").model_dump()` gives `{'name': 'Food', 'description': None}`.
- `**` - the **dictionary unpacking** operator in a function call: it spreads the dictionary into keyword arguments. `Category(**{'name': 'Food', 'description': None})` is the same as `Category(name='Food', description=None)`. (One star, `*`, would spread a list into positional arguments; two stars spread a dict into keyword arguments.)
- `, owner_id=current_user.id` - one more keyword argument added by hand. The owner is **never taken from the request body**; it always comes from the token. The schema does not even have an `owner_id` field, so a client cannot try to set it.

**Why it is here.** It copies the validated fields into the model in one line and attaches the owner from the trusted source. You wrote the same pattern in the old project (`table(**post.model_dump(), owner_id=current_user.id)`).

**If you removed or changed it.** Leave out `owner_id` and the insert fails (NOT NULL), a 500. Take `owner_id` from the body and users could create categories under someone else's account.

### Block 25: Writing the category

```python
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
```

**Word by word**

- `db.add(category)` - stage the insert (auth.py Block 19).
- `db.commit()` - run the `INSERT` and make it permanent (auth.py Block 20). This is not wrapped in `try/except IntegrityError`. Honest note: if two requests from the same user created the same name at the exact same moment, both could pass Block 23 and the second `commit()` would raise `IntegrityError` from the database constraint, giving a 500 instead of a 409. The auth router handles this case; this one does not. It is rare (one user racing with themselves), but it is a small gap you could close with the same `try/except` pattern.
- `db.refresh(category)` - reload `id` and `created_at` from the database (auth.py Block 21).
- `return category` - converted through `CategoryResponse`. I checked: `201 {"id": 4, "name": "Food", "description": null, "created_at": "..."}`.

**Why it is here.** The standard write sequence.

**If you removed or changed it.** Without `add`, nothing is inserted and `refresh` raises. Without `commit`, the insert is rolled back when `get_db` closes the session and the client gets a 201 for a category that does not exist. Without `refresh`, the response would still be correct here (attributes reload on access, as explained in auth.py Block 21).

### Block 26: The list decorator

```python
@router.get("", response_model=list[CategoryResponse], summary="List my categories")
```

**Word by word**

- `@router.get("")` - GET on the empty path: `GET /api/v1/categories`. The same URL as create, different method; FastAPI routes by method and path together.
- `response_model=list[CategoryResponse]` - a **list of** `CategoryResponse`. Square brackets after `list` say what the items are. FastAPI converts each `Category` object in the returned list through `CategoryResponse`, and documents the response as a JSON array.
- `summary="List my categories"` - the docs title. "my" because the owner filter is built in.
- Default status 200.

**Why it is here.** Registers the list endpoint.

**If you removed or changed it.** Without `response_model`, the `-> list[Category]` annotation would be tried and fail at import (same `FastAPIError` as before, since `Category` is not a Pydantic type).

### Block 27: The list function header

```python
def list_categories(db: DatabaseSession, current_user: CurrentUser) -> list[Category]:
```

**Word by word**

- `db: DatabaseSession`, `current_user: CurrentUser` - session and identity. No body (GET) and no path parameters.
- `-> list[Category]` - returns a Python list of `Category` objects.

**Why it is here.** Declares what the endpoint needs.

**If you removed or changed it.** Drop `current_user` and there is no owner to filter by: either the endpoint lists everyone's categories (if you also dropped the filter) or hits `NameError`.

### Block 28: The list query

```python
    categories = db.scalars(
        select(Category)
        .where(Category.owner_id == current_user.id)
        .order_by(Category.name)
    )
```

**Word by word**

- `categories =` - the result object.
- `db.scalars(...)` - like `db.scalar` but for **many rows**. I read the SQLAlchemy source: `scalars` runs the statement and calls `.scalars()` on the result, which gives a `ScalarResult`: an object you can loop over, where each item is the first column of a row, here a `Category` object. It has `.all()`, `.first()`, `.one()`, `.one_or_none()` and can be iterated once. I checked: iterating it a second time gives an empty list, because the rows were consumed the first time.
- `select(Category)` - all columns, as objects.
- `.where(Category.owner_id == current_user.id)` - only mine.
- `.order_by(Category.name)` - sorted by name, ascending (A to Z). Each method call is on its own line; this is called **method chaining**, and the line breaks are allowed because the whole thing is inside the `db.scalars(` parentheses.

The SQL:

```sql
SELECT categories.id, categories.name, categories.description, categories.owner_id, categories.created_at
FROM categories
WHERE categories.owner_id = %(owner_id_1)s ORDER BY categories.name
```

**`db.scalar` versus `db.scalars`.** `scalar` (singular): one value, the first column of the first row, or `None`; use it when you expect at most one row. `scalars` (plural): a stream of values, one per row; use it for lists. Both replace the old `db.query(...)`: `.first()` maps to `scalar`, `.all()` maps to `list(scalars(...))` or `scalars(...).all()`.

**Why it is here.** The one query of the endpoint, with the owner filter and a stable order so the frontend does not need to sort.

**If you removed or changed it.** Drop the `where` and every user would see every category. Drop `order_by` and the order would be whatever PostgreSQL happens to return (usually insertion order, but not guaranteed).

### Block 29: Returning the list

```python
    return list(categories)
```

**Word by word**

- `list(...)` - the built-in that consumes an iterable and builds a Python list from it. I checked: `list(db.scalars(...))` gave `[(2, 'Food'), (1, 'Rent'), (3, 'Travel')]` when printed as `(id, name)` pairs, in name order.
- `return` - FastAPI converts each item via `CategoryResponse`. An empty result gives `[]` with 200, not an error.

**Why it is here.** FastAPI needs a real list to serialise; a `ScalarResult` is a cursor-like object, not JSON. `categories.all()` would do the same job; `list(...)` is plain Python.

**If you removed or changed it.** Honest answer: returning the `ScalarResult` directly would also work. I tried it: FastAPI still answered 200 with the JSON array, because Pydantic accepts any iterable when validating a `list` field. `list(...)` is still the better habit: it makes the function really return the `list[Category]` its annotation promises, it is clearer to read, and it is easier to inspect in a test. Raising an error when the list is empty (as the old code did) would make "no categories yet" look like a failure.

### Block 30: The get-one decorator

```python
@router.get("/{category_id}", response_model=CategoryResponse, summary="Get one category")
```

**Word by word**

- `@router.get(...)` - GET.
- `"/{category_id}"` - a path with a **path parameter**. The curly braces mark a placeholder: `/api/v1/categories/7` matches, and `7` is captured under the name `category_id`. FastAPI passes it to the function parameter with the same name.
- `response_model=CategoryResponse` - one category out.
- `summary="Get one category"` - the docs title.

**Why it is here.** Registers `GET /api/v1/categories/{category_id}`.

**If you removed or changed it.** If the placeholder name and the function parameter name did not match, FastAPI would treat the function parameter as a query parameter and the path value would be ignored.

### Block 31: The get-one function header

```python
def get_category(
    category_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Category:
```

**Word by word**

- `category_id: int` - the path value, converted to an integer. If it cannot be converted, FastAPI answers 422 before the function runs. I checked: `GET /api/v1/categories/abc` gives `422` with `Input should be a valid integer` and `loc: ["path", "category_id"]`.
- `db`, `current_user` - session and identity.
- `-> Category` - documentation.

**Why it is here.** Declares the id, the session and the identity.

**If you removed or changed it.** Annotating `category_id: str` would pass `"abc"` into the query, where PostgreSQL would reject comparing an integer column to text (a 500).

### Block 32: Delegating to the helper

```python
    return get_owned_category_or_404(db, category_id, current_user.id)
```

**Word by word**

- `get_owned_category_or_404(db, category_id, current_user.id)` - the helper from Block 10: the category if it exists **and is mine**, else a 404 is raised inside the helper.
- `return` - the found object, converted through `CategoryResponse`.

I checked: my own category gives `200` with its fields; a deleted or foreign id gives `404 {"detail": "Category not found"}`.

**Why it is here.** The whole endpoint is one line because the rule lives in the helper.

**If you removed or changed it.** Replacing the helper with `db.get(Category, category_id)` (a lookup by primary key only) would drop the ownership check and expose other users' categories.

### Block 33: The update decorator

```python
@router.patch("/{category_id}", response_model=CategoryResponse, summary="Update a category")
```

**Word by word**

- `@router.patch(...)` - HTTP **PATCH** means "change some fields of an existing resource". Compare **PUT**, which means "replace the whole resource" and therefore expects every field. Your old code used PUT; the comparison below explains the switch.
- `"/{category_id}"` - the same path parameter as Block 30.
- `response_model=CategoryResponse` - the updated category is returned in full.
- `summary="Update a category"` - the docs title.

**Why it is here.** Registers `PATCH /api/v1/categories/{category_id}`.

**If you removed or changed it.** Changing it to `router.put` would keep the code working but would mislabel the operation: PUT clients expect to send all fields, and this endpoint accepts any subset.

### Block 34: The update function header

```python
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Category:
```

**Word by word**

- `category_id: int` - from the path.
- `category_in: CategoryUpdate` - the JSON body, in which every field is optional. The schema's validator rejects `"name": null` with a 422 (I checked: `PATCH ... {"name": null}` gives `422` with `name cannot be null`), because a category must always have a name.
- `db`, `current_user` - session and identity.
- `-> Category` - documentation.
- One parameter per line with a trailing comma: formatting.

**Why it is here.** It declares all four inputs an update needs.

**If you removed or changed it.** Using `CategoryCreate` as the body type would make `name` required on every PATCH, turning it into a PUT in disguise.

### Block 35: Loading the category

```python
    category = get_owned_category_or_404(db, category_id, current_user.id)
```

**Word by word**

- The same helper call as Block 32, but this time the result is kept in `category` so it can be changed.

**Why it is here.** Ownership check plus load, before any change.

**If you removed or changed it.** No category to update; `NameError` below.

### Block 36: Extracting only the sent fields

```python
    # exclude_unset=True -> only the fields the client actually sent.
    changes = category_in.model_dump(exclude_unset=True)
```

**Word by word**

- The comment states the key idea of a PATCH in one line.
- `changes =` - a dictionary of field name to new value.
- `category_in.model_dump(...)` - Pydantic's "give me a dict" method (Block 24).
- `exclude_unset=True` - a keyword argument that means "leave out every field the client did not send". Pydantic tracks which fields were **set** by the input (it keeps them in `model_fields_set`) versus which merely took their default. I checked all the cases:
  - `CategoryUpdate(name="Food").model_dump()` gives `{'name': 'Food', 'description': None}` (the default for `description` is included),
  - `CategoryUpdate(name="Food").model_dump(exclude_unset=True)` gives `{'name': 'Food'}` and `model_fields_set` is `{'name'}`,
  - `CategoryUpdate(description=None).model_dump(exclude_unset=True)` gives `{'description': None}` - the client **did** send `description: null`, so it is kept, meaning "clear the description",
  - `CategoryUpdate().model_dump(exclude_unset=True)` gives `{}` - an empty PATCH changes nothing.

**Why it is here.** This is the difference between "the client did not mention `description`" (leave it alone) and "the client sent `description: null`" (clear it). A plain `model_dump()` cannot tell those apart, because both give `None`.

**If you removed or changed it.** With `model_dump()` and no `exclude_unset`, a PATCH with only `{"name": "Food"}` would also set `description` to `None`, silently wiping the description every time someone renamed a category. I checked the correct behaviour: `PATCH {"description": "Eating out"}` returns the category with the new description **and the old name untouched**.

### Block 37: Checking the new name

```python
    if "name" in changes:
        ensure_category_name_is_unique(
            db, current_user.id, changes["name"], ignore_category_id=category.id
        )
```

**Word by word**

- `if "name" in changes:` - `in` on a dictionary tests whether the key exists. So this reads: "only if the client sent a name".
- `ensure_category_name_is_unique(...)` - the helper from Block 15.
- `changes["name"]` - the new name, looked up by key.
- `ignore_category_id=category.id` - a keyword argument: "do not count this category as a clash with itself" (Block 18).

**Why it is here.** The uniqueness rule applies to renames too, but only when a name was actually sent, and never against the category's own current name.

**If you removed or changed it.** Without the `if`, `changes["name"]` would raise `KeyError` (500) on any PATCH that did not include a name. Without `ignore_category_id`, re-sending the current name would be a 409.

### Block 38: Applying the changes

```python
    for field_name, value in changes.items():
        setattr(category, field_name, value)
```

**Word by word**

- `for ... in ...:` - a loop.
- `changes.items()` - the dictionary method that yields `(key, value)` pairs. I checked: `{"name": "Food", "description": None}.items()` yields `('name', 'Food')` then `('description', None)`.
- `field_name, value` - the two parts of each pair, unpacked into two variables.
- `setattr(category, field_name, value)` - the built-in function "set attribute": `setattr(obj, "name", "Food")` is exactly `obj.name = "Food"`, but with the attribute **name as a string**, which is what makes a loop possible. You cannot write `category.field_name = value` (that would set an attribute literally called `field_name`).
- SQLAlchemy notices each assignment. I checked: after the loop, `category in db.dirty` is `True`, and at commit it emitted `UPDATE categories SET name=? WHERE categories.id = ?`. Only the column whose value actually changed was in the `SET`; a field set to the value it already had is not written.

**Why it is here.** It applies whatever subset of fields the client sent, without a chain of `if "name" in changes: category.name = ...` lines for each field. Adding a field to the schema later needs no change here.

**If you removed or changed it.** No changes would be applied, and the endpoint would return the category unchanged with 200. Note the loop trusts `changes` to contain only real column names; that is guaranteed because `CategoryUpdate` only has `name` and `description`, and Pydantic drops unknown keys from the input.

### Block 39: Saving and returning

```python
    db.commit()
    db.refresh(category)
    return category
```

**Word by word**

- `db.commit()` - the pending `UPDATE` is sent and committed. No `db.add` is needed: the object came out of a query on this session, so the session already tracks it.
- `db.refresh(category)` - reload from the database.
- `return category` - through `CategoryResponse`. I checked: `PATCH {"name": "FOOD"}` returns `200` with `"name": "FOOD"` and the description preserved.

**Why it is here.** Standard save-and-return.

**If you removed or changed it.** Without `commit`, the changes are rolled back when the session closes, but the response would still show them (the object in memory was changed), which is a confusing lie. Without `refresh`, the response would still be correct (attributes reload on access).

### Block 40: The delete decorator

```python
@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
```

**Word by word**

- `@router.delete(...)` - HTTP **DELETE**.
- `"/{category_id}"` - the path parameter.
- `status_code=status.HTTP_204_NO_CONTENT` - 204. **204 No Content** means "done, and there is nothing to send back". It is the conventional answer for a successful delete. FastAPI also uses it in the docs: I checked the OpenAPI, which lists `204` as the success response for this endpoint.
- `summary="Delete a category"` - the docs title.
- **No `response_model`**, on purpose. I read FastAPI's `is_body_allowed_for_status_code`: for 204 (and 205, 304, and anything below 200) it returns `False`, and the router asserts that a route with a response model must be allowed a body. I tried `@router.delete("/x", status_code=204, response_model=dict)`: it fails at import with `AssertionError: Status code 204 must not have a response body`.

**Why it is here.** Registers `DELETE /api/v1/categories/{category_id}` with the correct empty-success code.

**If you removed or changed it.** Without `status_code`, a successful delete would answer 200 with the body returned by the function; since the function returns an explicit 204 `Response` (Block 45), the real status would still be 204 but the docs would say 200.

### Block 41: The delete function header

```python
def delete_category(
    category_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Response:
```

**Word by word**

- `category_id: int`, `db`, `current_user` - as before.
- `-> Response` - the function returns a raw `Response` object (Block 2). This matters for FastAPI: I read the source, and when `response_model` is not given, FastAPI looks at the return annotation; if it is a `Response` subclass, it sets the response model to `None` instead of trying to build a schema from it. I also tried the alternative: `-> dict` with `status_code=204` fails at import with the same `AssertionError: Status code 204 must not have a response body`, because `dict` would become a response model.

**Why it is here.** The `-> Response` annotation is what makes a 204 route with no response model type-check cleanly in FastAPI.

**If you removed or changed it.** Removing the annotation would also work (no annotation, no response model). Changing it to a data type would break the app at import.

### Block 42: The delete docstring

```python
    """The category's expenses are kept and become uncategorized."""
```

**Word by word**

- A function docstring; because this *is* an endpoint, FastAPI shows it in `/docs` as the description.
- `The category's expenses are kept` - deleting a category does **not** delete the expenses in it.
- `and become uncategorized` - their `category_id` becomes `NULL`. This is done by the database: `expenses.category_id` is declared `ForeignKey("categories.id", ondelete="SET NULL")` (I checked `app/models/expense.py`, line 62). PostgreSQL applies the rule itself when the `DELETE` runs. The `Category.expenses` relationship has `passive_deletes=True` (doc 06), which tells SQLAlchemy not to load the expenses and null them out one by one in Python, but to leave it to the database.

**Why it is here.** This is the one thing an API user would worry about before deleting a category, so it is stated where they will see it.

**If you removed or changed it.** Nothing breaks; the description disappears from `/docs`.

### Block 43: Loading the category

```python
    category = get_owned_category_or_404(db, category_id, current_user.id)
```

**Word by word**

- The helper again (Block 10): the category if it is mine, else 404.

**Why it is here.** You can only delete what you own, and the 404 for "not mine" keeps ids private.

**If you removed or changed it.** Without the ownership check, any user could delete any category.

### Block 44: Deleting

```python
    db.delete(category)
    db.commit()
```

**Word by word**

- `db.delete(category)` - SQLAlchemy's doc: "Mark an instance as deleted." Nothing is sent yet. I checked: right after this call, `category in db.deleted` is `True` and no SQL has run.
- `db.commit()` - flush sends `DELETE FROM categories WHERE categories.id = ?` (I captured it), the database applies `ON DELETE SET NULL` to the expenses, and the transaction is committed.

**Why it is here.** The actual removal, as a two-step "mark, then commit" so it takes part in the same transaction as anything else the request did.

**If you removed or changed it.** Without `commit`, the delete is rolled back when the session closes and the client gets a 204 for a category that still exists. I checked the correct behaviour: after the delete, a second `DELETE` of the same id gives `404`.

### Block 45: The empty 204 response

```python
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

**Word by word**

- `Response(...)` - build a raw response (Block 2).
- `status_code=status.HTTP_204_NO_CONTENT` - 204, matching the decorator.
- No body argument, so the body is empty. I checked: `Response(status_code=204)` has `body == b''` and no headers at all.
- I read the FastAPI source: when an endpoint returns a `Response` object, FastAPI sends it **as-is** (it only attaches background tasks); no JSON encoding, no response model. I checked the real call: `DELETE /api/v1/categories/4` answers `204` with an empty body (`b''`) and no `content-length`.

**Why it is here.** 204 must have no body. Returning `None` would also produce an empty 204 in current FastAPI, but returning an explicit `Response` makes the intent unmistakable and does not depend on how FastAPI treats `None`. Your old `delete_all` did exactly this, correctly.

**If you removed or changed it.** Returning a dict such as `{"message": "deleted"}` would be a mismatch: the decorator promises 204 and 204 may not carry a body. (The old `delete_post` returned a dict with `"status code": 204` inside it while the real HTTP status was 200, which is the confusion this line avoids.)

### Compared to your old code

The old `app/routers/post.py` is the closest match: it was the CRUD for posts, as this file is the CRUD for categories. I go through it endpoint by endpoint.

**List.** Old:

```python
@router.get("/",response_model=List[Post])
def get_post(db: Session = Depends(get_db), current_user: int = Depends(get_current_user), limit : int = 10 , skip : int = 3, search : Optional[str] = ""):
    # posts = db.query(table).filter(table.owner_id ==current_user.id ).all()
    posts = db.query(table).filter(table.title.contains(search)).limit(limit).offset(skip).all()
    if  len(posts) == 0:
        raise HTTPException(status_code=status.HTTP_200_OK ,detail=f"No posts found")
    return  posts
```

- The owner filter is in a **comment**, so every logged-in user saw every user's posts. The new `list_categories` always filters by `owner_id`.
- `skip : int = 3` skips the first three posts by default; that looks like a leftover from testing. The new endpoint has no paging (a user has few categories); `expenses.py` has proper `limit`/`offset` with defaults of 20 and 0 (doc 09).
- An empty result raised `HTTPException(status_code=200, detail="No posts found")`: an error-shaped body `{"detail": ...}` with a success code, which also breaks any client expecting a list. The new endpoint returns `[]` with 200.
- `current_user: int` says the value is an integer, but `get_current_user` returns a `User` object; the annotation was wrong. The new `CurrentUser` alias carries the right type.
- `@router.get("/")` with prefix `/posts` gave the URL `/posts/` (with a slash). The new file uses `""` so the URL is `/api/v1/categories`.
- `List[Post]` and `Optional[str]` are the older `typing` spellings; the new code writes `list[CategoryResponse]` and `str | None`, which mean the same and need no import.

**Get one.** Old:

```python
@router.get("/{id}")
def get_post(id: int, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    post = db.query(table).filter(table.id == id).first()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NO POST IS FOUND")
    return {"data": post}
```

- No ownership check at all: any logged-in user could read any post by id. The new `get_category` goes through `get_owned_category_or_404`, which puts `owner_id` in the query.
- No `response_model`, so nothing documents or filters the output. The new endpoint returns through `CategoryResponse`.
- A small Python point, said kindly: this function is also called `get_post`, the same name as the list endpoint above it. The second `def` replaces the name in the module, but both routes still work because each decorator registered its function at the moment it was defined. It is harmless, but confusing when you search for the function. The new file gives every endpoint a distinct name.

**Create.** Old:

```python
@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a new post",
             description="Insert a post into the database and return the created record", response_model=ResponsePost)
def create_post(post: CreatePost, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    print(current_user.password)
    new_post = table(**post.model_dump(), owner_id = current_user.id )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return {"message" : "Post Created Successfully", "data" : new_post}
```

- You already used `status_code=201`, `summary`, `response_model` and the `**model_dump()` + `owner_id` pattern. All of that is kept in `create_category`.
- `print(current_user.password)` wrote the user's password hash to the server console on every create. Even a hash should not be printed. The new code never logs or prints credentials.
- The old response wrapped the record in `{"message": ..., "data": ...}`. The new API returns the record itself: the 201 status already says "created", and clients do not have to unwrap `data` on every call.
- New: the uniqueness check (`ensure_category_name_is_unique`) before the insert. Posts had no such rule, categories do.

**Update.** Old:

```python
@router.put("/{id}",response_model=ResponsePost)
def update_post(id: int, updated_post: PostBase, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    get_post = db.query(table).filter(table.id==id)
    post = get_post.first()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail = "NO Found")
    if post.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED ,detail = {"message" : f"Post with ID : {id} Not Found"})
    get_post.update(updated_post.model_dump(), synchronize_session = False)
    db.commit()
    return {"message": "Post Updated successfully", "data": get_post.first()}
```

- **PUT with every field required** (`PostBase`: title, content, published). To change one word of the title the client had to resend everything. The new endpoint is **PATCH** with `CategoryUpdate` (all optional) and `exclude_unset=True`, so the client sends only what changes.
- **Two-step ownership check**: load by id, then `if post.owner_id != current_user.id`. It works, but it answers **401** for someone else's post and 404 for a missing one, so the two cases are distinguishable, and 401 is the wrong code anyway (401 means "not logged in"; the user *is* logged in). The new code puts `owner_id` in the query and answers 404 for both.
- The old code used a **bulk update** (`query.update(...)`) and then ran a second `SELECT` (`get_post.first()`) to return the row. The new code changes the loaded object with `setattr` and commits; SQLAlchemy writes only the changed columns.
- The old function reused the name `get_post` for a local variable; inside this function that hides the `get_post` endpoint. Harmless, but another reason the new file uses distinct names.

**Delete.** Old:

```python
@router.delete("/{id}")
def delete_post(id : int , db : Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    delete_post = db.query(table).filter(table.id == id).first()
    if delete_post == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND ,detail = {"message" : f"Post with ID : {id} Not Found"})
    if delete_post.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED ,detail = {"message" : f"Post with ID : {id} Not Found"})
    db.delete(delete_post)
    db.commit()
    return {"message":"Post Deleted Successfully", "status code": status.HTTP_204_NO_CONTENT}
```

- Same 404-versus-401 split as the update, with the same two problems (reveals existence, wrong code). New: one query, one 404.
- The body **said** `"status code": 204`, but there was no `status_code=` in the decorator, so the real HTTP status was 200, and a 204 is not allowed to have a body anyway. New: `status_code=204` in the decorator and an empty `Response(status_code=204)`.
- `delete_post == None` should be `delete_post is None` (it works, but `is` is the correct comparison with `None`, and linters flag `== None`).
- The old `delete_all` endpoint (`db.query(table).delete()`) deleted **every post of every user** with one request. It did use `Response(status_code=204)` correctly, which is the pattern the new delete keeps. The new project has no "delete everything" endpoint; it would be too dangerous to expose.

**Helpers.** The old file had none; every endpoint repeated its own lookup and ownership `if`. The new file's two helpers are the main structural change: the ownership rule and the uniqueness rule each exist in exactly one place.

### Key terms in this file

| Term                          | One-line meaning                                                                                      |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| helper function               | A plain function (no decorator) that endpoints call to share a rule.                                  |
| `db: Session`                 | Type hint on a helper; `Depends` only works on endpoint parameters, so helpers take `db` directly.    |
| ownership filter              | `Category.owner_id == current_user.id` inside the query, so other users' rows are never loaded.       |
| same 404 for others' data     | Foreign ids and missing ids both give 404, so nobody can learn which ids exist.                       |
| `func.lower(col)`             | The SQL function `lower(...)` applied to a column; makes a comparison case-insensitive.               |
| `select(Model.id)`            | Select one column only; `db.scalar` then returns that value or `None`.                                |
| `query = query.where(...)`    | `.where()` returns a new statement; assign it back or the condition is lost.                          |
| `int \| None = None`          | Optional parameter: an `int` or `None`, defaulting to `None`.                                         |
| f-string                      | `f"...{name}..."`: a string with variables filled in.                                                 |
| `""` path                     | Empty path on a prefixed router: the URL is the prefix itself, with no trailing slash.                |
| `{category_id}` path parameter| A placeholder in the path, passed to the parameter of the same name and converted to its type.        |
| `**model_dump()`              | Turn the schema into a dict and spread it as keyword arguments into the model constructor.            |
| `db.scalars(stmt)`            | Run the statement; iterate the first column of every row (a `ScalarResult`, consumable once).         |
| `list(...)`                   | Build a real Python list from the result.                                                             |
| PATCH vs PUT                  | PATCH changes some fields; PUT replaces the whole resource.                                           |
| `model_dump(exclude_unset=True)` | Only the fields the client actually sent; a sent `null` is kept, an unsent field is dropped.       |
| `model_fields_set`            | The set of field names that were present in the input; what `exclude_unset` looks at.                |
| `setattr(obj, name, value)`   | `obj.<name> = value` with the attribute name as a string; lets a loop apply a dict of changes.        |
| `db.dirty` / `db.deleted`     | Objects the session will UPDATE / DELETE at the next flush.                                           |
| `db.delete(obj)` + `commit()` | Mark for deletion, then run the `DELETE` and commit.                                                  |
| `ON DELETE SET NULL`          | Database rule: when a category row is deleted, expenses pointing at it get `category_id = NULL`.      |
| 204 No Content                | Success with an empty body; a route with 204 may not declare a response model.                        |
| `Response(status_code=204)`   | A raw empty response that FastAPI sends as-is.                                                        |
| `-> Response` annotation      | Tells FastAPI not to build a response model from the return type.                                     |

## Summary of this folder

The four router files in this document are the public face of the API; everything else in the project exists to serve them. `__init__.py` makes `app/routers` a package and lists what each file does. `health.py` is the odd one out: it needs no login and no session, it just asks the database engine "are you there?" and answers 200 or 503, with the real error in the log. `auth.py` is where a person enters: `register` validates the body with `UserCreate`, lowercases the email, checks for a duplicate (409), hashes the password, inserts the row, and catches the rare race through `IntegrityError` + `rollback`; `login` reads the OAuth2 form (email in `username`), gives one 401 for every kind of failure, and returns a `Token`. From then on every request carries that token, and the `CurrentUser` dependency from `app/core/dependencies.py` turns it back into a `User` object, which is all `users.py` needs to answer `GET /users/me`. `categories.py` shows the pattern that `expenses.py` repeats in doc 09: a `DatabaseSession` and a `CurrentUser` on every endpoint, `select(...)` statements that always include `owner_id == current_user.id`, `db.scalar` for one row and `db.scalars` for many, a helper that returns the owned row or a neutral 404, a helper that enforces the one business rule with a 409, `model_dump(exclude_unset=True)` plus a `setattr` loop for PATCH, and an explicit empty `Response(status_code=204)` for DELETE. The decorators carry the facts that `/docs` and clients rely on (`response_model`, `status_code`, `summary`, `tags`), and `app/main.py` mounts each `router` under `/api/v1` (except `/health`). Compared with your old `post.py`, the big shifts are: ownership inside the query instead of after it, one error code per situation chosen on purpose (401 not logged in, 404 not yours or not there, 409 clashes, 422 bad input), helpers instead of repeated `if`s, and responses that are the resource itself rather than a `{"message", "data"}` wrapper.
