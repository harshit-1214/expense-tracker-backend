# app/core/security.py and app/core/dependencies.py

These two files are the "login machinery" of the project.

- `app/core/security.py` knows how to **hash a password**, **check a password**, **create a token** and **read a token**. It never touches the database and never touches FastAPI. It is pure Python plus two small libraries.
- `app/core/dependencies.py` is the glue between that machinery and FastAPI. It gives every router three ready-made "parameters": `DatabaseSession` (a database session), `CurrentUser` (the logged-in user, or a 401 error) and `DateRangeFilter` (the optional `?start_date=&end_date=` filter).

Everything below is explained word by word. Where I say "I checked this", I ran the real library code from the project's virtual environment and I am reporting what it did, not what I remember.

## The big picture: one login, start to finish

Before the line-by-line part, here is the story these two files tell together.

1. **Register.** The client sends an email and a password to `POST /api/v1/auth/register`. The router calls `hash_password(...)` from `security.py`. The *hash* (not the password) is saved in the `users.hashed_password` column.
2. **Login.** The client sends email and password to `POST /api/v1/auth/login`. The router loads the user, calls `verify_password(...)` to check the password against the stored hash, and if it matches calls `create_access_token(user.id)`. The token string is returned to the client.
3. **Every protected request.** The client sends the token back in a header: `Authorization: Bearer <token>`. In `dependencies.py`, `oauth2_scheme` reads that header, `decode_access_token(...)` checks the token and gives back the user id, `db.get(User, user_id)` loads the user, and the endpoint receives it as `current_user`. If any step fails the client gets `401 Unauthorized` and the endpoint never runs.

Keep this story in mind. Every line below serves one of these three steps.

## File: app/core/security.py

### What this file is for

This file has four small functions and one shared object. Two functions deal with passwords (`hash_password`, `verify_password`). Two deal with tokens (`create_access_token`, `decode_access_token`). The shared object `password_hasher` is the Argon2 hashing tool the two password functions use.

The file imports only `datetime` (standard library), `jose` (the `python-jose` library, for JWT tokens), `pwdlib` (the password-hashing library) and the project's `settings` object. It does **not** import anything from FastAPI or SQLAlchemy. That is on purpose: a file that does not know about web requests or databases is easy to test and easy to reuse.

Who imports it:

- `app/routers/auth.py` imports `hash_password`, `verify_password` and `create_access_token` (register and login).
- `app/core/dependencies.py` imports `decode_access_token` (reading the token on every protected request).

### The whole file

```python
"""
Security helpers: password hashing and JWT access tokens.

Nothing in this file talks to the database or to FastAPI, which keeps it
easy to test and reuse.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2id with safe default settings.
password_hasher = PasswordHash.recommended()


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Return a salted hash that is safe to store in the database."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login password against the stored hash."""
    return password_hasher.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
def create_access_token(user_id: int) -> str:
    """Create a signed JWT that identifies the user until it expires."""
    # Always use UTC: the "exp" claim is compared against UTC when decoding.
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),  # "sub" (subject) is the standard claim for the user
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """
    Return the user id stored in the token.

    Returns None when the token is invalid, tampered with, or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        return None
```

### Walkthrough, block by block

### Block 1: The module docstring

```python
"""
Security helpers: password hashing and JWT access tokens.

Nothing in this file talks to the database or to FastAPI, which keeps it
easy to test and reuse.
"""
```

**Word by word**

- `"""` ... `"""` - three double quotes start and end a *string that spans several lines*. When such a string is the very first thing in a file, Python stores it as the file's **docstring** (documentation string). It does nothing when the program runs; it is a note for humans and for tools (editors show it when you hover over the import).
- `Security helpers: password hashing and JWT access tokens.` - the one-line summary. "Helpers" means small reusable functions. "JWT" is explained in Block 11.
- `Nothing in this file talks to the database or to FastAPI ...` - tells you the design rule of this file: no database, no web framework. "Easy to test" means you can call these functions from a plain Python script. "Reuse" means another project could copy this file as-is.

**Why it is here.** A reader opening the file learns in two sentences what it does and what it deliberately does not do.

**If you removed or changed it.** Nothing breaks. The program runs exactly the same. You would only lose the explanation.

### Block 2: Importing date and time tools

```python
from datetime import datetime, timedelta, timezone
```

**Word by word**

- `from` - keyword. "Take something out of a module."
- `datetime` (the first one, after `from`) - the standard-library module that deals with dates and times. It comes with Python, nothing to install.
- `import` - keyword. "Bring these names into this file."
- `datetime` (the second one) - a **class** inside the `datetime` module with the same name as the module. One `datetime` object is one moment in time: year, month, day, hour, minute, second, microsecond, and optionally a time zone. We use `datetime.now(...)` to get "right now".
- `,` - separates the names in the list.
- `timedelta` - a class that represents a **length of time** ("60 minutes", "3 days"). You can add a `timedelta` to a `datetime` to get a later `datetime`. We use it for "now plus 60 minutes".
- `timezone` - a class for fixed time zones. We only use the ready-made constant `timezone.utc`, which means "UTC time, offset zero". UTC is explained in Block 12.

**Why it is here.** `create_access_token` needs to compute "when does this token stop working". That needs "now" (`datetime`), "plus N minutes" (`timedelta`) and "in UTC" (`timezone`).

**If you removed or changed it.** The file would fail to import with `NameError: name 'datetime' is not defined` the first time `create_access_token` runs. Because `dependencies.py` imports this file, and every router imports `dependencies.py`, the whole app would fail at startup.

### Block 3: Importing the JWT library

```python
from jose import JWTError, jwt
```

**Word by word**

- `jose` - the import name of the library listed in `requirements.txt` as `python-jose[cryptography]`. The name comes from "JOSE" = *JSON Object Signing and Encryption*, the family of standards that JWT belongs to. The `[cryptography]` part in requirements means "also install the `cryptography` package so that signing is done by a fast, well-reviewed implementation".
- `JWTError` - an **exception class** (a kind of error). The library raises it when a token is broken, has a bad signature, has expired, or has a bad claim. I checked `jose/exceptions.py`: `ExpiredSignatureError` and `JWTClaimsError` are both *subclasses* of `JWTError`, so catching `JWTError` catches those too. This matters in Block 18.
- `jwt` - a **module** inside the library (`jose/jwt.py`). It has the two functions we use: `jwt.encode(...)` to build a token and `jwt.decode(...)` to check and read one.

**Why it is here.** Without a JWT library we would have to write the base64 encoding, the JSON handling and the HMAC signing by hand. Getting any of that slightly wrong is a security hole.

**If you removed or changed it.** `create_access_token` and `decode_access_token` would fail with `NameError`. Login would return a 500 error, and every protected endpoint would also return 500 instead of 401.

### Block 4: Importing the password-hashing library

```python
from pwdlib import PasswordHash
```

**Word by word**

- `pwdlib` - the password-hashing library. In `requirements.txt` it is `pwdlib[argon2,bcrypt]`: the `[argon2,bcrypt]` part installs the two optional backends. This project uses Argon2; bcrypt is installed but unused.
- `PasswordHash` - a class from `pwdlib`. One `PasswordHash` object holds a list of "hashers" (algorithms) and knows how to `hash` and `verify`. I checked `pwdlib/__init__.py`: `PasswordHash` is the only name it exports.

**Why it is here.** It gives us a safe, modern password hasher in one line (Block 6).

**If you removed or changed it.** Block 6 would fail with `NameError` and the app would not start.

### Block 5: Importing the settings

```python
from app.core.config import settings
```

**Word by word**

- `app.core.config` - the project's own module `app/core/config.py` (explained in document 03). The dots mean "folder `app`, folder `core`, file `config.py`".
- `settings` - the single ready-made `Settings` object created at the bottom of that file. It has already read the `.env` file and the environment variables. We use three of its values here: `settings.SECRET_KEY`, `settings.ALGORITHM` and `settings.ACCESS_TOKEN_EXPIRE_MINUTES`.

**Why it is here.** The secret key must never be typed into source code (it would end up in Git). Reading it from `settings` keeps it in `.env`, which is ignored by Git.

**If you removed or changed it.** `create_access_token` would fail with `NameError: name 'settings' is not defined`. If you replaced it with a hard-coded secret, every copy of the repository (including public ones) would be able to forge valid tokens for your API.

### Block 6: Creating the password hasher

```python
# Argon2id with safe default settings.
password_hasher = PasswordHash.recommended()
```

**Word by word**

- `# Argon2id with safe default settings.` - a comment. It tells you which algorithm the next line picks and that its settings are safe defaults chosen by the library authors.
- `password_hasher` - a module-level variable (a name that exists for the whole file). It is created once when the file is imported and reused by every call to `hash_password` and `verify_password`.
- `=` - assignment. "Store the right-hand value under the left-hand name."
- `PasswordHash` - the class from Block 4.
- `.recommended` - a method of that class. The dot means "look inside `PasswordHash` for something called `recommended`". It is a *class method* (you call it on the class, not on an object).
- `()` - calls the method with no arguments. The return value is a new `PasswordHash` object.

I checked `pwdlib/_hash.py`: `recommended()` returns `PasswordHash((Argon2Hasher(),))`, that is, a hasher list with exactly one entry, Argon2. And `Argon2Hasher()` with no arguments uses the defaults of the underlying `argon2-cffi` library: `time_cost=3`, `memory_cost=65536` (kibibytes, so 64 MiB), `parallelism=4`, `hash_len=32`, `salt_len=16`, type `Argon2id`.

**What "hashing" means, in plain words.** A hash function takes any text and produces a fixed-size scrambled string. Going forward (password to hash) is easy. Going backward (hash to password) is designed to be practically impossible. So we store the hash, and when someone logs in we hash what they typed and see whether it leads to the same result.

