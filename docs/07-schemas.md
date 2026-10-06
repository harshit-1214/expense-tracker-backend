# app/schemas/ (auth, user, category, expense, report)

This document explains the six files inside `app/schemas/`, word by word:

| File                        | What it defines                                                        |
| --------------------------- | ---------------------------------------------------------------------- |
| `app/schemas/__init__.py`   | makes `app.schemas` a package; holds only a docstring                  |
| `app/schemas/auth.py`       | `Token` - what `POST /auth/login` returns                              |
| `app/schemas/user.py`       | `UserCreate` (register body) and `UserResponse` (profile)              |
| `app/schemas/category.py`   | `CategoryCreate`, `CategoryUpdate`, `CategoryResponse`, `CategorySummary` |
| `app/schemas/expense.py`    | `ExpenseCreate`, `ExpenseUpdate`, `ExpenseResponse`, `ExpenseListResponse` |
| `app/schemas/report.py`     | `ExpenseSummary`, `CategoryTotal`, `MonthlyTotal` (report responses)   |

## What a "schema" is (read this first)

A **schema** is a Python class that describes the **shape of JSON**: which keys
exist, what type each value has, and which rules the values must follow. The
library that does this is **Pydantic**. Every schema in this folder is a class
that inherits from `pydantic.BaseModel`.

Schemas sit between the outside world and your code, in both directions:

```
   request body (JSON text)                      response (JSON text)
            |                                             ^
            v                                             |
   request schema  (UserCreate, ExpenseCreate ...)   response schema (UserResponse, ExpenseResponse ...)
   - checks every value                              - picks which attributes to show
   - converts "2026-10-06" -> date, "20" -> Decimal   - converts Decimal -> "20.00", date -> "2026-10-06"
   - rejects bad input with HTTP 422                  - never shows hashed_password
            |                                             ^
            v                                             |
         router function  -------->  SQLAlchemy model object (a row)
```

Two rules that the whole folder follows:

1. **Models describe tables, schemas describe JSON.** `app/models/user.py` has a
   `hashed_password` column. No schema in this folder has a `hashed_password` or
   `password` field in a *response* class, so the hash can never reach a client.
2. **One class per job.** `XxxCreate` is the body of `POST`, `XxxUpdate` is the
   body of `PATCH`, `XxxResponse` is what the API returns. In your old project
   one class sometimes did two jobs (for example `PostBase` was both the create
   body and the update body). You will see below why that was a problem.

How Pydantic reads a class, in one sentence: every line of the form
`name: type` (or `name: type = default`) inside a `BaseModel` class is a
**field**, and Pydantic generates the checking code for it from the `type`.

When a check fails, Pydantic raises a `ValidationError`. FastAPI catches it and
answers with status **422 Unprocessable Content** and a JSON body that lists
every problem. You will see real examples of those bodies below.

All facts in this document (error messages, JSON output, library behaviour)
were checked by running the real code with Pydantic 2.13.5, FastAPI 0.141.1
and Python 3.14 in this project's environment, so you can trust them. Where
I could not verify something, I say so.

---

## File: app/schemas/__init__.py

### What this file is for

A folder is importable as a Python **package** only if it contains a file named
`__init__.py`. This file makes `app/schemas/` importable as `app.schemas`. It
contains only a docstring: a note for the reader about what each file in the
folder does. Unlike `app/models/__init__.py` (doc 06), it does **not** import
the classes, because nothing in the project needs "all schemas at once": each
router imports exactly the schemas it uses, for example
`from app.schemas.user import UserCreate, UserResponse`.

Who imports it: nobody directly. Python runs it automatically the first time any
`app.schemas.something` is imported.

What it imports: nothing.

### The whole file

```python
"""
schemas/ - Pydantic models that define what the API accepts and returns.

Models (app/models) describe database tables; schemas describe JSON.
Keeping them separate means a column like `hashed_password` can never
leak into a response by accident.

    auth.py      -> login token response
    user.py      -> register request and user profile response
    category.py  -> category create / update / response
    expense.py   -> expense create / update / response and the paginated list
    report.py    -> spending summary responses
"""
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""
schemas/ - Pydantic models that define what the API accepts and returns.

Models (app/models) describe database tables; schemas describe JSON.
Keeping them separate means a column like `hashed_password` can never
leak into a response by accident.

    auth.py      -> login token response
    user.py      -> register request and user profile response
    category.py  -> category create / update / response
    expense.py   -> expense create / update / response and the paginated list
    report.py    -> spending summary responses
"""
```

- `"""` ... `"""` - three double quotes open and close a multi-line string. A
  string that is the first thing in a file is the **module docstring**. Python
  keeps it in `app.schemas.__doc__` and otherwise ignores it.
- `schemas/ - Pydantic models that define what the API accepts and returns.` -
  the one-line job of the folder. "Pydantic models" is Pydantic's own word for
  these classes; in this project we call them *schemas* to avoid mixing them up
  with the SQLAlchemy *models* in `app/models/`.
- `Models (app/models) describe database tables; schemas describe JSON.` - the
  key rule of the folder, explained above.
- `Keeping them separate means a column like hashed_password can never leak
  into a response by accident.` - the safety reason for the rule. If routers
  returned SQLAlchemy objects with no response schema, every column, including
  the hash, would be sent to the client.
- `auth.py -> login token response` ... `report.py -> spending summary
  responses` - a table of contents of the folder: which file holds which schemas.

**Why it is here:** so the next developer understands the folder without
opening every file.

**If you removed or changed it:** nothing changes at runtime. If you deleted
the whole file, `app/schemas/` would stop being a regular package and every
`from app.schemas.user import ...` line in the routers would fail with
`ModuleNotFoundError` on older Python versions (newer Python treats a folder
without `__init__.py` as a "namespace package" and the imports would still
work, but it is the convention to keep the file).

### Compared to your old code

Your old project had no `schemas/` folder. All schemas lived in one file,
`app/schema.py` (singular). That is fine for a small project. The new project
has one file per topic because the schemas grew to 14 classes; a single file
would be about 200 lines and you would scroll a lot to find the one you need.
There is no old equivalent of this `__init__.py`.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| package | a folder with an `__init__.py` that Python can import |
| module docstring | the string at the very top of a file; documentation only |
| schema | a Pydantic class that describes the shape of JSON |
| model | a SQLAlchemy class that describes a database table |

---

## File: app/schemas/auth.py

### What this file is for

This file holds one small class, `Token`. It describes the JSON that
`POST /auth/login` returns: the access token and the word `bearer`. The router
in `app/routers/auth.py` uses it twice: as `response_model=Token` on the login
endpoint, and as `return Token(access_token=...)` inside the function.

Who imports it: `app/routers/auth.py` (`from app.schemas.auth import Token`).

What it imports: `BaseModel` from Pydantic.

### The whole file

```python
"""Schemas for authentication responses."""

from pydantic import BaseModel


class Token(BaseModel):
    """Returned by POST /auth/login. Send it back as `Authorization: Bearer <token>`."""

    access_token: str
    token_type: str = "bearer"
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""Schemas for authentication responses."""
```

- `"""..."""` - the module docstring (see the `__init__.py` section).
- `Schemas for authentication responses.` - tells you the file only has
  *response* schemas. The login *request* is not a JSON body; it is an HTML
  form (`OAuth2PasswordRequestForm`, explained in doc 04), so it needs no
  schema here.

**Why it is here:** documentation.

**If you removed or changed it:** nothing changes at runtime.

### Block 2: import BaseModel

```python
from pydantic import BaseModel
```

- `from` - Python keyword: take a name out of a module.
- `pydantic` - the Pydantic library (installed from `requirements.txt`). It
  validates data and converts it between JSON and Python.
- `import` - Python keyword: load the name into this file.
- `BaseModel` - the Pydantic base class. A class that inherits from it gets,
  for free: a constructor that checks every field, `.model_dump()` (turn the
  object into a `dict`), `.model_dump_json()` (turn it into JSON text),
  `.model_validate(...)` (build it from a `dict` or an object), and more.

**Why it is here:** `Token` must inherit from `BaseModel` to be a schema.

**If you removed or changed it:** the next `class Token(BaseModel):` line would
fail with `NameError: name 'BaseModel' is not defined` the moment the file is
imported, so the whole app would fail to start.

### Block 3: the Token class header

```python
class Token(BaseModel):
    """Returned by POST /auth/login. Send it back as `Authorization: Bearer <token>`."""
```

- `class` - Python keyword: define a new type.
- `Token` - the name of the new type. Capitalised, as Python classes usually are.
- `(BaseModel)` - the parentheses after a class name list the **parent
  class**: `Token` *inherits from* `BaseModel`, so it gets everything
  `BaseModel` has.
- `:` - starts the body of the class. Everything indented under it belongs
  to the class.
- `"""Returned by POST /auth/login. ..."""` - the **class docstring**. The
  first string inside a class body is documentation for that class. It says
  which endpoint returns this shape, and how the client must use it: put the
  token in the `Authorization` header as `Bearer <token>` on every later
  request. (FastAPI also shows this docstring in the `/docs` page.)

**Why it is here:** the login endpoint needs a fixed, documented response
shape so that clients (and Swagger UI) know exactly what they get.

**If you removed or changed it:** `app/routers/auth.py` would fail at import
(`ImportError: cannot import name 'Token'`), so the app would not start.

### Block 4: access_token

```python
    access_token: str
```

- `access_token` - the name of the field, and therefore the key in the JSON:
  `{"access_token": "..."}`. The name is not random: the OAuth2 standard says
  a token response has a key called exactly `access_token`, and Swagger UI's
  "Authorize" button looks for that key.
- `:` - inside a class body, `name: type` is a **type annotation**: "this
  attribute has this type". Pydantic reads these annotations to build the
  field.
- `str` - the Python string type. The value must be text (the JWT, which is a
  long text like `eyJhbGciOi...`).
- There is **no `= default`**, so the field is **required**. Verified:
  `Token()` raises a `ValidationError` with `"type": "missing"`,
  `"msg": "Field required"`.

**Why it is here:** this is the whole point of logging in - the client gets a
token to prove who it is on later requests.

**If you removed or changed it:** the login router still calls
`Token(access_token=...)`. Pydantic ignores keys that are not fields (that is
the default; verified in the register example later, where an extra
`"hashed_password"` key in the body is silently dropped). So there would be
no error: the login response would just be `{"token_type": "bearer"}` with no
token, and no client could log in.

### Block 5: token_type with a default

```python
    token_type: str = "bearer"
```

- `token_type` - the field name / JSON key. Also fixed by the OAuth2 standard.
- `: str` - must be text.
- `=` - gives the field a **default value**. A field with a default is
  **optional** when you build the object: you may leave it out.
- `"bearer"` - the default. "Bearer" is the OAuth2 word for "whoever *bears*
  (carries) this token is allowed in". The login router never passes
  `token_type`; it just writes `Token(access_token=create_access_token(user.id))`
  and Pydantic fills in `"bearer"`. Verified:
  `Token(access_token="abc").model_dump()` gives
  `{'access_token': 'abc', 'token_type': 'bearer'}`.

**Why it is here:** the token type is always the same, so writing it once here
is safer than repeating the string in every place a token is returned.

**If you removed or changed it:** if you removed the `= "bearer"` default,
`Token(access_token=...)` in the router would raise `ValidationError`
(`token_type` is missing) and every login would answer 500. If you changed the
string to, say, `"Bearer"`, the response would still work for most clients
(the header value is matched case-insensitively), but it would no longer match
what the standard and Swagger UI expect, so I would leave it lowercase.

### Compared to your old code

Your old `app/schema.py` had:

```python
class Token(BaseModel):
    access_token : str
    token_type : str 

class TokenData(BaseModel):
    id : Optional[int] = None
```

and your old login endpoint ended with:

```python
    return {"access_token": access_token, "token_type":"bearer"}
```

What is different, and why:

1. **`token_type` has a default now.** In the old code it was required, so the
   router had to spell out `"token_type": "bearer"` itself. With the default,
   the router only passes the token.
2. **The old login did not use the schema at all.** The old `@router.post("/")`
   had no `response_model`, and the function returned a plain `dict`. The
   `Token` class existed but nothing used it, so Swagger UI could not document
   the response, and a typo in the dict key (say `"acces_token"`) would go
   unnoticed. The new router has `response_model=Token` and returns a
   `Token(...)` object, so the shape is checked every time.
3. **`TokenData` is gone.** The old code wrapped the user id from the JWT in a
   `TokenData` object (`TokenData(id=user_id)`) and then read `token.id`. The
   new `decode_access_token` (doc 04) returns the `int` directly, so a wrapper
   class adds nothing. `Optional[int]` there meant "an `int` or `None`"; the
   new project writes that as `int | None` (explained in the user.py section).
4. **Spacing.** The old file wrote `access_token : str` with a space before
   the colon. It works, but the usual Python style is `access_token: str`
   (no space before, one space after). Tools like `black` format it that way.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `BaseModel` | Pydantic base class; inherit from it to get validation and JSON conversion |
| field | one `name: type` line inside a `BaseModel` class |
| required field | a field with no default; missing it gives "Field required" |
| default value | the value used when the field is not given |
| class docstring | the first string in a class body; documentation (shown in `/docs`) |
| bearer token | a token that grants access to whoever sends it in the `Authorization` header |

---

## File: app/schemas/user.py

### What this file is for

This file defines the two JSON shapes about a user: `UserCreate`, the body a
client sends to `POST /auth/register`, and `UserResponse`, what the API returns
whenever it shows a user (after registering, and on `GET /users/me`). It also
defines a reusable string type, `FullName`, with the rules for a person's name.
It is the first file in this folder that uses `Annotated`, `StringConstraints`,
`EmailStr`, `Field` and `ConfigDict`, so this section explains those in full;
the later files reuse them.

