from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Candidate Automation - Marathi Document Generator"
    app_env: str = "development"
    api_prefix: str = "/api"
    frontend_url: str = "http://127.0.0.1:5173"
    backend_url: str = "http://127.0.0.1:8000"
    frontend_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    database_url: str = "sqlite:///./candidate_registration.db"
    session_secret: str = "local-development-secret-change-before-deploying"
    encryption_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/api/auth/google/callback"
    google_cloud_project: str = ""
    google_application_credentials: str = ""
    translation_mock: bool = True
    polling_interval_seconds: int = 120
    max_upload_bytes: int = 15 * 1024 * 1024
    template_path: str = "app/templates/candidate_template.docx"
    cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
