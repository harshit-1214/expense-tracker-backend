# Deep request flow part 2: /expenses and /reports

## How to read this document

Documents 06 to 09 explain the files. This document explains the **journey of one request**. For each of the eight endpoints under `/api/v1/expenses` and `/api/v1/reports` you will follow a real HTTP request from the moment it reaches uvicorn to the moment the JSON leaves, including:

1. the exact request (method, path, headers, body),
2. how FastAPI picks the Python function,
3. the exact order in which the dependencies run and what each one can raise,
4. the pydantic validation and what a `422` looks like,
5. the function body line by line, with the **real SQL** that SQLAlchemy sends and what the session does in between,
6. the response, the status code, what happens to the database session afterwards, and every error path,
7. a sequence diagram of the whole thing.

Nothing here is from memory. I ran the real project code (FastAPI 0.141.1, Starlette 1.7.0, pydantic 2.13.5, SQLAlchemy 2.0.54) against an in-memory SQLite database the same way `tests/conftest.py` does, recorded every SQL statement and every response, and compiled every statement a second time for the PostgreSQL driver (`psycopg2`) so that you see what production sends. Where SQLite and PostgreSQL differ, I say so. Where I checked something in the library source, I say "I checked this in ...".

**Conventions used below**

- SQL is shown as PostgreSQL receives it from psycopg2. A piece like `%(owner_id_1)s` is a **placeholder**. The real value travels separately (I show it as "params"). This is how SQLAlchemy avoids SQL injection: the user's text is never pasted into the SQL string.
- Our example user is **Asha** (`users.id = 1`). Her categories are **Food** (`id 1`) and **Transport** (`id 2`). A second user (`users.id = 2`) owns category 3 ("Secret") and expense 6. He exists so you can see the ownership filter at work.
- Asha's token (created by `POST /api/v1/auth/login`) is written as `eyJhbGciOi...vqfCw` to save space. Its real content is shown in Block 6.
- `created_at` / `updated_at`: PostgreSQL returns these with microseconds and a time zone, for example `"2026-10-06T12:02:13.481729Z"` when the server time zone is UTC (pydantic writes UTC as `Z`) or `"2026-10-06T17:32:13.481729+05:30"` when the server is set to India time. My SQLite capture printed `"2026-10-06T12:02:13"` (no fraction, no zone) because SQLite's `CURRENT_TIMESTAMP` has neither. In the JSON examples I write the PostgreSQL form.
- "Line N" always means the line number in the source file named just before it.

Startup (how `settings`, `engine`, `SessionLocal` and the routers come to exist) is **not** repeated here. It is in document 11. This document starts at the moment the server is already running and a request arrives.

## Before the first request: the route table

When `app/main.py` ran `app.include_router(expenses.router, prefix=settings.API_V1_PREFIX)` and the same for `reports.router`, FastAPI built this table. I printed it from the running app:

| Method | Full path | Python function | `response_model` | Success status |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/expenses` | `app/routers/expenses.py` → `create_expense` | `ExpenseResponse` | 201 |
| GET | `/api/v1/expenses` | `app/routers/expenses.py` → `list_expenses` | `ExpenseListResponse` | 200 |
| GET | `/api/v1/expenses/{expense_id}` | `app/routers/expenses.py` → `get_expense` | `ExpenseResponse` | 200 |
| PATCH | `/api/v1/expenses/{expense_id}` | `app/routers/expenses.py` → `update_expense` | `ExpenseResponse` | 200 |
| DELETE | `/api/v1/expenses/{expense_id}` | `app/routers/expenses.py` → `delete_expense` | none | 204 |
| GET | `/api/v1/reports/summary` | `app/routers/reports.py` → `get_expense_summary` | `ExpenseSummary` | 200 |
| GET | `/api/v1/reports/by-category` | `app/routers/reports.py` → `get_spending_by_category` | `list[CategoryTotal]` | 200 |
| GET | `/api/v1/reports/monthly` | `app/routers/reports.py` → `get_monthly_spending` | `list[MonthlyTotal]` | 200 |

**How each full path was built.** Three pieces are glued together, in two steps.

1. At import time, when Python reaches `@router.post("")` in `app/routers/expenses.py`, FastAPI's `APIRouter.add_api_route` stores the path as `self.prefix + path`, that is `"/expenses" + ""` = `"/expenses"`. I checked this in `fastapi/routing.py` (the line `self.prefix + path`). For `@router.get("/{expense_id}")` it stores `"/expenses/{expense_id}"`. For `@router.get("/summary")` in `reports.py` it stores `"/reports/summary"`.
2. When `main.py` calls `app.include_router(expenses.router, prefix="/api/v1")`, FastAPI keeps the router and the prefix together (an object called `_IncludedRouter` in this FastAPI version). When a request is matched, the effective path is `prefix + route.path` (the method `path_for` in `fastapi/routing.py` returns exactly `self.prefix + route.path`), so `"/api/v1" + "/expenses"` = `"/api/v1/expenses"`.

Each path is also turned into a **regular expression** (a text pattern) used for matching:

| Path | Regex |
| --- | --- |
| `/api/v1/expenses` | `^/api/v1/expenses$` |
| `/api/v1/expenses/{expense_id}` | `^/api/v1/expenses/(?P<expense_id>[^/]+)$` |
| `/api/v1/reports/by-category` | `^/api/v1/reports/by\-category$` |

`^` means "start of the text", `$` means "end of the text", and `(?P<expense_id>[^/]+)` means "one or more characters that are not a slash; remember them under the name `expense_id`". Note that the regex accepts **any** text for `expense_id`, even `abc`. Turning it into an `int` (and rejecting `abc`) is pydantic's job later, not the router's.

## The shared machinery (read once; every endpoint uses it)

All eight endpoints share the same dependencies and the same session rules. I explain them here once, word by word. The endpoint sections then say *which* pieces run and in *which order*, and point back here for the details.

### Block 1: The words in every function signature

Here is the signature of `list_expenses` as an example (from `app/routers/expenses.py` lines 67-85):

```python
def list_expenses(
    db: DatabaseSession,
    current_user: CurrentUser,
    date_range: DateRangeFilter,
    category_id: Annotated[
        int | None, Query(description="Only expenses in this category")
    ] = None,
    ...
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many expenses to skip")] = 0,
) -> ExpenseListResponse:
```

**Word by word**

- `db: DatabaseSession` - a parameter named `db` with the *type hint* `DatabaseSession`. A type hint is the part after the colon; Python itself ignores it, but FastAPI reads it. `DatabaseSession` is defined in `app/core/dependencies.py` line 27 as `Annotated[Session, Depends(get_db)]`.
- `Annotated[X, Y]` - from the `typing` module. It means "the type is `X`, and here is extra information `Y` attached to it". Python treats the variable as an `X`. FastAPI reads the extra information `Y`. So `Annotated[Session, Depends(get_db)]` means: "this parameter is a SQLAlchemy `Session`, and to get one, call `get_db`". In your old code you wrote `db: Session = Depends(get_db)` on every endpoint; `Annotated` lets the project write that once and reuse the name `DatabaseSession`.
- `Depends(get_db)` - a FastAPI marker that says "do not expect this value from the client; call the function `get_db` and give me what it returns (or yields)". The function given to `Depends` is called a **dependency**. A dependency can itself have parameters with `Depends`, which gives a **dependency tree**.
- `current_user: CurrentUser` - `CurrentUser` is `Annotated[User, Depends(get_current_user)]` (dependencies.py line 57). So `current_user` is a `User` ORM object, produced by calling `get_current_user`.
- `date_range: DateRangeFilter` - `Annotated[DateRange, Depends(get_date_range)]` (line 88). A `DateRange` object produced by `get_date_range`.
- `int | None` - "an `int`, or `None`". The `|` between types means "or". `None` is Python's "no value". This is the modern spelling of `Optional[int]` which you used in your old `schema.py`.
- `Query(...)` - a FastAPI marker that says "this value comes from the **query string**" (the part of the URL after `?`, like `?limit=10&offset=20`). Inside it you can put rules: `ge=1` means "greater than or equal to 1", `le=100` "less than or equal to 100", `max_length=150` "at most 150 characters". `description=` only feeds the `/docs` page.
- `= None`, `= 20`, `= 0` - default values. A parameter with a default is optional: when the client does not send it, the default is used. A parameter without a default (like `expense_id: int` in `get_expense`) is required.
- `-> ExpenseListResponse` - the *return type hint*. FastAPI does not use it for the response here because `response_model=` is given in the decorator; it is documentation for humans and editors.

A rule that matters for ordering: FastAPI looks at the parameters **in the order they are written**. That order decides the order in which the dependencies run (Block 3).

### Block 2: What uvicorn and Starlette do before FastAPI sees the request

uvicorn is the server program. It owns the network socket. When bytes arrive it:

1. parses the HTTP text (request line, headers, body) with its HTTP parser,
2. builds an **ASGI scope**: a plain Python `dict` with keys like `"type": "http"`, `"method": "POST"`, `"path": "/api/v1/expenses"`, `"query_string": b"limit=10"`, `"headers": [(b"authorization", b"Bearer ..."), ...]`,
3. calls `await app(scope, receive, send)` where `app` is the `FastAPI` object from `app/main.py`. `receive` is a function the app calls to get the body; `send` is a function the app calls to send the response.

ASGI is just the name of this agreement between a server (uvicorn) and a framework (FastAPI/Starlette): "call me with scope, receive, send".

The `FastAPI` object is a chain of **middleware** (code that wraps every request). I printed the chain from the running app, outermost first:

```
starlette.middleware.errors.ServerErrorMiddleware    -> turns an unexpected crash into a 500 response
starlette.middleware.cors.CORSMiddleware             -> the one main.py added with app.add_middleware(...)
starlette.middleware.exceptions.ExceptionMiddleware  -> installs the handlers that turn HTTPException / 422 into JSON
fastapi.middleware.asyncexitstack.AsyncExitStackMiddleware
fastapi.routing.APIRouter                            -> the router: finds the route
```

The router walks its list of routes in registration order (`health`, then `auth`, `users`, `categories`, `expenses`, `reports`, because that is the order of the `include_router` calls in `main.py`). For each route it asks "does the regex match the path?" and "is the method allowed?". A route whose path matches but whose method does not (for example `POST /api/v1/expenses` when the request is `GET /api/v1/expenses`) is remembered as a *partial* match and is only used to answer `405 Method Not Allowed` if nothing better is found. The first **full** match wins.

One small extra: if nothing matches and the path ends with `/`, Starlette tries again without the slash (`redirect_slashes=True`, the default). I tested `POST /api/v1/expenses/`: the answer is `307 Temporary Redirect` with the header `location: http://.../api/v1/expenses` and no body. The client is expected to repeat the request at the new URL.