Who imports it: `app/routers/auth.py` (`UserCreate`, `UserResponse`) and
`app/routers/users.py` (`UserResponse`).

What it imports: `datetime` from the standard library, `Annotated` from
`typing`, and five names from Pydantic.

### The whole file

```python
"""Schemas for user registration and profile responses."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

FullName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class UserCreate(BaseModel):
    """Body of POST /auth/register."""

    email: EmailStr
    full_name: FullName
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Public view of a user. Deliberately has no password field."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    created_at: datetime
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""Schemas for user registration and profile responses."""
```

- `"""..."""` - module docstring.
- `Schemas for user registration and profile responses.` - the two jobs of the
  file: the register request, and the user profile response.

**Why it is here:** documentation.

**If you removed or changed it:** nothing changes at runtime.

### Block 2: import datetime

```python
from datetime import datetime
```

- `from datetime import` - take a name out of the standard-library module
  `datetime` (a module about dates and times; part of Python, nothing to
  install).
- `datetime` - a class inside that module with the same name as the module. A
  `datetime` object holds a date **and** a time (year, month, day, hour,
  minute, second, microsecond, and optionally a timezone).

**Why it is here:** `UserResponse.created_at` is a `datetime`. The database
column `users.created_at` is `TIMESTAMP WITH TIME ZONE` (doc 06), and
SQLAlchemy hands it to Python as a `datetime` object. Pydantic turns it into
ISO text in JSON, for example `"2026-10-06T11:51:59"`.

**If you removed or changed it:** the line `created_at: datetime` would raise
`NameError: name 'datetime' is not defined` at import, and the app would not
start.

### Block 3: import Annotated

```python
from typing import Annotated
```

- `from typing import` - take a name out of `typing`, the standard-library
  module for type hints.
- `Annotated` - a special tool for type hints. `Annotated[T, extra1, extra2]`
  means: "the type is `T`, **and** here is some extra information attached to
  it". Python itself ignores the extras; it treats the whole thing as `T`.
  But libraries can read the extras. Pydantic reads them and turns them into
  validation rules. You will see the exact use in Block 5.

**Why it is here:** `FullName` (Block 5) is built with `Annotated`.

**If you removed or changed it:** Block 5 would raise
`NameError: name 'Annotated' is not defined` at import.

### Block 4: import from pydantic

```python
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
```

- `from pydantic import` - take several names out of Pydantic.
- `BaseModel` - the base class for every schema (explained in auth.py).
- `,` - commas separate the names in one import line.
- `ConfigDict` - a helper for writing the **settings** of a schema class. You
  write `model_config = ConfigDict(setting=value, ...)` inside the class and
  Pydantic reads it. Explained in Block 11.
- `EmailStr` - a Pydantic type that means "a string that must be a valid email
  address". Explained in Block 7.
- `Field` - a function that attaches rules (minimum length, maximum, default,
  description, ...) to one field. Explained in Block 9.
- `StringConstraints` - a small object that holds rules for a string (strip
  spaces, min length, max length, ...). It is used inside `Annotated`.
  Explained in Block 5.

**Why it is here:** all five names are used below.

**If you removed or changed it:** the first missing name would raise
`NameError` at import.

### Block 5: the FullName reusable type

```python
FullName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
```

- `FullName` - a new name at module level (not inside a class). It is a
  **type alias**: a name that stands for a type, so the type can be reused
  without copying the rules. Capitalised because it names a type.
- `=` - assignment: "from now on, `FullName` means the thing on the right".
- `Annotated[` - start of an `Annotated` expression. The square brackets `[ ]`
  after `Annotated` are **subscription**: the same brackets you use for
  `my_list[0]`, but here they hand parameters to a type.
- `str` - the first thing inside the brackets is the real type: a string.
- `,` - separates the real type from the extra information.
- `StringConstraints(` - creates a `StringConstraints` object. The round
  brackets `( )` **call** it, like calling a function. Each argument inside is
  one rule.
- `strip_whitespace=True` - rule 1: remove spaces, tabs and newlines from the
  **start and end** of the string before anything else. `"  Shivam Rawat "`
  becomes `"Shivam Rawat"`. Spaces in the middle are kept. Verified.
- `,` - separates arguments.
- `min_length=1` - rule 2: after stripping, the string must have at least one
  character. So `"   "` (only spaces) is rejected: it strips to `""`, which
  has length 0. Verified: the error is `"String should have at least 1
  character"`, type `string_too_short`. The order matters - strip first, then
  count - and that is the order Pydantic uses (verified with `"    "`).
- `max_length=100` - rule 3: at most 100 characters. This matches the
  database column `full_name VARCHAR(100)` (doc 06), so a too-long name is
  rejected with a clean 422 instead of a database error.
- `)` - closes the `StringConstraints(...)` call.
- `]` - closes `Annotated[...]`.
- The line break after `Annotated[` and the indentation are only formatting
  (the line would be too long otherwise). Python allows line breaks inside
  brackets.

So `FullName` means: "a `str`, stripped, 1 to 100 characters". Any field that
says `: FullName` gets all three rules.

**Why it is here:** the rules are written once and given a name. `UserCreate`
uses it now; a future `UserUpdate` schema could use the same name and the two
could never drift apart.

**If you removed or changed it:** if you wrote `full_name: str` instead, an
empty name `""` or a name of only spaces would be accepted and stored, and a
101-character name would reach PostgreSQL and fail there with a
`StringDataRightTruncation` error, which FastAPI turns into a 500. If you
changed `min_length=1` to `0`, empty names would be stored.

### Block 6: the UserCreate class header

```python
class UserCreate(BaseModel):
    """Body of POST /auth/register."""
```

- `class UserCreate(BaseModel):` - a new schema class named `UserCreate` that
  inherits from `BaseModel`. The naming pattern `<Thing>Create` means "the body
  the client sends to create a `<Thing>`".
- `"""Body of POST /auth/register."""` - class docstring: this is the JSON
  body of the register endpoint. The router declares `user_in: UserCreate` as
  a parameter, which is how FastAPI knows to read the body into this class.

**Why it is here:** the register endpoint needs a checked input shape.

**If you removed or changed it:** `app/routers/auth.py` would fail to import.

### Block 7: email

```python
    email: EmailStr
```

- `email` - field name and JSON key.
- `: EmailStr` - the type. `EmailStr` is a Pydantic type that validates an
  email address using the `email-validator` package (version 2.3.0 is
  installed; it is in `requirements.txt`). Pydantic's own docstring says: "To
  use this type, you need to install the optional email-validator package".
  Without that package, importing this file would raise an `ImportError`.
- No default, so the field is required.

What `EmailStr` does, verified:

| Input | Result |
| --- | --- |
| `"shivam@example.com"` | accepted as is |
| `"Shivam.Rawat@Example.COM"` | accepted and **normalised** to `"Shivam.Rawat@example.com"` - the domain is lowercased, the part before `@` is kept as typed |
| `"  shivam@example.com "` | accepted, spaces removed |
| `"not-an-email"` | 422: `"value is not a valid email address: An email address must have an @-sign."` |
| `"shivam@"` | 422: `"... There must be something after the @-sign."` |

Note that `EmailStr` does **not** lowercase the part before `@`. That is why the
register router does `email = user_in.email.lower()` itself before saving (doc
08), so that `Shivam@Example.COM` and `shivam@example.com` are the same
account.

**Why it is here:** a wrong email cannot be fixed later by the user (they have
no login), so it is checked at the door.

**If you removed or changed it:** with `email: str`, anything would be
accepted, including `"hello"` and `""`. The user would be created with a
useless email and could still log in with it, because login matches the text
exactly.

### Block 8: full_name

```python
    full_name: FullName
```

- `full_name` - field name and JSON key.
- `: FullName` - the reusable type from Block 5: stripped, 1 to 100 characters.
- Required (no default).

Verified: registering with `"full_name": "   "` gives 422
`"String should have at least 1 character"` with `"loc": ["body", "full_name"]`;
leaving the key out gives 422 `"Field required"`.

**Why it is here:** the `users.full_name` column is `NOT NULL`, so the API
must insist on a value.

**If you removed or changed it:** the router does
`User(..., full_name=user_in.full_name, ...)`; without this field it would
raise `AttributeError: 'UserCreate' object has no attribute 'full_name'` (a
500 response).

### Block 9: password with Field rules

```python
    password: str = Field(min_length=8, max_length=128)
```

- `password` - field name and JSON key. The plain password the user chose.
- `: str` - text.
- `= Field(` - `Field` is Pydantic's function for attaching rules or a default
  to one field. It is written in the "default" position (after `=`), but it
  does **not** give a default here, because no `default=` argument is passed.
  So the field stays **required**. This is the second way to attach rules to a
  field; `Annotated[str, StringConstraints(...)]` (Block 5) is the first. Both
  work; `Field` is shorter when the rules are used only once.
- `min_length=8` - the password must have at least 8 characters. Verified: 7
  characters gives 422 `"String should have at least 8 characters"`.
- `max_length=128` - at most 128 characters. Verified: 129 characters gives
  `"String should have at most 128 characters"`. The upper limit stops someone
  from sending a 10 MB "password" that would make Argon2 hashing slow.
- `)` - closes the call.
- No `strip_whitespace` here, on purpose: spaces are a valid part of a
  password and must not be removed.

**Why it is here:** the only place a password rule can be enforced is at
registration, before it is hashed.

**If you removed or changed it:** with `password: str`, a one-character
password would be accepted. There is no database rule to catch it, because the
database only ever sees the hash.

### Block 10: the UserResponse class header

```python
class UserResponse(BaseModel):
    """Public view of a user. Deliberately has no password field."""
```

- `class UserResponse(BaseModel):` - a new schema class. The naming pattern
  `<Thing>Response` means "what the API returns when it shows a `<Thing>`".
- `"""Public view of a user. Deliberately has no password field."""` - class
  docstring. "Public view" means: only the fields that are safe to show. The
  second sentence is the security rule of the file: a response schema lists
  the fields to show, and `hashed_password` is not in the list, so it is never
  serialised.

How this protects you: the router returns a SQLAlchemy `User` object, which
*does* have `hashed_password`. FastAPI takes `response_model=UserResponse`,
reads only `id`, `email`, `full_name`, `created_at` from that object, and
sends those. Verified: `UserResponse.model_validate(user).model_dump()` has no
`hashed_password` key, and the real `POST /auth/register` response is
`{"id": 1, "email": "shivam@example.com", "full_name": "Shivam Rawat",
"created_at": "2026-10-06T11:51:59"}`.

**Why it is here:** every endpoint that shows a user needs one agreed, safe
shape.

**If you removed or changed it:** this is the most important "what if" in the
folder, so I tested it. If you removed `response_model=UserResponse` from a
router and returned the `User` object directly, FastAPI would **not** fail. It
would convert the object attribute by attribute and send **every column**.
Verified response:
`{"id":1,"hashed_password":"HASH","created_at":"2026-10-06T11:57:24","full_name":"S","email":"a@b.com","is_active":true}`.
The password hash would be public. The schema is the only thing standing
between the database row and the client.

### Block 11: model_config with from_attributes

```python
    model_config = ConfigDict(from_attributes=True)
```

- `model_config` - a **special attribute name** that Pydantic looks for inside
  every `BaseModel` class. Whatever you assign to it becomes the class's
  settings. It is not a field (Pydantic knows to skip this name). You met the
  same idea in `app/core/config.py` with `SettingsConfigDict` (doc 03);
  `SettingsConfigDict` is the pydantic-settings version of the same thing with
  a few extra options (`env_file`, and so on).
- `=` - assignment.
- `ConfigDict(` - a call that builds the settings. Technically `ConfigDict` is
  a `TypedDict`, a plain `dict` with known keys; calling it just makes a dict
  like `{'from_attributes': True}` (verified). Its benefit is that your editor
  and type checker know the allowed keys and warn you about typos.
- `from_attributes=True` - the one setting used. Pydantic's docstring:
  "Whether to build models ... using python object attributes." With it on,
  Pydantic can build a `UserResponse` from **any object that has attributes**
  called `id`, `email`, `full_name`, `created_at` (for example a SQLAlchemy
  `User` row), by reading `obj.id`, `obj.email`, and so on. Without it,
  Pydantic only accepts a `dict` (`{"id": 1, ...}`) or another `UserResponse`.
- `)` - closes the call.

Verified behaviour:

- with the setting: `UserResponse.model_validate(user_row)` works.
- without the setting: the same call fails with
  `"Input should be a valid dictionary or instance of UserResponse"`.
- One honest detail: FastAPI itself passes `from_attributes=True` when it
  validates a `response_model` (it is in `fastapi/_compat/v2.py`,
  `validate_python(value, from_attributes=True)`). So `GET /users/me` would
  *still* work without this line. It is kept because (1) the project also
  builds response objects by hand in some routers (`ExpenseListResponse(items=rows, ...)`
  in `expenses.py`, and that path has no such help - see the expense.py
  section, where removing it really does give a 500), (2) it documents that
  this class is meant to be built from database rows, and (3) it keeps every
  response schema in the project consistent.

**Why it is here:** so a database row can be turned into this schema directly,
without writing `UserResponse(id=user.id, email=user.email, ...)` by hand.

**If you removed or changed it:** see the verified list above. The symptom
appears wherever the class is built from an object instead of a dict.

### Block 12: id

```python
    id: int
```

- `id` - field name and JSON key: the user's primary key from the `users` table.
- `: int` - a whole number. When building from a row, Pydantic checks that
  `user.id` is an `int`.
- Required.

