from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Business Info
    business_name: str = "Macomb Powersports"
    business_owner_email: str = "owner@macombpowersports.com"
    business_owner_name: str = "Owner"

    # App
    app_secret_key: str = "change-this-secret-key-in-production"
    app_base_url: str = "http://localhost:8000"
    poll_interval_minutes: int = 15

    # Database — SQLite for local dev, Supabase PostgreSQL for production
    # Supabase connection string from: Project Settings → Database → Connection string (URI)
    # Use the "Session mode" pooler URL for Vercel serverless:
    # postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
    database_url: str = "sqlite:///./reviews.db"

    # Vercel Cron secret (set CRON_SECRET in Vercel env vars to protect the /api/cron endpoint)
    cron_secret: Optional[str] = None

    # Claude API
    anthropic_api_key: str = ""

    # Email Notifications (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    # Google Business Profile API
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_refresh_token: Optional[str] = None
    google_location_name: Optional[str] = None  # e.g. "accounts/123/locations/456"

    # Facebook Graph API
    facebook_page_access_token: Optional[str] = None
    facebook_page_id: Optional[str] = None

    # Yelp Fusion API (read-only — Yelp does not allow API-based review responses)
    yelp_api_key: Optional[str] = None
    yelp_business_id: Optional[str] = None  # e.g. "macomb-powersports-macomb"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
