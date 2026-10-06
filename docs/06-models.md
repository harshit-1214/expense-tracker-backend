# app/models/ (user.py, category.py, expense.py)

This document explains the four files inside `app/models/`, word by word:

| File                       | What it defines                                     |
| -------------------------- | --------------------------------------------------- |
| `app/models/__init__.py`   | makes `app.models` a package and re-exports the classes |
| `app/models/user.py`       | the `users` table (class `User`)                    |
| `app/models/category.py`   | the `categories` table (class `Category`)           |
| `app/models/expense.py`    | the `expenses` table (class `Expense`) and the `PaymentMethod` list |

## What a "model" is (read this first)

A **model** is a Python class that describes one database table.
Each class attribute describes one column. SQLAlchemy (the library) reads the
class and from it can:

1. build the `CREATE TABLE ...` SQL (Alembic uses this to write migrations),
2. turn a row from the database into a Python object (`user.email`, `expense.amount`),
3. turn a Python object back into `INSERT` / `UPDATE` / `DELETE` SQL.

In your old project you had one file, `app/model.py`, with all tables inside.
The new project has **one file per table**, and a small `__init__.py` that glues
them together. The three tables are connected like this:

```
users (1) ----< categories (many)      a user owns many categories
users (1) ----< expenses   (many)      a user owns many expenses
categories (1) ----< expenses (many)   a category groups many expenses (optional)
```

The `<` end is the "many" side. The "many" side always holds the foreign key
column (`owner_id`, `category_id`) that points at the "one" side.

All verified facts in this document (the SQL, the error messages, the behaviour
of library functions) were checked by running the real code against SQLAlchemy
2.0.54 on Python 3.14, so you can trust them.

This is the exact `CREATE TABLE` SQL that SQLAlchemy produces for PostgreSQL
from these three files. Keep it open while you read; every line of the models
maps to one line here:

```sql
CREATE TABLE users (
    id SERIAL NOT NULL,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_users PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE categories (
    id SERIAL NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    owner_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_categories PRIMARY KEY (id),
    CONSTRAINT uq_categories_owner_id_name UNIQUE (owner_id, name),
    CONSTRAINT fk_categories_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_categories_owner_id ON categories (owner_id);

CREATE TABLE expenses (
    id SERIAL NOT NULL,
    title VARCHAR(150) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    expense_date DATE NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    notes TEXT,
    owner_id INTEGER NOT NULL,
    category_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_expenses PRIMARY KEY (id),
    CONSTRAINT ck_expenses_amount_positive CHECK (amount > 0),
    CONSTRAINT fk_expenses_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_expenses_category_id_categories FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL
);
CREATE INDEX ix_expenses_category_id ON expenses (category_id);
CREATE INDEX ix_expenses_owner_id_expense_date ON expenses (owner_id, expense_date);
```

---

## File: app/models/__init__.py

### What this file is for

A folder becomes a Python **package** (something you can `import`) only when it
contains a file named `__init__.py`. This file does two jobs. First, it makes
`app/models/` importable as `app.models`. Second, it imports every model class
into one place, so that one line, `import app.models`, loads **all** tables.
That matters for Alembic: `alembic/env.py` does exactly `import app.models` so
that `Base.metadata` knows about every table before autogenerate compares it
with the real database.

Who imports it: `alembic/env.py` (`import app.models`). The routers and
`app/core/dependencies.py` import the model files directly
(`from app.models.user import User`, and so on), which also works because
importing `app.models.user` runs this `__init__.py` first.

What it imports: the three model modules in this folder.

### The whole file

```python
"""
models/ - Database tables, written as SQLAlchemy ORM models (one file per table).

    user.py      -> `users` table: accounts that can log in
    category.py  -> `categories` table: each user's own expense categories
    expense.py   -> `expenses` table: the money a user spent

Every model is imported here so that `import app.models` registers all the
tables on `Base.metadata`. Alembic relies on that for autogenerate.
"""

from app.models.category import Category
from app.models.expense import Expense, PaymentMethod
from app.models.user import User

__all__ = ["Category", "Expense", "PaymentMethod", "User"]
```

### Walkthrough, block by block

#### Block 1: the module docstring

```python
"""
models/ - Database tables, written as SQLAlchemy ORM models (one file per table).

    user.py      -> `users` table: accounts that can log in
    category.py  -> `categories` table: each user's own expense categories
    expense.py   -> `expenses` table: the money a user spent

Every model is imported here so that `import app.models` registers all the
tables on `Base.metadata`. Alembic relies on that for autogenerate.
"""
```

- `"""` ... `"""` - three double quotes start and end a multi-line string. A
  string that is the very first thing in a file is called the **module
  docstring**. Python stores it in `app.models.__doc__`. It does nothing when
  the program runs; it is a note for the person reading.
- `models/ - Database tables, written as SQLAlchemy ORM models` - tells the
  reader what the folder contains. **ORM** means "Object Relational Mapper":
  a library that maps Python objects to database rows. SQLAlchemy is the ORM
  used here.
- `(one file per table)` - the organisation rule of this folder.
- `user.py -> users table ...`, `category.py -> ...`, `expense.py -> ...` - a
  small table of contents: which file makes which database table.
- `Every model is imported here so that import app.models registers all the
  tables on Base.metadata.` - explains the reason for the three import lines
  below. `Base.metadata` is the list of all tables that SQLAlchemy knows about
  (see doc 05 for `Base`). A table is added to that list the moment its class
  is defined, which happens when its file is imported.
- `Alembic relies on that for autogenerate.` - `alembic revision --autogenerate`
  compares `Base.metadata` with the real database. If a model file was never
  imported, its table is missing from `Base.metadata`, and Alembic would
  think the table should be **dropped**.

**Why it is here:** so the next developer understands the folder without
opening every file.

**If you removed or changed it:** nothing changes at runtime. The code works
the same. Only the explanation is lost.

#### Block 2: import Category

```python
from app.models.category import Category
```

- `from` - Python keyword: "take something out of a module".
- `app.models.category` - the module path. `app` is the top folder, `models`
  is this folder, `category` is the file `category.py`. Dots separate folder
  levels.
- `import` - Python keyword: "load it into this file".
- `Category` - the class defined inside `category.py`. After this line,
  `app.models.Category` exists, and `category.py` has been executed, so the
  `categories` table is registered on `Base.metadata`.

**Why it is here:** two reasons. (1) Running this file (which happens on
`import app.models`) must load every table for Alembic. (2) It lets other code
write the shorter `from app.models import Category` if it wants to.

**If you removed or changed it:** `import app.models` would no longer load
`category.py`. In `alembic/env.py` the `categories` table would be missing from
`Base.metadata`, so `alembic revision --autogenerate` would generate a migration
that **drops** the `categories` table. The API itself would still run, because
`app/routers/categories.py` imports `app.models.category` directly.

#### Block 3: import Expense and PaymentMethod

```python
from app.models.expense import Expense, PaymentMethod
```

- `from app.models.expense import` - same pattern as Block 2, now for the file
  `expense.py`.
- `Expense` - the class for the `expenses` table.
- `,` - a comma lets you import several names in one line.
- `PaymentMethod` - not a table. It is the small list of allowed payment
  methods (`cash`, `card`, ...), defined in the same file. It is re-exported
  here because `app/schemas/expense.py` and `app/routers/expenses.py` use it.

**Why it is here:** same as Block 2: registers the `expenses` table and makes
the names available from `app.models`.

**If you removed or changed it:** same consequence as Block 2, for the
`expenses` table. If you removed only `PaymentMethod` from the line, the only
thing that breaks is `from app.models import PaymentMethod` (no file in this
project writes that; they import from `app.models.expense` directly), and the
name would also disappear from `__all__` checks (Block 5).

#### Block 4: import User

```python
from app.models.user import User
```

- `from app.models.user import User` - loads `user.py` and takes the `User`
  class out of it.

Notice the order of the three imports: `category`, `expense`, `user` - that is
alphabetical order, nothing more. The order does **not** matter for
correctness, because each model file only needs `Base`, and the links between
models (`relationship(...)`) are resolved later, by class name, once all
classes exist. (We will see exactly how in `user.py`, Block 7 and Block 15.)

**Why it is here:** registers the `users` table and exports `User`.

**If you removed or changed it:** same consequence as Block 2, for the `users`
table. Alembic autogenerate would try to drop `users`.

#### Block 5: `__all__`

```python
__all__ = ["Category", "Expense", "PaymentMethod", "User"]
```

- `__all__` - a special variable name that Python looks at. The double
  underscores on both sides ("dunder") mark it as a name with a meaning to
  Python itself. `__all__` answers one question: *"when somebody writes
  `from app.models import *`, which names should the star bring in?"*
- `=` - assignment.
- `[` ... `]` - a Python list.
- `"Category", "Expense", "PaymentMethod", "User"` - four **strings** (note the
  quotes). They are the names, as text, not the classes themselves. They are
  listed alphabetically.

Verified: `from app.models import *` in a fresh namespace brings in exactly
`['Category', 'Expense', 'PaymentMethod', 'User']`.

`__all__` has a second, human use: it is the official "public list" of the
package. Tools such as linters and IDEs read it, and a developer reading the
file sees at once what the package offers.

**Why it is here:** it declares the public names of the package, so star
imports and tools behave predictably. It also stops linters from complaining
that the four imports above are "unused" (they are there to be re-exported).

**If you removed or changed it:** `from app.models import *` would still work,
but Python would then export *every* name that does not start with an
underscore - the four classes, yes, but also the sub-modules `category`,
`expense`, `user`, which you did not mean to export. If you misspelled a name
inside the list, for example `"Users"`, then `from app.models import *` would
raise `AttributeError: module 'app.models' has no attribute 'Users'`.

### Compared to your old code

Your old project had no `models/` folder and no `__init__.py`. Everything lived
in one file:

```python
# old: app/model.py (top of file)
from app.database import Base
from sqlalchemy import Column , Integer , String , Boolean,TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped , mapped_column, relationship
from sqlalchemy.sql.expression import text
from datetime import time

class Post(Base):
    ...

class User(Base):
    ...
```

and your old `alembic/env.py` did `from app.model import Base`.

What is different and why:

- **One file per table.** With two tables one file is fine. With three tables,
  each having comments, constraints and relationships, one file becomes long
  and hard to scan. Separate files also make `git diff` and code review easier:
  a change to expenses touches only `expense.py`.
- **A package needs a glue file.** Once the models are split, something must
  import all of them for Alembic. That is the whole reason `__init__.py` has
  those three import lines. Your old `env.py` imported `Base` from `app.model`,
  which, as a side effect, defined both tables. The new `env.py` imports
  `Base` from `app.database.base` (which defines *no* tables) and then
  `import app.models` (which defines all of them). The two jobs are separated
  on purpose: `Base` can be imported anywhere without dragging in every table.
- `from datetime import time` in the old file was never used. Unused imports
  are harmless but confusing; the new files import only what they use.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| package | a folder with an `__init__.py`, importable with dots: `app.models` |
| `__init__.py` | the file Python runs when the package is imported |
| module docstring | the `"""..."""` text at the top of a file; a note, no runtime effect |
| `Base.metadata` | SQLAlchemy's list of all known tables; filled when model classes are defined |
| re-export | importing a name into `__init__.py` so others can import it from the package |
| `__all__` | list of names that `from package import *` brings in; the package's public list |
| autogenerate | Alembic comparing `Base.metadata` with the real database to write a migration |

---

## File: app/models/user.py

### What this file is for

This file defines the `users` table as the Python class `User`. One row of
`users` is one account that can log in. A user owns categories and expenses;
this file also declares those two links (`User.categories`, `User.expenses`)
so that, in Python, you can write `some_user.expenses` and get a list.

Who imports it: `app/core/dependencies.py` (to load the current user from the
JWT), `app/routers/auth.py` (register and login), `app/routers/users.py`
(`/users/me`), and `app/models/__init__.py`.

What it imports: `datetime` (for the type of `created_at`), `TYPE_CHECKING`
(a trick explained in Block 3), column types and helpers from `sqlalchemy`,
the mapping tools from `sqlalchemy.orm`, and `Base` from `app/database/base.py`.

### The whole file