**Why it is here:** clients need the id to refer to the user later.

**If you removed or changed it:** the response would simply not contain `id`.
No error, just missing information.

### Block 13: email in the response

```python
    email: EmailStr
```

- `email` - field name / JSON key.
- `: EmailStr` - the same email type as in `UserCreate`. In a response it acts
  as a double check: the value read from the database must still look like an
  email.

**Why it is here:** the profile shows the login email.

**If you removed or changed it:** if you wrote `str`, nothing would change in
practice (the stored value already passed `EmailStr` at registration).

### Block 14: full_name in the response

```python
    full_name: str
```

- `full_name` - field name / JSON key.
- `: str` - plain `str`, **not** `FullName`. The strip / length rules are input
  rules; on output the value already obeys them (it was checked on the way
  in), so the simpler type is enough and avoids re-stripping.

**Why it is here:** the profile shows the name.

**If you removed or changed it:** the key disappears from the response.

### Block 15: created_at

```python
    created_at: datetime
```

- `created_at` - field name / JSON key.
- `: datetime` - the class imported in Block 2. SQLAlchemy gives a `datetime`
  object; Pydantic writes it in JSON as ISO-8601 text, such as
  `"2026-10-06T11:51:59"` (with PostgreSQL's timezone-aware column the text
  also carries the timezone).

**Why it is here:** "member since" information for the client.

**If you removed or changed it:** the key disappears from the response. If
you wrote `created_at: str`, Pydantic would reject the `datetime` object with
`"Input should be a valid string"` and the endpoint would answer 500.

### Compared to your old code

Your old `app/schema.py` had:

```python
class User_Inherit(BaseModel):
    email : EmailStr


class User(User_Inherit):
    password : str


class Create_User_Response(User_Inherit):
 
    id : int
    created_at : datetime    
    model_config = ConfigDict(from_attributes=True)
```

What is the same: the idea is right. You already used `EmailStr`, you already
kept the password **out** of the response class, and you already used
`model_config = ConfigDict(from_attributes=True)` so the response could be
built from a database row. Well done on that - many beginners put the password
in the response.

What is different, and why:

1. **Names.** The old request class was called `User`, which is also the name
   of the database model. That forced `from app.model import User as user_table`
   in `routers/user.py` to avoid the clash. The new names `UserCreate` and
   `UserResponse` say what each class is for and never collide with the model
   `User`.
2. **No inheritance.** The old code shared `email` through a parent class
   `User_Inherit`. That saves one line but means you must open two classes to
   know what `User` contains. The new classes are flat: each one lists all its
   fields. Inheritance is not wrong; it is a trade-off, and for two fields
   the flat version is easier to read.
3. **Password rules.** Old: `password : str`, so `"1"` was a valid password.
   New: `Field(min_length=8, max_length=128)`.
4. **Name rules.** The old project had no name. The new `full_name` uses
   `FullName` so that blank or over-long names are rejected with a 422.
5. **`created_at` in the response is unchanged**, and `full_name` was added.
6. **`model_config` position.** The old code placed `model_config` after the
   fields. That works. The new code puts it first, so the reader sees the
   settings before the fields. Convention only.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `Annotated[T, extra]` | "type `T`, plus extra info"; Python ignores the extra, Pydantic reads it |
| `StringConstraints(...)` | the extra info for a string: strip, min/max length, pattern |
| type alias | a name (like `FullName`) that stands for a type, so rules are written once |
| `EmailStr` | a string that must be a valid email; normalises the domain to lowercase |
| `Field(...)` | attaches rules or a default to one field |
| `min_length` / `max_length` | smallest / largest allowed number of characters |
| `model_config` | the special attribute holding a schema's settings |
| `ConfigDict(...)` | builds the settings dict with checked key names |
| `from_attributes=True` | allow building the schema from an object's attributes (a database row) |
| required field | no default: the client must send it |
| 422 | the HTTP status FastAPI uses when validation fails |

---

## File: app/schemas/category.py

### What this file is for

This file defines the four JSON shapes about a category: `CategoryCreate`
(body of `POST /categories`), `CategoryUpdate` (body of `PATCH /categories/{id}`),
`CategoryResponse` (what the API returns for a category) and `CategorySummary`
(a two-field version that is nested inside each expense response). It also
defines the reusable `CategoryName` type. This is the first file that uses
`str | None`, `model_validator` and `model_fields_set`; the difference between
"a key that was not sent" and "a key sent as `null`" is explained here in full
because the whole PATCH design depends on it.

Who imports it: `app/routers/categories.py` (`CategoryCreate`,
`CategoryResponse`, `CategoryUpdate`) and `app/schemas/expense.py`
(`CategorySummary`).

What it imports: `datetime`, `Annotated`, and five names from Pydantic.

### The whole file

```python
"""Schemas for expense categories."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]


class CategoryCreate(BaseModel):
    """Body of POST /categories."""

    name: CategoryName
    description: str | None = Field(default=None, max_length=255)


class CategoryUpdate(BaseModel):
    """Body of PATCH /categories/{id}. Only the fields you send are changed."""

    name: CategoryName | None = None
    description: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def name_cannot_be_null(self) -> "CategoryUpdate":
        # Leaving `name` out is fine; sending "name": null is not.
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class CategorySummary(BaseModel):
    """Small version of a category, nested inside expense responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""Schemas for expense categories."""
```

- `"""..."""` - module docstring.
- `Schemas for expense categories.` - the topic of the file.

**Why it is here:** documentation.

**If you removed or changed it:** nothing changes at runtime.

### Block 2: import datetime

```python
from datetime import datetime
```

- `from datetime import datetime` - the date-and-time class, exactly as in
  user.py Block 2.

**Why it is here:** `CategoryResponse.created_at` is a `datetime`.

**If you removed or changed it:** `NameError` at import.

### Block 3: import Annotated

```python
from typing import Annotated
```

- `from typing import Annotated` - the "type plus extra info" tool, exactly as
  in user.py Block 3.

**Why it is here:** `CategoryName` (Block 5) is built with it.

**If you removed or changed it:** `NameError` at import.

### Block 4: import from pydantic

```python
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
```

- `BaseModel`, `ConfigDict`, `Field`, `StringConstraints` - explained in
  user.py Block 4.
- `model_validator` - new. It is a **decorator** (explained in Block 12) that
  marks a method as "a check that runs on the whole object, after all the
  individual fields have been checked". You use it when a rule involves more
  than one field, or involves *how* the data was given (which keys were
  present), which is exactly the case in `CategoryUpdate`.

**Why it is here:** all five names are used below.

**If you removed or changed it:** the first missing name gives `NameError` at
import.

### Block 5: the CategoryName reusable type

```python
CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]
```

- `CategoryName` - a type alias, like `FullName` in user.py.
- `= Annotated[str, StringConstraints(...)]` - a `str` with rules.
- `strip_whitespace=True` - remove spaces at both ends. Verified:
  `"  Food  "` becomes `"Food"`.
- `min_length=1` - not empty after stripping. Verified: `"   "` gives 422
  `"String should have at least 1 character"`.
- `max_length=50` - matches the `categories.name VARCHAR(50)` column.
  Verified: 51 characters gives `"String should have at most 50 characters"`.

**Why it is here:** `CategoryCreate.name` and `CategoryUpdate.name` must obey
exactly the same rules. One alias guarantees that.

**If you removed or changed it:** with plain `str`, a category named `""` or
`"   "` could be created, and `"  Food"` and `"Food"` would be two different
categories (the uniqueness check in the router compares the stripped,
lowercased text, but the stored text would still have the spaces).

### Block 6: the CategoryCreate class header

```python
class CategoryCreate(BaseModel):
    """Body of POST /categories."""
```

- `class CategoryCreate(BaseModel):` - the create-body schema.
- `"""Body of POST /categories."""` - which endpoint reads it. The router does
  `Category(**category_in.model_dump(), owner_id=current_user.id)`: every field
  of this class becomes a keyword argument of the model. So the field names
  here must match the column names in `app/models/category.py`.

**Why it is here:** the create endpoint needs a checked input.

**If you removed or changed it:** `app/routers/categories.py` fails to import.

### Block 7: name

```python
    name: CategoryName
```

- `name` - field / JSON key.
- `: CategoryName` - the alias from Block 5. Required.

**Why it is here:** a category without a name makes no sense, and the column
is `NOT NULL`.

**If you removed or changed it:** `Category(**category_in.model_dump(), ...)`
would create a row with no `name`, and PostgreSQL would reject the INSERT
(`NOT NULL` violation, a 500).

### Block 8: description, optional with a limit

```python
    description: str | None = Field(default=None, max_length=255)
```

- `description` - field / JSON key.
- `: str | None` - the type. The vertical bar `|` between two types means
  **"either this or that"**: the value may be a `str` **or** `None`. `None` is
  Python's "no value"; in JSON it is `null`. This syntax exists since Python
  3.10. The older spelling is `Optional[str]` from the `typing` module, which
  your old project used; the two are exactly the same thing. Verified:
  `Optional[int] == (int | None)` is `True`, and Python even prints
  `Optional[int]` as `int | None`.
- `= Field(` - attach a default and a rule.
- `default=None` - the default value when the key is not sent. Because of the
  default, the field is **optional to send**.
- `,` - separates the arguments.
- `max_length=255` - at most 255 characters, matching
  `categories.description VARCHAR(255)`. The rule is applied only when the
  value is a string; `None` is passed through untouched. Verified: `None` is
  accepted, 256 characters gives 422 `"String should have at most 255
  characters"`.
- `)` - closes the call.

An important point that trips many people: `| None` and `default=None` are
**two separate things**. `| None` says "`null` is an allowed *value*".
`default=None` says "the *key* may be left out". A field can have one without
the other, and you will see such a field in Block 22.

**Why it is here:** a description is a nice-to-have, so the client may skip it
or send `null`, but a 10,000-character description must not reach the
database.

**If you removed or changed it:** if you wrote `description: str | None = None`
(dropping `Field`), a too-long description would pass validation and fail in
PostgreSQL with a 500. If you dropped `= Field(default=None, ...)` entirely,
the key would become required and `{"name": "Food"}` would be rejected with
`"Field required"`.

### Block 9: the CategoryUpdate class header

```python
class CategoryUpdate(BaseModel):
    """Body of PATCH /categories/{id}. Only the fields you send are changed."""
```

- `class CategoryUpdate(BaseModel):` - the update-body schema. The naming
  pattern `<Thing>Update` means "the body of `PATCH`".
- `"""Body of PATCH /categories/{id}. Only the fields you send are changed."""`
  - class docstring. The second sentence is the contract of a PATCH: it is a
  *partial* update. If you send `{"description": "Groceries"}`, only the
  description changes; the name stays as it was.

**Why it is here:** a separate class is needed because in a PATCH *every*
field is optional, whereas in a POST `name` is required. One class cannot be
both.

**If you removed or changed it:** if you reused `CategoryCreate` for PATCH,
`name` would be required on every update, so renaming would be the only kind
of update possible, and the description could never be changed on its own.

### Block 10: optional name

```python
    name: CategoryName | None = None
```

- `name` - field / JSON key.
- `: CategoryName | None` - the alias **or** `None`. You can put `| None`
  after an `Annotated` alias; Pydantic understands it. Verified: Python shows
  it as `Annotated[str, StringConstraints(...)] | None`, and
  `CategoryUpdate(name=" Food ").name` is `"Food"` (the rules still apply).
- `= None` - default `None`, so the key may be left out.

So far this says: "name may be missing, may be `null`, or may be a valid
name". The next blocks remove the `null` option again, with a reason.

**Why it is here:** the client must be allowed to send a PATCH without `name`.

**If you removed or changed it:** without `= None`, every PATCH would need a
`name`.

### Block 11: optional description

```python
    description: str | None = Field(default=None, max_length=255)
```

- identical to Block 8, and it means the same: optional, nullable, at most
  255 characters.

Here `null` is a **meaningful value**: "clear the description". Verified:
`PATCH /categories/1` with `{"description": null}` answers 200 and the
response shows `"description": null`.

**Why it is here:** a client must be able to remove a description.

**If you removed or changed it:** same as Block 8.

### Block 12: the model_validator decorator

```python
    @model_validator(mode="after")
```

- `@` - the **decorator** symbol. A line starting with `@` directly above a
  `def` means: "take the function defined below, pass it to the thing after
  `@`, and use whatever comes back instead". It is a way to wrap or register a
  function. You have used `@router.post(...)` in FastAPI: that is a decorator
  that registers your function as an endpoint. Here the decorator registers
  the method as a validator.
