# app/database/ (base.py and session.py)

This folder is the bridge between Python and PostgreSQL. It has three files:

| File                       | Job                                                                 |
| -------------------------- | ------------------------------------------------------------------- |
| `app/database/__init__.py` | Marks the folder as a Python package and describes the other two.  |
| `app/database/base.py`     | The `Base` class that every table model inherits from.              |
| `app/database/session.py`  | The connection pool (`engine`), the session factory (`SessionLocal`), the `get_db` dependency, and the startup/health check. |

In your old project all of this lived in one file, `app/database.py`. The new project splits it in two because the two halves are used by different people: `base.py` is needed by the **models** and by **Alembic** (table definitions), while `session.py` is needed by the **routers** and by **main.py** (talking to the live database). Keeping them apart avoids a circular import: `models` -> `base.py` is a clean one-way street, and nothing in `base.py` needs `settings` or an engine.

Versions used while writing this (every claim below was checked against them): SQLAlchemy 2.0.54, FastAPI 0.141.1, Alembic 1.20.0, Python 3.14.

---

## File: app/database/__init__.py

### What this file is for

A folder becomes a Python *package* (something you can `import`) when it contains a file named `__init__.py`. This one holds only a docstring that lists the two real files, so that anyone who opens the folder knows where to look. Nothing imports anything *from* this file; it is only a signpost.

Who imports it: Python itself runs it (once) the first time anything does `from app.database.base import ...` or `from app.database.session import ...`. What it imports: nothing.

### The whole file

```python
"""
database/ - Everything needed to talk to PostgreSQL through SQLAlchemy.

    base.py     -> declarative Base class that every model inherits from
    session.py  -> engine, session factory and the `get_db` dependency
"""
```

### Walkthrough, block by block

### Block 1: the package docstring

```python
"""
database/ - Everything needed to talk to PostgreSQL through SQLAlchemy.

    base.py     -> declarative Base class that every model inherits from
    session.py  -> engine, session factory and the `get_db` dependency
"""
```

- `"""` ... `"""` - three double quotes start and end a *docstring*. A docstring is a string that sits at the very top of a file, class or function. Python stores it in the special variable `__doc__` and tools (editors, `help()`) show it. It does not run anything.
- `database/` - the name of this folder. The slash is just a hint that it is a folder, not a file.
- `Everything needed to talk to PostgreSQL through SQLAlchemy.` - the one-line summary. *SQLAlchemy* is the library that turns Python classes and method calls into SQL text and sends it to PostgreSQL.
- `base.py -> declarative Base class that every model inherits from` - tells you what is inside `base.py`. "Declarative" is SQLAlchemy's word for *you describe a table by writing a Python class*; "Base" is the class those classes inherit from. Both are explained fully below.
- `session.py -> engine, session factory and the get_db dependency` - tells you what is inside `session.py`. *Engine* = the connection pool. *Session factory* = the thing that hands out sessions. *`get_db` dependency* = the function FastAPI calls to give each request its own session.

**Why it is here:** without an `__init__.py`, `app.database` is not a package, so `from app.database.base import Base` in the models would still work in modern Python (as a "namespace package"), but tools such as linters, type checkers and some packaging tools treat the folder differently. The docstring is a free table of contents.

**If you removed or changed it:** deleting the file alone would normally still let the imports work (Python 3.3+ allows packages without `__init__.py`), but the folder would lose its docstring and the project would become inconsistent with every other `app/...` folder, which all have one. Deleting the whole folder breaks every model (`from app.database.base import Base`) and every router (`from app.database.session import get_db`) with `ModuleNotFoundError: No module named 'app.database'`.

### Compared to your old code

Your old project had no `database/` folder. It had one file, `app/database.py`, so there was nothing to put a package docstring on. The new project turns it into a folder with two files (explained next), and this `__init__.py` is simply the required marker file for that folder.

### Key terms in this file

| Term           | One-line meaning                                                                 |
| -------------- | -------------------------------------------------------------------------------- |
| package        | A folder Python can import; marked by an `__init__.py` file.                     |
| docstring      | A string at the top of a file/class/function that documents it; stored in `__doc__`. |
| SQLAlchemy     | The library that converts Python objects and calls into SQL for PostgreSQL.      |
| declarative    | SQLAlchemy's style where a Python class *declares* a table.                      |

---

## File: app/database/base.py

### What this file is for

This file creates `Base`, the parent class of every table model (`User`, `Category`, `Expense`). When a class inherits from `Base`, SQLAlchemy reads its attributes and builds a `Table` object from them, and stores that `Table` in `Base.metadata`. `Base.metadata` is therefore the list of *every* table the application expects to exist. Alembic reads that list to generate migrations.

The file also fixes one thing your old project left to chance: the **names** of indexes, primary keys, foreign keys, unique constraints and check constraints. It gives SQLAlchemy a *naming convention* so those names are predictable (`pk_users`, `fk_expenses_owner_id_users`, ...) instead of invented by PostgreSQL.

Who imports it: `app/models/user.py`, `app/models/category.py`, `app/models/expense.py` (each does `from app.database.base import Base`), `alembic/env.py` (`target_metadata = Base.metadata`) and `tests/conftest.py`. What it imports: only two things from SQLAlchemy, nothing from the rest of the project. That is on purpose - it keeps this file import-safe from anywhere.

### The whole file

```python
"""
Declarative Base that every ORM model inherits from.

`Base.metadata` is the registry of all tables; Alembic compares it with the
real database to autogenerate migrations.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Predictable names for indexes and constraints. Without this the database
# invents names, which makes later migrations (dropping / altering a
# constraint) painful.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""
Declarative Base that every ORM model inherits from.

`Base.metadata` is the registry of all tables; Alembic compares it with the
real database to autogenerate migrations.
"""
```

- `"""` ... `"""` - a docstring (see the previous file). It explains the file; it does nothing when run.
- `Declarative Base` - the class defined at the bottom of this file. "Declarative" = you declare tables as classes.
- `ORM model` - ORM is *Object Relational Mapper*: the part of SQLAlchemy that maps a Python object (`User(...)`) to a row in a table (`users`). A *model* is one such class.
- `inherits from` - Python inheritance: `class User(Base)` means `User` *is a kind of* `Base` and gets all of its behaviour.
- `` `Base.metadata` `` - the attribute defined on line 24. Backticks are just Markdown-style quoting inside the comment; they have no meaning to Python.
- `registry of all tables` - a registry is a list that things sign up to. Every class that inherits from `Base` adds its `Table` to `Base.metadata.tables`.
- `Alembic compares it with the real database` - Alembic is the migration tool. `alembic revision --autogenerate` connects to PostgreSQL, looks at the real tables, compares them with `Base.metadata`, and writes the difference as a migration file.
- `autogenerate migrations` - the `--autogenerate` flag described above.

**Why it is here:** so a reader knows the file's one job and the one attribute that matters (`Base.metadata`) without reading the code.

**If you removed or changed it:** nothing changes at runtime. `app.database.base.__doc__` becomes `None`, and the next reader has to work out the file's purpose alone.

### Block 2: importing `MetaData`

```python
from sqlalchemy import MetaData
```

- `from` ... `import` - the Python statement that pulls one name out of a module. `from sqlalchemy import MetaData` means: load the top-level `sqlalchemy` package and copy its name `MetaData` into this file.
- `sqlalchemy` - the SQLAlchemy library (installed from `requirements.txt`, version 2.0.54).
- `MetaData` - a class. One `MetaData` object is a *container of `Table` objects*. Think of it as a dictionary `{"users": <Table users>, "categories": <Table categories>, ...}` plus some settings that apply to all of those tables. One of those settings is `naming_convention`, which is the reason this file creates its own `MetaData` instead of accepting the default one.