```python
"""`users` table: an account that owns categories and expenses."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.expense import Expense


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercase so "A@x.com" and "a@x.com" are the same account.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    # Never the plain password - only the Argon2 hash.
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Set to False to block a user from logging in without deleting their data.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # passive_deletes=True lets the database's ON DELETE CASCADE remove the
    # rows instead of SQLAlchemy loading and deleting them one by one.
    categories: Mapped[list["Category"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
```

### Walkthrough, block by block

#### Block 1: the module docstring

```python
"""`users` table: an account that owns categories and expenses."""
```

- `"""..."""` - the module docstring (explained in `__init__.py`, Block 1).
- `` `users` table `` - the backticks are just Markdown-style quoting inside the
  text; they mean "the thing named users". It names the table this file makes.
- `an account that owns categories and expenses` - the one-sentence meaning of
  a row in this table.

**Why it is here:** a one-line summary for the reader.

**If you removed or changed it:** no runtime change.

#### Block 2: import datetime

```python
from datetime import datetime
```

- `from datetime import datetime` - Python's standard library module is called
  `datetime`, and inside it there is a **class** also called `datetime`. The
  class represents one moment in time: year, month, day, hour, minute, second,
  microsecond, and optionally a time zone. Example: `2026-10-06 11:39:44+00:00`.
- It is used only in one place: the type hint `Mapped[datetime]` on
  `created_at` (Block 14).

**Why it is here:** SQLAlchemy reads the Python type inside `Mapped[...]` and
uses it to decide the column type. For `datetime` the default column type is
`DateTime`. Also, when a row is loaded, `user.created_at` will be a real
`datetime` object, so you can compare it, format it, and so on.

**If you removed or changed it:** Python would raise
`NameError: name 'datetime' is not defined` the moment `class User` is defined
(annotations are evaluated when SQLAlchemy inspects the class). The app would
not start.

#### Block 3: import TYPE_CHECKING

```python
from typing import TYPE_CHECKING
```

- `typing` - Python's standard library module for type hints (the `: int`,
  `-> str` notes that say what type a variable holds).
- `TYPE_CHECKING` - a constant inside `typing`. Its value is **always `False`
  when the program runs**. (Verified: `typing.TYPE_CHECKING` prints `False`.)
  Type-checker tools such as mypy and Pylance (the thing that gives you
  autocomplete in VS Code) pretend it is `True` while they read your code.

So `if TYPE_CHECKING:` means: *"the next lines are only for the type checker
and editor; Python itself skips them."* We use that in Block 7.

**Why it is here:** needed for Block 7, which is the standard solution to a
"circular import" problem. Explained fully there.

**If you removed or changed it:** `NameError: name 'TYPE_CHECKING' is not
defined` at import time; the app would not start.

#### Block 4: import column types and SQL helpers

```python
from sqlalchemy import Boolean, DateTime, String, func, true
```

- `sqlalchemy` - the ORM library. The top-level package exports the most used
  names so you do not need to know the inner folders.
- `Boolean` - a column type: `True`/`False`. In PostgreSQL it becomes `BOOLEAN`.
- `DateTime` - a column type: a date plus a time. Called as `DateTime(timezone=True)`
  it becomes `TIMESTAMP WITH TIME ZONE` in PostgreSQL (Block 14).
- `String` - a column type: text with a maximum length. `String(255)` becomes
  `VARCHAR(255)`.
- `func` - a special object. Any attribute you ask it for becomes a **SQL
  function call** with that name: `func.now()` means the SQL `now()`,
  `func.count()` means `count()`, `func.lower(x)` means `lower(x)`.
  Verified: `str(func.now().compile(dialect=postgresql))` prints `now()`.
  SQLAlchemy does not check that the function exists; it just writes the name
  into the SQL and lets the database decide.
- `true` - a small function that returns the SQL constant `true`. In
  PostgreSQL it renders as the word `true`; in SQLite, which has no boolean
  type, it renders as `1`. (Verified both.) It is used as a server default in
  Block 13.

**Why it is here:** these are the column types and SQL expressions this file
needs. Importing exactly what you use keeps the file readable and lets your
editor warn you about typos.

**If you removed or changed it:** `NameError` for whichever name is missing,
when the class body runs. For example without `true`:
`NameError: name 'true' is not defined` at line 26.

#### Block 5: import the mapping tools

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

- `sqlalchemy.orm` - the "ORM" sub-package: the part of SQLAlchemy that maps
  classes to tables (the other part, `sqlalchemy` core, is about raw SQL).
- `Mapped` - a **generic type** used in annotations. "Generic" means it takes
  another type inside square brackets: `Mapped[int]`, `Mapped[str]`,
  `Mapped[list["Category"]]`. `Mapped[int]` says: *"this attribute is mapped to
  the database, and in Python it holds an `int`."* SQLAlchemy 2.0 reads these
  annotations to build the table. Full explanation in Block 9.
- `mapped_column` - a function that creates one **column**. The annotation
  gives the Python type; `mapped_column(...)` gives the database details
  (length, primary key, default, index...). Full explanation in Block 9.
- `relationship` - a function that creates a **link to another model** (not
  a column). `User.categories` is a relationship: it is not stored in the
  `users` table; it is computed from `categories.owner_id`. Full explanation in
  Block 15.

**Why it is here:** these three names are the whole "SQLAlchemy 2.0 declarative
style". Every model file uses them.

**If you removed or changed it:** `NameError` at the first column definition
(line 19), the app would not start.

#### Block 6: import Base

```python
from app.database.base import Base
```

- `app.database.base` - the file `app/database/base.py` (doc 05).
- `Base` - the class every model inherits from. It carries `metadata`, the
  registry of tables, with the naming convention for indexes and constraints.

**Why it is here:** `class User(Base)` (Block 8) needs it. Inheriting from
`Base` is what turns a plain class into a table definition and adds the table
to `Base.metadata`.

**If you removed or changed it:** `NameError: name 'Base' is not defined`
at `class User(Base):`. If you instead made your own `Base` here, `User` would
be registered on a different `metadata` and Alembic would not see the table.

#### Block 7: imports only for the type checker

```python
if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.expense import Expense
```

- `if` - Python keyword: run the indented lines only when the condition is true.
- `TYPE_CHECKING` - always `False` at runtime (Block 3). So **Python never runs
  these two imports**. Your editor and mypy, which treat it as `True`, do read
  them, and that is how they know what `"Category"` and `"Expense"` in
  Block 15 and Block 16 mean, so they can autocomplete `user.categories[0].name`.
- `from app.models.category import Category` - the class for the `categories`
  table.
- `from app.models.expense import Expense` - the class for the `expenses` table.

Why not import them normally? Because of a **circular import**. Look at the
chain: `user.py` wants `Category` from `category.py`. But `category.py` wants
`User` from `user.py` (for its `owner` relationship). If both files imported
each other at the top, Python would start loading `user.py`, pause at line 12
to load `category.py`, which at its line 13 would ask for `User` from
`user.py` - but `user.py` is only half loaded and `class User` has not been
reached yet. Verified error with two tiny modules that import each other:

```
ImportError: cannot import name 'A' from partially initialized module 'pkg.a'
(most likely due to a circular import)
```

With `if TYPE_CHECKING:` the imports never run, so there is no circle. But
then how does SQLAlchemy know what `"Category"` is in Block 15? Because the
name is given as a **string** in quotes. SQLAlchemy does not look it up when
the class is defined. It looks it up later, by name, in the registry attached
to `Base`, at the moment the mappers are "configured" (the first time you
query or create an object). By then `__init__.py` has imported all three files,
so `Category` is found. We verified the error you get if the class was
never imported anywhere:

```
InvalidRequestError: When initializing mapper Mapper[User(users)],
expression 'Category' failed to locate a name ('Category').
```

**Why it is here:** gives the editor and type checker the real classes for
`"Category"` and `"Expense"` without creating a circular import at runtime.

**If you removed or changed it:** at runtime nothing breaks (SQLAlchemy
resolves the strings by name anyway). You would lose autocomplete and type
checking on `user.categories` / `user.expenses`. If you moved the two imports
*out* of the `if` block, you would get the circular `ImportError` shown above
as soon as anything imports `app.models.user`.

#### Block 8: the class and its table name

```python
class User(Base):
    __tablename__ = "users"
```

- `class` - Python keyword: define a new class (a blueprint for objects).
- `User` - the class name. Convention: singular, CapitalWords. One `User`
  object is one row.
- `(Base)` - the parent class in parentheses. "`User` inherits from `Base`."
  Because `Base` is a SQLAlchemy `DeclarativeBase`, defining this class
  immediately creates a `Table` object and registers it on `Base.metadata`.
- `:` - starts the class body; everything indented below belongs to the class.
- `__tablename__` - a special attribute name SQLAlchemy looks for (dunder, like
  `__all__`). It is the real table name in the database.
- `=` - assignment.
- `"users"` - a string. Convention: plural, lowercase. The class is `User`, the
  table is `users`.

**Why it is here:** this is the line that says "there is a table called
`users`". All the columns below are attached to it.

**If you removed or changed it:** without `__tablename__` SQLAlchemy raises
`InvalidRequestError: Class <class 'app.models.user.User'> does not have a
__table__ or __tablename__ specified and does not inherit from an existing
table-mapped class.` If you changed the string to `"user"`, note that `user`
is a **reserved word in PostgreSQL** (`SELECT user` returns the current
database user). SQLAlchemy would then have to write `"user"` with double quotes
in every statement, and so would you in any hand-written SQL. Your old project
used `"user"`; see "Compared to your old code" below. Also the foreign keys in
`category.py` and `expense.py` say `ForeignKey("users.id")` - the string
`"users"` must match exactly, or you get
`NoReferencedTableError: Foreign key associated with column 'categories.owner_id' could not find table 'users'`.

#### Block 9: the primary key (and what `Mapped` / `mapped_column` mean)

```python
    id: Mapped[int] = mapped_column(primary_key=True)
```

Read this line in three parts: `id`, then `: Mapped[int]`, then
`= mapped_column(primary_key=True)`.

- `id` - the attribute name, which becomes the **column name** `id`.
- `:` - in Python, a colon after a variable name starts a **type annotation**
  (a note about the type). On its own, an annotation does nothing. SQLAlchemy
  reads it.
- `Mapped` - the generic type from `sqlalchemy.orm` (Block 5). "Mapped" means
  "this attribute is mapped to a database column or relationship".
- `[` `]` - square brackets after a generic type give the inner type.
- `int` - Python's integer type. So `Mapped[int]` means "a database column
  whose Python value is an int".
- `=` - assignment. The right side is the column definition.
- `mapped_column` - the function that builds a column (Block 5).
- `(` `)` - call the function with the arguments inside.
- `primary_key` - a **keyword argument**: an argument given by name,
  `name=value`.
- `True` - Python's boolean "yes".

**How SQLAlchemy turns this into a column.** It looks at the annotation and
the arguments together:

1. **Type.** No type was passed to `mapped_column`, so SQLAlchemy takes the
   Python type from `Mapped[int]` and looks it up in its default type map.
   Verified from the library (`sqlalchemy.sql.sqltypes._type_map`):

   | Python type inside `Mapped[...]` | Column type SQLAlchemy picks |
   | --- | --- |
   | `int` | `Integer()` |
   | `str` | `String()` (no length) |
   | `bool` | `Boolean()` |
   | `float` | `Float()` |
   | `Decimal` | `Numeric()` |
   | `date` | `Date()` |
   | `datetime` | `DateTime()` |
   | `bytes` | `LargeBinary()` |

   So `Mapped[int]` gives `Integer`. If you *do* pass a type to
   `mapped_column` (like `String(255)` in Block 10), that wins, and the
   annotation is then only used for the Python side and for the NULL rule below.

2. **NULL or NOT NULL.** This is the part that surprises most people. The
   **Python type decides `nullable`**. `Mapped[int]` has no `None` in it, so
   the column is `NOT NULL`. `Mapped[int | None]` (read `|` as "or") would
   allow NULL. Verified in the library source
   (`sqlalchemy/orm/properties.py`):

   ```python
   nullable = includes_none(argument)      # does the annotation allow None?
   if not self._has_nullable:              # unless nullable=... was given explicitly
       self.column.nullable = nullable
   ```

   `includes_none` returns `True` for `X | None`, `Optional[X]`, and the same
   written as a string. An explicit `nullable=` argument to `mapped_column`
   always wins over the annotation.