- `model_validator` - the Pydantic function imported in Block 4. "model"
  (Pydantic's word for the whole class) means the check looks at the **whole
  object**, not one field.
- `(mode="after")` - the one argument. `"after"` means: run **after** all
  fields have been validated and the object has been built. Inside the method,
  `self` is the finished object and `self.name` already holds the stripped,
  checked value. The other modes are `"before"` (gets the raw input dict
  before any checking) and `"wrap"` (gets both); `"after"` is the simplest and
  is enough here.

A verified detail about ordering: if a *field* fails, the after-validator does
not run at all. `ExpenseUpdate(title=None, amount="-1")` (same pattern, next
file) reports only the `amount` error, because field errors stop the process
before the model validator. You will only ever see one of the two kinds of
error at a time.

**Why it is here:** the rule "name may be missing but may not be `null`"
cannot be written as a type. A type can say "str or None" or "str"; it cannot
say "str, or absent". Only a validator that can see *which keys were sent*
can express it.

**If you removed or changed it:** without the decorator, `name_cannot_be_null`
would be an ordinary method that nobody calls, and `{"name": null}` would be
accepted. The router would then see `"name"` in the changes and call
`ensure_category_name_is_unique(db, ..., changes["name"], ...)`, which does
`name.lower()` on `None` and crashes with `AttributeError: 'NoneType' object
has no attribute 'lower'` - a 500 instead of a clean 422. (And if that check
were not there, PostgreSQL would reject the UPDATE because `name` is
`NOT NULL`, also a 500.)

### Block 13: the validator method header

```python
    def name_cannot_be_null(self) -> "CategoryUpdate":
```

- `def` - Python keyword: define a function. Inside a class it is a **method**.
- `name_cannot_be_null` - the method name. Pydantic does not care what it is
  called; it only matters for readability and for error tracebacks. The name
  states the rule.
- `(self)` - the one parameter. In an `"after"` validator, `self` is the
  fully built `CategoryUpdate` object.
- `->` - the **return type arrow**: what comes after it is the type of the
  value the function returns.
- `"CategoryUpdate"` - the return type, written as a **string**. Why a string?
  Because at this exact moment Python is still in the middle of executing the
  class body; the name `CategoryUpdate` does not exist yet, so writing it bare
  would raise `NameError`. A quoted type name is called a **forward
  reference**; Python and type checkers resolve it later. (A validator in
  `"after"` mode must return the object, so the return type is the class
  itself.)
- `:` - starts the method body.

**Why it is here:** this is the function the decorator registers.

**If you removed or changed it:** if you forgot the quotes and wrote
`-> CategoryUpdate`, the file would fail at import with
`NameError: name 'CategoryUpdate' is not defined`.

### Block 14: the explaining comment

```python
        # Leaving `name` out is fine; sending "name": null is not.
```

- `#` - starts a comment; Python ignores the rest of the line.
- `Leaving name out is fine; sending "name": null is not.` - the rule in one
  line. "Leaving out" = the key is absent from the JSON. "Sending null" = the
  key is present with the value `null`.

**Why it is here:** the next line is subtle; the comment says what it means.

**If you removed or changed it:** nothing changes at runtime.

### Block 15: the check

```python
        if "name" in self.model_fields_set and self.name is None:
```

- `if` - Python keyword: run the indented block only when the condition is
  true.
- `"name"` - the field name, as a string.
- `in` - membership test: "is this item inside that collection?"
- `self.model_fields_set` - a **set** (an unordered collection of unique
  items) that Pydantic fills on every object: the names of the fields that
  were **explicitly given** when the object was built. Fields that got their
  default because the key was absent are **not** in it. This is how Pydantic
  remembers the difference between "not sent" and "sent as `null`".
- `and` - both sides must be true.
- `self.name` - the value of the `name` field after validation.
- `is None` - `is` compares identity; `x is None` is the correct way to ask
  "is x the `None` object?".
- `:` - starts the block.

Put together: "the client sent a `name` key, **and** its value is `null`".

Here is what `model_fields_set` contains for different JSON bodies (verified):

| JSON body sent to PATCH | `model_fields_set` | `model_dump(exclude_unset=True)` | Result |
| --- | --- | --- | --- |
| `{}` | `set()` (empty) | `{}` | 200, nothing changes |
| `{"description": null}` | `{'description'}` | `{'description': None}` | 200, description cleared |
| `{"name": "Food"}` | `{'name'}` | `{'name': 'Food'}` | 200, renamed |
| `{"name": null}` | `{'name'}` | (never reached) | 422 `"Value error, name cannot be null"` |

Note that for `{}`, `model_dump()` without `exclude_unset` would give
`{'name': None, 'description': None}` - the defaults. That is why the router
uses `model_dump(exclude_unset=True)`: it gives back **only the keys the
client sent**, so the loop `for field_name, value in changes.items():
setattr(category, field_name, value)` touches only those columns. The schema
(this file) and the router (doc 08) are two halves of the same design.

**Why it is here:** `name` is `NOT NULL` in the database, so `null` must be
refused, but an absent key must be allowed. Only `model_fields_set` can tell
the two apart, because after validation both cases have `self.name is None`.

**If you removed or changed it:** if you wrote just `if self.name is None:`,
then `{}` and `{"description": "x"}` would also fail, because `name` is `None`
by default in both. Every PATCH would have to include a name. That is the
exact trap the comment warns about.

### Block 16: raise the error

```python
            raise ValueError("name cannot be null")
```

- `raise` - Python keyword: throw an exception; stop here.
- `ValueError` - a built-in exception type meaning "the value is wrong".
  Pydantic has a rule: a `ValueError` (or `AssertionError`) raised inside a
  validator is **caught and turned into a `ValidationError`**, with the
  message included. Any other exception type would crash through as a 500.
- `("name cannot be null")` - the message text. Verified HTTP response for
  `PATCH /categories/1` with `{"name": null}`:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, name cannot be null",
      "input": {"name": null},
      "ctx": {"error": {}}
    }
  ]
}
```

  Notice `"loc": ["body"]` and not `["body", "name"]`: a model validator
  belongs to the whole object, so Pydantic cannot point at one field. The
  message makes up for that by naming the field.

**Why it is here:** turn a bad request into a clear 422.

**If you removed or changed it:** if you raised `TypeError` or
`HTTPException` here instead, Pydantic would not catch it and the client would
get a 500.

### Block 17: return self

```python
        return self
```

- `return` - Python keyword: leave the function and hand back a value.
- `self` - the object itself, unchanged.

In an `"after"` validator the value you return **becomes the result of
validation**. You could return a modified object; here nothing is modified,
so the same object goes back.

**Why it is here:** Pydantic requires it.

**If you removed or changed it:** the method would return `None`. Verified:
Pydantic prints a warning ("A custom validator is returning a value other than
`self`") and `CategoryUpdate.model_validate({...})` returns **`None`** instead
of an object. FastAPI uses that same validation path for the body, so the
router would receive `category_in = None` and crash on
`category_in.model_dump(...)` with `AttributeError` (a 500) on every PATCH.

### Block 18: the CategoryResponse class header

```python
class CategoryResponse(BaseModel):
```

- `class CategoryResponse(BaseModel):` - the response schema for one category.
  No docstring; the name says enough.

**Why it is here:** `POST`, `GET` (one and list) and `PATCH` on `/categories`
all return this shape, via `response_model=CategoryResponse` and
`response_model=list[CategoryResponse]`.

**If you removed or changed it:** `app/routers/categories.py` fails to import.

### Block 19: model_config

```python
    model_config = ConfigDict(from_attributes=True)
```

- exactly as in user.py Block 11: allow building the schema from a SQLAlchemy
  `Category` row by reading its attributes.

**Why it is here:** the router returns `Category` rows.

**If you removed or changed it:** the routers would still work for the reason
explained in user.py Block 11 (FastAPI passes `from_attributes=True` itself),
but direct `CategoryResponse.model_validate(row)` calls would fail.

### Block 20: id

```python
    id: int
```

- `id: int` - the primary key. Required.

**Why it is here:** clients use it in `/categories/{id}` and as `category_id`
when creating an expense.

**If you removed or changed it:** the key disappears from responses and
clients could not refer to the category.

### Block 21: name

```python
    name: str
```

- `name: str` - plain `str` on output, for the same reason as `full_name` in
  user.py: the rules were applied on the way in.

**Why it is here:** the name is the main thing to show.

**If you removed or changed it:** the key disappears from responses.

### Block 22: description, nullable but required

```python
    description: str | None
```

- `description` - field / JSON key.
- `: str | None` - a string or `null`.
- **No default.** Compare with Block 8: there, `= Field(default=None, ...)`
  made the key optional *to send*. Here there is no default, so the field is
  **required**: whoever builds a `CategoryResponse` must supply a value for
  `description` - but that value is allowed to be `None`. Verified:
  `CategoryResponse(id=1, name="Food", created_at=...)` with no `description`
  raises `"Field required"`; with `description=None` it works and the JSON
  shows `"description": null`.

This is the right choice for a response: a database row **always** has a
`description` attribute (possibly `NULL`), so there is never a reason to leave
it out, and making it required means a bug that forgot it would be caught.

**Why it is here:** show the description, or `null` when there is none.

**If you removed or changed it:** if you wrote `description: str` (no
`| None`), every category without a description would fail to serialise:
`"Input should be a valid string"` on the `None` value, and the endpoint would
answer 500.

### Block 23: created_at

```python
    created_at: datetime
```

- `created_at: datetime` - as in user.py Block 15.

**Why it is here:** when the category was created.

**If you removed or changed it:** the key disappears from responses.

### Block 24: the CategorySummary class header

```python
class CategorySummary(BaseModel):
    """Small version of a category, nested inside expense responses."""
```

- `class CategorySummary(BaseModel):` - a second, smaller response schema for
  a category.
- `"""Small version of a category, nested inside expense responses."""` -
  class docstring. "Nested" means this object appears **inside** another
  JSON object: every expense response has a `"category": {"id": 3, "name":
  "Food"}` part (or `"category": null`). That part is a `CategorySummary`.

**Why it is here:** when you list 100 expenses, you do not want each one to
carry the category's `description` and `created_at` as well; `id` and `name`
are enough to show a label and to link to the full category. A separate small
schema says exactly that.

**If you removed or changed it:** `app/schemas/expense.py` would fail to
import. If you replaced it with `CategoryResponse` inside `ExpenseResponse`,
everything would still work; responses would just be bigger.

### Block 25: model_config

```python
    model_config = ConfigDict(from_attributes=True)
```

- as before. This one matters in practice: `ExpenseResponse` is built from an
  `Expense` row whose `.category` attribute is a `Category` row (or `None`),
  and Pydantic must be allowed to read `category.id` and `category.name` from
  that nested object. Verified: with the setting, building an
  `ExpenseResponse` from an expense object gives
  `"category": {"id": 3, "name": "Food"}` and nothing else from the category.

**Why it is here:** nested rows must be readable by attribute too.

**If you removed or changed it:** `ExpenseListResponse(items=rows, ...)` in
`expenses.py` would fail for every expense that has a category:
`"Input should be a valid dictionary or instance of CategorySummary"` (a 500).

### Block 26: id

```python
    id: int
```

- `id: int` - the category's id. Required.

**Why it is here:** so a client can fetch the full category or filter
expenses by it.

**If you removed or changed it:** the nested object would have only a name.

### Block 27: name

```python
    name: str
```

- `name: str` - the category's name. Required.

**Why it is here:** so a client can show the label without a second request.

**If you removed or changed it:** the nested object would have only an id.

### Compared to your old code

Your old project had no categories, so there is no direct equivalent. The
closest pattern is your post schemas:

```python
class PostBase(BaseModel):
    title: str
    content: str
    published: bool = True

class CreatePost(PostBase):
    pass

class Post(PostBase):
    id: int
    created_at : datetime
    owner_id : int
    owner : Create_User_Response
    class Config:
        from_attributes = True
```

and the old update endpoint:

```python
@router.put("/{id}",response_model=ResponsePost)
def update_post(id: int, updated_post: PostBase, ...):
    ...
    get_post.update(updated_post.model_dump(), synchronize_session = False)
