# Deep request flow part 1: startup, /health, /auth, /users, /categories

## How to read this document

The other docs explain the code **file by file**. This one is different. It follows
**one HTTP request at a time**, from the moment it arrives at uvicorn until the
response bytes leave the server, and shows everything that happens in between:

- which Python function is chosen for the URL,
- which *dependencies* run before the function, in which exact order,
- which pydantic schema checks the input and what a bad input gets back,
- every line of the function body, with the **real SQL** that SQLAlchemy sends,
- how the return value becomes JSON,
- every error path, with the exact status code and `detail` text.

Nothing here is guessed. Every SQL statement, every JSON body and every order of
events was captured by actually running this project's code (FastAPI 0.141.1,
SQLAlchemy 2.0.54, pydantic 2.13.5, Starlette 1.7.0, uvicorn 0.53.0,
python-jose 3.5.0, pwdlib 0.3.1, Python 3.14). The SQL was captured on an
in-memory SQLite database using the same trick the tests use (swap `get_db`),
and then the same statements were compiled for the PostgreSQL driver so you can
see both spellings. The only differences between the two are cosmetic:

| Thing                | SQLite capture                 | PostgreSQL (what your real server receives)      |
| -------------------- | ------------------------------ | ------------------------------------------------ |
| parameter placeholder| `?`                            | `%(email)s` (a named placeholder)                |
| `RETURNING` columns  | `RETURNING id, created_at`     | `RETURNING users.id, users.created_at`           |
| `created_at` value   | `2026-10-06 11:58:39` (no zone)| `2026-10-06 11:58:39.412563+00:00` (with zone)   |

So when you see `WHERE users.email = ?` below, your PostgreSQL log will show
`WHERE users.email = 'asha@example.com'` (psycopg2 fills the value in before
sending). Same statement, same columns, same order.

**Example data used everywhere in this document.** One user, *Asha Verma*,
`asha@example.com`, password `correct-horse-battery`, who gets `id = 1`. A second
user *Ravi*, `ravi@example.com`, `id = 2`, appears only to prove that users cannot
touch each other's data. Asha's categories: *Food* (`id = 1`), *Rent* (`id = 2`),
*Travel* (`id = 3`).

Scope of this part: application startup, `GET /health`, `POST /api/v1/auth/register`,
`POST /api/v1/auth/login`, `GET /api/v1/users/me`, and the five `/api/v1/categories`
endpoints. The `get_date_range` dependency and `/expenses` and `/reports` are in
part 2 (`12-request-flow-expenses-reports.md`).

A few words you will meet again and again. Each is also explained the first time
it appears, but here they are in one place:

- **ASGI**: the agreement between a server (uvicorn) and a Python web app
  (FastAPI). The server calls `await app(scope, receive, send)` for every request.
  `scope` is a dict describing the request (method, path, headers), `receive` is
  how the app reads the body, `send` is how it sends the response.
- **Dependency**: a function FastAPI calls *for* you before your endpoint, to
  produce one of your endpoint's parameters (`Depends(...)`).
- **Session**: SQLAlchemy's "workspace" for one request: it holds a database
  connection, a transaction and the objects you loaded.
- **Transaction**: a group of SQL statements that either all become permanent
  (`COMMIT`) or are all thrown away (`ROLLBACK`).
- **Flush**: the moment SQLAlchemy sends the pending `INSERT` / `UPDATE` /
  `DELETE` statements to the database. `commit()` flushes first, then commits.
- **Identity map**: the session's dictionary `(class, primary key) -> object`.
  Loading the same row twice gives you the *same* Python object.
- **Expire**: after `commit()` the session marks every loaded attribute as "stale".
  The next time you read one, SQLAlchemy runs a `SELECT` to get fresh values.
- **JWT**: a signed text token in three parts (`header.payload.signature`). The
  **claims** are the keys inside the payload (`sub`, `exp`).
- **422**: the HTTP status FastAPI uses when input does not match a schema.

---

# Startup flow

Before the first request can be answered, three things happen in this order:
Python imports `app/main.py` (and everything it imports), uvicorn runs the
**lifespan** startup code, and uvicorn starts listening on the port.

## Step 1: `uvicorn app.main:app` imports the code

`uvicorn app.main:app` means: *import the module `app.main` and use the variable
named `app` inside it as the ASGI application*. Importing `app/main.py` runs the
file top to bottom, and every `import` line pulls in another file, which also
runs top to bottom. This is the real order (follow the imports in `app/main.py`):