Once a route is chosen, Starlette calls the route's handler. In FastAPI that handler is the function built by `get_request_handler` in `fastapi/routing.py`. Everything from Block 3 on happens inside it.

### Block 3: The order in which FastAPI resolves parameters (the algorithm)

This is the single most useful thing to understand in this document, so here it is as FastAPI really does it. I read it in `fastapi/routing.py` (function `get_request_handler`) and `fastapi/dependencies/utils.py` (function `solve_dependencies`).

**Step A - read the body (only for POST/PATCH here).** Before any dependency runs, the handler reads the raw body bytes. If the `Content-Type` is `application/json` it parses the JSON text into a Python `dict`. If the JSON text is broken (for example a missing comma), it raises a `422` right here, with `"type": "json_invalid"`, and **nothing else runs** - not even `get_db`. An *empty* body is not an error at this step; it becomes `None` and is judged later in Step C.

**Step B - solve the dependency tree, depth first, in signature order.** `solve_dependencies` loops over the endpoint's `Depends` parameters in the order they appear in the signature. For each one it first recursively solves *that dependency's own* `Depends` parameters, then calls it. So for

```python
def create_expense(expense_in: ExpenseCreate, db: DatabaseSession, current_user: CurrentUser)
```

the tree (printed from the running app) is:

