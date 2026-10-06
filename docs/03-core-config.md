# app/core/config.py (settings)

This document explains two files:

- `app/core/__init__.py` - a tiny file that turns the `core` folder into a Python package.
- `app/core/config.py` - the **settings** of the application: database address, secret key, token lifetime, allowed frontend URLs, and so on.

Every line is explained. The part you said you did not understand (`model_config = SettingsConfigDict(...)`) gets the most space, in Block 5 of `config.py`.

## Four words you will see a lot

Before the code, four plain-words definitions. Come back here if you forget one.

| Word | Meaning |
| --- | --- |
| **environment variable** | A named value that the operating system keeps for a running program. Example: `DATABASE_PORT=5432`. You can set one in the terminal (`set DATABASE_PORT=5432` on Windows, `export DATABASE_PORT=5432` on Linux/Mac) or in a hosting dashboard. Programs read them with `os.environ["DATABASE_PORT"]`. |
| **`.env` file** | A plain text file named `.env` in the project root, one `NAME=value` per line. It is a convenient place to keep environment variables for your own machine. It is listed in `.gitignore`, so it never goes to GitHub. |
| **pydantic** | A library that checks and converts data. You already use it: every `BaseModel` schema in your old project is pydantic. `pydantic-settings` is a small add-on library from the same team. It makes a pydantic model that fills itself from environment variables and `.env`. |
| **field** | One named value inside a pydantic model, written as `NAME: type = default`. In this file every field is one setting. |

---

## File: app/core/__init__.py

### What this file is for

In Python, a folder becomes a **package** (something you can import from with dots) only when it contains a file named `__init__.py`. This file exists so that `from app.core.config import settings` works: `app` is a folder, `core` is a folder inside it, `config` is the file `config.py`, and `settings` is a name inside that file. Python needs an `__init__.py` in `app/` and in `app/core/` to follow that dotted path.

Nobody imports this file by name. Python runs it automatically, once, the first time anything inside `app.core` is imported. It imports nothing itself. Its only content is a docstring that tells a human what the three files in the folder do.

### The whole file

```python
"""
core/ - Cross-cutting building blocks used by the whole application.

    config.py        -> settings read from environment variables / .env
    security.py      -> password hashing and JWT access tokens
    dependencies.py  -> reusable FastAPI dependencies (db session, current user)
"""
```

### Walkthrough, block by block

#### Block 1: the folder docstring (lines 1-7)

```python
"""
core/ - Cross-cutting building blocks used by the whole application.

    config.py        -> settings read from environment variables / .env
    security.py      -> password hashing and JWT access tokens
    dependencies.py  -> reusable FastAPI dependencies (db session, current user)
"""
```

- `"""` (three double quotes) - starts a string that may span many lines. When such a string is the very first thing in a file, Python stores it as the file's **docstring** (documentation string). You can read it later with `help(app.core)` or `app.core.__doc__`. It does nothing at run time.
- `core/` - the folder name, with a slash to show it is a folder, not a file.
- `-` - just a dash separating the name from the description.
- `Cross-cutting building blocks used by the whole application.` - "cross-cutting" means "used by many different parts". The routers, the database code and `main.py` all need settings, security and dependencies, so those three live together in one folder called `core`.
- `config.py -> settings read from environment variables / .env` - one line per file in the folder. `->` is just an arrow drawn with characters (a dash and a greater-than sign) meaning "is for". This line is what this document explains.
- `security.py -> password hashing and JWT access tokens` - the second file (explained in doc 04).
- `dependencies.py -> reusable FastAPI dependencies (db session, current user)` - the third file (also doc 04).
- the closing `"""` - ends the docstring.

**Why it is here:** two reasons. First, the file must exist for `app.core` to be importable (see "What this file is for"). Second, the docstring is a map: when you open the folder in six months, you know in five seconds what each file does without opening it.

**If you removed or changed it:**

- If you deleted the whole file: in modern Python (3.3 and later) a folder without `__init__.py` can still be imported as a "namespace package", so `from app.core.config import settings` would *probably* still work. But many tools (linters, packaging tools, some test runners) treat a folder without `__init__.py` as "not part of the project", and it breaks the convention every other folder in this project follows. Keep it.
- If you deleted only the docstring and left an empty file: nothing changes at run time. You would only lose the map for humans.
- If you wrote real code here (for example `from app.core.config import settings`): that code would run every time anything in `app.core` is imported. This is allowed but easy to get wrong (circular imports), so this project keeps every `__init__.py` to a docstring only.

### Compared to your old code

Your old project had `app/__init__.py` as an empty file (0 bytes) and no `core` folder at all: `config.py`, `oauth2.py`, `utils.py` and `database.py` sat directly in `app/`.

```python
# old project: app/__init__.py
# (empty file)
```

Nothing was wrong with that. An empty `__init__.py` does its job. Two things changed in the new project:

1. **A `core/` subfolder exists.** As a project grows, a flat `app/` folder with ten files becomes hard to read. The new project groups files by job: `core/` (settings, security, dependencies), `database/`, `models/`, `schemas/`, `routers/`. Each group needs its own `__init__.py`.
2. **The `__init__.py` has a docstring.** It costs nothing and explains the folder.

### Key terms in this file

| Term | Meaning |
| --- | --- |
| package | A folder that Python can import from, because it contains `__init__.py`. |
| `__init__.py` | The file that marks a folder as a package. Runs once, automatically, on first import. |
| docstring | A `"""..."""` string at the top of a file, class or function. Documentation, not code. |
| cross-cutting | Used by many different parts of the program. |
| namespace package | A folder without `__init__.py` that Python can still import from (since 3.3). Not used in this project. |

---

## File: app/core/config.py

### What this file is for

This file defines **one class, `Settings`, and one object, `settings`**. The object holds every value the application needs that is different from machine to machine or must stay secret: where the database is, what the password is, which secret key signs the login tokens, which frontend URLs may call the API. None of these values are written in the code. They are read from environment variables and from the `.env` file the moment `settings = Settings()` runs.

It imports two things: `BaseSettings` and `SettingsConfigDict` from the `pydantic-settings` library (to read and check the values), and `URL` from SQLAlchemy (to build a safe database connection string).

Who imports it (every one of them writes `from app.core.config import settings`):

| File | What it uses |
| --- | --- |
| `app/main.py` | `settings.APP_NAME`, `settings.APP_VERSION`, `settings.cors_allowed_origins_list`, `settings.API_V1_PREFIX` |
| `app/database/session.py` | `settings.database_url` (to create the engine) |
| `app/core/security.py` | `settings.SECRET_KEY`, `settings.ALGORITHM`, `settings.ACCESS_TOKEN_EXPIRE_MINUTES` |
| `app/core/dependencies.py` | `settings.API_V1_PREFIX` (for the login URL in `OAuth2PasswordBearer`) |
| `alembic/env.py` | `settings.database_url` (so migrations use the same database) |

Because `settings = Settings()` runs at import time, **the first `import` of this file is the moment the whole app checks its configuration**. If something required is missing, the app refuses to start, with a clear error, before any request is served.

### The whole file