**What "Argon2id" is.** Argon2 is a password hashing function that won the Password Hashing Competition in 2015. The "id" variant is the recommended one for passwords. It is deliberately **slow** and **memory-hungry** (the 64 MiB above): a legitimate login does one hash and barely notices, but an attacker trying billions of guesses pays 64 MiB and a few tens of milliseconds for every single guess. I timed `hash_password("abc")` on this machine: about 0.06 seconds. Fast enough for a login, far too slow for brute force.

**What a "salt" is.** Before hashing, the library generates 16 random bytes (the salt) and mixes them into the hash. Because of the salt, the same password hashed twice gives two different strings. I checked this:

```text
hash_password("secret123")  ->  $argon2id$v=19$m=65536,t=3,p=4$/CURuNvUtjUjocMsnxiNzQ$ODK4rO6LbsK2yNG4Gyl443fJczATYXCwu+8QTsWpK0I
hash_password("secret123")  ->  $argon2id$v=19$m=65536,t=3,p=4$YCAjdKjN2WSQX3mYFmgImg$HpNqkVJEhxv9RMUmYgOx3BJQdKZJ0DIYGkdI+jm+3KI
```

Read the stored string from left to right, split on `$`:

| Part | Meaning |
| --- | --- |
| `argon2id` | the algorithm name |
| `v=19` | Argon2 version |
| `m=65536,t=3,p=4` | memory (KiB), time cost (iterations), parallelism |
| `/CURuNvUtjUjocMsnxiNzQ` | the random salt, base64-encoded |
| `ODK4rO6L...` | the actual hash, base64-encoded |

The string is 97 characters long, which is why `users.hashed_password` is a `String(255)` column in `app/models/user.py`. Everything needed to re-check a password later (algorithm, settings, salt) is inside the string itself. That is why `verify` works without any extra stored data.

Why salt matters: without it, two users with the password `123456` would have identical hashes, and an attacker could precompute hashes of common passwords once and look them up ("rainbow tables"). With a different random salt per user, every hash has to be attacked separately.

**Why it is here.** One shared hasher object, created once. Creating it per call would work too, but there is no reason to.

**If you removed or changed it.** Both password functions would fail with `NameError`. If you replaced `recommended()` with a weaker algorithm such as plain SHA-256, hashing would become so fast that leaked hashes could be cracked by brute force in hours. If you changed the parameters (say `time_cost=1`), existing hashes would still verify (the parameters are read from the stored string), new ones would just be weaker.

### Block 7: Section banner "Passwords"

```python
# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
```

**Word by word**

- `# ----...` - a comment line made of dashes. Purely visual, a horizontal rule for humans.
- `# Passwords` - a comment naming the section that follows.

**Why it is here.** The file has two topics (passwords, tokens). The banners make the split visible when scrolling.

**If you removed or changed it.** Nothing changes at runtime. Comments are ignored by Python.

### Block 8: hash_password

```python
def hash_password(plain_password: str) -> str:
    """Return a salted hash that is safe to store in the database."""
    return password_hasher.hash(plain_password)
```

**Word by word**

- `def` - keyword that starts a function definition.
- `hash_password` - the function's name. Called by `app/routers/auth.py` during registration.
- `(` ... `)` - the parameter list.
- `plain_password` - the one parameter: the password exactly as the user typed it ("plain" = not hashed).
- `: str` - a **type hint**. The colon after a parameter name means "the type of this parameter is ...". `str` is Python's text type. Type hints do not change how Python runs the code; they document the intent and let editors and tools warn you if you pass the wrong thing.
- `-> str` - the **return type hint**. The arrow means "this function returns a ...". Here, a string (the hash).
- `:` at the end of the `def` line - starts the function body. Everything indented below belongs to the function.
- `"""Return a salted hash that is safe to store in the database."""` - the function's docstring. "Salted" refers to the random salt from Block 6. "Safe to store" means: even if the database leaks, the original passwords are not revealed.
- `return` - keyword. "Give this value back to whoever called the function and stop."
- `password_hasher` - the shared object from Block 6.
- `.hash` - its `hash` method. I checked `pwdlib/_hash.py`: it first checks that the argument is `str` or `bytes` (otherwise `TypeError`), then calls the Argon2 hasher's `hash`, which generates a fresh salt and returns the `$argon2id$...` string.
- `(plain_password)` - the argument passed to `hash`.

**Why it is here.** Registration must never store the password itself. This function is the only place in the project that turns a password into its stored form, so there is exactly one place to get it right.

**If you removed or changed it.** `app/routers/auth.py` would fail to import (`ImportError: cannot import name 'hash_password'`), so the app would not start. If you changed the body to `return plain_password`, the app would still run, but the database would hold readable passwords. Anyone with database access, or any backup, would then expose every user's password, including the ones they reuse on other sites.