```
app/main.py
  -> app/core/config.py        settings = Settings()  (reads env vars + .env)
  -> app/database/session.py   engine = create_engine(...)  (NO connection yet)
                               SessionLocal = sessionmaker(...)
  -> app/routers/auth.py
       -> app/core/dependencies.py   oauth2_scheme = OAuth2PasswordBearer(...)
            -> app/core/security.py  password_hasher = PasswordHash.recommended()
            -> app/models/user.py    class User(Base)  (table registered in Base.metadata)
       -> app/models/user.py, app/schemas/auth.py, app/schemas/user.py
  -> app/routers/categories.py, expenses.py, health.py, reports.py, users.py
       (each one creates its own `router = APIRouter(...)`)
```

### Block 1: the settings object is created at import time

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    ...
    SECRET_KEY: str  # required: no default
    ...

settings = Settings()
```

- `class Settings(BaseSettings)`: a class that inherits from pydantic-settings'
  `BaseSettings`. A `BaseSettings` is a pydantic model whose values come from
  **environment variables** instead of from a JSON body.
- `model_config`: a special class attribute that pydantic looks for. It is the
  model's *configuration* (how the model should behave). In pydantic v1 you wrote
  `class Config:` inside the class (your old `config.py` did exactly that).
  In pydantic v2 the same thing is written as `model_config = ...`.
- `SettingsConfigDict(...)`: a function that builds that configuration dictionary
  with the right keys. It is just a typed dict; `SettingsConfigDict(env_file=".env")`
  is the same as `{"env_file": ".env"}` but your editor can check the key names.
- `env_file=".env"`: also read a file named `.env` (in the folder you start uvicorn
  from). **Real environment variables win over the file.** That is why the tests
  can set `DATABASE_URL` in `os.environ` and never touch your real database.
- `env_file_encoding="utf-8"`: how to read that file's bytes as text.
- `extra="ignore"`: if `.env` contains a key that is not a field of `Settings`
  (say `PGADMIN_PASSWORD=...`), ignore it instead of raising an error.
- `SECRET_KEY: str` with **no `= default`**: a required field. If neither the
  environment nor `.env` has it, `Settings()` raises and the import fails. This
  is the real error text (captured):

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
SECRET_KEY
  Field required [type=missing, input_value={}, input_type=dict]
```

  uvicorn then prints the traceback and stops. The app never starts. That is on
  purpose: a JWT signed with an empty or default secret would be worthless.
- `DATABASE_URL: str | None = None`: `str | None` is Python's way to write "a
  string, or `None`". `|` means "or" in a type hint. Default `None` means "not
  set". `settings.database_url` (the property below) uses it when present.
- `settings = Settings()`: the one shared object. Every other file does
  `from app.core.config import settings` and gets this same object. The
  environment is read **once**, here, at import time.

```python
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DATABASE_USERNAME,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOSTNAME,
            port=self.DATABASE_PORT,
            database=self.DATABASE_NAME,
        ).render_as_string(hide_password=False)
```

- `@property`: a decorator that turns a method into something you read like an
  attribute. You write `settings.database_url` (no parentheses) and Python
  calls the function for you. It exists so that a *computed* value looks like a
  plain field.
- `URL.create(...)`: SQLAlchemy's safe URL builder. With the defaults and
  password `p@ss:w/rd` it produces
  `postgresql+psycopg2://postgres:p%40ss%3Aw%2Frd@localhost:5432/expense_tracker`
  (captured). The `@`, `:` and `/` in the password are escaped as `%40`, `%3A`,
  `%2F`. Your old code built the URL with an f-string, which breaks on such
  passwords.
- `.replace("postgres://", "postgresql://", 1)`: hosting providers sometimes give
  the old `postgres://` scheme; SQLAlchemy 2 refuses it. The `1` means "replace
  only the first occurrence".

### Block 2: the engine and the session factory

```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
```

- `create_engine(...)`: builds the **engine**: the object that owns a **pool** of
  database connections. Important: **this opens no connection**. SQLAlchemy only
  connects the first time someone asks for a connection. So importing the app
  never touches PostgreSQL; the lifespan step does that.
- `pool_pre_ping=True`: before handing out a connection that sat in the pool,
  SQLAlchemy sends a tiny test query (`SELECT 1`). If the connection is dead
  (PostgreSQL restarted), it silently opens a new one. Without this, a database
  restart shows up as random `server closed the connection unexpectedly` errors.
- `sessionmaker(...)`: a *factory*. `SessionLocal()` (called with parentheses)
  creates a new `Session`. `bind=engine` says which engine the sessions use.