```
create_expense
├── get_db                      (param "db")
└── get_current_user            (param "current_user")
    ├── OAuth2PasswordBearer    (param "token")   <- oauth2_scheme
    └── get_db                  (param "db")      <- same get_db as above
```

and the run order is: `get_db` → `oauth2_scheme` → `get_db` (**served from cache, not called again**) → `get_current_user`.

The **cache** works like this: each dependency gets a key made of the function object plus its scope (I checked `_get_cache_key` in `fastapi/dependencies/models.py`). The first time `get_db` is solved its yielded value (the `Session`) is stored under that key; when `get_current_user` asks for `get_db` the same `Session` object is handed back. That is why the endpoint and `get_current_user` share one session per request (my capture shows exactly one "session opened" per request).

Three kinds of dependency are called in three ways:

- `get_db` is a **generator** (it uses `yield`). FastAPI wraps it in a context manager and enters it on an "exit stack" that belongs to the request. The code after `yield` runs when that stack is closed - see Block 4 for *when* that is.
- `oauth2_scheme` is an `async` callable, so it is awaited directly.
- `get_current_user` and `get_date_range` are plain `def` functions, so FastAPI runs each one in a **worker thread** (`run_in_threadpool`) so that the server's event loop is not blocked while they talk to the database.

Two very different things can go wrong inside Step B:

- A dependency **raises `HTTPException`** (401 from the token checks, 422 from `get_date_range`). The exception stops everything immediately. Dependencies later in the order never run, and the body is never validated.
- A dependency's **own query parameters fail validation** (for example `?start_date=bad` for `get_date_range`). This does *not* raise. The errors are added to a list, that dependency is skipped (its function is never called), and solving continues with the next dependency.

**Step C - validate the endpoint's own parameters**, in this fixed order: path parameters, then query parameters, then headers, then cookies, then the body. Each failure is appended to the same error list from Step B.

**Step D - decide.** If the error list is not empty, raise `RequestValidationError`, which the handler installed by `ExceptionMiddleware` turns into `422` with `{"detail": [ ...one entry per error... ]}`. Otherwise call the endpoint function (in a worker thread, because all endpoints here are plain `def`).

Two consequences you will see in the endpoint sections:

- A request with a bad token **and** a bad body gets `401`, never `422`: Step B raised before Step C ran.
- A request with a good token and a bad body still costs one `SELECT` on `users`: `get_current_user` ran (and queried) in Step B before the body was judged in Step C.

### Block 4: `get_db` - one session per request

File `app/database/session.py` lines 27-33:

```python
def get_db() -> Generator[Session, None, None]:
    """Open a session for the request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Word by word**

- `def get_db()` - a function with no parameters. FastAPI calls it; nobody passes it anything.
- `-> Generator[Session, None, None]` - the return type hint says "this is a generator that yields `Session` objects". A **generator** is a function that contains `yield`. Calling it does not run the body; it gives back an object you can step through. The first step runs the body until `yield` and hands out the yielded value. The next step resumes after `yield`.
- `db = SessionLocal()` - `SessionLocal` is the `sessionmaker(...)` factory from line 24 of the same file. Calling it creates a new, empty `Session`. **No database connection is taken yet.** The session borrows a connection from the engine's pool only when the first SQL statement is executed. (My capture of the `401` requests shows "session opened" and "closed" with no `BEGIN` in between: the session was created but never touched the database.)
- `try:` ... `finally:` - whatever happens inside `try` (normal end, or an exception), the `finally` block runs.
- `yield db` - hand the session to FastAPI, and **pause here**. FastAPI gives `db` to whoever asked (`get_current_user`, the endpoint).
- `db.close()` - runs when FastAPI resumes the generator. `Session.close()` does two things: if a transaction is still open it is rolled back (you will see `ROLLBACK` at the end of almost every request below), and the connection is returned to the pool. The `Session` object itself becomes empty and unusable.

**When exactly does the `finally` run?** I read this in `fastapi/routing.py` (`request_response`). The handler is wrapped like this:

```python
async with AsyncExitStack() as request_stack:        # get_db is entered on THIS stack
    scope["fastapi_inner_astack"] = request_stack
    async with AsyncExitStack() as function_stack:
        scope["fastapi_function_astack"] = function_stack
        response = await f(request)                   # dependencies + endpoint + response_model
    await response(scope, receive, send)              # the bytes go to uvicorn here
