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