```

What is different, and why:

1. **There was no Update schema.** The old PUT used `PostBase`, the same class
   as create. So every update had to send `title` **and** `content`; a client
   that only wanted to change the title got a 422. Worse, `published` had a
   default of `True`, so an update body that left out `published` silently
   set it back to `True` even if the post had been unpublished - because
   `model_dump()` (without `exclude_unset`) includes defaults. The new
   `CategoryUpdate` + `model_fields_set` + `exclude_unset=True` design is the
   fix for exactly that bug. Please do not feel bad about it: it is the most
   common mistake in FastAPI update endpoints, and the fix needs a Pydantic
   feature that is easy to miss.
2. **`class Config` is the old style.** `class Config: from_attributes = True`
   still works in Pydantic 2, but it is deprecated. Verified warning when you
   define such a class: `PydanticDeprecatedSince20: Support for class-based
   config is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0
   to be removed in V3.0.` The new project uses `model_config = ConfigDict(...)`
   everywhere. (Your old file actually mixed both styles: `Create_User_Response`
   used `ConfigDict`, `Post` used `class Config`.)
3. **No length rules.** `title: str` accepted an empty title. The new
   `CategoryName` alias rejects empty and over-long names.
4. **Nested object.** Your old `Post` already nested `owner: Create_User_Response`,
   which is the same idea as `category: CategorySummary` in the next file. The
   new code adds a purpose-built small schema instead of reusing the full one.
5. **`CreatePost(PostBase): pass`** - an empty subclass only to have a
   different name. The new code does not need that trick because each class
   lists its own fields.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `str \| None` | the value may be a `str` or `None` (`null` in JSON); same as `Optional[str]` |
| `default=None` | the key may be left out of the JSON; different from allowing `null` |
| required but nullable | no default (must be given) but `None` is an allowed value |
| decorator (`@`) | a line above `def` that wraps or registers the function |
| `@model_validator(mode="after")` | run this method on the whole object after field validation |
| forward reference | a type name written as a string because the class is not defined yet |
| `model_fields_set` | the set of field names the client actually sent |
| unset vs null | key absent (not in `model_fields_set`) vs key present with `null` |
| `model_dump(exclude_unset=True)` | a dict with only the fields that were sent |
| `ValueError` in a validator | becomes a 422 `value_error` with your message |
| `return self` | required at the end of an after-validator |
| nested schema | a schema used as the type of a field inside another schema |
| `class Config` | the Pydantic 1 way to set options; deprecated, use `ConfigDict` |

---

## File: app/schemas/expense.py

### What this file is for

This is the largest schema file. It defines the JSON shapes about an expense:
`ExpenseCreate` (body of `POST /expenses`), `ExpenseUpdate` (body of
`PATCH /expenses/{id}`), `ExpenseResponse` (one expense, with its category
nested inside) and `ExpenseListResponse` (one page of expenses plus the
numbers a client needs for pagination). It also defines two reusable types:
`ExpenseTitle` and `MoneyAmount`. New things explained here: `Decimal` for
money, `max_digits` / `decimal_places`, `use_enum_values`, `validate_default`,
`default_factory`, a `for` loop inside a validator with `getattr`, a nested
schema, and `list[...]`.

Who imports it: `app/routers/expenses.py` (all four classes).

What it imports: `date` and `datetime`, `Decimal`, `Annotated`, five Pydantic
names, the `PaymentMethod` enum from `app/models/expense.py`, and
`CategorySummary` from `app/schemas/category.py`.

### The whole file

```python
"""
Schemas for expenses.

Amounts are `Decimal`, never `float`, so 0.1 + 0.2 style rounding errors
cannot creep into money. In JSON responses they appear as strings ("250.00").
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.expense import PaymentMethod
from app.schemas.category import CategorySummary

ExpenseTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
# Matches the Numeric(12, 2) column: positive, at most 2 decimal places.
MoneyAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class ExpenseCreate(BaseModel):
    """Body of POST /expenses."""

    # Store "cash" (the plain string) instead of the PaymentMethod enum object.
    model_config = ConfigDict(use_enum_values=True)

    title: ExpenseTitle
    amount: MoneyAmount
    # Defaults to today when the client does not send a date.
    expense_date: date = Field(default_factory=date.today)
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.CASH, validate_default=True
    )
    notes: str | None = Field(default=None, max_length=1000)
    # Leave out (or send null) for an uncategorized expense.
    category_id: int | None = None


class ExpenseUpdate(BaseModel):
    """Body of PATCH /expenses/{id}. Only the fields you send are changed."""

    model_config = ConfigDict(use_enum_values=True)

    title: ExpenseTitle | None = None
    amount: MoneyAmount | None = None
    expense_date: date | None = None
    payment_method: PaymentMethod | None = None
    notes: str | None = Field(default=None, max_length=1000)
    # Send null to remove the category from the expense.
    category_id: int | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "ExpenseUpdate":
        # `notes` and `category_id` may be set to null; these columns may not.
        for field_name in ("title", "amount", "expense_date", "payment_method"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: Decimal
    expense_date: date
    payment_method: PaymentMethod
    notes: str | None
    category: CategorySummary | None
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    """One page of expenses plus what a client needs to build pagination."""

    items: list[ExpenseResponse]
    total: int  # how many expenses match the filters across all pages
    limit: int
    offset: int
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""
Schemas for expenses.

Amounts are `Decimal`, never `float`, so 0.1 + 0.2 style rounding errors
cannot creep into money. In JSON responses they appear as strings ("250.00").
"""
```

- `"""..."""` - module docstring.
- `Schemas for expenses.` - the topic.
- `Amounts are Decimal, never float` - the one design decision of this file
  that you must remember. `float` is the binary floating-point number type;
  it cannot store most decimal fractions exactly. Verified in Python:
  `0.1 + 0.2` gives `0.30000000000000004`. With money, those tiny errors add
  up across thousands of rows and totals stop matching. `Decimal` (Block 3)
  stores decimal digits exactly: `Decimal('0.1') + Decimal('0.2')` gives
  `Decimal('0.3')` (verified).
- `so 0.1 + 0.2 style rounding errors cannot creep into money.` - the reason.
- `In JSON responses they appear as strings ("250.00").` - a consequence to
  know about when you write a client: JSON has no exact-decimal number type,
  so Pydantic writes a `Decimal` as a **string** (verified:
  `"amount": "250.00"` in every response). A client must parse that string
  with its own decimal type, not with `parseFloat`.

**Why it is here:** the `Decimal` choice surprises people (why is my number
in quotes?), so the file explains it at the top.

**If you removed or changed it:** nothing changes at runtime.

### Block 2: import date and datetime

```python
from datetime import date, datetime
```

- `from datetime import` - from the standard-library date/time module.
- `date` - a class for a **calendar day only**: year, month, day. No time.
  Used for `expense_date` - the day the money was spent. Comparing "is this
  expense in October?" is simpler with a pure date.
- `,` - two names in one import.
- `datetime` - date **and** time. Used for `created_at` and `updated_at`, the
  exact moments the row was written.

**Why it is here:** both types are used as field types below.

**If you removed or changed it:** `NameError` at import for the first missing
name.

### Block 3: import Decimal

```python
from decimal import Decimal
```

- `from decimal import` - from the standard-library module `decimal`, which
  implements exact decimal arithmetic.
- `Decimal` - the class. `Decimal("250.00")` is the number two hundred fifty,
  stored as the digits `25000` and an exponent of `-2`, so it is exact and it
  remembers that it has two decimal places. It is the standard Python type for
  money, and it is the type SQLAlchemy uses for a `NUMERIC(12, 2)` column (doc
  06).

**Why it is here:** `MoneyAmount` and `ExpenseResponse.amount` use it.

**If you removed or changed it:** `NameError` at import.

### Block 4: import Annotated

```python
from typing import Annotated
```

- as in user.py Block 3.

**Why it is here:** `ExpenseTitle` and `MoneyAmount` are built with it.

**If you removed or changed it:** `NameError` at import.

### Block 5: import from pydantic

```python
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
```

- the same five names as in category.py Block 4. All are used below.

**Why it is here:** needed below.

**If you removed or changed it:** `NameError` at import.

### Block 6: import the PaymentMethod enum

```python
from app.models.expense import PaymentMethod
```

- `from app.models.expense import` - from the *model* file of expenses (doc 06).
- `PaymentMethod` - the **enum** defined there. An enum (short for
  "enumeration") is a fixed list of named allowed values. This one is
  `class PaymentMethod(str, enum.Enum)` with members `CASH = "cash"`,
  `CARD = "card"`, `UPI = "upi"`, `BANK_TRANSFER = "bank_transfer"`,
  `OTHER = "other"`. Because it also inherits from `str`, each member *is* a
  string: `isinstance(PaymentMethod.CASH, str)` is `True`, and
  `PaymentMethod.CASH.value` is `"cash"` (verified).

When you use an enum as a Pydantic field type, Pydantic accepts only the
member **values** (`"cash"`, `"card"`, ...) and rejects anything else with a
helpful message. Verified: `"cheque"` gives 422
`"Input should be 'cash', 'card', 'upi', 'bank_transfer' or 'other'"`, and so
does `"CASH"` in capitals (the values are case-sensitive).

This is the one place where a schema imports from a model. It is safe: the
enum is a plain list of values that both the table and the JSON share, and
`app/models/expense.py` does not import anything from `app/schemas`, so there
is no circular import.

**Why it is here:** the allowed payment methods must be the same list in the
API and in the database.

**If you removed or changed it:** if you wrote `payment_method: str`, any
text would be accepted and stored, and the reports could not rely on a fixed
set of values.

### Block 7: import CategorySummary

```python
from app.schemas.category import CategorySummary
```

- `from app.schemas.category import` - from the sibling file explained above.
- `CategorySummary` - the two-field category schema, used as the type of
  `ExpenseResponse.category` (Block 41).

**Why it is here:** an expense response nests its category.

**If you removed or changed it:** `NameError` at the `category:` line.

### Block 8: the ExpenseTitle reusable type

```python
ExpenseTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
```

- the same pattern as `FullName` and `CategoryName`: stripped, 1 to 150
  characters. `150` matches `expenses.title VARCHAR(150)`. Verified: 151
  characters gives `"String should have at most 150 characters"`, and
  `"  Tea  "` becomes `"Tea"`.

**Why it is here:** `ExpenseCreate.title` and `ExpenseUpdate.title` share it.

**If you removed or changed it:** empty or over-long titles would be accepted
or would fail in the database.

### Block 9: the MoneyAmount reusable type

```python
# Matches the Numeric(12, 2) column: positive, at most 2 decimal places.
MoneyAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
```

- `# Matches the Numeric(12, 2) column: ...` - comment: the rules below are
  copied from the database column type so that bad values are stopped at the
  API with a 422 instead of at the database with a 500.
- `MoneyAmount` - a type alias for "an amount of money".
- `= Annotated[Decimal, Field(...)]` - a `Decimal` with rules. Here the extra
  info is a `Field(...)` object instead of `StringConstraints`, because the
  rules are about numbers. (`Field` works inside `Annotated` just like it
  works after `=`; verified.)
- `gt=0` - "greater than 0". The amount must be strictly positive. Verified:
  `0` and `"-5"` give 422 `"Input should be greater than 0"`. This mirrors the
  database `CHECK (amount > 0)` constraint (doc 06).
- `max_digits=12` - at most 12 significant digits in total (digits before
  plus digits after the decimal point). This is the `12` in `NUMERIC(12, 2)`.
- `decimal_places=2` - at most 2 digits after the decimal point. This is the
  `2` in `NUMERIC(12, 2)`. Together they mean at most 10 digits before the
  point, so the largest amount is `9,999,999,999.99` (verified accepted).

What Pydantic does with different inputs (verified):

| Input (JSON) | Result |
| --- | --- |
| `"250.00"` (string) | `Decimal('250.00')` |
| `250` (number) | `Decimal('250')` |
| `19.99` (number) | `Decimal('19.99')` - Pydantic converts the float by its shortest text form, so no `19.989999...` |
| `"10.5"` | `Decimal('10.5')` - not padded to two places by Pydantic; the database column does that on save, so the response shows `"10.50"` |
| `"1.000"` | accepted - trailing zeros do not count as decimal places |
| `"250.123"` | 422 `"Decimal input should have no more than 2 decimal places"` |
| `"10000000000.00"` (11 digits before the point) | 422 `"Decimal input should have no more than 10 digits before the decimal point"` |
| `"1234567890.123"` | 422 `"Decimal input should have no more than 12 digits in total"` |
| `"abc"` | 422 `"Input should be a valid decimal"` |
| `"NaN"` | 422 `"Input should be a finite number"` |

A client may send the amount as a JSON number or as a JSON string; the
OpenAPI schema FastAPI generates says `anyOf: number, string` (verified).
Sending a string is the safest, because JSON numbers go through `float` in
most clients.

**Why it is here:** money must be exact, positive, and must fit the column.

**If you removed or changed it:** with `amount: float`, `19.99` could become
`19.989999999999998` in arithmetic and totals in the reports would drift.
Without `gt=0`, a `0` or negative amount would reach PostgreSQL and be
rejected by the `CHECK` constraint with a 500. Without `max_digits`, a huge
number would fail in PostgreSQL with `numeric field overflow` (500).

### Block 10: the ExpenseCreate class header

```python
class ExpenseCreate(BaseModel):
    """Body of POST /expenses."""
```

- `class ExpenseCreate(BaseModel):` - the create-body schema.
- `"""Body of POST /expenses."""` - which endpoint reads it. The router does
  `Expense(**expense_in.model_dump(), owner_id=current_user.id)`, so the field
  names must match the `Expense` model's column names.

**Why it is here:** the create endpoint needs a checked input.

**If you removed or changed it:** `app/routers/expenses.py` fails to import.

### Block 11: model_config with use_enum_values

```python
    # Store "cash" (the plain string) instead of the PaymentMethod enum object.
    model_config = ConfigDict(use_enum_values=True)
```

- `# Store "cash" (the plain string) instead of the PaymentMethod enum object.`
  - comment explaining the setting below.
- `model_config = ConfigDict(` - the class settings, as before.
- `use_enum_values=True` - Pydantic's docstring: "Whether to populate models
  with the `value` property of enums, rather than the raw enum." Normally,
  when a field's type is an enum, the validated attribute is the enum
  **member** (`PaymentMethod.CARD`). With this setting it is the member's
  **value** (`"card"`, a plain `str`). Verified:
  `ExpenseCreate(..., payment_method="card").payment_method` is `'card'` of
  type `str`; with a test class without the setting it is
  `<PaymentMethod.CARD: 'card'>` of type `PaymentMethod`.
- `)` - closes the call.

Why plain strings are wanted: the router passes `expense_in.model_dump()`
straight into the `Expense` model, and the `expenses.payment_method` column
is `String(20)` (doc 06): it stores text. Giving it the text directly is the
simplest and most predictable thing.

**Why it is here:** so `model_dump()` gives `{'payment_method': 'cash'}`, ready
for the database.

**If you removed or changed it:** `model_dump()` would give
`{'payment_method': <PaymentMethod.CARD: 'card'>}`. Because the enum also
inherits from `str`, SQLAlchemy would most likely still store the text
`"card"` (verified on SQLite: the stored raw value is `'card'`), so the
app might appear to work. But the Python object would hold an enum member in
one code path and a string in another, which is the kind of inconsistency
that causes confusing bugs later (for example `== "card"` comparisons behave
differently from `is`). The setting removes the doubt.

### Block 12: title

```python
    title: ExpenseTitle
```

- `title: ExpenseTitle` - required; stripped; 1 to 150 characters.

**Why it is here:** the column is `NOT NULL`.

**If you removed or changed it:** `Expense(**...)` would create a row with no
title and PostgreSQL would reject it (500).

### Block 13: amount

```python
    amount: MoneyAmount
```

- `amount: MoneyAmount` - required; positive `Decimal` with at most 2 decimal
  places and 12 digits.

Verified: leaving both `title` and `amount` out gives one 422 with **two**
entries in `detail`, one per missing field. Pydantic reports all field errors
at once, not just the first.

**Why it is here:** an expense without an amount is meaningless.

**If you removed or changed it:** see Block 9.

### Block 14: expense_date with default_factory