```

`get_db` has no explicit scope, and for a generator dependency FastAPI then uses the scope `"request"` (I checked `_get_computed_scope` in `fastapi/dependencies/models.py`), which means it is entered on `request_stack`. `request_stack` closes when its `async with` block ends, which is **after** `await response(scope, receive, send)`. So on the happy path:

1. the endpoint returns,
2. `response_model` reads the ORM object (this may run extra `SELECT`s - the session is still open, which is exactly why this works),
3. the response bytes are sent to the client,
4. only then `db.close()` runs.

On an error path (an `HTTPException` or a validation error), the exception flies out of `f(request)`, which unwinds both `async with` blocks - so `db.close()` runs **first** - and only then the exception handler builds and sends the JSON error. Keep this in mind: for errors, the session is already closed when the error response is sent; for success, it is closed after.

`contextmanager_in_threadpool` in `fastapi/concurrency.py` is what runs the generator's enter and exit steps in a worker thread; you do not have to care about it beyond knowing that `db.close()` runs in a thread, not on the event loop.

### Block 5: `oauth2_scheme` - read the `Authorization` header

File `app/core/dependencies.py` line 24:

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
```

`OAuth2PasswordBearer` is a FastAPI class. An *instance* of it (`oauth2_scheme`) can be called like a function, which is why it can be used in `Depends(oauth2_scheme)`. `tokenUrl="/api/v1/auth/login"` is only used by the `/docs` page so that its "Authorize" button knows where to post the login form.

What the call does (I read `OAuth2PasswordBearer.__call__` in `fastapi/security/oauth2.py`):

```python
async def __call__(self, request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        if self.auto_error:
            raise self.make_not_authenticated_error()
        else:
            return None
    return param
```

- It reads the header `Authorization`.
- `get_authorization_scheme_param` splits the header value at the first space: `"Bearer eyJ..."` becomes `scheme="Bearer"`, `param="eyJ..."`.
- If the header is missing, or the first word is not `bearer` (case does not matter), it raises `HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})`. I checked `make_not_authenticated_error` for the exact text. `auto_error` is `True` by default, so this project always raises.
- Otherwise it returns the token text only (the part after the space, with surrounding spaces stripped).

So `oauth2_scheme` never checks whether the token is *valid*. It only extracts it. Validation is `get_current_user`'s job.

### Block 6: `get_current_user` - from token to `User` row

File `app/core/dependencies.py` lines 33-53:

```python
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DatabaseSession,
) -> User:
    """Read the Bearer token and return the logged-in user, or respond 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error

    user = db.get(User, user_id)
    # The token can outlive the account (deleted or deactivated user).
    if user is None or not user.is_active:
        raise credentials_error

    return user
```

**The token itself.** A JWT (JSON Web Token) is three pieces of base64 text joined by dots: `header.payload.signature`. For Asha's token:

- header (decoded): `{"alg": "HS256", "typ": "JWT"}` - "signed with HMAC-SHA256".
- payload (decoded): `{"sub": "1", "exp": 1791291693}`. These two keys are called **claims**. `sub` ("subject") is the standard name for "who this token is about" - here the user id as a string. `exp` ("expiration") is a Unix timestamp (seconds since 1970-01-01 UTC); `1791291693` is `2026-10-06 13:01:33 UTC`, one hour after login because `ACCESS_TOKEN_EXPIRE_MINUTES` is 60.
- signature: HMAC of the first two pieces using `settings.SECRET_KEY`. Anyone can *read* the payload (it is only base64), but nobody can *change* it without the secret, because the signature would no longer match.

**Line by line**

- `credentials_error = HTTPException(...)` - builds the error object in advance; it is only *raised* later. `status.HTTP_401_UNAUTHORIZED` is the number 401. The `WWW-Authenticate: Bearer` header is what the HTTP standard asks a server to send with a 401 so that clients know which kind of credentials are expected.
- `user_id = decode_access_token(token)` - `app/core/security.py` lines 48-60. It calls `jwt.decode(token, SECRET_KEY, algorithms=["HS256"])`, which checks the signature **and** that `exp` is still in the future, then returns `int(payload["sub"])`. Every failure (bad signature, expired, not even a JWT, no `sub`, `sub` not a number) is caught and turned into `None`. I ran it: a token with two characters changed → `None`; the text `"nope"` → `None`.
- `if user_id is None: raise credentials_error` - the first 401 exit.
- `user = db.get(User, user_id)` - `Session.get(Model, primary_key)`. First it looks in the session's **identity map** (a dictionary "primary key → object already loaded in this session"). The session is brand new for this request, so the map is empty and it emits:

  ```sql
  SELECT users.id AS users_id, users.email AS users_email, users.full_name AS users_full_name,
         users.hashed_password AS users_hashed_password, users.is_active AS users_is_active,
         users.created_at AS users_created_at
  FROM users
  WHERE users.id = %(pk_1)s
  ```
  params: `{'pk_1': 1}`. This is also the statement that starts the request's transaction: SQLAlchemy logs `BEGIN (implicit)` just before it (Block 8). It returns a `User` object or `None`.
- `if user is None or not user.is_active: raise credentials_error` - the second 401 exit. `user is None` happens when the account was deleted after the token was issued. `not user.is_active` happens when the account was deactivated (I tested this: deactivating user 3 and reusing his still-valid token gives `401 Could not validate credentials`).
- `return user` - the `User` object becomes `current_user` in the endpoint. Only `current_user.id` is used by the endpoints in this document.

Summary of the 401s a protected endpoint can produce, in the order they are checked:

| Situation | Raised by | Status | `detail` |
| --- | --- | --- | --- |
| No `Authorization` header, or it does not start with `Bearer ` | `oauth2_scheme` | 401 | `Not authenticated` |
| Token tampered, expired, or not a JWT | `get_current_user` line 46 | 401 | `Could not validate credentials` |
| Token fine but user deleted or `is_active = false` | `get_current_user` line 51 | 401 | `Could not validate credentials` |

All three carry the header `www-authenticate: Bearer`.

### Block 7: `get_date_range` and the `DateRange` dataclass

File `app/core/dependencies.py` lines 63-88:

```python
@dataclass
class DateRange:
    start_date: date | None
    end_date: date | None


def get_date_range(
    start_date: Annotated[
        date | None,
        Query(description="Only include expenses on or after this date (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="Only include expenses on or before this date (YYYY-MM-DD)"),
    ] = None,
) -> DateRange:
    """Optional ?start_date=&end_date= filter shared by expenses and reports."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date",
        )
    return DateRange(start_date=start_date, end_date=end_date)


DateRangeFilter = Annotated[DateRange, Depends(get_date_range)]
```

**Word by word**