```python
"""
Application settings.

Every value is read from an environment variable, falling back to the `.env`
file in the project root. Import the ready-made `settings` object anywhere:

    from app.core.config import settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown keys in .env instead of crashing
    )

    # --- General ---
    APP_NAME: str = "Expense Tracker API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # --- Database (PostgreSQL) ---
    DATABASE_HOSTNAME: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "expense_tracker"
    DATABASE_USERNAME: str = "postgres"
    DATABASE_PASSWORD: str = ""
    # Optional full connection URL. When set it wins over the parts above.
    # Hosting providers (Render, Railway, Heroku...) usually give you this.
    DATABASE_URL: str | None = None

    # --- JWT authentication ---
    SECRET_KEY: str  # required: no default so the app refuses to start without it
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS ---
    # Comma-separated list of frontend origins allowed to call this API,
    # e.g. "http://localhost:3000,http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = ""

    @property
    def database_url(self) -> str:
        """Connection URL that SQLAlchemy and Alembic use."""
        if self.DATABASE_URL:
            # Some providers still hand out the old "postgres://" scheme,
            # which SQLAlchemy no longer accepts.
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)

        # URL.create() safely escapes special characters (@, :, /) in the password.
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DATABASE_USERNAME,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOSTNAME,
            port=self.DATABASE_PORT,
            database=self.DATABASE_NAME,
        ).render_as_string(hide_password=False)

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        """CORS_ALLOWED_ORIGINS split into a clean list."""
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
```

### Walkthrough, block by block

#### Block 1: the module docstring (lines 1-8)

```python
"""
Application settings.

Every value is read from an environment variable, falling back to the `.env`
file in the project root. Import the ready-made `settings` object anywhere:

    from app.core.config import settings
"""
```

- `"""` - opens a multi-line string. Because it is the first statement in the file, it is the file's docstring (see Block 1 of `__init__.py`).
- `Application settings.` - a one-line title for the file.
- `Every value is read from an environment variable, falling back to the` `.env` `file in the project root.` - the rule of the file in one sentence. "Falling back to" means "if the environment variable is not set, look in `.env` instead". The exact order is explained in Block 5.
- `Import the ready-made` `settings` `object anywhere:` - tells you that you should never write `Settings()` yourself in other files. One object is created at the bottom of this file and everybody shares it.
- `from app.core.config import settings` - the copy-paste line to use. It is indented inside the docstring only so it looks like code; it is not executed here.
- the closing `"""` - ends the docstring.

**Why it is here:** so that anyone opening the file knows in ten seconds what it does and how to use it.

**If you removed or changed it:** nothing changes at run time. Docstrings are never executed. You would only lose the explanation.

#### Block 2: importing from pydantic-settings (line 10)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
```

- `from` - Python keyword: "take something out of a module".
- `pydantic_settings` - the module name of the library `pydantic-settings` (pip name with a dash, import name with an underscore - this is common in Python). It is listed in `requirements.txt` as `pydantic-settings==2.15.0`. It is a small library built on top of pydantic.
- `import` - Python keyword: "bring this name into the current file".
- `BaseSettings` - a class. It is a subclass of pydantic's `BaseModel` (the same `BaseModel` you use for schemas). The difference: when you create a `BaseModel` you must pass the values yourself (`UserCreate(email=..., password=...)`), but when you create a `BaseSettings` with no arguments (`Settings()`), it goes and *finds* the values itself in environment variables and the `.env` file. Our `Settings` class inherits from it (Block 4).
- `,` - separates the two names being imported.
- `SettingsConfigDict` - a special dictionary type used to configure how `BaseSettings` finds its values. Explained in full in Block 5.

**Why it is here:** without `BaseSettings` there is no automatic reading of environment variables; without `SettingsConfigDict` there is no `.env` support and no way to say "ignore unknown keys".

**If you removed or changed it:** `NameError: name 'BaseSettings' is not defined` on line 14, the moment any file imports `settings`. The whole app fails to start.

#### Block 3: importing URL from SQLAlchemy (line 11)

```python
from sqlalchemy.engine import URL
```

- `from sqlalchemy.engine import` - take a name out of the `engine` sub-module of SQLAlchemy. `sqlalchemy` is the ORM library you already use (`create_engine`, `sessionmaker`, `db.query`). `sqlalchemy.engine` is the part of it that deals with connecting to databases.
- `URL` - a class that represents a database connection address **as separate pieces** (driver name, username, password, host, port, database name) instead of one long string. It has a method `URL.create(...)` to build it from the pieces and a method `.render_as_string(...)` to turn it into the string `create_engine` wants. Both are used in Block 13.

**Why it is here:** your old project built the connection string with an f-string. That breaks when the password contains characters like `@`, `:` or `/`. `URL.create` knows how to escape those characters, so the password can be anything.

**If you removed or changed it:** `NameError: name 'URL' is not defined`, but only when `settings.database_url` is first read (which is when `app/database/session.py` is imported, which is at app start). Note: this `URL` must not be confused with the `HttpUrl` type from pydantic; they are unrelated.

#### Block 4: the Settings class (line 14)

```python
class Settings(BaseSettings):
```

- `class` - Python keyword: define a new class (a blueprint for objects).
- `Settings` - the name of our class. Capital S by convention for class names.
- `(BaseSettings)` - the parentheses after a class name list the **parent class** (also called base class). Our class *inherits* from `BaseSettings`: it gets everything `BaseSettings` can do (read environment variables, check types, report errors) and adds its own list of fields.
- `:` - starts the indented class body. Everything indented below belongs to `Settings`.

**Why it is here:** this is the container for every setting. Because it inherits from `BaseSettings`, writing `Settings()` later (Block 16) triggers the reading of environment variables and `.env`.

**If you removed or changed it:**

- If you wrote `class Settings(BaseModel):` (pydantic's normal model) instead: `Settings()` would raise `ValidationError: SECRET_KEY Field required` *even if* `SECRET_KEY` is set in the environment, because `BaseModel` never looks at environment variables. It only takes values you pass by hand.
- If you wrote `class Settings:` with no parent: the type annotations below would be plain Python annotations with no checking, no reading of `.env`, and `self.DATABASE_PORT` would be whatever text you typed, never converted.

#### Block 5: model_config = SettingsConfigDict(...) (lines 15-19)

```python
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown keys in .env instead of crashing
    )