- `autocommit=False`: you must call `db.commit()` yourself (the normal way).
- `autoflush=False`: SQLAlchemy does not send pending `INSERT`s automatically
  before every query; it sends them at `commit()` (or when you call `flush()`).
  Captured fact: a new session is created with `expire_on_commit=True`,
  `autoflush=False`, and is *not* in a transaction until the first query.

### Block 3: the OAuth2 scheme object and the type aliases

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```

- `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")`: an object that, when
  used as a dependency, reads the `Authorization` header and returns the token
  text. `tokenUrl` is only used by the Swagger page (`/docs`) so its "Authorize"
  button knows where to send the login form.
- `Annotated[Session, Depends(get_db)]`: `Annotated` comes from the `typing`
  module. It lets you attach extra information to a type. The first item is the
  real type (`Session`), everything after it is "metadata" for tools. FastAPI
  reads that metadata and sees `Depends(get_db)`. So writing
  `db: DatabaseSession` in an endpoint is exactly the same as your old
  `db: Session = Depends(get_db)`, just reusable and without repeating it.
- `CurrentUser`: same idea for `get_current_user`.
- `@dataclass class DateRange` and `get_date_range` also live in this file. A
  `dataclass` is a class where Python writes `__init__` for you from the listed
  fields. They are only used by `/expenses` and `/reports`, so they are explained
  in part 2.

### Block 4: the FastAPI app, CORS and the router table

```python
app = FastAPI(title=..., version=..., description=..., lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_allowed_origins_list, ...)
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(categories.router, prefix=settings.API_V1_PREFIX)
app.include_router(expenses.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
```

A **middleware** is a layer that wraps the whole app: every request goes *in*
through each layer and every response comes *out* through them in reverse.
Captured from the running app, this is the exact stack (outermost first):

```
starlette.middleware.errors.ServerErrorMiddleware      -> turns any crash into "500 Internal Server Error"
starlette.middleware.cors.CORSMiddleware               -> adds CORS headers for browser frontends
starlette.middleware.exceptions.ExceptionMiddleware    -> turns HTTPException / validation errors into JSON
fastapi.middleware.asyncexitstack.AsyncExitStackMiddleware -> cleanup helper for uploaded files
fastapi.routing.APIRouter                              -> picks the route
```

`CORSMiddleware` does nothing for requests that have no `Origin` header (curl,
Postman, the tests): it just passes them through. Only browsers send `Origin`.

The final URL of every endpoint is **include prefix + router prefix + decorator
path**. `include_router(prefix="/api/v1")` + `APIRouter(prefix="/auth")` +
`@router.post("/register")` = `/api/v1/auth/register`. This is the complete route
table of the app, in registration order, captured from the app object:

```
GET    /health                              -> app.routers.health.health_check
POST   /api/v1/auth/register                -> app.routers.auth.register_user       (201, UserResponse)
POST   /api/v1/auth/login                   -> app.routers.auth.login               (200, Token)
GET    /api/v1/users/me                     -> app.routers.users.get_my_profile     (200, UserResponse)
POST   /api/v1/categories                   -> app.routers.categories.create_category (201, CategoryResponse)
GET    /api/v1/categories                   -> app.routers.categories.list_categories (200, list[CategoryResponse])
GET    /api/v1/categories/{category_id}     -> app.routers.categories.get_category   (200, CategoryResponse)
PATCH  /api/v1/categories/{category_id}     -> app.routers.categories.update_category (200, CategoryResponse)
DELETE /api/v1/categories/{category_id}     -> app.routers.categories.delete_category (204, no body)
POST   /api/v1/expenses ...                 (part 2)
GET    /api/v1/reports/... ...              (part 2)
```

Plus the four routes FastAPI adds itself: `/openapi.json`, `/docs`,
`/docs/oauth2-redirect`, `/redoc`.

Order matters: when a request comes in, the router tries routes **top to bottom**
and takes the first one whose path *and* method match. If a path matches but the
method does not (say `PUT /api/v1/categories/1`), the answer is
`405 {"detail":"Method Not Allowed"}`. If nothing matches, `404 {"detail":"Not Found"}`.
And because `redirect_slashes` is on by default, `POST /api/v1/categories/`
(trailing slash) gets a `307` redirect to `/api/v1/categories` (captured).

## Step 2: uvicorn runs the lifespan startup

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    check_database_connection()
    logger.info("Database connection established")
    yield
    # Code after `yield` runs once at shutdown.