3. **Primary key.** `primary_key=True` makes this the row identifier: unique,
   never NULL, and (for an `Integer` primary key) **auto-numbered** by the
   database. In PostgreSQL this becomes `id SERIAL NOT NULL` plus
   `CONSTRAINT pk_users PRIMARY KEY (id)`. (`SERIAL` is PostgreSQL's shorthand
   for "integer that counts up by itself".) The constraint name `pk_users`
   comes from the naming convention `pk_%(table_name)s` in
   `app/database/base.py`.

Because the database gives the number, you never set `id` yourself. After
`db.add(user); db.commit()` SQLAlchemy reads it back; verified SQL:

```sql
INSERT INTO users (email, full_name, hashed_password, is_active)
VALUES (?, ?, ?, ?) RETURNING id, created_at
```

**Why it is here:** every table needs a primary key so a row can be found,
updated, deleted, and pointed at by foreign keys (`categories.owner_id`
references `users.id`).

**If you removed or changed it:** with no primary key at all SQLAlchemy raises
`ArgumentError: Mapper Mapper[User(users)] could not assemble any primary key
columns for mapped table 'users'`. If you wrote `Mapped[int | None]` the
annotation would ask for NULL, but PostgreSQL ignores that on a primary key
(a primary key is always NOT NULL), so it would only be misleading.

#### Block 10: email

```python
    # Stored lowercase so "A@x.com" and "a@x.com" are the same account.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
```

- `# Stored lowercase ...` - a comment (`#` starts a comment; Python ignores
  the rest of the line). It tells you a rule that is enforced **elsewhere**:
  `app/routers/auth.py` does `user_in.email.lower()` before saving and
  `credentials.username.lower()` before looking up. The database does not
  lowercase anything itself.
- `email` - column name.
- `Mapped[str]` - Python type `str`, no `None`, so `NOT NULL`.
- `mapped_column(...)` - the column.
- `String(255)` - the column type, passed explicitly. `String` is the class
  from Block 4; `255` is the maximum number of characters. PostgreSQL makes
  this `VARCHAR(255)`. 255 is a long-standing conventional upper bound for an
  email address (the schema in `app/schemas/user.py` uses Pydantic's
  `EmailStr`, which rejects nonsense before it gets here).
- `unique=True` - no two rows may have the same email.
- `index=True` - create an **index** on this column. An index is a sorted
  lookup structure the database keeps next to the table so that
  `WHERE email = ...` is fast even with millions of rows. Login does exactly
  that query.

`unique=True` together with `index=True` makes SQLAlchemy create a **unique
index** instead of a separate UNIQUE constraint. Verified DDL:
`CREATE UNIQUE INDEX ix_users_email ON users (email)`. The name
`ix_users_email` comes from the convention `ix_%(column_0_label)s`.

**Why it is here:** the email is the login name. It must exist (NOT NULL), be
unique (one account per address), and be fast to look up (index).

**If you removed or changed it:** without `unique=True`, two people could
register the same email and login would find two rows (`db.scalar` would just
return the first one). The register endpoint also checks for an existing
email before inserting, but two requests at the same instant can both pass
that check; the unique index is the real guard - then PostgreSQL raises an
`IntegrityError` and the endpoint answers 409. Without `index=True` the unique
index becomes a unique constraint (PostgreSQL still builds an index behind it,
so speed is similar; the difference is only the name and the kind of object).
If you dropped `String(255)` and left `Mapped[str]`, the type would be
`VARCHAR` with no limit - fine in PostgreSQL, invalid in MySQL.

#### Block 11: full_name

```python
    full_name: Mapped[str] = mapped_column(String(100))
```

- `full_name` - column name.
- `Mapped[str]` - a `str`, NOT NULL.
- `mapped_column(String(100))` - `VARCHAR(100)`. The schema
  (`app/schemas/user.py`) limits the name to 100 characters too, so the two
  agree.

**Why it is here:** the display name shown in the profile (`/users/me`).

**If you removed or changed it:** `app/schemas/user.py` (`UserResponse`) has a
`full_name` field; building the response from a `User` without that attribute
would fail with a validation error. If a name longer than 100 characters ever
reached the database (it cannot, because the schema stops it at 100),
PostgreSQL would raise `value too long for type character varying(100)`.

#### Block 12: hashed_password

```python
    # Never the plain password - only the Argon2 hash.
    hashed_password: Mapped[str] = mapped_column(String(255))
```

- `# Never the plain password ...` - comment: the value stored here is the
  **hash** (a one-way scrambled form) produced in `app/core/security.py` with
  Argon2 (doc 04). You cannot get the password back from the hash; you can
  only check whether a given password produces the same hash.
- `hashed_password` - column name. The name itself reminds you it is a hash.
- `Mapped[str]` - `str`, NOT NULL: an account must have a password hash.
- `String(255)` - `VARCHAR(255)`. An Argon2 hash string is around 100
  characters; 255 leaves room.

**Why it is here:** login needs something to compare the typed password
against, and storing the plain password would be a serious security bug.

**If you removed or changed it:** register (`auth.py`) sets
`hashed_password=...` when building the `User`; without the column that would
raise `TypeError: 'hashed_password' is an invalid keyword argument for User`.
Login would have nothing to verify. If the column were too short, PostgreSQL
would reject the insert with `value too long for type character varying(n)`.

#### Block 13: is_active (Python default vs server default)

```python
    # Set to False to block a user from logging in without deleting their data.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
```

- `# Set to False to block ...` - comment: this is a "soft disable" switch.
  `app/core/dependencies.py` line 50 (`if user is None or not user.is_active`)
  and `app/routers/auth.py` line 67 refuse inactive users.
- `is_active` - column name.
- `Mapped[bool]` - Python `bool`, NOT NULL.
- `Boolean` - the column type (Block 4), given explicitly. `BOOLEAN` in PostgreSQL.
- `default=True` - a **Python-side default**. When you create
  `User(email=..., ...)` and do not pass `is_active`, SQLAlchemy fills in
  `True` *in Python* and sends it in the `INSERT`. Verified: the INSERT above
  includes `is_active` with value `True` even though the code never set it.
- `server_default=true()` - a **database-side default**. It becomes part of
  the `CREATE TABLE`: `is_active BOOLEAN DEFAULT true NOT NULL`. The database
  applies it when an `INSERT` does not mention the column at all - for example
  a row inserted by hand in `psql`, or by a migration, or by another program.
- `true()` - the SQL constant (Block 4). It is called with `()` because it is
  a function that returns the expression object.

**`default` vs `server_default` vs `onupdate` - the three kinds of default:**

| Argument | Who fills the value | When |
| --- | --- | --- |
| `default=` | SQLAlchemy, in Python | on INSERT, if the attribute was not set |
| `server_default=` | the database | on INSERT, if the column is missing from the statement; also written into `CREATE TABLE` |
| `onupdate=` | SQLAlchemy, in Python (or as SQL in the UPDATE) | on every UPDATE of the row (used in `expense.py`, Block 24) |

Having both `default` and `server_default` is deliberate: the Python default
makes `user.is_active` already `True` on the object before it is even saved,
and the server default makes the table itself safe for rows that do not come
through SQLAlchemy.

**Why it is here:** lets an admin block an account (set `is_active = false`)
without deleting the user's categories and expenses.

**If you removed or changed it:** without `default=True`, SQLAlchemy would
leave `is_active` out of the INSERT and the database would fill `true`
(verified on a test model: the statement becomes
`INSERT INTO t DEFAULT VALUES RETURNING id, flag`, and the value is read
back). The only difference is that `user.is_active` is `None` in Python
between `User(...)` and the flush, so any code that checked it before saving
would see `None` instead of `True`. Without `server_default`, a hand-written `INSERT INTO users (email, ...)` that omits
`is_active` would fail with `null value in column "is_active" violates
not-null constraint`. Without the whole column, `dependencies.py` would raise
`AttributeError: 'User' object has no attribute 'is_active'` on every
authenticated request.

#### Block 14: created_at

