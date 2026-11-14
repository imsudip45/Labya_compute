import logging
import secrets
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    """All configuration comes from environment variables (or backend/.env locally)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./labhya-dev.db"
    secret_key: str = ""
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    # Comma-separated list of exact origins allowed to call the API from a browser.
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:3001"
    # Cloudflare Tunnel, which connects renters to containers (see app/cloudflare.py).
    # Without these, renting is turned off: nobody could connect to a session.
    cloudflare_api_token: str = ""
    cloudflare_account_id: str = ""
    cloudflare_zone_id: str = ""
    tunnel_domain: str = ""  # sessions get sess-<id>.<tunnel_domain>
    # "Add funds" credits the wallet without taking a payment. Never enable this
    # in production once real money is involved.
    simulated_payments: bool = True
    max_failed_logins: int = 5
    login_lockout_minutes: int = 15

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def tunnels_enabled(self) -> bool:
        return all((self.cloudflare_api_token, self.cloudflare_account_id, self.cloudflare_zone_id, self.tunnel_domain))

    @property
    def sqlalchemy_url(self) -> str:
        # Providers hand out postgres:// or postgresql://; use the psycopg 3 driver for both.
        for prefix in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefix):
                return "postgresql+psycopg://" + self.database_url[len(prefix):]
        return self.database_url

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _check(self):
        if self.is_production:
            problems = []
            if len(self.secret_key) < 32:
                problems.append("SECRET_KEY must be set to at least 32 random characters")
            if self.sqlalchemy_url.startswith("sqlite"):
                problems.append("DATABASE_URL must point to PostgreSQL")
            if "*" in self.cors_allowed_origins:
                problems.append("CORS_ALLOWED_ORIGINS must list exact origins, not *")
            if problems:
                raise ValueError("Invalid production settings: " + "; ".join(problems))
        elif not self.secret_key:
            # Development only: tokens stop working when the process restarts.
            self.secret_key = secrets.token_urlsafe(48)
            log.warning("SECRET_KEY is not set; using a temporary key for this process.")
        return self


settings = Settings()