### Block 9: verify_password

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login password against the stored hash."""
    return password_hasher.verify(plain_password, hashed_password)
```

**Word by word**

- `def verify_password(` - defines the function used by the login endpoint.
- `plain_password: str` - what the user typed in the login form.
- `,` - separates parameters.
- `hashed_password: str` - the `$argon2id$...` string loaded from the `users.hashed_password` column.
- `) -> bool:` - returns a boolean: `True` (password matches) or `False` (it does not).
- `"""Check a login password against the stored hash."""` - the docstring.
- `return password_hasher.verify(plain_password, hashed_password)` - calls the `verify` method with the two values and returns its answer.

I checked what `verify` does in `pwdlib/_hash.py` and `pwdlib/hashers/argon2.py`:

1. It checks both arguments are `str` or `bytes` (otherwise `TypeError`).
2. It asks each hasher in the list "do you recognise this hash string?" (`identify`). Argon2 recognises strings that start with `$argon2id$`, `$argon2i$` or `$argon2d$`.
3. If nobody recognises it, it raises `pwdlib.exceptions.UnknownHashError`. I confirmed: `verify_password("abc", "not-a-hash")` raises that error. In this project it cannot happen for a real user, because every `hashed_password` was produced by `hash_password`.
4. Otherwise it calls the Argon2 verify. That reads the salt and the parameters from the stored string, hashes the typed password with the same salt and parameters, and compares the result with the stored hash. A mismatch returns `False` (the library catches the "mismatch" exception for you). A match returns `True`.

I confirmed: `verify_password("secret123", h1)` is `True`, `verify_password("secret124", h1)` is `False`, and the second hash `h2` of the same password also verifies `True` even though the strings differ.

**Why "verify" and not `==`.** Two reasons.

- You cannot do `hash_password(typed) == stored`, because `hash_password` generates a *new random salt* each time, so the two strings will never be equal even for the right password. `verify` reuses the salt that is inside the stored string.
- You cannot do `typed == stored_password` either, because we do not store the password. We only store something that the password can be checked against. That is the whole point.

(One more detail: the library compares the two hash results in "constant time", meaning it takes the same time whether the first byte differs or the last one. A plain `==` stops at the first difference, and a patient attacker can measure that. You do not need to remember this; just know `verify` is the correct tool.)

**Why it is here.** It is the only way to check a password in the project, and it lives next to `hash_password` so the two always use the same hasher.

**If you removed or changed it.** `app/routers/auth.py` would fail to import. If you changed it to return `True` always, anyone could log in as anyone by knowing only an email.

### Block 10: Section banner "JWT access tokens"

```python
# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
```

**Word by word**

- `# ---...` - decorative comment lines.
- `# JWT access tokens` - names the second section. "Access token" is the thing the client sends on every request to prove who it is. "JWT" is the format of that token, explained in the next block.

**Why it is here.** Visual separation only.

**If you removed or changed it.** No runtime change.

### Block 11: create_access_token, the signature line and docstring

```python
def create_access_token(user_id: int) -> str:
    """Create a signed JWT that identifies the user until it expires."""
```

**Word by word**

- `def create_access_token(` - defines the function the login endpoint calls after the password check passed.
- `user_id: int` - the one parameter: the primary key of the logged-in user (`user.id`), an integer. Compare with your old code, which took a whole `data: dict`; the new version takes only what it needs.
- `) -> str:` - returns a string: the token.
- `"""Create a signed JWT that identifies the user until it expires."""` - the docstring. "Signed" means it carries a signature that proves we made it. "Identifies the user" means the user id is inside it. "Until it expires" means it carries an expiry time.

**What a JWT is.** JWT stands for *JSON Web Token*. It is a string with three parts separated by dots:

```text
header.payload.signature
```

Here is a real token produced by this function for user id 7 (I ran it):

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzkxMjkwNDA4fQ.UDouxB9YYjQImHUQLmHrKzizIifNz4ueJCSNJoYlaMM
```

Each part is **base64url** text. Base64 is just a way to write bytes using only letters, digits, `-` and `_`, so the token can travel safely inside an HTTP header. Base64 is **not** encryption. Anyone can decode the first two parts and read them. I decoded the token above:

- Header (part 1): `{"alg":"HS256","typ":"JWT"}` - "this is a JWT, signed with algorithm HS256".
- Payload (part 2): `{"sub":"7","exp":1791290408}` - the **claims**. A claim is one fact the token states. Here: subject is `"7"`, it expires at Unix time 1791290408 (seconds since 1 January 1970 UTC).
- Signature (part 3): 32 bytes computed as `HMAC-SHA256(part1 + "." + part2, SECRET_KEY)`.

**What the signature gives you.** HMAC is a keyed checksum. Only someone who knows `SECRET_KEY` can produce the right signature for a given header and payload. So:

- The server does **not** need to store tokens anywhere. When a token comes back, it recomputes the signature with the secret. If it matches, the server knows it issued this token and nobody changed it.
- If an attacker edits the payload (say changes `"sub":"7"` to `"sub":"1"`), the signature no longer matches and the token is rejected. I tested exactly this: `jose` raised `JWTError: Signature verification failed.`
- But the payload is readable by anyone. Never put secrets (passwords, card numbers) in a JWT. This project puts only the user id and the expiry.

The `HS256` in the header means "HMAC with SHA-256". It is *symmetric*: the same secret both creates and checks the signature. That is fine here because the same server does both jobs.

**Why it is here.** After a successful login the server must give the client something it can send back on later requests to prove "I am user 7". A signed token with an expiry does that without a sessions table in the database.

**If you removed or changed it.** `app/routers/auth.py` would fail to import. Without any token mechanism, every endpoint would be either open to everyone or usable by no one.

### Block 12: Computing the expiry time in UTC

```python
    # Always use UTC: the "exp" claim is compared against UTC when decoding.
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
```

**Word by word**

- `# Always use UTC: ...` - a comment that states the rule and the reason. The next paragraphs explain it.
- `expires_at` - a local variable holding the moment the token stops being valid.
- `=` - assignment.
- `datetime.now(timezone.utc)` - `datetime` is the class from Block 2, `.now` is its method "the current moment", and `timezone.utc` is the argument that says "give it to me in UTC, and attach the UTC time zone to it". The result is a *time-zone-aware* `datetime`.
- `+` - adds a length of time to a moment, giving a later moment.
- `timedelta(` ... `)` - builds a length of time (Block 2).
- `minutes=` - a keyword argument of `timedelta`: the length in minutes.
- `settings.ACCESS_TOKEN_EXPIRE_MINUTES` - the number from `.env`, default `60` in `config.py`.
- The expression spans three lines because it is inside parentheses; Python allows line breaks there.

**What UTC is.** UTC is the world's reference clock. Every time zone is UTC plus or minus some hours. India is UTC+5:30, so when it is 17:00 in India it is 11:30 UTC. A computer's "local time" is whatever time zone the machine is set to. Different machines (your laptop, a server in Frankfurt, a server in Virginia) have different local times but the same UTC time.

**Why `exp` must be UTC.** A JWT `exp` claim is defined by the standard as "seconds since 1970-01-01 00:00 UTC". I checked `jose/jwt.py`: when you pass a `datetime` as `exp`, `encode` converts it with `timegm(claims["exp"].utctimetuple())`. For an *aware* datetime (one with `tzinfo`), `utctimetuple()` first converts it to UTC, so the number is correct. For a *naive* datetime (no `tzinfo`), `utctimetuple()` cannot know the zone and simply **assumes the value is already UTC**. And when checking a token, `decode` compares `exp` with `datetime.now(UTC)`, always UTC.

**The bug in your old code.** `app/oauth2.py` did:

```python
expire = datetime.now() + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
```

`datetime.now()` with no argument returns naive **local** time. On this machine (India, UTC+5:30) I measured it:

```text
datetime.now()             -> 2026-10-06 17:10:31   (tzinfo = None)
datetime.now(timezone.utc) -> 2026-10-06 11:40:31   (tzinfo = UTC)
```

`jose` treated the 17:10 as if it were 17:10 UTC, which is 5 hours 30 minutes in the future. So an old-style token with `ACCESS_TOKEN_EXPIRE_MINUTES=60` was actually valid for **390 minutes** (6.5 hours), not 60. I confirmed by creating one and computing its real remaining time. On a machine *west* of UTC the bug flips: I simulated a UTC-5 machine and the freshly created 60-minute token was already **expired** (`ExpiredSignatureError: Signature has expired.`), so nobody could ever log in. It "worked" for you only because India is east of UTC, and even then with the wrong lifetime.

`datetime.now(timezone.utc)` removes both problems: the value is explicitly UTC, so the number inside the token is right everywhere.

**Why it is here.** To decide how long the token lives, correctly, on any machine.

**If you removed or changed it.** Without an `expires_at`, the token would carry no `exp` claim. I checked: `jose` accepts a token without `exp` by default (it does not require it). The token would then be valid **forever**: a stolen token could never be invalidated by waiting. If you changed `timezone.utc` back to nothing, you would reintroduce the bug above.

### Block 13: The payload (the claims)

```python
    payload = {
        "sub": str(user_id),  # "sub" (subject) is the standard claim for the user
        "exp": expires_at,
    }
```

**Word by word**

- `payload` - a local variable holding a dictionary: the claims to put inside the token.
- `{` ... `}` - a Python dictionary (key-value pairs).
- `"sub"` - the key. In the JWT standard, `sub` means **subject**: "who this token is about". Libraries and other systems expect the user identity here, so we follow the convention instead of inventing a name like `user_id`.
- `:` - separates key and value in a dictionary.
- `str(user_id)` - converts the integer id to a string, e.g. `7` to `"7"`. This is **required**, not a style choice. I checked `jose/jwt.py`: `decode` runs `_validate_sub`, which raises `JWTClaimsError("Subject must be a string.")` if `sub` is not a string. I confirmed by creating a token with `"sub": 7` (an integer) and decoding it: it was rejected. So an integer `sub` would make every login produce a token that the server itself refuses.
- `# "sub" (subject) is the standard claim for the user` - comment stating the convention.
- `,` - separates dictionary entries.
- `"exp"` - the key. In the JWT standard `exp` means **expiration time**.
- `expires_at` - the aware datetime from Block 12. `jose` converts it to an integer (Block 12).
- `,` - trailing comma, allowed in Python, makes adding a line later cleaner.

**Why it is here.** These two claims are the minimum useful token: who, and until when.

**If you removed or changed it.** Remove `"sub"`: `decode_access_token` would hit `KeyError` on `payload["sub"]` and return `None`, so every protected request would get 401 even with a fresh token. Remove `"exp"`: tokens would never expire. Rename `"sub"` to `"user_id"`: it would still work if you also changed Block 17, but you would lose the standard meaning and the string check.

### Block 14: Signing the token

```python
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

**Word by word**

- `return` - give the result back to the login endpoint.
- `jwt` - the module from Block 3.
- `.encode` - its function that builds a token.
- `payload` - first argument: the claims dictionary from Block 13.
- `settings.SECRET_KEY` - second argument: the secret used to compute the signature. `config.py` declares it without a default, so the app refuses to start if `.env` does not define it. It should be long and random (`.env.example` shows how to generate one).
- `algorithm=` - keyword argument naming the signing algorithm.
- `settings.ALGORITHM` - from `.env`, default `"HS256"`.

What `encode` does, checked in `jose/jwt.py`: it converts `exp` (and `iat`, `nbf` if present) from `datetime` to an integer, then calls `jws.sign`, which builds the header `{"alg":"HS256","typ":"JWT"}`, base64url-encodes header and payload, computes the HMAC-SHA256 signature over `header.payload` with the key, and joins the three parts with dots.

**Why it is here.** This is the line that actually produces the string the client will carry around.

**If you removed or changed it.** No token, no login. If `SECRET_KEY` were weak (like `"secret"`), an attacker could guess it offline and then sign tokens for any user id. If you changed `algorithm` to something `decode` does not allow, every token would be rejected (see Block 16).

### Block 15: decode_access_token, signature line and docstring

```python
def decode_access_token(token: str) -> int | None:
    """
    Return the user id stored in the token.

    Returns None when the token is invalid, tampered with, or expired.
    """
```

**Word by word**

- `def decode_access_token(` - defines the function `dependencies.py` calls on every protected request.
- `token: str` - the raw token string taken from the `Authorization` header.
- `) -> int | None:` - the return type hint. `int | None` reads "an int **or** None". The vertical bar `|` between two types means "either of these". This syntax needs Python 3.10 or newer (the project uses 3.14). Your old code wrote the same idea as `Optional[int]` from `typing`; the new spelling is the modern one and needs no import.
- The docstring says exactly what the two possible results mean: an id on success, `None` for anything wrong. Note the design: the function never raises. The caller only has to check for `None`.

**Why it is here.** It turns "a string from a header" into "a trusted user id or nothing". All the checking happens in one place.

**If you removed or changed it.** `dependencies.py` would fail to import, so the app would not start.

### Block 16: Decoding and checking the token

```python
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
```

**Word by word**

- `try:` - starts a block of code that *may* raise an error. If an error happens inside, Python jumps to the matching `except` (Block 18) instead of crashing.
- `payload` - local variable: the claims dictionary read from the token.
- `jwt.decode(` - the library function that checks a token and returns its claims.
- `token` - the string to check.
- `settings.SECRET_KEY` - the same secret used in Block 14. The signature is recomputed with it.
- `algorithms=[settings.ALGORITHM]` - keyword argument, a **list** of algorithms the server accepts. `[` `]` make a list; here it has one element, `"HS256"`. The decoder reads the algorithm name from the token's header and refuses any name not in this list. This closes a classic attack where a forged token says `"alg":"none"` (no signature). I tested it: a token with `alg=none` was rejected with `JWTError: The specified alg value is not allowed`, and so was a token signed with `HS512`.

**What `jwt.decode` checks, in order.** I read `jose/jwt.py` and `jose/jws.py` and tested each case:

1. **Shape.** The string must have three dot-separated parts. `"abc"`, `""` or `"a.b"` give `JWTError: Not enough segments`.
2. **Header.** Part 1 must be valid base64 and valid JSON. Garbage gives `JWTError: Invalid header string: ...`.
3. **Algorithm.** The header's `alg` must be in `algorithms`. Otherwise `JWTError: The specified alg value is not allowed`.
4. **Signature.** It recomputes the HMAC over `part1.part2` with `SECRET_KEY` and compares with part 3. Any edit to the payload, or a token made with a different secret, gives `JWTError: Signature verification failed.`
5. **Payload.** Part 2 must be JSON and must be an object (a dict).
6. **Claims.** With the default options it validates: `exp` (if present and in the past: `ExpiredSignatureError: Signature has expired.`), `nbf` (not-before), `iat` (issued-at), `aud`, `iss`, `sub` (must be a string: `JWTClaimsError: Subject must be a string.`), `jti`, `at_hash`. None of these claims are *required* by default; they are checked only if present. Our tokens always contain `sub` and `exp`.

Only when all of that passes does `decode` return the dictionary, e.g. `{'sub': '7', 'exp': 1791290408}`.

**Why it is here.** This single call is the whole security check of the token. Everything an attacker could try (edit, forge, reuse an old one, change the algorithm) is caught here.

**If you removed or changed it.** If you used `jwt.get_unverified_claims(token)` instead, the server would trust any payload without checking the signature, and anyone could craft a token for user id 1. If you removed `algorithms=[...]`, the library would raise a `JWTError` for every token, because it refuses to guess (it needs an explicit allow list).

### Block 17: Extracting the user id

```python
        return int(payload["sub"])
```

**Word by word**

- `return` - give the value back and leave the function (also leaves the `try` block normally).
- `int(` ... `)` - converts a string to an integer, `"7"` to `7`. The inverse of the `str(user_id)` in Block 13.
- `payload["sub"]` - looks up the key `"sub"` in the claims dictionary. Square brackets after a dictionary mean "get the value for this key". If the key is missing this raises `KeyError`.

**Why it is here.** `dependencies.py` needs an integer to pass to `db.get(User, user_id)`, and the token stores a string.

**If you removed or changed it.** Return `payload["sub"]` without `int`: `db.get(User, "7")` would still find the user on PostgreSQL (the driver converts), but the type hint `-> int | None` would be a lie and some comparisons elsewhere could silently misbehave. Use `payload.get("sub")` instead: a missing `sub` would give `None`, then `int(None)` raises `TypeError`, which is caught anyway. Keeping `["sub"]` is simply clearer.

### Block 18: Catching every failure

```python
    except (JWTError, KeyError, TypeError, ValueError):
        return None
```

**Word by word**

- `except` - keyword: "if an error of one of these types happened in the `try` block, run this instead".
- `(` ... `)` - a tuple (a fixed group) of exception classes. One `except` can catch several types.
- `JWTError` - from Block 3. Catches bad shape, bad header, disallowed algorithm, bad signature, bad payload, expired token (`ExpiredSignatureError` is a subclass), bad claim (`JWTClaimsError` is a subclass).
- `KeyError` - raised by `payload["sub"]` when the token has no `sub` claim. I confirmed: a signed token without `sub` passes `decode` and then fails here, and the function returns `None`.
- `TypeError` - raised when a value has the wrong type for an operation, e.g. `int(None)`. I tried to trigger it through `jwt.decode` and `int(...)` with many bad tokens and could not: `jose` already rejects a non-string `sub` with `JWTClaimsError`. So in this project it is a safety net rather than a case that occurs. That is fine; being defensive in the security layer costs nothing.
- `ValueError` - raised by `int("abc")` when `sub` is a string that is not a number. I confirmed: a signed token with `"sub": "abc"` returns `None`.
- `return None` - the uniform "no" answer.

One honest note: if `token` were not a string at all (for example `None`), `jose` raises `AttributeError`, which this `except` does **not** catch. I checked. That cannot happen through the normal path, because `oauth2_scheme` in `dependencies.py` either returns a string or stops the request with 401 before this function is called. If you ever call `decode_access_token` from somewhere else, pass a string.

**Why it is here.** The caller gets a simple contract: an id or `None`. All the many ways a token can be wrong collapse into one answer, and `get_current_user` turns that one answer into one `401` response. The client gets the same message for every failure, so it cannot learn *why* its token failed (which would help an attacker).

**If you removed or changed it.** Without the `except`, an expired or forged token would raise an uncaught exception inside the dependency, and FastAPI would answer **500 Internal Server Error** instead of **401 Unauthorized**. Your logs would fill with tracebacks for something that is a normal, expected situation (tokens expire every hour). If you caught only `JWTError`, a token without `sub` would still be a 500.

### Compared to your old code

The old project split this work across two files: `app/utils.py` (passwords) and `app/oauth2.py` (tokens). The new project keeps both halves in one file, `security.py`, because they are both "pure security, no web, no database".

**Passwords: `app/utils.py` (old)**

```python
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()   # Argon2id with safe default settings


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
```

This part was already right. You chose `pwdlib` with Argon2id, which is the modern recommendation. The new file is the same code with three cosmetic changes: the variable is called `password_hasher` instead of `password_hash` (so it is not confused with "a password hash", which is a string), the parameter is called `plain_password` to make "not hashed yet" explicit, and each function has a one-line docstring. Nothing to fix here. Well done.

**Tokens: `app/oauth2.py` (old), the token part**

```python
from jose import JWTError, jwt
from datetime import datetime , timedelta

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data : dict):
    to_encode = data.copy()

    expire = datetime.now() + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

def verify_access_token(token: str, credentials_exceptions):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exceptions
        token_data = TokenData(id=user_id)
    except JWTError:
        raise credentials_exceptions
    return token_data


    return token_data
```

What changed and why, one item at a time:

1. **`datetime.now()` to `datetime.now(timezone.utc)`.** This is the real bug, explained fully in Block 12. Your tokens lived 6.5 hours instead of 1 hour, and on a machine west of UTC they would have been dead on arrival. Nothing in your code told you, because `jose` silently assumes a naive datetime is UTC.

2. **`data: dict` to `user_id: int`.** The old function accepted any dictionary, and the login router had to know the magic key name `"user_id"`. If two routers spelled it differently, tokens would silently stop working. The new function takes exactly one integer and builds the payload itself, so the key name lives in one place.

3. **`"user_id"` to `"sub"`, stored as a string.** `sub` is the standard JWT claim for "who". Using the standard name means any JWT tool or library understands the token. Storing it as `str(user_id)` is required by `jose`'s `decode` (Block 13). Your old `"user_id": 7` worked only because `jose` does not validate custom claim names; the moment you switched to `sub` with an integer, decoding would fail.

4. **Module-level copies `SECRET_KEY = settings.SECRET_KEY` removed.** They were harmless, but they duplicate names and make it look like there are two sources of truth. The new code reads `settings.X` at the point of use.

5. **`verify_access_token(token, credentials_exceptions)` to `decode_access_token(token) -> int | None`.** The old function mixed two jobs: decoding a token *and* raising an HTTP error. That forced it to take an `HTTPException` as a parameter, which ties a pure function to FastAPI. The new function just returns an id or `None`. Deciding what HTTP response to send is the job of `dependencies.py`, which is the FastAPI-aware file.

6. **`TokenData(id=user_id)` removed.** The old code wrapped the id in a Pydantic model (`class TokenData(BaseModel): id: Optional[int] = None`) only to read `.id` back out one line later. An `int` is enough. The `TokenData` schema is gone from the new project.

7. **More exceptions caught.** The old code caught only `JWTError`. A signed token without `user_id` returned `None` from `.get`, which you handled, but a `"user_id": "abc"` would have produced a `TokenData` validation error (a 500). The new `except (JWTError, KeyError, TypeError, ValueError)` covers all of these.

8. **The unreachable line.** The old `verify_access_token` has `return token_data` twice. The second one can never run, because the first `return` already left the function. Python does not warn about this. It did no harm, but it shows why keeping functions short helps: there is less room for leftovers.

### Key terms in this file

| Term | Meaning |
| --- | --- |
| hash | A one-way scramble of a text. Easy to compute, practically impossible to reverse. |
| Argon2id | The password-hashing algorithm used here. Slow and memory-hungry on purpose. |
| salt | 16 random bytes mixed into each hash so the same password gives different hashes. Stored inside the hash string. |
| `PasswordHash.recommended()` | `pwdlib`'s one-line way to get an Argon2id hasher with safe defaults. |
| `verify` | Re-hash the typed password with the stored salt and parameters and compare. Never use `==`. |
| JWT | JSON Web Token: `header.payload.signature`, three base64url parts joined by dots. |
| claim | One fact inside the payload, e.g. `sub` or `exp`. |
| `sub` | Subject: who the token is about. Must be a string. Here, the user id. |
| `exp` | Expiration time, as seconds since 1970-01-01 UTC. |
| HS256 | HMAC with SHA-256: a keyed checksum. The same secret signs and verifies. |
| `SECRET_KEY` | The long random string in `.env` that signs tokens. Never commit it. |
| UTC | The reference clock all time zones are measured from. Tokens must use it. |
| naive / aware datetime | A `datetime` without / with time-zone information. `datetime.now()` is naive; `datetime.now(timezone.utc)` is aware. |
| `int \| None` | Type hint: "an int or None". Same as `Optional[int]`. |
| `try` / `except` | Run the code; if one of the listed errors happens, run the `except` block instead of crashing. |
| `JWTError` | The base error class of `python-jose` for any token problem; `ExpiredSignatureError` and `JWTClaimsError` are subclasses. |

## File: app/core/dependencies.py

### What this file is for

This file defines the three things every router in the project needs and should not have to rebuild: a database session, the logged-in user, and the optional date-range filter. Each one is a **FastAPI dependency**: a function that FastAPI calls *before* your endpoint and whose result it hands to your endpoint as a parameter. The file then wraps each dependency in a short alias (`DatabaseSession`, `CurrentUser`, `DateRangeFilter`) so that an endpoint can say `db: DatabaseSession, current_user: CurrentUser` instead of repeating `Depends(...)` everywhere.

It imports `dataclass`, `date` and `Annotated` from the standard library; `Depends`, `HTTPException`, `Query`, `status` and `OAuth2PasswordBearer` from FastAPI; `Session` from SQLAlchemy; and four project pieces: `settings`, `decode_access_token`, `get_db` and the `User` model.

Who imports it: every router except `health.py`. `auth.py` uses `DatabaseSession`; `users.py` uses `CurrentUser`; `categories.py` uses both; `expenses.py` and `reports.py` use both plus `DateRangeFilter` (and `reports.py` also imports the `DateRange` class itself for a type hint).

### The whole file

```python
"""
Reusable FastAPI dependencies.