```python
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- `created_at` - column name: when the row was created.
- `Mapped[datetime]` - Python type `datetime` (Block 2), NOT NULL.
- `mapped_column(` ... `)` - split over three lines; Python allows line breaks
  inside parentheses.
- `DateTime(timezone=True)` - the column type. `DateTime` is the class from
  Block 4. `timezone=True` asks for a type that stores the time zone offset.
  In PostgreSQL that is `TIMESTAMP WITH TIME ZONE` (often written
  `timestamptz`). Without `timezone=True` you would get plain `TIMESTAMP`,
  which stores "11:39" with no idea whether that is 11:39 in Delhi or in
  London. With time zone, PostgreSQL stores the instant in UTC and gives it
  back with an offset, so the value is unambiguous.
- `server_default=func.now()` - the database fills the value with the SQL
  function `now()` (the current time on the database server, at the start of
  the transaction). Verified DDL:
  `created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL`.
- `func.now()` - `func` from Block 4; `.now` picks the function name;
  `()` calls it with no arguments. Result: the SQL text `now()`.

Because there is no Python `default`, SQLAlchemy does not send the column in
the INSERT; instead it adds `RETURNING id, created_at` so the object gets the
database's value right away (see the INSERT in Block 9).

**Why it is here:** auditing - knowing when an account was created. The value
is in `UserResponse`, so `/users/me` shows it.

**If you removed or changed it:** without `server_default`, the column is NOT
NULL and nothing fills it, so every register would fail with
`null value in column "created_at" violates not-null constraint`. Without
`timezone=True`, the API would return times with no offset, and clients in
different time zones would show different clock times for the same event.

#### Block 15: the `categories` relationship

```python
    # passive_deletes=True lets the database's ON DELETE CASCADE remove the
    # rows instead of SQLAlchemy loading and deleting them one by one.
    categories: Mapped[list["Category"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
```

This is **not a column**. There is no `categories` column in the `users`
table (check the DDL at the top). It is a Python-side link that SQLAlchemy
computes from the foreign key `categories.owner_id -> users.id`.

- `# passive_deletes=True lets ...` - comment explaining the last argument;
  details below.
- `categories` - the attribute name. `user.categories` will be a Python list of
  `Category` objects.
- `Mapped[list["Category"]]` - annotation. `list[...]` says this side holds
  **many** items (a list), so SQLAlchemy sets this up as a **one-to-many**
  relationship (one user, many categories). Verified:
  `User.categories: direction=ONETOMANY, uselist=True, collection_class=list`.
- `"Category"` - the target class name, **as a string**, because the real class
  is not imported at runtime (Block 7). SQLAlchemy resolves the string by name
  later.
- `relationship(` ... `)` - the function from Block 5.
- `back_populates="owner"` - "the other side of this link is the attribute
  called `owner` on `Category`". `Category.owner` says
  `back_populates="categories"` back. With the two sides joined like this,
  SQLAlchemy keeps them in sync **in memory**: verified that after
  `user.categories.append(cat)`, `cat.owner is user` is already `True` before
  anything is saved, and after `db.flush()` the foreign key `cat.owner_id`
  equals `user.id`. Without `back_populates`, the FK is still written at flush,
  but `cat.owner` would stay `None` until reloaded from the database
  (verified with a test pair of models).
- `cascade="all, delete-orphan"` - a comma-separated list of **cascade rules**:
  which Session operations on the parent (`User`) should also apply to the
  children (`Category`). From the library's own docstring: `all` is shorthand
  for `save-update, merge, refresh-expire, expunge, delete`, and the default
  (when you do not pass `cascade`) is only `save-update, merge`. In plain
  words:
  - `save-update`: `db.add(user)` also adds the categories in `user.categories`.
  - `merge`, `refresh-expire`, `expunge`: the same idea for `db.merge`,
    `db.refresh` / `db.expire`, and `db.expunge`.
  - `delete`: `db.delete(user)` also deletes the categories.
  - `delete-orphan`: a category **removed from the list** (no longer belongs
    to any user) is deleted. Verified: `user.categories.remove(cat)` then
    `db.commit()` ran `DELETE FROM categories WHERE categories.id = ?`.
- `passive_deletes=True` - "when the parent is deleted, do **not** load the
  children to delete them one by one; trust the database to do it". From the
  library docstring: *"A value of True indicates that unloaded child items
  should not be loaded during a delete operation on the parent... Marking
  this flag as True usually implies an ON DELETE <CASCADE|SET NULL> rule is in
  place."* The `categories.owner_id` foreign key has `ondelete="CASCADE"`
  (`category.py`, Block 13), so the database deletes the children itself.

  Verified difference. With `passive_deletes=True`, `db.delete(user)` sent
  exactly one statement:

  ```sql
  DELETE FROM users WHERE users.id = ?
  ```

  and afterwards the user's expenses and categories were gone (the database
  did it). Without `passive_deletes`, the same delete on a test parent with
  three children sent:

  ```sql
  SELECT p.id ... FROM p WHERE p.id = ?
  SELECT k.id, k.p_id FROM k WHERE ? = k.p_id      -- load every child
  DELETE FROM k WHERE k.id = ?   [(1,), (2,), (3,)] -- delete each one
  DELETE FROM p WHERE p.id = ?
  ```

  For a user with ten thousand expenses that is ten thousand rows loaded into
  memory for nothing.

One more property, not written but important: `relationship()` defaults to
`lazy="select"` (verified). That means `user.categories` is **not** loaded
when the user is loaded; the first time you touch `user.categories`,
SQLAlchemy runs a separate `SELECT ... FROM categories WHERE ? = categories.owner_id`.
This is called **lazy loading**.

**Why it is here:** gives the Python-side convenience `user.categories`, and
declares what should happen to a user's categories when the user object is
deleted through SQLAlchemy. No endpoint deletes a user today; the rule is
here so the model is already correct when one is added, and so that a delete
from any code path stays cheap.

**If you removed or changed it:** without the whole relationship,
`category.py` would fail at mapper configuration with
`InvalidRequestError: Mapper 'Mapper[User(users)]' has no property 'categories'`
because `Category.owner` says `back_populates="categories"`. Without
`passive_deletes=True`, deleting a user still works but loads and deletes
every child row first (SQL shown above). Without `delete-orphan`, removing a
category from `user.categories` would try to set `categories.owner_id` to
NULL, which the NOT NULL column rejects
(`IntegrityError: NOT NULL constraint failed: categories.owner_id`).

#### Block 16: the `expenses` relationship

```python
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
```

- `expenses` - attribute name; `user.expenses` is a list of `Expense` objects.
- `Mapped[list["Expense"]]` - one-to-many, target class `Expense` by name.
  Verified: `User.expenses: direction=ONETOMANY, uselist=True`.
- `relationship(` ... `)` - same function.
- `back_populates="owner"` - the other side is `Expense.owner` (`expense.py`,
  Block 25).
- `cascade="all, delete-orphan"` - same rules as Block 15.
- `passive_deletes=True` - same reason: `expenses.owner_id` has
  `ondelete="CASCADE"` (`expense.py`, Block 21).

**Why it is here:** same as Block 15, for expenses.

**If you removed or changed it:** same failure modes as Block 15, with
`Expense.owner` complaining that `User` has no property `expenses`.

### Compared to your old code

Your old `User` model:

```python
# old: app/model.py
class User(Base):
    __tablename__ = "user"

    id : Mapped[int] = mapped_column(Integer,primary_key=True, nullable=True)
    email : Mapped[str] = mapped_column(String,nullable=False, unique=True)
    password : Mapped[str] = mapped_column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    phone = Column(Integer(), nullable=False)
```

I compiled this old class for PostgreSQL to see exactly what it produces:

```sql
CREATE TABLE "user" (
    id SERIAL,
    email VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    phone INTEGER NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (email)
)
```

What is different, and why:

1. **Table name `"user"` vs `users`.** `user` is a reserved word in
   PostgreSQL, so SQLAlchemy has to quote it (`"user"`, see the DDL). It works,
   but every hand-written query must also quote it, and errors are confusing.
   The new project uses `users` - plural, and not reserved.

2. **`nullable=True` on the primary key.** The old line
   `mapped_column(Integer, primary_key=True, nullable=True)` tells SQLAlchemy
   "id may be NULL" (verified: the column's `nullable` is `True`, and the DDL
   shows `id SERIAL` without `NOT NULL`). PostgreSQL ignores this, because
   `PRIMARY KEY` always means NOT NULL - so nothing broke, but the line says
   something that is not true. The new code just writes
   `mapped_column(primary_key=True)` and lets the type map pick `Integer`.

3. **No more `nullable=False` everywhere.** In the old code you wrote
   `nullable=False` on every column by hand. In the new code the annotation
   does it: `Mapped[str]` is NOT NULL, `Mapped[str | None]` allows NULL. Same
   result, less to type, and the Python type and the database rule can never
   disagree.

4. **Mixed styles.** Old `created_at` and `phone` use the older `Column(...)`
   style without `Mapped[...]`, while the other columns use `mapped_column`.
   Both work, but the editor cannot tell what type `user.created_at` is in the
   old style. The new code uses `Mapped[...] = mapped_column(...)` for every
   column.

5. **`server_default=text('now()')` vs `func.now()`.** Both produce
   `DEFAULT now()`. `text('now()')` is raw SQL text; `func.now()` is a
   SQLAlchemy expression object. The result is the same here. `func.now()`
   is preferred because it is the same object you can use inside queries and
   because SQLAlchemy knows it is a function, not arbitrary text.

6. **`String` without a length.** Old `email` and `password` are `VARCHAR`
   with no limit. PostgreSQL allows that; MySQL does not. The new code gives
   every string a length (`String(255)`, `String(100)`), which also documents
   the expected size.

7. **`password` renamed to `hashed_password`.** Same purpose. The new name
   makes it impossible to forget that the value is a hash.

8. **`phone` as `Integer` - a real bug, kindly.** PostgreSQL's `INTEGER` holds
   values up to 2,147,483,647 (about 2.1 billion). A ten-digit phone number
   such as 9876543210 is bigger than that (verified: `9876543210 > 2147483647`
   is `True`), so inserting it would fail with `integer out of range`. Also,
   integers drop leading zeros and cannot hold `+91`. Phone numbers are text,
   not numbers. The new project does not store a phone at all; if it did, it
   would be `String(20)`.

9. **`unique=True` without `index=True`.** The old code gets a `UNIQUE (email)`
   constraint with no explicit name; PostgreSQL invents one (`user_email_key`).
   The new code gets a named unique index, `ix_users_email`, from the naming
   convention, so a future migration can refer to it by a predictable name.

10. **New columns.** `full_name` (for the profile) and `is_active` (for
    blocking an account) did not exist in the old project.

11. **Relationships.** The old `User` had no relationships at all; only `Post`
    had a one-directional `owner = relationship("User")`. The new `User` has
    two-way links (`back_populates`) with explicit cascade and
    `passive_deletes` rules.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `Mapped[T]` | annotation: "this attribute is a database column/relationship holding a Python `T`" |
| `mapped_column(...)` | builds one column; the annotation gives the Python type, the arguments give DB details |
| type map | SQLAlchemy's table: `int -> Integer`, `str -> String`, `bool -> Boolean`, `datetime -> DateTime`, ... |
| nullable | whether a column may be NULL; decided by `\| None` in the annotation unless `nullable=` is given |
| `primary_key=True` | the row identifier; auto-numbered (`SERIAL`) for an Integer column |
| `unique=True` | no two rows may share this value |
| `index=True` | build a lookup index so `WHERE col = ...` is fast |
| `default=` | Python-side value filled by SQLAlchemy on INSERT |
| `server_default=` | database-side `DEFAULT ...` written into `CREATE TABLE` |
| `true()` | the SQL constant `true` (`1` on SQLite) |
| `func.now()` | the SQL function call `now()` |
| `DateTime(timezone=True)` | `TIMESTAMP WITH TIME ZONE`: stores an unambiguous instant |
| `TYPE_CHECKING` | `False` at runtime, `True` for type checkers; guards imports that would be circular |
| circular import | two files importing each other at the top; fails with "partially initialized module" |
| `relationship(...)` | a Python-side link to another model, computed from a foreign key; not a column |
| `back_populates` | names the attribute on the other model that is the same link seen from there |
| `cascade="all, delete-orphan"` | child objects follow the parent in add/delete, and are deleted when removed from the list |
| `passive_deletes=True` | on parent delete, do not load children; the database's `ON DELETE` rule handles them |
| lazy loading | the related list is fetched with a separate SELECT the first time you touch it |

---

## File: app/models/category.py

### What this file is for

This file defines the `categories` table as the class `Category`. A category
is a label a user gives to expenses: "Food", "Rent", "Travel". Each user has
their own list; two users can both have a "Food" category, but one user cannot
have "Food" twice. A category belongs to exactly one user (`owner_id`) and may
be attached to many expenses.

Who imports it: `app/routers/categories.py` (all `/categories` endpoints),
`app/routers/reports.py` (spending by category), and `app/models/__init__.py`.

What it imports: `datetime`, `TYPE_CHECKING`, column types and constraint
helpers from `sqlalchemy`, the mapping tools from `sqlalchemy.orm`, and `Base`.

### The whole file

```python
"""`categories` table: a user's own labels for grouping expenses (Food, Rent...)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.user import User


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        # A user cannot have two categories with the same name,
        # but two different users can both have "Food".
        UniqueConstraint("owner_id", "name", name="uq_categories_owner_id_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="categories")
    # Deleting a category keeps its expenses: the database sets their
    # category_id to NULL (see ON DELETE SET NULL in models/expense.py).
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="category", passive_deletes=True
    )
```

### Walkthrough, block by block

#### Block 1: the module docstring

```python
"""`categories` table: a user's own labels for grouping expenses (Food, Rent...)."""
```

- `"""..."""` - module docstring.
- `` `categories` table `` - names the table this file creates.
- `a user's own labels for grouping expenses (Food, Rent...)` - what one row
  means, with examples.

**Why it is here:** one-line summary for the reader.

**If you removed or changed it:** no runtime change.

#### Block 2: import datetime

```python
from datetime import datetime
```

- `from datetime import datetime` - the `datetime` class from the standard
  library module of the same name (see `user.py`, Block 2). Used in
  `Mapped[datetime]` for `created_at` (Block 14).

**Why it is here:** gives SQLAlchemy the Python type of `created_at`.

**If you removed or changed it:** `NameError: name 'datetime' is not defined`
when the class is defined.

#### Block 3: import TYPE_CHECKING

```python
from typing import TYPE_CHECKING
```

- `from typing import TYPE_CHECKING` - the constant that is `False` at runtime
  and `True` for type checkers (`user.py`, Block 3). Used in Block 7.

**Why it is here:** needed by the `if TYPE_CHECKING:` guard in Block 7.

**If you removed or changed it:** `NameError` at line 11.

#### Block 4: import column types and constraint helpers

```python
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
```

- `DateTime` - date-and-time column type (`user.py`, Block 4).
- `ForeignKey` - a class that marks a column as **pointing at a column in
  another table**. `ForeignKey("users.id")` means "values in this column must
  exist in `users.id`". The database enforces it: you cannot insert a category
  whose `owner_id` is not a real user id, and (depending on the `ondelete`
  rule) deleting the user does something to the category. Explained fully in
  Block 13.
- `String` - text column type with a maximum length.
- `UniqueConstraint` - a class for a **table-level** rule "the combination of
  these columns must be unique across rows". A column-level `unique=True` can
  only cover one column; `UniqueConstraint("owner_id", "name")` covers the
  pair. Explained in Block 9.
- `func` - the SQL function builder; `func.now()` is used for `created_at`.

**Why it is here:** these are the SQLAlchemy pieces this file uses.

**If you removed or changed it:** `NameError` for the missing name, at the
line where it is first used (`UniqueConstraint` at line 21, `String` at line
25, `ForeignKey` at line 28, `DateTime`/`func` at line 31).

#### Block 5: import the mapping tools

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

- `Mapped` - the annotation type: "this attribute is mapped to the database"
  (`user.py`, Block 5 and Block 9).
- `mapped_column` - builds one column.
- `relationship` - builds a link to another model.

**Why it is here:** used by every attribute of `Category`.

**If you removed or changed it:** `NameError` at line 24.

#### Block 6: import Base

```python
from app.database.base import Base
```

- `Base` - the declarative base class from `app/database/base.py` that every
  model inherits from (`user.py`, Block 6). It carries the naming convention
  that turns `name="amount_positive"` into `ck_expenses_amount_positive`, and
  so on.

**Why it is here:** `class Category(Base)` needs it to become a table.

**If you removed or changed it:** `NameError: name 'Base' is not defined`.

#### Block 7: imports only for the type checker

```python
if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.user import User
```

- `if TYPE_CHECKING:` - the lines inside never run; they exist for the editor
  and mypy (`user.py`, Block 7).
- `from app.models.expense import Expense` - so the type checker knows what
  `"Expense"` in Block 16 is.
- `from app.models.user import User` - so it knows what `"User"` in Block 15 is.

This file and `user.py` import each other, so these imports **must** be inside
the guard; otherwise you get the circular-import `ImportError` shown in
`user.py`, Block 7.

**Why it is here:** autocomplete and type checking for `category.owner` and
`category.expenses` without a circular import.

**If you removed or changed it:** runtime unaffected; editor support lost. If
moved outside the `if`, `ImportError: cannot import name 'User' from partially
initialized module 'app.models.user' (most likely due to a circular import)`.

#### Block 8: the class and its table name

```python
class Category(Base):
    __tablename__ = "categories"
```

- `class Category(Base):` - a new class, child of `Base`, so SQLAlchemy
  registers a table for it (`user.py`, Block 8).
- `__tablename__ = "categories"` - the table is called `categories` in the
  database. `expense.py` refers to it as `ForeignKey("categories.id")`, so the
  string must match.

**Why it is here:** declares the `categories` table.

**If you removed or changed it:** without `__tablename__`:
`InvalidRequestError: Class ... does not have a __table__ or __tablename__
specified`. If you renamed it, `expense.py` would fail at table creation with
`NoReferencedTableError: ... could not find table 'categories'`.

#### Block 9: `__table_args__` and the UniqueConstraint

```python
    __table_args__ = (
        # A user cannot have two categories with the same name,
        # but two different users can both have "Food".
        UniqueConstraint("owner_id", "name", name="uq_categories_owner_id_name"),
    )
```

- `__table_args__` - another special attribute SQLAlchemy looks for. It holds
  **table-level** things that are not a single column: multi-column
  constraints, indexes over several columns, check constraints, and table
  options.
- `=` - assignment.
- `(` ... `,` `)` - a Python **tuple** (an unchangeable list). SQLAlchemy
  requires a tuple here (or a dict, or `None`). Note the comma before the
  closing parenthesis: `(x,)` is a tuple with one item, but `(x)` is just `x`
  in parentheses. Verified: without the trailing comma SQLAlchemy raises
  `ArgumentError: __table_args__ value must be a tuple, dict, or None`.
- `# A user cannot have two categories with the same name, but two different
  users can both have "Food".` - comment stating the rule in words.
- `UniqueConstraint(` ... `)` - the constraint object (Block 4).
- `"owner_id", "name"` - the column names, as strings, that together must be
  unique. The rule is on the **pair**: `(1, "Food")` and `(2, "Food")` are
  different pairs and both allowed; `(1, "Food")` twice is not. Verified:
  inserting "Food" twice for one user raises
  `IntegrityError: UNIQUE constraint failed: categories.owner_id, categories.name`,
  and a second user can insert "Food" fine.
- `name="uq_categories_owner_id_name"` - the constraint's name in the database.
  It is given explicitly on purpose. The naming convention in
  `app/database/base.py` for unique constraints is
  `uq_%(table_name)s_%(column_0_name)s`, which only includes the **first**
  column. Verified: without a name, the convention would have produced
  `uq_categories_owner_id`, which hides the fact that `name` is part of the
  rule. The explicit name says exactly what is covered. (The `uq_` prefix is
  kept so it still looks like the others.)

The resulting DDL line: `CONSTRAINT uq_categories_owner_id_name UNIQUE (owner_id, name)`.

**Why it is here:** it is the one rule that cannot be written on a single
column: uniqueness of `name` *per user*. The router also checks
case-insensitively before inserting (`ensure_category_name_is_unique` in
`app/routers/categories.py`, which compares `func.lower(Category.name)`), but
the constraint is the guarantee that survives two requests racing each other.

Note the difference: the database rule is **case-sensitive** ("Food" and
"food" are different to PostgreSQL), while the router's check is
case-insensitive. So the router is stricter; the constraint is the safety net.

**If you removed or changed it:** two identical category names could be
created for one user if two requests arrived at the same moment (the router's
check would pass for both). If you wrote `unique=True` on `name` alone, no
two users could share "Food" - wrong. If you forgot the trailing comma you get
the `ArgumentError` above at import time.

#### Block 10: id

```python
    id: Mapped[int] = mapped_column(primary_key=True)
```

- `id: Mapped[int]` - an integer, NOT NULL.
- `mapped_column(primary_key=True)` - primary key, auto-numbered (`SERIAL` in
  PostgreSQL), constraint named `pk_categories` by the convention. Full
  explanation in `user.py`, Block 9.

**Why it is here:** every row needs an identifier; `expenses.category_id`
points at it.

**If you removed or changed it:** `ArgumentError: Mapper ... could not
assemble any primary key columns for mapped table 'categories'`.

#### Block 11: name

```python
    name: Mapped[str] = mapped_column(String(50))
```

- `name` - column name.
- `Mapped[str]` - text, NOT NULL. Verified: inserting a `Category` without a
  name raises `IntegrityError: NOT NULL constraint failed: categories.name`.
- `String(50)` - `VARCHAR(50)`. The schema (`app/schemas/category.py`) also
  limits `name` to 50 characters, after stripping spaces, so they agree.

**Why it is here:** the label itself ("Food").

**If you removed or changed it:** `CategoryResponse` expects `name`; the
`UniqueConstraint` in Block 9 refers to `"name"` and would fail at table
creation with an error that the column does not exist.

#### Block 12: description (an optional column)

```python
    description: Mapped[str | None] = mapped_column(String(255))
```

- `description` - column name.
- `Mapped[str | None]` - here is the `|` symbol. In a type annotation, `X | Y`
  means "either X or Y". `str | None` means "a string, or `None`". `None` is
  Python's "no value", which maps to SQL `NULL`. Because `None` is allowed,
  SQLAlchemy makes the column **nullable** (`user.py`, Block 9, point 2).
  Verified DDL: `description VARCHAR(255)` with no `NOT NULL`.
  (`str | None` is the modern spelling of `Optional[str]`; Python 3.10+
  understands it.)
- `String(255)` - `VARCHAR(255)`, matching the schema's `max_length=255`.

**Why it is here:** an optional note about the category. Not every category
needs one, so NULL must be allowed.

**If you removed or changed it:** with `Mapped[str]` (no `| None`) the column
would become NOT NULL, and creating a category without a description would
fail with `null value in column "description" violates not-null constraint`
(the schema sends `None` by default).

#### Block 13: owner_id (ForeignKey with ON DELETE CASCADE)

```python
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
```

- `owner_id` - column name: the id of the user who owns this category.
- `Mapped[int]` - integer, NOT NULL: every category must have an owner.
- `mapped_column(` ... `)` - note that **no column type is passed**. When a
  `ForeignKey` is present, SQLAlchemy copies the type from the referenced
  column (`users.id` is `Integer`), so it is not needed. Verified DDL:
  `owner_id INTEGER NOT NULL`.
- `ForeignKey(` ... `)` - the foreign key marker (Block 4).
- `"users.id"` - `tablename.columnname` as one string: the column this one
  points at. The table name must match `User.__tablename__`.
- `ondelete="CASCADE"` - what the **database** should do with this row when
  the referenced user row is deleted. `CASCADE` = "delete this row too".
  The alternative used in `expense.py` is `SET NULL` = "keep this row, set
  the column to NULL". A third option, the default when you give nothing, is
  to **refuse** the delete with an error while children exist. In DDL this
  becomes `ON DELETE CASCADE` at the end of the `FOREIGN KEY` line.
- `index=True` - an index on `owner_id`. Every categories query in the router
  has `WHERE categories.owner_id = ?` (list my categories, get one of mine),
  so this index is used on every request. Named `ix_categories_owner_id` by
  the convention.

Resulting DDL:
`CONSTRAINT fk_categories_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE`
and `CREATE INDEX ix_categories_owner_id ON categories (owner_id)`. The
constraint name comes from the convention
`fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`.

**Why it is here:** links each category to its owner; the database refuses a
category with a non-existent owner; deleting a user cleans up their categories
without extra code (and this is what makes `passive_deletes=True` on
`User.categories` safe).

**If you removed or changed it:** without `ForeignKey`, a category could point
at user 9999 who does not exist, and deleting a user would leave orphan
categories. Without `ondelete="CASCADE"`, deleting a user who has categories
would fail in PostgreSQL with
`update or delete on table "users" violates foreign key constraint
"fk_categories_owner_id_users" on table "categories"` (unless SQLAlchemy loaded
and deleted the children first, which `passive_deletes=True` tells it not
to). With `ondelete="SET NULL"` it would fail differently: `owner_id` is NOT
NULL, so the database could not set it to NULL. Without `index=True`, listing
categories would scan the whole table.

#### Block 14: created_at

```python
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- `created_at: Mapped[datetime]` - a timestamp, NOT NULL.
- `DateTime(timezone=True)` - `TIMESTAMP WITH TIME ZONE` (`user.py`, Block 14).
- `server_default=func.now()` - the database fills it with `now()` on insert.

**Why it is here:** records when the category was made; returned in
`CategoryResponse`.

**If you removed or changed it:** without the server default, every insert
would fail with a not-null violation on `created_at`.

#### Block 15: the `owner` relationship (many-to-one)

```python
    owner: Mapped["User"] = relationship(back_populates="categories")
```

- `owner` - attribute name: `category.owner` gives the `User` object.
- `Mapped["User"]` - **not** a list, so this is the "one" side: many
  categories, one user. SQLAlchemy calls it **many-to-one**. Verified:
  `Category.owner: direction=MANYTOONE, uselist=False`. `"User"` is a string
  because `User` is only imported under `TYPE_CHECKING` (Block 7).
- `relationship(back_populates="categories")` - the other side of this link is
  `User.categories`. No `cascade` is given, so the default
  `save-update, merge` applies (verified). That is correct here: deleting a
  category must never delete its owner.

How does SQLAlchemy know which column joins the two tables? It finds the
only foreign key between `categories` and `users`: `owner_id -> users.id`.
If there were two, you would have to tell it with `foreign_keys=`.

**Why it is here:** convenience in Python (`category.owner.email`) and the
required partner of `User.categories` (`back_populates` must be mutual).

**If you removed or changed it:** `User.categories` says
`back_populates="owner"`; with no `owner` here, mapper configuration fails:
`InvalidRequestError: Mapper 'Mapper[Category(categories)]' has no property
'owner'`. If you added `cascade="all, delete-orphan"` here by mistake,
deleting a category would delete the user.

#### Block 16: the `expenses` relationship

```python
    # Deleting a category keeps its expenses: the database sets their
    # category_id to NULL (see ON DELETE SET NULL in models/expense.py).
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="category", passive_deletes=True
    )
