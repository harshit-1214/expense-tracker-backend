# app/routers/ part 2: expenses and reports

This document explains two files inside `app/routers/`, word by word:

| File                       | What it defines                                                        |
| -------------------------- | ---------------------------------------------------------------------- |
| `app/routers/expenses.py`  | the five `/expenses` endpoints: create, list (filters + pages), read one, update, delete |
| `app/routers/reports.py`   | the three `/reports` endpoints: overall summary, totals by category, totals by month |

Both routers are plugged into the app in `app/main.py` with
`app.include_router(expenses.router, prefix=settings.API_V1_PREFIX)` and the same
for `reports.router`, so the real URLs are `/api/v1/expenses...` and
`/api/v1/reports...`.

These two files are where the project does its "real work" with the database:
filtering, counting, paging, summing and grouping. So this document spends a lot
of time on SQLAlchemy's `select()` and on a few Python features (`*`, `**`,
`Annotated`, `Decimal`, dictionary comprehensions) that you have not used before.

Every fact in this document (the SQL text, the error messages, the Python types
that come back from the database) was checked by running the real code with
FastAPI 0.141.1, Pydantic 2.13.5 and SQLAlchemy 2.0.54 on Python 3.14. When a
block says "this produces this SQL", that SQL was captured from a real run.

A reminder of three names you already met in document 04
(`app/core/dependencies.py`), because they appear in every endpoint here:

- `DatabaseSession` = `Annotated[Session, Depends(get_db)]` - "give me a database session for this request".
- `CurrentUser` = `Annotated[User, Depends(get_current_user)]` - "read the Bearer token, give me the logged-in `User`, or answer 401".
- `DateRangeFilter` = `Annotated[DateRange, Depends(get_date_range)]` - "read the optional `?start_date=&end_date=` query parameters, check that start is not after end, give me a small `DateRange` object with `.start_date` and `.end_date`".

They are explained again, shortly, the first time each one is used below.

---

## File: app/routers/expenses.py

### What this file is for

This file is the heart of the API. It defines the five endpoints a client uses
to manage expenses:

| Method   | URL                     | Function          | Job                                  |
| -------- | ----------------------- | ----------------- | ------------------------------------ |
| `POST`   | `/expenses`             | `create_expense`  | add one expense                      |
| `GET`    | `/expenses`             | `list_expenses`   | one page of expenses, with filters   |
| `GET`    | `/expenses/{id}`        | `get_expense`     | one expense                          |
| `PATCH`  | `/expenses/{id}`        | `update_expense`  | change some fields of one expense    |
| `DELETE` | `/expenses/{id}`        | `delete_expense`  | remove one expense                   |

The single most important rule in this file: **every database query includes
`Expense.owner_id == current_user.id`**. A user can only ever see or touch their
own rows. There is no endpoint that returns another user's expense, not even a
"404 vs 403" hint that it exists.

Its place in the project:

- **It imports from**: `app.core.dependencies` (the `DatabaseSession`, `CurrentUser`,
  `DateRangeFilter` helpers), `app.models.expense` (the `Expense` table class and the
  `PaymentMethod` list), `app.routers.categories` (one helper function,
  `get_owned_category_or_404`, re-used so the rule "you can only use your own
  category" is written once), and `app.schemas.expense` (the request and
  response shapes).
- **It is imported by**: `app/main.py` only, which does
  `app.include_router(expenses.router, prefix="/api/v1")`.

### The whole file

```python
"""
Expense endpoints: create, list (with filters + pagination), read, update, delete.

Every query is filtered by `owner_id`, so users can only ever see and
change their own expenses.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import CurrentUser, DatabaseSession, DateRangeFilter
from app.models.expense import Expense, PaymentMethod
from app.routers.categories import get_owned_category_or_404
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseUpdate,
)

router = APIRouter(prefix="/expenses", tags=["Expenses"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_owned_expense_or_404(db: Session, expense_id: int, owner_id: int) -> Expense:
    """Fetch an expense that belongs to the user, or respond 404."""
    expense = db.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.owner_id == owner_id)
    )
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )
    return expense


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an expense",
)
def create_expense(
    expense_in: ExpenseCreate, db: DatabaseSession, current_user: CurrentUser
) -> Expense:
    if expense_in.category_id is not None:
        # Stops a user from attaching their expense to someone else's category.
        get_owned_category_or_404(db, expense_in.category_id, current_user.id)

    expense = Expense(**expense_in.model_dump(), owner_id=current_user.id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("", response_model=ExpenseListResponse, summary="List my expenses")
def list_expenses(
    db: DatabaseSession,
    current_user: CurrentUser,
    date_range: DateRangeFilter,
    category_id: Annotated[
        int | None, Query(description="Only expenses in this category")
    ] = None,
    payment_method: Annotated[
        PaymentMethod | None, Query(description="Only expenses paid this way")
    ] = None,
    min_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    max_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    search: Annotated[
        str | None,
        Query(max_length=150, description="Text to look for in the title (case-insensitive)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many expenses to skip")] = 0,
) -> ExpenseListResponse:
    # Build the WHERE conditions once; they are shared by the count query
    # and the page query below.
    filters = [Expense.owner_id == current_user.id]
    if date_range.start_date is not None:
        filters.append(Expense.expense_date >= date_range.start_date)
    if date_range.end_date is not None:
        filters.append(Expense.expense_date <= date_range.end_date)
    if category_id is not None:
        filters.append(Expense.category_id == category_id)
    if payment_method is not None:
        filters.append(Expense.payment_method == payment_method.value)
    if min_amount is not None:
        filters.append(Expense.amount >= min_amount)
    if max_amount is not None:
        filters.append(Expense.amount <= max_amount)
    if search:
        # autoescape=True treats % and _ typed by the user as normal characters.
        filters.append(Expense.title.icontains(search, autoescape=True))

    total = db.scalar(select(func.count()).select_from(Expense).where(*filters))

    expenses = db.scalars(
        select(Expense)
        # Load all categories for the page in one extra query (avoids N+1).
        .options(selectinload(Expense.category))
        .where(*filters)
        # Newest first; id breaks ties so pages never overlap.
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return ExpenseListResponse(items=expenses, total=total, limit=limit, offset=offset)


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Get one expense")
def get_expense(
    expense_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Expense:
    return get_owned_expense_or_404(db, expense_id, current_user.id)


@router.patch("/{expense_id}", response_model=ExpenseResponse, summary="Update an expense")
def update_expense(
    expense_id: int,
    expense_in: ExpenseUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Expense:
    expense = get_owned_expense_or_404(db, expense_id, current_user.id)

    # exclude_unset=True -> only the fields the client actually sent.
    changes = expense_in.model_dump(exclude_unset=True)
    if changes.get("category_id") is not None:
        get_owned_category_or_404(db, changes["category_id"], current_user.id)

    for field_name, value in changes.items():
        setattr(expense, field_name, value)

    db.commit()
    db.refresh(expense)
    return expense


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
)
def delete_expense(
    expense_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Response:
    expense = get_owned_expense_or_404(db, expense_id, current_user.id)
    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

### Walkthrough, block by block

#### Block 1: the module docstring

```python
"""
Expense endpoints: create, list (with filters + pagination), read, update, delete.

Every query is filtered by `owner_id`, so users can only ever see and
change their own expenses.
"""
```

- `"""..."""` - three double quotes start and end a multi-line string. When such
  a string is the very first thing in a file it is the **module docstring**: a
  note that describes the file. Python stores it in `__doc__`; editors show it
  when you hover the module name. It runs no code.
- `Expense endpoints: create, list (with filters + pagination), read, update, delete.` -
  tells the reader the five jobs of the file. "pagination" means "giving the
  results page by page instead of all at once".
- `Every query is filtered by owner_id ...` - states the security rule of the
  file. If you remember one sentence from this file, remember this one.

**Why it is here**: so the next developer (including you in six months) knows
the file's purpose and its one rule without reading all the code.

**If you removed or changed it**: nothing would break. The file would just be
less friendly to read.

#### Block 2: Python standard-library imports

```python
from decimal import Decimal
from typing import Annotated
```

- `from ... import ...` - "take one name out of a module and make it usable in
  this file".
- `decimal` - a module that ships with Python. It provides exact decimal numbers.
- `Decimal` - the class from that module. A `Decimal("0.10")` is exactly one
  tenth. A Python `float` `0.1` is **not** exactly one tenth (it is the closest
  binary fraction, `0.1000000000000000055...`). That is why `0.1 + 0.2 == 0.3` is
  `False` with floats and `True` with Decimals. Money must be exact, so this
  project uses `Decimal` for every amount. Here it is used as the type of the
  `min_amount` and `max_amount` query parameters.
- `typing` - the standard module that holds the tools for **type hints** (the
  `: int`, `-> str` notes you already use).
- `Annotated` - a special type-hint tool. `Annotated[X, extra]` means "the type is
  `X`, and here is some **extra information** attached to it". Python itself
  ignores the extra part. FastAPI reads it. In this file the extra part is a
  `Query(...)` object that tells FastAPI how to validate a query parameter.
  You will see it in action in Block 22, with a full explanation there.

**Why it is here**: `Decimal` so that amount filters are exact money values;
`Annotated` so each query parameter can carry its validation rules (`ge=0`,
`max_length=150`...) right next to its type.

**If you removed or changed it**: removing `Decimal` gives `NameError: name
'Decimal' is not defined` when Python loads the file (the `min_amount` parameter
mentions it). Removing `Annotated` gives the same kind of `NameError` on the
first `Annotated[...]`. If you changed `Decimal` to `float` for the amount
filters, values like `?min_amount=0.1` would arrive as an inexact float before
being compared to an exact `NUMERIC` column; harmless for a filter in practice,
but not the habit this project wants for money.

#### Block 3: FastAPI imports

```python
from fastapi import APIRouter, HTTPException, Query, Response, status
```

- `fastapi` - the web framework.
- `APIRouter` - a class for a "mini app" that holds a group of endpoints. You
  used it in your old `post.py`. The main app later includes the router.
- `HTTPException` - the exception you raise to send an error status (404, 409,
  ...) with a JSON `{"detail": ...}` body. Same as in your old code.
- `Query` - a function that returns a small object describing **one query
  parameter** (the `?name=value` part of a URL): its default, its rules (`ge`,
  `le`, `max_length`) and its description for the docs page. It is new to you;
  full explanation in Block 22.
- `Response` - the plain, lowest-level HTTP response class. FastAPI re-exports it
  from Starlette (the library FastAPI is built on). It is used in
  `delete_expense` to send "204 No Content" with an empty body.
- `status` - a module of named constants for HTTP status codes:
  `status.HTTP_404_NOT_FOUND` is just the number `404`,
  `status.HTTP_201_CREATED` is `201`, `status.HTTP_204_NO_CONTENT` is `204`.
  Names are easier to read than bare numbers.

**Why it is here**: these are the five FastAPI tools this file needs: a router to
hang endpoints on, exceptions for errors, query-parameter rules, an empty
response for delete, and readable status codes.

**If you removed or changed it**: any missing name causes a `NameError` at
import time, which means the whole app fails to start (`app/main.py` imports
this file). For example, without `Query` the line `Query(description=...)` in
`list_expenses` cannot be evaluated.

#### Block 4: SQLAlchemy imports

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
```

- `sqlalchemy` - the database library.
- `func` - a special object that turns attribute names into SQL functions.
  `func.count()` becomes `count(*)`, `func.sum(Expense.amount)` becomes
  `sum(expenses.amount)`, `func.lower(x)` becomes `lower(x)`. Any name works;
  SQLAlchemy writes it into the SQL as-is. In this file only `func.count()` is
  used (Block 32).
- `select` - the function that starts a `SELECT` statement in SQLAlchemy 2.0
  style. `select(Expense)` means "SELECT all columns of the expenses table".
  You then chain `.where(...)`, `.order_by(...)`, `.limit(...)` onto it. This
  replaces `db.query(Expense)` from your old code (which still works but is the
  older style).
- `sqlalchemy.orm` - the part of SQLAlchemy that maps classes to tables (ORM =
  Object Relational Mapper).
- `Session` - the class of the `db` object. One `Session` = one conversation with
  the database (a transaction). Used here only as a type hint in
  `get_owned_expense_or_404(db: Session, ...)`.
- `selectinload` - a **loader option**. It tells SQLAlchemy: "after you load these
  expenses, load all their categories in **one** extra `SELECT ... WHERE id IN
  (...)` query, instead of one query per expense". Full explanation, with the
  real SQL, in Block 33.

**Why it is here**: `select` and `func` build the queries; `Session` documents the
helper's parameter type; `selectinload` keeps the list endpoint fast.

**If you removed or changed it**: `NameError` at import for any missing name.
Removing only the `selectinload(...)` line (not the import) would still work but
would make the list endpoint run up to one extra query per expense - see Block 33.

#### Block 5: project dependency imports

```python
from app.core.dependencies import CurrentUser, DatabaseSession, DateRangeFilter
```

- `app.core.dependencies` - the project file explained in document 04.
- `CurrentUser` - an alias. It is `Annotated[User, Depends(get_current_user)]`.
  Writing `current_user: CurrentUser` in an endpoint is the same as writing
  `current_user: User = Depends(get_current_user)`, but shorter and impossible to
  get wrong. FastAPI runs `get_current_user`, which reads the `Authorization:
  Bearer <token>` header, checks the JWT, loads the `User` row and returns it (or
  raises 401).
- `DatabaseSession` - alias for `Annotated[Session, Depends(get_db)]`: a fresh
  database session for this request, closed automatically afterwards.
- `DateRangeFilter` - alias for `Annotated[DateRange, Depends(get_date_range)]`:
  FastAPI reads the optional `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` query
  parameters, rejects a start after the end with 422, and hands the endpoint a
  `DateRange` object with two attributes, `.start_date` and `.end_date` (each a
  `date` or `None`).

**Why it is here**: the three things almost every endpoint needs (a database
session, the logged-in user, and - for the list endpoint - the date filter), each
written once in `dependencies.py` and reused here.

**If you removed or changed it**: `NameError` at import. If you replaced
`current_user: CurrentUser` with nothing, the endpoints would no longer require a
login and would have no `current_user.id` to filter by - every user would see
everyone's data.

#### Block 6: model and helper imports

```python
from app.models.expense import Expense, PaymentMethod
from app.routers.categories import get_owned_category_or_404
```

- `app.models.expense` - the file that defines the `expenses` table (document 06).
- `Expense` - the table class. `Expense.id`, `Expense.title`, `Expense.amount`,
  `Expense.expense_date`, `Expense.payment_method`, `Expense.owner_id`,
  `Expense.category_id` are its columns; `Expense.category` is the relationship
  to the `Category` row. Used in every query here.
- `PaymentMethod` - the `enum` (a fixed list of allowed values: `cash`, `card`,
  `upi`, `bank_transfer`, `other`). Used as the type of the `payment_method` query
  parameter so FastAPI rejects anything else with 422.
- `app.routers.categories` - the categories router file (document 08).
- `get_owned_category_or_404` - a helper function from that file. Given `db`, a
  `category_id` and an `owner_id`, it returns the category if that user owns it,
  otherwise raises `HTTPException(404, "Category not found")`. Importing it here
  means the rule "you can only attach your own categories to an expense" is
  written in one place.

**Why it is here**: `Expense` is the table we read and write; `PaymentMethod`
validates a filter; the helper stops a user from attaching an expense to
someone else's category (Block 17 and Block 41).

**If you removed or changed it**: `NameError` at import. Without the category
check, user A could create an expense with `category_id` of user B's category.
Nothing in the database stops that (the foreign key only checks that the
category exists), so B's category would appear on A's expense and A's expense
would be counted in... nothing of B's, but the data would be wrong and A could
probe which category ids exist.

#### Block 7: schema imports