Routers import the `Annotated` aliases defined here instead of repeating
`Depends(...)` in every endpoint:

    def list_expenses(db: DatabaseSession, current_user: CurrentUser): ...
"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User

# Tells Swagger UI (/docs) where to send the login form to get a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# One database session per request.
DatabaseSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
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


# Any endpoint that declares this parameter requires a valid login.
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Shared query filters
# ---------------------------------------------------------------------------
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

### Walkthrough, block by block

### Block 1: The module docstring

```python
"""
Reusable FastAPI dependencies.

Routers import the `Annotated` aliases defined here instead of repeating
`Depends(...)` in every endpoint:

    def list_expenses(db: DatabaseSession, current_user: CurrentUser): ...
"""
```

**Word by word**

- `"""` ... `"""` - the file's docstring (see `security.py` Block 1).
- `Reusable FastAPI dependencies.` - the summary. "Dependency" here is FastAPI's word for "a function FastAPI runs for you to prepare a parameter". Explained in depth in Block 13.
- `Routers import the `Annotated` aliases ...` - tells you the intended usage: do not write `Depends(get_db)` in routers; import `DatabaseSession` and friends.
- `def list_expenses(db: DatabaseSession, current_user: CurrentUser): ...` - an example signature. The `...` means "body omitted".

**Why it is here.** It shows the pattern the whole project follows in one glance.

