from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os


def _strip(key: str, default: str = "") -> str:
    """Read an env var and strip surrounding whitespace/newlines."""
    return os.environ.get(key, default).strip()


class Settings(BaseSettings):
    business_name: str = "Macomb Powersports"
    business_owner_email: str = "lloyd@macombpowersports.com"
    business_owner_name: str = "Lloyd"

    app_secret_key: str = "change-this-secret-key-in-production"
    app_base_url: str = "http://localhost:8000"
    poll_interval_minutes: int = 15

    database_url: str = "sqlite:///./reviews.db"
    cron_secret: Optional[str] = None

    anthropic_api_key: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_refresh_token: Optional[str] = None
    google_location_name: Optional[str] = None

    @field_validator("smtp_use_tls", mode="before")
    @classmethod
    def strip_bool(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator(
        "database_url", "anthropic_api_key", "smtp_username", "smtp_password",
        "smtp_from_email", "smtp_host", "cron_secret",
        "google_client_id", "google_client_secret", "google_refresh_token",
        "google_location_name",
        mode="before",
    )
    @classmethod
    def strip_str(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