- `@dataclass` - a decorator from the standard library `dataclasses`. You write only the fields with type hints; it writes `__init__`, `__repr__` and `__eq__` for you. So `DateRange(start_date=..., end_date=...)` works, printing one gives `DateRange(start_date=datetime.date(2026, 9, 1), end_date=datetime.date(2026, 10, 31))`, and two with the same values compare equal. It is a tiny bag of two values with no behaviour - cheaper and simpler than a pydantic model, which it does not need to be because no validation happens here.
- `start_date: date | None` ... `= None` - two optional query parameters. `date` is `datetime.date`. pydantic parses the text `2026-09-01` into `date(2026, 9, 1)`. Anything else (`bad`, `01-09-2026`, `2026-13-01`) becomes a validation error with `loc: ["query", "start_date"]` and the dependency function is skipped (Block 3, Step B).
- `if start_date and end_date and start_date > end_date` - only when both were sent. `date` objects compare in calendar order (`date(2026,10,31) > date(2026,10,1)` is `True`).
- `raise HTTPException(status_code=422, detail="start_date must be on or before end_date")` - note this is a **string** `detail`, not the list of error objects that pydantic produces. `status.HTTP_422_UNPROCESSABLE_CONTENT` is the number 422 (Starlette renamed the constant from `UNPROCESSABLE_ENTITY`; both exist). Because this is an `HTTPException`, it stops the request immediately - the endpoint's own query parameters are **not** validated afterwards. I tested `?start_date=2026-10-31&end_date=2026-10-01&limit=0`: the answer is only `{"detail": "start_date must be on or before end_date"}`; the invalid `limit=0` is never mentioned.
- `return DateRange(start_date=start_date, end_date=end_date)` - the object the endpoint receives as `date_range`.

Possible outcomes:

| Query string | `date_range` | Error |
| --- | --- | --- |
| (nothing) | `DateRange(start_date=None, end_date=None)` | none |
| `?start_date=2026-09-01` | `DateRange(start_date=date(2026,9,1), end_date=None)` | none |
| `?start_date=bad` | function not called | 422 list entry, `type: date_from_datetime_parsing` |
| `?start_date=2026-10-31&end_date=2026-10-01` | function raises | 422, string detail |

### Block 8: SQLAlchemy session mechanics you will see in every function

Every endpoint section below shows a list of SQL statements. These are the rules that explain *why* each statement appears where it does. All of them were confirmed by the capture.

- **Autobegin / `BEGIN (implicit)`.** A `Session` does not open a transaction when it is created. It opens one the moment the first statement is executed. SQLAlchemy logs this as `BEGIN (implicit)`. With psycopg2 the real `BEGIN` is sent by the driver just before the first statement.
- **`db.get(User, 1)`** - looks in the identity map, then `SELECT ... WHERE users.id = %(pk_1)s`.
- **`db.scalar(stmt)`** - executes the `select(...)` and returns the first column of the first row, or `None` if there is no row. When the statement is `select(Expense)` the "first column" is the whole `Expense` object. No `LIMIT` is added; the database may return several rows but only the first is read.
- **`db.scalars(stmt).all()`** - executes and returns a Python `list` of objects (first column of every row).
- **`db.execute(stmt).one()` / `.all()`** - executes and returns `Row` objects. A `Row` behaves like a tuple (you can unpack it: `a, b, c = row`) and also lets you read columns by name (`row.total_amount`). `.one()` insists on exactly one row.
- **Identity map.** Every object the session loads is stored under its primary key. Loading the same row again in the same session gives back the *same* Python object (and, if the row was already loaded, no new `SELECT` for `get`).
- **`db.add(obj)`** - marks a new object as **pending**. Nothing is sent yet.
- **Flush.** The moment the session turns pending/changed objects into `INSERT`/`UPDATE`/`DELETE` statements. `autoflush=False` in `SessionLocal` means a plain query does not flush; `db.commit()` always flushes first.
- **`db.commit()`** - flush, then send `COMMIT`, then **expire** every object in the session (`expire_on_commit=True` is the default). "Expire" means: forget the loaded column values; the next attribute read will reload them from the database. After `commit()` the `Expense` object's `__dict__` holds no column values at all (I printed it: empty).
- **`db.refresh(obj)`** - send one `SELECT ... WHERE expenses.id = %(pk_1)s` and refill the column attributes. Relationship attributes that use the default lazy loading (`expense.category`, `expense.owner`) are **not** loaded by `refresh` - I checked the docstring: they stay lazy unless named explicitly.
- **Lazy loading.** Reading a relationship attribute that is not loaded yet (`expense.category`) makes the session run a `SELECT` on the related table right then. It needs an open session, which is why Block 4's "close after the response" matters.
- **`selectinload(Expense.category)`** - a loader option that says "after loading the expenses, load all their categories in **one** extra query, `WHERE categories.id IN (...)`", instead of one query per expense (the "N+1 problem").
- **`onupdate=func.now()`** on `updated_at` - whenever the ORM emits an `UPDATE` for an expense, it adds `updated_at=now()` to the `SET` list automatically. You never set it by hand.
- **`server_default=func.now()`** on `created_at`/`updated_at` and the auto-increment `id` - the database fills these during `INSERT`. SQLAlchemy asks for them back with `RETURNING` so that the object knows its `id` right after the flush.
- **`db.delete(obj)`** - marks the object for deletion; the `DELETE` statement is sent at the next flush (the `commit()`).
- **`db.close()`** - if a transaction is open, `ROLLBACK`; return the connection to the pool. After a `commit()` followed by a `refresh()`, a *new* transaction was auto-begun by the `refresh`'s `SELECT`, so you will see `COMMIT` ... `SELECT` ... `ROLLBACK`. That final `ROLLBACK` throws away nothing - the data was already committed. It just ends the read-only transaction cleanly.