**If you removed or changed it.** No runtime change.

### Block 2: Importing dataclass

```python
from dataclasses import dataclass
```

**Word by word**

- `dataclasses` - a standard-library module for classes that mainly hold data.
- `dataclass` - a **decorator** from that module. A decorator is a function you put above a class or function with an `@` sign; it receives the class and returns a modified version. `@dataclass` writes the boring methods for you (Block 23).

**Why it is here.** `DateRange` (Block 23) is a tiny container with two fields. `@dataclass` lets it be defined in three lines.

**If you removed or changed it.** Block 23 would fail with `NameError: name 'dataclass' is not defined`; the app would not start.

### Block 3: Importing date

```python
from datetime import date
```

**Word by word**

- `datetime` - the standard-library module (see `security.py` Block 2).
- `date` - a class for a calendar day with no time part: year, month, day. Example: `date(2026, 1, 31)`. Two dates can be compared with `<`, `>`, `==`.

**Why it is here.** The filter parameters `start_date` and `end_date` are days, not moments. Using `date` tells FastAPI to parse `"2026-01-31"` into a `date` object and to reject anything that is not a valid day.

**If you removed or changed it.** `NameError` at import. If you used `datetime` instead, the query string `?start_date=2026-01-31` would still parse (Pydantic accepts a plain date for a datetime), but comparisons with the `Expense.expense_date` column (a `Date` column) would mix types and the "on or before" logic for `end_date` would become confusing (midnight vs the whole day).

### Block 4: Importing Annotated

```python
from typing import Annotated
```

**Word by word**

- `typing` - the standard-library module for type hints.
- `Annotated` - a special form that lets you attach **extra information** to a type hint without changing the type.

**`Annotated`, word by word.** The shape is:

```python
Annotated[<the real type>, <extra 1>, <extra 2>, ...]
```

- `Annotated` - the name.
- `[` `]` - square brackets, like indexing. For typing objects, brackets mean "parameterise this with the following items".
- The **first** item is the real type. To Python's type system, `Annotated[Session, X]` *is* `Session`. Your editor still autocompletes `db.` as a `Session`.
- Every **other** item is metadata: any Python object. Python itself ignores it. But a library can read it. FastAPI reads it.

I checked what the object looks like at runtime:

```text
DatabaseSession.__origin__   -> <class 'sqlalchemy.orm.session.Session'>
DatabaseSession.__metadata__ -> (Depends(dependency=<function get_db>, use_cache=True, scope=None),)
```

So `Annotated[Session, Depends(get_db)]` is "type `Session`, plus one note that says `Depends(get_db)`". When FastAPI inspects an endpoint's parameters, it finds the `Depends` note and knows: "call `get_db` and pass the result here". When it finds a `Query(...)` note (Block 24), it knows: "read this from the URL query string".

**Why `Annotated` instead of a default value.** Your old code wrote `db: Session = Depends(get_db)`. That puts the dependency in the *default value* slot, which is a trick: `Depends(get_db)` is not really a default. It also cannot be reused, because a default value belongs to one function. With `Annotated`, the type plus its note is a single object that can be stored in a variable (`DatabaseSession`) and reused by every router. This is the style the FastAPI documentation recommends today.

**Why it is here.** It is the mechanism behind all three aliases.

**If you removed or changed it.** `NameError` at import. If you rewrote the aliases without `Annotated` (e.g. `DatabaseSession = Session`), FastAPI would see a plain `Session` parameter with no note, would try to read it from the request body, and every endpoint would return 422 or fail.

### Block 5: Importing from FastAPI

```python
from fastapi import Depends, HTTPException, Query, status
```

**Word by word**

- `fastapi` - the web framework.
- `Depends` - a function that marks a parameter as "filled by calling this other function". It returns a small `fastapi.params.Depends` object holding the function to call, `use_cache=True` and `scope=None` (I checked). Full explanation in Block 13.
- `HTTPException` - an exception class. When you `raise` it, FastAPI stops the request and sends an HTTP error response with the status code, a JSON body `{"detail": ...}` and any extra headers you give. You used it in the old project too.
- `Query` - a function that marks a parameter as "read from the URL query string" (`?start_date=...`) and lets you attach a description and validation rules. It returns a `fastapi.params.Query` object, which is a subclass of Pydantic's `FieldInfo` (I checked `fastapi/params.py`).
- `status` - a module of named integer constants, e.g. `status.HTTP_401_UNAUTHORIZED == 401`. I checked `fastapi/__init__.py`: it is simply `from starlette import status`. Using the name instead of the bare number makes the intent readable.

**Why it is here.** These are the four FastAPI tools this file uses.

**If you removed or changed it.** `NameError` at import for whichever name you removed.

### Block 6: Importing OAuth2PasswordBearer

```python
from fastapi.security import OAuth2PasswordBearer
```

**Word by word**

- `fastapi.security` - FastAPI's sub-package of ready-made authentication helpers.
- `OAuth2PasswordBearer` - a class. You create one object from it (Block 12) and use that object as a dependency. It does two jobs: at request time it reads the `Authorization: Bearer <token>` header and returns the token string; at documentation time it tells `/docs` how to show the "Authorize" button.

The name, piece by piece: **OAuth2** is the standard that defines the token flows; **Password** is the specific flow where the client sends username and password to get a token; **Bearer** is the way the token is sent back: `Authorization: Bearer <token>`. "Bearer" literally means "whoever carries this token is treated as the user", which is why tokens must expire and must travel only over HTTPS.

**Why it is here.** Reading the header by hand (`request.headers.get("Authorization")`, split on the space, check the word "Bearer") is easy to get subtly wrong and would not show up in `/docs`. The class does it correctly and documents it.

**If you removed or changed it.** `NameError` at import.

### Block 7: Importing Session

```python
from sqlalchemy.orm import Session
```

**Word by word**

- `sqlalchemy.orm` - the ORM (object-relational mapper) part of SQLAlchemy: the part that maps Python classes to tables.
- `Session` - the class whose objects represent one "conversation" with the database: a place to add objects, run queries, commit or roll back. `get_db` in `app/database/session.py` creates one per request.

**Why it is here.** Only for the type hint inside `DatabaseSession = Annotated[Session, ...]`, so editors know that `db` is a `Session` and can autocomplete `db.get`, `db.scalar`, `db.commit` and so on.

**If you removed or changed it.** `NameError` at import. The hint has no effect at runtime; FastAPI uses the `Depends(get_db)` note, not the type, to fill the parameter.

### Block 8: Importing settings

```python
from app.core.config import settings
```

**Word by word**

- Same `settings` object as in `security.py` Block 5.

**Why it is here.** Block 12 needs `settings.API_V1_PREFIX` to build the login URL for `/docs`.

**If you removed or changed it.** `NameError` on Block 12; the app would not start.

### Block 9: Importing decode_access_token

```python
from app.core.security import decode_access_token
```

**Word by word**

- `app.core.security` - the file explained in the first half of this document.
- `decode_access_token` - the function that turns a token string into a user id or `None` (`security.py` Blocks 15 to 18).

**Why it is here.** `get_current_user` (Block 17) needs it.

**If you removed or changed it.** `NameError` inside `get_current_user`, so every protected endpoint would answer 500.

### Block 10: Importing get_db

```python
from app.database.session import get_db
```

**Word by word**

- `app.database.session` - the file that builds the engine and the session factory (document 05).
- `get_db` - the generator function that opens a `Session`, `yield`s it, and closes it in a `finally` block. You had the same function in the old `app/database.py`.

**Why it is here.** It is the dependency behind `DatabaseSession` (Block 13).

**If you removed or changed it.** `NameError` at import.

### Block 11: Importing the User model

```python
from app.models.user import User
```

**Word by word**

- `app.models.user` - the file with the `users` table mapping (document 06).
- `User` - the SQLAlchemy model class. One `User` object is one row of `users`.

**Why it is here.** `get_current_user` loads a `User` with `db.get(User, user_id)` and returns it; the alias `CurrentUser` is typed as `User`.

**If you removed or changed it.** `NameError` at import.

### Block 12: The OAuth2 scheme

```python
# Tells Swagger UI (/docs) where to send the login form to get a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
```

**Word by word**

- `# Tells Swagger UI (/docs) where to send the login form to get a token.` - comment. "Swagger UI" is the interactive documentation page FastAPI serves at `/docs`.
- `oauth2_scheme` - a module-level variable holding the one scheme object, reused by every request.
- `=` - assignment.
- `OAuth2PasswordBearer(` - creates an object of the class from Block 6.
- `tokenUrl=` - the one required keyword argument: the URL where a client can POST username and password to get a token.
- `f"..."` - an **f-string**: a string with `{}` placeholders that Python fills with the value of the expression inside.
- `{settings.API_V1_PREFIX}` - the prefix from `config.py`, default `"/api/v1"`.
- `/auth/login` - the auth router's prefix `/auth` plus its route `/login` (see `app/routers/auth.py`).
- The result is `"/api/v1/auth/login"`. I checked `oauth2_scheme.model.flows.password.tokenUrl` and it is exactly that, and I checked `/openapi.json`: that path exists.