```python
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseUpdate,
)
```

- `from app.schemas.expense import (` ... `)` - the parentheses let one import
  statement spread over several lines, one name per line. Pure style.
- `ExpenseCreate` - the Pydantic model for the body of `POST /expenses` (`title`,
  `amount`, `expense_date`, `payment_method`, `notes`, `category_id`). Document 07.
- `ExpenseListResponse` - the response shape of `GET /expenses`: `{"items": [...],
  "total": n, "limit": n, "offset": n}`.
- `ExpenseResponse` - the response shape of one expense (includes a small nested
  `category` object or `null`).
- `ExpenseUpdate` - the body of `PATCH /expenses/{id}`, where every field is
  optional.

**Why it is here**: FastAPI needs the request schemas to validate incoming JSON
and the response schemas (`response_model=`) to shape and validate outgoing JSON.

**If you removed or changed it**: `NameError` at import. If you used
`ExpenseCreate` as the PATCH body instead of `ExpenseUpdate`, a client would have
to resend `title` and `amount` on every small change, because in `ExpenseCreate`
those fields are required.

#### Block 8: the router

```python
router = APIRouter(prefix="/expenses", tags=["Expenses"])
```

- `router` - the variable name. `app/main.py` imports this file and uses
  `expenses.router`.
- `=` - assignment.
- `APIRouter(...)` - creates the mini app.
- `prefix="/expenses"` - every path in this file is appended to `/expenses`. So
  `@router.post("")` is `/expenses` and `@router.get("/{expense_id}")` is
  `/expenses/{expense_id}`. Together with the `/api/v1` prefix added in
  `main.py`, the final URL is `/api/v1/expenses`.
- `tags=["Expenses"]` - a list with one string. The automatic docs page (`/docs`)
  groups all endpoints with the same tag under one heading, "Expenses".

**Why it is here**: one place to set the common URL prefix and docs heading.

**If you removed or changed it**: without `router`, `main.py` fails with
`AttributeError: module 'app.routers.expenses' has no attribute 'router'`.
Changing the prefix to `/expense` would change every URL and break every client.

#### Block 9: the "Helpers" comment banner

```python
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
```

- `#` - starts a comment; Python ignores the rest of the line.
- The dashes are just a visual ruler; `Helpers` is a section title.

**Why it is here**: the file has two kinds of functions: helpers (plain Python
functions, called by the endpoints) and endpoints (decorated with
`@router....`). The banner separates them so you can scan the file.

**If you removed or changed it**: nothing changes for Python.

#### Block 10: the helper's signature and docstring

```python
def get_owned_expense_or_404(db: Session, expense_id: int, owner_id: int) -> Expense:
    """Fetch an expense that belongs to the user, or respond 404."""
```

- `def` - defines a function.
- `get_owned_expense_or_404` - the name says exactly what it does: get an
  expense **owned** by this user, **or** answer **404**.
- `db: Session` - first parameter, the database session. `: Session` is a type
  hint (a note for readers and editors; Python does not enforce it).
- `expense_id: int` - which expense.
- `owner_id: int` - which user must own it.
- `-> Expense` - return type hint: the function gives back an `Expense` object.
  The arrow `->` always introduces the return type.
- `"""Fetch an expense ..."""` - the function's docstring: one sentence describing
  the contract.

This is **not** an endpoint (no `@router` decorator) and takes plain values, not
`Depends(...)`. It is called by `get_expense`, `update_expense` and
`delete_expense`.

**Why it is here**: three endpoints need the same "load it, check the owner, 404
if not" logic. Writing it once means it cannot be done slightly differently (or
forgotten) in one of them.

**If you removed or changed it**: each endpoint would repeat the four-line
query-and-check. The danger is not the repetition but forgetting the
`owner_id` part in one copy, which would let users read or delete each other's
expenses.

#### Block 11: the query

```python
    expense = db.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.owner_id == owner_id)
    )
```

- `expense =` - store the result.
- `db.scalar(...)` - run the statement and return **the first column of the first
  row**, or `None` if there are no rows. "Scalar" means "a single value" (as
  opposed to a row or a list). When you `select(Expense)`, the "first column" is
  the whole `Expense` object, so `db.scalar` gives you one `Expense` or `None`.
  This replaces `.first()` from your old `db.query(...).filter(...).first()`.
- `select(Expense)` - start a `SELECT expenses.id, expenses.title, ... FROM expenses`.
- `.where(...)` - add the `WHERE` part. It is the new-style name for `.filter(...)`.
- `Expense.id == expense_id` - this is **not** a Python comparison that gives
  `True`/`False`. `Expense.id` is a SQLAlchemy column object, and SQLAlchemy
  overrides `==` so that this expression builds the SQL fragment
  `expenses.id = :expense_id`. You did the same with `table.id == id` in your old
  code.
- `,` (the comma between the two conditions) - `.where()` accepts several
  conditions; it joins them with `AND`.
- `Expense.owner_id == owner_id` - the ownership check, inside the SQL itself.

The SQL that runs is:

```sql
SELECT expenses.id, expenses.title, expenses.amount, expenses.expense_date,
       expenses.payment_method, expenses.notes, expenses.owner_id,
       expenses.category_id, expenses.created_at, expenses.updated_at
FROM expenses
WHERE expenses.id = ? AND expenses.owner_id = ?
```

**Why it is here**: one round trip to the database answers both questions, "does
it exist?" and "is it mine?". Someone else's expense simply does not come back.

**If you removed or changed it**: dropping `Expense.owner_id == owner_id` would
return any expense by id. `GET /expenses/7` would then show user B's expense to
user A, and `DELETE /expenses/7` would let A delete it. Using `db.execute(...)`
instead of `db.scalar(...)` would give you a `Result` object, not an `Expense`,
and `expense.id` later would fail with `AttributeError`.

#### Block 12: the 404

```python
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )
```

- `if expense is None:` - `db.scalar` returned nothing. `is None` is the correct
  way to test for "no value" (not `== None`).
- `raise` - stop the function right here and throw an exception.
- `HTTPException(...)` - FastAPI catches this and turns it into an HTTP error
  response.
- `status_code=status.HTTP_404_NOT_FOUND` - the number 404.
- `detail="Expense not found"` - becomes the JSON body `{"detail": "Expense not found"}`.

Note that the message is the same whether the expense does not exist at all or
belongs to another user. That is on purpose: the API never confirms "this id
exists but is not yours".

**Why it is here**: the caller (the endpoint) can then assume it always has a
real, owned `Expense`, with no extra checks.

**If you removed or changed it**: `expense` could be `None`, and the endpoint would
later crash with `AttributeError: 'NoneType' object has no attribute ...` -
which FastAPI reports as a 500 Internal Server Error. The client would get a
server error instead of a clear 404.

#### Block 13: the return

```python
    return expense
```

- `return expense` - hand the found `Expense` object back to whoever called the
  helper.

**Why it is here**: the helper's whole point is to give the endpoint the object.

**If you removed or changed it**: the function would return `None` (Python's
default when there is no `return`), and `get_expense` would answer... FastAPI
would try to build an `ExpenseResponse` from `None` and fail with a 500.

#### Block 14: the "Endpoints" comment banner

```python
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
```

- Comment lines, same as Block 9: "from here on, the `@router` endpoints".

**Why it is here**: readability.

**If you removed or changed it**: nothing.

#### Block 15: the create decorator

```python
@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an expense",
)
```

- `@` - a **decorator**: "take the function defined right below, and pass it to
  `router.post(...)`, which registers it as an endpoint". Same as your old
  `@router.post("/")`.
- `router.post(` ... `)` - "this endpoint answers HTTP POST". The arguments are
  spread over lines for readability.
- `""` - an empty path. With the prefix it becomes exactly `/expenses`. Your old
  code used `"/"`, which gives `/posts/`. The empty string avoids the trailing
  slash so clients can call `/api/v1/expenses` without a redirect.
- `response_model=ExpenseResponse` - FastAPI converts whatever the function
  returns (an `Expense` database object) into an `ExpenseResponse`, validates it,
  and only sends the fields listed there. The `owner_id` column, for example, is
  not in `ExpenseResponse`, so it never leaves the server.
- `status_code=status.HTTP_201_CREATED` - the success status is 201 ("Created")
  instead of the default 200. Same as in your old code.
- `summary="Add an expense"` - the short title shown in `/docs`.

**Why it is here**: registers the endpoint, states its success code, and locks
down the response shape.

**If you removed or changed it**: without the decorator, `create_expense` is
just a function nobody calls - `POST /expenses` would answer 405 Method Not
Allowed (the GET on the same path exists, the POST does not). Without
`response_model`, FastAPI would try to serialise the raw `Expense` object with
its own rules; the `-> Expense` return annotation would then be used as the
response model, and an `Expense` is not a Pydantic model, so the app would fail
to start with an error about the return type.

#### Block 16: the create function signature

```python
def create_expense(
    expense_in: ExpenseCreate, db: DatabaseSession, current_user: CurrentUser
) -> Expense:
```

- `def create_expense(` - the endpoint function.
- `expense_in: ExpenseCreate` - because `ExpenseCreate` is a Pydantic model,
  FastAPI reads the JSON **body** of the request, validates it against
  `ExpenseCreate` (title not empty, amount > 0 with at most 2 decimals, a valid
  payment method, ...) and hands the function a ready object. Bad JSON never
  reaches this line; the client gets 422 with details. The `_in` suffix is a
  naming habit: "the incoming data".
- `db: DatabaseSession` - a database session (Block 5).
- `current_user: CurrentUser` - the logged-in `User` (Block 5). If the token is
  missing or bad, FastAPI answers 401 before the body runs.
- `-> Expense` - the function returns an `Expense` database object. Because the
  decorator sets `response_model=ExpenseResponse`, FastAPI uses **that** for the
  response; the `-> Expense` note is for human readers and editors.

**Why it is here**: three inputs: what to create, where to store it, who owns it.

**If you removed or changed it**: removing `current_user` would make the endpoint
public and leave no `owner_id` to store (the database would refuse the insert
because `owner_id` is `NOT NULL`). Changing `expense_in: ExpenseCreate` to a
plain `dict` would skip all validation: a negative amount would then hit the
database and be rejected by the `CHECK (amount > 0)` constraint with a 500
instead of a clean 422.

#### Block 17: the category ownership check

```python
    if expense_in.category_id is not None:
        # Stops a user from attaching their expense to someone else's category.
        get_owned_category_or_404(db, expense_in.category_id, current_user.id)
```

- `if expense_in.category_id is not None:` - the client sent a category. (`None`
  means "uncategorized", which needs no check.)
- `# Stops a user ...` - the comment explains the purpose of the next line.
- `get_owned_category_or_404(db, expense_in.category_id, current_user.id)` - the
  helper imported in Block 6. If the category exists **and** belongs to the
  current user, it quietly returns it (the return value is ignored here - only
  the check matters). Otherwise it raises `HTTPException(404, "Category not
  found")` and the function stops.

**Why it is here**: the foreign key in the database only checks that the
category id exists somewhere. It does not know about users. This line adds the
"it must be yours" rule.

**If you removed or changed it**: `POST /expenses` with another user's
`category_id` would succeed (201). Verified against the real code: with the
check in place the response is `404 {"detail": "Category not found"}`.

#### Block 18: building the row

```python
    expense = Expense(**expense_in.model_dump(), owner_id=current_user.id)
```

- `expense =` - the new, not-yet-saved row object.
- `Expense(...)` - calling the table class creates a row object (nothing is sent
  to the database yet).
- `expense_in.model_dump()` - a Pydantic method: turn the validated model into a
  plain dictionary, for example
  `{"title": "Pizza", "amount": Decimal("250.00"), "expense_date": date(2026, 1, 5),
  "payment_method": "cash", "notes": None, "category_id": 1}`. Because
  `ExpenseCreate` has `use_enum_values=True`, `payment_method` is already the
  plain string `"cash"`, not the enum object.
- `**` (two stars, before a dictionary, inside a call) - **unpack the dictionary
  into keyword arguments**. `Expense(**{"title": "Pizza", "amount": 250})` is
  exactly `Expense(title="Pizza", amount=250)`. It saves you from typing every
  field by hand, and it automatically follows the schema if a field is added
  later.
- `,` then `owner_id=current_user.id` - one more keyword argument, added by hand,
  because the client does not (and must not) send the owner. The owner is always
  the logged-in user.

You used exactly this pattern in your old code:
`table(**post.model_dump(), owner_id=current_user.id)`.

**Why it is here**: builds the row from the validated input plus the trusted
owner id.

**If you removed or changed it**: without `**`, `Expense({...})` would fail
(`__init__() takes 1 positional argument but 2 were given`). Without
`owner_id=current_user.id`, the `INSERT` would fail on the `NOT NULL` constraint
(a 500). If `owner_id` were taken from the request body instead, a client could
create expenses "as" another user.

#### Block 19: save and return

```python
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense
```

- `db.add(expense)` - put the new object into the session's "to be saved" list.
  Still no SQL.
- `db.commit()` - send the `INSERT`, and commit the transaction so it is
  permanent. After this the database has assigned the `id`, `created_at` and
  `updated_at` values (they are generated by the database).
- `db.refresh(expense)` - run a `SELECT` for this row and copy the database
  values (`id`, `created_at`, `updated_at`, the default `payment_method` if any)
  into the Python object. Without it, after a commit SQLAlchemy marks the
  object's attributes as "expired" and would reload them lazily on first access;
  `refresh` makes the reload explicit and immediate so the response is built
  from complete data.
- `return expense` - FastAPI turns it into an `ExpenseResponse`. That schema has
  a `category` field, so FastAPI reads `expense.category`; SQLAlchemy then runs
  one small `SELECT ... FROM categories WHERE id = ?` (a lazy load) if a category
  is set.

The same four lines appear in your old `create_post`.

**Why it is here**: add -> commit -> refresh is the standard "insert one row and
return it complete" sequence.

**If you removed or changed it**: no `commit` means the `INSERT` is rolled back
when the session closes at the end of the request; the client would receive 201
but the expense would not exist. No `refresh` would still work here in practice
(SQLAlchemy reloads expired attributes on access) but makes the intent less
clear and depends on session settings.

#### Block 20: the list decorator

```python
@router.get("", response_model=ExpenseListResponse, summary="List my expenses")
```

- `@router.get("")` - HTTP GET on `/expenses` (empty path + prefix).
- `response_model=ExpenseListResponse` - the response is the page object
  `{"items": [...], "total": ..., "limit": ..., "offset": ...}`, not a bare list.
- `summary="List my expenses"` - docs title.

**Why it is here**: registers the list endpoint. Returning a page object instead
of a bare list lets the client show "page 2 of 7" without a second request.

**If you removed or changed it**: no decorator, no endpoint (GET `/expenses` -> 404
Not Found from the router). With `response_model=list[ExpenseResponse]` the
function's return value (an `ExpenseListResponse`) would not match and FastAPI
would answer 500.

#### Block 21: the list function and its dependencies

```python
def list_expenses(
    db: DatabaseSession,
    current_user: CurrentUser,
    date_range: DateRangeFilter,
```

- `def list_expenses(` - the endpoint function. Its parameters continue for
  several blocks; FastAPI reads each one and decides where it comes from
  (dependency, query string, body) by its type.
- `db: DatabaseSession` - database session.
- `current_user: CurrentUser` - logged-in user (401 if not logged in).
- `date_range: DateRangeFilter` - the shared `?start_date=&end_date=` filter.
  FastAPI runs `get_date_range`, which declares those two query parameters, and
  gives this function a `DateRange` object. So although you do not see
  `start_date` here, the endpoint **does** accept `?start_date=2026-01-01`; the
  docs page lists both. If start is after end, the dependency answers
  `422 {"detail": "start_date must be on or before end_date"}` before this
  function body runs (verified).