```python
    # Defaults to today when the client does not send a date.
    expense_date: date = Field(default_factory=date.today)
```

- `# Defaults to today when the client does not send a date.` - comment.
- `expense_date` - field / JSON key.
- `: date` - a calendar day. The client sends it as text in ISO format,
  `"2026-10-01"`. Verified conversions: `"2026-10-01"` becomes
  `date(2026, 10, 1)`; `"06/10/2026"` gives 422
  `"Input should be a valid date or datetime, invalid character in year"`;
  `null` gives 422 `"Input should be a valid date"`; a date-time string with
  a non-zero time such as `"2026-10-01T10:00:00"` gives 422
  `"Datetimes provided to dates should have zero time - e.g. be exact dates"`.
- `= Field(` - attach a default.
- `default_factory=` - a **function that produces the default**, instead of a
  fixed default value. Pydantic **calls** this function each time an object is
  built without this key, and uses what it returns.
- `date.today` - the function. Note: **no parentheses**. `date.today` is the
  function itself; `date.today()` would *call* it right now, once, while the
  class is being defined, and freeze that date forever. I verified the
  difference: a test class with `d: date = date.today()` has a fixed default
  of today's date baked in at class creation, so after midnight it would be
  wrong, and it would stay wrong until the server restarts. With
  `default_factory=date.today`, every new `ExpenseCreate()` gets a fresh
  `date.today()` (verified: `ExpenseCreate(...).expense_date == date.today()`).
- `)` - closes the call.

**Why it is here:** most expenses are entered the same day, so the client may
skip the date.

**If you removed or changed it:** with `default=date.today()` you would get
the "stuck date after midnight" bug above. With no default at all,
`expense_date` would be required in every POST.

### Block 15: payment_method with validate_default

```python
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.CASH, validate_default=True
    )
```

- `payment_method` - field / JSON key.
- `: PaymentMethod` - the enum from Block 6. Only `"cash"`, `"card"`, `"upi"`,
  `"bank_transfer"`, `"other"` are accepted. `null` is **not** accepted here
  (verified: 422, type `enum`), because the column is `NOT NULL`.
- `= Field(` - attach a default plus one more setting. The call is split over
  three lines only because it is long.
- `default=PaymentMethod.CASH` - when the client does not send a payment
  method, use cash. Written as the enum member, not the string `"cash"`, so
  that a typo would be caught by your editor.
- `,` - separates the arguments.
- `validate_default=True` - Pydantic's docstring: "Whether to validate default
  values during validation. Defaults to `False`." By default, Pydantic trusts
  defaults and does **not** run them through validation - which also means it
  does not apply `use_enum_values` to them. With this set to `True`, the
  default is validated like client input, so `PaymentMethod.CASH` is turned
  into `"cash"`. Pydantic's own documentation for `use_enum_values` mentions
  exactly this: if you set a default for an enum field, "you need to use
  `validate_default=True`". Verified:
  - with this line: `ExpenseCreate(title="Tea", amount="20").payment_method`
    is `'cash'` (a `str`).
  - with a test class without `validate_default=True`: the default stays
    `<PaymentMethod.CASH: 'cash'>` (an enum member) and `model_dump()` shows
    the enum member, not the string.
- `)` - closes the call.

**Why it is here:** so the default goes through the same `use_enum_values`
conversion as explicit input, and `model_dump()` always holds a plain string.

**If you removed or changed it:** the inconsistency described in Block 11
would appear for every expense created without an explicit payment method -
which is most of them.

### Block 16: notes

```python
    notes: str | None = Field(default=None, max_length=1000)
```

- `notes: str | None = Field(default=None, max_length=1000)` - the same shape
  as `description` in category.py Block 8: optional, may be `null`, at most
  1000 characters. Verified: 1001 characters gives `"String should have at
  most 1000 characters"`. The column is `TEXT` (no limit), so the 1000 here is
  an API decision, not a database one: it stops a client from storing a book
  in the notes.

**Why it is here:** free text is useful but should have a sane limit.

**If you removed or changed it:** without `max_length`, any size would be
accepted. Without the default, `notes` would be required.

### Block 17: category_id

```python
    # Leave out (or send null) for an uncategorized expense.
    category_id: int | None = None
```

- `# Leave out (or send null) for an uncategorized expense.` - comment: both
  ways give the same result when creating.
- `category_id` - field / JSON key. The id of one of the user's categories.
- `: int | None` - a whole number or `null`. Verified: `"3"` (a string of
  digits) is accepted and converted to `3`; `"abc"` gives 422 `"Input should
  be a valid integer, unable to parse string as an integer"`.
- `= None` - default `None`, so the key may be left out. Here `None` is a real
  value: the `expenses.category_id` column allows `NULL` and that means
  "uncategorized" (doc 06).

Note what this schema does **not** check: that the category exists and
belongs to the user. A schema sees only the JSON; it has no database access.
The router does that check (`get_owned_category_or_404`) right after
validation (doc 09).

**Why it is here:** an expense may belong to a category.

**If you removed or changed it:** without `| None`, every expense would need
a category. Without `= None`, the key would be required (even if `null`).

### Block 18: the ExpenseUpdate class header

```python
class ExpenseUpdate(BaseModel):
    """Body of PATCH /expenses/{id}. Only the fields you send are changed."""
```

- `class ExpenseUpdate(BaseModel):` - the update-body schema.
- `"""Body of PATCH /expenses/{id}. Only the fields you send are changed."""`
  - the same partial-update contract as `CategoryUpdate`.

**Why it is here:** every field must be optional on PATCH; `ExpenseCreate`
has required fields, so a separate class is needed.

**If you removed or changed it:** `app/routers/expenses.py` fails to import.

### Block 19: model_config

```python
    model_config = ConfigDict(use_enum_values=True)
```

- the same setting as Block 11, for the same reason: when the client sends
  `"payment_method": "card"`, `model_dump(exclude_unset=True)` must give the
  string `'card'` for the `setattr` loop in the router. Verified:
  `ExpenseUpdate(payment_method="card").payment_method` is `'card'`, type
  `str`. No `validate_default` is needed here because the default is `None`
  (Block 23), and `None` has no enum value to convert.

**Why it is here:** consistent plain strings on the way to the database.

**If you removed or changed it:** the router would `setattr(expense,
"payment_method", PaymentMethod.CARD)` - most likely still stored as `"card"`,
but inconsistent, as discussed in Block 11.

### Block 20: optional title

```python
    title: ExpenseTitle | None = None
```

- `title: ExpenseTitle | None = None` - the title rules, or `None`, default
  `None`. The validator in Block 26 to 32 removes the `null` option again.

**Why it is here:** the client may leave the title out.

**If you removed or changed it:** without `= None`, every PATCH would need a
title.

### Block 21: optional amount

```python
    amount: MoneyAmount | None = None
```

- `amount: MoneyAmount | None = None` - the money rules, or `None`, default
  `None`. Verified: `PATCH /expenses/2` with `{"amount": "21.00"}` answers 200
  with `"amount": "21.00"` and nothing else changed.

**Why it is here:** the client may leave the amount out.

**If you removed or changed it:** same as Block 20.

### Block 22: optional expense_date

```python
    expense_date: date | None = None
```

- `expense_date: date | None = None` - a date or `None`, default `None`. No
  `default_factory` here: on an update, "not sent" must mean "keep the old
  date", **not** "set it to today". That is a real difference between the
  Create and Update classes, and a good example of why they are separate.

**Why it is here:** the client may leave the date out.

**If you removed or changed it:** if you copied the `default_factory=date.today`
from `ExpenseCreate`, then `model_fields_set` would still not contain
`expense_date` (defaults are not "set"), so `exclude_unset=True` would still
skip it - the router would behave correctly by luck. But it would mislead the
reader, so the plain `None` is right.

### Block 23: optional payment_method

```python
    payment_method: PaymentMethod | None = None
```

- `payment_method: PaymentMethod | None = None` - one of the five values, or
  `None`, default `None`. Verified: `ExpenseUpdate().payment_method` is
  `None`.

**Why it is here:** the client may leave it out.

**If you removed or changed it:** same as Block 20.

### Block 24: notes

```python
    notes: str | None = Field(default=None, max_length=1000)
```

- identical to Block 16. Here `null` is meaningful: "clear the notes".
  Verified: `ExpenseUpdate(notes=None).model_dump(exclude_unset=True)` is
  `{'notes': None}`, and the validator (Block 29) does not include `notes`,
  so this passes.

**Why it is here:** the client may change or clear the notes.

**If you removed or changed it:** same as Block 16.

### Block 25: category_id, where null means "remove"

```python
    # Send null to remove the category from the expense.
    category_id: int | None = None
```

- `# Send null to remove the category from the expense.` - comment: on an
  update, `null` is an action.
- `category_id: int | None = None` - as in Block 17.

Verified: `PATCH /expenses/2` with `{"category_id": null}` answers 200 and the
response shows `"category": null`; `model_fields_set` is `{'category_id'}` and
`model_dump(exclude_unset=True)` is `{'category_id': None}`, so the router sets
the column to `NULL`.

**Why it is here:** the client must be able to un-categorise an expense.

**If you removed or changed it:** if `category_id` were in the validator's
tuple (Block 29), `null` would be refused and there would be no way to remove a
category from an expense.

### Block 26: the model_validator decorator

```python
    @model_validator(mode="after")
```

- `@model_validator(mode="after")` - exactly as in category.py Block 12:
  register the method below as a whole-object check that runs after the
  fields are validated.

**Why it is here:** the "absent is fine, `null` is not" rule for four fields.

**If you removed or changed it:** `{"title": null}` would pass validation; the
router would `setattr(expense, "title", None)` and PostgreSQL would reject the
UPDATE (`title` is `NOT NULL`) with a 500.

### Block 27: the validator method header

```python
    def required_fields_cannot_be_null(self) -> "ExpenseUpdate":
```

- `def required_fields_cannot_be_null(self)` - the method; `self` is the built
  `ExpenseUpdate` object. The name says the rule: fields that are required
  in the database cannot be set to `null`.
- `-> "ExpenseUpdate"` - forward-reference return type, as explained in
  category.py Block 13.
- `:` - starts the body.

**Why it is here:** the function the decorator registers.

**If you removed or changed it:** `-> ExpenseUpdate` without quotes would be
a `NameError` at import.

### Block 28: the explaining comment

```python
        # `notes` and `category_id` may be set to null; these columns may not.
```

- `#` - comment.
- `notes and category_id may be set to null; these columns may not.` - the
  reason the tuple on the next line lists exactly four fields: those are the
  four `NOT NULL` columns among the updatable ones. `notes` and `category_id`
  are nullable columns, so `null` is allowed for them.

**Why it is here:** so a future developer adding a field knows which list to
put it in.

**If you removed or changed it:** nothing changes at runtime.

### Block 29: the for loop

```python
        for field_name in ("title", "amount", "expense_date", "payment_method"):
```

- `for` - Python keyword: repeat the indented block once for each item.
- `field_name` - the loop variable; on each pass it holds the next item.
- `in` - separates the variable from the collection to loop over.
- `("title", "amount", "expense_date", "payment_method")` - a **tuple** (an
  ordered, unchangeable list, written with round brackets) of four strings:
  the names of the fields to check.
- `:` - starts the loop body.

This loop is the same check as `CategoryUpdate.name_cannot_be_null`, done four
times. Writing four `if` statements would work but would be repetitive; the
loop keeps the rule in one place.

**Why it is here:** four fields share one rule.

**If you removed or changed it:** if you dropped `"amount"` from the tuple,
`{"amount": null}` would pass and hit the database `NOT NULL` with a 500.

### Block 30: the check, with getattr

```python
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
```

- `if field_name in self.model_fields_set` - was this field sent by the
  client? (`model_fields_set` is explained in category.py Block 15.)
- `and` - both conditions.
- `getattr(` - a built-in function: **get attribute by name**.
  `getattr(self, "title")` is the same as `self.title`, but the name is a
  string variable, so it works inside a loop where the name changes each
  pass. You cannot write `self.field_name` - that would look for an attribute
  literally called `field_name`.
- `self` - the object to read from.
- `,` - separates arguments.
- `field_name` - the attribute name, a string.
- `)` - closes the call.
- `is None` - is the value `None`?
- `:` - starts the block.

Verified: `ExpenseUpdate(title=None)` fails with `"Value error, title cannot
be null"`, `ExpenseUpdate(amount=None)` with `"amount cannot be null"`;
`ExpenseUpdate(category_id=None)` and `ExpenseUpdate(notes=None)` pass. If
two of the four are `null` at once, only the first in tuple order is reported
(verified: `title` before `amount`), because `raise` stops the loop.

**Why it is here:** the heart of the rule.

**If you removed or changed it:** with `if getattr(self, field_name) is
None:` alone, every PATCH that did not include all four fields would fail,
because absent fields are `None` too.

### Block 31: raise with an f-string

```python
                raise ValueError(f"{field_name} cannot be null")
```

- `raise ValueError(` - as in category.py Block 16: becomes a 422.
- `f"..."` - an **f-string** ("formatted string"): a string with an `f`
  before the opening quote, in which `{...}` parts are replaced by the value
  of the expression inside the braces.
- `{field_name}` - replaced by the current field name, so the message is
  `"title cannot be null"`, `"amount cannot be null"`, and so on.
- `cannot be null` - the rest of the message.
- `)` - closes the call.

Verified HTTP response for `PATCH /expenses/2` with `{"title": null}`:
`422`, `"loc": ["body"]`, `"msg": "Value error, title cannot be null"`.

**Why it is here:** one message template for all four fields.

**If you removed or changed it:** without the `f`, the message would be the
literal text `{field_name} cannot be null`, which is useless to the client.

