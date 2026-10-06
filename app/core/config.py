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