**Why it is here:** line 24 calls `MetaData(naming_convention=...)`. Without the import, that name does not exist.

**If you removed or changed it:** line 24 fails at import time with `NameError: name 'MetaData' is not defined`. Because every model imports this file, the whole application (and Alembic, and the tests) would refuse to start.

### Block 3: importing `DeclarativeBase`

```python
from sqlalchemy.orm import DeclarativeBase
```

- `from sqlalchemy.orm import` - take a name from the `sqlalchemy.orm` sub-package. `orm` holds everything about mapping classes to tables (`Session`, `relationship`, `Mapped`, and this).
- `DeclarativeBase` - a class that SQLAlchemy 2.0 added. You do not use it directly; you *subclass* it to create your own `Base`. Any class that then inherits from your `Base` is scanned by SQLAlchemy, and a `Table` is built from its `__tablename__` and its `mapped_column(...)` attributes.

How is this different from the old `declarative_base()` function? Your old file had `Base = declarative_base()`: a *function call* that *manufactures* a class at runtime. The new code has `class Base(DeclarativeBase):` - a normal class statement. The result behaves the same for models, but the new way:

- is a real class in the source file, so editors and type checkers (mypy, Pylance) understand `Mapped[int]` annotations on the models;
- lets you put settings on the class body (that is exactly what line 24 does with `metadata = ...`);
- is the only non-deprecated way in SQLAlchemy 2.0. I ran the old import in this project's venv and it prints `MovedIn20Warning: The declarative_base() function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0)`.

**Why it is here:** line 23 needs it as the parent of `Base`.

**If you removed or changed it:** `class Base(DeclarativeBase)` raises `NameError: name 'DeclarativeBase' is not defined` at import time, and nothing that touches the database can start. If you replaced it with the old `declarative_base()` function you would lose the ability to set `metadata` inside the class body and would get the deprecation warning on every start.

### Block 4: the comment above the naming convention

```python
# Predictable names for indexes and constraints. Without this the database
# invents names, which makes later migrations (dropping / altering a
# constraint) painful.
```

- `#` - starts a comment. Python ignores everything after `#` on that line.
- `Predictable names` - names you can *work out from a rule* without looking them up.
- `indexes and constraints` - an *index* is a lookup structure that makes `WHERE email = ...` fast. A *constraint* is a rule the database enforces: primary key (unique id), foreign key (must point at an existing row), unique (no duplicates), check (a condition such as `amount > 0`). Each of these objects has a name inside PostgreSQL.
- `Without this the database invents names` - if SQLAlchemy sends `UNIQUE (email)` with no name, PostgreSQL picks one itself (for example `users_email_key`). The rule it uses is PostgreSQL's, not yours, and it differs between databases.
- `later migrations (dropping / altering a constraint) painful` - to drop a constraint you must write `op.drop_constraint("<name>", ...)`. If you do not know the name, you have to connect to the database and look it up first; and it may differ between your laptop, a teammate's laptop and the server.

**Why it is here:** to explain *why* a block of string templates follows. Without it the dictionary looks like magic.

**If you removed or changed it:** no runtime change; just less understanding for the next reader.

### Block 5: start of the dictionary and the `ix` rule

```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
```

- `NAMING_CONVENTION` - a variable name. All capitals is the Python convention for a *constant* (a value you never reassign).
- `=` - assignment.
- `{` - opens a dictionary (`dict`). A dict is a set of `key: value` pairs.
- `"ix"` - the first key. SQLAlchemy recognises five short keys: `"ix"` = index, `"uq"` = unique constraint, `"ck"` = check constraint, `"fk"` = foreign key constraint, `"pk"` = primary key constraint. (You may also use the classes themselves, such as `Index`, as keys; the project uses the short strings.)
- `:` - separates key from value.
- `"ix_%(column_0_label)s"` - the value: a *template* for the index name.

Now the strange `%(...)s` part. This is Python's old-style string formatting with a dictionary. The pattern is `%(key)s`: a percent sign, the key in parentheses, and `s` for "insert as a string". Python example you can run:

```python
>>> "uq_%(table_name)s_%(column_0_name)s" % {"table_name": "categories", "column_0_name": "owner_id"}
'uq_categories_owner_id'
```

SQLAlchemy does exactly this: `template % ConventionDict(...)` (in its file `sqlalchemy/sql/naming.py`), where `ConventionDict` is a dictionary-like object that knows how to compute each token for the constraint being named. These are all the tokens this project uses:

| Token                     | What it becomes                                                                                                   | Available for                  |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `%(table_name)s`          | The name of the table the constraint belongs to, e.g. `users`.                                                    | every kind                     |
| `%(column_0_name)s`       | The name of the **first** column in the constraint (position 0), e.g. `owner_id`.                                 | every kind that has columns    |
| `%(column_0_label)s`      | The first column's *label*: `tablename_columnname`, e.g. `users_email`. (I checked: for `users.email` SQLAlchemy's internal `_ddl_label` is `users_email`.) | every kind that has columns    |
| `%(constraint_name)s`     | The name **you** gave the constraint with `name=...`. Required: if the constraint has no name, SQLAlchemy raises an error (shown in Block 7). | `ck` and others with a given name |
| `%(referred_table_name)s` | For a foreign key: the table it points **to**, e.g. `users` for `ForeignKey("users.id")`.                         | `fk` only                      |

(There are more tokens, such as `%(column_0_N_name)s` for "all columns joined with `_`", but the project does not use them.)

- `ix_` - a literal prefix; "ix" is short for index.
- `%(column_0_label)s` - the first column's label, i.e. `<table>_<column>`.

Concrete results from this project (I printed them from `Base.metadata` with the real models):

| Model line                                                                 | Resulting index name                 |
| -------------------------------------------------------------------------- | ------------------------------------ |
| `users.email` has `index=True`                                             | `ix_users_email`                     |
| `categories.owner_id` has `index=True`                                     | `ix_categories_owner_id`             |
| `expenses.category_id` has `index=True`                                    | `ix_expenses_category_id`            |
| `Index("ix_expenses_owner_id_expense_date", "owner_id", "expense_date")`  | `ix_expenses_owner_id_expense_date` (given by hand; the rule is not applied because a name was supplied and the template has no `%(constraint_name)s`) |

You can see these exact names in the migration file: `op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)`.

One small detail: this `"ix"` rule is the **only** rule SQLAlchemy has by default. I checked: `MetaData().naming_convention` is `{'ix': 'ix_%(column_0_label)s'}`. So the project repeats the default on purpose, because passing your own dictionary *replaces* the default; if `"ix"` were left out, indexes created with `index=True` would have no name at all.

**Why it is here:** so `index=True` on a column produces a name you can predict and type into `op.drop_index(...)` later.

**If you removed or changed it:** remove the whole `"ix"` entry and every `index=True` column gets an index whose `name` is `None`. I tested this: building the `CREATE INDEX` statement for such an index, or calling `Base.metadata.create_all(...)`, then fails with a bare `AssertionError` from inside SQLAlchemy (no helpful message), because an index must have a name. Change the template (say to `"idx_%(column_0_label)s"`) and Alembic's autogenerate would see that the database has `ix_users_email` while the models want `idx_users_email`, and propose dropping and recreating every index.

### Block 6: the `uq` rule

```python
    "uq": "uq_%(table_name)s_%(column_0_name)s",
```

- `"uq"` - the key for *unique constraints*: rules like "no two rows may share this value".
- `uq_` - literal prefix.
- `%(table_name)s` - the table name.
- `_` - a literal underscore between the parts.
- `%(column_0_name)s` - the first column in the constraint.

