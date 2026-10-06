"""
Application entry point: creates the FastAPI app and wires everything together.

Run locally with:
    uvicorn app.main:app --reload

Interactive API docs: http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import check_database_connection
from app.routers import auth, categories, expenses, health, reports, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: fail fast if the database is unreachable instead
    # of starting an API where every request would error.
    check_database_connection()
    logger.info("Database connection established")
    yield
    # Code after `yield` runs once at shutdown.


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Track your expenses, organise them by category and see where your money goes.",
    lifespan=lifespan,
)

# Lets browser frontends on the listed origins call this API.
# Tables are created by Alembic migrations (`alembic upgrade head`), not here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# /health stays unversioned; everything else lives under /api/v1.
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(categories.router, prefix=settings.API_V1_PREFIX)
app.include_router(expenses.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