```

- `# Deleting a category keeps its expenses ...` - comment: the behaviour is
  decided by the `SET NULL` rule on `expenses.category_id` (`expense.py`,
  Block 22), not here.
- `expenses` - attribute name: `category.expenses` is a list of `Expense`.
- `Mapped[list["Expense"]]` - one-to-many (one category, many expenses).
  Verified: `direction=ONETOMANY, uselist=True`.
- `relationship(` ... `)`:
- `back_populates="category"` - the other side is `Expense.category`.
- `passive_deletes=True` - on `db.delete(category)`, do not load the expenses.
  The database applies `ON DELETE SET NULL` itself.
- **No `cascade` argument** - so the default `save-update, merge` applies, and
  in particular **no `delete`**: deleting a category must not delete
  expenses. Verified end to end: `db.delete(category)` sent only
  `DELETE FROM categories WHERE categories.id = ?`; afterwards the expense
  still existed with `category_id = None`.

Compare with `User.categories`: there the cascade is `all, delete-orphan`
because a user's categories die with the user. Here it is the default, because
an expense outlives its category.

**Why it is here:** `category.expenses` in Python, and the mutual partner of
`Expense.category`. `passive_deletes=True` keeps the delete endpoint
(`DELETE /categories/{id}`) to a single SQL statement.

**If you removed or changed it:** without `passive_deletes=True`, deleting a
category would first `SELECT` all its expenses and then run one
`UPDATE expenses SET category_id=NULL` per row in Python - correct but slow.
If you added `cascade="all, delete-orphan"`, `DELETE /categories/{id}` would
silently delete every expense in that category.