Concrete result from this project: `categories` has `UniqueConstraint("owner_id", "name", name="uq_categories_owner_id_name")`. Here the author gave the name by hand, and the template has no `%(constraint_name)s`, so SQLAlchemy keeps the hand-written name as is: `uq_categories_owner_id_name`. If the `name=` had been left out, the rule would have produced `uq_categories_owner_id` - only the *first* column (`column_0`), which hides the fact that `name` is also part of the constraint. That is exactly why the model writes the fuller name by hand.

Note: `users.email` has `unique=True`, `index=True`. SQLAlchemy turns that combination into one **unique index** (`CREATE UNIQUE INDEX ix_users_email`), not a `UNIQUE` constraint, so the `"uq"` rule is not used there. I confirmed this by compiling the `CREATE TABLE users` statement for PostgreSQL: there is no `UNIQUE` line in it, only the separate unique index.

**Why it is here:** so that any unique constraint you add later without a name still gets a predictable one.

**If you removed or changed it:** currently no constraint in the project relies on it (the only unique constraint is named by hand), so nothing changes today. The first time someone writes `UniqueConstraint("a")` without `name=`, PostgreSQL would invent `tablename_a_key` instead, and a future `op.drop_constraint` would have to guess it.

### Block 7: the `ck` rule

```python
    "ck": "ck_%(table_name)s_%(constraint_name)s",
```

- `"ck"` - the key for *check constraints*: a condition every row must satisfy, such as `amount > 0`.
- `ck_` - literal prefix.
- `%(table_name)s` - the table name.
- `%(constraint_name)s` - the name **you** wrote in `CheckConstraint(..., name="...")`. This token is special: when it appears in a template, SQLAlchemy takes the name you gave, feeds it into the template, and **replaces** your name with the result.

Concrete result from this project: `expenses` has `CheckConstraint("amount > 0", name="amount_positive")`. The template turns `amount_positive` into `ck_expenses_amount_positive`. That is the name in the migration file: `sa.CheckConstraint('amount > 0', name=op.f('ck_expenses_amount_positive'))`.

Why can the template not just use the column name, like the others? Because a check constraint is an arbitrary SQL expression (`amount > 0`, or `start_date <= end_date`); SQLAlchemy cannot reliably tell which column it is "about". So the rule says: *you* supply a short meaningful name, *I* add the prefix and the table.

The flip side: with this template, every `CheckConstraint` **must** have a `name=`. I tested a `CheckConstraint("amount > 0")` without a name under this convention: SQLAlchemy raises `sqlalchemy.exc.InvalidRequestError: Naming convention including %(constraint_name)s token requires that constraint is explicitly named.` the moment the table is defined (that is, at import time, not when you run a query).