**Why it is here**: the date range is used by expenses **and** by every report, so
it lives in one dependency instead of being copied into four functions.

**If you removed or changed it**: without `date_range`, the two `if
date_range...` lines in Block 28 would fail with `NameError`, and the endpoint
would lose date filtering.

#### Block 22: the `category_id` query parameter (and what `Annotated` + `Query` mean)

```python
    category_id: Annotated[
        int | None, Query(description="Only expenses in this category")
    ] = None,
```

Read this block slowly; the next four blocks use the same pattern.

- `category_id` - the parameter name. Because its type is a simple value (not a
  Pydantic model, not a dependency), FastAPI takes it from the **query string**:
  `GET /expenses?category_id=3`.
- `:` - "its type is...".
- `Annotated[` ... `]` - from `typing` (Block 2). The square brackets hold a
  comma-separated list. The **first** item is the real type. Everything **after**
  the first comma is extra information ("metadata") attached to that type.
- `int | None` - the real type. The vertical bar `|` means **"or"** in a type
  hint (Python 3.10+). So: "an `int`, or `None`". It is the modern spelling of
  `Optional[int]`, which you used in your old code.
- `,` - separates the type from the metadata.
- `Query(description="Only expenses in this category")` - from `fastapi`
  (Block 3). It creates an object that says "this is a query parameter, and here
  is extra information about it". `description=` is the text shown next to the
  parameter in `/docs`. It has no effect on validation.
- `] = None` - the **default value**. Because there is a default, the parameter
  is optional: leave `?category_id=` out of the URL and the function gets `None`.

So the full line reads: "`category_id` is an optional query parameter; it is an
integer or nothing; default nothing; here is its description".

How FastAPI uses it: it reads the string `"3"` from the URL, converts it to the
integer `3` (because the type says `int`), and passes it in. If the client
sends `?category_id=abc`, FastAPI answers (verified):

```json
{"detail": [{"type": "int_parsing", "loc": ["query", "category_id"],
             "msg": "Input should be a valid integer, unable to parse string as an integer",
             "input": "abc"}]}
```

with status 422, and the function body never runs.

Why `Annotated[int | None, Query(...)] = None` instead of the older
`category_id: Optional[int] = Query(None, description=...)`: both work in
FastAPI. The `Annotated` style keeps the **default** in the normal Python
place (after `=`) and the **metadata** with the type, which is what the FastAPI
documentation now recommends. It also means that if you call `list_expenses`
directly from Python (for example in a test) the default really is `None`,
not a `Query` object.

**Why it is here**: lets the client narrow the list to one category.

**If you removed or changed it**: no category filter. If you wrote `int` without
`| None` and without `= None`, the parameter would become **required** and every
request without `?category_id=` would get 422 "Field required".

#### Block 23: the `payment_method` query parameter

```python
    payment_method: Annotated[
        PaymentMethod | None, Query(description="Only expenses paid this way")
    ] = None,
```

- `payment_method` - optional query parameter `?payment_method=upi`.
- `PaymentMethod | None` - the type is the enum from `app/models/expense.py`, or
  nothing. An `enum` is a class whose only allowed values are a fixed list;
  `PaymentMethod` has `CASH = "cash"`, `CARD = "card"`, `UPI = "upi"`,
  `BANK_TRANSFER = "bank_transfer"`, `OTHER = "other"`.
- `Query(description=...)` - docs text.
- `= None` - optional.

FastAPI validates the string against the enum. `?payment_method=upi` gives the
function the member `PaymentMethod.UPI`. `?payment_method=bitcoin` gives 422
(verified):

```json
{"type": "enum", "loc": ["query", "payment_method"],
 "msg": "Input should be 'cash', 'card', 'upi', 'bank_transfer' or 'other'",
 "input": "bitcoin"}
```

The `/docs` page shows a dropdown with the five values, because FastAPI
generates the list from the enum.

**Why it is here**: filter by how the expense was paid, with the valid list
enforced for free.

**If you removed or changed it**: with type `str` instead of `PaymentMethod`,
`?payment_method=bitcoin` would be accepted, match nothing, and return an empty
page - a silent mistake instead of a clear 422.

#### Block 24: the `min_amount` and `max_amount` query parameters

```python
    min_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    max_amount: Annotated[Decimal | None, Query(ge=0)] = None,
```

- `min_amount`, `max_amount` - optional query parameters:
  `?min_amount=100&max_amount=500`.
- `Decimal | None` - the type is an exact decimal number (Block 2) or nothing.
  FastAPI turns the string `"100.50"` into `Decimal("100.50")`.
- `Query(ge=0)` - `ge` stands for **"greater than or equal"**. The value must be
  `>= 0`. There are four such keywords: `gt` (greater than), `ge`, `lt` (less
  than), `le` (less than or equal).
- `= None` - optional.

Verified behaviour: `?min_amount=-5` answers 422 with
`"msg": "Input should be greater than or equal to 0"`; `?min_amount=abc` answers
422 with `"type": "decimal_parsing", "msg": "Input should be a valid decimal"`.

Note that nothing checks `min_amount <= max_amount`. If a client sends
`?min_amount=500&max_amount=100` the result is simply an empty page. That is a
harmless, honest answer, so no extra rule was added.

**Why it is here**: price-range filtering, with negative values rejected up
front (a negative amount can never exist, see the `CHECK (amount > 0)` in the
model).

**If you removed or changed it**: without `ge=0`, a negative filter would be
accepted and just match everything (`amount >= -5`) - not dangerous, only
sloppy. With `float` instead of `Decimal`, the value would be an inexact binary
number compared against an exact `NUMERIC` column.

#### Block 25: the `search` query parameter

```python
    search: Annotated[
        str | None,
        Query(max_length=150, description="Text to look for in the title (case-insensitive)"),
    ] = None,
```

- `search` - optional query parameter `?search=pizza`.
- `str | None` - text or nothing.
- `Query(max_length=150, ...)` - `max_length` limits the string length. 150 is
  chosen because the `title` column is `String(150)`: a search text longer than
  any possible title can never match, so rejecting it is fair. Verified: 151
  characters answer 422 `"String should have at most 150 characters"`.
- `description=...` - docs text; it promises case-insensitive matching, which
  Block 31 delivers.
- `= None` - optional.

**Why it is here**: lets the client find expenses by part of the title.

**If you removed or changed it**: without `max_length`, a client could send a
megabyte-long search string that the database would have to compare against
every row. Not a security hole, but a free way to slow the server.

#### Block 26: `limit`, `offset`, and the return type

```python
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many expenses to skip")] = 0,
) -> ExpenseListResponse:
```

- `limit` - how many expenses to return at most (the page size).
- `Annotated[int, Query(ge=1, le=100, ...)]` - an integer between 1 and 100
  inclusive. `le` = "less than or equal". Note there is no `| None` here: the
  parameter always has a value.
- `= 20` - default page size when the client does not say.
- `offset` - how many matching expenses to **skip** before starting the page.
  Page 1 is `offset=0`, page 2 is `offset=20` (with `limit=20`), page 3 is
  `offset=40`, and so on.
- `Query(ge=0, ...)` - cannot be negative.
- `= 0` - default: start from the first one.
- `) -> ExpenseListResponse:` - the end of the parameter list, and the return
  type: the function returns the page object itself (this time the function
  builds the Pydantic model by hand, Block 36).

Verified: `?limit=0` -> 422 "Input should be greater than or equal to 1";
`?limit=101` -> 422 "Input should be less than or equal to 100";
`?offset=-1` -> 422 "Input should be greater than or equal to 0".

**Why it is here**: paging is what keeps the endpoint fast and the response
small when a user has thousands of expenses. The cap of 100 stops a client from
asking for everything in one go.

**If you removed or changed it**: without `le=100`, `?limit=1000000` would make
the database load and the server serialise every row. Without `ge=1`,
`?limit=0` would return an empty page with a non-zero `total`, which confuses
clients. Your old code had `limit: int = 10, skip: int = 3` with no rules at
all, and - a real bug - a default `skip` of 3, so the first three posts were
always hidden by default.

#### Block 27: starting the filters list

```python
    # Build the WHERE conditions once; they are shared by the count query
    # and the page query below.
    filters = [Expense.owner_id == current_user.id]
```

- `# Build the WHERE conditions once ...` - the comment explains the plan: the
  endpoint needs **two** queries (one to count all matches, one to fetch the
  page), and both must use exactly the same `WHERE`. So the conditions are
  collected in a list first.
- `filters =` - a plain Python list variable.
- `[` ... `]` - a list with one element to start.
- `Expense.owner_id == current_user.id` - a SQLAlchemy condition object (Block
  11): `expenses.owner_id = <my id>`. It is the one filter that is **always**
  present. Everything else is optional.

This is "the filters list pattern": start with the mandatory condition, append
optional ones, and pass the whole list to `.where()` at the end.

**Why it is here**: one list, used twice, guarantees that `total` really counts
the same rows the page is taken from.

**If you removed or changed it**: starting with an empty list `[]` would, when
no filter is given, produce a `WHERE` with nothing in it - i.e. **all users'
expenses**. This single line is the privacy rule of the endpoint.

#### Block 28: the date filters

```python
    if date_range.start_date is not None:
        filters.append(Expense.expense_date >= date_range.start_date)
    if date_range.end_date is not None:
        filters.append(Expense.expense_date <= date_range.end_date)
```

- `if date_range.start_date is not None:` - the client gave `?start_date=`.
- `filters.append(...)` - add one more condition to the list.
- `Expense.expense_date >= date_range.start_date` - SQL fragment
  `expenses.expense_date >= :start_date`. `>=` means the start day itself is
  included.
- The `end_date` pair works the same with `<=`, so the end day is included too.

**Why it is here**: "expenses between two dates" is the most common question for
an expense tracker. Both ends are inclusive, which is what people expect from
"from 1 Jan to 31 Jan".

**If you removed or changed it**: no date filtering. If you used `<` instead of
`<=` for the end, `?end_date=2026-01-31` would silently drop everything spent on
31 January.

#### Block 29: category and payment-method filters

```python
    if category_id is not None:
        filters.append(Expense.category_id == category_id)
    if payment_method is not None:
        filters.append(Expense.payment_method == payment_method.value)
```

- `if category_id is not None:` -> append `expenses.category_id = :category_id`.
  Note there is **no** ownership check on `category_id` here. It is not needed:
  the `owner_id` filter is already in the list, so asking for someone else's
  category just yields an empty page. (For *writing* an expense, Block 17 does
  check.)
- `if payment_method is not None:` - the client sent a valid enum member.
- `payment_method.value` - `.value` turns the enum member `PaymentMethod.UPI`
  into its underlying string `"upi"`. The column stores plain text (`String(20)`),
  so the comparison is made with the plain string. Verified SQL:
  `WHERE expenses.payment_method = 'upi'`.

**Why it is here**: two of the optional filters.

**If you removed or changed it**: comparing with `payment_method` (the member)
instead of `payment_method.value` would also work in practice, because
`PaymentMethod` inherits from `str` (`class PaymentMethod(str, enum.Enum)`), so
SQLAlchemy would send the same `"upi"`. Using `.value` just makes it explicit
and does not depend on that detail.

#### Block 30: amount filters

```python
    if min_amount is not None:
        filters.append(Expense.amount >= min_amount)
    if max_amount is not None:
        filters.append(Expense.amount <= max_amount)
```

- `Expense.amount >= min_amount` -> `expenses.amount >= :min_amount`.
- `Expense.amount <= max_amount` -> `expenses.amount <= :max_amount`.
- `is not None` is used, not `if min_amount:`, on purpose: `Decimal("0")` is
  "falsy" in Python, so `if min_amount:` would wrongly ignore `?min_amount=0`.
  With `is not None` a zero works as a real filter.

**Why it is here**: the price range filter.

**If you removed or changed it**: no amount filtering. Using `if min_amount:`
would quietly drop a `0` filter (harmless here, since `0` matches everything,
but the `is not None` habit matters elsewhere).

#### Block 31: the text search, and `icontains(autoescape=True)`

```python
    if search:
        # autoescape=True treats % and _ typed by the user as normal characters.
        filters.append(Expense.title.icontains(search, autoescape=True))
```

- `if search:` - here `if search:` (not `is not None`) is intentional: an empty
  string `?search=` should mean "no search", and `""` is falsy. Verified: an
  empty search returns the full list.