### Compared to your old code

There was no category table in the old project, so there is no direct
equivalent. The closest old code is the `Post` model, because it also had an
owner:

```python
# old: app/model.py
class Post(Base):
    __tablename__ = "post"

    id  : Mapped[int] = mapped_column(Integer, primary_key=True)
    title : Mapped[str] = mapped_column(String, nullable=False)
    ...
    owner_id : Mapped[int] = mapped_column(Integer , ForeignKey("user.id", ondelete="CASCADE") , nullable=False )
    owner = relationship("User")
```

What `Category` does differently, and why:

1. **`ForeignKey` without `Integer`.** Old: `mapped_column(Integer, ForeignKey(...))`.
   New: `mapped_column(ForeignKey(...))`. The type is copied from `users.id`
   automatically, so repeating it is unnecessary (and could disagree).

2. **`index=True` on the foreign key.** The old `owner_id` had no index.
   PostgreSQL does **not** create an index for a foreign key automatically, so
   `WHERE owner_id = ?` scanned the whole `post` table. The new code indexes
   every foreign key it filters on.

3. **Two-way relationship.** Old: `owner = relationship("User")` with no
   annotation and no `back_populates`, so `user.posts` did not exist and
   `post.owner` was not kept in sync in memory. New: `Mapped["User"]` plus
   `back_populates="categories"`, with `User.categories` on the other side.

4. **A multi-column rule.** `__table_args__` with `UniqueConstraint` did not
   appear in the old project. It is the right tool whenever a rule involves
   more than one column.

5. **Optional column spelled with the type.** `description: Mapped[str | None]`
   instead of `nullable=True`.

6. **Why a category table exists at all.** The old posts API had no concept of
   grouping. An expense tracker needs "spending by category" reports
   (`app/routers/reports.py`), and categories are per user so each person can
   name them as they like.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `__table_args__` | tuple of table-level constraints/indexes that are not a single column |
| tuple with one item | `(x,)` - the trailing comma matters; `(x)` is just `x` |
| `UniqueConstraint(a, b, name=...)` | the pair `(a, b)` must be unique across rows |
| `str \| None` | annotation meaning "a string or None"; makes the column nullable |
| `ForeignKey("users.id")` | values in this column must exist in `users.id` |
| `ondelete="CASCADE"` | database deletes this row when the referenced row is deleted |
| `ondelete="SET NULL"` | database sets this column to NULL when the referenced row is deleted |
| many-to-one | the side holding the foreign key; `Mapped["User"]`, not a list |
| one-to-many | the side with the list; `Mapped[list["Expense"]]` |
| default cascade | `save-update, merge` - add follows the parent, delete does not |
| naming convention | the `uq_`, `fk_`, `ix_`, `pk_`, `ck_` name patterns from `app/database/base.py` |

---

## File: app/models/expense.py

### What this file is for

This file defines two things. First, `PaymentMethod`: the fixed list of ways
an expense can be paid (`cash`, `card`, `upi`, `bank_transfer`, `other`).
Second, the `expenses` table as the class `Expense`: one row each time the
user spent money, with a title, an exact amount, the day it happened, how it
was paid, optional notes, the owner, and an optional category. This is the
biggest table and the one every report reads.

Who imports it: `app/routers/expenses.py` (`Expense` and `PaymentMethod`),
`app/routers/reports.py` (`Expense`), `app/schemas/expense.py`
(`PaymentMethod`, to validate the request body), and `app/models/__init__.py`.

What it imports: `enum` and `Decimal` from the standard library, `date` and
`datetime`, `TYPE_CHECKING`, several column types and constraint helpers from
`sqlalchemy`, the mapping tools, and `Base`.

### The whole file

```python
"""`expenses` table: one row for each time the user spent money."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class PaymentMethod(str, enum.Enum):
    """How the expense was paid. Stored in the database as plain text."""

    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        # Last line of defence: the API validates this too, but the database
        # must never hold a zero or negative expense.
        CheckConstraint("amount > 0", name="amount_positive"),
        # Almost every query is "this user's expenses in a date range".
        Index("ix_expenses_owner_id_expense_date", "owner_id", "expense_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    # Numeric (not Float) so money is stored exactly: up to 9,999,999,999.99
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # The day the money was spent - can differ from created_at.
    expense_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.CASH.value
    )
    notes: Mapped[str | None] = mapped_column(Text)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # NULL means "uncategorized".
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="expenses")
    category: Mapped["Category | None"] = relationship(back_populates="expenses")
```

### Walkthrough, block by block

#### Block 1: the module docstring

```python
"""`expenses` table: one row for each time the user spent money."""
```

- `"""..."""` - module docstring.
- `` `expenses` table `` - the table this file creates.
- `one row for each time the user spent money` - what a row means.

**Why it is here:** summary for the reader.

**If you removed or changed it:** no runtime change.

#### Block 2: import enum

```python
import enum
```

- `import` - load a module.
- `enum` - Python's standard library module for **enumerations**. An
  enumeration (short: enum) is a fixed set of named choices. Instead of
  letting `payment_method` be any text ("csh", "Cash ", "credit"), you list
  the allowed values once, and everything else is rejected. Used in Block 10
  as `enum.Enum`.

**Why it is here:** needed to define `PaymentMethod`.

**If you removed or changed it:** `NameError: name 'enum' is not defined` at
`class PaymentMethod(str, enum.Enum)`.

#### Block 3: import date and datetime

```python
from datetime import date, datetime
```

- `from datetime import` - from the standard library module `datetime`.
- `date` - a class holding only a calendar day: year, month, day. Example
  `2026-10-01`. No hours, no time zone. Used for `expense_date` (Block 18).
- `,` - import two names in one line.
- `datetime` - a class holding a day **and** a time (`user.py`, Block 2).
  Used for `created_at` and `updated_at` (Blocks 23-24).

**Why it is here:** the two Python types that SQLAlchemy reads from
`Mapped[date]` and `Mapped[datetime]` to pick `Date` and `DateTime`.

**If you removed or changed it:** `NameError` at the first annotation that
uses the missing name.

#### Block 4: import Decimal

```python
from decimal import Decimal
```

- `decimal` - a standard library module for **exact decimal arithmetic**.
- `Decimal` - the class. A `Decimal` stores numbers the way humans write them,
  in base ten, so `Decimal("0.10")` is exactly ten paise, not "approximately
  0.1". Compare with `float`, which stores numbers in base two and cannot
  represent most decimal fractions exactly. Verified in Python:

  ```
  0.1 + 0.2                    -> 0.30000000000000004
  Decimal("0.1") + Decimal("0.2") -> 0.3
  ```

  For money, that tiny error is unacceptable: totals in reports would drift
  by fractions of a paisa and then show up as `99.99999999` on screen.

**Why it is here:** `amount: Mapped[Decimal]` (Block 17). Also, when a row is
loaded, `expense.amount` comes back as a `Decimal` (verified:
`type(e.amount).__name__ == "Decimal"`), so all arithmetic in the reports is
exact.

**If you removed or changed it:** `NameError: name 'Decimal' is not defined`
at the `amount` line.

#### Block 5: import TYPE_CHECKING

```python
from typing import TYPE_CHECKING
```

- `TYPE_CHECKING` - `False` at runtime, `True` for type checkers (`user.py`,
  Block 3). Used in Block 9.

**Why it is here:** guards the imports of `Category` and `User`.

**If you removed or changed it:** `NameError` at line 23.

#### Block 6: import column types and constraint helpers

```python
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
```

- `from sqlalchemy import (` ... `)` - when an import list is long, Python
  lets you wrap it in parentheses and put one name per line. Each line ends
  with a comma; the last comma is allowed and makes future diffs cleaner.
- `CheckConstraint` - a class for a table-level rule written as an SQL
  condition, for example `amount > 0`. The database checks it on every INSERT
  and UPDATE and refuses rows that fail. Block 13.
- `Date` - column type for a calendar day. `DATE` in PostgreSQL. Block 18.
- `DateTime` - column type for day and time. Blocks 23-24.
- `ForeignKey` - marks a column as pointing at another table's column
  (`category.py`, Block 4). Blocks 21-22.
- `Index` - a class for creating an index over one or more columns,
  by name. Different from `index=True`, which is for a single column and gets
  an automatic name. Block 14.
- `Numeric` - column type for exact decimal numbers with a fixed number of
  digits. `NUMERIC(12, 2)` in PostgreSQL. Block 17.
- `String` - text with a maximum length. Blocks 16 and 19.
- `Text` - text with **no** maximum length. `TEXT` in PostgreSQL. Block 20.
- `func` - SQL function builder; `func.now()`. Blocks 23-24.

**Why it is here:** every SQLAlchemy name this file needs, imported once.

**If you removed or changed it:** `NameError` for the missing name at its
first use.

#### Block 7: import the mapping tools

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

- `Mapped`, `mapped_column`, `relationship` - the annotation type, the
  column builder and the link builder (`user.py`, Blocks 5, 9, 15).

**Why it is here:** used by every attribute of `Expense`.

**If you removed or changed it:** `NameError` at line 48.

#### Block 8: import Base

```python
from app.database.base import Base
```

- `Base` - the declarative base from `app/database/base.py`.

**Why it is here:** `class Expense(Base)` needs it to become a table.

**If you removed or changed it:** `NameError: name 'Base' is not defined`.

#### Block 9: imports only for the type checker

```python
if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User
```

- `if TYPE_CHECKING:` - never runs; only for the editor/mypy.
- `from app.models.category import Category` - what `"Category"` in Block 26
  refers to.
- `from app.models.user import User` - what `"User"` in Block 25 refers to.

Both `category.py` and `user.py` import `expense.py` names in *their*
`TYPE_CHECKING` blocks, so all three files are in a circle, broken by this
guard in each of them.

**Why it is here:** editor support for `expense.owner` and `expense.category`
without a circular import.

**If you removed or changed it:** runtime unaffected; editor support lost. If
moved outside the `if`: circular `ImportError`.

#### Block 10: the PaymentMethod enum class

```python
class PaymentMethod(str, enum.Enum):
    """How the expense was paid. Stored in the database as plain text."""
```

- `class PaymentMethod` - a new class named `PaymentMethod`.
- `(str, enum.Enum)` - **two** parent classes, separated by a comma. Python
  allows a class to inherit from several parents. Here:
  - `enum.Enum` - makes it an enumeration: the class attributes below become
    the fixed members, you can iterate over them, and `PaymentMethod("upi")`
    looks a member up by value.
  - `str` - makes every member **also a string**. This is the important trick.
    Verified:

    ```
    PaymentMethod.CASH == "cash"            -> True
    isinstance(PaymentMethod.CASH, str)     -> True
    PaymentMethod("upi")                    -> PaymentMethod.UPI
    PaymentMethod("cheque")                 -> ValueError: 'cheque' is not a valid PaymentMethod
    PaymentMethod.CASH.value                -> 'cash'
    PaymentMethod.CASH.name                 -> 'CASH'
    str(PaymentMethod.CASH)                 -> 'PaymentMethod.CASH'   (careful!)
    [m.value for m in PaymentMethod]        -> ['cash', 'card', 'upi', 'bank_transfer', 'other']
    ```

    Because members are strings, they compare equal to the plain text in the
    database, Pydantic can validate JSON `"cash"` into `PaymentMethod.CASH`,
    and FastAPI can show the five choices in the docs. Note the one trap:
    `str(member)` gives `'PaymentMethod.CASH'`, not `'cash'`. That is why the
    code always uses `.value` when it needs the plain text (Block 19).
- `:` - starts the class body.
- `"""How the expense was paid. Stored in the database as plain text."""` -
  the class docstring. It tells you the design decision: the database column
  is ordinary text, not a special database enum type (see Block 19 for why).

**Why it is here:** one single place that lists the allowed payment methods.
Schemas, routers and the model all import it, so the list can never drift
between them.

**If you removed or changed it:** `app/schemas/expense.py` imports it for the
`payment_method` field, and `app/routers/expenses.py` uses it as the type of
the `payment_method` query filter; both would fail with `ImportError`. If
you dropped `str` from the parents, `PaymentMethod.CASH == "cash"` would be
`False`, and comparing a filter value against the text column would never
match.

#### Block 11: the five members