**What this object does at request time.** The object is *callable* (its class defines `__call__`), so `Depends(oauth2_scheme)` works like `Depends(some_function)`. I read `fastapi/security/oauth2.py`. When FastAPI calls it with the incoming request:

1. It reads the `Authorization` header.
2. It splits the value at the first space into a *scheme* and a *parameter*. For `Bearer eyJhbG...` the scheme is `Bearer` and the parameter is the token.
3. If the header is missing, or the scheme (compared in lower case, so `bearer` also works, I tested it) is not `bearer`, it raises `HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})`. This is the `auto_error=True` default. I confirmed all three: no header gives 401 `Not authenticated`; `Authorization: Basic ...` gives 401 `Not authenticated`; `Authorization: bearer <token>` is accepted.
4. Otherwise it returns the parameter: the raw token string. Note it does **not** check the token; that is `decode_access_token`'s job.

One edge: `Authorization: Bearer` with nothing after it passes step 3 (scheme is right) and returns `""`. `decode_access_token("")` returns `None` (`JWTError: Not enough segments`), so the client still gets a clean 401, just with the other message. I tested this too.

**What `tokenUrl` does.** It is **only** used for documentation. The value goes into the OpenAPI document under `components.securitySchemes` as an `oauth2` scheme with a `password` flow. I checked the generated JSON:

```json
{"OAuth2PasswordBearer": {"type": "oauth2", "flows": {"password": {"scopes": {}, "tokenUrl": "/api/v1/auth/login"}}}}
```

Swagger UI reads that and shows an **Authorize** button. When you type an email and a password there, it POSTs them as a form to `/api/v1/auth/login`, takes the `access_token` from the response, and from then on adds `Authorization: Bearer <token>` to every "Try it out" request. Every endpoint that depends on `oauth2_scheme` (directly or through `CurrentUser`) gets a padlock icon and a `security` entry in the spec; I checked `/users/me` and it has `[{"OAuth2PasswordBearer": []}]`.

**Why it is here.** It is the single place that knows how the token arrives (the header) and where `/docs` can get one.

**If you removed or changed it.** Remove it: `get_current_user` cannot be defined; the app will not start. Change `tokenUrl` to a wrong path (for example `"login"` like the old code, or forget the prefix): the API itself keeps working, because the header reading does not use `tokenUrl`, but the Authorize button in `/docs` would POST to a URL that does not exist and show an error. Set `auto_error=False`: a missing header would give `token=None`, and `decode_access_token(None)` raises an uncaught `AttributeError` (see `security.py` Block 18), so you would get 500 instead of 401.

### Block 13: The DatabaseSession alias

```python
# One database session per request.
DatabaseSession = Annotated[Session, Depends(get_db)]
```

**Word by word**

- `# One database session per request.` - comment stating the guarantee this gives.
- `DatabaseSession` - the alias name. Capitalised like a class because routers use it like a type.
- `=` - assignment.
- `Annotated[` ... `]` - from Block 4: a type plus a note.
- `Session` - the real type (Block 7).
- `,` - separates the type from the note.
- `Depends(get_db)` - the note: "to fill this parameter, call `get_db`". `Depends` is called with the function *object* `get_db`, not with `get_db()`; FastAPI will call it later, at the right moment.

**How FastAPI runs dependencies.** This is the heart of the file, so here it is step by step. When a request arrives for an endpoint such as

```python
def list_categories(db: DatabaseSession, current_user: CurrentUser) -> ...
```

FastAPI has already (at startup) inspected the function's parameters and built a tree:

```text
list_categories
 |- db            <- get_db
 |- current_user  <- get_current_user
                     |- token  <- oauth2_scheme
                     |- db     <- get_db   (same function as above)
```

For each request it walks that tree, deepest first, and for every dependency it:

1. Fills that function's own parameters the same way (recursively).
2. Calls the function. A plain function returns a value. A **generator** function (one with `yield`, like `get_db`) is run up to the `yield`; the yielded value is used as the result, and the rest of the function (after `yield`, including `finally`) is run later, after the response is sent.
3. Passes the result into the parameter.

Two facts I verified with a small test app:

- **Order.** With a `yield` dependency `A`, a dependency `B` that itself needs `A`, and an endpoint that needs both, the recorded order was `A-start, B, endpoint, A-end`. So `get_db` opens the session before anything else, `get_current_user` runs next, then the endpoint body, and the session is closed last.
- **Caching.** `Depends` has `use_cache=True` by default (I printed the object). It means: within one request, the same dependency function is called **once** and its result reused. In the tree above `get_db` appears twice, but I counted and it was called exactly once per request (for `/users/me` and for `/expenses`). So the endpoint and `get_current_user` share the same `Session`. That is what the comment "One database session per request" promises, and it matters: if they had two sessions, the user loaded in one could not be safely used in the other.

**Why it is here.** Every router needs a session. Writing `Annotated[Session, Depends(get_db)]` in thirty endpoints is noise and a chance for typos; the alias makes it one word.

**If you removed or changed it.** Every router imports `DatabaseSession`, so removing it breaks the app at import. If you wrote `Depends(get_db())` (with parentheses), `get_db()` would run once at import time, returning a generator object, and FastAPI would raise an error at startup because a generator object is not a callable dependency.

### Block 14: Section banner "Authentication"

```python
# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
```

**Word by word**

- Decorative comment lines plus a section name. "Authentication" means "finding out who the caller is".

**Why it is here.** Visual separation.

**If you removed or changed it.** No runtime change.

### Block 15: get_current_user, signature and docstring

```python
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DatabaseSession,
) -> User:
    """Read the Bearer token and return the logged-in user, or respond 401."""
```

**Word by word**

- `def get_current_user(` - defines the dependency behind `CurrentUser`. It is never called by your code directly; FastAPI calls it.
- `token` - first parameter.
- `: Annotated[str, Depends(oauth2_scheme)]` - type `str`, with the note "fill this by calling `oauth2_scheme`". From Block 12 we know that gives the raw token string or stops the request with 401.
- `,` - separates parameters. Each parameter sits on its own line; this is just formatting.
- `db: DatabaseSession` - the session, via the alias from Block 13. Thanks to caching it is the same session the endpoint will get.
- `) -> User:` - returns a `User` model object. (It can also raise; raising is not a return.)
- `"""Read the Bearer token and return the logged-in user, or respond 401."""` - the docstring, naming the three possible paths: read, return, or 401.

**Why it is here.** Every protected endpoint needs "which user is calling?". This function is that answer, computed once per request.

**If you removed or changed it.** `CurrentUser` could not be defined; every router except `health.py` and `auth.py` would fail to import.

### Block 16: Preparing the error