### Block 32: return self

```python
        return self
```

- `return self` - as in category.py Block 17: required; the returned object is
  the validation result.

**Why it is here:** Pydantic requires it.

**If you removed or changed it:** the body would validate to `None` and the
router would crash with `AttributeError` on every PATCH (verified mechanism
in category.py Block 17).

### Block 33: the ExpenseResponse class header

```python
class ExpenseResponse(BaseModel):
```

- `class ExpenseResponse(BaseModel):` - the response schema for one expense.
  Used as `response_model` on `POST`, `GET /{id}` and `PATCH`, and as the item
  type inside `ExpenseListResponse`.

This is what one looks like in JSON (verified, from the real app):

```json
{
  "id": 2,
  "title": "Groceries",
  "amount": "19.99",
  "expense_date": "2026-10-01",
  "payment_method": "upi",
  "notes": "weekly",
  "category": {"id": 1, "name": "Food & Drink"},
  "created_at": "2026-10-06T11:51:59",
  "updated_at": "2026-10-06T11:51:59"
}
```

Note what is **not** there: `owner_id` (the client already knows who they
are, and showing ids of other users' data is never needed) and the category's
`description` and `created_at` (the summary schema leaves them out).

**Why it is here:** one agreed shape for an expense.

**If you removed or changed it:** `app/routers/expenses.py` fails to import.

### Block 34: model_config

```python
    model_config = ConfigDict(from_attributes=True)
```

- `from_attributes=True` - build from an `Expense` row by reading attributes.

For this class the setting is **not optional**, unlike `UserResponse`. The
list endpoint builds the response by hand:
`ExpenseListResponse(items=expenses, total=total, limit=limit, offset=offset)`,
where `expenses` is a list of `Expense` rows. That constructor call validates
each row as an `ExpenseResponse` right there, with no help from FastAPI.
Verified with a copy of the class without the setting: the call fails with
`"Input should be a valid dictionary or instance of ExpenseResponse"` at
`"loc": ["items", 0]`, which is a 500 for `GET /expenses`.

**Why it is here:** rows must be accepted as input.

**If you removed or changed it:** `GET /expenses` answers 500 whenever there
is at least one expense.

### Block 35: id

```python
    id: int
```

- `id: int` - the expense's primary key.

**Why it is here:** clients use it for `/expenses/{id}`.

**If you removed or changed it:** the key disappears; clients could not
update or delete.

### Block 36: title

```python
    title: str
```

- `title: str` - plain string on output.

**Why it is here:** the main label.

**If you removed or changed it:** the key disappears.

### Block 37: amount as Decimal

```python
    amount: Decimal
```

- `amount: Decimal` - the exact money type. SQLAlchemy gives a `Decimal` for
  the `NUMERIC(12, 2)` column, with two decimal places (`Decimal('20.00')`
  for an expense created with `20`; verified in the real response
  `"amount": "20.00"`). Pydantic writes it in JSON as a string. No `gt` /
  `max_digits` rules here: the value came from the database, it was checked
  on the way in.

**Why it is here:** show the amount exactly.

**If you removed or changed it:** with `amount: float`, Pydantic would
convert the `Decimal` to a float and the JSON would show a number like
`19.99` - which looks nicer but reintroduces the rounding problem on the
client side. With `amount: int`, a `Decimal('19.99')` would be rejected
(`"Input should be a valid integer, got a number with a fractional part"`,
verified with the same type on another field) - a 500.

### Block 38: expense_date

```python
    expense_date: date
```

- `expense_date: date` - a calendar day; JSON `"2026-10-01"`.

**Why it is here:** the day the money was spent.

**If you removed or changed it:** the key disappears.

### Block 39: payment_method as the enum

```python
    payment_method: PaymentMethod
```

- `payment_method: PaymentMethod` - the enum. This class has **no**
  `use_enum_values`, so the validated attribute is the enum member
  (`<PaymentMethod.CASH: 'cash'>`, verified), but in JSON it is written as its
  value `"cash"` (verified). Using the enum type here does one more useful
  thing: it **checks the database value**. If a row somehow held
  `"cheque"`, building the response would fail with `"Input should be 'cash',
  'card', ..."` (verified) - a loud 500 instead of silently passing bad data
  to clients. With the `String(20)` column and the API checks, that cannot
  happen through the API; it would need a manual database edit.
- It also makes `/docs` show the five allowed values for this field in the
  response schema.

**Why it is here:** typed output, documented values.

**If you removed or changed it:** with `str`, the docs would lose the list of
values and a bad row would pass through.

### Block 40: notes

```python
    notes: str | None
```

- `notes: str | None` - required but nullable, as explained in category.py
  Block 22: the row always has a `notes` attribute; it may be `NULL`.

**Why it is here:** show the notes, or `null`.

**If you removed or changed it:** with `notes: str`, every expense without
notes would fail to serialise (500).

### Block 41: the nested category

```python
    category: CategorySummary | None
```

- `category` - the JSON key. Note: not `category_id`. The response gives the
  client the **object** (`{"id": 1, "name": "Food & Drink"}`), so a list of
  expenses can show category names without one extra request per row.
- `: CategorySummary` - the nested schema from category.py. Pydantic reads
  `expense.category` from the row, which is the related `Category` row loaded
  by SQLAlchemy's `relationship` (doc 06), and builds a `CategorySummary` from
  its `id` and `name` attributes (`from_attributes=True` on `CategorySummary`
  makes that possible).
- `| None` - an uncategorised expense has `expense.category is None`, and
  the JSON shows `"category": null` (verified).
- No default, so required: the attribute always exists on a row.

A performance note that belongs to the router (doc 09) but is caused by this
field: reading `expense.category` for 20 expenses could mean 20 extra
`SELECT`s (the "N+1" problem). The list endpoint avoids that with
`selectinload(Expense.category)`, which loads all categories for the page in
one query *before* this schema reads them.

**Why it is here:** show the category label inline.

**If you removed or changed it:** if you wrote `category_id: int | None`
instead, clients would need a second request per expense to get the name. If
you dropped `| None`, every uncategorised expense would fail to serialise.

### Block 42: created_at

```python
    created_at: datetime
```

- `created_at: datetime` - when the row was inserted.

**Why it is here:** audit information.

**If you removed or changed it:** the key disappears.

### Block 43: updated_at

```python
    updated_at: datetime
```

- `updated_at: datetime` - when the row was last changed. The database keeps
  it current (`onupdate=func.now()`, doc 06); the schema only shows it.

**Why it is here:** lets a client see that an expense was edited.

**If you removed or changed it:** the key disappears.

### Block 44: the ExpenseListResponse class header

```python
class ExpenseListResponse(BaseModel):
    """One page of expenses plus what a client needs to build pagination."""
```

- `class ExpenseListResponse(BaseModel):` - the response schema for
  `GET /expenses`.
- `"""One page of expenses plus what a client needs to build pagination."""`
  - class docstring. **Pagination** means returning the results in pages
  (say 20 at a time) instead of all at once. To show "page 3 of 15" or a
  "next" button, the client needs more than the items: it needs the total and
  the page position. That is why the list is wrapped in an object instead of
  being a bare JSON array.

Verified, from the real app, `GET /expenses?limit=2&offset=0` with three
expenses in the database:

```json
{
  "items": [
    {"id": 3, "title": "Shoes", "amount": "250.50", "...": "..."},
    {"id": 1, "title": "Tea", "amount": "20.00", "...": "..."}
  ],
  "total": 3,
  "limit": 2,
  "offset": 0
}
```

(The `"..."` stands for the other `ExpenseResponse` fields, shortened here.)
The client can compute: pages = ceil(3 / 2) = 2; current page = offset /
limit + 1 = 1; there is a next page because offset + limit (2) < total (3).

**Why it is here:** a bare list cannot carry `total`.

**If you removed or changed it:** `app/routers/expenses.py` fails to import.

### Block 45: items

```python
    items: list[ExpenseResponse]
```

- `items` - the JSON key holding the page of expenses.
- `: list[` - a Python list. The square brackets after `list` say what the
  elements are. (This is the built-in `list` used as a type; the older
  spelling is `List[...]` from `typing`, which your old project used.)
- `ExpenseResponse` - each element is validated as an `ExpenseResponse`, so
  every row in the list goes through Block 33 to 43.
- `]` - closes the bracket.
- Required.

Verified: passing something that is not a list gives `"Input should be a
valid list"`; passing a list of `Expense` rows works thanks to
`from_attributes=True` on `ExpenseResponse`.

**Why it is here:** the actual data of the page.

**If you removed or changed it:** with `list[dict]`, the rows would not be
converted and FastAPI would fail to serialise them.

### Block 46: total

```python
    total: int  # how many expenses match the filters across all pages
```

- `total: int` - a whole number, required.
- `# how many expenses match the filters across all pages` - comment: this is
  **not** `len(items)`. It is the result of a separate `SELECT count(*)` with
  the same `WHERE` filters but without `LIMIT`/`OFFSET` (doc 09). In the
  example above `total` is 3 while `items` has 2 entries.

**Why it is here:** without it a client cannot know how many pages exist.

**If you removed or changed it:** the key disappears and the client could
only guess that there is a next page by asking for it.

### Block 47: limit

```python
    limit: int
```

- `limit: int` - the page size that was used for this response. It echoes the
  `?limit=` query parameter (default 20, maximum 100, set in the router).

**Why it is here:** so the client does not have to remember what it asked
for, and so the default is visible when the client sent nothing.

**If you removed or changed it:** the key disappears; pagination arithmetic
on the client needs it.

### Block 48: offset

```python
    offset: int
```

- `offset: int` - how many expenses were skipped before this page. It echoes
  the `?offset=` query parameter (default 0).

**Why it is here:** same as `limit`: it tells the client where this page sits.

**If you removed or changed it:** the key disappears.

### Compared to your old code

Your old post schemas and endpoints are the closest match:

```python
class PostBase(BaseModel):
    title: str
    content: str
    published: bool = True

class Post(PostBase):
    id: int
    created_at : datetime
    owner_id : int
    owner : Create_User_Response
    class Config:
        from_attributes = True

class ResponsePost(BaseModel):
    message : str
    data : Post
```

```python
@router.get("/",response_model=List[Post]) 
def get_post(db: Session = Depends(get_db), current_user: int = Depends(get_current_user),
             limit : int = 10 , skip : int = 3, search : Optional[str] = ""):
```

What is different, and why:

1. **No rules on input.** `title: str` accepted `""`. The new `ExpenseTitle`
   and `MoneyAmount` aliases reject empty titles, zero or negative amounts,
   and values that would not fit the columns.
2. **No money.** The old project had no amounts, so this is new: `Decimal`
   with `max_digits` / `decimal_places`, never `float`.
3. **Nested object: same idea, smaller.** Your old `Post` nested
   `owner: Create_User_Response` - that is exactly the pattern of
   `category: CategorySummary`. You had already done this; the new code only
   adds a purpose-built small schema and allows `None`.
4. **The list response.** The old list returned `List[Post]` - a bare JSON
   array. It took `limit` and `skip` but gave no `total`, so a client could
   never know how many pages there were. Also, `skip: int = 3` was a small
   bug: by default the first three posts were skipped, so a plain
   `GET /posts/` never showed the newest three. The new `ExpenseListResponse`
   carries `total`, `limit` and `offset`, and the defaults are `limit=20`,
   `offset=0`.
5. **No `message` wrapper.** The old `ResponsePost` wrapped the post in
   `{"message": "...", "data": {...}}`. The new API uses the HTTP status code
   as the message (201 Created, 204 No Content) and returns the object
   itself. The only wrapper is the list response, and it exists for the
   pagination numbers, not for a message.
6. **Update schema.** Your old PUT reused `PostBase`, with the "resets
   `published` to True" bug explained in the category.py comparison. The new
   `ExpenseUpdate` has every field optional and a validator that still
   refuses `null` where the database refuses `NULL`.
7. **`List[Post]` vs `list[ExpenseResponse]`.** Same meaning; `list[...]`
   is the modern spelling (Python 3.9+), so the `typing.List` import is no
   longer needed.
8. **`class Config` vs `ConfigDict`.** Explained in the category.py
   comparison; the old style is deprecated.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `Decimal` | exact decimal number type; the right type for money |
| `float` | binary floating point; `0.1 + 0.2 != 0.3`; never use for money |
| `gt=0` | greater than zero |
| `max_digits` | maximum total number of digits (before + after the point) |
| `decimal_places` | maximum digits after the decimal point |
| enum | a fixed list of named allowed values (`PaymentMethod`) |
| `use_enum_values=True` | store the enum's value (`"cash"`) instead of the member (`PaymentMethod.CASH`) |
| `validate_default=True` | run the default through validation too (so `use_enum_values` applies to it) |
| `default_factory=` | a function called to produce the default each time; `date.today` without `()` |
| `date` vs `datetime` | a calendar day vs a day plus a time |
| tuple | an ordered, unchangeable list, written `("a", "b")` |
| `getattr(obj, "name")` | read an attribute whose name is in a string |
| f-string | `f"{x} text"` - a string with values filled in |
| nested schema | `category: CategorySummary \| None` - an object inside an object |
| `list[T]` | a JSON array whose elements are validated as `T` |
| pagination | returning results page by page; needs `total`, `limit`, `offset` |
| `total` | number of matching rows across all pages, from a separate count query |

---

## File: app/schemas/report.py

### What this file is for

This file defines the three response shapes of the reports: `ExpenseSummary`
(`GET /reports/summary`: totals for a date range), `CategoryTotal`
(`GET /reports/by-category`: one row per category) and `MonthlyTotal`
(`GET /reports/monthly`: one row per month). Reports are **read-only**, so
there are no `Create` or `Update` classes here. Unlike the other response
schemas, these are not built from database rows; the router computes the
numbers with `SUM` / `COUNT` / `AVG` / `MAX` queries and then builds each
object with keyword arguments, for example
`ExpenseSummary(start_date=..., total_amount=to_money(total_amount), ...)`.
That is why none of these classes needs `from_attributes=True`.

Who imports it: `app/routers/reports.py` (all three classes).

What it imports: `date`, `Decimal`, `BaseModel`.

### The whole file

```python
"""Schemas for the spending reports (response only - reports are read-only)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ExpenseSummary(BaseModel):
    """Overall totals for a date range. GET /reports/summary"""

    start_date: date | None
    end_date: date | None
    total_amount: Decimal
    expense_count: int
    average_amount: Decimal
    highest_amount: Decimal


class CategoryTotal(BaseModel):
    """Spending for one category. GET /reports/by-category"""

    category_id: int | None  # null for the "Uncategorized" row
    category_name: str
    total_amount: Decimal
    expense_count: int
    percentage_of_total: float


class MonthlyTotal(BaseModel):
    """Spending for one calendar month. GET /reports/monthly"""

    year: int
    month: int  # 1 = January ... 12 = December
    total_amount: Decimal
    expense_count: int
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""Schemas for the spending reports (response only - reports are read-only)."""
```

- `"""..."""` - module docstring.
- `Schemas for the spending reports` - the topic.
- `(response only - reports are read-only)` - tells you not to look for
  request schemas: the reports take their inputs (`start_date`, `end_date`,
  `year`) as query parameters, which FastAPI validates directly in the router
  function signature (doc 04 and doc 09), not through a body schema.

**Why it is here:** documentation.

**If you removed or changed it:** nothing changes at runtime.

### Block 2: import date

```python
from datetime import date
```

- `from datetime import date` - the calendar-day class (expense.py Block 2).
  Only `date` is needed here; no `datetime`, because reports have no
  timestamps.

**Why it is here:** `start_date` and `end_date` are dates.

**If you removed or changed it:** `NameError` at import.

### Block 3: import Decimal

```python
from decimal import Decimal
```

- `from decimal import Decimal` - the exact money type (expense.py Block 3).

**Why it is here:** every total, average and maximum is money.

**If you removed or changed it:** `NameError` at import.

### Block 4: import BaseModel

```python
from pydantic import BaseModel
```

- `from pydantic import BaseModel` - only the base class. No `Field`,
  `ConfigDict` or validators are needed: these schemas are built by the
  router from values it computed itself, so there are no input rules to
  enforce, and they are built from keyword arguments, not from rows.

**Why it is here:** the three classes inherit from it.

**If you removed or changed it:** `NameError` at import.

### Block 5: the ExpenseSummary class header

```python
class ExpenseSummary(BaseModel):
    """Overall totals for a date range. GET /reports/summary"""
```

- `class ExpenseSummary(BaseModel):` - the response schema of the summary
  report.
- `"""Overall totals for a date range. GET /reports/summary"""` - class
  docstring: what the numbers are, and which endpoint returns them.

Verified response from the real app for `GET /reports/summary?start_date=2026-01-01`
with three expenses of 20.00, 21.00 and 250.50:

```json
{
  "start_date": "2026-01-01",
  "end_date": null,
  "total_amount": "291.50",
  "expense_count": 3,
  "average_amount": "97.17",
  "highest_amount": "250.50"
}
```

**Why it is here:** one agreed shape for the summary.

**If you removed or changed it:** `app/routers/reports.py` fails to import.

### Block 6: start_date

```python
    start_date: date | None
```

- `start_date` - JSON key.
- `: date | None` - a date or `null`. The report echoes back the filter the
  client used; if the client gave no `?start_date=`, this is `null`, meaning
  "from the beginning".
- No default, so required: the router must always pass it (verified: leaving
  it out when building the object raises `"Field required"`). That is a
  deliberate safety net: the router cannot forget to echo the filter.

**Why it is here:** so the client can show "totals from 2026-01-01".

**If you removed or changed it:** with `date` alone (no `| None`), the
report would fail with a 500 whenever the client sent no start date.

### Block 7: end_date

```python
    end_date: date | None
```

- `end_date: date | None` - the other end of the range, or `null` for "until
  now". Same rules as `start_date`.

**Why it is here:** echo the filter.

**If you removed or changed it:** same as Block 6.

### Block 8: total_amount

```python
    total_amount: Decimal
```

- `total_amount` - JSON key.
- `: Decimal` - the sum of all matching amounts, exact. The router rounds the
  database `SUM` to two places (`to_money`) before passing it, so the JSON
  shows `"291.50"`.

**Why it is here:** the headline number of the report.

**If you removed or changed it:** the key disappears. With `float`, the sum
could show as `291.49999999999994` after conversion.

### Block 9: expense_count

```python
    expense_count: int
```

- `expense_count` - JSON key.
- `: int` - how many expenses matched; the database `COUNT`. Verified
  conversions for an `int` field: `"2026"` (a numeric string) is accepted as
  `2026`; `2026.5` is rejected with `"Input should be a valid integer, got a
  number with a fractional part"`.

**Why it is here:** "3 expenses" next to the total.

**If you removed or changed it:** the key disappears.

### Block 10: average_amount

```python
    average_amount: Decimal
```

- `average_amount: Decimal` - the database `AVG`, rounded to two places by the
  router (`"97.17"` in the example: 291.50 / 3 = 97.1666..., rounded half up).

**Why it is here:** average spend per expense.

**If you removed or changed it:** the key disappears.

### Block 11: highest_amount

```python
    highest_amount: Decimal
```

- `highest_amount: Decimal` - the database `MAX`; the single biggest expense
  in the range.

**Why it is here:** "your largest expense was 250.50".

**If you removed or changed it:** the key disappears.

### Block 12: the CategoryTotal class header

```python
class CategoryTotal(BaseModel):
    """Spending for one category. GET /reports/by-category"""
```

- `class CategoryTotal(BaseModel):` - one row of the by-category report. The
  endpoint returns `list[CategoryTotal]`, one per category that has expenses
  in the range.
- `"""Spending for one category. GET /reports/by-category"""` - docstring.

Verified response from the real app (all three expenses uncategorised at that
point):

```json
[
  {
    "category_id": null,
    "category_name": "Uncategorized",
    "total_amount": "291.50",
    "expense_count": 3,
    "percentage_of_total": 100.0
  }
]
```

**Why it is here:** one agreed row shape for the category breakdown.

**If you removed or changed it:** `app/routers/reports.py` fails to import.

### Block 13: category_id, null for the uncategorized row

```python
    category_id: int | None  # null for the "Uncategorized" row
```

- `category_id` - JSON key.
- `: int | None` - the category's id, or `null`.
- `# null for the "Uncategorized" row` - comment: the report groups expenses
  with no category into one extra row. That row has no id to give, so it is
  `null`. The router produces it with an `OUTER JOIN` (doc 09).
- Required (no default): the router always passes it.

**Why it is here:** lets a client link each row to `/categories/{id}`, except
the uncategorised row.

**If you removed or changed it:** with `int` alone, the uncategorised row
would fail to build (`"Input should be a valid integer"` on `None`) - a 500
for any user who has an expense without a category.

### Block 14: category_name

```python
    category_name: str
```

- `category_name: str` - the label to display. For the uncategorised row the
  router passes the text `"Uncategorized"`, so this is never `None` and the
  type is plain `str`.

**Why it is here:** charts and tables show the name.

**If you removed or changed it:** the key disappears.

### Block 15: total_amount

```python
    total_amount: Decimal
```

- `total_amount: Decimal` - the `SUM` for this category, rounded to two
  places.

**Why it is here:** the size of the slice.

**If you removed or changed it:** the key disappears.

### Block 16: expense_count

```python
    expense_count: int
```

- `expense_count: int` - how many expenses are in this category.

**Why it is here:** "12 expenses in Food".

**If you removed or changed it:** the key disappears.

### Block 17: percentage_of_total as a float

```python
    percentage_of_total: float
```

- `percentage_of_total` - JSON key: this category's share of the grand total,
  in percent (`33.33` means 33.33 %).
- `: float` - a floating-point number. This is the **only** `float` in the
  whole folder, and it is on purpose. A percentage is not money: nobody adds
  percentages up to pay a bill, and a display value like `33.33` does not
  need to be exact. The router computes it as
  `round(float(category_total / grand_total * 100), 2)` and the JSON shows a
  plain number (`100.0` above), which is what a chart library wants. Verified:
  passing a `Decimal("33.33")` to this field gives `33.33` as a float.

**Why it is here:** a pie chart needs a share per slice.

**If you removed or changed it:** with `Decimal`, the JSON would show
`"33.33"` as a string and chart code would have to convert it. Either works;
`float` is simply more convenient for a value that is only displayed.

### Block 18: the MonthlyTotal class header

```python
class MonthlyTotal(BaseModel):
    """Spending for one calendar month. GET /reports/monthly"""
```

- `class MonthlyTotal(BaseModel):` - one row of the monthly report. The
  endpoint returns `list[MonthlyTotal]` with **always 12 rows** (January to
  December, zeros for months without expenses; doc 09).
- `"""Spending for one calendar month. GET /reports/monthly"""` - docstring.

Verified response rows from the real app (`GET /reports/monthly?year=2026`):

```json
[
  {"year": 2026, "month": 1, "total_amount": "0.00", "expense_count": 0},
  {"year": 2026, "month": 2, "total_amount": "0.00", "expense_count": 0},
  ...
  {"year": 2026, "month": 10, "total_amount": "291.50", "expense_count": 3},
  ...
  {"year": 2026, "month": 12, "total_amount": "0.00", "expense_count": 0}
]
```

**Why it is here:** one agreed row shape for the monthly chart.

**If you removed or changed it:** `app/routers/reports.py` fails to import.

### Block 19: year

```python
    year: int
```

- `year: int` - the year the row belongs to. Every row of one response has
  the same year (the `?year=` parameter, or the current year by default), and
  echoing it makes each row self-contained.

**Why it is here:** so a row like `{"month": 3, ...}` is not ambiguous.

**If you removed or changed it:** the key disappears.

### Block 20: month

```python
    month: int  # 1 = January ... 12 = December
```

- `month: int` - the month number.
- `# 1 = January ... 12 = December` - comment: the numbering convention, so
  nobody wonders whether it starts at 0 (as JavaScript's `Date` does).

**Why it is here:** identifies the row.

**If you removed or changed it:** the key disappears.

### Block 21: total_amount

```python
    total_amount: Decimal
```

- `total_amount: Decimal` - the month's `SUM`, rounded to two places; `"0.00"`
  for an empty month.

**Why it is here:** the bar height in a monthly chart.

**If you removed or changed it:** the key disappears.

### Block 22: expense_count

```python
    expense_count: int
```

- `expense_count: int` - how many expenses in that month; `0` for an empty
  month.

**Why it is here:** "5 expenses in March".

**If you removed or changed it:** the key disappears.

### Compared to your old code

There is no old equivalent: the posts API had no reports or aggregate
queries. The file exists because the reports endpoints return computed
numbers, not table rows, and those numbers still need a documented, checked
shape. Two habits from the rest of the folder carry over: money is `Decimal`,
and nullable values are spelled `| None` with no default when the router
always supplies them. The one new idea is the deliberate `float` for a
percentage (Block 17).

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| read-only endpoint | returns data, never changes it; needs only response schemas |
| aggregate | a number computed over many rows: `SUM`, `COUNT`, `AVG`, `MAX` |
| `to_money(...)` | router helper that rounds an aggregate to 2 decimal places (doc 09) |
| echoing a filter | returning the `start_date` / `end_date` the client sent, so the response is self-describing |
| uncategorized row | the `by-category` row with `category_id: null` for expenses without a category |
| `float` for a percentage | acceptable because a percentage is a display value, not money |
| 12 fixed rows | the monthly report always returns January to December |

---

## Summary of this folder

`app/schemas/` is the border of the application: every byte of JSON that
comes in or goes out passes through one of these classes. The **request**
classes (`UserCreate`, `CategoryCreate`, `CategoryUpdate`, `ExpenseCreate`,
`ExpenseUpdate`) check types and rules at the door and answer with a 422 that
lists every problem, so the routers and the database only ever see clean
data. The **response** classes (`Token`, `UserResponse`, `CategoryResponse`,
`CategorySummary`, `ExpenseResponse`, `ExpenseListResponse` and the three
report classes) decide exactly which fields a client may see, which is why
`hashed_password` and `owner_id` never leave the server. Reusable aliases
(`FullName`, `CategoryName`, `ExpenseTitle`, `MoneyAmount`) hold each rule in
one place, and their limits are copied from the database columns so that bad
values are rejected with a clean 422 instead of a 500 from PostgreSQL. The
`Create` and `Update` classes are separate because a `POST` has required
fields while a `PATCH` must allow any subset; the `Update` classes use
`model_fields_set` in a `model_validator` to allow a *missing* key but refuse
an explicit `null` on `NOT NULL` columns, and the routers complete that
design with `model_dump(exclude_unset=True)`. Money is always `Decimal` with
`max_digits=12, decimal_places=2`, matching `NUMERIC(12, 2)`, and it travels
through JSON as a string. `from_attributes=True` lets the response classes be
built straight from SQLAlchemy rows, including the nested `CategorySummary`
inside each expense. The files depend on each other in only one direction:
`expense.py` imports `CategorySummary` from `category.py` and `PaymentMethod`
from the models; nothing in `app/models/` imports a schema, so there are no
circular imports.