```

This is the block you said you did not understand. Read it slowly. We will go through it four times: what `model_config` is, what `SettingsConfigDict` is, each option one by one, and finally what the old `class Config:` style was and why this replaces it.

##### 5a. What `model_config` is

`model_config` is a **class attribute**: a variable that belongs to the class itself, written directly in the class body, not inside a method and not with `self.`.

pydantic looks for an attribute with **exactly this name** when it builds a model class. It is pydantic's way of letting you pass *options*: not "which fields exist" (those are the `NAME: type` lines) but "how should this model behave". Think of it as the settings *of the settings class*.

You have already used it once without noticing. In your old `app/schema.py`:

```python
model_config = ConfigDict(from_attributes=True)
```

That line told pydantic "allow building this schema from an ORM object". Same mechanism, different options. `ConfigDict` is for normal pydantic models, `SettingsConfigDict` is the version for `BaseSettings` with a few extra options added.

Three facts about `model_config`:

1. The name is fixed. If you call it `config` or `settings_config`, pydantic ignores it and nothing you wrote there takes effect.
2. It must be written in the class body, before or after the fields; position does not matter.
3. It is not a field. `Settings.model_fields` lists the 13 settings (I checked: `APP_NAME` ... `CORS_ALLOWED_ORIGINS`), and `model_config` is not among them. It is metadata.

##### 5b. What `SettingsConfigDict` is

`SettingsConfigDict` is a **typed dictionary** (`TypedDict` in Python). A typed dictionary is a normal `dict`, but with a written list of which keys are allowed and what type each value must have. Calling it is like calling `dict(...)`:

```python
SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
# produces exactly this plain dict:
{"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
```

I ran `type(SettingsConfigDict(env_file=".env"))` in the project's Python and it printed `<class 'dict'>`. So at run time it is just a dictionary.

Why not write a plain `{...}` dictionary then? Because of the "typed" part. Your editor and type checker know the allowed keys. If you type `env_fil=".env"` (typo), the editor underlines it immediately. With a plain dict you would only find out when the `.env` file was silently ignored. The typed dict is a spell checker for option names.

Where do the allowed keys come from? In the library source (`pydantic_settings/main.py`) the class is defined as `class SettingsConfigDict(ConfigDict, total=False):`. Two things to read there:

- `(ConfigDict, ...)` - it inherits every key of pydantic's normal `ConfigDict` (`extra`, `from_attributes`, `frozen`, `str_strip_whitespace`, and so on) and adds the settings-only keys: `env_file`, `env_file_encoding`, `env_prefix`, `case_sensitive`, `secrets_dir`, `env_nested_delimiter`, and more.
- `total=False` - every key is optional. You only write the ones you want to change. Everything you leave out keeps its default.

##### 5c. Each option, word by word

- `model_config` - the fixed attribute name pydantic reads (5a).
- `=` - assignment: store the dictionary on the right under this name.
- `SettingsConfigDict(` - call the typed dict with keyword arguments (5b). The opening parenthesis starts the argument list; the matching `)` on line 19 closes it.
- `env_file=".env"` - key `env_file`, value the string `".env"`. This tells `BaseSettings`: "besides the real environment variables, also open the file at this path and read `NAME=value` lines from it". Three details that matter:
  - The path is **relative to the current working directory**: the folder your terminal was in when you ran `uvicorn app.main:app` or `alembic upgrade head`. It is *not* relative to `config.py`. I verified this: running the same class from a sub-folder makes `.env` not found. That is why the README tells you to run commands from the project root.
  - If the file does not exist, nothing happens. No error, no warning. The library checks `is_file()` and skips it silently. Your settings then come only from real environment variables and defaults. (This is exactly what happens on a hosting provider, where you set real environment variables and have no `.env` file.)
  - Trailing comma after the value: Python allows a comma after the last argument. It makes adding a new line later a one-line change in git. Every line in this call ends with a comma for that reason.
- `env_file_encoding="utf-8"` - key `env_file_encoding`, value `"utf-8"`. An encoding is the rule for turning the bytes on disk into text characters. UTF-8 is the worldwide standard and the one every modern editor uses. The `.env` file is opened with this encoding. Honest note: in the version installed here (pydantic-settings 2.15.0) the library itself already falls back to `'utf8'` when this key is missing (I read the line `dotenv_values(file_path, encoding=encoding or 'utf8')` in the source). So this line does not change behaviour today. It is here to say the expectation out loud and to protect against a future version or a machine with an unusual default. On this Windows machine Python's own default encoding is `cp1252`, not UTF-8, so being explicit is a reasonable habit.
- `extra="ignore"` - key `extra`, value `"ignore"`. "Extra" means a key that is present in the input but has no matching field in the class. For `BaseSettings`, the input that can have extra keys is the `.env` file. (Real environment variables are never a problem: the library only *looks up* the names of declared fields, it never scans `PATH`, `TEMP` and the other hundred variables on your machine.) Three possible values:
  - `"ignore"` - unknown `.env` keys are dropped quietly. **This is what the file chooses.**
  - `"forbid"` - unknown `.env` keys are an error. **This is the default for `BaseSettings`** (I checked: `BaseSettings.model_config.get("extra")` prints `'forbid'`). Note this is different from a normal `BaseModel`, where the default is `"ignore"`.
  - `"allow"` - unknown keys are kept and become attributes on the object.
- `# ignore unknown keys in .env instead of crashing` - a comment (everything after `#` on a line is ignored by Python) that says why `"ignore"` was chosen. The next bullet shows the crash it refers to.
- `)` - closes the `SettingsConfigDict(` call.

What the crash looks like. I added one line `UNKNOWN_KEY=hello` to a `.env` and built a class **without** `extra="ignore"`:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
unknown_key
  Extra inputs are not permitted [type=extra_forbidden, input_value='hello', input_type=str]
```

So with the default, a teammate adding `MY_NOTE=something` to their `.env`, or an old key you removed from the class but forgot to delete from the file, would stop the whole app from starting. With `extra="ignore"` the stray key is simply skipped.

##### 5d. The order: where does a value come from?

When `Settings()` runs, pydantic-settings asks several **sources** for each field, in a fixed order, and **the first source that has the value wins**. The order is written in the library's `settings_customise_sources` method, which returns:

```python
return init_settings, env_settings, dotenv_settings, file_secret_settings
```

In plain words, for every field:

1. **`init_settings`** - a value you passed by hand, like `Settings(SECRET_KEY="abc")`. This project never does that, so skip it.
2. **`env_settings`** - a real environment variable with the field's name.
3. **`dotenv_settings`** - a line in the `.env` file.
4. **`file_secret_settings`** - a file in a "secrets directory" (used by Docker secrets). Not configured here (`secrets_dir` is not set), so it is always empty.
5. If none of them has it: **the default** written in the class (`= 5432`, `= "localhost"`, ...).
6. If there is no default either: **error** `Field required` (Block 9).

I verified 2 and 3 with a tiny experiment: `.env` said `DATABASE_PORT=1111`, no environment variable set, result `1111`. Then I set the environment variable `DATABASE_PORT=2222` and ran again: result `2222`. The environment variable beats the file. That is the whole point: on your laptop you keep values in `.env`; on a server you set real environment variables and they win, with no code change.

One more detail: names are matched **case-insensitively** by default (`case_sensitive` is `False`). A line `secret_key=abc` in `.env` fills the field `SECRET_KEY`. I checked this too. Spaces around `=` are also fine: `SECRET_KEY = abc` works, which is why your old `.env` (which had `SECRET_KEY =...` with a space) worked.

##### 5e. How this replaces the old `class Config:` style

Your old `config.py` wrote the same idea like this:

```python
    class Config:
        env_file = ".env"
```

This is the **pydantic version 1** way: a nested class named `Config` whose attributes are the options. pydantic 2 still accepts it, but it is officially deprecated. I ran the old style with the installed pydantic and it printed this warning:

```
Support for class-based `config` is deprecated, use ConfigDict instead.
Deprecated in Pydantic V2.0 to be removed in V3.
```

"Removed in V3" means that when pydantic 3 comes out, the old style will stop working entirely. The two forms map one to one:

| Old (`class Config`) | New (`model_config`) |
| --- | --- |
| `class Config:` | `model_config = SettingsConfigDict(` |
| `    env_file = ".env"` | `    env_file=".env",` |
| `    extra = "ignore"` | `    extra="ignore",` |
| (nothing) | `)` |

Same option names, same values. The new form is a dictionary call instead of a nested class, gets editor autocomplete for the keys, and will keep working in pydantic 3.

**Why it is here:** three concrete benefits for this project. (1) `env_file=".env"` lets you keep your database password and secret key in a file that is not committed, instead of typing eight `set` commands before each run. (2) `extra="ignore"` means a stray or old key in `.env` cannot stop the app. (3) `env_file_encoding="utf-8"` makes the file's encoding explicit.

**If you removed or changed it:**

- Remove the whole block: `.env` is no longer read. On your laptop, unless you have set real environment variables, `Settings()` fails with `SECRET_KEY Field required` and the app does not start; even if `SECRET_KEY` happened to be set, the database values would fall back to the defaults (`localhost`, port `5432`, empty password), so the first query would fail with a PostgreSQL authentication error.
- Remove only `extra="ignore"`: the default `"forbid"` applies. Any key in `.env` that is not a field of `Settings` (a typo, an old key, a teammate's note) raises `ValidationError: Extra inputs are not permitted` at start.
- Rename `model_config` to anything else: pydantic does not see it. Same effect as removing the whole block.
- Change `env_file` to `"config/.env"`: pydantic-settings would look for that path instead; the existing `.env` in the project root would be silently ignored.

#### Block 6: general settings (lines 21-24)

```python
    # --- General ---
    APP_NAME: str = "Expense Tracker API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
```

Before the words, the shape. Every field in this class follows one pattern:

```
NAME: type = default
```

- `NAME` is the field name. It is also the environment variable name pydantic-settings looks for (upper case by convention, because environment variables are traditionally upper case).
- `:` followed by `type` is a **type annotation**. In plain Python an annotation is only a note. In pydantic it is an instruction: "check that the value is this type, and convert it if you can". Block 7 shows the conversion.
- `= default` is the value used when no source provides one (5d, step 5). A field without `= default` is **required** (Block 9).

Now the lines:

- `# --- General ---` - a comment used as a section heading, so the eye can find the group. The dashes are decoration.
- `APP_NAME` - field name. `: str` - must be text. `= "Expense Tracker API"` - default text. `app/main.py` passes it to `FastAPI(title=settings.APP_NAME)`, so this is the title shown at the top of the `/docs` page.
- `APP_VERSION` - `: str = "1.0.0"`. Shown next to the title on `/docs` (`FastAPI(version=settings.APP_VERSION)`). A string, not a number, because `"1.0.0"` has two dots and is not a valid number.
- `API_V1_PREFIX` - `: str = "/api/v1"`. Every router except `/health` is mounted with `prefix=settings.API_V1_PREFIX` in `main.py`, so the login endpoint is `/api/v1/auth/login`, categories are `/api/v1/categories`, and so on. `dependencies.py` also uses it to build the `tokenUrl` for the Swagger "Authorize" button. One place to change if you ever release `/api/v2`.

**Why it is here:** these three values appear in more than one file. Keeping them as settings means one definition, and the option to override them from the environment (for example a staging server could set `APP_NAME="Expense Tracker API (staging)"`) without touching code.

**If you removed or changed it:** removing any of the three gives `AttributeError: 'Settings' object has no attribute 'APP_NAME'` (or the other name) when `main.py` or `dependencies.py` is imported, so the app fails at start. Changing `API_V1_PREFIX` to `"/v1"` would move every endpoint: `/api/v1/auth/login` would become `/v1/auth/login`, and the Swagger "Authorize" button would follow automatically because `dependencies.py` reads the same setting.

#### Block 7: database connection parts (lines 26-31)

```python
    # --- Database (PostgreSQL) ---
    DATABASE_HOSTNAME: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "expense_tracker"
    DATABASE_USERNAME: str = "postgres"
    DATABASE_PASSWORD: str = ""
```

- `# --- Database (PostgreSQL) ---` - section heading comment.
- `DATABASE_HOSTNAME: str = "localhost"` - the machine where PostgreSQL runs. `"localhost"` means "this same computer". On a hosting provider you would set it to their database address.
- `DATABASE_PORT: int = 5432` - the network port PostgreSQL listens on. `5432` is PostgreSQL's standard port. **`: int` is the important part, read the paragraph below.**
- `DATABASE_NAME: str = "expense_tracker"` - the name of the database inside the PostgreSQL server (one server can hold many databases).
- `DATABASE_USERNAME: str = "postgres"` - the PostgreSQL user to log in as. `postgres` is the superuser created by the installer.
- `DATABASE_PASSWORD: str = ""` - that user's password. The default is an **empty string** (two quotes with nothing between). An empty default means "if you do not set it, try with no password", which only works on machines where PostgreSQL is configured to trust local connections. In practice you always set it in `.env`.

**About `DATABASE_PORT: int` and type conversion.** Environment variables and `.env` lines are always *text*. `DATABASE_PORT=5432` in `.env` gives the string `"5432"` (four characters), not the number 5432. Because the field is annotated `: int`, pydantic **converts** the text to a real integer before storing it. I checked: with `DATABASE_PORT=5432` in the environment, `settings.DATABASE_PORT` is `5432` and `type(...)` is `<class 'int'>`. The conversion is also a check. If someone writes `DATABASE_PORT=abc`, the app refuses to start with:

```
DATABASE_PORT
  Input should be a valid integer, unable to parse string as an integer
  [type=int_parsing, input_value='abc', input_type=str]
```

This matters because `URL.create(port=...)` in Block 13 expects an `int`, and so does the database driver. Your old `config.py` declared `DATABASE_PORT: str`, which would have handed a string to code expecting a number, except that the old `database.py` never used the port at all (see "Compared to your old code").

**Why it is here:** these five values together describe one PostgreSQL connection. Keeping them as separate fields (instead of one long URL) makes `.env` easy to read and edit, and lets the code build a correctly escaped URL (Block 13).

**If you removed or changed it:**

- Remove any of the five: `AttributeError` inside the `database_url` property, raised when `app/database/session.py` creates the engine, so at app start.
- Change `DATABASE_PORT: int` to `DATABASE_PORT: str`: the value stays text. `URL.create(port="5432")` is typed to receive an `int`; passing a string is not what the function promises to accept. I am not 100% sure every driver would reject it, but it is the kind of silent mismatch that produces confusing errors later. Keep `int`.
- Change the default `DATABASE_PASSWORD` to a real password: it would be committed to git for everyone to see. Defaults must never contain secrets. That is also why `SECRET_KEY` has no default at all (Block 9).

#### Block 8: optional full database URL (lines 32-34)

```python
    # Optional full connection URL. When set it wins over the parts above.
    # Hosting providers (Render, Railway, Heroku...) usually give you this.
    DATABASE_URL: str | None = None
```

- `# Optional full connection URL. When set it wins over the parts above.` - comment: this field is an alternative to the five parts in Block 7. "Wins over" means: if this one is set, the five parts are ignored. The `database_url` property in Block 12 implements that rule.
- `# Hosting providers (Render, Railway, Heroku...) usually give you this.` - comment: the reason the field exists. Cloud hosts typically hand you one line like `postgresql://user:pass@host:5432/dbname` as a single environment variable named `DATABASE_URL`, rather than five separate values.
- `DATABASE_URL` - field name. Note the upper case: this is the *field*, holding raw text from the environment. The lower-case `database_url` in Block 11 is the *property* that computes the final answer. Two different things with similar names; keep them apart in your head.
- `:` - starts the type annotation.
- `str | None` - read this as "a `str`, **or** `None`". The vertical bar `|` between two types means "either of these". This is the modern Python (3.10 and newer) spelling of what older code wrote as `Optional[str]` from the `typing` module. Both mean the same. `None` is Python's special value for "nothing / not set".
- `= None` - the default is `None`, meaning "not provided". Because there is a default, this field is optional: the app starts fine without it.

A small but real edge case I checked: if `.env` contains the line `DATABASE_URL=` with nothing after the `=`, the field becomes the empty string `""`, not `None`. The property in Block 12 handles this correctly because it tests `if self.DATABASE_URL:` (truthiness) rather than `if self.DATABASE_URL is not None:`. An empty string counts as false, so the five parts are used.

**Why it is here:** so the same code runs on your laptop (five parts in `.env`) and on a cloud host (one `DATABASE_URL` variable) with zero code changes.

**If you removed or changed it:**

- Remove the field: `AttributeError: 'Settings' object has no attribute 'DATABASE_URL'` inside the property, at app start.
- Change `str | None = None` to `str` (required): the app would refuse to start on your laptop unless you also provide a full URL, defeating the purpose of the five parts.
- Change `str | None = None` to `str = ""`: works the same in practice (empty string is also false), but `None` says "not set" more clearly than "empty text".

#### Block 9: JWT settings and the one required field (lines 36-39)

```python
    # --- JWT authentication ---
    SECRET_KEY: str  # required: no default so the app refuses to start without it
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
```

- `# --- JWT authentication ---` - section heading. JWT (JSON Web Token) is the signed token your login endpoint returns and the client sends back on every request. `security.py` creates and checks it; this block holds the three values it needs.
- `SECRET_KEY: str` - field name and type, and **no `= default`**. This makes it a **required field**: pydantic must find a value in a source (environment variable or `.env`) or it raises an error. It is the only required field in the class (I checked with `Settings.model_fields` and `is_required()`; the list is `['SECRET_KEY']`). The secret key is the password used to *sign* every token. Anyone who knows it can forge a token for any user, so it must be long, random and private.
- `# required: no default so the app refuses to start without it` - comment explaining exactly that. A default like `"changeme"` would be worse than an error: someone would forget to change it, deploy, and every token in production would be forgeable.
- `ALGORITHM: str = "HS256"` - the signing algorithm name. `HS256` means HMAC with SHA-256: a symmetric signature where the same secret both signs and verifies. `security.py` passes it to `jwt.encode(...)` and `jwt.decode(...)`.
- `ACCESS_TOKEN_EXPIRE_MINUTES: int = 60` - how long a token stays valid after login, in minutes. `security.py` computes `now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)` and stores it in the token's `exp` claim. `: int` so the text `"60"` from `.env` becomes the number 60, which `timedelta` needs.

What "required" looks like when it fails. I ran `Settings()` with no `SECRET_KEY` anywhere:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
SECRET_KEY
  Field required [type=missing, input_value={...}, input_type=dict]
```

This happens at the moment `settings = Settings()` runs (Block 16), which is during `import`, so `uvicorn` prints this traceback and exits. No request is ever served with a missing key.

**Why it is here:** these three values fully describe how tokens are made and checked. Making `SECRET_KEY` required is a safety feature: forgetting it is a loud startup error, not a silent security hole.

**If you removed or changed it:**

- Give `SECRET_KEY` a default: the app starts without configuration, and every deployment that forgets to set its own key signs tokens with a key that is visible on GitHub.
- Remove `SECRET_KEY` entirely: `AttributeError` in `security.py` the first time a user logs in or sends a token (`create_access_token` / `decode_access_token`).
- Change `ALGORITHM` to a value `python-jose` does not support (say `"XYZ"`): `jwt.encode` raises an error at the first login.
- Change `ACCESS_TOKEN_EXPIRE_MINUTES` to `0`: tokens expire immediately; every request after login returns `401 Unauthorized`.
- Change `SECRET_KEY` on a running server: every token issued before the change becomes invalid (signature no longer matches); all users must log in again. Sometimes that is exactly what you want (for example after a leak).

#### Block 10: CORS allowed origins (lines 41-44)

```python
    # --- CORS ---
    # Comma-separated list of frontend origins allowed to call this API,
    # e.g. "http://localhost:3000,http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = ""
```

- `# --- CORS ---` - section heading. CORS stands for Cross-Origin Resource Sharing. Browsers block JavaScript on one website (say `http://localhost:3000`, a React app) from calling an API on a different **origin** (say `http://localhost:8000`, this backend) unless the API explicitly says "that origin is allowed". An origin is scheme + host + port: `http://localhost:3000` and `http://localhost:5173` are two different origins.
- `# Comma-separated list of frontend origins allowed to call this API,` - comment: the value is one string containing several origins separated by commas.
- `# e.g. "http://localhost:3000,http://localhost:5173"` - example value. `3000` is the usual port for Create React App, `5173` for Vite.
- `CORS_ALLOWED_ORIGINS: str = ""` - field name, type text, default empty string (no origins allowed).

Why a plain `str` and not `list[str]`? Because environment variables are text. pydantic-settings *can* parse a `list[str]` field, but then it expects JSON in the variable (`["http://a","http://b"]`, with the brackets and quotes), which is awkward to type in a hosting dashboard. A comma-separated string is friendlier, and the property in Block 14 turns it into a proper list.

**Why it is here:** `main.py` passes `settings.cors_allowed_origins_list` to `CORSMiddleware(allow_origins=...)`. Without this setting, no browser frontend could call the API.

**If you removed or changed it:** removing the field breaks `main.py` at import (`AttributeError`). Leaving it empty is safe but means the API only works from tools like Swagger UI (same origin), Postman and `curl` (not browsers), never from a separate frontend. Setting it to `"*"` would tell every website on the internet that it may call this API from a visitor's browser. For an API with logins that is unsafe, so keep the list explicit.

#### Block 11: the database_url property header (lines 46-48)

```python
    @property
    def database_url(self) -> str:
        """Connection URL that SQLAlchemy and Alembic use."""
```

- `@` - the "at" sign starts a **decorator**. A decorator is a function that takes the function written right below it and wraps or changes it. You have used decorators before: `@router.get("/posts")` is one. The `@` line and the `def` line belong together.
- `property` - a built-in Python decorator. It turns a method into something that is **read like an attribute**. Without it you would write `settings.database_url()` (with parentheses, a call). With it you write `settings.database_url` (no parentheses), and Python silently calls the method for you and gives you its return value. Every time you read it, the method runs again (there is no caching), which is fine because the work is tiny.
- `def` - Python keyword: define a function. Inside a class, a function is called a **method**.
- `database_url` - the method name, in lower case. Compare with the field `DATABASE_URL` (upper case) in Block 8. The upper-case one is *raw input* from the environment; this lower-case one is the *final answer* the rest of the app uses.
- `(self)` - the parameter list. `self` is the object the method is called on (the `settings` object). Inside the method, `self.DATABASE_URL`, `self.DATABASE_PORT` and so on read that object's fields. Every normal method has `self` as its first parameter; Python fills it in for you.
- `->` - the arrow introduces the **return type annotation**: what kind of value the method gives back.
- `str` - the return type: a text string. This is a note for readers and editors; Python does not enforce it, but it tells you `create_engine` will receive a string.
- `:` - starts the method body.
- `"""Connection URL that SQLAlchemy and Alembic use."""` - the method's docstring. Says who consumes the value: `app/database/session.py` (SQLAlchemy engine) and `alembic/env.py` (migrations).

**Why it is a property and not a field.** Four reasons:

1. It is **computed** from other fields, not read from the environment. There is no `database_url=` line anyone needs to write in `.env`.
2. If it were a field, pydantic-settings would try to *fill* it from an environment variable, and because names are matched case-insensitively (5d), it would collide with the real `DATABASE_URL` field.
3. A property is not in `Settings.model_fields` (I checked: the list ends at `CORS_ALLOWED_ORIGINS`), so it is never validated as input and never shows up in `settings.model_dump()`.
4. It stays **always correct**. If the code ever changed a field after creation, the property would reflect the change on the next read, because it is recalculated each time.

**Why it is here:** two different files need the same connection string. Writing the logic once here means the API and the migrations can never disagree about which database they talk to.

**If you removed or changed it:**

- Remove `@property`: `settings.database_url` would be the method object itself, not a string. `create_engine(settings.database_url)` would fail with an error like `ArgumentError: Expected string or URL object, got <bound method ...>` at app start.
- Rename it: `AttributeError: 'Settings' object has no attribute 'database_url'` in `session.py` and `alembic/env.py`.
- Delete the docstring: no runtime change.

#### Block 12: use the full URL when it is given (lines 49-52)

```python
        if self.DATABASE_URL:
            # Some providers still hand out the old "postgres://" scheme,
            # which SQLAlchemy no longer accepts.
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
```

- `if` - Python keyword: run the indented block only when the condition is true.
- `self.DATABASE_URL` - the raw field from Block 8. Used directly as the condition. Python treats `None` and the empty string `""` as **false**, and any non-empty string as **true**. So this reads: "if a full URL was provided". This is why an empty `DATABASE_URL=` line in `.env` is harmless (Block 8).
- `:` - starts the block.
- `# Some providers still hand out the old "postgres://" scheme,` - comment. The **scheme** is the part before `://`. For years, Heroku and some others gave URLs starting with `postgres://`.
- `# which SQLAlchemy no longer accepts.` - comment. SQLAlchemy removed support for the short name `postgres` (it only knows `postgresql`). I confirmed with the installed version: `create_engine("postgres://u:p@h/d")` raises `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres`.
- `return` - Python keyword: stop here and hand back this value.
- `self.DATABASE_URL.replace(` - call the string method `replace` on the URL text. `replace` takes three arguments:
  - `"postgres://"` - the text to look for (old).
  - `"postgresql://"` - the text to put in its place (new).
  - `1` - the **count**: replace at most one occurrence. It prevents touching the same text if it somehow appeared again later in the URL (for example inside a database name). If the URL already starts with `postgresql://`, the text `postgres://` is not found (because `postgresql://` is not the same characters) and `replace` returns the string unchanged. I checked: `"postgres://u:p@h/d".replace("postgres://", "postgresql://", 1)` gives `"postgresql://u:p@h/d"`.
- `)` - closes the call.

**Why it is here:** so a `DATABASE_URL` copied straight from a hosting dashboard works, even if it uses the old scheme. Without the `replace`, deploying to such a host would crash at start with the `NoSuchModuleError` above, and the fix would need a code change.

**If you removed or changed it:**

- Remove the whole `if` block: `DATABASE_URL` is ignored and the five parts are always used. On a cloud host that gives only `DATABASE_URL`, the app would try `localhost:5432` with user `postgres` and an empty password, and fail to connect.
- Remove the `, 1`: behaviour is the same for every realistic URL (the scheme appears once). It is there as a precaution.
- Change `if self.DATABASE_URL:` to `if self.DATABASE_URL is not None:`: an empty `DATABASE_URL=` line in `.env` would now pass the test and `create_engine("")` would fail with `ArgumentError: Could not parse SQLAlchemy URL from given URL string` (I checked).

#### Block 13: build the URL from the five parts (lines 54-62)

```python
        # URL.create() safely escapes special characters (@, :, /) in the password.
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DATABASE_USERNAME,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOSTNAME,
            port=self.DATABASE_PORT,
            database=self.DATABASE_NAME,
        ).render_as_string(hide_password=False)
```

This code runs only when the `if` in Block 12 was false (no full URL), because that `if` would otherwise have already returned.

- `# URL.create() safely escapes special characters (@, :, /) in the password.` - comment stating the reason this is not an f-string. "Escapes" means "rewrites in a way that cannot be misread". Explained below.
- `return` - hand back the value of the whole expression that follows.
- `URL.create(` - `URL` is the class imported in Block 3. `.create` is a **class method** (called on the class, not on an object) that builds a `URL` object from named pieces. The pieces are passed as keyword arguments (`name=value`):
  - `drivername="postgresql+psycopg2"` - which database and which driver library. `postgresql` is the **dialect** (the flavour of SQL), `psycopg2` is the **driver** (the Python package that actually talks to the server; `psycopg2-binary` in `requirements.txt`). The `+` joins them. Your old code wrote only `postgresql://`, which makes SQLAlchemy pick its default driver for PostgreSQL, which is also psycopg2. The new code says it explicitly so that nobody has to guess.
  - `username=self.DATABASE_USERNAME` - the user, from Block 7.
  - `password=self.DATABASE_PASSWORD` - the password, exactly as typed, **not** escaped by you. The SQLAlchemy docstring says the password "should not be URL encoded when passed" because `URL.create` does the encoding itself.
  - `host=self.DATABASE_HOSTNAME` - the server address.
  - `port=self.DATABASE_PORT` - the port, an `int` thanks to Block 7.
  - `database=self.DATABASE_NAME` - the database name.
  - `,` after the last argument and `)` on its own line - same trailing-comma style as Block 5.
- `.render_as_string(hide_password=False)` - called directly on the `URL` object that `URL.create(...)` returned (this is called **method chaining**: the result of one call is immediately used for the next). `render_as_string` turns the object into the one-line text form. Its one parameter:
  - `hide_password` - defaults to `True`, which prints `***` instead of the password. That default exists so that logging a URL does not leak the password. Here we need the real thing, because this string will be given to `create_engine`, which must log in. So `hide_password=False`.

What escaping does, with real output from the project's Python. Suppose the password is `p@ss:w/ord#1` (it contains `@`, `:`, `/` and `#`).

```python
URL.create(drivername="postgresql+psycopg2", username="postgres",
           password="p@ss:w/ord#1", host="localhost", port=5432,
           database="expense_tracker").render_as_string(hide_password=False)
# 'postgresql+psycopg2://postgres:p%40ss%3Aw%2Ford%231@localhost:5432/expense_tracker'
```

Each special character became `%` plus two hex digits of its character code (`@` is 64, hex 40, so `%40`; `:` is `%3A`; `/` is `%2F`; `#` is `%23`). This is called **percent-encoding**. The database driver decodes it back to the real password before logging in. Now the only `@` in the string is the one that separates the password from the host, and the only `:` after the host is the one before the port, so nothing can be misread.

Compare the f-string approach from your old `database.py` with the same password:

```
postgresql://postgres:p@ss:w/ord#1@localhost/expense_tracker
```

There are now two `@` signs and SQLAlchemy cannot tell where the password ends. When I asked SQLAlchemy to parse that string it raised `ValueError: invalid literal for int() with base 10: 'w'`: it took `ss` as the host, tried to read `w/ord#1@localhost` as the port number, and failed. With a slightly different password it might not even fail; it could quietly try to connect to the wrong host. Your old password happened to be only digits, which is why you never hit this.

Two more outputs I checked, so you know what to expect:

- With the default `hide_password=True` (or just `str(url)`): `postgresql+psycopg2://postgres:***@localhost:5432/expense_tracker`. Handy for logs, useless for connecting.
- With the default empty password: `postgresql+psycopg2://postgres:@localhost:5432/expense_tracker`. The empty password is still rendered as `:` followed by nothing; the driver understands that as "no password".

**Why it is here:** this is the normal path on your laptop. It builds a correct connection string from the five `.env` values no matter what characters the password contains, and it names the driver explicitly.

**If you removed or changed it:**

- Replace it with an f-string: works until the first password with `@`, `:`, `/`, `#` or `%`, then connection errors that are very hard to debug.
- Remove `hide_password=False`: the URL contains `***` as the password. PostgreSQL answers `FATAL: password authentication failed for user "postgres"` at the first connection (which is at startup, in the `lifespan` function of `main.py`).
- Remove `port=self.DATABASE_PORT`: SQLAlchemy would leave the port out of the string and the driver would use its own default, 5432. Works for the default port only; `DATABASE_PORT` in `.env` would silently stop having any effect.
- Change `drivername` to `"postgresql"` only: still works (default driver is psycopg2). Change it to `"postgresql+asyncpg"`: `NoSuchModuleError`, because the async driver is not installed, and it would not work with the sync `Session` anyway.

#### Block 14: the CORS list property header (lines 64-66)

```python
    @property
    def cors_allowed_origins_list(self) -> list[str]:
        """CORS_ALLOWED_ORIGINS split into a clean list."""
```

- `@property` - as in Block 11: read like an attribute, computed on each read.
- `def cors_allowed_origins_list(self)` - a method named to say exactly what it returns: the allowed origins **as a list**. The field (Block 10) is upper case and holds one string; this is lower case and gives a list. `self` as always.
- `->` - return type annotation follows.
- `list[str]` - "a list whose items are strings". The square brackets after `list` specify the item type (this is called a **generic** type). Python 3.9 and newer allow `list[str]` directly; older code wrote `List[str]` from `typing`. `CORSMiddleware` in `main.py` expects a list of origin strings, so the type matches the consumer.
- `:` and the docstring `"""CORS_ALLOWED_ORIGINS split into a clean list."""` - "clean" means: no surrounding spaces, no empty items. Block 15 does the cleaning.

**Why it is here:** `main.py` needs a list; the environment gives a string. This property is the bridge, kept in the settings file so `main.py` stays simple.

**If you removed or changed it:** renaming or deleting the method makes `main.py` fail at import with `AttributeError`. If you removed only `@property`, `main.py` would pass the method object itself as `allow_origins`; the middleware immediately does `"*" in allow_origins` on it and crashes at import with `TypeError: argument of type 'method' is not a container or iterable` (I checked). Either way the app does not start.

#### Block 15: splitting the string into a list (lines 67-71)

```python
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]
```

This is a **list comprehension**: a compact way to build a list by looping. It is spread over several lines for readability, but it is one expression. Read it from the middle line outward.

- `self.CORS_ALLOWED_ORIGINS.split(",")` - start here. `split` is a string method that cuts the text at every comma and returns a list of the pieces. `"http://a:3000, http://b:5173 ,"` becomes `['http://a:3000', ' http://b:5173 ', '']`. Note the spaces and the empty last item.
- `for origin in ...` - loop over those pieces, calling each one `origin`.
- `if origin.strip()` - a **filter**: keep this piece only if `origin.strip()` is true. `strip()` removes spaces (and tabs, newlines) from both ends. An empty piece, or a piece that is only spaces, becomes `""`, which is false, so it is dropped.
- `origin.strip()` (the first line inside the brackets) - what goes **into** the result for each kept piece: the piece with its surrounding spaces removed.
- `[` and `]` - the square brackets make the whole thing a list.
- `return` - give back that list.

Written as a normal loop it would be:

```python
result = []
for origin in self.CORS_ALLOWED_ORIGINS.split(","):
    if origin.strip():
        result.append(origin.strip())
return result
```

Real results from the project's Python:

- `""` (the default) - `"".split(",")` gives `['']`, one empty piece; the filter drops it; result `[]`. So no origins allowed, and no crash.
- `"http://a:3000, http://b:5173 ,"` - result `['http://a:3000', 'http://b:5173']`. Spaces and the trailing comma are cleaned away.

**Why it is here:** people type `.env` values with spaces after commas or leave a trailing comma. Without the cleaning, `" http://b:5173"` (leading space) would not match the browser's `Origin` header and that frontend would be blocked, with no error anywhere to tell you why.

**If you removed or changed it:**

- Remove `if origin.strip()`: the default `""` would give `['']`, a list with one empty origin. Harmless in practice (no browser sends an empty origin) but untidy, and a trailing comma would also add an empty item.
- Remove the `.strip()` calls: `" http://b:5173"` with its space stays, the browser sends `http://b:5173` without the space, the two do not match, requests from that frontend are blocked.
- Replace `split(",")` with `split(";")`: the documented comma format in `.env.example` stops working; the whole string would be one single "origin" that matches nothing.

#### Block 16: the one shared settings object (line 74)

```python
settings = Settings()
```

- `settings` - a lower-case name for the **object** (an instance). Compare with `Settings` (capital S), the **class**. The class is the blueprint; this is the one house built from it.
- `=` - assignment.
- `Settings()` - calling the class creates an object. Because `Settings` inherits from `BaseSettings` (Block 4), this call does all the work described in 5d: read environment variables, read `.env`, apply defaults, convert types (`"5432"` to `5432`), and check that `SECRET_KEY` is present. If any check fails, the `ValidationError` is raised **here**.
- No indentation - this line is at the left margin, so it is **outside** the class, at module level. It runs once, the first time the file is imported.

Two consequences of "runs at import time":

1. `from app.core.config import settings` anywhere in the project triggers this line the first time, and every later import reuses the same object (Python caches imported modules). All files share one `settings`. That is what the module docstring (Block 1) meant by "the ready-made `settings` object".
2. Configuration errors appear at startup, in the terminal, as a traceback from this line. They never appear as a 500 error during a request. That is a feature: a server that cannot be configured should not pretend to be running.

**Why it is here:** so other files write `settings.SECRET_KEY` instead of each creating their own `Settings()` (which would re-read `.env` every time and could, in theory, disagree with each other).

**If you removed or changed it:**

- Remove the line: every `from app.core.config import settings` fails with `ImportError: cannot import name 'settings'`. Nothing starts.
- Write `settings = Settings` (no parentheses): `settings` is the class, not an object, and nothing is read from the environment. In pydantic 2, reading a field name on the class raises `AttributeError` (I checked: `Settings.APP_NAME` and `Settings.SECRET_KEY` both raise it, because the class holds field *definitions*, not values). The crash happens at startup, the moment `main.py` reads `settings.APP_NAME`.
- Create a second object elsewhere, `other = Settings()`: it would work and have the same values, but it is wasted work and a second place to get out of sync. Always import the shared one.

### Compared to your old code

Here is your old `app/config.py`, complete:

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

And the one line in your old `app/database.py` that used it:

```python
Database_URL = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}/{settings.DATABASE_NAME}"
```

The shape is the same: a `Settings(BaseSettings)` class with upper-case fields, `.env` support, and one `settings = Settings()` at the bottom. You had the right idea. Here is what changed, and why, one item at a time.

**1. `class Config:` became `model_config = SettingsConfigDict(...)`.**
Covered in detail in Block 5e. The old nested class is the pydantic 1 style; it still runs today but prints a deprecation warning and will be removed in pydantic 3. The new form is the pydantic 2 style with the same option names.

**2. The old version had no `extra="ignore"`.**
So it used the `BaseSettings` default, `"forbid"`. It worked for you only because your `.env` contained exactly the eight keys the class declared. The day you added a ninth line to `.env` for any reason, the app would have refused to start with `Extra inputs are not permitted`. The new version ignores unknown keys.

**3. `DATABASE_PASSWORD: int` was a bug waiting to happen.**
A password is text, but the old class declared it as a number. It worked because your password happened to be only digits, so pydantic converted `"2233"` to `2233` and the f-string turned it back into `"2233"`. Two ways it would have broken:

- Any password with a letter or symbol (`my_pass`, `p@ss1`) fails at start with `Input should be a valid integer`.
- A numeric password with a leading zero, say `0123`, silently becomes the integer `123`, and the f-string sends `123` to PostgreSQL. Wrong password, login refused, and nothing in the code tells you why.

The new version declares `DATABASE_PASSWORD: str = ""`. Text in, text out.

**4. `DATABASE_PORT: str` was declared as text and never used.**
Look at the old f-string: there is no port in it (`@{hostname}/{dbname}`). The old setting had no effect at all; the driver always used 5432. The new version declares it `int` and passes it to `URL.create(port=...)`, so it is converted, checked, and actually used.

**5. Everything was required; now only `SECRET_KEY` is.**
The old class had no defaults, so all eight values had to be present or the app would not start. The new class gives safe public defaults to everything that has one (`localhost`, `5432`, `HS256`, `60`...) and keeps **no** default only for `SECRET_KEY`, because a default secret would be a security hole. Fewer lines to type in `.env`, same safety.

**6. The connection URL moved out of `database.py` into a property here.**
The old f-string works until a password contains `@`, `:`, `/` or `#` (Block 13 shows the exact failure). The new `database_url` property uses `URL.create`, which escapes those characters, names the driver explicitly (`postgresql+psycopg2`), includes the port, and is shared by both the app and Alembic. To be fair, your old project shared it too: the old `alembic/env.py` did `from app.database import Database_URL` and injected it with `config.set_main_option("sqlalchemy.url", Database_URL)`. The difference is *where* it lives. Importing `app.database` to get a string also runs `create_engine(...)` as a side effect (that module creates the engine at import). Importing `app.core.config` only reads settings, which is a cleaner dependency for a migration script.

**7. New fields for new features.**
`APP_NAME`, `APP_VERSION`, `API_V1_PREFIX` (versioned routes and the `/docs` title), `DATABASE_URL` (one-variable cloud deploys), `CORS_ALLOWED_ORIGINS` (browser frontends). The old project did not have these features, so it did not need these settings.

**8. Small style points, not bugs.**
`SECRET_KEY : str` with a space before the colon works, but the Python style guide (PEP 8) writes `SECRET_KEY: str` with no space before the colon and one after, which is what the new file does. The old `.env` had `SECRET_KEY =` with a space before `=`, which python-dotenv tolerates (I checked), so that was fine too. The new file also adds a docstring and section comments, so the next reader does not need this document to understand it.

**9. How other files read the values.**
Your old `oauth2.py` copied the values into module constants at import: `SECRET_KEY = settings.SECRET_KEY`, `ALGORITHM = settings.ALGORITHM`. The new `security.py` reads `settings.SECRET_KEY` directly where it is needed. Both work; the new way has one less name to keep in sync and makes it obvious where each value comes from.

### Key terms in this file

| Term | Meaning |
| --- | --- |
| `BaseSettings` | pydantic-settings class. A pydantic model that fills its fields from environment variables and `.env` when created with no arguments. |
| `model_config` | The fixed attribute name pydantic reads for options. Not a field. |
| `SettingsConfigDict` | A typed dictionary of options for `BaseSettings`. At run time it is a plain `dict`; the typing gives editor checks. |
| `TypedDict` | A `dict` with a declared list of allowed keys and value types. |
| `env_file` | Option: path of the `.env` file to read, relative to the folder you run the command from. Missing file is silently skipped. |
| `env_file_encoding` | Option: how to decode the `.env` bytes. `"utf-8"` here; the library also defaults to utf8. |
| `extra` | Option: what to do with `.env` keys that have no field. `"ignore"` drops them, `"forbid"` (the `BaseSettings` default) raises an error. |
| source | One place pydantic-settings can take a value from: arguments, environment variables, `.env` file, secrets directory. First source with a value wins. |
| field | `NAME: type = default` inside the class. One setting. |
| required field | A field with no default (`SECRET_KEY: str`). Missing value raises `Field required`. |
| type conversion | pydantic turning the text `"5432"` into the integer `5432` because the field says `: int`. Fails loudly for `"abc"`. |
| `str \| None` | "a string, or `None`". Same as `Optional[str]`. |
| `None` | Python's "no value". Counts as false in an `if`. |
| `@property` | Decorator that makes a method readable like an attribute (`settings.database_url`, no parentheses). Recomputed on every read. |
| decorator | A line starting with `@` that wraps the function below it. |
| `self` | Inside a method, the object the method was called on. |
| `->` | Introduces the return type annotation of a function. |
| `list[str]` | A list whose items are strings. |
| list comprehension | `[expr for item in iterable if condition]`: build a list in one expression. |
| `str.split(",")` | Cut a string at every comma into a list of pieces. |
| `str.strip()` | Remove spaces from both ends of a string. |
| `str.replace(old, new, 1)` | Replace at most one occurrence of `old` with `new`. |
| truthiness | `if value:` treats `None`, `""`, `0`, `[]` as false and everything else as true. |
| `URL` (SQLAlchemy) | Object holding a database address as separate pieces. |
| `URL.create(...)` | Builds a `URL` from driver, username, password, host, port, database. Escapes special characters. |
| `render_as_string(hide_password=False)` | Turns the `URL` into text, with the real password instead of `***`. |
| percent-encoding | Writing a special character as `%` plus its hex code (`@` becomes `%40`) so it cannot be misread in a URL. |
| scheme | The part of a URL before `://`. `postgres://` is old and rejected; `postgresql://` is correct. |
| dialect + driver | `postgresql+psycopg2`: the SQL flavour and the Python package that talks to the server. |
| CORS | Browser rule that blocks a web page on one origin from calling an API on another unless the API allows it. |
| origin | Scheme + host + port, for example `http://localhost:3000`. |
| JWT | JSON Web Token: the signed login token. `SECRET_KEY` signs it, `ALGORITHM` says how, `ACCESS_TOKEN_EXPIRE_MINUTES` says for how long. |
| import time | The moment a file is first imported. `settings = Settings()` runs then, so configuration errors appear at startup. |

## Summary of this folder

`app/core/__init__.py` makes the `core` folder importable and lists what lives inside it. `app/core/config.py` defines the `Settings` class, whose upper-case fields are the application's settings, and creates the single shared `settings` object at import time. When that object is created, pydantic-settings fills each field from the first source that has it: a real environment variable first, then the `.env` file in the folder you ran the command from, then the default written in the class; a field with no default, which here is only `SECRET_KEY`, must be found or the app refuses to start. Text from the environment is converted to the declared type on the way in, so `DATABASE_PORT` is a real integer, and bad values fail loudly with a clear message. The `model_config = SettingsConfigDict(...)` line is where the `.env` behaviour is switched on and where unknown keys are told to be ignored instead of crashing the app. Two `@property` methods compute values the rest of the project needs but that are not themselves settings: `database_url` builds a correctly escaped connection string (or passes through a provider's `DATABASE_URL`, fixing the old `postgres://` scheme), and `cors_allowed_origins_list` turns a comma-separated string into a clean list. `main.py`, `session.py`, `security.py`, `dependencies.py` and `alembic/env.py` all import the same `settings` object, so there is exactly one place in the project where configuration is defined and checked.