```python
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

**Word by word**

- `credentials_error` - a local variable holding an exception *object*. Creating an exception does not raise it. It is created once here and raised in two places below, so the two failure paths send the identical response.
- `HTTPException(` - the class from Block 5.
- `status_code=` - keyword argument: the HTTP status number.
- `status.HTTP_401_UNAUTHORIZED` - the constant `401`. In HTTP, 401 means "you did not prove who you are (or your proof is bad)". It is the right code for a missing, bad or expired token. (403 Forbidden means "I know who you are and you are not allowed", which is a different situation.)
- `detail=` - the message that goes into the JSON body as `{"detail": "..."}`.
- `"Could not validate credentials"` - deliberately vague. It does not say *why* (expired? forged? deleted user?), so an attacker probing tokens learns nothing.
- `headers=` - extra response headers, as a dictionary.
- `{"WWW-Authenticate": "Bearer"}` - the HTTP standard says a 401 response *must* include a `WWW-Authenticate` header telling the client which kind of credentials it should use. `Bearer` says "send a bearer token". Browsers and HTTP clients look at it. I confirmed the header is present on the 401 responses.

**Why it is here.** One correct, standard-conforming error, defined once.

**If you removed or changed it.** Without it, the two `raise credentials_error` lines fail with `NameError` (a 500). If you dropped the `headers=`, the API would still work but would violate the HTTP spec for 401. If you used 403, API clients that automatically refresh or re-login on 401 would stop doing so.

### Block 17: Decoding the token

```python
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
```

**Word by word**

- `user_id` - local variable: the id from the token, or `None`.
- `= decode_access_token(token)` - the function from `security.py`, called with the header's token string. It never raises for a bad token; it returns `None`.
- `if` - keyword: run the indented block only when the condition is true.
- `user_id is None` - `is` checks identity with the single `None` object. For `None` you write `is None`, not `== None`; that is the Python convention and it is also faster and safer.
- `:` - ends the `if` line.
- `raise` - keyword: throw the exception. Execution stops here; FastAPI catches the `HTTPException` and sends the 401 response. The endpoint body never runs.
- `credentials_error` - the exception object from Block 16.

**Why it is here.** This is the point where "a string someone sent us" becomes "an id we trust" or "go away".

**If you removed or changed it.** Skip the `None` check and go straight to `db.get(User, None)`: SQLAlchemy would raise an error for a `None` primary key, which becomes a 500. Worse, if you ever changed `decode_access_token` to return something non-`None` on failure, a forged token would get through.

### Block 18: Loading the user by primary key

```python
    user = db.get(User, user_id)
```

**Word by word**

- `user` - local variable: the `User` object or `None`.
- `db` - the `Session` from Block 15.
- `.get(` - `Session.get`, SQLAlchemy 2.0's method for "fetch one row by primary key".
- `User` - the model class: which table.
- `user_id` - the primary-key value.

**What `db.get` does.** I read `sqlalchemy/orm/session.py` and ran it with SQL logging on:

1. First it looks in the session's **identity map**: the in-memory dictionary of objects this session has already loaded, keyed by (class, primary key). If the user is there, it returns that object with **no SQL at all**. I confirmed: a second `db.get(User, 1)` in the same session printed no query and returned the very same Python object (`is` was `True`).
2. Otherwise it runs one `SELECT`. The real statement (SQLite dialect shown; PostgreSQL is the same with `%(pk_1)s` instead of `?`):

```sql
SELECT users.id AS users_id, users.email AS users_email, users.full_name AS users_full_name,
       users.hashed_password AS users_hashed_password, users.is_active AS users_is_active,
       users.created_at AS users_created_at
FROM users
WHERE users.id = ?
```

3. It returns the mapped `User` object, or `None` when no row matched. I confirmed: `db.get(User, 999)` returned `None`.

Compare with the old `db.query(User).filter(User.id == token.id).first()`: same result, but `query()` is the legacy 1.x API, it always sends SQL even if the object is already loaded, and `.first()` adds `LIMIT 1` for a lookup that can only match one row anyway. `get` says exactly what you mean: "the row with this primary key".

**Why it is here.** The token only proves "user 7 logged in at some point". The endpoint needs the actual user row (email, name, `is_active`), and the database is the source of truth.

**If you removed or changed it.** If you returned `user_id` instead of loading the user, you could not check `is_active`, and endpoints that use `current_user.id` or `current_user.email` would break. If you used `db.scalar(select(User).where(User.id == user_id))` it would work the same; `get` is just shorter and uses the identity map.

### Block 19: Rejecting deleted or deactivated accounts

```python
    # The token can outlive the account (deleted or deactivated user).
    if user is None or not user.is_active:
        raise credentials_error
```

**Word by word**

- `# The token can outlive the account ...` - comment explaining the situation this handles: a token is valid for 60 minutes no matter what happens to the account in the meantime.
- `if` - conditional.
- `user is None` - true when `db.get` found no row: the account was deleted after the token was issued, or the token's `sub` never matched a user.
- `or` - logical "or": the whole condition is true if either side is true. Python evaluates left to right and stops early: if `user is None` is true, it does **not** evaluate `user.is_active` (which would crash on `None`). This ordering is therefore important.
- `not` - logical negation.
- `user.is_active` - the `Boolean` column from `app/models/user.py`, `True` by default. Setting it to `False` is a soft block: the row and its data stay, but the person cannot use the API.
- `raise credentials_error` - the same 401 as before. The client cannot tell "deleted" from "deactivated" from "bad token", on purpose.

I tested both: after setting `is_active = False` for the user, the same token that worked a moment earlier got `401 Could not validate credentials`; a freshly signed token for a non-existent user id 99 got the same.

**Why it is here.** Without this, a stateless token would be a problem: an admin could not lock out a user until the token expired.

**If you removed or changed it.** Remove the whole `if`: a deleted user's token would make `get_current_user` return `None`, and the endpoint would crash on `current_user.id` with `AttributeError` (a 500). This is exactly what the old code did (see the comparison below). Remove only the `is_active` part: deactivating a user would do nothing until their token expired, and the login endpoint's own `is_active` check would be the only barrier.

### Block 20: Returning the user

```python
    return user
```

**Word by word**

- `return` - hand back the value.
- `user` - the loaded, active `User` object.

**Why it is here.** This value is what every endpoint receives as `current_user`.

**If you removed or changed it.** The function would return `None` by default, and every endpoint would crash on `current_user.id`.

### Block 21: The CurrentUser alias

```python
# Any endpoint that declares this parameter requires a valid login.
CurrentUser = Annotated[User, Depends(get_current_user)]
```

**Word by word**

- `# Any endpoint that declares this parameter requires a valid login.` - comment describing the effect: just mentioning `current_user: CurrentUser` in an endpoint's parameters protects it.
- `CurrentUser` - the alias.
- `Annotated[User, Depends(get_current_user)]` - type `User`, note "call `get_current_user`".

**Why the alias exists.** Three reasons. (1) Brevity: `current_user: CurrentUser` versus `current_user: Annotated[User, Depends(get_current_user)]` in every endpoint. (2) One source of truth: if authentication ever changes (say, a different header), routers do not change. (3) Readability: an endpoint's signature now reads like a sentence: "this needs a database session and a logged-in user".

Note that an endpoint does not even have to *use* `current_user` to be protected. Declaring it is enough, because FastAPI runs the dependency either way.

**Why it is here.** It is the public face of everything above.

**If you removed or changed it.** Every router that imports `CurrentUser` would fail at import.

### Block 22: Section banner "Shared query filters"

```python
# ---------------------------------------------------------------------------
# Shared query filters
# ---------------------------------------------------------------------------
```

**Word by word**

- Decorative lines plus the section name. "Query filters" are the `?key=value` parts of a URL that narrow down results. "Shared" because `expenses.py` and `reports.py` both use the same one.

**Why it is here.** Visual separation.

**If you removed or changed it.** No runtime change.

### Block 23: The DateRange dataclass

```python
@dataclass
class DateRange:
    start_date: date | None
    end_date: date | None
```

**Word by word**

- `@dataclass` - the decorator from Block 2 applied to the class below. The `@` sign means "pass the following class through this function and use what it returns".
- `class` - keyword that defines a new type.
- `DateRange` - the class name.
- `:` - starts the class body.
- `start_date: date | None` - a field declaration: name `start_date`, type "a `date` or `None`" (the `|` from `security.py` Block 15). No default, so it is required.
- `end_date: date | None` - second field, same shape.

**What `@dataclass` does.** Without it, those two lines would be nothing but type hints; `DateRange(...)` would take no arguments. With it, Python generates the methods you would otherwise write by hand. I checked the resulting class:

- `__init__(self, start_date, end_date)` - so `DateRange(start_date=d1, end_date=None)` works. Calling `DateRange()` with no arguments raises `TypeError: ... missing 2 required positional arguments: 'start_date' and 'end_date'`.
- `__repr__` - printing an instance shows `DateRange(start_date=datetime.date(2026, 1, 1), end_date=None)`, handy when debugging.
- `__eq__` - two instances with the same field values compare equal with `==`.

**Why a class at all.** The dependency could return a tuple `(start_date, end_date)`, but then every router would have to remember the order. With a dataclass, routers write `date_range.start_date` and `date_range.end_date`, and `reports.py` can type-hint a helper parameter as `DateRange`.

**Why not a Pydantic `BaseModel`.** Pydantic models validate and convert input. Here the two dates have *already* been validated by FastAPI before `get_date_range` runs. A dataclass is the lightest possible container for already-clean data.

**Why it is here.** It is the return type of the dependency below and the type routers see.

**If you removed or changed it.** Remove `@dataclass`: `DateRange(start_date=..., end_date=...)` in Block 28 would raise `TypeError: DateRange() takes no arguments`. Remove the class: Block 25 and Block 28 fail with `NameError`, and `reports.py` fails to import.

### Block 24: get_date_range, the start_date parameter

```python
def get_date_range(
    start_date: Annotated[
        date | None,
        Query(description="Only include expenses on or after this date (YYYY-MM-DD)"),
    ] = None,
```

**Word by word**

- `def get_date_range(` - defines the dependency behind `DateRangeFilter`.
- `start_date` - the parameter name. Because the note is `Query`, FastAPI reads it from the URL query string using this exact name: `?start_date=2026-01-01`.
- `: Annotated[` - type plus note, spread over several lines inside the brackets.
- `date | None` - the type: a calendar day or nothing.
- `,` - separates type from note.
- `Query(` - the function from Block 5. It says "this comes from the query string" and carries documentation and rules.
- `description=` - keyword argument: text shown in `/docs` next to the field. I checked `/openapi.json`: the `start_date` parameter of `GET /api/v1/expenses` carries exactly this description and the schema `{"type": "string", "format": "date"}` or `null`.
- `"Only include expenses on or after this date (YYYY-MM-DD)"` - the description. "On or after" tells the reader the bound is inclusive. "YYYY-MM-DD" tells them the format.
- `)` - closes `Query(`.
- `]` - closes `Annotated[`.
- `= None` - the **default value**. This is what makes the parameter *optional*: if the URL has no `start_date`, the function receives `None`. With `Annotated`, defaults go here, after the bracket, as a normal Python default. (The `None` default and the `| None` type go together: the type says `None` is allowed, the default makes it the value when absent.)

**What happens with bad input.** FastAPI plus Pydantic parse the string. `?start_date=2026-01-01` becomes `date(2026, 1, 1)`. `?start_date=hello` is rejected before `get_date_range` runs. I tested it: the response is `422` with a body that points at `["query", "start_date"]` and says `Input should be a valid date or datetime, input is too short`. You get this validation for free from the type hint.

**Why it is here.** It declares the first half of the filter, with its documentation, in one place.

**If you removed or changed it.** Remove `= None`: the parameter becomes required, and `GET /api/v1/expenses` without `start_date` would return 422 `Field required`. Remove the `Query(...)` note but keep `= None`: FastAPI still treats a simple-typed parameter as a query parameter, so it would still work, but the description would disappear from `/docs`. Change the type to `str`: no parsing, no validation; the router would receive `"hello"` and the SQL comparison would fail.

### Block 25: The end_date parameter and the return type

```python
    end_date: Annotated[
        date | None,
        Query(description="Only include expenses on or before this date (YYYY-MM-DD)"),
    ] = None,
) -> DateRange:
```

**Word by word**

- `end_date: Annotated[date | None, Query(description=...)] = None` - the mirror of Block 24 for the upper bound. "On or before" again marks the bound as inclusive.
- `,` - trailing comma after the last parameter (allowed).
- `)` - closes the parameter list.
- `-> DateRange:` - the function returns a `DateRange` (Block 23).

**Why it is here.** The second half of the filter.

**If you removed or changed it.** Same consequences as for `start_date`.

### Block 26: The docstring

```python
    """Optional ?start_date=&end_date= filter shared by expenses and reports."""
```

**Word by word**

- A one-line docstring. `?start_date=&end_date=` is the shape of the query string. "Shared by expenses and reports" tells you where it is used: `GET /api/v1/expenses` and the `/api/v1/reports/...` endpoints.

**Why it is here.** Documentation.

**If you removed or changed it.** No runtime change.

### Block 27: Rejecting an impossible range

```python
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date",
        )
```

**Word by word**

- `if` - conditional.
- `start_date` - used as a condition on its own. In Python, `None` is "falsy" and a `date` object is always "truthy" (I checked: `bool(date(2026, 1, 1))` is `True`). So `start_date` here means "a start date was given".
- `and` - logical "and": every part must be true. Like `or`, it stops early: if `start_date` is `None`, Python never evaluates the rest, so the `>` comparison is never attempted on `None`.
- `end_date` - "an end date was given".
- `start_date > end_date` - compares two `date` objects chronologically; true when the start is later than the end, which is a range that can match nothing.
- `:` - ends the condition.
- `raise HTTPException(` - send an error response and stop.
- `status_code=status.HTTP_422_UNPROCESSABLE_CONTENT` - the constant `422`. This is the status FastAPI itself uses for validation errors, so our hand-written check looks the same to clients as the automatic ones. The name is the current one in this Starlette version (1.7.0); the older name `HTTP_422_UNPROCESSABLE_ENTITY` still exists but I checked `starlette/status.py`: using it emits a deprecation warning that points to the new name.
- `detail="start_date must be on or before end_date"` - a clear message. "On or before" allows equality: `start_date == end_date` is a valid one-day range. I tested both: `start=2026-02-01&end=2026-01-01` gives `422` with this message; `start=2026-01-01&end=2026-01-01` gives `200`.

**Why it is here.** An inverted range is not a crash, it just returns nothing. But a client sending it almost certainly has a bug (swapped fields), and silently returning an empty list hides that bug. Failing loudly with a precise message is kinder.

**If you removed or changed it.** The API would accept `start > end` and return empty results with status 200. Nothing would break; a frontend developer would just spend an hour wondering where their data went.

### Block 28: Building the result

```python
    return DateRange(start_date=start_date, end_date=end_date)
```

**Word by word**

- `return` - hand back the value.
- `DateRange(` - the dataclass constructor generated by `@dataclass` (Block 23).
- `start_date=start_date` - keyword argument: the field `start_date` gets the parameter `start_date`. The same name on both sides is normal: left is the field, right is the local variable.
- `end_date=end_date` - same for the second field.

**Why it is here.** It packages the two validated values into the object routers expect.

**If you removed or changed it.** The function would return `None`, and `expenses.py` would crash on `date_range.start_date` with `AttributeError: 'NoneType' object has no attribute 'start_date'`.

### Block 29: The DateRangeFilter alias

```python
DateRangeFilter = Annotated[DateRange, Depends(get_date_range)]
```

**Word by word**

- `DateRangeFilter` - the alias routers import.
- `Annotated[DateRange, Depends(get_date_range)]` - type `DateRange`, note "call `get_date_range`".

One subtle and useful point: when FastAPI builds the dependency tree for an endpoint with `date_range: DateRangeFilter`, it sees that `get_date_range` has two `Query` parameters, so **the endpoint inherits them**. `start_date` and `end_date` appear in `/docs` for `GET /api/v1/expenses` and the report endpoints even though those functions never mention them by name. I confirmed this in `/openapi.json`: the expenses endpoint lists `start_date` and `end_date` among its parameters, with the descriptions from Block 24 and 25.

**Why it is here.** Same reasons as `CurrentUser`: short, single source of truth, readable signatures.

**If you removed or changed it.** `expenses.py` and `reports.py` would fail at import.

### Compared to your old code

The old `app/oauth2.py` held both the token functions (compared above, in the `security.py` section) and the FastAPI parts. Here is the FastAPI part:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database import get_db
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def  get_current_user(token : str = Depends(oauth2_scheme) , db : Session = Depends(get_db)):

    credentials_exceptions = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED ,detail="Invalid id not found", headers={"WWW-Authenticate":"Bearer"})

    token = verify_access_token(token, credentials_exceptions)

    user = db.query(User).filter(User.id == token.id ).first()

    return user
```

And this is how your routers used it:

```python
def create_post(post: CreatePost, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
```

What changed and why:

1. **`tokenUrl='login'` to `tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"`.** Your old login route was `POST /login/` (router prefix `/login`, path `/`). The value `'login'` is a *relative* URL, which Swagger UI resolves against the page it is on; it reached your route only because the app had no prefix and the server redirected `/login` to `/login/`. The new project mounts everything under `/api/v1`, so the full path is written out, built from the same `settings` the router uses. If the prefix ever changes, `/docs` keeps working.

2. **`token: str = Depends(oauth2_scheme)` to `token: Annotated[str, Depends(oauth2_scheme)]`.** Same meaning, modern style (Block 4). It also lets the `db` parameter use the shared `DatabaseSession` alias.

3. **The 401 message.** `"Invalid id not found"` was a bit garbled and leaked a hint about what went wrong. `"Could not validate credentials"` is the standard neutral wording.

4. **`verify_access_token(token, credentials_exceptions)` to `decode_access_token(token)` plus an `if user_id is None`.** The HTTP decision now lives here, in the FastAPI-aware file, and the token function stays pure.

5. **`db.query(User).filter(User.id == token.id).first()` to `db.get(User, user_id)`.** Same row, SQLAlchemy 2.0 style, uses the identity map (Block 18).

6. **The missing check, kindly.** The old function returned `user` even when it was `None`. A user who had been deleted could still present a valid token; `get_current_user` would return `None`, and the first `current_user.id` in a router would crash with `AttributeError`, a 500. There was also no `is_active` column, so there was no way to block a user without deleting them. The new Block 19 covers both cases and answers 401.

7. **The type hint in routers.** Old routers wrote `current_user: int = Depends(get_current_user)`, but the function returned a `User` object, not an `int`. Python did not complain (hints are not enforced), but the hint was wrong and would mislead anyone reading it. New routers write `current_user: CurrentUser`, which is really `User`.

8. **The aliases.** Every old endpoint repeated `db: Session = Depends(get_db), current_user: int = Depends(get_current_user)`. The new ones write `db: DatabaseSession, current_user: CurrentUser`. Shorter, and impossible to get inconsistent.

**`DateRange` / `get_date_range` / `DateRangeFilter`: no old equivalent.** The old posts API had `limit`, `skip` and `search` parameters written directly in the `get_post` signature, which was fine for one endpoint. The expense tracker needs the same date filter in four endpoints (list expenses, and three reports). Writing it four times means four places to keep in sync and four places to forget the `start > end` check. A shared dependency is the FastAPI way to write it once.

### Key terms in this file

| Term | Meaning |
| --- | --- |
| dependency | A function FastAPI calls before your endpoint to prepare one parameter. |
| `Depends(f)` | The note that says "fill this parameter by calling `f`". Pass the function, do not call it. |
| `Annotated[T, note]` | Type `T` plus extra information that FastAPI reads; Python itself ignores the note. |
| alias (`DatabaseSession`, `CurrentUser`, `DateRangeFilter`) | A named, reusable `Annotated[...]` so routers do not repeat `Depends(...)`. |
| `use_cache=True` | Default of `Depends`: within one request, each dependency function runs once and its result is shared. |
| `yield` dependency | A generator dependency: code before `yield` runs before the endpoint, code after runs after the response (cleanup). `get_db` is one. |
| `OAuth2PasswordBearer` | Reads `Authorization: Bearer <token>`, returns the token or raises 401; also documents the scheme for `/docs`. |
| `tokenUrl` | The login URL written into the OpenAPI document so Swagger UI's Authorize button knows where to POST. Not used when handling requests. |
| Bearer token | A token sent as `Authorization: Bearer <token>`; whoever holds it is treated as the user. |
| `HTTPException` | Raise it to stop the request and send an error response with a status code, a `detail` and optional headers. |
| `status.HTTP_401_UNAUTHORIZED` | The number 401 with a readable name; from `starlette.status`. |
| `WWW-Authenticate: Bearer` | Header the HTTP spec requires on a 401; tells the client what kind of credentials to send. |
| `db.get(Model, pk)` | Fetch one row by primary key; checks the session's identity map first; returns `None` if absent. |
| identity map | The session's memory of already-loaded objects, so the same row is the same Python object within a session. |
| `is_active` | Boolean column on `users`; `False` blocks login and token use without deleting data. |
| `@dataclass` | Decorator that generates `__init__`, `__repr__` and `__eq__` from the class's annotated fields. |
| `Query(description=...)` | Note saying "read this parameter from the URL query string", plus text for `/docs`. |
| `= None` after `Annotated[...]` | Makes the parameter optional; the value when the client omits it. |
| 422 Unprocessable Content | The status for "your input is well-formed but invalid". FastAPI uses it for validation errors; `get_date_range` uses it for `start > end`. |

## Summary of this folder

`app/core/` holds the three files that every other part of the project leans on: `config.py` (document 03) reads the settings, and the two files in this document turn those settings into authentication. `security.py` is the pure layer: given a password it produces an Argon2id hash with a fresh random salt, given a password and a hash it says yes or no, given a user id it produces a signed JWT whose `sub` is the id and whose `exp` is a UTC time sixty minutes ahead, and given a token string it either returns the id or `None`, never raising. `dependencies.py` is the FastAPI layer on top: `oauth2_scheme` pulls the bearer token out of the `Authorization` header and tells `/docs` where to log in, `get_current_user` chains `decode_access_token` with `db.get(User, ...)` and the `is_active` check and raises one neutral 401 for every failure, and the aliases `DatabaseSession`, `CurrentUser` and `DateRangeFilter` package `Depends(...)` into single words that routers can use as types. FastAPI runs those dependencies deepest-first, once per request thanks to caching, so the endpoint and `get_current_user` share one database session that `get_db` closes after the response. The register and login endpoints in `app/routers/auth.py` are the only callers of `hash_password`, `verify_password` and `create_access_token`; every other router simply declares `current_user: CurrentUser` and is protected. Compared with the old `utils.py` and `oauth2.py`, the password part was already correct, and the rest fixes the local-time expiry bug, uses the standard `sub` claim as a string, separates "decode" from "respond 401", handles deleted and deactivated accounts, and removes the repetition from the routers.