```

- `async def`: an *asynchronous* function (a coroutine). FastAPI and uvicorn are
  built on `asyncio`, so this hook must be `async`.
- `yield`: a function with `yield` in it is a **generator**: it runs up to the
  `yield`, pauses, and continues after it later. Everything *before* `yield` is
  the startup code; everything *after* is the shutdown code.
- `@asynccontextmanager`: turns that generator into a **context manager**, the
  thing you use with `async with`. A context manager is anything with an "enter"
  part and an "exit" part. FastAPI does the equivalent of
  `async with lifespan(app): serve requests`, so "enter" = the code before
  `yield` (runs once at startup) and "exit" = the code after `yield` (runs once
  when uvicorn shuts down).

The ASGI protocol has a special pseudo-request for this. uvicorn sends
`{"type": "lifespan.startup"}` to the app. Starlette's router receives it, enters
our context manager, and our code runs:

```python
def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
```

- `with engine.connect() as connection:`: `with` is the *synchronous* context
  manager syntax. "Enter" = take a connection from the pool (the pool is empty, so
  **this is the first real TCP connection to PostgreSQL** in the whole process);
  "exit" = return it to the pool, even if an exception happened inside.
- `text("SELECT 1")`: wraps a raw SQL string so SQLAlchemy can execute it.
- `connection.execute(...)`: sends the SQL. The result (`1`) is ignored; the point
  is that no exception was raised.

Real SQL sent: `SELECT 1`.

Two outcomes:

| Outcome              | What you see                                                                 |
| -------------------- | ---------------------------------------------------------------------------- |
| PostgreSQL answers   | log line `... \| INFO \| app.main \| Database connection established`, then uvicorn logs `Application startup complete.` and starts accepting requests. The connection stays in the pool and is reused by the first request. |
| PostgreSQL is down   | `engine.connect()` raises `sqlalchemy.exc.OperationalError` (wrapping psycopg2's `connection refused`). Starlette sends `lifespan.startup.failed` to uvicorn, which logs the traceback and `Application startup failed. Exiting.` The process stops. No port is opened. |

Compared with your old project: same idea (`connect_database()` in lifespan),
but `print("Database Connecting Successfully")` became a proper `logger.info`.

## Startup sequence diagram

```
 shell                 uvicorn                  Python import            Starlette/FastAPI        SQLAlchemy          PostgreSQL
  |  uvicorn app.main:app |                          |                          |                     |                   |
  |---------------------->|  import app.main         |                          |                     |                   |
  |                       |------------------------->| Settings()  reads env/.env                      |                   |
  |                       |                          | create_engine()  (no connection)                |                   |
  |                       |                          | APIRouter objects, FastAPI(app), include_router |                   |
  |                       |<-------------------------|  `app` object ready      |                     |                   |
  |                       |  lifespan.startup -------------------------------->|                     |                   |
  |                       |                          |                          | lifespan(): check_database_connection() |
  |                       |                          |                          |-------------------->| engine.connect()  |
  |                       |                          |                          |                     |------------------>| TCP connect + auth
  |                       |                          |                          |                     | SELECT 1 -------->|
  |                       |                          |                          |                     |<------- 1 --------|
  |                       |                          |                          |<--- ok, logger.info |                   |
  |                       |<------- lifespan.startup.complete -----------------|                     |                   |
  |                       |  "Application startup complete." / listening on :8000                     |                   |
```

---

# Endpoint: GET /health

## 1. The request

```
GET /health HTTP/1.1
Host: 127.0.0.1:8000
```

No headers needed, no body, no token. Uptime monitors call this every minute.

## 2. Routing

uvicorn reads the raw bytes with its HTTP parser (`h11`), builds the ASGI `scope`
(`{"type": "http", "method": "GET", "path": "/health", "headers": [...], ...}`)
and calls `await app(scope, receive, send)`. The request passes through the
middleware stack (nothing to do: no crash yet, no `Origin` header, no exception)
and reaches the `APIRouter`. It walks the route table from the top. The first
entry, `GET /health`, matches path and method. `health.router` was included
**without** a prefix, so the final path is `"" + "" + "/health"`.

Chosen function: `app/routers/health.py` -> `health_check`.

## 3. Dependencies run first

None. The function has no parameters. The dependency step is skipped entirely.

## 4. Validation

Nothing to validate: no body, no path or query parameters.

## 5. Inside the function, line by line

```python
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

- `def health_check()` (not `async def`): FastAPI runs plain `def` endpoints in a
  **worker thread** so that a slow database call does not freeze the server for
  other requests. All endpoints in this project are plain `def`, so this is true
  for every section below.
- `-> dict[str, str]`: the return annotation. Because the decorator gives no
  `response_model`, FastAPI uses this annotation as the response model: "a dict
  whose keys and values are strings".
- `check_database_connection()`: the same function as at startup. It borrows a
  pooled connection (pre-ping first, because `pool_pre_ping=True`), runs
  `SELECT 1`, and returns the connection.