```python
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"
```

- `CASH`, `CARD`, `UPI`, `BANK_TRANSFER`, `OTHER` - the member **names**.
  Convention: UPPER_CASE, like constants. You use them in code as
  `PaymentMethod.CARD`.
- `=` - inside an `Enum` class body, assignment creates a member rather than a
  plain attribute.
- `"cash"`, `"card"`, `"upi"`, `"bank_transfer"`, `"other"` - the member
  **values**: the exact text stored in the `payment_method` column and the
  exact text clients send in JSON. Lowercase with underscores. The longest,
  `"bank_transfer"`, is 13 characters, which fits in the `String(20)` column
  (Block 19).

**Why it is here:** these are the choices the product supports. `OTHER` is a
catch-all so a user is never blocked from entering an expense.

**If you removed or changed it:** removing a member (say `UPI`) would make
every request with `"upi"` fail validation (HTTP 422 from the schema), while
old rows with `upi` would still sit in the database. Changing a value
(`"card"` to `"credit_card"`) has the same effect on existing rows: they
would no longer match the enum. Adding a member is safe, as long as the value
is at most 20 characters.

#### Block 12: the class and its table name

```python
class Expense(Base):
    __tablename__ = "expenses"
```

- `class Expense(Base):` - a model class, so a table is registered.
- `__tablename__ = "expenses"` - the database table name.

**Why it is here:** declares the `expenses` table.

**If you removed or changed it:** `InvalidRequestError` about a missing
`__tablename__`; the `Index` in Block 14 is also named after the table, so a
rename would make the index name misleading.

#### Block 13: `__table_args__` - the CheckConstraint

```python
    __table_args__ = (
        # Last line of defence: the API validates this too, but the database
        # must never hold a zero or negative expense.
        CheckConstraint("amount > 0", name="amount_positive"),
```

- `__table_args__ = (` - start of the tuple of table-level items
  (`category.py`, Block 9). This tuple has two items (this block and the next).
- `# Last line of defence: ...` - comment: the schema already rejects
  `amount <= 0` (`MoneyAmount = Annotated[Decimal, Field(gt=0, ...)]` in
  `app/schemas/expense.py`), so this constraint only fires if something
  bypasses the API - a hand-written SQL, a bug, a future endpoint.
- `CheckConstraint(` ... `)` - the class from Block 6.
- `"amount > 0"` - the condition, as SQL text. The database evaluates it for
  every row on INSERT and UPDATE. Verified: inserting an expense with
  `amount = 0` raises `IntegrityError: CHECK constraint failed:
  ck_expenses_amount_positive` (SQLite wording; PostgreSQL says
  `new row for relation "expenses" violates check constraint
  "ck_expenses_amount_positive"`).
- `name="amount_positive"` - the short name. The naming convention for check
  constraints in `app/database/base.py` is `ck_%(table_name)s_%(constraint_name)s`,
  so the final name is `ck_expenses_amount_positive` (see the DDL at the top
  and the migration file). Here the name is **required**: verified that a
  `CheckConstraint` without `name=` under this convention raises
  `InvalidRequestError: Naming convention including %(constraint_name)s token
  requires that constraint is explicitly named.`
- `,` - separates this item from the next inside the tuple.

**Why it is here:** money that is zero or negative is never a valid expense;
the database guarantees it no matter where the row comes from.

**If you removed or changed it:** normal API use would behave the same
(the schema stops bad values first). But a direct SQL insert or a future
bug could store `-500`, and the reports' totals would be wrong. Without
`name=`, the app fails at import with the `InvalidRequestError` above.

#### Block 14: `__table_args__` - the composite Index

```python
        # Almost every query is "this user's expenses in a date range".
        Index("ix_expenses_owner_id_expense_date", "owner_id", "expense_date"),
    )
```

- `# Almost every query is ...` - comment: the reason for this index.
  `GET /expenses` filters on `owner_id` and (optionally) a date range and
  sorts by `expense_date`; the three `/reports/*` endpoints filter on
  `owner_id` and a date range and group by month or category.
- `Index(` ... `)` - the class from Block 6.
- `"ix_expenses_owner_id_expense_date"` - the index name, given explicitly.
  The convention `ix_%(column_0_label)s` only uses the **first** column;
  verified that an unnamed index over these two columns would be called
  `ix_expenses_owner_id`, hiding `expense_date`. The explicit name is honest.
- `"owner_id", "expense_date"` - the two columns, **in this order**. A
  multi-column (composite) index is sorted first by `owner_id`, then by
  `expense_date` inside each owner. The database can use it for
  `WHERE owner_id = ?` alone, and for `WHERE owner_id = ? AND expense_date
  BETWEEN ? AND ?`, and for `ORDER BY expense_date` within one owner. It
  cannot help a query that filters on `expense_date` alone - which this app
  never does.
- `)` - closes the `__table_args__` tuple.

Because this index starts with `owner_id`, there is no separate
`index=True` on the `owner_id` column (Block 21): it would be redundant.

**Why it is here:** performance of the most common queries. With thousands of
users and millions of expenses, finding one user's expenses for one month
becomes a small index range scan instead of a full-table scan.

**If you removed or changed it:** every list and report query would scan
the whole `expenses` table. Correct answers, but slower and slower as the
table grows. If you swapped the column order to `("expense_date",
"owner_id")`, the index would no longer serve `WHERE owner_id = ?` on its own.

#### Block 15: id

```python
    id: Mapped[int] = mapped_column(primary_key=True)
```

- `id: Mapped[int] = mapped_column(primary_key=True)` - the auto-numbered
  primary key (`user.py`, Block 9). Named `pk_expenses`.

**Why it is here:** row identity; `GET /expenses/{expense_id}` looks it up.

**If you removed or changed it:** `ArgumentError: ... could not assemble any
primary key columns`.

#### Block 16: title

```python
    title: Mapped[str] = mapped_column(String(150))
```

- `title` - column name: a short label like "Tea" or "October rent".
- `Mapped[str]` - text, NOT NULL.
- `String(150)` - `VARCHAR(150)`; the schema also limits titles to 150.

**Why it is here:** what the money was spent on; also searched by the
`search` query parameter of `GET /expenses`.

**If you removed or changed it:** `ExpenseResponse` needs `title`; the update
schema's list of columns that must not be null includes `"title"`.

#### Block 17: amount (Numeric, not Float)

```python
    # Numeric (not Float) so money is stored exactly: up to 9,999,999,999.99
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
```

- `# Numeric (not Float) ...` - comment with the reason and the maximum.
- `amount` - column name.
- `Mapped[Decimal]` - Python type `Decimal` (Block 4), NOT NULL.
- `Numeric(12, 2)` - the column type. The two numbers are **precision** and
  **scale**: 12 digits in total, of which 2 are after the decimal point. So
  10 digits before the point: the largest value is `9,999,999,999.99`.
  PostgreSQL stores `NUMERIC(12, 2)` exactly, with no rounding error. If a
  value has more than 2 decimals, PostgreSQL rounds it to 2; if it has more
  than 10 digits before the point, PostgreSQL refuses it
  (`numeric field overflow`). The schema's `max_digits=12, decimal_places=2`
  mirrors this so the API rejects such values with 422 before the database
  sees them.

Why not `Float`? `Float` becomes a binary floating-point column
(`DOUBLE PRECISION` / `FLOAT`), with the `0.1 + 0.2 = 0.30000000000000004`
problem shown in Block 4. Summing thousands of float amounts gives totals
that are off by tiny fractions, and `WHERE amount = 19.99` can fail to match
`19.99` stored as `19.989999999...`. `Numeric` has none of these problems.

**Why it is here:** the money itself, stored exactly.

**If you removed or changed it:** with `Float`, report totals would be
slightly wrong and comparisons unreliable. With `Mapped[float]` and no type,
you would get `Float` by the type map - the same problem. With
`Numeric(8, 2)` the maximum would drop to 999,999.99 and a large rent would
fail with `numeric field overflow`.

#### Block 18: expense_date (Date, not DateTime)

```python
    # The day the money was spent - can differ from created_at.
    expense_date: Mapped[date] = mapped_column(Date)
```

- `# The day the money was spent - can differ from created_at.` - comment:
  a user may enter on Monday an expense from last Friday. `expense_date` is
  Friday; `created_at` (Block 23) is Monday.
- `expense_date` - column name.
- `Mapped[date]` - Python `date` (Block 3): only a day, NOT NULL.
- `Date` - the column type. `DATE` in PostgreSQL: a calendar day with no time
  and no time zone.

`Date` vs `DateTime(timezone=True)`: a purchase "on 1 October" is a calendar
fact; it does not have an hour, and it must not shift to 30 September when a
client in another time zone reads it. `DateTime` would force a fake time of
day and a time zone onto it. So the day the money was spent is a `Date`,
while `created_at`/`updated_at`, which are real instants recorded by the
server, are `DateTime(timezone=True)`.

**Why it is here:** the day the expense belongs to; the basis for date-range
filters, monthly reports (`extract("month", Expense.expense_date)` in
`reports.py`) and the sort order of the list.

**If you removed or changed it:** the list and all reports filter on it;
the composite index names it. With `DateTime` instead, monthly grouping would
depend on the time zone and could put a late-night purchase in the wrong
month.

#### Block 19: payment_method (a String column with a Python default)

```python
    payment_method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.CASH.value
    )
```

- `payment_method` - column name.
- `Mapped[str]` - a plain `str`, NOT NULL. Not `Mapped[PaymentMethod]`: the
  column holds ordinary text.
- `String(20)` - `VARCHAR(20)`. The longest allowed value is 13 characters,
  so 20 leaves room for a future value.
- `default=PaymentMethod.CASH.value` - Python-side default (`user.py`,
  Block 13). `PaymentMethod.CASH` is the member; `.value` is its text,
  `"cash"`. Verified: creating an `Expense` without `payment_method` sends
  `'cash'` in the INSERT. `.value` is used rather than the member itself
  because `str(PaymentMethod.CASH)` is `'PaymentMethod.CASH'` (Block 10);
  the plain string is what must reach the database.

**Why `String(20)` and not a database enum type?** PostgreSQL has
`CREATE TYPE payment_method AS ENUM (...)`, and SQLAlchemy has `Enum(...)`
to use it. The project avoids it on purpose:

- Adding a value to a PostgreSQL enum needs a migration with
  `ALTER TYPE ... ADD VALUE`, which Alembic's autogenerate does not write for
  you; removing or renaming a value is harder still. With `String(20)`,
  adding `"wallet"` is a one-line change in Block 11 and no migration.
- The Python `PaymentMethod` enum plus the Pydantic schema already reject
  unknown values at the API door, so the database type adds little safety.
- Plain text is portable: the same model works on SQLite (where the tests
  run) without special handling.

The trade-off, stated honestly: the database itself would accept
`'cheque'` if someone inserted it by hand. The API never will.

**Why it is here:** records how the expense was paid; filterable in
`GET /expenses?payment_method=upi`; defaults to cash so a quick entry needs
fewer fields.

**If you removed or changed it:** without `default=`, the schema still
defaults to `PaymentMethod.CASH`, so normal requests are unaffected; a row
created in code without the field would fail with a not-null violation.
With `String(10)`, inserting `"bank_transfer"` (13 characters) would fail in
PostgreSQL with `value too long for type character varying(10)`.

#### Block 20: notes

```python
    notes: Mapped[str | None] = mapped_column(Text)
```

- `notes` - column name.
- `Mapped[str | None]` - text or `None`, so the column is nullable
  (`category.py`, Block 12).
- `Text` - the column type: `TEXT`, no length limit at the database level.
  The schema caps it at 1000 characters at the API level.

**Why it is here:** free-form details ("split with Rahul, he owes half").
Optional, so NULL is allowed.

**If you removed or changed it:** with `Mapped[str]`, creating an expense
without notes (the normal case) would fail with a not-null violation. With
`String(255)`, long notes would be rejected by the database.

#### Block 21: owner_id

```python
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
```

- `owner_id` - column name: who spent the money.
- `Mapped[int]` - integer, NOT NULL: every expense has an owner.
- `ForeignKey("users.id", ondelete="CASCADE")` - points at `users.id`; when
  the user is deleted, the database deletes the expense too (`category.py`,
  Block 13). Type copied from `users.id` (`INTEGER`). Constraint named
  `fk_expenses_owner_id_users`.