### Block 9: How the response is built, and how errors become JSON

**Success.** After the endpoint function returns, the handler (`fastapi/routing.py`, function `serialize_response`) does two steps when `response_model=` was given:

1. `field.validate(returned_value)` - pydantic validates the returned value against the response model. For an ORM object this works because `ExpenseResponse` has `model_config = ConfigDict(from_attributes=True)`, and FastAPI additionally passes `from_attributes=True` (I checked `fastapi/_compat/v2.py`). "From attributes" means: instead of expecting a `dict` with keys, read `obj.id`, `obj.title`, `obj.category`, ... as attributes. Reading `obj.category` is what triggers the lazy load (Block 8). Pydantic then also converts: `"upi"` (a plain string in the database) becomes `PaymentMethod.UPI`; the `Category` object becomes a `CategorySummary`.
2. `field.serialize_json(value)` - pydantic turns the validated model into JSON bytes in one go (this version of FastAPI uses pydantic's Rust-based `dump_json`). Conversions you will see: `Decimal("250.00")` → the JSON string `"250.00"` (pydantic writes decimals as strings so no precision is lost), `date(2026, 10, 3)` → `"2026-10-03"`, an aware UTC `datetime` → `"2026-10-06T12:02:13.481729Z"`, `PaymentMethod.UPI` → `"upi"`, `None` → `null`.

Then a `Response` is built with `media_type="application/json"` and the status code from the decorator (`status_code=201` for `create_expense`; the default `200` elsewhere). For `delete_expense` the function returns a `Response` object itself; FastAPI then uses it as is and skips both steps.

**Errors.** Both kinds of error are caught by Starlette's `wrap_app_handling_exceptions` and handed to the handlers that FastAPI installed:

- `HTTPException` → `http_exception_handler` in `fastapi/exception_handlers.py` → `JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)`. So `detail` is whatever the code put there: a string in this project.
- `RequestValidationError` → `request_validation_exception_handler` → status 422, body `{"detail": [ ...error dicts... ]}`. Each error dict has `type` (a machine-readable code like `missing` or `greater_than`), `loc` (where: `["body", "amount"]`, `["query", "limit"]`, `["path", "expense_id"]`), `msg` (human text), `input` (what was received) and sometimes `ctx` (the rule that failed, like `{"gt": 0}`).

<!-- CONTINUE -->
