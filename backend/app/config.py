import logging
import secrets
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    postgres_db: str = "labhya_compute"
    postgres_user: str = "labhya_user"
    postgres_password: str = "labhya_password"
    db_host: str = "db"
    db_port: int = 5432
    database_url: Optional[str] = None
    # Must be set through the SECRET_KEY environment variable in any real deployment.
    secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours for stable local dev dev sessions
    refresh_token_expire_days: int = 7
    relay_host: str = "localhost"
    relay_port_range_start: int = 8001
    relay_port_range_end: int = 8999
    cors_allowed_origins: str = "*"

    @property
    def get_database_url(self) -> str:
        url = self.database_url
        if url:
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.db_host}:{self.db_port}/{self.postgres_db}"

    @property
    def get_cors_origins(self) -> List[str]:
        if not self.cors_allowed_origins:
            return ["*"]
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

if not settings.secret_key:
    # Without a configured key, use a random one for this process only. Logins then
    # stop working after a restart, which is acceptable for local development but
    # makes a missing production setting obvious instead of silently insecure.
    settings.secret_key = secrets.token_urlsafe(48)
    logging.getLogger(__name__).warning(
        "SECRET_KEY is not set; using a temporary random key. Set SECRET_KEY in the environment."
    )