About `op.f(...)` in the migration: the name produced by a convention is a special string subclass called `conv` (short for *converted*). It is a marker that says "this name has already been through the template; do not apply the template again". Alembic writes `op.f('ck_expenses_amount_positive')` in generated migrations for the same reason: `op.f` wraps the string in `conv`, so Alembic does not turn it into `ck_expenses_ck_expenses_amount_positive`. (Alembic's own docstring for `f`: "Indicate a string name that has already had a naming convention applied to it.")

**Why it is here:** so the one check constraint in the project (and any future ones) has a name you can find in `pg_constraint` and drop or change in a later migration.

**If you removed or changed it:** with no `"ck"` rule, `CheckConstraint("amount > 0", name="amount_positive")` would keep the bare name `amount_positive`. That still works, but it no longer tells you which table it belongs to, and two tables could not both have an `amount_positive` constraint without confusion. Alembic autogenerate would also notice that the database has `ck_expenses_amount_positive` while the models now want `amount_positive`.

### Block 8: the `fk` rule

```python
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
```

- `"fk"` - the key for *foreign key constraints*: a column that must contain the id of a row in another table.
- `fk_` - literal prefix.
- `%(table_name)s` - the table that **has** the foreign key column (the "child").
- `%(column_0_name)s` - the foreign key column itself (first column; all foreign keys here are single-column).
- `%(referred_table_name)s` - the table the foreign key **points to** (the "parent"). SQLAlchemy reads it from the string in `ForeignKey("users.id")` - the part before the dot.

Concrete results from this project:

| Model line                                                              | Resulting constraint name            |
| ----------------------------------------------------------------------- | ------------------------------------ |
| `categories.owner_id = mapped_column(ForeignKey("users.id", ...))`      | `fk_categories_owner_id_users`       |
| `expenses.owner_id = mapped_column(ForeignKey("users.id", ...))`        | `fk_expenses_owner_id_users`         |
| `expenses.category_id = mapped_column(ForeignKey("categories.id", ...))`| `fk_expenses_category_id_categories` |

Read the name left to right: "foreign key, on table `expenses`, column `category_id`, pointing to `categories`". All three appear in the migration file, for example `sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_categories_owner_id_users'), ondelete='CASCADE')`.

**Why it is here:** foreign keys are the constraints you most often need to change later (for example switching `ondelete` from `CASCADE` to `SET NULL`). That change is "drop the old constraint, create a new one", and `op.drop_constraint` needs the exact name.

**If you removed or changed it:** without the rule, SQLAlchemy sends `FOREIGN KEY(owner_id) REFERENCES users (id)` with no name and PostgreSQL invents one (`categories_owner_id_fkey` on PostgreSQL). Your old project hit exactly this: your migration `4161ea502697` had to *invent* a name by hand (`'post_users_fk'`) so that `downgrade()` could drop it. With the convention, you never have to think about it.

### Block 9: the `pk` rule and the end of the dictionary

```python
    "pk": "pk_%(table_name)s",
}
```

- `"pk"` - the key for *primary key constraints*: the column(s) that identify a row, here always `id`.
- `pk_` - literal prefix.
- `%(table_name)s` - the table name. No column token, because one table has exactly one primary key, so the table name alone is enough.
- `}` - closes the dictionary that started in Block 5.

Concrete results from this project: `pk_users`, `pk_categories`, `pk_expenses`. In the migration: `sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))`.

**Why it is here:** completeness. You rarely drop a primary key, but if you ever change `id` from `Integer` to `BigInteger`, or move to a composite key, you will be glad the name is known.

**If you removed or changed it:** PostgreSQL would name them `users_pkey`, `categories_pkey`, `expenses_pkey`. The application would run the same; only future migrations that touch the primary key would need to look up the names first.

### Block 10: the `Base` class

```python
class Base(DeclarativeBase):
```

- `class` - the Python keyword that defines a new class (a blueprint for objects).
- `Base` - the name of the new class. Every model does `class User(Base):`, so this is the root of the family tree.
- `(DeclarativeBase)` - the parentheses after a class name list its *parent classes*. `Base` inherits from SQLAlchemy's `DeclarativeBase` (imported in Block 3). SQLAlchemy watches for subclasses of a `DeclarativeBase` subclass: when it sees `class User(Base)` with a `__tablename__`, it creates `Table("users", Base.metadata, ...)` from the class attributes and sets up the mapping between `User` objects and `users` rows.
- `:` - starts the class body (the indented lines below).

**Why it is here:** the project needs one shared parent for all models so that they all register into the *same* `MetaData`. If two models used two different bases, they would live in two different `MetaData` objects, `Base.metadata.create_all` and Alembic would only see one of them, and `relationship()` between them would fail.

**If you removed or changed it:** every model file does `from app.database.base import Base`, so deleting the class gives `ImportError: cannot import name 'Base' from 'app.database.base'`. Renaming it means renaming it in three model files, `alembic/env.py` and `tests/conftest.py`.

### Block 11: attaching the `MetaData` with the naming convention

```python
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

- `metadata` - a class attribute with a name SQLAlchemy specifically looks for. The `DeclarativeBase` documentation lists `metadata` as one of the optional class-level attributes: "optional MetaData collection. If a registry is constructed automatically, this MetaData collection will be used to construct it." In plain words: *if you give me a `metadata` attribute, I will store all your tables in it instead of making my own.*
- `=` - assignment inside the class body, which creates a class attribute (shared by `Base` and all its subclasses, so `User.metadata is Base.metadata`).
- `MetaData(...)` - calling the class imported in Block 2 to create one `MetaData` object.
- `naming_convention=` - a *keyword argument*: you give the parameter by name. `MetaData` accepts a `naming_convention` dictionary and stores it as `metadata.naming_convention`.
- `NAMING_CONVENTION` - the dictionary from Blocks 5-9.

How the naming happens: when a `Table` is built and an `Index` or `Constraint` is attached to it, SQLAlchemy fires an internal "after_parent_attach" event (in `sqlalchemy/sql/naming.py`). The handler looks at the constraint's type, finds the matching key (`"fk"`, `"pk"`, ...) in `table.metadata.naming_convention`, and if the constraint has no name (or the template contains `%(constraint_name)s`) it fills the template and assigns the result. All of this happens while your model classes are being imported - long before any SQL is sent.

**Why it is here:** this single line is what connects the dictionary to the models. Without it, `NAMING_CONVENTION` would be a dictionary that nobody reads.

**If you removed or changed it:** `Base` would fall back to a default `MetaData()` whose only rule is `{"ix": "ix_%(column_0_label)s"}`. The models would still import and the indexes would still be named, but `pk`, `fk` and `uq` names would be left to PostgreSQL, and - important - the `CheckConstraint("amount > 0", name="amount_positive")` would keep the bare name `amount_positive`. The existing migration file, which contains `op.f('pk_users')` and friends, would then disagree with the models, and the next `alembic revision --autogenerate` would propose renaming everything.

### Compared to your old code

Your old `app/database.py` had this:

```python
from sqlalchemy.ext.declarative import declarative_base
...
Base = declarative_base()
```

What is different and why:

1. **`declarative_base()` function -> `class Base(DeclarativeBase)`.** The old import path `sqlalchemy.ext.declarative` is the SQLAlchemy 1.x location. In 2.0 it still works but prints `MovedIn20Warning` every time the app starts (I ran it to check). The 2.0 way is to subclass `DeclarativeBase`. Your models already used `Mapped[int] = mapped_column(...)`, which is 2.0 style, so the base was the one piece of 1.x left over.

2. **No naming convention -> `NAMING_CONVENTION`.** Your old `Base` used the default `MetaData()`, so only indexes got names. The effect is visible in your old migrations: in `4161ea502697_add_foregin_key_to_post_table.py` you had to write `op.create_foreign_key('post_users_fk', ...)` with a hand-made name so that `downgrade()` could call `op.drop_constraint('post_users_fk', ...)`. And in `a2ea52613b30_add_user_table.py` the `sa.UniqueConstraint('email')` had no name, so PostgreSQL picked one; if you ever needed to drop it you would have to look it up in `psql` first. The new project fixes that once, here, for every table.

3. **Base lives in its own file.** In the old project, `app/model.py` imported `Base` from `app/database.py`, which also built the engine from `settings`. That meant *importing a model* also *created an engine* and *read the `.env` file*. It worked, but it is the kind of coupling that later causes circular imports (for example when `config` wants to import a model). The new `base.py` imports nothing from the project, so it can be imported from anywhere, in any order.

There is no old equivalent of the docstring or of the naming-convention comment.

### Key terms in this file

| Term                  | One-line meaning                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| ORM                   | Object Relational Mapper: maps Python classes/objects to tables/rows.                                     |
| `MetaData`            | A container that holds all `Table` objects plus shared settings such as the naming convention.           |
| `DeclarativeBase`     | SQLAlchemy 2.0 class you subclass to create your own `Base`.                                             |
| `Base`                | This project's parent class for all models; `Base.metadata` lists every table.                           |
| constraint            | A rule the database enforces: primary key, foreign key, unique, check.                                   |
| index                 | A lookup structure that speeds up searches on a column.                                                  |
| naming convention     | A dictionary of templates that decide the names of constraints and indexes.                               |
| `%(key)s`             | Python's old-style string formatting with a dictionary; `"a_%(x)s" % {"x": "b"}` gives `"a_b"`.          |
| `%(table_name)s`      | Token: the table the constraint belongs to.                                                               |
| `%(column_0_name)s`   | Token: the name of the first column in the constraint.                                                   |
| `%(column_0_label)s`  | Token: `tablename_columnname` of the first column.                                                        |
| `%(constraint_name)s` | Token: the name you gave with `name=`; the template result replaces it; a name is then mandatory.         |
| `%(referred_table_name)s` | Token: the table a foreign key points to.                                                             |
| `conv` / `op.f()`     | A marker meaning "this name is already converted, do not apply the template again".                      |
| keyword argument      | Passing an argument by name: `MetaData(naming_convention=...)`.                                           |
| class attribute       | A variable defined in a class body, shared by the class and its subclasses.                              |

---

## File: app/database/session.py

### What this file is for

This file owns the live connection to PostgreSQL. It creates four things:

1. `engine` - the *connection pool*. Opening a TCP connection to PostgreSQL is slow (tens of milliseconds); the engine opens a few and reuses them.
2. `SessionLocal` - a *factory* that produces `Session` objects. A `Session` is the ORM's workspace: you add objects to it, query through it, and `commit()` it.
3. `get_db` - the FastAPI *dependency* that gives every HTTP request its own `Session` and guarantees it is closed afterwards.
4. `check_database_connection` - a tiny function that runs `SELECT 1` and raises if the database cannot be reached. It is used once at startup (`app/main.py`) and by `GET /health`.

Who imports it: `app/core/dependencies.py` (`from app.database.session import get_db`, then wraps it as `DatabaseSession = Annotated[Session, Depends(get_db)]` which every router uses), `app/main.py` and `app/routers/health.py` (`check_database_connection`), and `tests/conftest.py` (to override `get_db`). What it imports: `settings` from `app/core/config.py` for the database URL, and four names from SQLAlchemy.

### The whole file

```python
"""
Database engine and session management.

    engine                     -> the connection pool to PostgreSQL
    SessionLocal               -> factory that creates database sessions
    get_db                     -> FastAPI dependency: one session per request
    check_database_connection  -> used at startup and by the health check
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    # Test each pooled connection before using it, so a database restart
    # does not surface as random "server closed the connection" errors.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Open a session for the request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> None:
    """Run a trivial query; raises an exception if the database is unreachable."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
```

### Walkthrough, block by block

### Block 1: the module docstring

```python
"""
Database engine and session management.

    engine                     -> the connection pool to PostgreSQL
    SessionLocal               -> factory that creates database sessions
    get_db                     -> FastAPI dependency: one session per request
    check_database_connection  -> used at startup and by the health check
"""
```

- `"""` ... `"""` - the module docstring; documentation only.
- `Database engine and session management.` - one-line summary. *Engine* and *session* are the two SQLAlchemy words you will see on every line below.
- `engine -> the connection pool to PostgreSQL` - a *pool* is a small set of already-open connections that are lent out and returned, instead of opening a new one for every query.
- `SessionLocal -> factory that creates database sessions` - a *factory* is anything you call to get a new object. `SessionLocal()` returns a fresh `Session`.
- `get_db -> FastAPI dependency: one session per request` - a *dependency* is a function FastAPI runs before your endpoint and whose result it passes in as a parameter. "One session per request" is the rule this file enforces.
- `check_database_connection -> used at startup and by the health check` - names the two callers: `lifespan()` in `app/main.py` and `health_check()` in `app/routers/health.py`.

**Why it is here:** a four-line map of the file, so you can find the piece you need.

**If you removed or changed it:** no runtime effect.

### Block 2: importing `Generator`

```python
from collections.abc import Generator
```

- `from collections.abc import` - `collections.abc` is a module in Python's standard library. "abc" stands for *abstract base classes*: it holds the official definitions of "what counts as an iterable", "what counts as a generator", and so on.
- `Generator` - the abstract base class for generator objects (functions that use `yield`; explained in Block 9). Here it is used only as a *type hint* on line 27, so that the annotation `Generator[Session, None, None]` can be written. The older spelling `typing.Generator` still works but is a deprecated alias since Python 3.9; `collections.abc.Generator` is the modern one.

**Why it is here:** so `get_db` can say precisely what it yields. FastAPI does not need the hint (it detects `yield` by looking at the function), but your editor and type checker do.

**If you removed or changed it:** line 27 raises `NameError: name 'Generator' is not defined` when the module is imported, which happens the moment `app/core/dependencies.py` is imported, which happens when any router is imported, which happens when `app/main.py` is imported. So: the app does not start.

### Block 3: importing `create_engine` and `text`

```python
from sqlalchemy import create_engine, text
```

- `from sqlalchemy import` - take names from the top-level SQLAlchemy package.
- `create_engine` - a *function* that builds an `Engine` from a database URL. The `Engine` knows which driver to use (psycopg2 for `postgresql+psycopg2://`), how to speak PostgreSQL's dialect of SQL, and manages the connection pool.
- `,` - separates the two names being imported.
- `text` - a function that wraps a plain SQL string into a `TextClause` object (I checked: `type(text("SELECT 1")).__name__` is `TextClause`). SQLAlchemy 2.0 refuses to execute a bare string: `connection.execute("SELECT 1")` raises `ObjectNotExecutableError: Not an executable object: 'SELECT 1'`. `text()` is the official way to say "this really is SQL, run it".

**Why it is here:** `create_engine` is used on line 17; `text` on line 39.

**If you removed or changed it:** `NameError` at import time on line 17 (for `create_engine`) or when `check_database_connection()` first runs (for `text`), which is at startup, so the app would fail to boot either way.

### Block 4: importing `Session` and `sessionmaker`

```python
from sqlalchemy.orm import Session, sessionmaker
```

- `from sqlalchemy.orm import` - names from the ORM sub-package.
- `Session` - the class of the object your endpoints receive as `db`. It holds the objects you have loaded or added, tracks what changed, starts a transaction when you first use it, and sends `INSERT`/`UPDATE`/`DELETE` on `flush()`/`commit()`. In this file `Session` is only used in the type hint `Generator[Session, None, None]`; the real objects are created by `SessionLocal()`.
- `sessionmaker` - a class that, when called with configuration, returns a *factory* for `Session` objects. You configure once (`sessionmaker(bind=engine, ...)`) and then call the result many times (`SessionLocal()`), each call giving a new `Session` with that configuration. SQLAlchemy's own docstring: "A configurable Session factory... generates new Session objects when called."

**Why it is here:** `sessionmaker` builds `SessionLocal` on line 24; `Session` annotates `get_db` on line 27.

**If you removed or changed it:** `NameError` on line 24 or 27 at import time; the application cannot start.

### Block 5: importing `settings`

```python
from app.core.config import settings
```

- `from app.core.config import` - import from this project's own `app/core/config.py` (explained in doc 03).
- `settings` - the single `Settings()` object that file creates. It has already read the environment variables and the `.env` file by the time this line runs.

Only one attribute is used here: `settings.database_url`. In `config.py` it is a `@property` - a method that you read like an attribute, without parentheses - which either returns the `DATABASE_URL` environment variable (fixing a `postgres://` prefix if a hosting provider gave one) or builds the URL from `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_HOSTNAME`, `DATABASE_PORT`, `DATABASE_NAME` with `sqlalchemy.engine.URL.create(...)`, which escapes special characters in the password.

**Why it is here:** the database URL must not be hard-coded; it differs between your laptop, the tests (which set `DATABASE_URL=sqlite+pysqlite:///:memory:`) and the server.

**If you removed or changed it:** `NameError: name 'settings' is not defined` on line 18 at import time.

### Block 6: creating the engine, first argument

```python
engine = create_engine(
    settings.database_url,
```

- `engine` - a module-level variable (a global inside this file). Created **once**, when the module is first imported, and shared by the whole process. That is correct: you want exactly one pool per application.
- `=` - assignment.
- `create_engine(` - calls the function imported in Block 3. The closing `)` is on line 22; the arguments are spread over several lines for readability.
- `settings.database_url` - the first, positional argument: the URL. A SQLAlchemy URL looks like `dialect+driver://username:password@host:port/database`, for example `postgresql+psycopg2://postgres:secret@localhost:5432/expense_tracker`. "postgresql" is the dialect (which flavour of SQL to speak), "psycopg2" the driver (the Python package that does the network talking).
- `,` - a trailing comma after the last-so-far argument; Python allows it and it keeps diffs small when you add arguments.

One important fact I confirmed by running it: **`create_engine` does not connect.** It parses the URL, imports the driver and prepares the pool, but no network traffic happens until the first `engine.connect()` or `Session` query. I created an engine with a host name that does not exist and it returned `Engine(postgresql+psycopg2://u:***@host-that-does-not-exist.invalid:5432/db)` without error; the error (`OperationalError: could not translate host name ...`) only appeared on `.connect()`. This is why `app/main.py` calls `check_database_connection()` in `lifespan` - to force that first connection at startup and fail early.

The pool you get by default (I checked `type(engine.pool).__name__`): `QueuePool`, with `pool_size=5` connections kept open, `max_overflow=10` extra allowed under load, and `pool_timeout=30` seconds to wait for a free one. If all 15 are busy for 30 seconds, a request fails with `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out...`. That only happens if sessions are not returned - which is what `get_db`'s `finally` (Block 13) prevents.

**Why it is here:** everything that touches the database goes through this one engine: `SessionLocal` is bound to it and `check_database_connection` connects through it.

**If you removed or changed it:** remove it and `sessionmaker(bind=engine, ...)` on line 24 raises `NameError` at import. Replace the URL with a wrong password and the app imports fine but `lifespan` raises `OperationalError: FATAL: password authentication failed` at startup, and `uvicorn` exits.

### Block 7: `pool_pre_ping=True` and its comment

```python
    # Test each pooled connection before using it, so a database restart
    # does not surface as random "server closed the connection" errors.
    pool_pre_ping=True,
)
```

- `#` ... - two comment lines explaining the argument below.
- `Test each pooled connection before using it` - what the option does (details next).
- `a database restart does not surface as random "server closed the connection" errors` - the problem it solves. "server closed the connection unexpectedly" is the message the PostgreSQL client library (libpq, used by psycopg2) gives when it tries to use a TCP connection that the server has since dropped.
- `pool_pre_ping=` - a keyword argument of `create_engine`. SQLAlchemy's docstring: "if True will enable the connection pool 'pre-ping' feature that tests connections for liveness upon each checkout."
- `True` - the Python boolean. The default is `False`.
- `,` - trailing comma.
- `)` - closes the `create_engine(` call that started on line 17.

What happens, step by step (I read the pool code in `sqlalchemy/pool/base.py` and `engine/default.py`):

1. A request asks the pool for a connection ("checkout").
2. If `pool_pre_ping` is on and the connection is not brand new, SQLAlchemy runs the dialect's ping - for PostgreSQL that is literally `SELECT 1` (`dialect._dialect_specific_select_one`).
3. If the ping succeeds, the connection is handed out as usual.
4. If the ping raises a *disconnect* error, SQLAlchemy throws that connection away, marks the other pooled connections from before the failure as stale, opens a fresh connection, and hands *that* out. Your code never sees the failure.

The scenario it protects against: the API has been running for a day; the pool holds 5 idle connections; someone restarts PostgreSQL (or a cloud provider fails over). Every one of those 5 connections is now dead on the server side, but the pool does not know. Without pre-ping, the first request after the restart grabs a dead connection and the user sees `500 Internal Server Error` with `OperationalError: server closed the connection unexpectedly`; only then does SQLAlchemy notice the disconnect and throw away the other stale connections, so later requests work again (if several requests arrive at the same moment, several can fail). With pre-ping, each of those first requests pays one extra `SELECT 1` round trip (well under a millisecond on a local network) and succeeds.

The cost: one tiny extra query per checkout, i.e. per request. For this project that is negligible.

**Why it is here:** a web API runs for days; databases restart. This makes restarts invisible to users.

**If you removed or changed it:** the app works identically until the first database restart or network blip, after which at least one request (more if several arrive together) fails with 500 before the pool heals itself. In the tests nothing changes (they build their own engine in `tests/conftest.py`).

### Block 8: the session factory

```python
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
```

- `SessionLocal` - the name of the factory. It is capitalised like a class because you *call* it like a class: `SessionLocal()` gives you a new `Session`. "Local" is a long-standing FastAPI-tutorial name meaning "the session for this one place (request)"; it is only a name.
- `=` - assignment.
- `sessionmaker(` - the class from Block 4. Calling it with configuration returns the factory.
- `bind=engine` - keyword argument: *bind* means "connect to". Every `Session` made by this factory will borrow its connections from this `engine`'s pool.
- `autocommit=False` - keyword argument. "Autocommit" would mean "save every statement immediately". `False` means nothing is saved until you call `db.commit()`. In SQLAlchemy 2.0 this is the **only** allowed value - I tried `autocommit=True` and got `sqlalchemy.exc.ArgumentError: autocommit=True is no longer supported`. The docstring says the parameter "is present for backwards compatibility but must remain at its default value of False". So the argument is here for readability: it tells the reader out loud that commits are manual.
- `autoflush=False` - keyword argument. *Flush* means "send my pending `INSERT`/`UPDATE`/`DELETE` to the database now (inside the open transaction, not yet committed)". With the default `autoflush=True`, the session flushes automatically **before every query**, so a query can "see" an object you added a moment ago. With `False`, pending changes stay in Python until you call `db.flush()` or `db.commit()`. I tested both: after `db.add(User(email="b@x.com", ...))`, a `select(User).where(User.email == "b@x.com")` found **nothing** with `autoflush=False` and found the user with `autoflush=True`.
- `)` - closes the call.

Why turn autoflush off? Two reasons people give: (1) SQL is sent only when *you* say so, which makes behaviour easier to predict and debug; (2) an `IntegrityError` (duplicate email, for example) surfaces at your `commit()` line, not in the middle of some unrelated read. In this project every router follows the pattern `db.add(x)` -> `db.commit()` -> `db.refresh(x)` (see `app/routers/auth.py`, `categories.py`, `expenses.py`), and the only reads that happen after an `add` are after the `commit`, so `autoflush` never actually changes a result here. It is a safe, conventional default inherited from your old file.

**Why it is here:** one shared, pre-configured factory so that `get_db` (and only `get_db`) creates sessions, all with the same settings.

**If you removed or changed it:** remove it and `get_db` raises `NameError` on `SessionLocal()` for every request (every endpoint that uses `db` returns 500). Drop `bind=engine` and `SessionLocal()` still works but the first query raises `UnboundExecutionError: Could not locate a bind configured on ...`. Change `autoflush` to `True` and, with the current routers, nothing observable changes.

### Block 9: the `get_db` signature

```python
def get_db() -> Generator[Session, None, None]:
```

- `def` - keyword that defines a function.
- `get_db` - the function name. Routers never call it themselves; FastAPI does, through `Depends(get_db)` (wrapped in `app/core/dependencies.py` as `DatabaseSession = Annotated[Session, Depends(get_db)]`).
- `()` - no parameters. FastAPI could inject other dependencies here, but a session needs nothing.
- `->` - "returns". Everything after the arrow is the *return type hint*: information for editors and type checkers, ignored by Python at run time.
- `Generator[Session, None, None]` - the type imported in Block 2, with three things in square brackets. Square brackets after a type name *parameterise* it, like filling in blanks. For `Generator` the three blanks are: **what it yields** (`Session`), **what can be sent into it** (`None` - nothing), **what it returns at the end** (`None` - nothing).
- `:` - starts the function body.

**What a generator is.** A normal function runs to the end and `return`s once. A function that contains the keyword `yield` is a *generator function*: calling it does **not** run it; it returns a *generator object* that you advance step by step. Each `next()` runs the body until the next `yield`, hands out the yielded value, and **pauses** there, keeping all local variables alive. I ran this:

```python
def g():
    print("before yield")
    x = yield 1
    print("after yield, got", x)

gen = g()     # nothing is printed: the body has not started
next(gen)     # prints "before yield", gives back 1, pauses at the yield
next(gen)     # resumes: prints "after yield, got None", reaches the end,
              # and raises StopIteration ("the generator is finished")
```

A `for` loop does the `next()` calls for you; FastAPI does them for `get_db`.

**How FastAPI uses a yield dependency.** When a request arrives for an endpoint that declares `db: DatabaseSession`, FastAPI:

1. calls `get_db()` to get the generator and advances it to the `yield` - everything *before* `yield` runs now;
2. takes the yielded value (`db`) and passes it to your endpoint as the `db` parameter;
3. runs your endpoint and sends the response;
4. advances the generator once more, so everything *after* `yield` runs - that is the cleanup.

I checked the exact timing in the FastAPI version this project pins (0.141.1, file `fastapi/routing.py`): a yield dependency with no explicit `scope` is attached to the request-level exit stack, which is closed **after** the response has been sent to the client. So `db.close()` runs after the user already has their answer; it never delays the response.

**Why it is here:** this is the "one session per request" rule in code. Each request gets its own `Session`, so two requests can never mix up their objects or transactions, and each session is guaranteed to be closed.

**If you removed or changed it:** `app/core/dependencies.py` does `from app.database.session import get_db` and would fail with `ImportError`; every router imports from `dependencies.py`, so the app does not start. If you turned it into a normal function with `return db` instead of `yield db`, FastAPI would still inject a session, but it would **never be closed**: each request would leak one pooled connection, and after 15 requests every further request would hang 30 seconds and fail with `TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00`.

### Block 10: the `get_db` docstring

```python
    """Open a session for the request and always close it afterwards."""
```

- `"""..."""` - a one-line function docstring. It becomes `get_db.__doc__`.
- `Open a session for the request` - what happens before `yield`.
- `always close it afterwards` - what the `finally` guarantees. "Always" is the key word: success or failure.

**Why it is here:** so the promise of the function ("always close") is written down where a reader will see it.

**If you removed or changed it:** no runtime change.

### Block 11: creating the session

```python
    db = SessionLocal()
```

- `db` - a local variable; the name every endpoint uses too, because FastAPI passes this exact object in as the `db` parameter.
- `=` - assignment.
- `SessionLocal()` - calls the factory from Block 8. Returns a brand-new `Session` bound to `engine`, with `autoflush=False`.

Like the engine, a new session is *lazy*: I created one with SQL echoing switched on and nothing was printed. The session only borrows a connection from the pool (and sends `BEGIN`) when the endpoint runs its first query. If the request ends before any query is run, the session never borrowed a connection, and `close()` simply has nothing to return.

**Why it is here:** this is the only place in the whole project where a `Session` is created for request handling. That makes it easy to swap: the tests replace `get_db` with a version that creates sessions on an in-memory SQLite engine instead.

**If you removed or changed it:** `yield db` would raise `NameError: name 'db' is not defined`, and every endpoint that uses the database would return 500.

### Block 12: handing the session to the endpoint

```python
    try:
        yield db
```

- `try:` - opens a *try block*. Python runs the indented code and, whatever happens inside it (normal finish, `return`, or an exception), the matching `finally:` block (Block 13) will run afterwards.
- `yield db` - the pause point explained in Block 9. The session object is handed to FastAPI, which passes it to the endpoint. The generator stays frozen on this line for the entire time the endpoint runs.

Why the `yield` is *inside* the `try`: if the endpoint raises an exception (an `HTTPException(404)`, an `IntegrityError`, anything), FastAPI re-raises that exception **inside the generator at the `yield` line** (this is how Python's `contextlib.contextmanager`, which FastAPI uses under the hood, works). Because the `yield` sits inside `try`, that re-raised exception triggers the `finally`.

**Why it is here:** this is where the request gets its session, and the `try` is what makes the cleanup unconditional.

**If you removed or changed it:** without `yield` the function is not a generator and FastAPI would pass the *return value* (`None`) as `db`; the first `db.scalar(...)` in any endpoint would fail with `AttributeError: 'NoneType' object has no attribute 'scalar'`. Without the `try`, see the next block.

### Block 13: always closing the session

```python
    finally:
        db.close()
```

- `finally:` - the part of a `try` statement that runs **no matter what**: after the body completed normally, after an exception, even if the exception is not caught.
- `db.close()` - method call on the `Session`. SQLAlchemy's docstring says it "expunges all ORM objects associated with this Session, ends any transaction in progress and releases any Connection objects which this Session itself has checked out". In plain words: (1) forget every loaded object; (2) if the endpoint did not `commit()`, **roll back** - I verified this: after `db.add(user)`, `db.flush()` (so the `INSERT` was already sent) and then `db.close()` without commit, the log shows `ROLLBACK` and `SELECT count(*) FROM users` returns `0`; (3) give the connection back to the pool so the next request can use it.

What `try/finally` buys you, concretely. Imagine `POST /api/v1/categories` with a name the user already has. The router does `db.add(category)`, `db.commit()`; the database rejects it with `IntegrityError` because of `uq_categories_owner_id_name`; the router turns that into `HTTPException(409)`. That exception leaves the endpoint, FastAPI throws it into `get_db` at the `yield`, the `finally` runs, `db.close()` rolls back the broken transaction and returns the connection, and *then* FastAPI sends the 409 response. Without the `finally`, the session (and its connection, stuck in a failed transaction) would be abandoned: the pool would slowly drain, and after 15 such errors the whole API would freeze with the `TimeoutError` from Block 9.

Note that `close()` is **not** `commit()`: it never saves anything by itself. Saving is always the endpoint's explicit `db.commit()`.

**Why it is here:** leak-proof sessions. The pool has only 5 (+10) connections; this line is why they always come back.

**If you removed or changed it:** every request that raises leaks a connection (see above). If you replaced it with `db.commit()`, an endpoint that raised halfway through would have its half-done changes saved - a data-corruption bug. If you wrote `db.close()` *after* the `try/finally` instead of inside `finally`, it would run only on the success path.

### Block 14: the `check_database_connection` signature

```python
def check_database_connection() -> None:
```

- `def` - defines a function.
- `check_database_connection` - the name: it *checks*, it does not "connect the app" (the engine already handles connections). It is called in `app/main.py` inside `lifespan()` (once, at startup) and in `app/routers/health.py` inside `health_check()` (every time someone calls `GET /health`).
- `()` - no parameters; it uses the module-level `engine`.
- `-> None` - return type hint: the function returns nothing useful. Its *result* is communicated by either returning normally (database reachable) or raising an exception (not reachable).
- `:` - starts the body.

**Why it is here:** two callers need the same three lines; putting them here means one definition. Also, keeping it in this file keeps `engine` private to this module - `main.py` and `health.py` do not need to import `engine` at all.

**If you removed or changed it:** `app/main.py` and `app/routers/health.py` both import it by name, so the app fails to import with `ImportError: cannot import name 'check_database_connection'`.

### Block 15: its docstring

```python
    """Run a trivial query; raises an exception if the database is unreachable."""
```

- `"""..."""` - the function docstring.
- `Run a trivial query` - `SELECT 1`, the smallest possible SQL statement.
- `raises an exception if the database is unreachable` - the contract: callers must be ready for an exception. `lifespan()` lets it propagate (so `uvicorn` refuses to start); `health_check()` catches it and answers `503 Service Unavailable` with `"Database is unavailable"`.

**Why it is here:** states the contract (success = no exception).

**If you removed or changed it:** no runtime change.

### Block 16: opening a connection with `with`

```python
    with engine.connect() as connection:
```

- `with` - the keyword that starts a *context manager* block. A context manager is any object that knows how to set something up when you enter the block and tear it down when you leave, **even if an exception happens inside**. The rule is: `with X as y:` calls `X.__enter__()` and stores the result in `y`; then runs the block; then calls `X.__exit__()` no matter how the block ended. It is the same guarantee as `try/finally`, packaged into an object. You already use it with files: `with open(path) as f:` closes the file for you.
- `engine.connect()` - method on the `Engine` from Block 6. This is where a real connection is taken: the pool hands out an idle connection (after the pre-ping of Block 7) or opens a new one if none is idle. It returns a `Connection` object. The SQLAlchemy docstring says: "after the block is completed, the connection is 'closed' and its underlying DBAPI resources are returned to the connection pool. This also has the effect of rolling back any transaction that was explicitly begun or was begun via autobegin".
- `as connection` - the name the `Connection` is bound to inside the block.
- `:` - starts the block.

I ran it with SQL echo on. Inside the block `connection.closed` was `False`; the log showed `BEGIN (implicit)`, then `SELECT 1`, then on leaving the block `ROLLBACK`; after the block `connection.closed` was `True`. So the connection is cleanly returned even though the code never calls `close()`.

**Why it is here:** borrow a connection for exactly the length of the check, and give it back automatically.

**If you removed or changed it:** written as `connection = engine.connect()` with no `with` and no `close()`, each `GET /health` call would leak one pooled connection; an uptime monitor hitting `/health` every 30 seconds would exhaust the pool in under 8 minutes and the API would start failing with the `TimeoutError` from Block 9.

### Block 17: the trivial query

```python
        connection.execute(text("SELECT 1"))
```

- `connection.execute(` - method on the `Connection` that sends a statement to PostgreSQL and returns a result object. The result is ignored here on purpose: the only thing that matters is whether the call raises.
- `text(` - the function from Block 3 that turns the string into a `TextClause`. Required: `connection.execute("SELECT 1")` with a bare string raises `ObjectNotExecutableError: Not an executable object: 'SELECT 1'` (I ran it).
- `"SELECT 1"` - the SQL. It asks the database to return the number 1. It needs no table, so it works on a brand-new empty database, and it proves the whole chain: host reachable, port open, user and password accepted, database name exists.
- `)` `)` - close `text(` and then `execute(`.

What can go wrong, and what the caller sees:

| Situation                                   | Exception raised here                                                   | At startup (`lifespan`)       | On `GET /health`                  |
| ------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------- | --------------------------------- |
| PostgreSQL not running / wrong host         | `OperationalError: ... could not translate host name` or `connection refused` | `uvicorn` exits with traceback | `503 {"detail": "Database is unavailable"}` |
| Wrong password                              | `OperationalError: FATAL: password authentication failed for user ...`  | same                          | same                              |
| Database name does not exist                | `OperationalError: FATAL: database "..." does not exist`                | same                          | same                              |
| Everything fine                             | nothing; returns `None`                                                 | logs "Database connection established" | `200 {"status": "ok", "database": "connected"}` |

Small aside: because `pool_pre_ping=True`, when this connection comes from the pool (not brand new) PostgreSQL actually receives **two** `SELECT 1`s - the ping from the pool and then this one. That is fine; they are the cheapest queries that exist.

**Why it is here:** the whole point of the function. Without a statement, `engine.connect()` alone would already prove the connection, but `SELECT 1` additionally proves the server answers queries, and it is the conventional, driver-independent way to do a health check.

**If you removed or changed it:** with only the `with engine.connect()` line, the check would still raise for an unreachable server (connecting is where most failures appear), so it would mostly still work; but a replaced `SELECT 1` with, say, `SELECT * FROM users` would make `/health` fail with `ProgrammingError: relation "users" does not exist` on a fresh database before `alembic upgrade head` has run, which is not what a health check should report.

### Compared to your old code

Your old `app/database.py` (without the commented-out lines at the bottom):

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config import settings
Database_URL = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}/{settings.DATABASE_NAME}"

engine= create_engine(Database_URL)

SessionLocal = sessionmaker(autocommit= False, autoflush=False, bind=engine)

Base = declarative_base()

def connect_database():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database Connecting Successfully")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

You had most of the right ideas already. `get_db` is **identical in logic** - the new one only adds the type hint and a docstring. `SessionLocal` has the **same three arguments** in a different order. `connect_database` is the same `with`/`SELECT 1` idea. What changed, and why:

1. **The URL moved to `settings.database_url`.** The old f-string had three small problems. (a) `DATABASE_PORT` was declared in `config.py` but never put into the URL, so it always used 5432 - fine on your laptop, wrong the first time a hosted database uses another port. (b) Special characters were not escaped. I tested the old f-string shape with a password of `p@ss`: SQLAlchemy parsed `postgresql://postgres:p@ss@localhost/db` as password `p` and host `ss@localhost`, so the connection would fail with a confusing "could not translate host name" error. `URL.create(...)` in the new `config.py` escapes the `@` to `%40` (`postgresql+psycopg2://postgres:p%40ss@localhost:5432/db`), which parses correctly. (c) The old `config.py` declared `DATABASE_PASSWORD: int`, which works for `2233` but makes the app refuse to start (`ValidationError`) the moment a password contains a letter. The new one is `str`. None of these bit you because your local setup happened to avoid them; they are the kind of thing that only shows up on deployment day.

2. **`pool_pre_ping=True` was added.** The old engine had no protection against the database restarting under a running API (see Block 7).

3. **`Base` moved to `base.py`**, together with the new naming convention (see that file's comparison).

4. **`connect_database` became `check_database_connection` and stopped printing.** The old function printed `"Database Connecting Successfully"` with `print`. The new one returns silently and lets *the caller* decide what to say: `main.py` logs through Python's `logging` (with timestamp and level), and `health.py` turns a failure into a `503`. A function that both checks *and* prints cannot be reused for `/health`, where a print is useless. The new name also says what it does: it does not connect "the database"; it checks that a connection is possible.

5. **The commented-out block at the bottom was removed.** It contained your real local password (`password=2233`) and a hand-written `psycopg2` retry loop. Passwords must never sit in source files, even in comments, because the file goes into Git. The retry idea is now covered differently: `pool_pre_ping` heals the pool at run time, and the `lifespan` check fails fast at startup so the process manager (or you) restarts it.

6. **Small style things:** `Database_URL` (capital D, snake case) became a property with a lowercase name; `engine= create_engine(` became `engine = create_engine(`; the two-blank-lines-between-functions rule (PEP 8) is followed; every function has a type hint and a docstring.

### Key terms in this file

| Term                   | One-line meaning                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| engine                 | The SQLAlchemy object that owns the connection pool and knows the SQL dialect and driver.              |
| connection pool        | A small set of open database connections that are lent out and returned, to avoid reconnecting.        |
| `create_engine`        | Builds an engine from a URL; does **not** connect until first use.                                     |
| `pool_pre_ping`        | Before lending out a pooled connection, run `SELECT 1` on it and replace it if it is dead.             |
| `QueuePool`            | The default pool: 5 connections kept, up to 10 more under load, 30 s wait before `TimeoutError`.        |
| `Session`              | The ORM workspace for one unit of work: holds objects, tracks changes, `commit()`s them.               |
| `sessionmaker`         | A configured factory; calling it returns a new `Session`.                                              |
| `autocommit=False`     | Nothing is saved until `db.commit()`; the only value SQLAlchemy 2.0 allows.                            |
| `autoflush=False`      | Pending adds/updates are not sent before queries; only on `flush()`/`commit()`.                        |
| generator function     | A function containing `yield`; calling it returns a generator that runs step by step and pauses at `yield`. |
| `yield`                | Pauses the generator, hands out a value, and later resumes from the same place.                        |
| `Generator[A, B, C]`   | Type hint: yields `A`, accepts `B` via `send()`, returns `C`.                                           |
| dependency with `yield`| A FastAPI dependency whose code after `yield` runs as cleanup after the response is sent.              |
| `try` / `finally`      | `finally` runs no matter how the `try` block ended - normal, `return`, or exception.                    |
| `Session.close()`      | Forgets loaded objects, rolls back any uncommitted transaction, returns the connection to the pool.    |
| context manager / `with` | `with X as y:` sets up on entry and always tears down on exit, like a packaged `try/finally`.        |
| `engine.connect()`     | Borrows a `Connection` from the pool; as a context manager it returns it (and rolls back) on exit.     |
| `text("...")`          | Wraps a raw SQL string so SQLAlchemy will execute it; bare strings are refused in 2.0.                 |
| `SELECT 1`             | The smallest valid query; used only to prove the database answers.                                      |
| `OperationalError`     | SQLAlchemy's exception for "cannot reach / cannot log in to the database".                             |

---

## Summary of this folder

`app/database/` is two small files with two clearly separated jobs. `base.py` defines *what the tables look like*: the `Base` class that every model inherits, carrying a `MetaData` whose naming convention gives every primary key, foreign key, unique, check constraint and index a predictable name such as `fk_expenses_owner_id_users` - names you can read in the migration file and later drop or alter without guessing. `session.py` defines *how to talk to the live database*: one `engine` (a connection pool that pings each connection before use so database restarts stay invisible), one `SessionLocal` factory configured for manual commits, the `get_db` generator that gives each HTTP request its own `Session` and always closes it through `try/finally`, and `check_database_connection`, a `SELECT 1` inside a `with engine.connect()` block that `main.py` runs at startup and `/health` runs on demand.

The two files never import each other. The models import `Base` from `base.py`; `alembic/env.py` reads `Base.metadata` to know what the database should contain; the routers reach `session.py` only through `DatabaseSession` in `app/core/dependencies.py`; and `main.py` and `health.py` import just the check function. Compared with your old single `app/database.py`, the logic of `get_db` and the session factory is unchanged - what was added is the naming convention, `pool_pre_ping`, a URL builder that escapes passwords and includes the port, a reusable check function with no `print`, and the removal of a password from a comment. Everything that runs in this folder runs either once at import time (engine, factory, `Base`) or once per request (`get_db`); nothing here ever decides *what* to query - that is the routers' job.