- No `index=True` here - the composite index of Block 14 begins with
  `owner_id` and serves the same purpose.

**Why it is here:** ownership. Every expense endpoint filters on
`Expense.owner_id == current_user.id`, so one user can never see another's
rows. `CASCADE` matches `passive_deletes=True` on `User.expenses`.

**If you removed or changed it:** without the foreign key, expenses could
point at missing users; without `CASCADE`, deleting a user with expenses
would fail with a foreign key violation. Adding `index=True` would create a
second, redundant index on `owner_id`.

#### Block 22: category_id (ForeignKey with ON DELETE SET NULL)

```python
    # NULL means "uncategorized".
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
```

- `# NULL means "uncategorized".` - comment: the meaning of an empty value.
- `category_id` - column name.
- `Mapped[int | None]` - integer **or None**, so the column is nullable
  (verified DDL: `category_id INTEGER` without `NOT NULL`). An expense does
  not have to be in a category.
- `ForeignKey("categories.id", ondelete="SET NULL")` - points at
  `categories.id`. `SET NULL`: when the category is deleted, the database
  keeps the expense and writes `NULL` into this column. Verified:
  `db.delete(category)` ran only `DELETE FROM categories WHERE ...`, and the
  expense was still there with `category_id = None`.
  `SET NULL` is only possible because the column is nullable; on a NOT NULL
  column the database could not do it.
- `index=True` - index `ix_expenses_category_id`, because the list endpoint
  filters by `category_id` and the by-category report joins on it.

**Why it is here:** optional grouping. Deleting a category should not erase
spending history, so `SET NULL`, not `CASCADE`. The router also checks that
the category belongs to the current user before accepting a `category_id`
(`get_owned_category_or_404` in `app/routers/expenses.py`), because the
foreign key alone cannot know who owns what.

**If you removed or changed it:** with `Mapped[int]` (no `| None`) the
column would be NOT NULL, uncategorized expenses would be impossible, and
`ondelete="SET NULL"` would fail at delete time. With `ondelete="CASCADE"`,
deleting a category would delete all its expenses. Without `ondelete` at
all, `DELETE /categories/{id}` would fail with a foreign key violation while
any expense uses that category.

#### Block 23: created_at

```python
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- `created_at: Mapped[datetime]` - timestamp, NOT NULL.
- `DateTime(timezone=True), server_default=func.now()` - stored as
  `TIMESTAMP WITH TIME ZONE`, filled by the database with `now()` on insert
  (`user.py`, Block 14).

**Why it is here:** when the row was entered (distinct from `expense_date`,
Block 18).

**If you removed or changed it:** insert fails with a not-null violation
without the server default.

#### Block 24: updated_at (onupdate)

```python
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- `updated_at` - column name: when the row was last changed.
- `Mapped[datetime]` - timestamp, NOT NULL.
- `DateTime(timezone=True)` - `TIMESTAMP WITH TIME ZONE`.
- `server_default=func.now()` - on insert, the database sets it to `now()`,
  so a new row has `updated_at == created_at`.
- `onupdate=func.now()` - the third kind of default (`user.py`, Block 13
  table). Whenever SQLAlchemy issues an `UPDATE` for this row and
  `updated_at` was not set by hand, it adds `updated_at = now()` to the
  statement. Verified, compiled for PostgreSQL after changing only the title:

  ```sql
  UPDATE expenses SET title=%(title)s, updated_at=now() WHERE expenses.id = %(id_1)s
  ```

  The `now()` is evaluated by the database. Note this is a SQLAlchemy
  feature, not a database trigger: an `UPDATE` written by hand in `psql`
  would **not** touch `updated_at`.

**Why it is here:** `ExpenseResponse` includes `updated_at`, so clients can
see when an expense was last edited (`PATCH /expenses/{id}`).

**If you removed or changed it:** without `onupdate`, `updated_at` would stay
at its creation value forever, and the response would be misleading.
Without `server_default`, the insert would fail on the NOT NULL rule.

#### Block 25: the `owner` relationship

```python
    owner: Mapped["User"] = relationship(back_populates="expenses")
```

- `owner: Mapped["User"]` - many-to-one: many expenses, one user. Verified:
  `Expense.owner: direction=MANYTOONE, uselist=False`.
- `relationship(back_populates="expenses")` - the partner of `User.expenses`.
  Default cascade (`save-update, merge`), so deleting an expense never
  touches the user.

**Why it is here:** `expense.owner` in Python and the required mutual side of
`User.expenses`.

**If you removed or changed it:** `InvalidRequestError: Mapper
'Mapper[Expense(expenses)]' has no property 'owner'` at mapper configuration,
because `User.expenses` names it.

#### Block 26: the `category` relationship (optional many-to-one)

```python
    category: Mapped["Category | None"] = relationship(back_populates="expenses")
```

- `category` - attribute name: `expense.category` is a `Category` object or
  `None`.
- `Mapped["Category | None"]` - the **whole** annotation is a string, so
  Python does not try to evaluate `Category` (not imported at runtime).
  SQLAlchemy parses the string: `Category` is the target class, `| None`
  says the link may be empty - which matches the nullable `category_id`.
  Verified: `Expense.category: direction=MANYTOONE, uselist=False`.
- `relationship(back_populates="expenses")` - the partner of
  `Category.expenses` (`category.py`, Block 16). Default cascade.

**Why it is here:** `expense.category.name` in Python (for example when
building a response), and the mutual side of `Category.expenses`.

**If you removed or changed it:** `Category.expenses` names
`back_populates="category"`, so mapper configuration would fail with
`Mapper 'Mapper[Expense(expenses)]' has no property 'category'`. Writing
`Mapped["Category"]` without `| None` would still work at runtime, but the
type checker would wrongly believe `expense.category` can never be `None`.

### Compared to your old code

The old `Post` model is the nearest relative of `Expense` (both are "things a
user owns"):

```python
# old: app/model.py
class Post(Base):
    __tablename__ = "post"

    id  : Mapped[int] = mapped_column(Integer, primary_key=True)
    title : Mapped[str] = mapped_column(String, nullable=False)
    content : Mapped[str] = mapped_column(String, nullable=False)
    published : Mapped[bool] = mapped_column(Boolean, server_default='True',nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    owner_id : Mapped[int] = mapped_column(Integer , ForeignKey("user.id", ondelete="CASCADE") , nullable=False )
    owner = relationship("User")
```

Compiled for PostgreSQL, the old class gives:

```sql
CREATE TABLE post (
    id SERIAL NOT NULL,
    title VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    published BOOLEAN DEFAULT 'True' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    owner_id INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(owner_id) REFERENCES "user" (id) ON DELETE CASCADE
)
```

What is different, and why:

1. **`server_default='True'` (a string) vs `server_default=true()`.** The old
   code produces `DEFAULT 'True'` - a text literal that PostgreSQL then
   converts to boolean. It works, because PostgreSQL accepts `'true'`,
   `'t'`, `'yes'`, `'1'` for booleans, but it is a text value in a boolean
   column. The new `true()` renders the real boolean `true`, and also works on
   SQLite (`1`). Small thing, but it shows the idea: use SQLAlchemy's
   expression objects instead of strings wherever one exists.

2. **No `updated_at`, no `onupdate`.** The old table could not tell when a
   post was edited. `Expense` adds `updated_at` with `onupdate=func.now()`.

3. **No constraints beyond NOT NULL.** The old table had no
   `CheckConstraint` and no multi-column `Index`. `Expense` has
   `amount > 0` as a database rule and a composite index for the hot query.

4. **Exact money.** The old project had no money column. If you had added one
   as `Float`, the rounding problems in Block 4 would have appeared in totals.
   `Expense.amount` is `Numeric(12, 2)` + `Decimal`.

5. **Day vs instant.** Old `created_at` was the only date. `Expense`
   separates the business day (`expense_date: Date`) from the technical
   timestamps (`created_at`, `updated_at: DateTime(timezone=True)`).

6. **A fixed list of choices.** The old project had nothing like
   `PaymentMethod`. Free text would have led to "Cash", "cash", "csh" all
   meaning the same thing and breaking filters.

7. **Optional foreign key with `SET NULL`.** Old `owner_id` used `CASCADE`,
   which is right for ownership and is kept for `Expense.owner_id`. The new
   `category_id` shows the other rule, `SET NULL`, for a link that must not
   drag the row down with it.

8. **Indexes on foreign keys.** Old `owner_id` had none; `Expense` indexes
   `category_id` directly and `owner_id` through the composite index.

9. **Relationships in both directions with explicit typing.** Old
   `owner = relationship("User")` has no `Mapped[...]`, no `back_populates`.
   New: `owner: Mapped["User"] = relationship(back_populates="expenses")`.

10. **`content: String` vs `notes: Text`.** Old free text was `VARCHAR` with no
    length; new free text is `TEXT`, which says clearly "no limit", and is
    optional (`str | None`).

11. **The commented-out `Vote` model.** Your old file ended with a
    commented-out `Vote` table (a two-column primary key). The new project
    has no equivalent; it is simply not a feature here. If it ever were, the
    pattern would be the same as the old one: two `mapped_column(ForeignKey(...),
    primary_key=True)` columns.

### Key terms in this file

| Term | One-line meaning |
| --- | --- |
| `enum.Enum` | a class whose attributes are a fixed set of named choices |
| `class X(str, enum.Enum)` | an enum whose members are also strings, so `X.CASH == "cash"` |
| `.value` / `.name` | the stored text (`"cash"`) / the member name (`"CASH"`) |
| `Decimal` | exact base-ten number; use for money, never `float` |
| `Numeric(12, 2)` | exact column: 12 digits total, 2 after the point; max 9,999,999,999.99 |
| `Date` | calendar day only (`DATE`); no time, no time zone |
| `DateTime(timezone=True)` | an instant with offset (`TIMESTAMP WITH TIME ZONE`) |
| `Text` | unlimited-length text column (`TEXT`) |
| `CheckConstraint("amount > 0", name=...)` | database rule checked on every insert/update; name required by the `ck_` convention |
| `Index(name, col1, col2)` | a named multi-column index; column order matters |
| composite index | one index over several columns; usable for the first column alone or the first N |
| `ondelete="SET NULL"` | keep the child row, blank the foreign key, when the parent is deleted |
| `onupdate=func.now()` | SQLAlchemy adds `updated_at = now()` to every UPDATE it issues |
| `Mapped["Category \| None"]` | string annotation for an optional many-to-one link |
| database enum type | PostgreSQL `CREATE TYPE ... AS ENUM`; avoided here in favour of `String(20)` |

---

## Summary of this folder

The three model files describe three tables, and `__init__.py` makes sure all
three are loaded whenever anyone writes `import app.models`, which is what
Alembic needs to see the full picture. Every file follows the same shape:
imports, a `TYPE_CHECKING` block that gives the editor the related classes
without creating a circular import, a class that inherits from `Base`, a
`__tablename__`, optional `__table_args__` for rules that span several
columns, then one `name: Mapped[type] = mapped_column(...)` line per column,
and finally the `relationship(...)` lines that link the classes. The Python
type inside `Mapped[...]` decides both the column type (`int` to `Integer`,
`Decimal` to `Numeric`, `date` to `Date`) and whether NULL is allowed
(`| None`), so the Python side and the database side can never disagree. The
tables are tied together by two foreign keys with different delete rules:
`owner_id` uses `ON DELETE CASCADE`, because a user's categories and expenses
belong to that user and go with them, while `expenses.category_id` uses
`ON DELETE SET NULL`, because deleting a label must not delete spending
history. The `relationship()` options mirror those rules: `User.categories`
and `User.expenses` carry `cascade="all, delete-orphan"` and
`passive_deletes=True`, so SQLAlchemy lets the database do the cascading in
one statement, while `Category.expenses` has the default cascade so expenses
survive their category. Defaults are placed where they belong: `server_default`
for values the database should always fill (`now()`, `true`), `default` for
values Python should know before saving (`is_active=True`, `payment_method="cash"`),
and `onupdate` for `updated_at`. Every index and constraint has a predictable
name from the naming convention in `app/database/base.py`, with explicit names
where the convention would have been misleading, so later migrations can refer
to them safely. Together, these files are the single source of truth for the
schema: the migration in `alembic/versions/` was generated from them, and the
schemas and routers in the next documents only read and write what is defined
here.