- `# autoescape=True ...` - the comment explains the keyword on the next line.
- `Expense.title.icontains(search, autoescape=True)` - a SQLAlchemy column
  operator. `contains(x)` builds `column LIKE '%' || x || '%'` ("x appears
  anywhere inside"). The leading `i` means **insensitive** (case-insensitive).
  SQLAlchemy's own documentation says it produces
  `lower(column) LIKE '%' || lower(<other>) || '%'`.
- `autoescape=True` - in SQL `LIKE`, two characters are special: `%` means "any
  characters" and `_` means "any one character". If the user types `100%`
  (for example, searching a title like "Flat rent 100%"), without escaping the
  `%` would be treated as a wildcard and would match any title containing
  "100" followed by anything. `autoescape=True` tells SQLAlchemy to put an
  escape character (`/`) in front of every `%`, `_` and `/` in the user's text
  and to add `ESCAPE '/'` to the SQL, so those characters match **themselves**.

Real SQL captured from the code, for `search = "100%"`:

On PostgreSQL (the real database; `ILIKE` is PostgreSQL's built-in
case-insensitive LIKE, so no `lower()` is needed):

```sql
WHERE (expenses.title ILIKE '%' || $1 || '%' ESCAPE '/')   -- $1 = '100/%'
```

On SQLite (used by the tests):

```sql
WHERE (lower(expenses.title) LIKE '%' || lower('100/%') || '%' ESCAPE '/')
```

Notice the parameter value is `100/%`: the `%` the user typed has been escaped.
Without `autoescape=True` the SQL would be `... LIKE '%' || lower('100%') || '%'`
and `100%` would behave like `100` followed by anything.

Verified: `?search=PIZ` finds "Pizza" (case-insensitive), and `?search=100%`
finds "Flat rent 100%".

**Why it is here**: lets users search titles the way they expect: any case,
any position, and with `%`/`_` taken literally.

**If you removed or changed it**: `Expense.title.contains(search)` (your old
code) would be case-sensitive (`?search=pizza` would not find "Pizza") and
would treat `%` and `_` as wildcards. `Expense.title == search` would require
the exact full title.

#### Block 32: the count query, and what `*filters` does

```python
    total = db.scalar(select(func.count()).select_from(Expense).where(*filters))
```

- `total =` - the number of expenses that match the filters across **all** pages.
- `db.scalar(...)` - run the query and return the single value (Block 11). Here
  the single value is an `int` (verified: `type(...)` is `int`).
- `select(func.count())` - `func.count()` with **no arguments** is the SQL
  `count(*)`: "how many rows". (SQLAlchemy's own docstring: "With no arguments,
  emits COUNT *".) `select(...)` of it is `SELECT count(*)`.
- `.select_from(Expense)` - because `select(func.count())` names no table,
  SQLAlchemy does not know what to count. `.select_from(Expense)` adds
  `FROM expenses`. (When you `select(Expense)`, the `FROM` is figured out from
  the columns; with a bare function it is not.)
- `.where(*filters)` - `.where()` wants its conditions as separate arguments:
  `.where(cond1, cond2, cond3)`. We have them in a **list**. The single star `*`
  in front of a list, inside a call, **unpacks the list into separate
  arguments**. So `.where(*[a, b, c])` is exactly `.where(a, b, c)`.
  Verified with a tiny function: `f([1, 2, 3])` receives one argument (the list),
  `f(*[1, 2, 3])` receives three arguments `1, 2, 3`. Without the star you would
  be passing one argument - a Python list - and SQLAlchemy would raise an error
  because a list is not a SQL condition.

The SQL that runs (for a user with id 1 and `?min_amount=100`):

```sql
SELECT count(*) AS count_1
FROM expenses
WHERE expenses.owner_id = 1 AND expenses.amount >= 100
```

**Why it is here**: the response's `total` lets the client compute the number of
pages (`ceil(total / limit)`) and show "showing 21-40 of 137".

**If you removed or changed it**: no `total`, so `ExpenseListResponse(...)` in
Block 36 would fail validation (`total` is required). If you used
`len(expenses)` instead, you would get the size of the **current page** (at most
`limit`), not the real total. Your old code had no count at all.

#### Block 33: the page query begins, with `selectinload` and the N+1 problem

```python
    expenses = db.scalars(
        select(Expense)
        # Load all categories for the page in one extra query (avoids N+1).
        .options(selectinload(Expense.category))
```

- `expenses =` - the list of `Expense` objects for this page.
- `db.scalars(...)` - like `db.scalar` but for **many** rows: run the statement
  and give back the first column of **every** row. With `select(Expense)` the
  first column is the whole object, so you get `Expense` objects. It returns a
  `ScalarResult`; `.all()` (Block 35) turns it into a plain list.
- `select(Expense)` - `SELECT ... FROM expenses`.
- `# Load all categories ...` - the comment names the problem being avoided.
- `.options(...)` - attach **loader options** to the statement: instructions about
  *how* to load related objects, not *which* rows.
- `selectinload(Expense.category)` - "after loading the expenses, load their
  `category` relationship using one `SELECT ... WHERE categories.id IN (...)`".

**The N+1 problem, concretely.** The response schema `ExpenseResponse` has a
`category` field. For each expense, FastAPI reads `expense.category`. By
default, SQLAlchemy loads a relationship **lazily**: the first time you touch
`expense.category`, it runs `SELECT ... FROM categories WHERE id = ?` for that
one expense. For a page of 20 expenses with 20 different categories that is
1 query for the page + 20 small queries = **21 queries** ("N + 1"). With 100
expenses, 101 queries. Each query is a network round trip to PostgreSQL, so the
endpoint gets slower in proportion to the page size.

With `selectinload`, SQLAlchemy collects the `category_id` values of the loaded
page and runs **one** extra query. Captured from a real run with a page of
expenses whose categories have ids 1 and 2:

```sql
-- query 1: the page
SELECT expenses.id, expenses.title, ... FROM expenses
WHERE expenses.owner_id = ? ORDER BY expenses.expense_date DESC, expenses.id DESC
LIMIT ? OFFSET ?
-- query 2: all categories of that page, at once
SELECT categories.id, categories.name, ... FROM categories
WHERE categories.id IN (?, ?)
```

Always exactly 2 queries, no matter the page size. The same run **without**
`selectinload` showed a separate `SELECT ... FROM categories WHERE categories.id = ?`
for each distinct category as it was touched. (SQLAlchemy remembers a category
once it has loaded it in the same session, so repeated categories do not repeat
the query - but you cannot count on that, and in the worst case it is one query
per expense.)

The name: "select **in** load" = load with a `SELECT ... IN (...)`.

**Why it is here**: makes the list endpoint cost two queries instead of up to
`limit + 1`.

**If you removed or changed it**: the endpoint would still return the correct
data, just slower, with one extra query per distinct category on the page. The
tests would pass; only the database log (and the response time under load)
would show the difference. This is the most common performance mistake in ORM
code, which is why the comment points it out.

#### Block 34: the WHERE and ORDER BY

```python
        .where(*filters)
        # Newest first; id breaks ties so pages never overlap.
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
```

- `.where(*filters)` - the **same** list, unpacked the same way (Block 32). This is
  what guarantees the page and the count agree.
- `# Newest first; id breaks ties ...` - the comment explains the two-column
  ordering.
- `.order_by(...)` - adds `ORDER BY`. It accepts several columns; the second is
  used only when two rows are equal on the first.
- `Expense.expense_date.desc()` - `expenses.expense_date DESC`: newest date
  first. `.desc()` means descending (big to small). The default, or `.asc()`,
  is ascending.
- `,` `Expense.id.desc()` - `expenses.id DESC`: among expenses on the **same
  day**, the one inserted last (higher id) comes first.

Why two columns matter for paging: `LIMIT`/`OFFSET` paging only works if the
order is **stable** - every run must put the rows in the same sequence. If you
order by `expense_date` alone and ten expenses share the same date, the
database is free to return those ten in any order it likes, and it may return
them in a *different* order on the next query. Then page 1 could show expense
A at position 20 and page 2 could show the same A again at position 21, while
another expense never appears at all. Adding `id` (which is unique) makes the
order total, so pages never overlap and never skip.

Produced SQL: `ORDER BY expenses.expense_date DESC, expenses.id DESC`.

**Why it is here**: newest-first is what a user expects to see; the `id`
tie-break makes paging reliable.

**If you removed or changed it**: no `ORDER BY` at all would make paging
meaningless (the database's row order is not guaranteed). Only
`expense_date.desc()` would cause the overlapping/skipping described above on
days with several expenses.

#### Block 35: LIMIT, OFFSET and `.all()`

```python
        .limit(limit)
        .offset(offset)
    ).all()
```

- `.limit(limit)` - `LIMIT <limit>`: return at most this many rows (the page
  size, 1-100, default 20).
- `.offset(offset)` - `OFFSET <offset>`: skip this many rows first. The database
  still has to walk past the skipped rows, which is why very large offsets are
  slower; for an expense tracker that is fine.
- `)` - closes `db.scalars(`.
- `.all()` - turn the `ScalarResult` into a Python **list** of `Expense` objects
  (verified: `type(...)` is `list`). Until `.all()`, the result is an iterator you
  could loop over once.

Full SQL for `?limit=2&offset=1` (verified):

```sql
SELECT expenses.id, expenses.title, ... FROM expenses
WHERE expenses.owner_id = 1
ORDER BY expenses.expense_date DESC, expenses.id DESC
LIMIT 2 OFFSET 1
```

and the response then contains the 2nd and 3rd newest expenses with
`"total": 3, "limit": 2, "offset": 1`.

**Why it is here**: the actual paging. The parameters are already validated, so
no checks are needed here.

**If you removed or changed it**: without `.limit()` the endpoint would return
every matching row regardless of `limit`. Without `.all()` you would pass a
`ScalarResult` to `ExpenseListResponse(items=...)`; Pydantic needs a list there
and would raise a validation error (500).

#### Block 36: building the page response

```python
    return ExpenseListResponse(items=expenses, total=total, limit=limit, offset=offset)
```

- `return` - the endpoint's answer.
- `ExpenseListResponse(...)` - build the response Pydantic model **in Python**
  (not left to FastAPI), because the data comes from two queries and two
  parameters, not from one object.
- `items=expenses` - the list of `Expense` **database objects**. `ExpenseListResponse`
  declares `items: list[ExpenseResponse]`, and `ExpenseResponse` has
  `from_attributes=True`, so Pydantic reads each object's attributes
  (`.id`, `.title`, `.category`, ...) and builds `ExpenseResponse` objects.
  Verified: the JSON shows nested `"category": {"id": 1, "name": "Food"}` or
  `"category": null`.
- `total=total` - from Block 32.
- `limit=limit`, `offset=offset` - echoed back so the client knows which page it
  got (useful when it relied on defaults).

**Why it is here**: one object that tells the client everything it needs to
render a paged list.

**If you removed or changed it**: returning `expenses` (a bare list) would not
match `response_model=ExpenseListResponse` and give a 500. Leaving out `total`
gives a Pydantic validation error ("Field required").

#### Block 37: get one expense

```python
@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Get one expense")
def get_expense(
    expense_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Expense:
    return get_owned_expense_or_404(db, expense_id, current_user.id)
```

- `@router.get("/{expense_id}", ...)` - GET on `/expenses/<number>`. The curly
  braces `{expense_id}` declare a **path parameter**: the part of the URL in that
  position is captured and passed to the function under that name.
- `response_model=ExpenseResponse` - one expense in the response.
- `summary="Get one expense"` - docs title.
- `def get_expense(` - the function.
- `expense_id: int` - the captured path piece, converted to `int`. The name must
  match the `{expense_id}` in the path exactly. `/expenses/abc` is rejected with
  422 before the function runs.
- `db: DatabaseSession`, `current_user: CurrentUser` - as before.
- `-> Expense` - returns the database object; FastAPI shapes it with the
  response model.
- `return get_owned_expense_or_404(db, expense_id, current_user.id)` - the
  helper from Block 10 does everything: load, ownership check, 404. The endpoint
  is one line.

Verified: another user's expense and a non-existent id both answer
`404 {"detail": "Expense not found"}`.

**Why it is here**: the "read one" endpoint; the helper does the work.

**If you removed or changed it**: no single-expense endpoint. Note the order of
routes does not matter here: `""` and `"/{expense_id}"` cannot collide, because
one has a path segment after `/expenses` and the other does not.

#### Block 38: the update decorator and signature

```python
@router.patch("/{expense_id}", response_model=ExpenseResponse, summary="Update an expense")
def update_expense(
    expense_id: int,
    expense_in: ExpenseUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Expense:
```

- `@router.patch(...)` - HTTP **PATCH**, which by convention means "change
  *some* fields". Your old code used **PUT**, which means "replace the whole
  thing"; PATCH matches what this endpoint actually does.
- `"/{expense_id}"` - path parameter, as in Block 37.
- `response_model=ExpenseResponse` - the updated expense is returned in full.
- `expense_id: int` - from the path.
- `expense_in: ExpenseUpdate` - the JSON body, validated against `ExpenseUpdate`,
  where **every field is optional**. The schema also has a rule (document 07)
  that `title`, `amount`, `expense_date` and `payment_method` may be left out
  but may **not** be sent as `null`, because those columns are `NOT NULL`.
  Verified: `{"title": null}` answers 422 `"Value error, title cannot be null"`.
- `db`, `current_user`, `-> Expense` - as before.

**Why it is here**: lets a client fix one field (for example only the amount)
without resending everything.

**If you removed or changed it**: with `ExpenseCreate` as the body type, a
client could not send `{"amount": "300"}` alone - 422 "Field required" for
`title`.

#### Block 39: load the expense

```python
    expense = get_owned_expense_or_404(db, expense_id, current_user.id)
```

- The same helper (Block 10). After this line, `expense` is guaranteed to be the
  current user's expense; otherwise the request already ended with 404.

**Why it is here**: ownership check before any change.

**If you removed or changed it**: without it there would be no object to change
(and no check). Fetching by id only would let a user modify another user's
expense.

#### Block 40: collect only the fields that were sent

```python
    # exclude_unset=True -> only the fields the client actually sent.
    changes = expense_in.model_dump(exclude_unset=True)
```

- `# exclude_unset=True -> ...` - the comment explains the keyword.
- `changes =` - a dictionary of what to update.
- `expense_in.model_dump(...)` - Pydantic: model to dictionary (Block 18).
- `exclude_unset=True` - **leave out every field the client did not send**.
  Pydantic remembers which fields were present in the JSON (it keeps the set in
  `model_fields_set`). Without this keyword, `model_dump()` would include every
  field with its default `None`, and the loop in Block 42 would then set
  `title = None`, `amount = None`, and so on - wiping the row.

Example: body `{"amount": "300"}` gives `changes == {"amount": Decimal("300")}`,
nothing else. Body `{"category_id": null}` gives `changes == {"category_id": None}`
- the client **did** send it, so it is kept, and the category is removed
(verified: the response shows `"category": null`).

That is the difference between "not sent" and "sent as null", and
`exclude_unset` is what lets the code tell them apart.

**Why it is here**: this is what makes PATCH a *partial* update.

**If you removed or changed it**: `model_dump()` without `exclude_unset=True`
would set every unsent field to `None`. For `title` and `amount` that violates
`NOT NULL` and the commit would fail (500); for `notes` and `category_id` it
would silently erase them. This is the classic PATCH bug.

#### Block 41: validate a new category

```python
    if changes.get("category_id") is not None:
        get_owned_category_or_404(db, changes["category_id"], current_user.id)
```

- `changes.get("category_id")` - dictionary `.get()` returns the value for the
  key, or `None` if the key is missing. So the condition is true only when the
  client sent a **real** category id (not missing, not `null`).
- `is not None` - see above.
- `get_owned_category_or_404(db, changes["category_id"], current_user.id)` -
  the same ownership check as in Block 17. `changes["category_id"]` (square
  brackets) is safe here because we just confirmed the key exists.

Verified: PATCH with another user's `category_id` answers
`404 {"detail": "Category not found"}`; PATCH with `"category_id": null` is
allowed and clears the category.

**Why it is here**: the same "only your own categories" rule, for updates.

**If you removed or changed it**: a user could move their expense into someone
else's category. Writing `if "category_id" in changes:` would also run the
check for `null`, and `get_owned_category_or_404(db, None, ...)` would answer
404 - so clearing the category would become impossible.

#### Block 42: apply the changes

```python
    for field_name, value in changes.items():
        setattr(expense, field_name, value)
```

- `for ... in ...:` - a loop.
- `changes.items()` - gives the dictionary's pairs, one `(key, value)` at a time.
- `field_name, value` - each pair is unpacked into two names: the column name
  (a string like `"amount"`) and the new value.
- `setattr(expense, field_name, value)` - a built-in Python function: "set the
  attribute whose **name is in this string**". `setattr(expense, "amount", 300)`
  does the same thing as `expense.amount = 300`. You need `setattr` because the
  attribute name is only known at run time (it is a string in a variable). As
  each attribute is set, SQLAlchemy notes that the object is "dirty" (changed).

**Why it is here**: applies exactly the sent fields, however many there are,
with no `if "title" in changes: expense.title = ...` repeated per field.

**If you removed or changed it**: nothing would change in the database; the
endpoint would return the old values. Your old code used
`query.update(data, synchronize_session=False)`, which issues an `UPDATE`
directly and bypasses the Python objects; `setattr` keeps the object in sync and
lets SQLAlchemy build the `UPDATE` only for the columns that changed.

#### Block 43: save and return the updated row

```python
    db.commit()
    db.refresh(expense)
    return expense
```

- `db.commit()` - SQLAlchemy builds an `UPDATE expenses SET amount = ? ... WHERE
  expenses.id = ?` for the changed columns and commits. The database also sets
  `updated_at = now()` because of `onupdate=func.now()` in the model.
- `db.refresh(expense)` - reload the row so `updated_at` (set by the database)
  is fresh in the object.
- `return expense` - serialised as `ExpenseResponse`.

Note there is no `db.add(expense)` here: the object came from a query in this
same session, so the session already tracks it.

**Why it is here**: persist and return the complete, current row.

**If you removed or changed it**: without `commit` the changes are discarded at
the end of the request. Without `refresh`, `updated_at` in the response could be
the old value, because it is computed by the database, not by Python.

#### Block 44: the delete decorator

```python
@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
)
```

- `@router.delete(` - HTTP DELETE.
- `"/{expense_id}"` - which expense.
- `status_code=status.HTTP_204_NO_CONTENT` - the success status is **204**,
  which by HTTP rules means "done, and there is deliberately **no body**".
- `summary="Delete an expense"` - docs title.
- No `response_model` - there is nothing to describe, since there is no body.

**Why it is here**: 204 is the standard reply for a successful delete.

**If you removed or changed it**: with the default 200 and a JSON body like your
old `{"message": "Post Deleted Successfully", "status code": 204}` the real
status would be 200 while the body *claims* 204 - a contradiction clients cannot
rely on.

#### Block 45: the delete signature

```python
def delete_expense(
    expense_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Response:
```

- `def delete_expense(` - the function.
- `expense_id: int`, `db`, `current_user` - as before.
- `-> Response` - this endpoint returns a raw `Response` object (Block 3), not a
  database object, because there is no body to shape.

**Why it is here**: the same three inputs as "get one".

**If you removed or changed it**: without `current_user` anyone could delete by
id, and the helper would have no `owner_id` to check.

#### Block 46: delete and answer 204

```python
    expense = get_owned_expense_or_404(db, expense_id, current_user.id)
    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- `expense = get_owned_expense_or_404(...)` - load and check ownership (404
  otherwise).
- `db.delete(expense)` - mark the object for deletion; SQLAlchemy will issue
  `DELETE FROM expenses WHERE expenses.id = ?` at the next flush.
- `db.commit()` - run the `DELETE` and commit.
- `return Response(status_code=status.HTTP_204_NO_CONTENT)` - an explicit empty
  response with status 204. Returning `None` would also produce a 204 in modern
  FastAPI, but an explicit `Response` makes the intent clear and is guaranteed
  to send no body.

Verified: first `DELETE /expenses/2` answers 204 with an empty body; a second
`DELETE /expenses/2` answers 404.

**Why it is here**: delete exactly one owned row and say "done".

**If you removed or changed it**: without `commit` the row would come back after
the request. If you returned a dictionary, FastAPI would try to send a JSON body
with a 204 status, which HTTP forbids (recent FastAPI versions raise an error
for a 204 with a body).

### Compared to your old code

Your old `app/routers/post.py` is the closest match. Here are the parts side by
side, with what changed and why. The old code was a fine learning project; the
notes below are about what the new version does differently, not about blame.

**1. The list endpoint**

Old:

```python
@router.get("/",response_model=List[Post])
def get_post(db: Session = Depends(get_db), current_user: int = Depends(get_current_user), limit : int = 10 , skip : int = 3, search : Optional[str] = ""):
    posts = db.query(table).filter(table.title.contains(search)).limit(limit).offset(skip).all()
    if  len(posts) == 0:
        raise HTTPException(status_code=status.HTTP_200_OK ,detail=f"No posts found")
    return  posts
```

New: Blocks 20-36.

- **Ownership.** The old filter is only `table.title.contains(search)`; there is
  no `owner_id` condition, so every logged-in user saw every user's posts. (The
  commented-out line above it shows you were thinking about it.) The new code
  starts `filters` with `Expense.owner_id == current_user.id` and nothing can
  remove it.
- **`skip: int = 3`.** The default offset was 3, so by default the three newest
  posts were never shown. The new default is `offset=0`.
- **No validation on `limit`/`skip`.** `?limit=-1` or `?limit=999999` were
  accepted. The new code uses `Query(ge=1, le=100)` and `Query(ge=0)`.
- **Empty list as an error.** Raising `HTTPException` with status **200** for
  "no posts" is contradictory (an exception that means success) and the body
  became `{"detail": "No posts found"}` instead of a list, so a client expecting
  `List[Post]` would break. The new code simply returns `items: []` with
  `total: 0` - an empty page is a normal result.
- **Search.** `.contains(search)` was case-sensitive and treated `%`/`_` as
  wildcards. New: `.icontains(search, autoescape=True)` (Block 31).
- **Ordering.** The old query had no `ORDER BY`, so the order of posts (and
  therefore what `limit`/`skip` returned) was not guaranteed. New: Block 34.
- **No total.** The old client could not know how many pages existed. New:
  Block 32 and the `ExpenseListResponse` page object.
- **Filters.** The new endpoint adds date range, category, payment method and
  amount range filters, all optional, all validated.
- **`current_user: int`.** The type hint said `int`, but `get_current_user`
  returned a `User` object (the code then used `current_user.id`). The new
  alias `CurrentUser` carries the correct type, `User`.
- **Style.** `db.query(...).filter(...)` is the SQLAlchemy 1.x style; the new
  code uses `select(...).where(...)` with `db.scalars(...)`. Both work in
  SQLAlchemy 2.0, but the `select()` form is the one the library documents for
  new code and is the same API used in Core (plain SQL) and ORM.

**2. Create**

Old:

```python
def create_post(post: CreatePost, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    print(current_user.password)
    new_post = table(**post.model_dump(), owner_id = current_user.id )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return {
        "message" : "Post Created Successfully",
        "data" : new_post
        }
```

New: Blocks 15-19.

- The core four lines (`table(**post.model_dump(), owner_id=...)`, add, commit,
  refresh) are **exactly the same idea**. You already had the right pattern.
- `print(current_user.password)` printed the user's hashed password to the
  server log on every request. It was debugging code, but logs are often kept
  and shared; the new code never logs secrets.
- The old response wrapped the record in `{"message": ..., "data": ...}`. The
  new API returns the record itself; the 201 status already says "created", and
  a flat object is easier for clients to use.
- New: the category ownership check (Block 17), which has no old equivalent
  because posts had no categories.

**3. Get one**

Old:

```python
@router.get("/{id}")
def get_post(id: int, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    post = db.query(table).filter(table.id == id).first()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NO POST IS FOUND")
    return {"data": post}
```

New: Blocks 10-13 and 37.

- No ownership check: any logged-in user could read any post by id. The new
  helper puts `owner_id` into the query.
- No `response_model`, so the raw object was returned wrapped in `{"data": ...}`
  and nothing stopped `owner_id` or other internal fields from leaking. The new
  endpoint uses `response_model=ExpenseResponse`.
- The function is named `get_post`, the same name as the list endpoint above
  it. Python lets the second definition replace the first in the module, and
  FastAPI had already registered the first, so it still worked - but it is
  confusing. The new functions all have distinct, descriptive names.
- The "load or 404" code is moved into a helper so it is written once for get,
  update and delete.

**4. Update**

Old:

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
    return {
        "message": "Post Updated successfully",
        "data": get_post.first()
    }
```

New: Blocks 38-43.

- You **did** check ownership here - good. But the check happened *after* the
  row was fetched, in Python, and answered **401 Unauthorized**. 401 means "you
  are not logged in", which is not the situation (the user is logged in, the
  row just is not theirs). The new code puts the owner into the `WHERE` and
  answers 404, the same as for a missing row, so the API does not reveal that
  the id exists.
- **PUT with the full `PostBase`** forced the client to resend `title`,
  `content` and `published` every time. New: PATCH with `ExpenseUpdate` and
  `exclude_unset=True` (Block 40), so one field can be changed alone.
- `get_post.update(..., synchronize_session=False)` sends an `UPDATE` directly
  and then needs a second `.first()` query to read the row back. New: `setattr`
  on the loaded object (Block 42), one `UPDATE`, one `refresh`.
- `updated_at` did not exist in the old table; the new model sets it on the
  database side.

**5. Delete**

Old:

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
    return {
                "message":"Post Deleted Successfully" ,
                "status code": status.HTTP_204_NO_CONTENT
            }

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_all(  db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    db.query(table).delete()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

New: Blocks 44-46.

- Same ownership-after-fetch pattern and 401 as in update; new code: owner in
  the query, 404.
- `delete_post == None` works but `is None` is the correct comparison for
  `None`.
- The variable `delete_post` has the same name as the function, which shadows
  it inside the body. Harmless here, but confusing.
- The response sent status **200** with a body claiming `"status code": 204`.
  New: a real 204 with no body.
- **`delete_all`** deleted **every post of every user** with one request, for
  any logged-in user. There is no equivalent in the new project, on purpose:
  there is no legitimate reason for one user to wipe the table.

**6. `get_title`** (old `GET /posts/title/{title}`, exact-title lookup) has no
new equivalent. Its job is covered by `?search=` on the list endpoint, which is
case-insensitive and matches partial titles.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `Annotated[T, X]` | a type hint `T` with extra information `X` attached; FastAPI reads `X` |
| `Query(...)` | describes one `?name=value` query parameter: default, `ge`/`le`/`max_length`, description |
| `ge`, `le`, `gt`, `lt` | greater-or-equal, less-or-equal, greater-than, less-than validation rules |
| `int \| None` | "an int or None"; the `\|` means "or" in a type hint (older spelling `Optional[int]`) |
| `Decimal` | exact decimal number from the standard library; used for all money |
| enum (`PaymentMethod`) | a class whose only allowed values are a fixed list; `.value` gives the plain string |
| path parameter | the `{expense_id}` part of a URL, captured into a function parameter |
| `select(Expense)` | starts a `SELECT ... FROM expenses` statement (SQLAlchemy 2.0 style) |
| `.where(a, b)` | adds `WHERE a AND b`; new name for `.filter` |
| `*filters` | unpacks a list into separate arguments: `f(*[a, b])` is `f(a, b)` |
| `**d` | unpacks a dictionary into keyword arguments: `f(**{"x": 1})` is `f(x=1)` |
| `db.scalar(stmt)` | run `stmt`, return the first column of the first row, or `None` |
| `db.scalars(stmt).all()` | run `stmt`, return a list of the first column of every row (here: `Expense` objects) |
| `func.count()` | the SQL `count(*)`; needs `.select_from(Expense)` to know the table |
| `.icontains(x, autoescape=True)` | case-insensitive "contains" (`LIKE '%x%'`), with `%` and `_` in `x` taken literally |
| `selectinload(Expense.category)` | load all categories of the loaded expenses in one `SELECT ... WHERE id IN (...)` |
| N+1 problem | 1 query for a list plus 1 extra query per item for a related object |
| `.order_by(a.desc(), b.desc())` | sort by `a` descending, then by `b` descending for ties |
| `.limit(n)` / `.offset(n)` | return at most `n` rows / skip the first `n` rows (paging) |
| `model_dump(exclude_unset=True)` | model to dict, leaving out fields the client did not send |
| `setattr(obj, "name", v)` | same as `obj.name = v` when the attribute name is in a string |
| `Response(status_code=204)` | an explicit empty HTTP response |

---

## File: app/routers/reports.py

### What this file is for

This file answers "where did my money go?". It has three read-only endpoints:

| Method | URL                      | Function                   | Job                                                   |
| ------ | ------------------------ | -------------------------- | ----------------------------------------------------- |
| `GET`  | `/reports/summary`       | `get_expense_summary`      | total, count, average and highest amount for a date range |
| `GET`  | `/reports/by-category`   | `get_spending_by_category` | one row per category with its total and share of the whole |
| `GET`  | `/reports/monthly`       | `get_monthly_spending`     | twelve rows, one per month of a year                  |

Nothing here writes to the database. The important design choice, stated in
the docstring: the **database** does the adding up (`SUM`, `COUNT`, `AVG`,
`MAX`, `GROUP BY`), not Python. Loading 10,000 expenses into Python just to add
them would be slow and use a lot of memory; asking PostgreSQL for one row with
the sums is fast, because that is what databases are built for.

Its place in the project:

- **It imports from**: `app.core.dependencies` (`CurrentUser`, `DatabaseSession`,
  `DateRange`, `DateRangeFilter`), `app.models.category` and `app.models.expense`
  (the two tables it reads), and `app.schemas.report` (the three response
  shapes: `ExpenseSummary`, `CategoryTotal`, `MonthlyTotal`).
- **It is imported by**: `app/main.py` only
  (`app.include_router(reports.router, prefix="/api/v1")`).

### The whole file

```python
"""
Report endpoints: read-only summaries of the logged-in user's spending.

The totals are calculated by the database (SUM / COUNT / GROUP BY), not in
Python, so they stay fast even with thousands of expenses.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import extract, func, select

from app.core.dependencies import CurrentUser, DatabaseSession, DateRange, DateRangeFilter
from app.models.category import Category
from app.models.expense import Expense
from app.schemas.report import CategoryTotal, ExpenseSummary, MonthlyTotal

router = APIRouter(prefix="/reports", tags=["Reports"])

UNCATEGORIZED_LABEL = "Uncategorized"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def to_money(value: Decimal | float | int | None) -> Decimal:
    """Round a database aggregate to 2 decimal places (None becomes 0.00)."""
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_expense_filters(owner_id: int, date_range: DateRange) -> list:
    """WHERE conditions shared by the reports: the user's expenses in the date range."""
    filters = [Expense.owner_id == owner_id]
    if date_range.start_date is not None:
        filters.append(Expense.expense_date >= date_range.start_date)
    if date_range.end_date is not None:
        filters.append(Expense.expense_date <= date_range.end_date)
    return filters


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=ExpenseSummary, summary="Overall spending totals")
def get_expense_summary(
    db: DatabaseSession, current_user: CurrentUser, date_range: DateRangeFilter
) -> ExpenseSummary:
    total_amount, expense_count, average_amount, highest_amount = db.execute(
        select(
            func.sum(Expense.amount),
            func.count(Expense.id),
            func.avg(Expense.amount),
            func.max(Expense.amount),
        ).where(*build_expense_filters(current_user.id, date_range))
    ).one()

    return ExpenseSummary(
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        total_amount=to_money(total_amount),
        expense_count=expense_count,
        average_amount=to_money(average_amount),
        highest_amount=to_money(highest_amount),
    )


@router.get(
    "/by-category",
    response_model=list[CategoryTotal],
    summary="Spending grouped by category",
)
def get_spending_by_category(
    db: DatabaseSession, current_user: CurrentUser, date_range: DateRangeFilter
) -> list[CategoryTotal]:
    """Biggest category first. Expenses without a category are grouped as "Uncategorized"."""
    total_amount = func.sum(Expense.amount)
    rows = db.execute(
        select(
            Category.id,
            Category.name,
            total_amount.label("total_amount"),
            func.count(Expense.id).label("expense_count"),
        )
        .select_from(Expense)
        # OUTER join keeps expenses whose category_id is NULL.
        .outerjoin(Category, Expense.category_id == Category.id)
        .where(*build_expense_filters(current_user.id, date_range))
        .group_by(Category.id, Category.name)
        .order_by(total_amount.desc())
    ).all()

    grand_total = sum((to_money(row.total_amount) for row in rows), Decimal("0"))

    return [
        CategoryTotal(
            category_id=row.id,
            category_name=row.name or UNCATEGORIZED_LABEL,
            total_amount=to_money(row.total_amount),
            expense_count=row.expense_count,
            percentage_of_total=round(
                float(to_money(row.total_amount) / grand_total * 100), 2
            ),
        )
        for row in rows
    ]


@router.get(
    "/monthly",
    response_model=list[MonthlyTotal],
    summary="Spending for each month of a year",
)
def get_monthly_spending(
    db: DatabaseSession,
    current_user: CurrentUser,
    year: Annotated[
        int | None,
        Query(ge=2000, le=2100, description="Defaults to the current year"),
    ] = None,
) -> list[MonthlyTotal]:
    """Always returns 12 rows (January to December) so charts need no gap-filling."""
    year = year or date.today().year
    month = extract("month", Expense.expense_date)

    rows = db.execute(
        select(
            month.label("month"),
            func.sum(Expense.amount).label("total_amount"),
            func.count(Expense.id).label("expense_count"),
        )
        .where(
            Expense.owner_id == current_user.id,
            # A date range (instead of extract(year) = ...) lets the database
            # use the (owner_id, expense_date) index.
            Expense.expense_date >= date(year, 1, 1),
            Expense.expense_date <= date(year, 12, 31),
        )
        .group_by(month)
    ).all()

    totals_by_month = {int(row.month): row for row in rows}

    monthly_totals = []
    for month_number in range(1, 13):
        row = totals_by_month.get(month_number)
        monthly_totals.append(
            MonthlyTotal(
                year=year,
                month=month_number,
                total_amount=to_money(row.total_amount if row else 0),
                expense_count=row.expense_count if row else 0,
            )
        )
    return monthly_totals
```

### Walkthrough, block by block

#### Block 1: the module docstring

```python
"""
Report endpoints: read-only summaries of the logged-in user's spending.

The totals are calculated by the database (SUM / COUNT / GROUP BY), not in
Python, so they stay fast even with thousands of expenses.
"""
```

- `"""..."""` - the module docstring (see expenses.py Block 1).
- `Report endpoints: read-only summaries ...` - what the file offers and the
  fact that nothing here changes data.
- `The totals are calculated by the database ...` - the design rule of the file
  and the reason for it (speed with large data).

**Why it is here**: explains the file's purpose and its main design decision.

**If you removed or changed it**: no effect on behaviour.

#### Block 2: standard-library imports

```python
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated
```

- `datetime` - the standard module for dates and times.
- `date` - the class for a calendar day (year, month, day; no time). Used to
  build `date(year, 1, 1)` and `date(year, 12, 31)` and to get `date.today()`.
- `decimal` - exact decimal numbers (expenses.py Block 2).
- `ROUND_HALF_UP` - a **rounding mode** constant (it is just a string,
  `"ROUND_HALF_UP"`, that `Decimal` understands). It means "when a value sits
  exactly in the middle, round **away from zero**": `2.675 -> 2.68`,
  `2.665 -> 2.67`. This is the rounding you learned in school. Python's
  **default** for `Decimal` is `ROUND_HALF_EVEN` ("banker's rounding": round a
  tie to the nearest *even* digit), which gives `2.665 -> 2.66`. Verified both.
  Money reports normally use half-up because that is what people expect.
- `Decimal` - the exact number class.
- `Annotated` - for the `year` query parameter (expenses.py Block 22).

**Why it is here**: dates for the monthly report, exact money with explicit
rounding for every amount, and a validated query parameter.

**If you removed or changed it**: `NameError` at import for any missing name.
Leaving `rounding=ROUND_HALF_UP` out of `to_money` would switch to banker's
rounding and, for example, an average of `2.665` would show as `2.66`.

#### Block 3: FastAPI and SQLAlchemy imports

```python
from fastapi import APIRouter, Query
from sqlalchemy import extract, func, select
```

- `APIRouter`, `Query` - as in expenses.py (Blocks 3 and 22). No `HTTPException`
  is imported: these endpoints never answer with an error of their own (an
  empty result is simply zeros or an empty list).
- `extract` - a SQLAlchemy function that builds the SQL `EXTRACT(field FROM
  expr)`: pull one part (year, month, day, ...) out of a date. Used as
  `extract("month", Expense.expense_date)` in Block 31.
- `func` - SQL functions: `func.sum`, `func.count`, `func.avg`, `func.max` here.
- `select` - start a `SELECT`.

**Why it is here**: the tools to build aggregate queries.

**If you removed or changed it**: `NameError` at import.

#### Block 4: dependency imports

```python
from app.core.dependencies import CurrentUser, DatabaseSession, DateRange, DateRangeFilter
```

- `CurrentUser`, `DatabaseSession`, `DateRangeFilter` - as in expenses.py Block 5.
- `DateRange` - new here: the **class** itself (a small `@dataclass` with
  `start_date` and `end_date`), not the dependency. It is imported only to be
  used as a type hint in `build_expense_filters(owner_id: int, date_range:
  DateRange)`, because that helper is a plain function that receives the
  object, not a FastAPI endpoint that asks for it.

**Why it is here**: login, database and the shared date filter for the three
endpoints; the plain class for the helper's type hint.

**If you removed or changed it**: `NameError` at import. Using `DateRangeFilter`
as the helper's type hint would be wrong in meaning (it carries a `Depends`
that only FastAPI understands) although Python would not complain.

#### Block 5: model imports

```python
from app.models.category import Category
from app.models.expense import Expense
```

- `Category` - the `categories` table class; needed for the by-category report,
  which joins expenses to their category names.
- `Expense` - the `expenses` table class; every report reads it.

**Why it is here**: the two tables the reports read.

**If you removed or changed it**: `NameError` at import.

#### Block 6: schema imports

```python
from app.schemas.report import CategoryTotal, ExpenseSummary, MonthlyTotal
```

- `app.schemas.report` - the file with the response shapes for reports
  (document 07). They are plain Pydantic models with no `from_attributes`,
  because the endpoints build them by hand with keyword arguments.
- `CategoryTotal` - one row of the by-category report (`category_id`,
  `category_name`, `total_amount`, `expense_count`, `percentage_of_total`).
- `ExpenseSummary` - the summary response (`start_date`, `end_date`,
  `total_amount`, `expense_count`, `average_amount`, `highest_amount`).
- `MonthlyTotal` - one row of the monthly report (`year`, `month`,
  `total_amount`, `expense_count`).

**Why it is here**: the three response models; FastAPI also uses them to
document the endpoints.

**If you removed or changed it**: `NameError` at import.

#### Block 7: the router

```python
router = APIRouter(prefix="/reports", tags=["Reports"])
```

- Same as expenses.py Block 8, with prefix `/reports` and docs tag "Reports".
  Final URLs: `/api/v1/reports/summary`, `/api/v1/reports/by-category`,
  `/api/v1/reports/monthly`.

**Why it is here**: common prefix and docs grouping.

**If you removed or changed it**: `main.py` fails with `AttributeError` on
`reports.router`.

#### Block 8: a named constant

```python
UNCATEGORIZED_LABEL = "Uncategorized"
```

- `UNCATEGORIZED_LABEL` - a module-level variable. ALL-CAPS is the Python
  convention for "a constant: set once, never changed".
- `= "Uncategorized"` - the name shown for expenses that have no category
  (`category_id` is `NULL`).

**Why it is here**: the word appears in the by-category report; giving it a name
means it is defined once, is easy to find, and is easy to translate or change.

**If you removed or changed it**: `NameError` in Block 27 where it is used. If
you wrote the string inline instead, nothing would break - this is purely
about keeping the file tidy.

#### Block 9: the "Helpers" banner

```python
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
```

- Comment lines: "plain functions used by the endpoints start here".

**Why it is here**: readability.

**If you removed or changed it**: nothing.

#### Block 10: `to_money` signature and docstring

```python
def to_money(value: Decimal | float | int | None) -> Decimal:
    """Round a database aggregate to 2 decimal places (None becomes 0.00)."""
```

- `def to_money(` - a helper that turns "whatever the database gave back for a
  sum/average/max" into a clean money value.
- `value: Decimal | float | int | None` - the parameter can be any of four types.
  The `|` means "or" (expenses.py Block 22). Why four? Because the database
  driver does not always hand back the same Python type:
  - `SUM(amount)` and `MAX(amount)` come back as `Decimal` (SQLAlchemy knows the
    column is `NUMERIC(12, 2)` and keeps that type for `sum`/`max`; verified).
  - `AVG(amount)` is a function SQLAlchemy has no type for, so the raw driver
    value comes back: a `float` on SQLite (verified: `2117.6225` as a float);
    on PostgreSQL the driver gives a `Decimal` for the average of a `NUMERIC`
    column.
  - With **no matching rows**, `SUM`, `AVG` and `MAX` are `NULL`, which Python
    sees as `None` (verified: `(None, 0, None, None)`).
  - `0` (an `int`) is passed explicitly by the monthly report for months with
    no data.
- `-> Decimal` - whatever comes in, a `Decimal` with two decimal places comes
  out.
- `"""Round a database aggregate ..."""` - the docstring; "aggregate" is the SQL
  word for a value computed over many rows (sum, count, average, ...).

**Why it is here**: the response schemas declare `total_amount: Decimal` etc.
This function makes sure every amount is a proper, consistently rounded
`Decimal`, whatever the database handed back.

**If you removed or changed it**: `ExpenseSummary(total_amount=None)` would fail
validation (a 500) for a user with no expenses; a float average like
`2117.6225` would appear with four decimals and float noise.

#### Block 11: the `to_money` body (`Decimal(str(...))`, `quantize`, `ROUND_HALF_UP`)

```python
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

Read it inside-out:

- `value or 0` - the `or` trick: if `value` is "falsy" (`None`, `0`, `0.0`,
  `Decimal("0")`) the expression is `0`; otherwise it is `value`. So `None`
  becomes `0`. Verified: `None or 0` is `0`; `Decimal("5") or 0` is
  `Decimal("5")`.
- `str(...)` - turn it into text: `Decimal("8470.49")` -> `"8470.49"`,
  `2117.6225` -> `"2117.6225"`, `0` -> `"0"`.
- `Decimal(...)` - make an exact decimal from that text. **Why go through
  `str`?** Because `Decimal(float)` copies the float's exact binary value, which
  is ugly: verified, `Decimal(2.675)` is
  `2.67499999999999982236431605997495353221893310546875`, while
  `Decimal(str(2.675))` is `2.675`. Converting through the string gives the
  number as the human (and the database) wrote it.
- `.quantize(Decimal("0.01"), ...)` - "give this number the **same number of
  decimal places** as `0.01`", i.e. two. `Decimal("8470.4")` becomes
  `8470.40`; `Decimal("2117.6225")` becomes `2117.62`. The argument `0.01` is
  only a *pattern* for the number of places; its value is not used.
- `rounding=ROUND_HALF_UP` - when the digits being dropped are exactly a half
  (`...5`), round up. Verified: `Decimal("2.675").quantize(Decimal("0.01"),
  rounding=ROUND_HALF_UP)` is `2.68`; with the default rounding it is also
  `2.68` here (7 is odd, so even-rounding goes up), but `2.665` gives `2.67`
  with `ROUND_HALF_UP` and `2.66` with the default. Being explicit removes the
  surprise.
- `return` - hand back the cleaned `Decimal`.

Compare with `round(2.675, 2)` on a float: verified, it gives `2.67`, because
the float `2.675` is really slightly less than 2.675. That is exactly the kind
of error this helper avoids.

**Why it is here**: one place that makes every reported amount exact, two
decimals, rounded the way people expect, and never `None`.

**If you removed or changed it**: `Decimal(value)` without `str` would carry
float garbage into averages on SQLite. Without `or 0`, `str(None)` is `"None"`
and `Decimal("None")` raises `InvalidOperation` (a 500) for any user with no
expenses in the range. Without `quantize`, totals could show as `8470.4` and
averages as `2117.6225`.

#### Block 12: `build_expense_filters` signature and docstring

```python
def build_expense_filters(owner_id: int, date_range: DateRange) -> list:
    """WHERE conditions shared by the reports: the user's expenses in the date range."""
```

- `def build_expense_filters(` - a helper that builds the same filters list you
  saw in expenses.py Blocks 27-28, so the summary and by-category reports do
  not repeat it.
- `owner_id: int` - whose expenses.
- `date_range: DateRange` - the object with `.start_date` and `.end_date`
  (Block 4).
- `-> list` - returns a Python list (of SQLAlchemy conditions).
- The docstring says what the list means in words.

**Why it is here**: two reports need exactly the same `WHERE`; writing it once
keeps them consistent.

**If you removed or changed it**: both reports would have to contain the six
lines of Block 13 themselves; forgetting the `owner_id` line in one of them
would leak other users' totals.

#### Block 13: `build_expense_filters` body

```python
    filters = [Expense.owner_id == owner_id]
    if date_range.start_date is not None:
        filters.append(Expense.expense_date >= date_range.start_date)
    if date_range.end_date is not None:
        filters.append(Expense.expense_date <= date_range.end_date)
    return filters
```

- `filters = [Expense.owner_id == owner_id]` - the always-present ownership
  condition (expenses.py Block 27).
- The two `if` blocks - add the inclusive date bounds when given (expenses.py
  Block 28).
- `return filters` - give the list back; the caller will unpack it with `*`
  into `.where(...)`.

**Why it is here**: the body of the shared filter.

**If you removed or changed it**: see Block 12. Note the monthly report does
**not** use this helper, because its date bounds are a whole year computed
from `year`, not from the client's `start_date`/`end_date`.

#### Block 14: the "Endpoints" banner

```python
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
```

- Comment lines: the `@router` functions start here.

**Why it is here**: readability.

**If you removed or changed it**: nothing.

#### Block 15: the summary decorator

```python
@router.get("/summary", response_model=ExpenseSummary, summary="Overall spending totals")
```

- `@router.get("/summary")` - GET `/reports/summary`.
- `response_model=ExpenseSummary` - the response shape with the six fields.
- `summary="Overall spending totals"` - docs title. (Do not confuse the keyword
  `summary=` - the docs title - with the path `/summary` - the report's name.
  They just happen to use the same word.)

**Why it is here**: registers the endpoint and its response shape.

**If you removed or changed it**: no endpoint; 404 from the router.

#### Block 16: the summary function signature

```python
def get_expense_summary(
    db: DatabaseSession, current_user: CurrentUser, date_range: DateRangeFilter
) -> ExpenseSummary:
```

- `db`, `current_user` - as always.
- `date_range: DateRangeFilter` - the optional `?start_date=&end_date=` filter,
  validated by the dependency (start after end -> 422).
- `-> ExpenseSummary` - the function builds and returns the response model
  itself.

**Why it is here**: "totals for me, optionally within these dates".

**If you removed or changed it**: without `date_range` the report would always
cover all time and the two `if` lines in the helper would get an error.

#### Block 17: four aggregates in one SELECT

```python
    total_amount, expense_count, average_amount, highest_amount = db.execute(
        select(
            func.sum(Expense.amount),
            func.count(Expense.id),
            func.avg(Expense.amount),
            func.max(Expense.amount),
        )
```

- `total_amount, expense_count, average_amount, highest_amount =` - **tuple
  unpacking**: the right side produces one row with four values, and Python
  assigns them to the four names, in order. It is the same as writing
  `row = ...; total_amount = row[0]; expense_count = row[1]; ...`, but shorter.
  The number of names must equal the number of values, or Python raises
  `ValueError: not enough values to unpack` / `too many values to unpack`.
- `db.execute(...)` - run a statement and return a `Result` object. It is used
  here (instead of `db.scalar`/`db.scalars`) because we want a whole **row** of
  several columns, not just the first column.
- `select(` ... `)` - a `SELECT` with four expressions instead of a table.
- `func.sum(Expense.amount)` - SQL `sum(expenses.amount)`: add up all amounts.
  `NULL` if there are no rows.
- `func.count(Expense.id)` - SQL `count(expenses.id)`: how many rows (counting
  a `NOT NULL` column such as the primary key is the same as `count(*)`).
  `0` if there are no rows, never `NULL`.
- `func.avg(Expense.amount)` - SQL `avg(expenses.amount)`: the mean. `NULL` if
  no rows.
- `func.max(Expense.amount)` - SQL `max(expenses.amount)`: the largest single
  expense. `NULL` if no rows.
- The trailing comma after `func.max(...)` is allowed by Python and keeps the
  lines uniform.

The SQL (verified):

```sql
SELECT sum(expenses.amount) AS sum_1, count(expenses.id) AS count_1,
       avg(expenses.amount) AS avg_1, max(expenses.amount) AS max_1
FROM expenses
WHERE expenses.owner_id = 1
```

SQLAlchemy invents the names `sum_1`, `count_1`... because no `.label()` was
given; that is fine here since the values are unpacked by position, not by
name. The result for the test data was the row
`(Decimal('8470.49'), 4, 2117.6225, Decimal('8000.00'))`.

**Why it is here**: one round trip gives all four numbers; the database does the
arithmetic over any number of rows.

**If you removed or changed it**: doing this in Python (`sum(e.amount for e in
all_expenses)`) would load every row of the user into memory just to add them.
Swapping the order of two `func.*` calls without swapping the names on the left
would silently put the count into `total_amount` - the names are only matched
**by position**.

#### Block 18: the WHERE and `.one()`

```python
        ).where(*build_expense_filters(current_user.id, date_range))
    ).one()
```

- `).where(` - the `WHERE` of the aggregate query.
- `*build_expense_filters(current_user.id, date_range)` - call the helper to
  get the filters list, then unpack it with `*` into separate arguments
  (expenses.py Block 32). So this is `.where(owner_cond, start_cond, end_cond)`
  with the date conditions present only when given.
- `)` - closes `db.execute(`.
- `.one()` - from the `Result`: "return **exactly one row**". SQLAlchemy's own
  documentation: it raises `NoResultFound` if there are no rows and
  `MultipleResultsFound` if there are several. An aggregate query **without**
  `GROUP BY` always returns exactly one row - even when no expense matches, you
  get one row of `(None, 0, None, None)` (verified). So `.one()` is safe here
  and expresses the intent: "I expect one row and it would be a bug to get
  anything else." The row it returns is a `Row` object, which behaves like a
  tuple, so the unpacking in Block 17 works.

**Why it is here**: filters shared with the by-category report; `.one()` for a
query that must give one row.

**If you removed or changed it**: `.first()` would also work and would return
`None` for zero rows - but an aggregate never gives zero rows, so `.one()` is
both correct and stricter. `.all()` would give a list of one row and the
unpacking would fail (`not enough values to unpack`, since a list of one row
has one element, not four).

#### Block 19: build the summary response

```python
    return ExpenseSummary(
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        total_amount=to_money(total_amount),
        expense_count=expense_count,
        average_amount=to_money(average_amount),
        highest_amount=to_money(highest_amount),
    )
```

- `return ExpenseSummary(` - build the response model with keyword arguments.
- `start_date=date_range.start_date`, `end_date=date_range.end_date` - echo the
  range back (both `None` when not given), so the client knows what the numbers
  cover.
- `total_amount=to_money(total_amount)` - the `SUM`, cleaned (Block 11).
- `expense_count=expense_count` - the `COUNT`, already an `int`; no cleaning
  needed.
- `average_amount=to_money(average_amount)` - the `AVG`, cleaned; this is where
  the float-on-SQLite / `None`-on-empty cases are handled.
- `highest_amount=to_money(highest_amount)` - the `MAX`, cleaned.

Verified responses: a user with two expenses of 300 and 8000 gets
`{"total_amount": "8300.00", "expense_count": 2, "average_amount": "4150.00",
"highest_amount": "8000.00"}`; a user with no expenses gets
`"0.00"`, `0`, `"0.00"`, `"0.00"`. Amounts appear as **strings** in JSON
because that is how Pydantic serialises `Decimal` here - it keeps them exact.

**Why it is here**: the endpoint's answer, with every money field normalised.

**If you removed or changed it**: passing `total_amount` raw would send `None`
for an empty range and fail validation (`Decimal` field cannot be `None`),
giving a 500 to new users who have not added anything yet.

#### Block 20: the by-category decorator

```python
@router.get(
    "/by-category",
    response_model=list[CategoryTotal],
    summary="Spending grouped by category",
)
```

- `@router.get("/by-category")` - GET `/reports/by-category`.
- `response_model=list[CategoryTotal]` - the response is a JSON **list**, each
  item shaped like `CategoryTotal`. `list[...]` with square brackets is the
  built-in way (Python 3.9+) to say "a list of X"; your old code used
  `List[Post]` from `typing`, which means the same.
- `summary=...` - docs title.

**Why it is here**: registers the endpoint; a list is the natural shape for
"one row per category".

**If you removed or changed it**: no endpoint. With `response_model=CategoryTotal`
(no list) FastAPI would reject the list the function returns (500).

#### Block 21: the by-category signature and docstring

```python
def get_spending_by_category(
    db: DatabaseSession, current_user: CurrentUser, date_range: DateRangeFilter
) -> list[CategoryTotal]:
    """Biggest category first. Expenses without a category are grouped as "Uncategorized"."""
```

- `db`, `current_user`, `date_range` - as in Block 16.
- `-> list[CategoryTotal]` - returns a list of the response models.
- The docstring states the two behaviours that are not obvious from the name:
  the sort order and what happens to expenses with no category. FastAPI also
  shows a function's docstring as the endpoint description in `/docs`.

**Why it is here**: the inputs for "my spending per category, optionally in this
range".

**If you removed or changed it**: as in Block 16.

#### Block 22: naming the sum expression

```python
    total_amount = func.sum(Expense.amount)
```

- `total_amount =` - store a SQL **expression** (not a value) in a variable.
  Nothing runs yet; this is the object that will print as
  `sum(expenses.amount)`.
- `func.sum(Expense.amount)` - the `SUM` of the amount column.

The same expression is needed twice below: in the `SELECT` list and in
`ORDER BY`. Putting it in a variable means it is written once, and the `ORDER BY`
is guaranteed to sort by the very same thing that is selected.

**Why it is here**: avoids repeating `func.sum(Expense.amount)` and keeps the
sort tied to the selected total.

**If you removed or changed it**: you would write `func.sum(Expense.amount)` in
both places; it works the same, with a little more room for typos.

#### Block 23: the SELECT list, and `label()`

```python
    rows = db.execute(
        select(
            Category.id,
            Category.name,
            total_amount.label("total_amount"),
            func.count(Expense.id).label("expense_count"),
        )
```

- `rows =` - the list of result rows (after `.all()` in Block 25).
- `db.execute(` - we want several columns per row, so `execute` + `Row`
  objects (Block 17).
- `select(` - the four things to return per group:
- `Category.id` - the category's id (will be `NULL`/`None` for the
  uncategorized group).
- `Category.name` - the category's name (also `None` for uncategorized).
- `total_amount.label("total_amount")` - the sum, **labelled**. `.label(name)`
  adds `AS name` in the SQL (`sum(expenses.amount) AS total_amount`). Without
  a label SQLAlchemy would call it `sum_1`. The label matters here because the
  rows are read **by name** later: `row.total_amount` (Block 26).
- `func.count(Expense.id).label("expense_count")` - how many expenses in the
  group, as `count(expenses.id) AS expense_count`, read later as
  `row.expense_count`.
- `Category.id` and `Category.name` need no label: a plain column is already
  reachable by its column name (`row.id`, `row.name`).

**Why it is here**: picks the four values each report row needs, with stable
names.

**If you removed or changed it**: without the labels, `row.total_amount` would
raise `AttributeError` (verified: a `Row` has only the names that were
selected or labelled; asking for a missing one gives `AttributeError`). You
would have to use `row[2]`, which breaks silently if the column order changes.

#### Block 24: `select_from` and `outerjoin`

```python
        .select_from(Expense)
        # OUTER join keeps expenses whose category_id is NULL.
        .outerjoin(Category, Expense.category_id == Category.id)
```

- `.select_from(Expense)` - make `expenses` the **starting table** of the
  `FROM`. Needed because the first columns in the `SELECT` list come from
  `Category`; without this SQLAlchemy would start from `categories` and the
  join direction would be reversed (or it would produce a cross join).
- `# OUTER join keeps expenses ...` - the comment explains the choice of join.
- `.outerjoin(Category, Expense.category_id == Category.id)` - add
  `LEFT OUTER JOIN categories ON expenses.category_id = categories.id`. The
  first argument is the table to join; the second is the `ON` condition
  (which expense row matches which category row).

**Why "outer"?** A plain (inner) `JOIN` returns only rows that match on both
sides. An expense with `category_id = NULL` matches **no** category, so an
inner join would **drop it** from the report - and its money would vanish from
the totals. A `LEFT OUTER JOIN` keeps every row from the left table
(`expenses`) and fills the right side (`categories`) with `NULL` when there is
no match. Those `NULL`-category expenses then group together into one row
whose `id` and `name` are `None` - the "Uncategorized" row.

Verified with four expenses (two Food, one Rent, one without a category):

- outer join: three rows, `(2, 'Rent', 8000.00, 1)`, `(1, 'Food', 370.50, 2)`,
  `(None, None, 99.99, 1)`.
- inner join (`.join` instead of `.outerjoin`): only the first two rows; the
  99.99 expense disappears.

The SQL (identical on SQLite and PostgreSQL, verified):

```sql
SELECT categories.id, categories.name, sum(expenses.amount) AS total_amount,
       count(expenses.id) AS expense_count
FROM expenses LEFT OUTER JOIN categories ON expenses.category_id = categories.id
WHERE expenses.owner_id = 1
GROUP BY categories.id, categories.name
ORDER BY sum(expenses.amount) DESC
```

**Why it is here**: attach each expense to its category name, without losing the
expenses that have none.

**If you removed or changed it**: `.join(...)` would silently omit uncategorized
spending, so the percentages would not add up to the real total. Without
`.select_from(Expense)` the `FROM` would start from `categories` and you would
get the join the other way round (categories with no expenses would appear
with `NULL` totals, and the `WHERE expenses.owner_id` would turn it back into
an inner join anyway).

#### Block 25: `where`, `group_by`, `order_by`, `.all()`

```python
        .where(*build_expense_filters(current_user.id, date_range))
        .group_by(Category.id, Category.name)
        .order_by(total_amount.desc())
    ).all()
```

- `.where(*build_expense_filters(...))` - the shared user + date filter,
  unpacked with `*` (Block 18).
- `.group_by(Category.id, Category.name)` - SQL `GROUP BY categories.id,
  categories.name`. `GROUP BY` collapses all rows that have the same values in
  the listed columns into **one** row, and the aggregate functions (`sum`,
  `count`) are computed **per group**. Grouping by both `id` and `name` is
  required by SQL: every non-aggregated column in the `SELECT` list must appear
  in `GROUP BY` (PostgreSQL enforces this strictly). `id` alone would be enough
  to define the groups, but `name` must be listed too because it is selected.
- `.order_by(total_amount.desc())` - `ORDER BY sum(expenses.amount) DESC`:
  biggest spending first, as the docstring promises. This reuses the
  expression from Block 22.
- `)` - closes `db.execute(`.
- `.all()` - fetch every row into a Python list of `Row` objects. The list is
  iterated **twice** below (once for the grand total, once to build the
  response), which is why it must be a list and not a one-shot iterator.

**Why it is here**: finish the query: filter, group, sort, fetch.

**If you removed or changed it**: without `group_by`, the database would reject
the query (`categories.id must appear in the GROUP BY clause or be used in an
aggregate function` on PostgreSQL). Without `.all()`, the second loop over
`rows` in Block 27 would find the iterator already exhausted and produce an
empty list.

#### Block 26: the grand total (generator expression + `sum` with a start value)

```python
    grand_total = sum((to_money(row.total_amount) for row in rows), Decimal("0"))
```

- `grand_total =` - the total over all categories, needed to compute each
  category's percentage.
- `sum(iterable, start)` - Python's built-in `sum`. It adds every item of the
  iterable to `start`.
- `(to_money(row.total_amount) for row in rows)` - a **generator expression**:
  like a list comprehension but with round brackets; it produces the values one
  at a time instead of building a list. For each `row` it yields
  `to_money(row.total_amount)` - the category's total as a clean `Decimal`.
- `row.total_amount` - **Row attribute access**: a `Row` acts like a named tuple,
  so a column can be read by its (label) name as an attribute. SQLAlchemy's own
  docstring: the `Row` "seeks to act as much like a Python named tuple as
  possible". `row[2]` would give the same value by position, and
  `row._mapping["total_amount"]` by dictionary key (verified all three).
- `Decimal("0")` - the **start value**. Without it, `sum` starts from the
  integer `0`; `0 + Decimal(...)` still works, but if `rows` is **empty** the
  result would be the `int` `0`, not a `Decimal`. Giving `Decimal("0")` keeps
  the type consistent in every case. Verified:
  `sum((Decimal("1.10"), Decimal("2.20")), Decimal("0"))` is `Decimal("3.30")`.

Why add the **rounded** per-category totals rather than one `SUM` over
everything? So that the percentages below are computed from exactly the
numbers the client sees, and add up to 100 as closely as rounding allows.

**Why it is here**: the denominator of the percentage.

**If you removed or changed it**: no `grand_total` -> `NameError` in Block 28.

#### Block 27: the list comprehension and the response rows

```python
    return [
        CategoryTotal(
            category_id=row.id,
            category_name=row.name or UNCATEGORIZED_LABEL,
            total_amount=to_money(row.total_amount),
            expense_count=row.expense_count,
```

- `return [` ... `for row in rows ]` - a **list comprehension**: build a list by
  evaluating the expression (`CategoryTotal(...)`) once for every `row`. It is
  the compact form of:

  ```python
  result = []
  for row in rows:
      result.append(CategoryTotal(...))
  return result
  ```

- `CategoryTotal(` - one response row.
- `category_id=row.id` - the category's id, or `None` for the uncategorized
  group. The schema allows `int | None` for this reason.
- `category_name=row.name or UNCATEGORIZED_LABEL` - the `or` trick again: if
  `row.name` is `None` (uncategorized group), use `"Uncategorized"` (Block 8);
  otherwise use the name. (A real category name can never be an empty string -
  the category schema requires at least one character - so `or` cannot
  misfire here.)
- `total_amount=to_money(row.total_amount)` - the group's sum, cleaned.
- `expense_count=row.expense_count` - the group's count, an `int`.

Verified response for a user whose only expenses are uncategorized:

```json
[{"category_id": null, "category_name": "Uncategorized",
  "total_amount": "8300.00", "expense_count": 2, "percentage_of_total": 100.0}]
```

and `[]` for a user with no expenses.

**Why it is here**: turns database rows into the documented response shape,
with a friendly label for the `NULL` group.

**If you removed or changed it**: `category_name=row.name` alone would pass
`None` into a `str` field and fail validation (500) for anyone with an
uncategorized expense.

#### Block 28: the percentage

```python
            percentage_of_total=round(
                float(to_money(row.total_amount) / grand_total * 100), 2
            ),
        )
        for row in rows
    ]
```

- `percentage_of_total=` - this category's share of all spending in the range.
- `to_money(row.total_amount) / grand_total` - `Decimal` divided by `Decimal`:
  the fraction (for example `Decimal("250.00") / Decimal("8470.49")` is
  `0.02951423117...`, computed exactly to 28 significant digits).
- `* 100` - to a percentage (still a `Decimal`).
- `float(...)` - convert to a float, because the schema declares
  `percentage_of_total: float`. A percentage for a chart does not need to be
  exact money; a float is the natural JSON number for it (`2.95`, not `"2.95"`).
- `round(..., 2)` - Python's built-in `round` to two decimal places. Verified:
  `round(float(Decimal("250.00") / Decimal("8470.49") * 100), 2)` is `2.95`.
- `)` closes `CategoryTotal(`; `for row in rows` is the loop of the
  comprehension; `]` closes the list.

**Can `grand_total` be zero (division by zero)?** No. If there are no rows,
the comprehension never runs, so the division never happens. If there are rows,
each has at least one expense, and every expense has `amount > 0` (enforced by
the schema and by the database `CHECK` constraint), so `grand_total > 0`.

**Why it is here**: a pie chart needs each slice's share.

**If you removed or changed it**: leaving out `float(...)` would pass a
`Decimal` to a `float` field; Pydantic would accept and convert it, but the
intent is clearer with the explicit conversion. Rounding to 0 places would
show "3" instead of "2.95".

#### Block 29: the monthly decorator

```python
@router.get(
    "/monthly",
    response_model=list[MonthlyTotal],
    summary="Spending for each month of a year",
)
```

- `@router.get("/monthly")` - GET `/reports/monthly`.
- `response_model=list[MonthlyTotal]` - a list of twelve `MonthlyTotal` rows.
- `summary=...` - docs title.

**Why it is here**: registers the endpoint.

**If you removed or changed it**: no endpoint.

#### Block 30: the monthly signature, the `year` parameter and the docstring

```python
def get_monthly_spending(
    db: DatabaseSession,
    current_user: CurrentUser,
    year: Annotated[
        int | None,
        Query(ge=2000, le=2100, description="Defaults to the current year"),
    ] = None,
) -> list[MonthlyTotal]:
    """Always returns 12 rows (January to December) so charts need no gap-filling."""
```

- `db`, `current_user` - as always. There is **no** `date_range` here: the
  period is a whole year chosen by `year`.
- `year: Annotated[int | None, Query(ge=2000, le=2100, description=...)] = None` -
  an optional query parameter `?year=2026` (the `Annotated` + `Query` pattern
  from expenses.py Block 22). `ge=2000, le=2100` keeps it to a sensible range;
  verified, `?year=1999` answers 422 "Input should be greater than or equal to
  2000". Default `None` means "the current year" (Block 31).
- `-> list[MonthlyTotal]` - the return type.
- The docstring explains the promise that makes this endpoint chart-friendly:
  twelve rows **always**, zeros included, so a frontend can draw a bar per
  month without first checking which months are missing.

**Why it is here**: "my spending per month in this year".

**If you removed or changed it**: without `ge`/`le`, `?year=99999` would be
accepted and `date(99999, 1, 1)` in Block 33 would raise `ValueError: year
99999 is out of range` - a 500 instead of a 422.

#### Block 31: default year and the month expression (`extract`)

```python
    year = year or date.today().year
    month = extract("month", Expense.expense_date)
```

- `year = year or date.today().year` - the `or` trick: if the client sent a year,
  keep it; if `year` is `None`, use the current year. `date.today()` is today's
  date (verified `2026-10-06` on the day this was checked), and `.year` is its
  year as an `int`. After this line `year` is always an `int`.
- `month = extract("month", Expense.expense_date)` - a SQL **expression** (not
  a value) that means "the month number of the `expense_date` column". It is
  stored in a variable because it is needed twice: in the `SELECT` list and in
  `GROUP BY`, which must match exactly.
- `extract(field, expr)` - SQLAlchemy's `EXTRACT`. The first argument is the
  part to pull out, as a string (`"year"`, `"month"`, `"day"`, ...); SQLAlchemy
  writes it into the SQL literally, which is why it must be a fixed string from
  the code, never user input (SQLAlchemy's docstring warns about exactly that).
  The second argument is the column.

What it becomes, verified:

- PostgreSQL: `EXTRACT(month FROM expenses.expense_date)`.
- SQLite (tests): `CAST(STRFTIME('%m', expenses.expense_date) AS INTEGER)` -
  SQLite has no `EXTRACT`, so SQLAlchemy translates it. You write the same
  Python either way.

**Why it is here**: a default that makes `/reports/monthly` work with no
parameters, and the month expression used in two places.

**If you removed or changed it**: without the default, `date(None, 1, 1)` in
Block 33 would raise `TypeError` for requests with no `?year=`. Writing
`extract("month", ...)` twice (select and group by) works but risks the two
drifting apart.

#### Block 32: the monthly SELECT list

```python
    rows = db.execute(
        select(
            month.label("month"),
            func.sum(Expense.amount).label("total_amount"),
            func.count(Expense.id).label("expense_count"),
        )
```

- `rows = db.execute(select(` - a multi-column aggregate query, as in Block 23.
- `month.label("month")` - the month expression from Block 31, labelled so it
  can be read as `row.month`.
- `func.sum(Expense.amount).label("total_amount")` - the month's total, read as
  `row.total_amount`.
- `func.count(Expense.id).label("expense_count")` - the month's count, read as
  `row.expense_count`.

**Why it is here**: one row per month that has data, with the three values the
response needs.

**If you removed or changed it**: without the labels, `row.month` etc. in
Blocks 35-37 would raise `AttributeError`.

#### Block 33: the year filter, written as a date range

```python
        .where(
            Expense.owner_id == current_user.id,
            # A date range (instead of extract(year) = ...) lets the database
            # use the (owner_id, expense_date) index.
            Expense.expense_date >= date(year, 1, 1),
            Expense.expense_date <= date(year, 12, 31),
        )
```

- `.where(` - three conditions joined with `AND`:
- `Expense.owner_id == current_user.id` - only my expenses (written directly
  here instead of via `build_expense_filters`, because the dates come from
  `year`, not from the client's date range).
- `# A date range (instead of extract(year) = ...) ...` - the comment explains
  a performance choice, see below.
- `Expense.expense_date >= date(year, 1, 1)` - on or after 1 January of the
  year. `date(year, 1, 1)` builds that Python date.
- `Expense.expense_date <= date(year, 12, 31)` - on or before 31 December.

**Why a range and not `extract("year", Expense.expense_date) == year`?** Both
give the same rows. But the `expenses` table has an index on
`(owner_id, expense_date)` (see `app/models/expense.py`). An index is like the
sorted index at the back of a book: the database can jump straight to the
user's rows in the date range. If the `WHERE` applies a **function** to the
column (`EXTRACT(year FROM expense_date)`), the index on the raw column cannot
be used, and PostgreSQL has to read every expense of the user and compute the
year for each. With plain `>=`/`<=` comparisons on the column itself, the
index works. The difference is invisible with ten expenses and large with a
hundred thousand.

The full SQL on PostgreSQL (verified):

```sql
SELECT EXTRACT(month FROM expenses.expense_date) AS month,
       sum(expenses.amount) AS total_amount, count(expenses.id) AS expense_count
FROM expenses
WHERE expenses.owner_id = 1
  AND expenses.expense_date >= '2026-01-01' AND expenses.expense_date <= '2026-12-31'
GROUP BY EXTRACT(month FROM expenses.expense_date)
```

**Why it is here**: restrict to the user's expenses of that year, in a way the
index can speed up.

**If you removed or changed it**: without the `owner_id` condition the report
would mix every user's spending. With `extract("year", ...) == year` the
result would be identical but slower on large tables.

#### Block 34: group by month and fetch

```python
        .group_by(month)
    ).all()
```

- `.group_by(month)` - `GROUP BY` the same month expression (Block 31): one
  output row per distinct month that has at least one expense. Months with no
  expenses produce **no row at all** - that gap is filled in Python below.
- `)` - closes `db.execute(`.
- `.all()` - the rows as a list.

Verified result for expenses in January, February and March only: three rows,
`(1, 370.50, 2)`, `(2, 8000.00, 1)`, `(3, 99.99, 1)`.

**Why it is here**: the per-month aggregation, done by the database.

**If you removed or changed it**: without `group_by`, PostgreSQL rejects the
query (the `month` column is not aggregated). Grouping by a *different*
expression than the one selected would also be rejected.

#### Block 35: the dictionary comprehension

```python
    totals_by_month = {int(row.month): row for row in rows}
```

- `totals_by_month =` - a dictionary that maps month number -> its row.
- `{ key: value for row in rows }` - a **dictionary comprehension**: like a list
  comprehension but with curly braces and a `key: value` pair. For each `row` it
  adds one entry. Verified shape: `{1: (1, 370.50, 2), 2: (2, 8000.00, 1), 3: (3, 99.99, 1)}`.
- `int(row.month)` - the key. `row.month` comes back as an `int` from SQLite
  (verified). From PostgreSQL, `EXTRACT` returns a numeric value and the exact
  Python type the driver hands back may be a `Decimal` - I am not 100% sure of
  the driver's choice for every PostgreSQL version, and that uncertainty is
  exactly why `int(...)` is here: whatever arrives, the key becomes a plain
  Python `int`, so it matches the `int` values of `range(1, 13)` in the next
  block. (`{Decimal("3"): ...}.get(3)` would, in fact, find the key, since
  `Decimal("3") == 3` and they hash the same - but relying on that is fragile.)
- `: row` - the value is the whole `Row`, so both `row.total_amount` and
  `row.expense_count` are available later.
- `for row in rows` - loop over the query result.

**Why it is here**: turns "a list of rows for some months" into "look up a month
in O(1)". Without the dictionary, the 12-month loop below would have to scan
the list for each month.

**If you removed or changed it**: using `row.month` without `int()` would still
work on SQLite and very probably on PostgreSQL, but the explicit conversion
makes the key type certain.

#### Block 36: the 12-month fill loop begins

```python
    monthly_totals = []
    for month_number in range(1, 13):
        row = totals_by_month.get(month_number)
```

- `monthly_totals = []` - an empty list to fill with twelve `MonthlyTotal`
  objects.
- `for month_number in range(1, 13):` - loop over the integers 1 to 12.
  `range(start, stop)` goes from `start` **up to but not including** `stop`, so
  `range(1, 13)` is `1, 2, ..., 12` (verified). This is the "always 12 rows"
  promise from the docstring.
- `row = totals_by_month.get(month_number)` - dictionary `.get()` returns the
  row for that month, or `None` if the month had no expenses (verified:
  `.get()` on a missing key is `None`, no error). Using `[month_number]` instead
  would raise `KeyError` for empty months.

**Why it is here**: walks every month, including the empty ones, so the gaps
can be filled with zeros.

**If you removed or changed it**: looping over `rows` instead would output only
the months that have data; a chart would then show January, February, March
and nothing else, and the frontend would have to guess which months were
missing.

#### Block 37: one `MonthlyTotal` per month, zeros for empty months

```python
        monthly_totals.append(
            MonthlyTotal(
                year=year,
                month=month_number,
                total_amount=to_money(row.total_amount if row else 0),
                expense_count=row.expense_count if row else 0,
            )
        )
```

- `monthly_totals.append(` - add one object to the list.
- `MonthlyTotal(` - the response model for one month.
- `year=year` - the year (the client's or the current one).
- `month=month_number` - 1 to 12.
- `total_amount=to_money(row.total_amount if row else 0)` - a **conditional
  expression**: `A if condition else B` evaluates to `A` when the condition is
  true, otherwise `B`. Here: if there is a row for this month, use its sum;
  otherwise use `0`. Then `to_money` cleans it (`0` becomes `Decimal("0.00")`).
- `expense_count=row.expense_count if row else 0` - the same idea for the
  count.
- `)` `)` - close `MonthlyTotal(` and `append(`.

Verified response for `?year=2026` with expenses in January (300) and February
(8000): twelve objects, `{"year": 2026, "month": 1, "total_amount": "300.00",
"expense_count": 1}`, `{"year": 2026, "month": 2, "total_amount": "8000.00",
"expense_count": 1}`, then ten objects with `"0.00"` and `0`.

**Why it is here**: builds the twelve rows, real values where there are
expenses, zeros elsewhere.

**If you removed or changed it**: `row.total_amount` without the `if row` guard
would raise `AttributeError: 'NoneType' object has no attribute 'total_amount'`
on the first empty month (a 500 for almost every user).

#### Block 38: return

```python
    return monthly_totals
```

- `return monthly_totals` - the list of twelve `MonthlyTotal` objects; FastAPI
  serialises it as a JSON array.

**Why it is here**: the endpoint's answer.

**If you removed or changed it**: the function would return `None`, which does
not match `list[MonthlyTotal]` - a 500.

### Compared to your old code

There is **no** old equivalent of `reports.py`. Your posts API had create, read,
update and delete, but no endpoint that summarised data: no totals, no
grouping, no per-month view. The closest thing in the old code is the shape of
a query - `db.query(table).filter(...)` - and even that never used `func.sum`,
`group_by` or a join.

Why the new file exists: an expense tracker is only useful if it can answer
"how much did I spend, on what, and when?". Those questions need aggregate
queries (`SUM`, `COUNT`, `AVG`, `MAX`, `GROUP BY`) rather than row-by-row reads,
so they get their own router, separate from the CRUD endpoints in
`expenses.py`.

Three habits from the old code that the new file deliberately changes, even
though the endpoints are new:

- **Where the arithmetic happens.** A tempting first version of a summary would
  fetch `db.query(table).all()` and add the amounts in Python. The new file
  always asks the database for the totals (file docstring). The database is
  faster at this and sends back one row instead of thousands.
- **Error status codes.** The old list endpoint raised an `HTTPException` with
  status 200 for "no posts". The reports never raise: no data means zeros
  (`/summary`, `/monthly`) or an empty list (`/by-category`), which is simply
  the truth.
- **Money types.** The old `Post` had no numbers to round. The new reports pass
  every amount through `to_money`, so a client never sees `None`, a float
  average like `2117.6225`, or a value that depends on which database driver
  produced it.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| aggregate | a value computed over many rows: `sum`, `count`, `avg`, `max` |
| `func.sum / count / avg / max` | the SQL aggregate functions; `count(Expense.id)` counts rows |
| `db.execute(stmt)` | run `stmt` and get a `Result` of multi-column `Row`s |
| `.one()` | take exactly one row from a `Result`; error if 0 or more than 1 |
| tuple unpacking | `a, b, c = row` assigns the row's values to names by position |
| `Row` | a result row that acts like a named tuple: `row[0]`, `row.name`, `row._mapping["name"]` |
| `.label("x")` | adds `AS x` to a selected expression so it can be read as `row.x` |
| `.select_from(Expense)` | sets the starting table of the `FROM` clause |
| `.outerjoin(T, cond)` | `LEFT OUTER JOIN T ON cond`: keeps left rows with no match, right side `NULL` |
| `.group_by(a, b)` | collapses rows with the same `a`, `b` into one; aggregates are per group |
| `extract("month", col)` | SQL `EXTRACT(month FROM col)`: the month number of a date |
| `Decimal(str(x))` | exact decimal from the text of `x` (avoids float garbage) |
| `.quantize(Decimal("0.01"))` | round to two decimal places |
| `ROUND_HALF_UP` | rounding mode: a tie (`...5`) rounds up (school rounding); the default is half-to-even |
| `x or default` | `default` when `x` is `None`/`0`/empty, else `x` |
| `A if cond else B` | conditional expression: `A` when `cond` is true, otherwise `B` |
| generator expression | `(f(r) for r in rows)`: produces values one at a time, no list built |
| list comprehension | `[f(r) for r in rows]`: builds a list from a loop in one expression |
| dictionary comprehension | `{k(r): v(r) for r in rows}`: builds a dict from a loop in one expression |
| `dict.get(key)` | the value for `key`, or `None` if missing (no `KeyError`) |
| `sum(iterable, start)` | adds every item to `start`; `Decimal("0")` keeps the result a `Decimal` |
| `range(1, 13)` | the integers 1 to 12 (the stop value is excluded) |
| index | a database structure that speeds up lookups on a column; defeated by wrapping the column in a function |

---

## Summary of this folder

`expenses.py` and `reports.py` are the two routers that work on the `expenses`
table, and together they are what makes this project an expense tracker rather
than a generic CRUD API. `expenses.py` writes and reads individual rows:
`POST`, `GET` (one page), `GET /{id}`, `PATCH` and `DELETE`, every one of them
locked to the logged-in user by `Expense.owner_id == current_user.id` and, where
a category is involved, by the shared `get_owned_category_or_404` helper from
`categories.py`. `reports.py` never writes; it asks the database to add things
up with `SUM`, `COUNT`, `AVG`, `MAX`, `GROUP BY` and an outer join, then tidies
the results into exact two-decimal `Decimal` values with `to_money`. Both files
get their database session, their current user and their optional date range
from the same three aliases in `app/core/dependencies.py`, and both use the
same "filters list + `.where(*filters)`" pattern so the ownership rule is
written once per query and cannot be forgotten. The list endpoint shows the
SQLAlchemy 2.0 query style in full - `select()`, `.where()`, `.order_by()` with
a tie-breaker, `.limit()`/`.offset()`, `selectinload` to avoid N+1 - and the
reports show the aggregate side of the same API - `func.*`, `.label()`,
`.group_by()`, `.outerjoin()`, `extract()`, `Row` attribute access. Their
request and response shapes live in `app/schemas/expense.py` and
`app/schemas/report.py`; the table definitions, including the
`(owner_id, expense_date)` index that the monthly report is written to use,
live in `app/models/`. `app/main.py` mounts both routers under `/api/v1`, which
is the only place they are imported.