Real SQL sent to the database: `SELECT 1`.

- `except Exception:`: any error at all (connection refused, timeout, wrong
  password after a config change...) is caught here.
- `logger.exception(...)`: logs the message **plus the full traceback**. Use this
  (not `logger.error`) inside an `except` block.
- `raise HTTPException(status_code=503, detail=...)`: `503 Service Unavailable` is
  the standard code for "I am up but something I depend on is not". Load balancers
  treat it as "take this instance out of rotation".

## 6. The response

Success: the dict is validated against `dict[str, str]` and dumped to JSON.

```
HTTP/1.1 200 OK
content-type: application/json
content-length: 38

{"status":"ok","database":"connected"}
```

(captured). There is no session here, so there is nothing to close; the
connection went back to the pool inside the `with` block.

| Situation                       | Status | `detail`                   | Raised where                              |
| ------------------------------- | ------ | -------------------------- | ----------------------------------------- |
| database reachable              | 200    | (body above)               | -                                         |
| database down / unreachable     | 503    | `"Database is unavailable"`| `health.py`, the `raise HTTPException`    |

How the `HTTPException` becomes JSON: it travels up to Starlette's
`ExceptionMiddleware`, which calls FastAPI's `http_exception_handler`. That
handler returns `JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
headers=exc.headers)`. This is the same path for **every** `HTTPException` in
this document, so it is not repeated below.

## 7. Sequence diagram

```
 Client          uvicorn           Router            health_check()        SQLAlchemy             PostgreSQL
   | GET /health   |                 |                     |                    |                      |
   |-------------->| scope,receive,send                    |                    |                      |
   |               |---------------->| match GET /health   |                    |                      |
   |               |                 |-------------------->| (worker thread)    |                      |
   |               |                 |                     | check_database_connection()               |
   |               |                 |                     |------------------->| engine.connect()     |
   |               |                 |                     |                    | (pre-ping, SELECT 1) |
   |               |                 |                     |                    |--- SELECT 1 -------->|
   |               |                 |                     |                    |<------ 1 ------------|
   |               |                 |                     |<-- ok --------------|                      |
   |               |                 |<-- {"status":"ok",...}                   |                      |
   |               |<-- 200 JSON ----|                     |                    |                      |
   |<--------------|                 |                     |                    |                      |
```

---

# Endpoint: POST /api/v1/auth/register

## 1. The request

```
POST /api/v1/auth/register HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
Content-Length: 85

{"email": "Asha@Example.com", "full_name": "  Asha Verma ", "password": "correct-horse-battery"}
```

Note the messy input on purpose: capital letters in the email and spaces around
the name. You will see exactly where each one gets cleaned.

## 2. Routing

uvicorn builds the scope (`method = "POST"`, `path = "/api/v1/auth/register"`)
and calls the app. Middlewares pass it through. The router tries the routes in
order: `/health` (no), `/openapi.json` and friends (no), then
`POST /api/v1/auth/register`: match. That path was built from
`include_router(auth.router, prefix="/api/v1")` + `APIRouter(prefix="/auth")` +
`@router.post("/register")`.

Chosen function: `app/routers/auth.py` -> `register_user(user_in: UserCreate, db: DatabaseSession)`.

## 3. Dependencies run first

Before dependencies, FastAPI's request handler **reads the body**. It looks at the
`Content-Type` header: `application/json`, so it parses the bytes as JSON into a
Python dict. If the JSON is broken (`{"email": "b@example.com",` with no closing
brace), it stops right here with a 422 and nothing else runs (captured):

```json
{"detail":[{"type":"json_invalid","loc":["body",26],"msg":"JSON decode error","input":{},"ctx":{"error":"Expecting property name enclosed in double quotes"}}]}
```

(`26` is the character position where the parser gave up.)

Then FastAPI walks the function's parameters **in the order they are written**
and builds a tree of dependencies (captured from the app):

```
register_user
  body_params: user_in            (validated AFTER the dependencies)
  dependencies:
    - db  -> get_db               (use_cache=True)
```

So exactly one dependency runs:

**`get_db`** (`app/database/session.py`):

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- `Generator[Session, None, None]`: the return type of a generator that yields
  `Session` objects (the two `None`s are "what you can send in" and "what it
  returns at the end": nothing).
- `db = SessionLocal()`: a new `Session`. Still **no connection** and **no
  transaction**: those start at the first query.
- `yield db`: hands the session to FastAPI, which stores it to pass as the `db`
  argument, and the generator **pauses here**.
- `finally: db.close()`: runs when FastAPI resumes the generator at the end of the
  request, whatever happened (success, `HTTPException`, crash).

Reads from the request: nothing. Returns: a `Session`. Cannot raise an HTTP error.

Captured fact about **when** that `finally` runs: FastAPI sends the response
*first* and only then resumes the generator. The real order observed with a raw
ASGI call was `http.response.start` -> `http.response.body` -> `db.close()`.
So the client already has the answer when the session is closed.

Captured fact about *invalid input*: `get_db` runs **even when the body is bad**.
With `{"email": "bad", ...}` the log showed `session opened` -> `db.close()`,
and the 422 was produced in between. The dependency step always comes before
body validation; the session is simply opened and closed without being used.

## 4. Validation

After the dependencies, FastAPI validates the body with `UserCreate`:

```python
FullName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]

class UserCreate(BaseModel):
    email: EmailStr
    full_name: FullName
    password: str = Field(min_length=8, max_length=128)
```

- `EmailStr`: a string that must look like an email. It uses the
  `email-validator` library, which also **normalises** the address: the domain
  part is lower-cased. Captured: `"Asha@Example.com"` becomes
  `"Asha@example.com"` (the part before `@` is left alone; the code lower-cases
  it in the next step). A trailing space is removed too.
- `FullName`: again `Annotated`: the real type is `str`, and the metadata is a
  `StringConstraints` object. `strip_whitespace=True` removes spaces at both ends
  **before** checking the length, so `"   "` becomes `""` and fails
  `min_length=1`. Captured: `"  Asha Verma "` becomes `"Asha Verma"`.
- `password: str = Field(min_length=8, max_length=128)`: `Field(...)` is how you
  add constraints to a plain field. At least 8 characters, at most 128.

Every error is collected and sent together. Real 422 for the body
`{"email": "not-an-email", "full_name": "   ", "password": "short"}` (captured):

```json
{
  "detail": [
    {"type":"value_error","loc":["body","email"],"msg":"value is not a valid email address: An email address must have an @-sign.","input":"not-an-email","ctx":{"reason":"An email address must have an @-sign."}},
    {"type":"string_too_short","loc":["body","full_name"],"msg":"String should have at least 1 character","input":"   ","ctx":{"min_length":1}},
    {"type":"string_too_short","loc":["body","password"],"msg":"String should have at least 8 characters","input":"short","ctx":{"min_length":8}}
  ]
}
```

A missing field (captured, no `full_name`):

```json
{"detail":[{"type":"missing","loc":["body","full_name"],"msg":"Field required","input":{"email":"b@example.com","password":"correct-horse-battery"}}]}
```

No body at all: `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}`.

`loc` always tells you *where*: `["body", "email"]` means "in the JSON body, key
`email`". These 422s are produced by FastAPI's
`request_validation_exception_handler`; the function never runs.

## 5. Inside the function, line by line

```python
def register_user(user_in: UserCreate, db: DatabaseSession) -> User:
    email_already_registered = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="An account with this email already exists",
    )
```

- `user_in` is now a `UserCreate` object:
  `email='Asha@example.com' full_name='Asha Verma' password='correct-horse-battery'`.
- `db` is the session from `get_db`.
- `email_already_registered = HTTPException(...)`: creating an exception object
  does **not** raise it. It is built once because it is needed in two places.
  `409 Conflict` means "the request is fine but it clashes with existing data".

```python
    email = user_in.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise email_already_registered
```

- `.lower()`: `"Asha@example.com"` -> `"asha@example.com"`. The table stores
  lower-case emails so that `A@x.com` and `a@x.com` are one account.
- `select(User)`: builds a SELECT statement object for all columns of the `users`
  table. `select` is SQLAlchemy 2.0's replacement for your old `db.query(User)`.
  Nothing is sent yet; it is just a description of a query.
- `.where(User.email == email)`: `User.email` is not a string here, it is a
  *column object*; `==` on it builds a SQL comparison, not a Python boolean.
- `db.scalar(stmt)`: executes the statement and returns **the first column of the
  first row**, or `None` if there is no row. With `select(User)` that "first
  column" is the whole `User` object. It replaces `db.query(User).filter(...).first()`.

This is the first query of the request, so right now the session checks a
connection out of the pool and begins a transaction. Real SQL (captured):

```sql
SELECT users.id, users.email, users.full_name, users.hashed_password, users.is_active, users.created_at
FROM users
WHERE users.email = ?            -- ('asha@example.com',)
```

PostgreSQL spelling: `WHERE users.email = %(email_1)s`. Result: no row, so
`db.scalar` returns `None`, the `if` is false, and we continue. (On a second
registration with the same email the row is found, `raise email_already_registered`
fires, and the response is `409 {"detail":"An account with this email already exists"}`;
captured with `"asha@example.com"` after `"Asha@Example.com"` was registered.)

```python
    user = User(
        email=email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )
```

- `User(...)`: a new ORM object. SQLAlchemy's `Base` gives every model a
  keyword-argument constructor. The object is **transient**: Python knows it,
  the session does not, the database does not.
- `hash_password(...)` (`app/core/security.py`): `password_hasher.hash(plain)`
  with Argon2id. The result (captured) looks like
  `$argon2id$v=19$m=65536,t=3,p=4$7UJ2gz6hvI1tEsBKUt0c1Q$TZ8PFX3mb+ZuCxmQqF/DKa2QqSKVUF8+MUzZPVHG8G0`,
  97 characters: algorithm, version, memory/time/parallelism settings, a random
  **salt**, and the hash. Because the salt is random, hashing the same password
  twice gives two different strings (verified). The plain password is never stored.
- `is_active` is not passed: the column has `default=True` (a Python-side
  default), so SQLAlchemy fills it in at insert time. `created_at` is not passed
  either: that one is a `server_default=func.now()`, so the **database** fills it.

```python
    db.add(user)
```

- `db.add(user)`: the object becomes **pending** in the session. Still no SQL.
  SQLAlchemy remembers "there is an INSERT to do".

```python
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise email_already_registered
```

- `db.commit()` does two things. First a **flush**: every pending change is
  turned into SQL and sent. Then `COMMIT` is sent, which makes it permanent.
  Real SQL from the flush (captured on SQLite):

```sql
INSERT INTO users (email, full_name, hashed_password, is_active) VALUES (?, ?, ?, ?) RETURNING id, created_at
-- ('asha@example.com', 'Asha Verma', '$argon2id$v=19$m=65536,t=3,p=4$...', 1)
```

  Same statement compiled for PostgreSQL:

```sql
INSERT INTO users (email, full_name, hashed_password, is_active)
VALUES (%(email)s, %(full_name)s, %(hashed_password)s, %(is_active)s)
RETURNING users.id, users.created_at
```

  Read the column list carefully: `id` and `created_at` are **not in it**.
  `id` is `SERIAL` (PostgreSQL generates it) and `created_at` has
  `DEFAULT now()`. `RETURNING users.id, users.created_at` asks PostgreSQL to send
  those two generated values straight back, so SQLAlchemy can put `user.id = 1`
  and `user.created_at = <timestamp>` on the object without another round trip.
  Then `COMMIT` is sent. After the commit, SQLAlchemy **expires** every attribute
  of `user` (`expire_on_commit=True`). Verified: right after `commit()`,
  `user.__dict__` holds no column values at all.
- `except IntegrityError:`: the database refused the INSERT because of a
  constraint. Here the only one that can fire is the unique index on email, named
  `ix_users_email` by the naming convention in `app/database/base.py`
  (`"ix": "ix_%(column_0_label)s"` -> `ix_users_email`; the PostgreSQL DDL is
  `CREATE UNIQUE INDEX ix_users_email ON users (email)`). When can it fire if we
  just checked with a SELECT? When two requests with the same email arrive at the
  same moment: both SELECTs see "no row", both try to INSERT, the second one gets
  PostgreSQL's `duplicate key value violates unique constraint "ix_users_email"`,
  which SQLAlchemy raises as `sqlalchemy.exc.IntegrityError` (verified on SQLite
  with `UNIQUE constraint failed: users.email`).
- `db.rollback()`: after a failed flush the transaction is broken and must be
  rolled back before the session can be used again (verified: `in_transaction()`
  is `False` afterwards). Then the same 409 is raised as before. From the client's
  point of view the two cases are identical.

```python
    db.refresh(user)
    return user
```

- `db.refresh(user)`: runs a SELECT by primary key and reloads every attribute.
  Real SQL (captured):

```sql
SELECT users.id, users.email, users.full_name, users.hashed_password, users.is_active, users.created_at
FROM users
WHERE users.id = ?               -- (1,)
```

  Why is it needed if `RETURNING` already gave `id` and `created_at`? Because
  the commit expired everything. Without `refresh`, the first attribute read
  during JSON serialisation would trigger the very same SELECT lazily (verified:
  touching `user.email` after a commit emits one SELECT that loads all columns).
  `refresh` just makes that load explicit and at a predictable place. Note that
  this SELECT opens a **new** transaction (the previous one ended at `COMMIT`);
  it is rolled back harmlessly by `db.close()` later.
- `return user`: the ORM object goes back to FastAPI.

Compared with your old `post_user`: identical shape (`add`, `commit`, `refresh`,
return), plus the email lower-casing, the duplicate check, and the `IntegrityError`
safety net.

## 6. The response

The decorator says `response_model=UserResponse, status_code=201`:

```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime
```

- `model_config = ConfigDict(from_attributes=True)`: the same `model_config`
  idea as in `Settings`, but with pydantic's `ConfigDict`. `from_attributes=True`
  means "you may build this model from an object by reading its attributes
  (`obj.id`, `obj.email`...) instead of from a dict". This is what lets FastAPI
  turn a SQLAlchemy `User` into JSON. (pydantic v1 called it `orm_mode`.)
- No `hashed_password` field: fields that are not listed are simply not read, so
  the hash never leaks. `is_active` is left out too.

FastAPI calls `TypeAdapter(UserResponse).validate_python(user, from_attributes=True)`
(this is the real call inside `fastapi/_compat/v2.py`), then dumps it to JSON.
Captured response:

```
HTTP/1.1 201 Created
content-type: application/json

{"id":1,"email":"asha@example.com","full_name":"Asha Verma","created_at":"2026-10-06T11:58:39"}
```

On PostgreSQL `created_at` is `TIMESTAMP WITH TIME ZONE`, so the value carries
an offset and microseconds, and pydantic writes it in ISO format:
`"2026-10-06T11:58:39.412563Z"` when the server's time zone is UTC, or
`"2026-10-06T17:28:39.412563+05:30"` when it is `Asia/Kolkata` (both formats
verified with pydantic; the digits depend on your server).

After the bytes are sent, FastAPI resumes `get_db`, and `db.close()` runs: it
rolls back the small transaction opened by `refresh`, returns the connection to
the pool, and detaches the `user` object (it is still a normal Python object, but
it no longer belongs to any session).

| Situation                                   | Status | `detail`                                                | Raised where                                     |
| ------------------------------------------- | ------ | ------------------------------------------------------- | ------------------------------------------------ |
| valid, new email                            | 201    | (body above)                                            | -                                                |
| broken JSON                                 | 422    | `[{"type":"json_invalid", ...}]`                        | FastAPI request handler, before any dependency   |
| bad email / short password / blank name     | 422    | list of errors, one per field                           | pydantic via FastAPI, after `get_db` ran         |
| email already exists                        | 409    | `"An account with this email already exists"`           | `auth.py`, `raise` after `db.scalar(...)`        |
| two identical registrations at the same time| 409    | same text                                               | `auth.py`, the `except IntegrityError` block     |
| database down during the request            | 500    | plain text `Internal Server Error` (not JSON)           | `ServerErrorMiddleware`; traceback in the log    |

## 7. Sequence diagram

```
 Client        uvicorn        Router/handler         get_db        register_user()      SQLAlchemy Session          PostgreSQL
   | POST ... JSON |               |                    |                 |                      |                        |
   |-------------->|-------------->| read+parse JSON    |                 |                      |                        |
   |               |               |------------------->| SessionLocal()  |                      |                        |
   |               |               |<--- yield db ------|                 |                      |                        |
   |               |               | validate UserCreate (422 if bad)     |                      |                        |
   |               |               |------------------------------------->| (worker thread)      |                        |
   |               |               |                    |                 | db.scalar(select...) |                        |
   |               |               |                    |                 |--------------------->| checkout conn, BEGIN   |
   |               |               |                    |                 |                      |--- SELECT ... email -->|
   |               |               |                    |                 |<------ None ---------|<------ 0 rows ---------|
   |               |               |                    |                 | hash_password()      |                        |
   |               |               |                    |                 | db.add(user)         |                        |
   |               |               |                    |                 | db.commit()  ------->| flush: INSERT ... RETURNING -->|
   |               |               |                    |                 |                      |<---- id=1, created_at -|
   |               |               |                    |                 |                      |--- COMMIT ------------>|
   |               |               |                    |                 |                      | expire all attributes  |
   |               |               |                    |                 | db.refresh(user) --->|--- SELECT ... id=1 --->|
   |               |               |                    |                 |<---------------------|<------ 1 row ----------|
   |               |               |<-- return user ----------------------|                      |                        |
   |               |               | UserResponse.validate (from_attributes) -> JSON             |                        |
   |               |<-- 201 JSON --|                    |                 |                      |                        |
   |<--------------|               |                    |                 |                      |                        |
   |               |               |--- resume get_db ->| db.close()  ---------------------------> ROLLBACK, conn to pool |
```

---

<!-- CONTINUE -->
