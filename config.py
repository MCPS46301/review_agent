from pydantic_settings import BaseSettings
from typing import Optional


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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
